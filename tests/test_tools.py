"""Tests for MCP tools.

This module contains tests for the MCP tools to ensure they're properly
registered with the expected names and that cache-first behavior works correctly.
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from models import (
    HistoricalOrder,
    HistoricalOrderDetails,
    HistoryDividendItem,
    HistoryTransactionItem,
    PaginatedResponseHistoricalOrder,
    PaginatedResponseHistoryDividendItem,
    PaginatedResponseHistoryTransactionItem,
)


@pytest.fixture(autouse=True)
def mock_env_variables():
    """Set up environment variables before importing tools."""
    env_vars = {
        "TRADING212_API_KEY": "test_api_key",
        "TRADING212_API_SECRET": "test_api_secret",
        "ENVIRONMENT": "demo",
    }
    with patch.dict(os.environ, env_vars):
        yield


class TestToolNames:
    """Tests to verify tool naming convention is followed."""

    def test_search_instruments_tool_exists(self) -> None:
        """Tool should be named 'search_instruments'."""
        # Need to reload the module after setting env vars
        if "tools" in sys.modules:
            del sys.modules["tools"]
        if "mcp_server" in sys.modules:
            del sys.modules["mcp_server"]
        from tools import search_instruments

        assert search_instruments is not None
        assert callable(search_instruments)

    def test_search_exchanges_tool_exists(self) -> None:
        """Tool should be named 'search_exchanges'."""
        if "tools" in sys.modules:
            del sys.modules["tools"]
        if "mcp_server" in sys.modules:
            del sys.modules["mcp_server"]
        from tools import search_exchanges

        assert search_exchanges is not None
        assert callable(search_exchanges)

    def test_get_pies_tool_exists(self) -> None:
        """Tool should be named 'get_pies'."""
        if "tools" in sys.modules:
            del sys.modules["tools"]
        if "mcp_server" in sys.modules:
            del sys.modules["mcp_server"]
        from tools import get_pies

        assert get_pies is not None
        assert callable(get_pies)

    def test_get_orders_tool_exists(self) -> None:
        """Tool should be named 'get_orders'."""
        if "tools" in sys.modules:
            del sys.modules["tools"]
        if "mcp_server" in sys.modules:
            del sys.modules["mcp_server"]
        from tools import get_orders

        assert get_orders is not None
        assert callable(get_orders)

    def test_place_market_order_tool_exists(self) -> None:
        """Tool should be named 'place_market_order'."""
        if "tools" in sys.modules:
            del sys.modules["tools"]
        if "mcp_server" in sys.modules:
            del sys.modules["mcp_server"]
        from tools import place_market_order

        assert place_market_order is not None
        assert callable(place_market_order)

    def test_get_account_info_tool_exists(self) -> None:
        """Tool should be named 'get_account_info'."""
        if "tools" in sys.modules:
            del sys.modules["tools"]
        if "mcp_server" in sys.modules:
            del sys.modules["mcp_server"]
        from tools import get_account_info

        assert get_account_info is not None
        assert callable(get_account_info)

    def test_get_positions_tool_exists(self) -> None:
        """Tool should be named 'get_positions'."""
        if "tools" in sys.modules:
            del sys.modules["tools"]
        if "mcp_server" in sys.modules:
            del sys.modules["mcp_server"]
        from tools import get_positions

        assert get_positions is not None
        assert callable(get_positions)

    def test_get_order_history_tool_exists(self) -> None:
        """Tool should be named 'get_order_history'."""
        if "tools" in sys.modules:
            del sys.modules["tools"]
        if "mcp_server" in sys.modules:
            del sys.modules["mcp_server"]
        from tools import get_order_history

        assert get_order_history is not None
        assert callable(get_order_history)

    def test_get_dividends_tool_exists(self) -> None:
        """Tool should be named 'get_dividends'."""
        if "tools" in sys.modules:
            del sys.modules["tools"]
        if "mcp_server" in sys.modules:
            del sys.modules["mcp_server"]
        from tools import get_dividends

        assert get_dividends is not None
        assert callable(get_dividends)

    def test_get_transactions_tool_exists(self) -> None:
        """Tool should be named 'get_transactions'."""
        if "tools" in sys.modules:
            del sys.modules["tools"]
        if "mcp_server" in sys.modules:
            del sys.modules["mcp_server"]
        from tools import get_transactions

        assert get_transactions is not None
        assert callable(get_transactions)


class TestToolAllExports:
    """Tests for the __all__ export list."""

    def test_all_tools_are_exported(self) -> None:
        """All tools should be listed in __all__."""
        if "tools" in sys.modules:
            del sys.modules["tools"]
        if "mcp_server" in sys.modules:
            del sys.modules["mcp_server"]
        from tools import __all__

        expected_tools = [
            "search_instruments",
            "search_exchanges",
            "get_pies",
            "create_pie",
            "delete_pie",
            "get_pie",
            "update_pie",
            "duplicate_pie",
            "get_orders",
            "place_limit_order",
            "place_market_order",
            "place_stop_order",
            "place_stop_limit_order",
            "cancel_order",
            "get_order",
            "get_account_info",
            "get_account_cash",
            "get_positions",
            "get_position",
            "get_order_history",
            "get_dividends",
            "get_exports",
            "create_export",
            "get_transactions",
        ]

        for tool_name in expected_tools:
            assert tool_name in __all__, f"Tool '{tool_name}' not in __all__"


class TestCacheFirstBehavior:
    """Tests for cache-first behavior in historical data tools."""

    @pytest.fixture
    def mock_data_store(self) -> MagicMock:
        """Create a mock data store."""
        mock = MagicMock()
        mock.enabled = True
        return mock

    @pytest.fixture
    def sample_orders(self) -> list[HistoricalOrder]:
        """Sample orders for testing."""
        return [
            HistoricalOrder(
                order=HistoricalOrderDetails(
                    id=1,
                    ticker="AAPL_US_EQ",
                    quantity=10.0,
                    filledQuantity=10.0,
                ),
            ),
        ]

    @pytest.fixture
    def sample_dividends(self) -> list[HistoryDividendItem]:
        """Sample dividends for testing."""
        return [
            HistoryDividendItem(
                ticker="AAPL_US_EQ",
                reference="DIV-001",
                amount=5.0,
            ),
        ]

    @pytest.fixture
    def sample_transactions(self) -> list[HistoryTransactionItem]:
        """Sample transactions for testing."""
        return [
            HistoryTransactionItem(
                reference="TXN-001",
                type="DEPOSIT",
                amount=100.0,
            ),
        ]

    def test_get_dividends_uses_cache_when_fresh(
        self, mock_data_store: MagicMock, sample_dividends: list[HistoryDividendItem]
    ) -> None:
        """Should return cached data without syncing when cache is fresh."""
        mock_data_store.is_cache_fresh.return_value = True
        mock_data_store.get_dividends.return_value = sample_dividends

        # Clear module cache to allow mocking
        if "tools" in sys.modules:
            del sys.modules["tools"]
        if "mcp_server" in sys.modules:
            del sys.modules["mcp_server"]

        with patch("mcp_server.client") as mock_client:
            mock_client._get_data_store.return_value = mock_data_store
            from tools import get_dividends

            result = get_dividends()

        assert isinstance(result, PaginatedResponseHistoryDividendItem)
        assert result.items == sample_dividends
        assert result.nextPagePath is None
        mock_data_store.is_cache_fresh.assert_called_once_with("dividends", None)
        mock_data_store.sync_dividends.assert_not_called()
        mock_client.get_dividends.assert_not_called()

    def test_get_dividends_syncs_when_cache_stale(
        self, mock_data_store: MagicMock, sample_dividends: list[HistoryDividendItem]
    ) -> None:
        """Should sync cache before returning when cache is stale."""
        mock_data_store.is_cache_fresh.return_value = False
        mock_data_store.get_dividends.return_value = sample_dividends

        if "tools" in sys.modules:
            del sys.modules["tools"]
        if "mcp_server" in sys.modules:
            del sys.modules["mcp_server"]

        with patch("mcp_server.client") as mock_client:
            mock_client._get_data_store.return_value = mock_data_store
            from tools import get_dividends

            result = get_dividends()

        assert isinstance(result, PaginatedResponseHistoryDividendItem)
        assert result.items == sample_dividends
        mock_data_store.sync_dividends.assert_called_once_with(
            mock_client, incremental=True
        )

    def test_get_dividends_force_refresh_syncs_even_when_fresh(
        self, mock_data_store: MagicMock, sample_dividends: list[HistoryDividendItem]
    ) -> None:
        """Should sync when force_refresh=True even if cache is fresh."""
        # is_cache_fresh returns False when max_age=0 (force refresh)
        mock_data_store.is_cache_fresh.return_value = False
        mock_data_store.get_dividends.return_value = sample_dividends

        if "tools" in sys.modules:
            del sys.modules["tools"]
        if "mcp_server" in sys.modules:
            del sys.modules["mcp_server"]

        with patch("mcp_server.client") as mock_client:
            mock_client._get_data_store.return_value = mock_data_store
            from tools import get_dividends

            result = get_dividends(force_refresh=True)

        assert isinstance(result, PaginatedResponseHistoryDividendItem)
        # max_age=0 is passed when force_refresh=True
        mock_data_store.is_cache_fresh.assert_called_once_with("dividends", 0)
        mock_data_store.sync_dividends.assert_called_once()

    def test_get_dividends_falls_back_to_api_when_cache_disabled(self) -> None:
        """Should call API directly when cache is disabled."""
        if "tools" in sys.modules:
            del sys.modules["tools"]
        if "mcp_server" in sys.modules:
            del sys.modules["mcp_server"]

        api_response = PaginatedResponseHistoryDividendItem(
            items=[],
            nextPagePath="cursor=123",
        )

        with patch("mcp_server.client") as mock_client:
            mock_client._get_data_store.return_value = None  # Cache disabled
            mock_client.get_dividends.return_value = api_response
            from tools import get_dividends

            result = get_dividends(cursor=1, ticker="AAPL_US_EQ", limit=10)

        assert result == api_response
        mock_client.get_dividends.assert_called_once_with(
            cursor=1, ticker="AAPL_US_EQ", limit=10
        )

    def test_get_order_history_uses_cache_when_fresh(
        self, mock_data_store: MagicMock, sample_orders: list[HistoricalOrder]
    ) -> None:
        """Should return cached orders without syncing when cache is fresh."""
        mock_data_store.is_cache_fresh.return_value = True
        mock_data_store.get_orders.return_value = sample_orders

        if "tools" in sys.modules:
            del sys.modules["tools"]
        if "mcp_server" in sys.modules:
            del sys.modules["mcp_server"]

        with patch("mcp_server.client") as mock_client:
            mock_client._get_data_store.return_value = mock_data_store
            from tools import get_order_history

            result = get_order_history()

        assert isinstance(result, PaginatedResponseHistoricalOrder)
        assert result.items == sample_orders
        assert result.nextPagePath is None
        mock_data_store.is_cache_fresh.assert_called_once_with("orders", None)
        mock_data_store.sync_orders.assert_not_called()

    def test_get_order_history_syncs_when_stale(
        self, mock_data_store: MagicMock, sample_orders: list[HistoricalOrder]
    ) -> None:
        """Should sync orders when cache is stale."""
        mock_data_store.is_cache_fresh.return_value = False
        mock_data_store.get_orders.return_value = sample_orders

        if "tools" in sys.modules:
            del sys.modules["tools"]
        if "mcp_server" in sys.modules:
            del sys.modules["mcp_server"]

        with patch("mcp_server.client") as mock_client:
            mock_client._get_data_store.return_value = mock_data_store
            from tools import get_order_history

            get_order_history()

        mock_data_store.sync_orders.assert_called_once_with(mock_client)

    def test_get_order_history_falls_back_to_api_when_cache_disabled(self) -> None:
        """Should call API directly when cache is disabled."""
        if "tools" in sys.modules:
            del sys.modules["tools"]
        if "mcp_server" in sys.modules:
            del sys.modules["mcp_server"]

        api_response = PaginatedResponseHistoricalOrder(
            items=[],
            nextPagePath="cursor=123",
        )

        with patch("mcp_server.client") as mock_client:
            mock_client._get_data_store.return_value = None
            mock_client.get_historical_order_data.return_value = api_response
            from tools import get_order_history

            result = get_order_history(cursor=1, ticker="AAPL_US_EQ", limit=5)

        assert result == api_response
        mock_client.get_historical_order_data.assert_called_once_with(
            cursor=1, ticker="AAPL_US_EQ", limit=5
        )

    def test_get_transactions_uses_cache_when_fresh(
        self,
        mock_data_store: MagicMock,
        sample_transactions: list[HistoryTransactionItem],
    ) -> None:
        """Should return cached transactions without syncing when cache is fresh."""
        mock_data_store.is_cache_fresh.return_value = True
        mock_data_store.get_transactions.return_value = sample_transactions

        if "tools" in sys.modules:
            del sys.modules["tools"]
        if "mcp_server" in sys.modules:
            del sys.modules["mcp_server"]

        with patch("mcp_server.client") as mock_client:
            mock_client._get_data_store.return_value = mock_data_store
            from tools import get_transactions

            result = get_transactions()

        assert isinstance(result, PaginatedResponseHistoryTransactionItem)
        assert result.items == sample_transactions
        assert result.nextPagePath is None
        mock_data_store.is_cache_fresh.assert_called_once_with("transactions", None)
        mock_data_store.sync_transactions.assert_not_called()

    def test_get_transactions_syncs_when_stale(
        self,
        mock_data_store: MagicMock,
        sample_transactions: list[HistoryTransactionItem],
    ) -> None:
        """Should sync transactions when cache is stale."""
        mock_data_store.is_cache_fresh.return_value = False
        mock_data_store.get_transactions.return_value = sample_transactions

        if "tools" in sys.modules:
            del sys.modules["tools"]
        if "mcp_server" in sys.modules:
            del sys.modules["mcp_server"]

        with patch("mcp_server.client") as mock_client:
            mock_client._get_data_store.return_value = mock_data_store
            from tools import get_transactions

            get_transactions()

        mock_data_store.sync_transactions.assert_called_once_with(
            mock_client, incremental=True
        )

    def test_get_transactions_falls_back_to_api_when_cache_disabled(self) -> None:
        """Should call API directly when cache is disabled."""
        if "tools" in sys.modules:
            del sys.modules["tools"]
        if "mcp_server" in sys.modules:
            del sys.modules["mcp_server"]

        api_response = PaginatedResponseHistoryTransactionItem(
            items=[],
            nextPagePath="cursor=123",
        )

        with patch("mcp_server.client") as mock_client:
            mock_client._get_data_store.return_value = None
            mock_client.get_history_transactions.return_value = api_response
            from tools import get_transactions

            result = get_transactions(
                cursor="abc", time_from="2024-01-01T00:00:00Z", limit=10
            )

        assert result == api_response
        mock_client.get_history_transactions.assert_called_once_with(
            cursor="abc", time_from="2024-01-01T00:00:00Z", limit=10
        )

    def test_get_dividends_filters_by_ticker(
        self, mock_data_store: MagicMock, sample_dividends: list[HistoryDividendItem]
    ) -> None:
        """Should pass ticker filter to data store."""
        mock_data_store.is_cache_fresh.return_value = True
        mock_data_store.get_dividends.return_value = sample_dividends

        if "tools" in sys.modules:
            del sys.modules["tools"]
        if "mcp_server" in sys.modules:
            del sys.modules["mcp_server"]

        with patch("mcp_server.client") as mock_client:
            mock_client._get_data_store.return_value = mock_data_store
            from tools import get_dividends

            get_dividends(ticker="MSFT_US_EQ")

        mock_data_store.get_dividends.assert_called_once_with(ticker="MSFT_US_EQ")

    def test_get_transactions_filters_by_time_from(
        self,
        mock_data_store: MagicMock,
        sample_transactions: list[HistoryTransactionItem],
    ) -> None:
        """Should pass time_from filter to data store."""
        mock_data_store.is_cache_fresh.return_value = True
        mock_data_store.get_transactions.return_value = sample_transactions

        if "tools" in sys.modules:
            del sys.modules["tools"]
        if "mcp_server" in sys.modules:
            del sys.modules["mcp_server"]

        with patch("mcp_server.client") as mock_client:
            mock_client._get_data_store.return_value = mock_data_store
            from tools import get_transactions

            get_transactions(time_from="2024-06-01T00:00:00Z")

        mock_data_store.get_transactions.assert_called_once_with(
            time_from="2024-06-01T00:00:00Z"
        )
