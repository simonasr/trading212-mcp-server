"""MCP tools for Trading212 API operations.

This module provides tool functions that can be called through the MCP protocol
to interact with the Trading212 API.
"""

from datetime import datetime
from typing import Any

from mcp_server import client, mcp
from models import (
    Account,
    AccountBucketInstrumentsDetailedResponse,
    AccountBucketResultResponse,
    Cash,
    DividendCashActionEnum,
    DuplicateBucketRequest,
    EnqueuedReportResponse,
    Exchange,
    HistoricalOrder,
    LimitRequest,
    LimitRequestTimeValidityEnum,
    MarketRequest,
    Order,
    PaginatedResponseHistoryDividendItem,
    PaginatedResponseHistoryTransactionItem,
    PieRequest,
    Position,
    ReportDataIncluded,
    ReportResponse,
    StopLimitRequest,
    StopLimitRequestTimeValidityEnum,
    StopRequest,
    StopRequestTimeValidityEnum,
    TradeableInstrument,
)

__all__ = [
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
    # Cache management tools
    "sync_historical_data",
    "clear_cache",
    "cache_stats",
]


# Instruments Metadata


@mcp.tool("search_instruments")
def search_instruments(search_term: str | None = None) -> list[TradeableInstrument]:
    """
    Search for tradeable instruments by ticker or name.

    Args:
        search_term: Optional search term to filter instruments by ticker or name
            (case-insensitive). If not provided, returns all instruments.

    Returns:
        List of matching TradeableInstrument objects.
    """
    instruments = client.get_instruments()

    if not search_term:
        return instruments

    search_lower = search_term.lower()
    return [
        inst
        for inst in instruments
        if (inst.ticker and search_lower in inst.ticker.lower())
        or (inst.name and search_lower in inst.name.lower())
    ]


@mcp.tool("search_exchanges")
def search_exchanges(search_term: str | None = None) -> list[Exchange]:
    """
    Search for exchanges by name or ID.

    Args:
        search_term: Optional search term to filter exchanges by name or ID
            (case-insensitive). If not provided, returns all exchanges.

    Returns:
        List of matching Exchange objects.
    """
    exchanges = client.get_exchanges()

    if not search_term:
        return exchanges

    search_lower = search_term.lower()
    return [
        exch
        for exch in exchanges
        if (exch.name and search_lower in exch.name.lower())
        or (str(exch.id) == search_term)
    ]


# Pies


@mcp.tool("get_pies")
def get_pies() -> list[AccountBucketResultResponse]:
    """
    Fetch all pies (portfolio buckets) for the account.

    Returns:
        List of AccountBucketResultResponse objects representing all pies.
    """
    return client.get_pies()


@mcp.tool("create_pie")
def create_pie(
    name: str,
    instrument_shares: dict[str, float],
    dividend_cash_action: DividendCashActionEnum | None = None,
    end_date: datetime | None = None,
    goal: float | None = None,
    icon: str | None = None,
) -> AccountBucketInstrumentsDetailedResponse:
    """
    Create a new pie with the specified parameters.

    Args:
        name: Name of the pie.
        instrument_shares: Dictionary mapping instrument tickers to their weights
            (e.g., {'AAPL_US_EQ': 0.5, 'MSFT_US_EQ': 0.5}). Weights must sum to 1.0.
        dividend_cash_action: How dividends should be handled (REINVEST or
            TO_ACCOUNT_CASH). Defaults to REINVEST.
        end_date: Optional target end date in ISO 8601 format.
        goal: Total desired value of the pie in account currency.
        icon: Optional icon identifier for the pie.

    Returns:
        AccountBucketInstrumentsDetailedResponse with details of the created pie.
    """
    pie_data = PieRequest(
        name=name,
        instrumentShares=instrument_shares,
        dividendCashAction=dividend_cash_action,
        endDate=end_date,
        goal=goal,
        icon=icon,
    )
    return client.create_pie(pie_data)


@mcp.tool("delete_pie")
def delete_pie(pie_id: int) -> None:
    """
    Delete a pie by its ID.

    Args:
        pie_id: The unique identifier of the pie to delete.
    """
    client.delete_pie(pie_id)


@mcp.tool("get_pie")
def get_pie(pie_id: int) -> AccountBucketInstrumentsDetailedResponse:
    """
    Fetch a specific pie by its ID.

    Args:
        pie_id: The unique identifier of the pie.

    Returns:
        AccountBucketInstrumentsDetailedResponse with the pie details.
    """
    return client.get_pie_by_id(pie_id)


@mcp.tool("update_pie")
def update_pie(
    pie_id: int,
    name: str | None = None,
    instrument_shares: dict[str, float] | None = None,
    dividend_cash_action: DividendCashActionEnum | None = None,
    end_date: datetime | None = None,
    goal: float | None = None,
    icon: str | None = None,
) -> AccountBucketInstrumentsDetailedResponse:
    """
    Update an existing pie with new parameters.

    Note: The pie must be renamed when updating it.

    Args:
        pie_id: ID of the pie to update.
        name: New name for the pie (required when updating).
        instrument_shares: New dictionary mapping instrument tickers to weights.
        dividend_cash_action: How dividends should be handled.
        end_date: New target end date.
        goal: New total desired value in account currency.
        icon: New icon identifier.

    Returns:
        AccountBucketInstrumentsDetailedResponse with updated pie details.
    """
    pie_data = PieRequest(
        name=name,
        instrumentShares=instrument_shares,
        dividendCashAction=dividend_cash_action,
        endDate=end_date,
        goal=goal,
        icon=icon,
    )
    return client.update_pie(pie_id, pie_data)


@mcp.tool("duplicate_pie")
def duplicate_pie(
    pie_id: int,
    name: str | None = None,
    icon: str | None = None,
) -> AccountBucketInstrumentsDetailedResponse:
    """
    Create a duplicate of an existing pie.

    Args:
        pie_id: ID of the pie to duplicate.
        name: Optional new name for the duplicated pie.
        icon: Optional new icon for the duplicated pie.

    Returns:
        AccountBucketInstrumentsDetailedResponse with details of the duplicated pie.
    """
    duplicate_request = DuplicateBucketRequest(name=name, icon=icon)
    return client.duplicate_pie(pie_id, duplicate_request)


# Equity Orders


@mcp.tool("get_orders")
def get_orders() -> list[Order]:
    """
    Fetch all active equity orders.

    Returns:
        List of Order objects representing all active orders.
    """
    return client.get_orders()


@mcp.tool("place_limit_order")
def place_limit_order(
    ticker: str,
    quantity: float,
    limit_price: float,
    time_validity: LimitRequestTimeValidityEnum = LimitRequestTimeValidityEnum.DAY,
) -> Order:
    """
    Place a limit order to buy or sell at a specified price or better.

    WARNING: Limit orders are only supported in the demo environment.
    Live environment only supports market orders.

    Args:
        ticker: Ticker symbol of the instrument (e.g., 'AAPL_US_EQ').
        quantity: Number of shares to trade. Positive for buy, negative for sell.
        limit_price: Maximum price for buy or minimum price for sell.
        time_validity: Order validity period (DAY or GOOD_TILL_CANCEL).

    Returns:
        Order object with details of the placed order.
    """
    limit_request = LimitRequest(
        ticker=ticker,
        quantity=quantity,
        limitPrice=limit_price,
        timeValidity=time_validity,
    )
    return client.place_limit_order(limit_request)


@mcp.tool("place_market_order")
def place_market_order(ticker: str, quantity: float) -> Order:
    """
    Place a market order to buy or sell at the current market price.

    Args:
        ticker: Ticker symbol of the instrument (e.g., 'AAPL_US_EQ').
        quantity: Number of shares to trade. Positive for buy, negative for sell.

    Returns:
        Order object with details of the placed order.
    """
    market_request = MarketRequest(ticker=ticker, quantity=quantity)
    return client.place_market_order(market_request)


@mcp.tool("place_stop_order")
def place_stop_order(
    ticker: str,
    quantity: float,
    stop_price: float,
    time_validity: StopRequestTimeValidityEnum = StopRequestTimeValidityEnum.DAY,
) -> Order:
    """
    Place a stop order that triggers when the market price reaches the stop price.

    WARNING: Stop orders are only supported in the demo environment.
    Live environment only supports market orders.

    Args:
        ticker: Ticker symbol of the instrument (e.g., 'AAPL_US_EQ').
        quantity: Number of shares to trade. Positive for buy, negative for sell.
        stop_price: Price that triggers the order execution.
        time_validity: Order validity period (DAY or GOOD_TILL_CANCEL).

    Returns:
        Order object with details of the placed order.
    """
    stop_request = StopRequest(
        ticker=ticker,
        quantity=quantity,
        stopPrice=stop_price,
        timeValidity=time_validity,
    )
    return client.place_stop_order(stop_request)


@mcp.tool("place_stop_limit_order")
def place_stop_limit_order(
    ticker: str,
    quantity: float,
    stop_price: float,
    limit_price: float,
    time_validity: StopLimitRequestTimeValidityEnum = StopLimitRequestTimeValidityEnum.DAY,
) -> Order:
    """
    Place a stop-limit order that triggers at the stop price with a limit.

    WARNING: Stop-limit orders are only supported in the demo environment.
    Live environment only supports market orders.

    Args:
        ticker: Ticker symbol of the instrument (e.g., 'AAPL_US_EQ').
        quantity: Number of shares to trade. Positive for buy, negative for sell.
        stop_price: Price that triggers the limit order.
        limit_price: Maximum/minimum price for execution after trigger.
        time_validity: Order validity period (DAY or GOOD_TILL_CANCEL).

    Returns:
        Order object with details of the placed order.
    """
    stop_limit_request = StopLimitRequest(
        ticker=ticker,
        quantity=quantity,
        stopPrice=stop_price,
        limitPrice=limit_price,
        timeValidity=time_validity,
    )
    return client.place_stop_limit_order(stop_limit_request)


@mcp.tool("cancel_order")
def cancel_order(order_id: int) -> None:
    """
    Cancel an existing order by its ID.

    Args:
        order_id: The unique identifier of the order to cancel.
    """
    client.cancel_order(order_id)


@mcp.tool("get_order")
def get_order(order_id: int) -> Order:
    """
    Fetch a specific order by its ID.

    Args:
        order_id: The unique identifier of the order.

    Returns:
        Order object with the order details.
    """
    return client.get_order_by_id(order_id)


# Account Data


@mcp.tool("get_account_info")
def get_account_info() -> Account:
    """
    Fetch account metadata including ID and currency.

    Returns:
        Account object with account metadata.
    """
    return client.get_account_info()


@mcp.tool("get_account_cash")
def get_account_cash() -> Cash:
    """
    Fetch account cash balance information.

    Returns:
        Cash object with balance details including free, invested, and total.
    """
    return client.get_account_cash()


# Personal Portfolio


@mcp.tool("get_positions")
def get_positions() -> list[Position]:
    """
    Fetch all open positions in the portfolio.

    Returns:
        List of Position objects representing all open positions.
    """
    return client.get_account_positions()


@mcp.tool("get_position")
def get_position(ticker: str) -> Position:
    """
    Search for a specific open position by ticker.

    Args:
        ticker: Ticker symbol of the instrument (e.g., 'AAPL_US_EQ').

    Returns:
        Position object with the position details.
    """
    return client.search_position_by_ticker(ticker)


# Historical items


@mcp.tool("get_order_history")
def get_order_history(
    cursor: int | None = None,
    ticker: str | None = None,
    limit: int = 8,
) -> list[HistoricalOrder]:
    """
    Fetch historical order data with optional pagination and filtering.

    Args:
        cursor: Pagination cursor for the next page of results.
        ticker: Optional ticker symbol to filter results.
        limit: Maximum number of items to return. Note: Trading212 has a
            server bug where limit > 8 causes 500 errors, so max is 8.

    Returns:
        List of HistoricalOrder objects.
    """
    return client.get_historical_order_data(cursor=cursor, ticker=ticker, limit=limit)


@mcp.tool("get_dividends")
def get_dividends(
    cursor: int | None = None,
    ticker: str | None = None,
    limit: int = 20,
) -> PaginatedResponseHistoryDividendItem:
    """
    Fetch historical dividend payments with optional pagination and filtering.

    Args:
        cursor: Pagination cursor for the next page of results.
        ticker: Optional ticker symbol to filter results.
        limit: Maximum number of items to return (max: 50, default: 20).

    Returns:
        PaginatedResponseHistoryDividendItem with dividend items and pagination info.
    """
    return client.get_dividends(cursor=cursor, ticker=ticker, limit=limit)


@mcp.tool("get_exports")
def get_exports() -> list[ReportResponse]:
    """
    Fetch information about all CSV account exports.

    Returns:
        List of ReportResponse objects with export details.
    """
    return client.get_reports()


@mcp.tool("create_export")
def create_export(
    include_dividends: bool = True,
    include_interest: bool = True,
    include_orders: bool = True,
    include_transactions: bool = True,
    time_from: str | None = None,
    time_to: str | None = None,
) -> EnqueuedReportResponse:
    """
    Request a CSV export of account history.

    Once the export is complete, it can be downloaded from the link in get_exports.

    Args:
        include_dividends: Whether to include dividend information.
        include_interest: Whether to include interest information.
        include_orders: Whether to include order history.
        include_transactions: Whether to include transaction history.
        time_from: Start time in ISO 8601 format (e.g., '2023-01-01T00:00:00Z').
        time_to: End time in ISO 8601 format (e.g., '2023-12-31T23:59:59Z').

    Returns:
        EnqueuedReportResponse with the report ID.
    """
    data_included = ReportDataIncluded(
        includeDividends=include_dividends,
        includeInterest=include_interest,
        includeOrders=include_orders,
        includeTransactions=include_transactions,
    )
    return client.request_export(
        data_included=data_included, time_from=time_from, time_to=time_to
    )


@mcp.tool("get_transactions")
def get_transactions(
    cursor: str | None = None,
    time_from: str | None = None,
    limit: int = 20,
) -> PaginatedResponseHistoryTransactionItem:
    """
    Fetch account transaction history (deposits, withdrawals, fees, transfers).

    Args:
        cursor: Pagination cursor for the next page of results.
        time_from: Retrieve transactions starting from this time (ISO 8601 format).
        limit: Maximum number of items to return (max: 50, default: 20).

    Returns:
        PaginatedResponseHistoryTransactionItem with transaction items and pagination.
    """
    return client.get_history_transactions(
        cursor=cursor, time_from=time_from, limit=limit
    )


# Cache Management Tools


@mcp.tool("sync_historical_data")
def sync_historical_data(
    tables: list[str] | None = None,
    force: bool = False,
) -> dict[str, dict[str, Any]]:
    """
    Manually sync historical data from Trading212 API to local cache.

    This tool syncs orders, dividends, and/or transactions from the API
    to a local SQLite database for faster access and offline analysis.
    Requires ENABLE_LOCAL_CACHE=true in environment.

    Args:
        tables: Which tables to sync. Options: "orders", "dividends",
                "transactions". If None, syncs all tables.
        force: If True, clears cache and does a full resync.

    Returns:
        Dictionary with sync results per table, including:
        - records_fetched: Number of records retrieved from API
        - records_added: Number of new records added to cache
        - total_records: Total records now in cache
        - last_sync: Timestamp of this sync
        - error: Error message if sync failed (optional)

    Example:
        >>> sync_historical_data()  # Sync all tables
        >>> sync_historical_data(tables=["orders"])  # Sync only orders
        >>> sync_historical_data(force=True)  # Force full resync
    """
    results = client.sync_historical_data(tables=tables, force=force)
    # Convert SyncResult dataclasses to dicts for JSON serialization
    return {
        table: {
            "table": result.table,
            "records_fetched": result.records_fetched,
            "records_added": result.records_added,
            "total_records": result.total_records,
            "last_sync": result.last_sync,
            "error": result.error,
        }
        for table, result in results.items()
    }


@mcp.tool("clear_cache")
def clear_cache(table: str | None = None) -> dict[str, int]:
    """
    Clear local cache for historical data.

    This tool deletes cached data from the local SQLite database.
    Requires ENABLE_LOCAL_CACHE=true in environment.

    Args:
        table: Specific table to clear ("orders", "dividends", "transactions").
               If None, clears entire cache including sync metadata.

    Returns:
        Dictionary with counts of deleted records per table.

    Example:
        >>> clear_cache()  # Clear all cached data
        >>> clear_cache(table="orders")  # Clear only cached orders
    """
    return client.clear_cache(table=table)


@mcp.tool("cache_stats")
def cache_stats() -> dict[str, Any]:
    """
    Get statistics about the local cache.

    This tool provides information about the current state of the
    local SQLite cache, including record counts and last sync times.

    Returns:
        Dictionary with cache statistics:
        - enabled: Whether caching is enabled
        - database_path: Path to the SQLite database file
        - database_size_bytes: Size of the database file in bytes
        - orders_count: Number of cached orders
        - dividends_count: Number of cached dividends
        - transactions_count: Number of cached transactions
        - last_orders_sync: Last sync timestamp for orders
        - last_dividends_sync: Last sync timestamp for dividends
        - last_transactions_sync: Last sync timestamp for transactions

    Example:
        >>> cache_stats()
        {
            "enabled": true,
            "database_path": "./data/trading212.db",
            "database_size_bytes": 524288,
            "orders_count": 150,
            "dividends_count": 42,
            "transactions_count": 89,
            "last_orders_sync": "2024-01-15T10:30:00",
            ...
        }
    """
    stats = client.get_cache_stats()
    return {
        "enabled": stats.enabled,
        "database_path": stats.database_path,
        "database_size_bytes": stats.database_size_bytes,
        "orders_count": stats.orders_count,
        "dividends_count": stats.dividends_count,
        "transactions_count": stats.transactions_count,
        "last_orders_sync": stats.last_orders_sync,
        "last_dividends_sync": stats.last_dividends_sync,
        "last_transactions_sync": stats.last_transactions_sync,
    }
