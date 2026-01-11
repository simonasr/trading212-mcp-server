"""Tests for the Trading212 API client.

This module contains unit tests for the Trading212Client class, including
authentication, request handling, and API method tests.
"""

import base64
import sys
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import httpx
import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

if TYPE_CHECKING:
    from pytest_mock.plugin import MockerFixture


class TestClientAuthentication:
    """Tests for client authentication."""

    def test_client_uses_basic_auth(
        self,
        api_key: str,
        api_secret: str,
    ) -> None:
        """Client should use Basic auth with base64-encoded key:secret."""
        from utils.client import Trading212Client

        # Expected auth header
        credentials = f"{api_key}:{api_secret}"
        expected_auth = f"Basic {base64.b64encode(credentials.encode()).decode()}"

        # Create client
        client = Trading212Client(
            api_key=api_key,
            api_secret=api_secret,
            environment="demo",
        )

        # Verify the auth header is set correctly in the client
        assert client.client.headers.get("Authorization") == expected_auth

    def test_client_raises_on_missing_api_key(self) -> None:
        """Client should raise ValueError when API key is missing."""
        from utils.client import Trading212Client

        with pytest.raises(ValueError, match="API key is required"):
            Trading212Client(api_key=None, api_secret="secret")

    def test_client_raises_on_missing_api_secret(self, api_key: str) -> None:
        """Client should raise ValueError when API secret is missing."""
        from utils.client import Trading212Client

        with pytest.raises(ValueError, match="API secret is required"):
            Trading212Client(api_key=api_key, api_secret=None)

    def test_client_reads_credentials_from_env(
        self,
        monkeypatch: pytest.MonkeyPatch,
        api_key: str,
        api_secret: str,
    ) -> None:
        """Client should read credentials from environment variables."""
        from utils.client import Trading212Client

        # Set environment variables
        monkeypatch.setenv("TRADING212_API_KEY", api_key)
        monkeypatch.setenv("TRADING212_API_SECRET", api_secret)

        # Create client without explicit credentials
        client = Trading212Client()

        # Verify credentials were read from env
        credentials = f"{api_key}:{api_secret}"
        expected_auth = f"Basic {base64.b64encode(credentials.encode()).decode()}"
        assert client.client.headers.get("Authorization") == expected_auth

    def test_client_uses_demo_environment_by_default(
        self,
        api_key: str,
        api_secret: str,
    ) -> None:
        """Client should use demo environment by default."""
        from utils.client import Trading212Client

        client = Trading212Client(api_key=api_key, api_secret=api_secret)

        assert client.environment == "demo"
        assert "demo.trading212.com" in str(client.client.base_url)

    def test_client_uses_live_environment_when_specified(
        self,
        api_key: str,
        api_secret: str,
    ) -> None:
        """Client should use live environment when specified."""
        from utils.client import Trading212Client

        client = Trading212Client(
            api_key=api_key,
            api_secret=api_secret,
            environment="live",
        )

        assert client.environment == "live"
        assert "live.trading212.com" in str(client.client.base_url)


class TestClientAccountMethods:
    """Tests for account-related client methods."""

    def test_get_account_info(
        self,
        mocker: "MockerFixture",
        api_key: str,
        api_secret: str,
        sample_account_response: dict,
    ) -> None:
        """Should fetch and parse account info correctly."""
        from utils.client import Trading212Client

        # Create client
        client = Trading212Client(api_key=api_key, api_secret=api_secret)

        # Mock the request method
        mock_response = MagicMock()
        mock_response.json.return_value = sample_account_response
        mock_response.content = b'{"data": "test"}'
        mocker.patch.object(client.client, "request", return_value=mock_response)

        result = client.get_account_info()

        assert result.currencyCode == "USD"
        assert result.id == 12345678

    def test_get_account_cash(
        self,
        mocker: "MockerFixture",
        api_key: str,
        api_secret: str,
        sample_cash_response: dict,
    ) -> None:
        """Should fetch and parse account cash correctly."""
        from utils.client import Trading212Client

        client = Trading212Client(api_key=api_key, api_secret=api_secret)

        mock_response = MagicMock()
        mock_response.json.return_value = sample_cash_response
        mock_response.content = b'{"data": "test"}'
        mocker.patch.object(client.client, "request", return_value=mock_response)

        result = client.get_account_cash()

        assert result.free == 1000.50
        assert result.total == 6150.75


class TestClientPortfolioMethods:
    """Tests for portfolio-related client methods."""

    def test_get_account_positions(
        self,
        mocker: "MockerFixture",
        api_key: str,
        api_secret: str,
        sample_position_response: dict,
    ) -> None:
        """Should fetch and parse positions correctly."""
        from utils.client import Trading212Client

        client = Trading212Client(api_key=api_key, api_secret=api_secret)

        mock_response = MagicMock()
        mock_response.json.return_value = [sample_position_response]
        mock_response.content = b'{"data": "test"}'
        mocker.patch.object(client.client, "request", return_value=mock_response)

        result = client.get_account_positions()

        assert len(result) == 1
        assert result[0].ticker == "AAPL_US_EQ"
        assert result[0].quantity == 10.0


class TestClientOrderMethods:
    """Tests for order-related client methods."""

    def test_get_orders(
        self,
        mocker: "MockerFixture",
        api_key: str,
        api_secret: str,
        sample_order_response: dict,
    ) -> None:
        """Should fetch and parse orders correctly."""
        from utils.client import Trading212Client

        client = Trading212Client(api_key=api_key, api_secret=api_secret)

        mock_response = MagicMock()
        mock_response.json.return_value = [sample_order_response]
        mock_response.content = b'{"data": "test"}'
        mocker.patch.object(client.client, "request", return_value=mock_response)

        result = client.get_orders()

        assert len(result) == 1
        assert result[0].ticker == "AAPL_US_EQ"
        assert result[0].type.value == "LIMIT"

    def test_place_market_order(
        self,
        mocker: "MockerFixture",
        api_key: str,
        api_secret: str,
    ) -> None:
        """Should place market order correctly."""
        from models import MarketRequest
        from utils.client import Trading212Client

        order_response = {
            "id": 123456,
            "ticker": "AAPL_US_EQ",
            "quantity": 5.0,
            "type": "MARKET",
            "status": "NEW",
        }

        client = Trading212Client(api_key=api_key, api_secret=api_secret)

        mock_response = MagicMock()
        mock_response.json.return_value = order_response
        mock_response.content = b'{"data": "test"}'
        request_mock = mocker.patch.object(
            client.client, "request", return_value=mock_response
        )

        order_data = MarketRequest(ticker="AAPL_US_EQ", quantity=5.0)
        result = client.place_market_order(order_data)

        assert result.id == 123456
        assert result.ticker == "AAPL_US_EQ"

        # Verify the request was made with correct method and path
        request_mock.assert_called_once()
        call_args = request_mock.call_args
        assert call_args[0][0] == "POST"
        assert call_args[0][1] == "/equity/orders/market"


class TestClientMetadataMethods:
    """Tests for metadata-related client methods."""

    def test_get_instruments(
        self,
        mocker: "MockerFixture",
        api_key: str,
        api_secret: str,
        sample_instrument_response: dict,
    ) -> None:
        """Should fetch and parse instruments correctly."""
        from utils.client import Trading212Client

        client = Trading212Client(api_key=api_key, api_secret=api_secret)

        mock_response = MagicMock()
        mock_response.json.return_value = [sample_instrument_response]
        mock_response.content = b'{"data": "test"}'
        mocker.patch.object(client.client, "request", return_value=mock_response)

        result = client.get_instruments()

        assert len(result) == 1
        assert result[0].ticker == "AAPL_US_EQ"
        assert result[0].name == "Apple Inc"

    def test_get_exchanges(
        self,
        mocker: "MockerFixture",
        api_key: str,
        api_secret: str,
        sample_exchange_response: dict,
    ) -> None:
        """Should fetch and parse exchanges correctly."""
        from utils.client import Trading212Client

        client = Trading212Client(api_key=api_key, api_secret=api_secret)

        mock_response = MagicMock()
        mock_response.json.return_value = [sample_exchange_response]
        mock_response.content = b'{"data": "test"}'
        mocker.patch.object(client.client, "request", return_value=mock_response)

        result = client.get_exchanges()

        assert len(result) == 1
        assert result[0].name == "NASDAQ"


class TestClientHistoricalMethods:
    """Tests for historical data client methods."""

    def test_get_dividends(
        self,
        mocker: "MockerFixture",
        api_key: str,
        api_secret: str,
        sample_dividend_response: dict,
    ) -> None:
        """Should fetch and parse dividends correctly."""
        from utils.client import Trading212Client

        client = Trading212Client(api_key=api_key, api_secret=api_secret)

        mock_response = MagicMock()
        mock_response.json.return_value = sample_dividend_response
        mock_response.content = b'{"data": "test"}'
        mock_response.headers = {}
        mocker.patch.object(client.client, "request", return_value=mock_response)

        result = client.get_dividends()

        assert len(result.items) == 1
        assert result.items[0].ticker == "AAPL_US_EQ"
        assert result.items[0].amount == 2.50


class TestClientErrorHandling:
    """Tests for client error handling."""

    def test_raises_authentication_error_on_401(
        self,
        mocker: "MockerFixture",
        api_key: str,
        api_secret: str,
    ) -> None:
        """Should raise AuthenticationError on 401 response."""
        from exceptions import AuthenticationError
        from utils.client import Trading212Client

        client = Trading212Client(api_key=api_key, api_secret=api_secret)

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Unauthorized",
            request=httpx.Request("GET", "http://test"),
            response=mock_response,
        )
        mocker.patch.object(client.client, "request", return_value=mock_response)

        with pytest.raises(AuthenticationError):
            client.get_account_info()

    def test_raises_authorization_error_on_403(
        self,
        mocker: "MockerFixture",
        api_key: str,
        api_secret: str,
    ) -> None:
        """Should raise AuthorizationError on 403 response."""
        from exceptions import AuthorizationError
        from utils.client import Trading212Client

        client = Trading212Client(api_key=api_key, api_secret=api_secret)

        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Forbidden",
            request=httpx.Request("GET", "http://test"),
            response=mock_response,
        )
        mocker.patch.object(client.client, "request", return_value=mock_response)

        with pytest.raises(AuthorizationError):
            client.get_account_info()

    def test_raises_not_found_error_on_404(
        self,
        mocker: "MockerFixture",
        api_key: str,
        api_secret: str,
    ) -> None:
        """Should raise NotFoundError on 404 response."""
        from exceptions import NotFoundError
        from utils.client import Trading212Client

        client = Trading212Client(api_key=api_key, api_secret=api_secret)

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found",
            request=httpx.Request("GET", "http://test"),
            response=mock_response,
        )
        mocker.patch.object(client.client, "request", return_value=mock_response)

        with pytest.raises(NotFoundError):
            client.get_order_by_id(999999)

    def test_raises_rate_limit_error_on_429(
        self,
        mocker: "MockerFixture",
        api_key: str,
        api_secret: str,
    ) -> None:
        """Should raise RateLimitError on 429 response."""
        from exceptions import RateLimitError
        from utils.client import Trading212Client

        client = Trading212Client(api_key=api_key, api_secret=api_secret)

        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {"x-ratelimit-reset": "1706000000"}
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Rate Limited",
            request=httpx.Request("GET", "http://test"),
            response=mock_response,
        )
        mocker.patch.object(client.client, "request", return_value=mock_response)

        with pytest.raises(RateLimitError):
            client.get_account_info()

    def test_raises_validation_error_on_400(
        self,
        mocker: "MockerFixture",
        api_key: str,
        api_secret: str,
    ) -> None:
        """Should raise ValidationError on 400 response."""
        from exceptions import ValidationError
        from utils.client import Trading212Client

        client = Trading212Client(api_key=api_key, api_secret=api_secret)

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "code": "InsufficientResources",
            "clarification": "Not enough funds",
        }
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Bad Request",
            request=httpx.Request("POST", "http://test"),
            response=mock_response,
        )
        mocker.patch.object(client.client, "request", return_value=mock_response)

        from models import MarketRequest

        with pytest.raises(ValidationError):
            client.place_market_order(MarketRequest(ticker="AAPL_US_EQ", quantity=100))

    def test_handles_empty_response_body(
        self,
        mocker: "MockerFixture",
        api_key: str,
        api_secret: str,
    ) -> None:
        """Should handle empty response body (e.g., DELETE)."""
        from utils.client import Trading212Client

        client = Trading212Client(api_key=api_key, api_secret=api_secret)

        mock_response = MagicMock()
        mock_response.content = b""
        mock_response.headers = {}
        mocker.patch.object(client.client, "request", return_value=mock_response)

        # Should not raise an error
        result = client.cancel_order(123)
        assert result is None

    def test_updates_rate_limiter_from_response_headers(
        self,
        mocker: "MockerFixture",
        api_key: str,
        api_secret: str,
        sample_account_response: dict,
    ) -> None:
        """Should update rate limiter from response headers."""
        from utils.client import Trading212Client

        client = Trading212Client(api_key=api_key, api_secret=api_secret)

        mock_response = MagicMock()
        mock_response.json.return_value = sample_account_response
        mock_response.content = b'{"data": "test"}'
        mock_response.headers = {
            "x-ratelimit-limit": "1",
            "x-ratelimit-remaining": "0",
            "x-ratelimit-reset": "1706000000",
        }
        mocker.patch.object(client.client, "request", return_value=mock_response)

        client.get_account_info()

        # Verify the rate limiter was updated
        assert "/equity/account/info" in client._rate_limiter._endpoints


class TestClientPagination:
    """Tests for pagination helper methods."""

    def test_get_all_dividends_fetches_all_pages(
        self,
        mocker: "MockerFixture",
        api_key: str,
        api_secret: str,
    ) -> None:
        """Should fetch all pages of dividends."""
        from utils.client import Trading212Client

        client = Trading212Client(api_key=api_key, api_secret=api_secret)

        # First page
        page1_response = MagicMock()
        page1_response.json.return_value = {
            "items": [
                {"ticker": "AAPL_US_EQ", "amount": 1.0},
                {"ticker": "MSFT_US_EQ", "amount": 2.0},
            ],
            "nextPagePath": "/history/dividends?cursor=12345",
        }
        page1_response.content = b'{"data": "test"}'
        page1_response.headers = {}

        # Second page
        page2_response = MagicMock()
        page2_response.json.return_value = {
            "items": [
                {"ticker": "GOOGL_US_EQ", "amount": 3.0},
            ],
            "nextPagePath": None,
        }
        page2_response.content = b'{"data": "test"}'
        page2_response.headers = {}

        # Return different responses for each call
        mocker.patch.object(
            client.client,
            "request",
            side_effect=[page1_response, page2_response],
        )

        result = client.get_all_dividends()

        assert len(result) == 3
        assert result[0].ticker == "AAPL_US_EQ"
        assert result[1].ticker == "MSFT_US_EQ"
        assert result[2].ticker == "GOOGL_US_EQ"

    def test_get_all_dividends_handles_single_page(
        self,
        mocker: "MockerFixture",
        api_key: str,
        api_secret: str,
    ) -> None:
        """Should handle single page response."""
        from utils.client import Trading212Client

        client = Trading212Client(api_key=api_key, api_secret=api_secret)

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "items": [
                {"ticker": "AAPL_US_EQ", "amount": 1.0},
            ],
            "nextPagePath": None,
        }
        mock_response.content = b'{"data": "test"}'
        mock_response.headers = {}

        mocker.patch.object(client.client, "request", return_value=mock_response)

        result = client.get_all_dividends()

        assert len(result) == 1
        assert result[0].ticker == "AAPL_US_EQ"

    def test_get_all_dividends_handles_empty_response(
        self,
        mocker: "MockerFixture",
        api_key: str,
        api_secret: str,
    ) -> None:
        """Should handle empty response."""
        from utils.client import Trading212Client

        client = Trading212Client(api_key=api_key, api_secret=api_secret)

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "items": [],
            "nextPagePath": None,
        }
        mock_response.content = b'{"data": "test"}'
        mock_response.headers = {}

        mocker.patch.object(client.client, "request", return_value=mock_response)

        result = client.get_all_dividends()

        assert len(result) == 0

    def test_get_all_transactions_fetches_all_pages(
        self,
        mocker: "MockerFixture",
        api_key: str,
        api_secret: str,
    ) -> None:
        """Should fetch all pages of transactions."""
        from utils.client import Trading212Client

        client = Trading212Client(api_key=api_key, api_secret=api_secret)

        # First page
        page1_response = MagicMock()
        page1_response.json.return_value = {
            "items": [
                {"type": "DEPOSIT", "amount": 1000.0},
            ],
            "nextPagePath": "/history/transactions?cursor=xyz789",
        }
        page1_response.content = b'{"data": "test"}'
        page1_response.headers = {}

        # Second page
        page2_response = MagicMock()
        page2_response.json.return_value = {
            "items": [
                {"type": "WITHDRAW", "amount": -500.0},
            ],
            "nextPagePath": None,
        }
        page2_response.content = b'{"data": "test"}'
        page2_response.headers = {}

        mocker.patch.object(
            client.client,
            "request",
            side_effect=[page1_response, page2_response],
        )

        result = client.get_all_transactions()

        assert len(result) == 2


class TestClientLiveEnvironmentValidation:
    """Tests for live environment order type validation."""

    def test_live_env_rejects_limit_orders(
        self,
        api_key: str,
        api_secret: str,
    ) -> None:
        """Should raise ValidationError for limit orders in live environment."""
        from exceptions import ValidationError
        from models import LimitRequest, LimitRequestTimeValidityEnum
        from utils.client import Trading212Client

        client = Trading212Client(
            api_key=api_key,
            api_secret=api_secret,
            environment="live",
        )

        limit_request = LimitRequest(
            ticker="AAPL_US_EQ",
            quantity=1.0,
            limitPrice=150.0,
            timeValidity=LimitRequestTimeValidityEnum.DAY,
        )

        with pytest.raises(
            ValidationError, match="not supported in the live environment"
        ):
            client.place_limit_order(limit_request)

    def test_live_env_rejects_stop_orders(
        self,
        api_key: str,
        api_secret: str,
    ) -> None:
        """Should raise ValidationError for stop orders in live environment."""
        from exceptions import ValidationError
        from models import StopRequest, StopRequestTimeValidityEnum
        from utils.client import Trading212Client

        client = Trading212Client(
            api_key=api_key,
            api_secret=api_secret,
            environment="live",
        )

        stop_request = StopRequest(
            ticker="AAPL_US_EQ",
            quantity=1.0,
            stopPrice=140.0,
            timeValidity=StopRequestTimeValidityEnum.DAY,
        )

        with pytest.raises(
            ValidationError, match="not supported in the live environment"
        ):
            client.place_stop_order(stop_request)

    def test_live_env_rejects_stop_limit_orders(
        self,
        api_key: str,
        api_secret: str,
    ) -> None:
        """Should raise ValidationError for stop-limit orders in live environment."""
        from exceptions import ValidationError
        from models import StopLimitRequest, StopLimitRequestTimeValidityEnum
        from utils.client import Trading212Client

        client = Trading212Client(
            api_key=api_key,
            api_secret=api_secret,
            environment="live",
        )

        stop_limit_request = StopLimitRequest(
            ticker="AAPL_US_EQ",
            quantity=1.0,
            stopPrice=140.0,
            limitPrice=138.0,
            timeValidity=StopLimitRequestTimeValidityEnum.DAY,
        )

        with pytest.raises(
            ValidationError, match="not supported in the live environment"
        ):
            client.place_stop_limit_order(stop_limit_request)

    def test_live_env_allows_market_orders(
        self,
        mocker: "MockerFixture",
        api_key: str,
        api_secret: str,
    ) -> None:
        """Should allow market orders in live environment."""
        from models import MarketRequest
        from utils.client import Trading212Client

        client = Trading212Client(
            api_key=api_key,
            api_secret=api_secret,
            environment="live",
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": 123456,
            "ticker": "AAPL_US_EQ",
            "quantity": 1.0,
            "type": "MARKET",
            "status": "NEW",
        }
        mock_response.content = b'{"data": "test"}'
        mock_response.headers = {}
        mocker.patch.object(client.client, "request", return_value=mock_response)

        market_request = MarketRequest(ticker="AAPL_US_EQ", quantity=1.0)
        result = client.place_market_order(market_request)

        assert result.id == 123456
        assert result.ticker == "AAPL_US_EQ"

    def test_demo_env_allows_limit_orders(
        self,
        mocker: "MockerFixture",
        api_key: str,
        api_secret: str,
    ) -> None:
        """Should allow limit orders in demo environment."""
        from models import LimitRequest, LimitRequestTimeValidityEnum
        from utils.client import Trading212Client

        client = Trading212Client(
            api_key=api_key,
            api_secret=api_secret,
            environment="demo",
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": 123456,
            "ticker": "AAPL_US_EQ",
            "quantity": 1.0,
            "type": "LIMIT",
            "status": "NEW",
        }
        mock_response.content = b'{"data": "test"}'
        mock_response.headers = {}
        mocker.patch.object(client.client, "request", return_value=mock_response)

        limit_request = LimitRequest(
            ticker="AAPL_US_EQ",
            quantity=1.0,
            limitPrice=150.0,
            timeValidity=LimitRequestTimeValidityEnum.DAY,
        )
        result = client.place_limit_order(limit_request)

        assert result.id == 123456
