"""Pytest configuration and shared fixtures.

This module provides common fixtures used across all test modules.
"""

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    pass


@pytest.fixture
def api_key() -> str:
    """Provide a test API key."""
    return "test_api_key_12345"


@pytest.fixture
def api_secret() -> str:
    """Provide a test API secret."""
    return "test_api_secret_67890"


@pytest.fixture
def demo_base_url() -> str:
    """Provide the demo environment base URL."""
    return "https://demo.trading212.com/api/v0"


@pytest.fixture
def live_base_url() -> str:
    """Provide the live environment base URL."""
    return "https://live.trading212.com/api/v0"


@pytest.fixture
def sample_account_response() -> dict:
    """Provide a sample account info response."""
    return {
        "currencyCode": "USD",
        "id": 12345678,
    }


@pytest.fixture
def sample_cash_response() -> dict:
    """Provide a sample cash balance response."""
    return {
        "blocked": 0.0,
        "free": 1000.50,
        "invested": 5000.00,
        "pieCash": 500.00,
        "ppl": 150.25,
        "result": 150.25,
        "total": 6150.75,
    }


@pytest.fixture
def sample_position_response() -> dict:
    """Provide a sample position response."""
    return {
        "averagePrice": 150.00,
        "currentPrice": 175.50,
        "frontend": "API",
        "fxPpl": 0.0,
        "initialFillDate": "2024-01-15T10:30:00Z",
        "maxBuy": 100.0,
        "maxSell": 10.0,
        "pieQuantity": 0.0,
        "ppl": 255.00,
        "quantity": 10.0,
        "ticker": "AAPL_US_EQ",
    }


@pytest.fixture
def sample_order_response() -> dict:
    """Provide a sample order response."""
    return {
        "creationTime": "2024-01-20T14:30:00Z",
        "filledQuantity": 0.0,
        "filledValue": 0.0,
        "id": 987654321,
        "limitPrice": 170.00,
        "quantity": 5.0,
        "status": "NEW",
        "stopPrice": None,
        "strategy": "QUANTITY",
        "ticker": "AAPL_US_EQ",
        "type": "LIMIT",
        "value": None,
    }


@pytest.fixture
def sample_instrument_response() -> dict:
    """Provide a sample instrument response."""
    return {
        "addedOn": "2020-01-01T00:00:00Z",
        "currencyCode": "USD",
        "isin": "US0378331005",
        "maxOpenQuantity": 10000.0,
        "minTradeQuantity": 0.001,
        "name": "Apple Inc",
        "shortName": "Apple",
        "ticker": "AAPL_US_EQ",
        "type": "STOCK",
        "workingScheduleId": 1,
    }


@pytest.fixture
def sample_exchange_response() -> dict:
    """Provide a sample exchange response."""
    return {
        "id": 1,
        "name": "NASDAQ",
        "workingSchedules": [
            {
                "id": 1,
                "timeEvents": [
                    {"date": "2024-01-22T14:30:00Z", "type": "OPEN"},
                    {"date": "2024-01-22T21:00:00Z", "type": "CLOSE"},
                ],
            }
        ],
    }


@pytest.fixture
def sample_dividend_response() -> dict:
    """Provide a sample dividend history response."""
    return {
        "items": [
            {
                "amount": 2.50,
                "amountInEuro": 2.30,
                "grossAmountPerShare": 0.25,
                "paidOn": "2024-01-15T00:00:00Z",
                "quantity": 10.0,
                "reference": "DIV-123456",
                "ticker": "AAPL_US_EQ",
                "type": "ORDINARY",
            }
        ],
        "nextPagePath": None,
    }


@pytest.fixture
def sample_historical_order_response() -> dict:
    """Provide a sample historical order response."""
    return {
        "items": [
            {
                "dateCreated": "2024-01-10T09:00:00Z",
                "dateExecuted": "2024-01-10T09:00:05Z",
                "dateModified": "2024-01-10T09:00:05Z",
                "executor": "API",
                "fillCost": 1500.00,
                "fillId": 111222333,
                "fillPrice": 150.00,
                "fillResult": 0.0,
                "fillType": "TOTV",
                "filledQuantity": 10.0,
                "filledValue": None,
                "id": 999888777,
                "limitPrice": None,
                "orderedQuantity": 10.0,
                "orderedValue": None,
                "parentOrder": None,
                "status": "FILLED",
                "stopPrice": None,
                "taxes": [],
                "ticker": "AAPL_US_EQ",
                "timeValidity": "DAY",
                "type": "MARKET",
            }
        ],
        "nextPagePath": None,
    }


@pytest.fixture
def sample_pie_response() -> dict:
    """Provide a sample pie response."""
    return {
        "cash": 1000.00,
        "dividendDetails": {
            "gained": 50.00,
            "inCash": 25.00,
            "reinvested": 25.00,
        },
        "id": 123,
        "progress": 0.5,
        "result": {
            "priceAvgInvestedValue": 1000.00,
            "priceAvgResult": 100.00,
            "priceAvgResultCoef": 0.1,
            "priceAvgValue": 1100.00,
        },
        "status": "ON_TRACK",
    }


@pytest.fixture
def rate_limit_headers() -> dict:
    """Provide sample rate limit response headers."""
    return {
        "x-ratelimit-limit": "1",
        "x-ratelimit-remaining": "0",
        "x-ratelimit-reset": "1706000000",
    }
