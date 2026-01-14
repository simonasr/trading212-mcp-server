"""Local SQLite cache for immutable historical Trading212 data.

This module provides a caching layer that stores historical orders, dividends,
and transactions locally to bypass API rate limits and enable richer analysis.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

from config import CACHE_FRESHNESS_MINUTES
from models import (
    HistoricalOrder,
    HistoryDividendItem,
    HistoryTransactionItem,
)

if TYPE_CHECKING:
    from utils.client import Trading212Client

__all__ = [
    "HistoricalDataStore",
    "SyncResult",
    "CacheStats",
    "DataCoverage",
]

logger = logging.getLogger(__name__)

# Order statuses that are considered final/immutable
# Orders in these states should not be overwritten by API updates
IMMUTABLE_ORDER_STATUSES: frozenset[str] = frozenset(
    {"FILLED", "CANCELLED", "REJECTED"}
)

# Valid table names and their date columns (whitelist for SQL injection prevention)
VALID_TABLES: frozenset[str] = frozenset({"orders", "dividends", "transactions"})
VALID_DATE_COLUMNS: dict[str, str] = {
    "orders": "date_created",
    "dividends": "paid_on",
    "transactions": "datetime",
}


@dataclass
class SyncResult:
    """Result of a sync operation."""

    table: str
    records_fetched: int
    records_added: int
    total_records: int
    last_sync: str
    error: str | None = None


@dataclass
class DataCoverage:
    """Date range coverage for cached data."""

    count: int
    oldest_date: str | None
    newest_date: str | None


@dataclass
class CacheStats:
    """Statistics about the local cache."""

    enabled: bool
    database_path: str
    database_size_bytes: int
    orders_count: int
    dividends_count: int
    transactions_count: int
    last_orders_sync: str | None
    last_dividends_sync: str | None
    last_transactions_sync: str | None
    # Data coverage - helps users know if cache is complete
    orders_coverage: DataCoverage | None
    dividends_coverage: DataCoverage | None
    transactions_coverage: DataCoverage | None


class HistoricalDataStore:
    """Local SQLite cache for immutable historical data.

    This class manages a local SQLite database that caches historical orders,
    dividends, and transactions from the Trading212 API. The data is immutable
    (orders are only stored when FILLED/CANCELLED, dividends and transactions
    are historical records), so it's safe to cache indefinitely.

    The cache supports incremental sync - only new records are fetched from
    the API on subsequent syncs.

    Attributes:
        db_path: Path to the SQLite database file.
        account_id: Trading212 account ID (used for multi-account support).
        enabled: Whether caching is enabled.
    """

    def __init__(
        self,
        db_path: str,
        account_id: int,
        enabled: bool = True,
    ) -> None:
        """Initialize the data store.

        Args:
            db_path: Path to the SQLite database file.
            account_id: Trading212 account ID.
            enabled: Whether caching is enabled.
        """
        self.db_path = db_path
        self.account_id = account_id
        self.enabled = enabled
        self._conn: sqlite3.Connection | None = None

        if self.enabled:
            self._ensure_schema()

    def _get_connection(self) -> sqlite3.Connection:
        """Get or create a database connection."""
        if self._conn is None:
            # Ensure directory exists
            db_dir = Path(self.db_path).parent
            db_dir.mkdir(parents=True, exist_ok=True)

            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def _ensure_schema(self) -> None:
        """Create database schema if it doesn't exist."""
        schema_path = Path(__file__).parent / "schema.sql"
        with open(schema_path) as f:
            schema_sql = f.read()

        conn = self._get_connection()
        conn.executescript(schema_sql)
        conn.commit()
        logger.info(f"Database schema ensured at {self.db_path}")

    def close(self) -> None:
        """Close the database connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    # ---- Freshness Methods ----

    def is_cache_fresh(
        self,
        table: str,
        max_age_minutes: int | None = None,
    ) -> bool:
        """Check if cache is fresh enough to skip API sync.

        Args:
            table: Table name ("orders", "dividends", "transactions").
            max_age_minutes: Maximum age in minutes for cache to be considered fresh.
                            None = use config default (CACHE_FRESHNESS_MINUTES).
                            0 = never fresh (always sync).
                            -1 = always fresh (never sync automatically).

        Returns:
            True if cache is fresh (no sync needed), False otherwise.
        """
        if not self.enabled:
            return False

        # Use provided value or config default
        freshness_minutes = (
            max_age_minutes if max_age_minutes is not None else CACHE_FRESHNESS_MINUTES
        )

        # Handle special values (works for both explicit param and config default)
        if freshness_minutes == -1:
            return True  # Never sync automatically
        if freshness_minutes == 0:
            return False  # Force sync

        metadata = self._get_sync_metadata(table)
        if not metadata or not metadata.get("last_sync"):
            return False  # Never synced

        try:
            last_sync = datetime.fromisoformat(metadata["last_sync"])
            # We always store naive local time via datetime.now().isoformat() in
            # _update_sync_metadata, so this should always be naive. The tzinfo
            # check is a defensive guard in case the stored format ever changes.
            if last_sync.tzinfo is not None:
                last_sync = last_sync.replace(tzinfo=None)
            age = datetime.now() - last_sync
            is_fresh = age < timedelta(minutes=freshness_minutes)
            if is_fresh:
                logger.debug(
                    "Cache for %s is fresh (age: %s, max: %d min)",
                    table,
                    age,
                    freshness_minutes,
                )
            else:
                logger.debug(
                    "Cache for %s is stale (age: %s, max: %d min)",
                    table,
                    age,
                    freshness_minutes,
                )
            return is_fresh
        except (ValueError, TypeError) as e:
            logger.warning("Failed to parse last_sync timestamp: %s", e)
            return False

    def _get_newest_record_date(self, table: str, date_column: str) -> str | None:
        """Get the newest record date from a table.

        Args:
            table: Table name (must be in VALID_TABLES).
            date_column: Column containing the date (must match VALID_DATE_COLUMNS).

        Returns:
            ISO 8601 date string of newest record, or None if empty.

        Raises:
            ValueError: If table or date_column is not in whitelist.
        """
        # Validate against whitelist to prevent SQL injection
        if table not in VALID_TABLES:
            raise ValueError(f"Invalid table: {table}")
        if date_column != VALID_DATE_COLUMNS.get(table):
            raise ValueError(f"Invalid date_column for {table}: {date_column}")

        conn = self._get_connection()
        row = conn.execute(
            f"SELECT MAX({date_column}) as newest FROM {table} WHERE account_id = ?",  # noqa: S608
            (self.account_id,),
        ).fetchone()
        return row["newest"] if row and row["newest"] else None

    # ---- Order Methods ----

    def get_orders(
        self,
        ticker: str | None = None,
        status: str | None = None,
    ) -> list[HistoricalOrder]:
        """Get cached orders.

        Args:
            ticker: Optional ticker to filter by.
            status: Optional status to filter by.

        Returns:
            List of HistoricalOrder objects from cache.
        """
        if not self.enabled:
            return []

        conn = self._get_connection()
        query = "SELECT raw_json FROM orders WHERE account_id = ?"
        params: list[Any] = [self.account_id]

        if ticker:
            query += " AND ticker = ?"
            params.append(ticker)
        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY date_created DESC"

        cursor = conn.execute(query, params)
        rows = cursor.fetchall()

        orders = []
        for row in rows:
            try:
                data = json.loads(row["raw_json"])
                orders.append(HistoricalOrder.model_validate(data))
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"Failed to parse cached order: {e}")

        return orders

    def _upsert_orders(self, orders: list[HistoricalOrder]) -> int:
        """Insert or update orders in the cache.

        Args:
            orders: List of orders to upsert.

        Returns:
            Number of new records inserted.
        """
        if not orders:
            return 0

        conn = self._get_connection()
        inserted = 0

        for order in orders:
            # Skip orders without an ID (shouldn't happen but be safe)
            if order.id is None:
                logger.warning("Skipping order without ID")
                continue

            # Extract values from nested structure
            order_details = order.order
            fill_details = order.fill

            # Get the new status from API
            new_status = (
                order_details.status.value
                if order_details and order_details.status
                else None
            )

            # Check if existing record has immutable status (immutability guard)
            existing = conn.execute(
                "SELECT status FROM orders WHERE id = ? AND account_id = ?",
                (order.id, self.account_id),
            ).fetchone()

            if existing:
                existing_status = existing["status"]
                if existing_status in IMMUTABLE_ORDER_STATUSES:
                    # Log discrepancy if status changed for immutable record
                    if existing_status != new_status:
                        logger.warning(
                            "Discrepancy detected: order %s has immutable status '%s' "
                            "but API returned '%s' - keeping cached version",
                            order.id,
                            existing_status,
                            new_status,
                        )
                    else:
                        logger.debug(
                            "Order %s already cached with immutable status '%s', skipping",
                            order.id,
                            existing_status,
                        )
                    continue  # Skip update for immutable records

            # Extract taxes from fill.walletImpact if present
            taxes_json = None
            if order.fill and order.fill.walletImpact and order.fill.walletImpact.taxes:
                taxes_json = json.dumps(
                    [t.model_dump(mode="json") for t in order.fill.walletImpact.taxes]
                )

            raw_json = order.model_dump_json()

            try:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO orders (
                        id, account_id, ticker, type, status, executor,
                        ordered_quantity, filled_quantity, limit_price, stop_price,
                        fill_price, fill_cost, fill_result, fill_id, fill_type,
                        filled_value, ordered_value, parent_order, time_validity,
                        date_created, date_executed, date_modified, taxes_json, raw_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        order_details.id if order_details else None,
                        self.account_id,
                        order_details.ticker if order_details else None,
                        order_details.type.value
                        if order_details and order_details.type
                        else None,
                        new_status,
                        order_details.initiatedFrom.value
                        if order_details and order_details.initiatedFrom
                        else None,
                        order_details.quantity if order_details else None,
                        order_details.filledQuantity if order_details else None,
                        order_details.limitPrice if order_details else None,
                        order_details.stopPrice if order_details else None,
                        fill_details.price if fill_details else None,
                        fill_details.walletImpact.netValue
                        if fill_details and fill_details.walletImpact
                        else None,
                        fill_details.walletImpact.realisedProfitLoss
                        if fill_details and fill_details.walletImpact
                        else None,
                        fill_details.id if fill_details else None,
                        fill_details.tradingMethod if fill_details else None,
                        None,  # filled_value - not in new API
                        None,  # ordered_value - not in new API
                        None,  # parent_order - not in new API
                        None,  # time_validity - not in new API
                        order_details.createdAt.isoformat()
                        if order_details and order_details.createdAt
                        else None,
                        fill_details.filledAt.isoformat()
                        if fill_details and fill_details.filledAt
                        else None,
                        None,  # date_modified - not in new API
                        taxes_json,
                        raw_json,
                    ),
                )
                inserted += 1
            except sqlite3.IntegrityError:
                # Record already exists with same primary key
                logger.debug("Order %s already exists, skipping", order.id)

        conn.commit()
        return inserted

    def sync_orders(self, api_client: Trading212Client) -> SyncResult:
        """Sync orders from the API to the local cache.

        Args:
            api_client: Trading212 API client instance.

        Returns:
            SyncResult with details about the sync operation.
        """
        if not self.enabled:
            return SyncResult(
                table="orders",
                records_fetched=0,
                records_added=0,
                total_records=0,
                last_sync=datetime.now().isoformat(),
                error="Cache is disabled",
            )

        # Fetch all orders from API (paginated)
        all_orders: list[HistoricalOrder] = []
        cursor: int | None = None
        pagination_error: str | None = None

        while True:
            try:
                response = api_client.get_historical_order_data(
                    cursor=cursor,
                    limit=8,  # Trading212 bug: limit > 8 causes 500 errors
                )
            except Exception as e:
                # Log pagination error but continue with what we have
                logger.warning(f"Orders pagination stopped due to error: {e}")
                pagination_error = f"Pagination stopped: {e}"
                break

            if not response.items:
                break

            all_orders.extend(response.items)

            # Check for next page using nextPagePath (like dividends)
            if not response.nextPagePath:
                break

            # Extract cursor from nextPagePath
            # Format: /api/v0/equity/history/orders?cursor=123&limit=8
            from urllib.parse import parse_qs, urlparse

            next_path = response.nextPagePath
            if next_path.startswith("/"):
                parsed = urlparse(next_path)
                params = parse_qs(parsed.query)
            else:
                params = parse_qs(next_path)

            cursor_list = params.get("cursor", [])
            if cursor_list:
                cursor = int(cursor_list[0])
            else:
                break

        # Upsert into local cache (even if pagination failed partway)
        added = self._upsert_orders(all_orders)

        # Update sync metadata
        now = datetime.now().isoformat()
        self._update_sync_metadata("orders", now, len(self.get_orders()))

        return SyncResult(
            table="orders",
            records_fetched=len(all_orders),
            records_added=added,
            total_records=len(self.get_orders()),
            last_sync=now,
            error=pagination_error,
        )

    # ---- Dividend Methods ----

    def get_dividends(self, ticker: str | None = None) -> list[HistoryDividendItem]:
        """Get cached dividends.

        Args:
            ticker: Optional ticker to filter by.

        Returns:
            List of HistoryDividendItem objects from cache.
        """
        if not self.enabled:
            return []

        conn = self._get_connection()
        query = "SELECT raw_json FROM dividends WHERE account_id = ?"
        params: list[Any] = [self.account_id]

        if ticker:
            query += " AND ticker = ?"
            params.append(ticker)

        query += " ORDER BY paid_on DESC"

        cursor = conn.execute(query, params)
        rows = cursor.fetchall()

        dividends = []
        for row in rows:
            try:
                data = json.loads(row["raw_json"])
                dividends.append(HistoryDividendItem.model_validate(data))
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"Failed to parse cached dividend: {e}")

        return dividends

    def _upsert_dividends(self, dividends: list[HistoryDividendItem]) -> int:
        """Insert or update dividends in the cache.

        Args:
            dividends: List of dividends to upsert.

        Returns:
            Number of new records inserted.
        """
        if not dividends:
            return 0

        conn = self._get_connection()
        inserted = 0

        for dividend in dividends:
            if not dividend.reference:
                continue

            raw_json = dividend.model_dump_json()

            try:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO dividends (
                        reference, account_id, ticker, amount, amount_eur,
                        gross_per_share, quantity, type, paid_on, raw_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        dividend.reference,
                        self.account_id,
                        dividend.ticker,
                        dividend.amount,
                        dividend.amountInEuro,
                        dividend.grossAmountPerShare,
                        dividend.quantity,
                        dividend.type,
                        dividend.paidOn.isoformat() if dividend.paidOn else None,
                        raw_json,
                    ),
                )
                inserted += 1
            except sqlite3.IntegrityError as exc:
                # Skip dividends that violate database integrity constraints,
                # preserving the previous behavior of continuing with remaining items.
                logger.warning(
                    "Failed to upsert dividend with reference %s: %s",
                    dividend.reference,
                    exc,
                )

        conn.commit()
        return inserted

    def sync_dividends(
        self,
        api_client: Trading212Client,
        incremental: bool = True,
    ) -> SyncResult:
        """Sync dividends from the API to the local cache.

        Note: The dividends API does not support server-side time filtering
        (unlike transactions). Incremental mode performs client-side filtering:
        pages are fetched in reverse chronological order, and for each page only
        dividends newer than the latest cached dividend are kept. If a page
        contains a mix of new and already-cached/older dividends, all new
        dividends from that page are included but no further pages are fetched.
        This reduces API calls when only a few new dividends exist.

        Args:
            api_client: Trading212 API client instance.
            incremental: If True, use the above incremental behavior and stop
                        pagination once a page contains any already-cached dates.
                        If False, fetch and process all available records (full sync).

        Returns:
            SyncResult with details about the sync operation.
        """
        if not self.enabled:
            return SyncResult(
                table="dividends",
                records_fetched=0,
                records_added=0,
                total_records=0,
                last_sync=datetime.now().isoformat(),
                error="Cache is disabled",
            )

        try:
            # Determine cutoff datetime for incremental sync
            # We parse to datetime for proper timezone-aware comparison
            # (string comparison fails with different tz representations)
            cutoff_dt: datetime | None = None
            if incremental:
                newest_date = self._get_newest_record_date("dividends", "paid_on")
                if newest_date:
                    cutoff_dt = datetime.fromisoformat(newest_date)
                    logger.info("Incremental dividends sync from %s", newest_date)

            # Fetch dividends from API (paginated)
            all_dividends: list[HistoryDividendItem] = []
            cursor: int | None = None

            while True:
                response = api_client.get_dividends(cursor=cursor, limit=50)
                if not response.items:
                    break

                # For incremental sync, filter client-side (API lacks time_from param)
                # This stops pagination early once we hit already-cached dates
                # Use >= (not >) to include records with same timestamp as cutoff:
                # multiple dividends from different tickers can have the same paidOn
                # timestamp, and we don't want to miss any (upsert handles duplicates)
                # Compare datetime objects directly (handles timezone differences)
                if cutoff_dt:
                    new_items = [
                        d for d in response.items if d.paidOn and d.paidOn >= cutoff_dt
                    ]
                    all_dividends.extend(new_items)
                    # Stop when we encounter older records (already in cache)
                    if len(new_items) < len(response.items):
                        logger.debug(
                            "Reached cached records, stopping incremental sync"
                        )
                        break
                else:
                    all_dividends.extend(response.items)

                # Check for next page
                if not response.nextPagePath:
                    break

                # Extract cursor from nextPagePath
                # Format: /api/v0/history/dividends?cursor=123
                import httpx

                parsed = httpx.URL(response.nextPagePath)
                cursor_str = parsed.params.get("cursor")
                if cursor_str:
                    cursor = int(cursor_str)
                else:
                    break

            # Upsert into local cache
            added = self._upsert_dividends(all_dividends)

            # Update sync metadata
            now = datetime.now().isoformat()
            self._update_sync_metadata("dividends", now, len(self.get_dividends()))

            return SyncResult(
                table="dividends",
                records_fetched=len(all_dividends),
                records_added=added,
                total_records=len(self.get_dividends()),
                last_sync=now,
            )

        except Exception as e:
            logger.error(f"Failed to sync dividends: {e}")
            return SyncResult(
                table="dividends",
                records_fetched=0,
                records_added=0,
                total_records=len(self.get_dividends()) if self.enabled else 0,
                last_sync=datetime.now().isoformat(),
                error=str(e),
            )

    # ---- Transaction Methods ----

    def get_transactions(
        self,
        time_from: str | None = None,
        transaction_type: str | None = None,
    ) -> list[HistoryTransactionItem]:
        """Get cached transactions.

        Args:
            time_from: Optional start time filter (ISO 8601).
            transaction_type: Optional transaction type filter.

        Returns:
            List of HistoryTransactionItem objects from cache.
        """
        if not self.enabled:
            return []

        conn = self._get_connection()
        query = "SELECT raw_json FROM transactions WHERE account_id = ?"
        params: list[Any] = [self.account_id]

        if time_from:
            query += " AND datetime >= ?"
            params.append(time_from)
        if transaction_type:
            query += " AND type = ?"
            params.append(transaction_type)

        query += " ORDER BY datetime DESC"

        cursor = conn.execute(query, params)
        rows = cursor.fetchall()

        transactions = []
        for row in rows:
            try:
                data = json.loads(row["raw_json"])
                transactions.append(HistoryTransactionItem.model_validate(data))
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"Failed to parse cached transaction: {e}")

        return transactions

    def _upsert_transactions(self, transactions: list[HistoryTransactionItem]) -> int:
        """Insert or update transactions in the cache.

        Args:
            transactions: List of transactions to upsert.

        Returns:
            Number of new records inserted.
        """
        if not transactions:
            return 0

        conn = self._get_connection()
        inserted = 0

        for transaction in transactions:
            if not transaction.reference:
                continue

            raw_json = transaction.model_dump_json()

            try:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO transactions (
                        reference, account_id, type, amount, datetime, raw_json
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        transaction.reference,
                        self.account_id,
                        transaction.type.value if transaction.type else None,
                        transaction.amount,
                        transaction.dateTime.isoformat()
                        if transaction.dateTime
                        else None,
                        raw_json,
                    ),
                )
                inserted += 1
            except sqlite3.IntegrityError as exc:
                # Skip transactions that violate database constraints but log for diagnostics.
                logger.warning(
                    "Failed to upsert transaction with reference %s: %s",
                    transaction.reference,
                    exc,
                )

        conn.commit()
        return inserted

    def sync_transactions(
        self,
        api_client: Trading212Client,
        incremental: bool = True,
    ) -> SyncResult:
        """Sync transactions from the API to the local cache.

        Supports incremental sync - if cache has existing data, only fetches
        transactions after the newest cached record.

        Args:
            api_client: Trading212 API client instance.
            incremental: If True, only fetch new records since last sync.
                        If False, fetch all records (full sync).

        Returns:
            SyncResult with details about the sync operation.
        """
        if not self.enabled:
            return SyncResult(
                table="transactions",
                records_fetched=0,
                records_added=0,
                total_records=0,
                last_sync=datetime.now().isoformat(),
                error="Cache is disabled",
            )

        try:
            # Determine time_from for incremental sync
            # The transactions API has a time_from parameter we can use directly
            api_time_from: str | None = None
            if incremental:
                newest_date = self._get_newest_record_date("transactions", "datetime")
                if newest_date:
                    api_time_from = newest_date
                    logger.info("Incremental transactions sync from %s", api_time_from)

            # Fetch transactions from API (paginated)
            all_transactions: list[HistoryTransactionItem] = []
            cursor: str | None = None
            # pagination_time comes from API's nextPagePath and is required for
            # cursor-based pagination to work correctly
            pagination_time: str | None = None

            while True:
                # First request uses api_time_from (incremental filter)
                # Subsequent requests use pagination_time from API's cursor mechanism
                # Falls back to api_time_from if API doesn't provide time param
                effective_time = (
                    pagination_time if pagination_time is not None else api_time_from
                )

                response = api_client.get_history_transactions(
                    cursor=cursor, time_from=effective_time, limit=50
                )
                if not response.items:
                    break

                all_transactions.extend(response.items)

                # Check for next page
                if not response.nextPagePath:
                    break

                # Extract cursor AND time from nextPagePath
                # Note: transactions API returns query string (limit=50&cursor=xxx&time=xxx)
                # not a full path like dividends/orders, so we need to handle both formats
                # The API requires BOTH cursor and time for pagination to work
                from urllib.parse import parse_qs, urlparse

                next_path = response.nextPagePath
                # If it starts with /, it's a full path; otherwise it's a query string
                if next_path.startswith("/"):
                    parsed = urlparse(next_path)
                    params = parse_qs(parsed.query)
                else:
                    # It's just a query string
                    params = parse_qs(next_path)

                cursor_list = params.get("cursor", [])
                cursor = cursor_list[0] if cursor_list else None

                # pagination_time is used with cursor for subsequent requests
                time_list = params.get("time", [])
                pagination_time = time_list[0] if time_list else None

                if not cursor:
                    break

            # Upsert into local cache
            added = self._upsert_transactions(all_transactions)

            # Update sync metadata
            now = datetime.now().isoformat()
            self._update_sync_metadata(
                "transactions", now, len(self.get_transactions())
            )

            return SyncResult(
                table="transactions",
                records_fetched=len(all_transactions),
                records_added=added,
                total_records=len(self.get_transactions()),
                last_sync=now,
            )

        except Exception as e:
            logger.error(f"Failed to sync transactions: {e}")
            return SyncResult(
                table="transactions",
                records_fetched=0,
                records_added=0,
                total_records=len(self.get_transactions()) if self.enabled else 0,
                last_sync=datetime.now().isoformat(),
                error=str(e),
            )

    # ---- Sync All ----

    def sync_all(self, api_client: Trading212Client) -> dict[str, SyncResult]:
        """Sync all tables from the API to the local cache.

        Uses incremental sync for dividends and transactions (only fetches
        new records since last sync). Orders always do a full sync due to
        API limitations.

        Args:
            api_client: Trading212 API client instance.

        Returns:
            Dictionary mapping table names to their SyncResult.
        """
        return {
            "orders": self.sync_orders(api_client),
            "dividends": self.sync_dividends(api_client, incremental=True),
            "transactions": self.sync_transactions(api_client, incremental=True),
        }

    # ---- Metadata Methods ----

    def _update_sync_metadata(
        self,
        table_name: str,
        last_sync: str,
        record_count: int,
    ) -> None:
        """Update sync metadata for a table."""
        conn = self._get_connection()
        conn.execute(
            """
            INSERT OR REPLACE INTO sync_metadata (
                table_name, account_id, last_sync, record_count
            ) VALUES (?, ?, ?, ?)
            """,
            (table_name, self.account_id, last_sync, record_count),
        )
        conn.commit()

    def _get_sync_metadata(self, table_name: str) -> dict[str, Any] | None:
        """Get sync metadata for a table."""
        conn = self._get_connection()
        cursor = conn.execute(
            """
            SELECT last_sync, last_cursor, record_count
            FROM sync_metadata
            WHERE table_name = ? AND account_id = ?
            """,
            (table_name, self.account_id),
        )
        row = cursor.fetchone()
        if row:
            return {
                "last_sync": row["last_sync"],
                "last_cursor": row["last_cursor"],
                "record_count": row["record_count"],
            }
        return None

    # ---- Management Methods ----

    def clear_cache(self, table: str | None = None) -> dict[str, int]:
        """Clear cached data.

        Args:
            table: Specific table to clear ("orders", "dividends", "transactions").
                   If None, clears all tables.

        Returns:
            Dictionary with counts of deleted records per table.
        """
        if not self.enabled:
            return {}

        conn = self._get_connection()
        deleted: dict[str, int] = {}

        tables = (
            [table]
            if table
            else ["orders", "dividends", "transactions", "sync_metadata"]
        )

        for t in tables:
            if t == "sync_metadata":
                cursor = conn.execute(
                    "DELETE FROM sync_metadata WHERE account_id = ?",
                    (self.account_id,),
                )
            else:
                cursor = conn.execute(
                    f"DELETE FROM {t} WHERE account_id = ?",  # noqa: S608
                    (self.account_id,),
                )
            deleted[t] = cursor.rowcount

        conn.commit()
        logger.info(f"Cache cleared: {deleted}")
        return deleted

    def _get_data_coverage(self, table: str, date_column: str) -> DataCoverage | None:
        """Get date range coverage for a table.

        Args:
            table: Table name (must be in VALID_TABLES).
            date_column: Column containing the date (must match VALID_DATE_COLUMNS).

        Returns:
            DataCoverage with count and date range, or None if empty.

        Raises:
            ValueError: If table or date_column is not in whitelist.
        """
        # Validate against whitelist to prevent SQL injection
        if table not in VALID_TABLES:
            raise ValueError(f"Invalid table: {table}")
        if date_column != VALID_DATE_COLUMNS.get(table):
            raise ValueError(f"Invalid date_column for {table}: {date_column}")

        conn = self._get_connection()
        row = conn.execute(
            f"""
            SELECT
                COUNT(*) as count,
                MIN({date_column}) as oldest,
                MAX({date_column}) as newest
            FROM {table}
            WHERE account_id = ?
            """,  # noqa: S608
            (self.account_id,),
        ).fetchone()

        if row and row["count"] > 0:
            return DataCoverage(
                count=row["count"],
                oldest_date=row["oldest"],
                newest_date=row["newest"],
            )
        return DataCoverage(count=0, oldest_date=None, newest_date=None)

    def get_stats(self) -> CacheStats:
        """Get statistics about the cache.

        Returns:
            CacheStats with record counts, sync times, and data coverage.
        """
        if not self.enabled:
            return CacheStats(
                enabled=False,
                database_path=self.db_path,
                database_size_bytes=0,
                orders_count=0,
                dividends_count=0,
                transactions_count=0,
                last_orders_sync=None,
                last_dividends_sync=None,
                last_transactions_sync=None,
                orders_coverage=None,
                dividends_coverage=None,
                transactions_coverage=None,
            )

        conn = self._get_connection()

        # Get record counts
        orders_count = conn.execute(
            "SELECT COUNT(*) FROM orders WHERE account_id = ?", (self.account_id,)
        ).fetchone()[0]
        dividends_count = conn.execute(
            "SELECT COUNT(*) FROM dividends WHERE account_id = ?", (self.account_id,)
        ).fetchone()[0]
        transactions_count = conn.execute(
            "SELECT COUNT(*) FROM transactions WHERE account_id = ?", (self.account_id,)
        ).fetchone()[0]

        # Get last sync times
        orders_meta = self._get_sync_metadata("orders")
        dividends_meta = self._get_sync_metadata("dividends")
        transactions_meta = self._get_sync_metadata("transactions")

        # Get data coverage (date ranges)
        orders_coverage = self._get_data_coverage("orders", "date_created")
        dividends_coverage = self._get_data_coverage("dividends", "paid_on")
        transactions_coverage = self._get_data_coverage("transactions", "datetime")

        # Get database file size
        db_size = 0
        if os.path.exists(self.db_path):
            db_size = os.path.getsize(self.db_path)

        return CacheStats(
            enabled=True,
            database_path=self.db_path,
            database_size_bytes=db_size,
            orders_count=orders_count,
            dividends_count=dividends_count,
            transactions_count=transactions_count,
            last_orders_sync=orders_meta["last_sync"] if orders_meta else None,
            last_dividends_sync=dividends_meta["last_sync"] if dividends_meta else None,
            last_transactions_sync=transactions_meta["last_sync"]
            if transactions_meta
            else None,
            orders_coverage=orders_coverage,
            dividends_coverage=dividends_coverage,
            transactions_coverage=transactions_coverage,
        )
