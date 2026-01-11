"""Tests for MCP tools.

This module contains tests for the MCP tools to ensure they're properly
registered with the expected names.
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


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
