"""Trading212 API client.

This module provides the Trading212Client class for interacting with the
Trading212 API, including account management, order placement, and market data.
"""

import base64
import logging
import os
from typing import Any

import hishel
import httpx

from config import DATABASE_PATH, ENABLE_LOCAL_CACHE
from exceptions import (
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    RateLimitError,
    ServerError,
    TimeoutError,
    ValidationError,
)
from models import (
    Account,
    AccountBucketInstrumentsDetailedResponse,
    AccountBucketResultResponse,
    Cash,
    DuplicateBucketRequest,
    EnqueuedReportResponse,
    Environment,
    Exchange,
    HistoricalOrder,
    HistoryDividendItem,
    HistoryTransactionItem,
    LimitRequest,
    MarketRequest,
    Order,
    PaginatedResponseHistoryDividendItem,
    PaginatedResponseHistoryTransactionItem,
    PieRequest,
    Position,
    ReportDataIncluded,
    ReportResponse,
    StopLimitRequest,
    StopRequest,
    TradeableInstrument,
)
from utils.data_store import CacheStats, HistoricalDataStore, SyncResult
from utils.hishel_config import controller, storage
from utils.rate_limiter import RateLimiter
from utils.retry import with_retry

__all__ = ["Trading212Client"]

logger = logging.getLogger(__name__)


class Trading212Client:
    """Client for interacting with the Trading212 API.

    This client handles authentication, request caching, rate limiting,
    and provides methods for all Trading212 API endpoints.

    Attributes:
        client: The underlying HTTP client with caching support.
        environment: The Trading212 environment ('demo' or 'live').
    """

    def __init__(
        self,
        api_key: str | None = None,
        api_secret: str | None = None,
        environment: str | None = None,
        version: str = "v0",
    ) -> None:
        """
        Initialize the Trading212 client.

        Args:
            api_key: Trading212 API key. If not provided, reads from
                TRADING212_API_KEY environment variable.
            api_secret: Trading212 API secret. If not provided, reads from
                TRADING212_API_SECRET environment variable.
            environment: 'demo' or 'live'. If not provided, reads from
                ENVIRONMENT env var, defaults to 'demo'.
            version: API version. Defaults to 'v0'.

        Raises:
            ValueError: If API key or secret is not provided and not found
                in environment variables.
        """
        api_key = api_key or os.getenv("TRADING212_API_KEY")
        if not api_key:
            raise ValueError(
                "API key is required. Provide api_key parameter or set "
                "TRADING212_API_KEY environment variable."
            )

        api_secret = api_secret or os.getenv("TRADING212_API_SECRET")
        if not api_secret:
            raise ValueError(
                "API secret is required. Provide api_secret parameter or set "
                "TRADING212_API_SECRET environment variable."
            )

        self.environment = (
            environment or os.getenv("ENVIRONMENT") or Environment.DEMO.value
        )

        # Build Basic auth header
        credentials = f"{api_key}:{api_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        auth_header = f"Basic {encoded_credentials}"

        base_url = f"https://{self.environment}.trading212.com/api/{version}"
        headers = {
            "Authorization": auth_header,
            "Content-Type": "application/json",
        }
        self.client = hishel.CacheClient(
            base_url=base_url,
            storage=storage,
            controller=controller,
            headers=headers,
            timeout=httpx.Timeout(10.0, connect=5.0),  # 10s read, 5s connect
        )

        # Initialize rate limiter
        self._rate_limiter = RateLimiter()

        # Create a retry-wrapped request function
        self._request_with_retry = with_retry(
            max_retries=3,
            base_delay=1.0,
            max_delay=30.0,
        )(self._raw_request)

        # Initialize local data store if enabled
        self._data_store: HistoricalDataStore | None = None
        self._data_store_init_pending = ENABLE_LOCAL_CACHE

    def _raw_request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        """
        Execute the raw HTTP request.

        This method is wrapped with retry logic for transient errors
        (500, 502, 503, 504, 408, 429).

        Args:
            method: HTTP method (GET, POST, DELETE, etc.).
            url: API endpoint URL (relative to base_url).
            **kwargs: Additional arguments passed to httpx.request.

        Returns:
            The httpx.Response object.

        Raises:
            httpx.HTTPStatusError: If the response has an error status code.
        """
        response = self.client.request(method, url, **kwargs)
        response.raise_for_status()
        return response

    def _make_request(self, method: str, url: str, **kwargs: Any) -> Any:
        """
        Make an HTTP request to the Trading212 API.

        This method handles rate limiting, retries, and converts HTTP errors
        to custom exceptions.

        Args:
            method: HTTP method (GET, POST, DELETE, etc.).
            url: API endpoint URL (relative to base_url).
            **kwargs: Additional arguments passed to httpx.request.

        Returns:
            Parsed JSON response data.

        Raises:
            AuthenticationError: If the API credentials are invalid (401).
            AuthorizationError: If the API key lacks required permissions (403).
            NotFoundError: If the requested resource doesn't exist (404).
            RateLimitError: If the rate limit is exceeded (429).
            ValidationError: If the request is invalid (400).
            TimeoutError: If the request times out (408).
            ServerError: If the server returns an error (5xx).
        """
        # Wait if rate limited
        self._rate_limiter.wait_if_needed(url)

        try:
            response = self._request_with_retry(method, url, **kwargs)

            # Update rate limiter from response headers
            self._rate_limiter.update_from_headers(url, response.headers)

            # Handle empty responses (e.g., DELETE)
            if not response.content:
                return None

            return response.json()

        except httpx.HTTPStatusError as e:
            # Update rate limiter even on errors (for 429 headers)
            self._rate_limiter.update_from_headers(url, e.response.headers)
            self._handle_http_error(e)

    def _validate_order_type_for_environment(self, order_type: str) -> None:
        """
        Validate that the order type is supported in the current environment.

        The live Trading212 environment only supports market orders via API.
        Limit, stop, and stop-limit orders are only available in the demo
        environment.

        Args:
            order_type: The type of order being placed ('limit', 'stop', 'stop-limit').

        Raises:
            ValidationError: If the order type is not supported in the live
                environment.
        """
        if self.environment == "live" and order_type != "market":
            raise ValidationError(
                f"{order_type.title()} orders are not supported in the live "
                "environment. Only market orders are allowed for live trading."
            )

    def _handle_http_error(self, error: httpx.HTTPStatusError) -> None:
        """
        Handle HTTP errors and raise appropriate custom exceptions.

        Args:
            error: The HTTP status error to handle.

        Raises:
            AuthenticationError: For 401 errors.
            AuthorizationError: For 403 errors.
            NotFoundError: For 404 errors.
            RateLimitError: For 429 errors.
            ValidationError: For 400 errors.
            TimeoutError: For 408 errors.
            ServerError: For 5xx errors.
        """
        status_code = error.response.status_code
        response = error.response

        logger.warning(
            "HTTP error %d on %s %s",
            status_code,
            error.request.method,
            error.request.url,
        )

        if status_code == 400:
            # Try to parse error details from response
            try:
                error_data = response.json()
                code = error_data.get("code")
                clarification = error_data.get("clarification")
                raise ValidationError(
                    message=f"Validation error: {clarification or code}",
                    code=code,
                    clarification=clarification,
                )
            except Exception as e:
                raise ValidationError("Request validation failed") from e

        elif status_code == 401:
            raise AuthenticationError("Invalid API credentials")

        elif status_code == 403:
            raise AuthorizationError(
                f"Missing required permission for {error.request.url}"
            )

        elif status_code == 404:
            raise NotFoundError(f"Resource not found: {error.request.url}")

        elif status_code == 408:
            raise TimeoutError("Request timed out")

        elif status_code == 429:
            retry_after = response.headers.get("x-ratelimit-reset")
            raise RateLimitError(
                message="Rate limit exceeded",
                retry_after=float(retry_after) if retry_after else None,
            )

        elif status_code >= 500:
            raise ServerError(f"Server error: {status_code}", status_code=status_code)

        else:
            # Re-raise for any other status codes
            raise

    # ---- Account Methods ----

    def get_account_info(self) -> Account:
        """
        Fetch account metadata.

        Returns:
            Account object with ID and currency code.
        """
        data = self._make_request("GET", "/equity/account/info")
        return Account.model_validate(data)

    def get_account_cash(self) -> Cash:
        """
        Fetch account cash balance.

        Returns:
            Cash object with balance details.
        """
        data = self._make_request("GET", "/equity/account/cash")
        return Cash.model_validate(data)

    # ---- Portfolio Methods ----

    def get_account_positions(self) -> list[Position]:
        """
        Fetch all open positions.

        Returns:
            List of Position objects.
        """
        data = self._make_request("GET", "/equity/portfolio")
        return [Position.model_validate(pos) for pos in data]

    def get_account_position_by_ticker(self, ticker: str) -> Position:
        """
        Fetch an open position by ticker (deprecated endpoint).

        Args:
            ticker: Ticker symbol of the instrument.

        Returns:
            Position object for the specified ticker.
        """
        data = self._make_request("GET", f"/equity/portfolio/{ticker}")
        return Position.model_validate(data)

    def search_position_by_ticker(self, ticker: str) -> Position:
        """
        Search for an open position by ticker using POST.

        Args:
            ticker: Ticker symbol of the instrument.

        Returns:
            Position object for the specified ticker.
        """
        data = self._make_request(
            "POST", "/equity/portfolio/ticker", json={"ticker": ticker}
        )
        return Position.model_validate(data)

    # ---- Order Methods ----

    def get_orders(self) -> list[Order]:
        """
        Fetch all current orders.

        Returns:
            List of Order objects.
        """
        data = self._make_request("GET", "/equity/orders")
        return [Order.model_validate(order) for order in data]

    def get_order_by_id(self, order_id: int) -> Order:
        """
        Fetch a specific order by ID.

        Args:
            order_id: Unique identifier of the order.

        Returns:
            Order object with order details.
        """
        data = self._make_request("GET", f"/equity/orders/{order_id}")
        return Order.model_validate(data)

    def place_market_order(self, order_data: MarketRequest) -> Order:
        """
        Place a market order.

        Args:
            order_data: MarketRequest with ticker and quantity.

        Returns:
            Order object with placed order details.
        """
        data = self._make_request(
            "POST", "/equity/orders/market", json=order_data.model_dump(mode="json")
        )
        return Order.model_validate(data)

    def place_limit_order(self, order_data: LimitRequest) -> Order:
        """
        Place a limit order.

        Note: Limit orders are only supported in the demo environment.
        Attempting to place a limit order in the live environment will raise
        a ValidationError.

        Args:
            order_data: LimitRequest with ticker, quantity, limit price, and validity.

        Returns:
            Order object with placed order details.

        Raises:
            ValidationError: If called in the live environment.
        """
        self._validate_order_type_for_environment("limit")
        data = self._make_request(
            "POST", "/equity/orders/limit", json=order_data.model_dump(mode="json")
        )
        return Order.model_validate(data)

    def place_stop_order(self, order_data: StopRequest) -> Order:
        """
        Place a stop order.

        Note: Stop orders are only supported in the demo environment.
        Attempting to place a stop order in the live environment will raise
        a ValidationError.

        Args:
            order_data: StopRequest with ticker, quantity, stop price, and validity.

        Returns:
            Order object with placed order details.

        Raises:
            ValidationError: If called in the live environment.
        """
        self._validate_order_type_for_environment("stop")
        data = self._make_request(
            "POST", "/equity/orders/stop", json=order_data.model_dump(mode="json")
        )
        return Order.model_validate(data)

    def place_stop_limit_order(self, order_data: StopLimitRequest) -> Order:
        """
        Place a stop-limit order.

        Note: Stop-limit orders are only supported in the demo environment.
        Attempting to place a stop-limit order in the live environment will
        raise a ValidationError.

        Args:
            order_data: StopLimitRequest with all order parameters.

        Returns:
            Order object with placed order details.

        Raises:
            ValidationError: If called in the live environment.
        """
        self._validate_order_type_for_environment("stop-limit")
        data = self._make_request(
            "POST", "/equity/orders/stop_limit", json=order_data.model_dump(mode="json")
        )
        return Order.model_validate(data)

    def cancel_order(self, order_id: int) -> None:
        """
        Cancel an existing order.

        Args:
            order_id: Unique identifier of the order to cancel.
        """
        self._make_request("DELETE", f"/equity/orders/{order_id}")

    # ---- Pie Methods ----

    def get_pies(self) -> list[AccountBucketResultResponse]:
        """
        Fetch all pies.

        Returns:
            List of AccountBucketResultResponse objects.
        """
        data = self._make_request("GET", "/equity/pies")
        return [AccountBucketResultResponse.model_validate(pie) for pie in data]

    def get_pie_by_id(self, pie_id: int) -> AccountBucketInstrumentsDetailedResponse:
        """
        Fetch a specific pie by ID.

        Args:
            pie_id: Unique identifier of the pie.

        Returns:
            AccountBucketInstrumentsDetailedResponse with pie details.
        """
        data = self._make_request("GET", f"/equity/pies/{pie_id}")
        return AccountBucketInstrumentsDetailedResponse.model_validate(data)

    def create_pie(
        self, pie_data: PieRequest
    ) -> AccountBucketInstrumentsDetailedResponse:
        """
        Create a new pie.

        Args:
            pie_data: PieRequest with pie configuration.

        Returns:
            AccountBucketInstrumentsDetailedResponse with created pie details.
        """
        data = self._make_request(
            "POST", "/equity/pies", json=pie_data.model_dump(mode="json")
        )
        return AccountBucketInstrumentsDetailedResponse.model_validate(data)

    def update_pie(
        self, pie_id: int, pie_data: PieRequest
    ) -> AccountBucketInstrumentsDetailedResponse:
        """
        Update a specific pie by ID.

        Args:
            pie_id: Unique identifier of the pie to update.
            pie_data: PieRequest with updated configuration.

        Returns:
            AccountBucketInstrumentsDetailedResponse with updated pie details.
        """
        payload = {
            k: v for k, v in pie_data.model_dump(mode="json").items() if v is not None
        }
        data = self._make_request("POST", f"/equity/pies/{pie_id}", json=payload)
        return AccountBucketInstrumentsDetailedResponse.model_validate(data)

    def duplicate_pie(
        self, pie_id: int, duplicate_request: DuplicateBucketRequest
    ) -> AccountBucketInstrumentsDetailedResponse:
        """
        Duplicate a pie.

        Args:
            pie_id: Unique identifier of the pie to duplicate.
            duplicate_request: DuplicateBucketRequest with optional new name/icon.

        Returns:
            AccountBucketInstrumentsDetailedResponse with duplicated pie details.
        """
        data = self._make_request(
            "POST",
            f"/equity/pies/{pie_id}/duplicate",
            json=duplicate_request.model_dump(mode="json"),
        )
        return AccountBucketInstrumentsDetailedResponse.model_validate(data)

    def delete_pie(self, pie_id: int) -> None:
        """
        Delete a pie.

        Args:
            pie_id: Unique identifier of the pie to delete.
        """
        self._make_request("DELETE", f"/equity/pies/{pie_id}")

    # ---- Historical Data Methods ----

    def get_historical_order_data(
        self,
        cursor: int | None = None,
        ticker: str | None = None,
        limit: int = 8,
    ) -> list[HistoricalOrder]:
        """
        Fetch historical order data with pagination.

        Args:
            cursor: Pagination cursor for the next page.
            ticker: Optional ticker to filter results.
            limit: Maximum items to return. Note: Trading212 has a server bug
                where limit > 8 causes 500 errors, so default is 8.

        Returns:
            List of HistoricalOrder objects.
        """
        # Trading212 bug: limit > 8 causes 500 errors
        params: dict[str, Any] = {"limit": min(limit, 8)}
        if cursor is not None:
            params["cursor"] = cursor
        if ticker is not None:
            params["ticker"] = ticker

        data = self._make_request("GET", "/equity/history/orders", params=params)
        return [HistoricalOrder.model_validate(order) for order in data["items"]]

    def get_dividends(
        self,
        cursor: int | None = None,
        ticker: str | None = None,
        limit: int = 20,
    ) -> PaginatedResponseHistoryDividendItem:
        """
        Fetch dividend history with optional pagination and filtering.

        Args:
            cursor: Pagination cursor for the next page.
            ticker: Optional ticker to filter results.
            limit: Maximum items to return (max: 50).

        Returns:
            PaginatedResponseHistoryDividendItem with dividend items.
        """
        params: dict[str, Any] = {}
        if cursor is not None:
            params["cursor"] = cursor
        if ticker is not None:
            params["ticker"] = ticker
        if limit is not None:
            params["limit"] = min(50, max(1, limit))

        data = self._make_request("GET", "/history/dividends", params=params)
        return PaginatedResponseHistoryDividendItem.model_validate(data)

    def get_history_transactions(
        self,
        cursor: str | None = None,
        time_from: str | None = None,
        limit: int = 20,
    ) -> PaginatedResponseHistoryTransactionItem:
        """
        Fetch transaction history (deposits, withdrawals, fees, transfers).

        Args:
            cursor: Pagination cursor for the next page.
            time_from: Retrieve transactions starting from this time (ISO 8601).
            limit: Maximum items to return (max: 50).

        Returns:
            PaginatedResponseHistoryTransactionItem with transaction items.
        """
        params: dict[str, Any] = {"limit": limit}
        if cursor is not None:
            params["cursor"] = cursor
        if time_from is not None:
            params["time"] = time_from

        data = self._make_request("GET", "/history/transactions", params=params)
        return PaginatedResponseHistoryTransactionItem.model_validate(data)

    # ---- Metadata Methods ----

    def get_instruments(self) -> list[TradeableInstrument]:
        """
        Fetch all tradeable instruments.

        Returns:
            List of TradeableInstrument objects.
        """
        data = self._make_request("GET", "/equity/metadata/instruments")
        return [TradeableInstrument.model_validate(inst) for inst in data]

    def get_exchanges(self) -> list[Exchange]:
        """
        Fetch all exchanges and their working schedules.

        Returns:
            List of Exchange objects.
        """
        data = self._make_request("GET", "/equity/metadata/exchanges")
        return [Exchange.model_validate(exchange) for exchange in data]

    # ---- Pagination Helper Methods ----

    def get_all_dividends(
        self,
        ticker: str | None = None,
    ) -> list[HistoryDividendItem]:
        """
        Fetch ALL dividends with automatic pagination.

        This method fetches all pages of dividend history.

        Args:
            ticker: Optional ticker to filter results.

        Returns:
            Complete list of HistoryDividendItem objects.
        """
        all_items: list[HistoryDividendItem] = []
        cursor: int | None = None

        while True:
            response = self.get_dividends(cursor=cursor, ticker=ticker, limit=50)
            all_items.extend(response.items)

            if not response.nextPagePath:
                break

            # Extract cursor from nextPagePath
            extracted = self._extract_cursor_from_path(response.nextPagePath)
            if extracted is None or isinstance(extracted, str):
                break
            cursor = extracted

        return all_items

    def get_all_transactions(
        self,
        time_from: str | None = None,
    ) -> list[HistoryTransactionItem]:
        """
        Fetch ALL transactions with automatic pagination.

        This method fetches all pages of transaction history.

        Args:
            time_from: Retrieve transactions starting from this time (ISO 8601).

        Returns:
            Complete list of HistoryTransactionItem objects.
        """
        all_items: list[HistoryTransactionItem] = []
        cursor: str | None = None

        while True:
            response = self.get_history_transactions(
                cursor=cursor, time_from=time_from, limit=50
            )
            all_items.extend(response.items)

            if not response.nextPagePath:
                break

            # Extract cursor from nextPagePath (string cursor for transactions)
            extracted = self._extract_cursor_from_path(
                response.nextPagePath, as_string=True
            )
            if extracted is None or isinstance(extracted, int):
                break
            cursor = extracted

        return all_items

    def _extract_cursor_from_path(
        self, path: str, as_string: bool = False
    ) -> int | str | None:
        """
        Extract the cursor value from a nextPagePath.

        Args:
            path: The nextPagePath value from a paginated response.
            as_string: If True, return cursor as string instead of int.

        Returns:
            The cursor value, or None if not found.
        """
        try:
            # Parse cursor from path like "/history/dividends?cursor=12345"
            if "cursor=" in path:
                cursor_str = path.split("cursor=")[1].split("&")[0]
                if as_string:
                    return cursor_str
                return int(cursor_str)
            return None
        except (ValueError, IndexError) as e:
            logger.warning("Failed to extract cursor from path %s: %s", path, e)
            return None

    # ---- Report Methods ----

    def get_reports(self) -> list[ReportResponse]:
        """
        Get account export reports.

        Returns:
            List of ReportResponse objects.
        """
        data = self._make_request("GET", "/history/exports")
        return [ReportResponse.model_validate(report) for report in data]

    def request_export(
        self,
        data_included: ReportDataIncluded | None = None,
        time_from: str | None = None,
        time_to: str | None = None,
    ) -> EnqueuedReportResponse:
        """
        Request a CSV export of account history.

        Args:
            data_included: What data to include in the export.
            time_from: Start time in ISO 8601 format.
            time_to: End time in ISO 8601 format.

        Returns:
            EnqueuedReportResponse with the report ID.
        """
        payload: dict[str, Any] = {}
        data_included = data_included or ReportDataIncluded()
        payload["dataIncluded"] = data_included.model_dump(mode="json")
        if time_from:
            payload["timeFrom"] = time_from
        if time_to:
            payload["timeTo"] = time_to

        data = self._make_request("POST", "/history/exports", json=payload)
        return EnqueuedReportResponse.model_validate(data)

    # ---- Local Cache Methods ----

    def _get_data_store(self) -> HistoricalDataStore | None:
        """
        Get or initialize the data store (lazy initialization).

        The data store requires the account ID, which we only get after
        making an API call. This method lazily initializes it on first use.

        Returns:
            HistoricalDataStore if caching is enabled, None otherwise.
        """
        if self._data_store_init_pending and self._data_store is None:
            try:
                account = self.get_account_info()
                self._data_store = HistoricalDataStore(
                    db_path=DATABASE_PATH,
                    account_id=account.id,
                    enabled=True,
                )
                logger.info(
                    "Local data store initialized for account %d at %s",
                    account.id,
                    DATABASE_PATH,
                )
            except Exception as e:
                logger.warning("Failed to initialize data store: %s", e)
                self._data_store_init_pending = False
        return self._data_store

    @property
    def cache_enabled(self) -> bool:
        """Check if local caching is enabled."""
        return ENABLE_LOCAL_CACHE and self._get_data_store() is not None

    def sync_historical_data(
        self,
        tables: list[str] | None = None,
        force: bool = False,
    ) -> dict[str, SyncResult]:
        """
        Sync historical data from API to local cache.

        Args:
            tables: Which tables to sync ("orders", "dividends", "transactions").
                    If None, syncs all tables.
            force: If True, clears cache before syncing.

        Returns:
            Dictionary mapping table names to their SyncResult.

        Raises:
            ValueError: If caching is not enabled.
        """
        data_store = self._get_data_store()
        if not data_store:
            raise ValueError(
                "Local caching is not enabled. Set ENABLE_LOCAL_CACHE=true "
                "in your environment to enable caching."
            )

        if force:
            if tables:
                for table in tables:
                    data_store.clear_cache(table)
            else:
                data_store.clear_cache()

        valid_tables = {"orders", "dividends", "transactions"}
        tables_to_sync = tables or list(valid_tables)

        # Validate table names
        for table in tables_to_sync:
            if table not in valid_tables:
                raise ValueError(
                    f"Invalid table name: {table}. "
                    f"Valid tables are: {', '.join(valid_tables)}"
                )

        results: dict[str, SyncResult] = {}
        for table in tables_to_sync:
            if table == "orders":
                results["orders"] = data_store.sync_orders(self)
            elif table == "dividends":
                results["dividends"] = data_store.sync_dividends(self)
            elif table == "transactions":
                results["transactions"] = data_store.sync_transactions(self)

        return results

    def clear_cache(self, table: str | None = None) -> dict[str, int]:
        """
        Clear local cache.

        Args:
            table: Specific table to clear. If None, clears all tables.

        Returns:
            Dictionary with counts of deleted records per table.

        Raises:
            ValueError: If caching is not enabled.
        """
        data_store = self._get_data_store()
        if not data_store:
            raise ValueError(
                "Local caching is not enabled. Set ENABLE_LOCAL_CACHE=true "
                "in your environment to enable caching."
            )

        return data_store.clear_cache(table)

    def get_cache_stats(self) -> CacheStats:
        """
        Get statistics about the local cache.

        Returns:
            CacheStats object with record counts and sync times.
        """
        data_store = self._get_data_store()
        if not data_store:
            return CacheStats(
                enabled=False,
                database_path=DATABASE_PATH,
                database_size_bytes=0,
                orders_count=0,
                dividends_count=0,
                transactions_count=0,
                last_orders_sync=None,
                last_dividends_sync=None,
                last_transactions_sync=None,
            )

        return data_store.get_stats()

    def get_cached_orders(
        self,
        ticker: str | None = None,
        sync_first: bool = True,
    ) -> list[HistoricalOrder]:
        """
        Get historical orders from local cache.

        Args:
            ticker: Optional ticker to filter by.
            sync_first: If True, sync from API before returning cached data.

        Returns:
            List of HistoricalOrder objects from cache.
        """
        data_store = self._get_data_store()
        if not data_store:
            # Fall back to API
            return self.get_historical_order_data(ticker=ticker)

        if sync_first:
            data_store.sync_orders(self)

        return data_store.get_orders(ticker=ticker)

    def get_cached_dividends(
        self,
        ticker: str | None = None,
        sync_first: bool = True,
    ) -> list[HistoryDividendItem]:
        """
        Get dividends from local cache.

        Args:
            ticker: Optional ticker to filter by.
            sync_first: If True, sync from API before returning cached data.

        Returns:
            List of HistoryDividendItem objects from cache.
        """
        data_store = self._get_data_store()
        if not data_store:
            # Fall back to API
            return self.get_all_dividends(ticker=ticker)

        if sync_first:
            data_store.sync_dividends(self)

        return data_store.get_dividends(ticker=ticker)

    def get_cached_transactions(
        self,
        time_from: str | None = None,
        sync_first: bool = True,
    ) -> list[HistoryTransactionItem]:
        """
        Get transactions from local cache.

        Args:
            time_from: Optional start time filter (ISO 8601).
            sync_first: If True, sync from API before returning cached data.

        Returns:
            List of HistoryTransactionItem objects from cache.
        """
        data_store = self._get_data_store()
        if not data_store:
            # Fall back to API
            return self.get_all_transactions(time_from=time_from)

        if sync_first:
            data_store.sync_transactions(self)

        return data_store.get_transactions(time_from=time_from)
