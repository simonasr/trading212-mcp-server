"""Tests for the HistoricalDataStore class."""

import sys
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from models import (
    HistoricalOrder,
    HistoricalOrderDetails,
    HistoricalOrderExecutorEnum,
    HistoricalOrderFill,
    HistoricalOrderStatusEnum,
    HistoricalOrderTypeEnum,
    HistoricalOrderWalletImpact,
    HistoryDividendItem,
    HistoryTransactionItem,
    HistoryTransactionTypeEnum,
    PaginatedResponseHistoricalOrder,
    PaginatedResponseHistoryDividendItem,
    PaginatedResponseHistoryTransactionItem,
)
from utils.data_store import HistoricalDataStore


def make_test_order(
    order_id: int,
    ticker: str = "AAPL_US_EQ",
    order_type: HistoricalOrderTypeEnum = HistoricalOrderTypeEnum.MARKET,
    status: HistoricalOrderStatusEnum = HistoricalOrderStatusEnum.FILLED,
    quantity: float = 10.0,
    filled_quantity: float = 10.0,
    fill_price: float | None = 150.25,
    created_at: datetime | None = None,
    filled_at: datetime | None = None,
) -> HistoricalOrder:
    """Create a test HistoricalOrder with the new nested structure."""
    order_details = HistoricalOrderDetails(
        id=order_id,
        ticker=ticker,
        type=order_type,
        status=status,
        quantity=quantity,
        filledQuantity=filled_quantity,
        initiatedFrom=HistoricalOrderExecutorEnum.API,
        createdAt=created_at or datetime(2024, 1, 15, 10, 30, 0),
    )

    fill_details = None
    if fill_price is not None:
        fill_details = HistoricalOrderFill(
            id=order_id + 1000,
            price=fill_price,
            quantity=filled_quantity,
            filledAt=filled_at or datetime(2024, 1, 15, 10, 30, 5),
            walletImpact=HistoricalOrderWalletImpact(
                netValue=fill_price * filled_quantity,
                currency="USD",
            ),
        )

    return HistoricalOrder(order=order_details, fill=fill_details)


@pytest.fixture
def temp_db_path() -> str:
    """Create a temporary database path."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        return f.name


@pytest.fixture
def data_store(temp_db_path: str) -> HistoricalDataStore:
    """Create a HistoricalDataStore instance with a temp database."""
    store = HistoricalDataStore(
        db_path=temp_db_path,
        account_id=12345,
        enabled=True,
    )
    yield store
    store.close()


@pytest.fixture
def disabled_data_store(temp_db_path: str) -> HistoricalDataStore:
    """Create a disabled HistoricalDataStore instance."""
    store = HistoricalDataStore(
        db_path=temp_db_path,
        account_id=12345,
        enabled=False,
    )
    yield store
    store.close()


@pytest.fixture
def sample_order() -> HistoricalOrder:
    """Create a sample historical order."""
    return make_test_order(
        order_id=1001,
        ticker="AAPL_US_EQ",
        order_type=HistoricalOrderTypeEnum.MARKET,
        status=HistoricalOrderStatusEnum.FILLED,
        quantity=10.0,
        filled_quantity=10.0,
        fill_price=150.25,
        created_at=datetime(2024, 1, 15, 10, 30, 0),
        filled_at=datetime(2024, 1, 15, 10, 30, 5),
    )


@pytest.fixture
def sample_dividend() -> HistoryDividendItem:
    """Create a sample dividend item."""
    return HistoryDividendItem(
        reference="DIV-12345",
        ticker="AAPL_US_EQ",
        amount=5.50,
        amountInEuro=5.00,
        grossAmountPerShare=0.55,
        quantity=10.0,
        type="DIVIDEND",
        paidOn=datetime(2024, 1, 20, 0, 0, 0),
    )


@pytest.fixture
def sample_transaction() -> HistoryTransactionItem:
    """Create a sample transaction item."""
    return HistoryTransactionItem(
        reference="TXN-67890",
        type=HistoryTransactionTypeEnum.DEPOSIT,
        amount=1000.0,
        dateTime=datetime(2024, 1, 10, 14, 0, 0),
    )


class TestDataStoreInit:
    """Tests for DataStore initialization."""

    def test_creates_database_directory(self, temp_db_path: str) -> None:
        """Should create the database directory if it doesn't exist."""
        nested_path = str(Path(temp_db_path).parent / "nested" / "test.db")
        store = HistoricalDataStore(
            db_path=nested_path,
            account_id=12345,
            enabled=True,
        )
        assert Path(nested_path).parent.exists()
        store.close()

    def test_creates_schema(self, data_store: HistoricalDataStore) -> None:
        """Should create all required tables."""
        conn = data_store._get_connection()
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}

        assert "orders" in tables
        assert "dividends" in tables
        assert "transactions" in tables
        assert "sync_metadata" in tables

    def test_disabled_store_skips_schema(
        self, disabled_data_store: HistoricalDataStore
    ) -> None:
        """Disabled store should not create schema."""
        # The store should work but return empty results
        orders = disabled_data_store.get_orders()
        assert orders == []


class TestOrderOperations:
    """Tests for order cache operations."""

    def test_upsert_order(
        self,
        data_store: HistoricalDataStore,
        sample_order: HistoricalOrder,
    ) -> None:
        """Should insert an order into the cache."""
        count = data_store._upsert_orders([sample_order])
        assert count == 1

        orders = data_store.get_orders()
        assert len(orders) == 1
        assert orders[0].id == sample_order.id
        assert orders[0].ticker == sample_order.ticker

    def test_upsert_duplicate_order(
        self,
        data_store: HistoricalDataStore,
        sample_order: HistoricalOrder,
    ) -> None:
        """Should handle duplicate orders (upsert behavior)."""
        data_store._upsert_orders([sample_order])
        data_store._upsert_orders([sample_order])

        orders = data_store.get_orders()
        assert len(orders) == 1

    def test_get_orders_filter_by_ticker(
        self,
        data_store: HistoricalDataStore,
        sample_order: HistoricalOrder,
    ) -> None:
        """Should filter orders by ticker."""
        # Insert the sample order
        data_store._upsert_orders([sample_order])

        # Insert another order with different ticker
        other_order = make_test_order(
            order_id=1002,
            ticker="MSFT_US_EQ",
            order_type=HistoricalOrderTypeEnum.MARKET,
            status=HistoricalOrderStatusEnum.FILLED,
        )
        data_store._upsert_orders([other_order])

        # Filter by ticker
        aapl_orders = data_store.get_orders(ticker="AAPL_US_EQ")
        assert len(aapl_orders) == 1
        assert aapl_orders[0].ticker == "AAPL_US_EQ"

    def test_get_orders_disabled(
        self, disabled_data_store: HistoricalDataStore
    ) -> None:
        """Disabled store should return empty list."""
        orders = disabled_data_store.get_orders()
        assert orders == []


class TestImmutabilityGuard:
    """Tests for the immutability guard on order updates."""

    def test_immutable_order_not_overwritten(
        self, data_store: HistoricalDataStore
    ) -> None:
        """Orders with immutable status should not be overwritten."""
        # Insert a FILLED order
        filled_order = make_test_order(
            order_id=2001,
            ticker="AAPL_US_EQ",
            status=HistoricalOrderStatusEnum.FILLED,
            fill_price=150.00,
        )
        data_store._upsert_orders([filled_order])

        # Try to update with different data
        updated_order = make_test_order(
            order_id=2001,
            ticker="AAPL_US_EQ",
            status=HistoricalOrderStatusEnum.FILLED,
            fill_price=999.99,  # Different price
        )
        count = data_store._upsert_orders([updated_order])

        # Should not have inserted (immutable record skipped)
        assert count == 0

        # Original data should be preserved
        orders = data_store.get_orders()
        assert len(orders) == 1
        assert orders[0].fillPrice == 150.00  # Original price preserved

    def test_immutable_cancelled_order_not_overwritten(
        self, data_store: HistoricalDataStore
    ) -> None:
        """Cancelled orders should also be immutable."""
        cancelled_order = make_test_order(
            order_id=2002,
            ticker="MSFT_US_EQ",
            status=HistoricalOrderStatusEnum.CANCELLED,
            fill_price=None,
        )
        data_store._upsert_orders([cancelled_order])

        # Try to update status
        changed_order = make_test_order(
            order_id=2002,
            ticker="MSFT_US_EQ",
            status=HistoricalOrderStatusEnum.FILLED,  # Changed status!
            fill_price=200.00,
        )
        count = data_store._upsert_orders([changed_order])

        assert count == 0  # Should be rejected

        # Check status was not changed
        orders = data_store.get_orders()
        assert len(orders) == 1
        assert orders[0].status == HistoricalOrderStatusEnum.CANCELLED

    def test_non_immutable_order_can_be_updated(
        self, data_store: HistoricalDataStore
    ) -> None:
        """Orders with non-immutable status can be updated."""
        # Insert a NEW order (not immutable)
        new_order = make_test_order(
            order_id=2003,
            ticker="GOOG_US_EQ",
            status=HistoricalOrderStatusEnum.NEW,
            fill_price=None,
        )
        data_store._upsert_orders([new_order])

        # Update to FILLED
        filled_order = make_test_order(
            order_id=2003,
            ticker="GOOG_US_EQ",
            status=HistoricalOrderStatusEnum.FILLED,
            fill_price=100.00,
        )
        count = data_store._upsert_orders([filled_order])

        assert count == 1  # Should update

        orders = data_store.get_orders()
        assert len(orders) == 1
        assert orders[0].status == HistoricalOrderStatusEnum.FILLED
        assert orders[0].fillPrice == 100.00

    def test_discrepancy_logged_for_status_mismatch(
        self, data_store: HistoricalDataStore, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Should log warning when API returns different status for immutable order."""
        import logging

        # Insert a FILLED order
        filled_order = make_test_order(
            order_id=2004,
            status=HistoricalOrderStatusEnum.FILLED,
        )
        data_store._upsert_orders([filled_order])

        # Try to update with CANCELLED status
        with caplog.at_level(logging.WARNING):
            changed_order = make_test_order(
                order_id=2004,
                status=HistoricalOrderStatusEnum.CANCELLED,
            )
            data_store._upsert_orders([changed_order])

        # Check that discrepancy was logged
        assert "Discrepancy detected" in caplog.text
        assert "FILLED" in caplog.text
        assert "CANCELLED" in caplog.text


class TestDividendOperations:
    """Tests for dividend cache operations."""

    def test_upsert_dividend(
        self,
        data_store: HistoricalDataStore,
        sample_dividend: HistoryDividendItem,
    ) -> None:
        """Should insert a dividend into the cache."""
        count = data_store._upsert_dividends([sample_dividend])
        assert count == 1

        dividends = data_store.get_dividends()
        assert len(dividends) == 1
        assert dividends[0].reference == sample_dividend.reference

    def test_upsert_dividend_without_reference(
        self, data_store: HistoricalDataStore
    ) -> None:
        """Should skip dividends without a reference."""
        dividend = HistoryDividendItem(
            reference=None,
            ticker="AAPL_US_EQ",
            amount=5.0,
        )
        count = data_store._upsert_dividends([dividend])
        assert count == 0

    def test_get_dividends_filter_by_ticker(
        self,
        data_store: HistoricalDataStore,
        sample_dividend: HistoryDividendItem,
    ) -> None:
        """Should filter dividends by ticker."""
        data_store._upsert_dividends([sample_dividend])

        other_dividend = HistoryDividendItem(
            reference="DIV-99999",
            ticker="MSFT_US_EQ",
            amount=3.0,
        )
        data_store._upsert_dividends([other_dividend])

        aapl_dividends = data_store.get_dividends(ticker="AAPL_US_EQ")
        assert len(aapl_dividends) == 1


class TestTransactionOperations:
    """Tests for transaction cache operations."""

    def test_upsert_transaction(
        self,
        data_store: HistoricalDataStore,
        sample_transaction: HistoryTransactionItem,
    ) -> None:
        """Should insert a transaction into the cache."""
        count = data_store._upsert_transactions([sample_transaction])
        assert count == 1

        transactions = data_store.get_transactions()
        assert len(transactions) == 1
        assert transactions[0].reference == sample_transaction.reference

    def test_get_transactions_filter_by_type(
        self,
        data_store: HistoricalDataStore,
        sample_transaction: HistoryTransactionItem,
    ) -> None:
        """Should filter transactions by type."""
        data_store._upsert_transactions([sample_transaction])

        other_txn = HistoryTransactionItem(
            reference="TXN-11111",
            type=HistoryTransactionTypeEnum.WITHDRAW,
            amount=-500.0,
        )
        data_store._upsert_transactions([other_txn])

        deposits = data_store.get_transactions(
            transaction_type=HistoryTransactionTypeEnum.DEPOSIT.value
        )
        assert len(deposits) == 1


class TestSyncOperations:
    """Tests for sync operations with mocked API client."""

    def test_sync_orders(
        self,
        data_store: HistoricalDataStore,
        sample_order: HistoricalOrder,
    ) -> None:
        """Should sync orders from API to cache."""
        mock_client = MagicMock()
        mock_client.get_historical_order_data.return_value = (
            PaginatedResponseHistoricalOrder(
                items=[sample_order],
                nextPagePath=None,
            )
        )

        result = data_store.sync_orders(mock_client)

        assert result.table == "orders"
        assert result.records_fetched == 1
        assert result.records_added == 1
        assert result.error is None

        # Verify order is in cache
        orders = data_store.get_orders()
        assert len(orders) == 1

    def test_sync_orders_handles_pagination(
        self, data_store: HistoricalDataStore
    ) -> None:
        """Should handle paginated order responses."""
        mock_client = MagicMock()

        # First page returns 8 orders with nextPagePath
        page1_orders = [
            make_test_order(order_id=i, ticker="AAPL_US_EQ") for i in range(8)
        ]
        # Second page returns 3 orders (no nextPagePath = last page)
        page2_orders = [
            make_test_order(order_id=i + 8, ticker="AAPL_US_EQ") for i in range(3)
        ]

        mock_client.get_historical_order_data.side_effect = [
            PaginatedResponseHistoricalOrder(
                items=page1_orders,
                nextPagePath="/api/v0/equity/history/orders?cursor=12345&limit=8",
            ),
            PaginatedResponseHistoricalOrder(
                items=page2_orders,
                nextPagePath=None,  # Last page
            ),
        ]

        result = data_store.sync_orders(mock_client)

        assert result.records_fetched == 11
        assert mock_client.get_historical_order_data.call_count == 2

    def test_sync_dividends(
        self,
        data_store: HistoricalDataStore,
        sample_dividend: HistoryDividendItem,
    ) -> None:
        """Should sync dividends from API to cache."""
        mock_client = MagicMock()
        mock_client.get_dividends.return_value = PaginatedResponseHistoryDividendItem(
            items=[sample_dividend],
            nextPagePath=None,
        )

        result = data_store.sync_dividends(mock_client)

        assert result.table == "dividends"
        assert result.records_fetched == 1
        assert result.error is None

    def test_sync_transactions(
        self,
        data_store: HistoricalDataStore,
        sample_transaction: HistoryTransactionItem,
    ) -> None:
        """Should sync transactions from API to cache."""
        mock_client = MagicMock()
        mock_client.get_history_transactions.return_value = (
            PaginatedResponseHistoryTransactionItem(
                items=[sample_transaction],
                nextPagePath=None,
            )
        )

        result = data_store.sync_transactions(mock_client)

        assert result.table == "transactions"
        assert result.records_fetched == 1
        assert result.error is None

    def test_sync_transactions_handles_query_string_pagination(
        self,
        data_store: HistoricalDataStore,
    ) -> None:
        """Should handle query string format nextPagePath (transactions API quirk)."""
        mock_client = MagicMock()

        # First page with query string format nextPagePath (no leading /)
        page1_txns = [
            HistoryTransactionItem(
                reference=f"ref-{i}",
                type=HistoryTransactionTypeEnum.DEPOSIT,
                amount=100.0 + i,
                dateTime=datetime(2024, 1, i + 1, tzinfo=UTC),
            )
            for i in range(3)
        ]
        page2_txns = [
            HistoryTransactionItem(
                reference=f"ref-{i + 3}",
                type=HistoryTransactionTypeEnum.DEPOSIT,
                amount=200.0 + i,
                dateTime=datetime(2024, 1, i + 4, tzinfo=UTC),
            )
            for i in range(2)
        ]

        mock_client.get_history_transactions.side_effect = [
            PaginatedResponseHistoryTransactionItem(
                items=page1_txns,
                # Query string format (no leading /) - this is what the API actually returns
                nextPagePath="limit=50&cursor=abc123&time=2024-01-01T00:00:00Z",
            ),
            PaginatedResponseHistoryTransactionItem(
                items=page2_txns,
                nextPagePath=None,
            ),
        ]

        result = data_store.sync_transactions(mock_client)

        assert result.table == "transactions"
        assert result.records_fetched == 5
        assert result.records_added == 5
        assert result.error is None
        assert mock_client.get_history_transactions.call_count == 2
        # Verify second call used cursor AND time from the query string
        second_call_args = mock_client.get_history_transactions.call_args_list[1]
        assert second_call_args.kwargs.get("cursor") == "abc123"
        assert second_call_args.kwargs.get("time_from") == "2024-01-01T00:00:00Z"

    def test_sync_all(self, data_store: HistoricalDataStore) -> None:
        """Should sync all tables."""
        mock_client = MagicMock()
        mock_client.get_historical_order_data.return_value = (
            PaginatedResponseHistoricalOrder(items=[], nextPagePath=None)
        )
        mock_client.get_dividends.return_value = PaginatedResponseHistoryDividendItem(
            items=[], nextPagePath=None
        )
        mock_client.get_history_transactions.return_value = (
            PaginatedResponseHistoryTransactionItem(items=[], nextPagePath=None)
        )

        results = data_store.sync_all(mock_client)

        assert "orders" in results
        assert "dividends" in results
        assert "transactions" in results

    def test_sync_handles_api_error(self, data_store: HistoricalDataStore) -> None:
        """Should handle API errors gracefully."""
        mock_client = MagicMock()
        mock_client.get_historical_order_data.side_effect = Exception("API Error")

        result = data_store.sync_orders(mock_client)

        assert result.error is not None
        assert "API Error" in result.error

    def test_sync_disabled_store(
        self, disabled_data_store: HistoricalDataStore
    ) -> None:
        """Disabled store should return error in sync result."""
        mock_client = MagicMock()

        result = disabled_data_store.sync_orders(mock_client)

        assert result.error == "Cache is disabled"


class TestCacheManagement:
    """Tests for cache management operations."""

    def test_clear_cache_all(
        self,
        data_store: HistoricalDataStore,
        sample_order: HistoricalOrder,
        sample_dividend: HistoryDividendItem,
        sample_transaction: HistoryTransactionItem,
    ) -> None:
        """Should clear all cached data."""
        # Populate cache
        data_store._upsert_orders([sample_order])
        data_store._upsert_dividends([sample_dividend])
        data_store._upsert_transactions([sample_transaction])

        # Clear all
        deleted = data_store.clear_cache()

        assert deleted["orders"] == 1
        assert deleted["dividends"] == 1
        assert deleted["transactions"] == 1

        # Verify cache is empty
        assert len(data_store.get_orders()) == 0
        assert len(data_store.get_dividends()) == 0
        assert len(data_store.get_transactions()) == 0

    def test_clear_cache_specific_table(
        self,
        data_store: HistoricalDataStore,
        sample_order: HistoricalOrder,
        sample_dividend: HistoryDividendItem,
    ) -> None:
        """Should clear only specified table."""
        data_store._upsert_orders([sample_order])
        data_store._upsert_dividends([sample_dividend])

        deleted = data_store.clear_cache(table="orders")

        assert deleted["orders"] == 1
        assert len(data_store.get_orders()) == 0
        # Dividends should still exist
        assert len(data_store.get_dividends()) == 1

    def test_get_stats(
        self,
        data_store: HistoricalDataStore,
        sample_order: HistoricalOrder,
        sample_dividend: HistoryDividendItem,
    ) -> None:
        """Should return accurate cache statistics."""
        data_store._upsert_orders([sample_order])
        data_store._upsert_dividends([sample_dividend])

        stats = data_store.get_stats()

        assert stats.enabled is True
        assert stats.orders_count == 1
        assert stats.dividends_count == 1
        assert stats.transactions_count == 0
        assert stats.database_size_bytes > 0

    def test_get_stats_disabled(self, disabled_data_store: HistoricalDataStore) -> None:
        """Disabled store should return empty stats."""
        stats = disabled_data_store.get_stats()

        assert stats.enabled is False
        assert stats.orders_count == 0


class TestSyncMetadata:
    """Tests for sync metadata operations."""

    def test_update_and_get_sync_metadata(
        self, data_store: HistoricalDataStore
    ) -> None:
        """Should store and retrieve sync metadata."""
        now = datetime.now().isoformat()
        data_store._update_sync_metadata("orders", now, 100)

        metadata = data_store._get_sync_metadata("orders")

        assert metadata is not None
        assert metadata["last_sync"] == now
        assert metadata["record_count"] == 100

    def test_get_nonexistent_metadata(self, data_store: HistoricalDataStore) -> None:
        """Should return None for nonexistent metadata."""
        metadata = data_store._get_sync_metadata("nonexistent")
        assert metadata is None


class TestCacheFreshness:
    """Tests for cache freshness checking."""

    def test_cache_never_synced_is_not_fresh(
        self, data_store: HistoricalDataStore
    ) -> None:
        """Cache should not be fresh if never synced."""
        assert data_store.is_cache_fresh("orders") is False
        assert data_store.is_cache_fresh("dividends") is False
        assert data_store.is_cache_fresh("transactions") is False

    def test_recently_synced_cache_is_fresh(
        self, data_store: HistoricalDataStore
    ) -> None:
        """Cache should be fresh if synced recently."""
        # Sync metadata with current timestamp
        now = datetime.now().isoformat()
        data_store._update_sync_metadata("orders", now, 10)

        # Default freshness is 60 minutes, so recently synced should be fresh
        assert data_store.is_cache_fresh("orders") is True

    def test_max_age_zero_always_returns_false(
        self, data_store: HistoricalDataStore
    ) -> None:
        """max_age_minutes=0 should always return False (force sync)."""
        now = datetime.now().isoformat()
        data_store._update_sync_metadata("orders", now, 10)

        # Even with fresh cache, max_age=0 should force sync
        assert data_store.is_cache_fresh("orders", max_age_minutes=0) is False

    def test_max_age_negative_one_always_returns_true(
        self, data_store: HistoricalDataStore
    ) -> None:
        """max_age_minutes=-1 should always return True (never auto-sync)."""
        # Even without any sync metadata, -1 should return True
        assert data_store.is_cache_fresh("orders", max_age_minutes=-1) is True

    def test_disabled_store_is_never_fresh(
        self, disabled_data_store: HistoricalDataStore
    ) -> None:
        """Disabled store should never be considered fresh."""
        assert disabled_data_store.is_cache_fresh("orders") is False

    def test_custom_max_age_minutes(self, data_store: HistoricalDataStore) -> None:
        """Should respect custom max_age_minutes parameter."""
        # Set sync time to 30 minutes ago
        thirty_min_ago = (datetime.now() - timedelta(minutes=30)).isoformat()
        data_store._update_sync_metadata("dividends", thirty_min_ago, 10)

        # Should be fresh with 60 minute threshold
        assert data_store.is_cache_fresh("dividends", max_age_minutes=60) is True

        # Should be stale with 15 minute threshold
        assert data_store.is_cache_fresh("dividends", max_age_minutes=15) is False


class TestIncrementalSync:
    """Tests for incremental sync functionality."""

    def test_get_newest_record_date_empty_table(
        self, data_store: HistoricalDataStore
    ) -> None:
        """Should return None for empty table."""
        result = data_store._get_newest_record_date("dividends", "paid_on")
        assert result is None

    def test_get_newest_record_date_with_data(
        self,
        data_store: HistoricalDataStore,
        sample_dividend: HistoryDividendItem,
    ) -> None:
        """Should return the newest date from table."""
        data_store._upsert_dividends([sample_dividend])

        result = data_store._get_newest_record_date("dividends", "paid_on")

        # Should return the date from our sample dividend
        assert result is not None

    def test_incremental_dividends_sync_uses_time_from(
        self, data_store: HistoricalDataStore
    ) -> None:
        """Incremental sync should only fetch new dividends."""
        # First, add an existing dividend
        existing_dividend = HistoryDividendItem(
            ticker="AAPL_US_EQ",
            reference="DIV-OLD",
            amount=5.0,
            paidOn=datetime(2024, 1, 1, 10, 0, 0, tzinfo=UTC),
        )
        data_store._upsert_dividends([existing_dividend])

        # Mock API client that returns new dividend
        mock_client = MagicMock()
        new_dividend = HistoryDividendItem(
            ticker="AAPL_US_EQ",
            reference="DIV-NEW",
            amount=10.0,
            paidOn=datetime(2024, 6, 1, 10, 0, 0, tzinfo=UTC),
        )
        mock_client.get_dividends.return_value = PaginatedResponseHistoryDividendItem(
            items=[new_dividend],
            nextPagePath=None,
        )

        # Incremental sync
        result = data_store.sync_dividends(mock_client, incremental=True)

        # Should have fetched 1 new record
        assert result.records_fetched == 1
        # Total should include both old and new
        assert result.total_records == 2

    def test_incremental_dividends_stops_on_mixed_page(
        self, data_store: HistoricalDataStore
    ) -> None:
        """Incremental sync should stop pagination when encountering a mixed page.

        A mixed page contains both new dividends (after cached date) and old
        dividends (before/equal to cached date). The sync should:
        1. Include all new dividends from the mixed page
        2. Stop pagination (not fetch subsequent pages)
        """
        # Add an existing dividend with a known date
        existing_dividend = HistoryDividendItem(
            ticker="AAPL_US_EQ",
            reference="DIV-EXISTING",
            amount=5.0,
            paidOn=datetime(2024, 3, 15, 10, 0, 0, tzinfo=UTC),
        )
        data_store._upsert_dividends([existing_dividend])

        # Mock API client returns a mixed page: 2 new + 1 old dividend
        mock_client = MagicMock()
        new_dividend_1 = HistoryDividendItem(
            ticker="AAPL_US_EQ",
            reference="DIV-NEW-1",
            amount=10.0,
            paidOn=datetime(2024, 6, 1, 10, 0, 0, tzinfo=UTC),
        )
        new_dividend_2 = HistoryDividendItem(
            ticker="MSFT_US_EQ",
            reference="DIV-NEW-2",
            amount=8.0,
            paidOn=datetime(2024, 5, 1, 10, 0, 0, tzinfo=UTC),
        )
        old_dividend = HistoryDividendItem(
            ticker="GOOG_US_EQ",
            reference="DIV-OLD",
            amount=3.0,
            paidOn=datetime(2024, 2, 1, 10, 0, 0, tzinfo=UTC),  # Before existing
        )
        # Page with mixed new/old dividends, has nextPagePath
        mock_client.get_dividends.return_value = PaginatedResponseHistoryDividendItem(
            items=[new_dividend_1, new_dividend_2, old_dividend],
            nextPagePath="cursor=123",  # Would have more pages
        )

        # Incremental sync
        result = data_store.sync_dividends(mock_client, incremental=True)

        # Should have fetched only the 2 new dividends (filtered out old)
        assert result.records_fetched == 2
        # Total: 1 existing + 2 new = 3
        assert result.total_records == 3
        # API should only be called once (pagination stopped due to old record)
        assert mock_client.get_dividends.call_count == 1

    def test_incremental_dividends_includes_same_timestamp(
        self, data_store: HistoricalDataStore
    ) -> None:
        """Incremental sync should include dividends with same timestamp as cached.

        Edge case: a new dividend from a different ticker could have the exact
        same timestamp as the newest cached dividend. We use >= comparison to
        ensure these aren't missed (upsert handles any true duplicates).
        """
        # Add an existing dividend with a known timestamp
        cached_timestamp = datetime(2024, 3, 15, 10, 0, 0, tzinfo=UTC)
        existing_dividend = HistoryDividendItem(
            ticker="AAPL_US_EQ",
            reference="DIV-EXISTING",
            amount=5.0,
            paidOn=cached_timestamp,
        )
        data_store._upsert_dividends([existing_dividend])

        # Mock API returns dividend with SAME timestamp but different ticker
        mock_client = MagicMock()
        same_timestamp_dividend = HistoryDividendItem(
            ticker="MSFT_US_EQ",  # Different ticker
            reference="DIV-SAME-TIME",
            amount=7.0,
            paidOn=cached_timestamp,  # Same timestamp as cached
        )
        mock_client.get_dividends.return_value = PaginatedResponseHistoryDividendItem(
            items=[same_timestamp_dividend],
            nextPagePath=None,
        )

        # Incremental sync
        result = data_store.sync_dividends(mock_client, incremental=True)

        # Should include the dividend with same timestamp
        assert result.records_fetched == 1
        # Total: 1 existing + 1 new (same timestamp, different ticker)
        assert result.total_records == 2

    def test_incremental_dividends_handles_different_timezones(
        self, data_store: HistoricalDataStore
    ) -> None:
        """Incremental sync should compare datetimes correctly across timezones.

        Edge case: API might return timestamps with different timezone offsets.
        String comparison would fail (e.g., '10:00:00Z' vs '15:00:00+05:00'),
        but datetime comparison handles this correctly.
        """
        from datetime import timezone

        # Add an existing dividend at 10:00 UTC
        utc_time = datetime(2024, 3, 15, 10, 0, 0, tzinfo=UTC)
        existing_dividend = HistoryDividendItem(
            ticker="AAPL_US_EQ",
            reference="DIV-EXISTING",
            amount=5.0,
            paidOn=utc_time,
        )
        data_store._upsert_dividends([existing_dividend])

        # Mock API returns dividend at 16:00+05:00 (which is 11:00 UTC - 1 hour later)
        mock_client = MagicMock()
        tz_plus_5 = timezone(timedelta(hours=5))
        different_tz_dividend = HistoryDividendItem(
            ticker="MSFT_US_EQ",
            reference="DIV-DIFFERENT-TZ",
            amount=7.0,
            # 16:00+05:00 = 11:00 UTC (1 hour after cached dividend)
            paidOn=datetime(2024, 3, 15, 16, 0, 0, tzinfo=tz_plus_5),
        )
        mock_client.get_dividends.return_value = PaginatedResponseHistoryDividendItem(
            items=[different_tz_dividend],
            nextPagePath=None,
        )

        # Incremental sync
        result = data_store.sync_dividends(mock_client, incremental=True)

        # Should include the dividend (it's newer when comparing actual time)
        assert result.records_fetched == 1
        assert result.total_records == 2
