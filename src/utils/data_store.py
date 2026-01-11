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
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

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
]

logger = logging.getLogger(__name__)


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

            # Extract taxes from fill.walletImpact if present
            taxes_json = None
            if order.fill and order.fill.walletImpact and order.fill.walletImpact.taxes:
                taxes_json = json.dumps(
                    [t.model_dump(mode="json") for t in order.fill.walletImpact.taxes]
                )

            raw_json = order.model_dump_json()

            # Extract values from nested structure
            order_details = order.order
            fill_details = order.fill

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
                        order_details.status.value
                        if order_details and order_details.status
                        else None,
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

        try:
            # Fetch all orders from API (paginated)
            all_orders: list[HistoricalOrder] = []
            cursor: int | None = None

            while True:
                orders = api_client.get_historical_order_data(
                    cursor=cursor,
                    limit=8,  # Trading212 bug: limit > 8 causes 500 errors
                )
                if not orders:
                    break

                all_orders.extend(orders)

                # Check if there are more pages
                # Orders are returned newest first, so we need the oldest ID
                if len(orders) < 8:
                    break

                # Use the oldest order ID as the cursor for the next page
                oldest_order = min(orders, key=lambda o: o.id or 0)
                if oldest_order.id is None:
                    break
                cursor = oldest_order.id

            # Upsert into local cache
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
            )

        except Exception as e:
            logger.error(f"Failed to sync orders: {e}")
            return SyncResult(
                table="orders",
                records_fetched=0,
                records_added=0,
                total_records=len(self.get_orders()) if self.enabled else 0,
                last_sync=datetime.now().isoformat(),
                error=str(e),
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
            except sqlite3.IntegrityError:
                pass

        conn.commit()
        return inserted

    def sync_dividends(self, api_client: Trading212Client) -> SyncResult:
        """Sync dividends from the API to the local cache.

        Args:
            api_client: Trading212 API client instance.

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
            # Fetch all dividends from API (paginated)
            all_dividends: list[HistoryDividendItem] = []
            cursor: int | None = None

            while True:
                response = api_client.get_dividends(cursor=cursor, limit=50)
                if not response.items:
                    break

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
            except sqlite3.IntegrityError:
                pass

        conn.commit()
        return inserted

    def sync_transactions(self, api_client: Trading212Client) -> SyncResult:
        """Sync transactions from the API to the local cache.

        Args:
            api_client: Trading212 API client instance.

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
            # Fetch all transactions from API (paginated)
            all_transactions: list[HistoryTransactionItem] = []
            cursor: str | None = None

            while True:
                response = api_client.get_history_transactions(cursor=cursor, limit=50)
                if not response.items:
                    break

                all_transactions.extend(response.items)

                # Check for next page
                if not response.nextPagePath:
                    break

                # Extract cursor from nextPagePath
                import httpx

                parsed = httpx.URL(response.nextPagePath)
                cursor = parsed.params.get("cursor")
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

        Args:
            api_client: Trading212 API client instance.

        Returns:
            Dictionary mapping table names to their SyncResult.
        """
        return {
            "orders": self.sync_orders(api_client),
            "dividends": self.sync_dividends(api_client),
            "transactions": self.sync_transactions(api_client),
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

    def get_stats(self) -> CacheStats:
        """Get statistics about the cache.

        Returns:
            CacheStats with record counts and sync times.
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
        )
