"""MCP resources for Trading212 API data access.

This module provides resource endpoints that can be accessed through the MCP
protocol to retrieve data from the Trading212 API.
"""

from mcp_server import client, mcp
from models import (
    Account,
    AccountBucketResultResponse,
    Cash,
    Exchange,
    Order,
    Position,
    ReportResponse,
    TradeableInstrument,
)

__all__ = [
    "get_account_info",
    "get_account_cash",
    "get_account_positions",
    "get_account_position_by_ticker",
    "get_orders",
    "get_order_by_id",
    "get_pies",
    "get_pie_by_id",
    "get_instruments",
    "get_exchanges",
    "get_reports",
]


# ---- Account Resources ----


@mcp.resource("trading212://account/info")
def get_account_info() -> Account:
    """
    Fetch account metadata including ID and currency code.

    Returns:
        Account object with metadata information.
    """
    return client.get_account_info()


@mcp.resource("trading212://account/cash")
def get_account_cash() -> Cash:
    """
    Fetch account cash balance information.

    Returns:
        Cash object with balance details.
    """
    return client.get_account_cash()


@mcp.resource("trading212://account/portfolio")
def get_account_positions() -> list[Position]:
    """
    Fetch all open positions in the portfolio.

    Returns:
        List of Position objects.
    """
    return client.get_account_positions()


@mcp.resource("trading212://account/portfolio/{ticker}")
def get_account_position_by_ticker(ticker: str) -> Position:
    """
    Fetch an open position by ticker symbol.

    Args:
        ticker: Ticker symbol of the instrument (e.g., 'AAPL_US_EQ').

    Returns:
        Position object for the specified ticker.
    """
    return client.get_account_position_by_ticker(ticker)


# ---- Order Resources ----


@mcp.resource("trading212://orders")
def get_orders() -> list[Order]:
    """
    Fetch all current orders.

    Returns:
        List of Order objects.
    """
    return client.get_orders()


@mcp.resource("trading212://orders/{order_id}")
def get_order_by_id(order_id: int) -> Order:
    """
    Fetch a specific order by ID.

    Args:
        order_id: Unique identifier of the order.

    Returns:
        Order object with order details.
    """
    return client.get_order_by_id(order_id)


# ---- Pie Resources ----


@mcp.resource("trading212://pies")
def get_pies() -> list[AccountBucketResultResponse]:
    """
    Fetch all pies (portfolio buckets).

    Returns:
        List of AccountBucketResultResponse objects.
    """
    return client.get_pies()


@mcp.resource("trading212://pies/{pie_id}")
def get_pie_by_id(pie_id: int) -> AccountBucketResultResponse:
    """
    Fetch a specific pie by ID.

    Args:
        pie_id: Unique identifier of the pie.

    Returns:
        AccountBucketResultResponse with pie details.
    """
    return client.get_pie_by_id(pie_id)


# ---- Market Data Resources ----


@mcp.resource("trading212://instruments")
def get_instruments() -> list[TradeableInstrument]:
    """
    Fetch all tradeable instruments.

    Returns:
        List of TradeableInstrument objects.
    """
    return client.get_instruments()


@mcp.resource("trading212://exchanges")
def get_exchanges() -> list[Exchange]:
    """
    Fetch all exchanges and their working schedules.

    Returns:
        List of Exchange objects.
    """
    return client.get_exchanges()


# ---- Report Resources ----


@mcp.resource("trading212://history/exports")
def get_reports() -> list[ReportResponse]:
    """
    Fetch all account export reports.

    Returns:
        List of ReportResponse objects.
    """
    return client.get_reports()
