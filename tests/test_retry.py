"""Tests for the retry decorator.

This module contains tests for the retry decorator with exponential backoff.
"""

import sys
from pathlib import Path
from typing import TYPE_CHECKING

import httpx
import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

if TYPE_CHECKING:
    from pytest_mock.plugin import MockerFixture


class TestRetryDecorator:
    """Tests for the with_retry decorator."""

    def test_retry_on_429(self, mocker: "MockerFixture") -> None:
        """Should retry with backoff on rate limit errors."""
        from utils.retry import with_retry

        # Mock sleep to avoid actual delays
        mocker.patch("time.sleep")

        call_count = 0

        @with_retry(max_retries=3, base_delay=0.1)
        def failing_func() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                response = httpx.Response(429)
                raise httpx.HTTPStatusError(
                    "Rate limited",
                    request=httpx.Request("GET", "http://test"),
                    response=response,
                )
            return "success"

        result = failing_func()
        assert result == "success"
        assert call_count == 3  # Failed twice, succeeded on third

    def test_retry_on_server_error(self, mocker: "MockerFixture") -> None:
        """Should retry on 5xx errors."""
        from utils.retry import with_retry

        mocker.patch("time.sleep")

        call_count = 0

        @with_retry(max_retries=3, base_delay=0.1)
        def failing_func() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                response = httpx.Response(500)
                raise httpx.HTTPStatusError(
                    "Server error",
                    request=httpx.Request("GET", "http://test"),
                    response=response,
                )
            return "success"

        result = failing_func()
        assert result == "success"
        assert call_count == 2

    def test_no_retry_on_client_error(self) -> None:
        """Should not retry on 4xx errors (except 429)."""
        from utils.retry import with_retry

        call_count = 0

        @with_retry(max_retries=3, base_delay=0.1)
        def failing_func() -> str:
            nonlocal call_count
            call_count += 1
            response = httpx.Response(400)
            raise httpx.HTTPStatusError(
                "Bad request",
                request=httpx.Request("GET", "http://test"),
                response=response,
            )

        with pytest.raises(httpx.HTTPStatusError):
            failing_func()

        # Should not retry on 400
        assert call_count == 1

    def test_no_retry_on_401(self) -> None:
        """Should not retry on authentication errors."""
        from utils.retry import with_retry

        call_count = 0

        @with_retry(max_retries=3, base_delay=0.1)
        def failing_func() -> str:
            nonlocal call_count
            call_count += 1
            response = httpx.Response(401)
            raise httpx.HTTPStatusError(
                "Unauthorized",
                request=httpx.Request("GET", "http://test"),
                response=response,
            )

        with pytest.raises(httpx.HTTPStatusError):
            failing_func()

        assert call_count == 1

    def test_max_retries_exceeded(self, mocker: "MockerFixture") -> None:
        """Should raise after max retries exceeded."""
        from utils.retry import with_retry

        mocker.patch("time.sleep")

        call_count = 0

        @with_retry(max_retries=3, base_delay=0.1)
        def always_fails() -> str:
            nonlocal call_count
            call_count += 1
            response = httpx.Response(500)
            raise httpx.HTTPStatusError(
                "Server error",
                request=httpx.Request("GET", "http://test"),
                response=response,
            )

        with pytest.raises(httpx.HTTPStatusError):
            always_fails()

        # Initial call + 3 retries
        assert call_count == 4

    def test_retry_on_timeout(self, mocker: "MockerFixture") -> None:
        """Should retry on timeout errors."""
        from utils.retry import with_retry

        mocker.patch("time.sleep")

        call_count = 0

        @with_retry(max_retries=3, base_delay=0.1)
        def timeout_func() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                response = httpx.Response(408)
                raise httpx.HTTPStatusError(
                    "Timeout",
                    request=httpx.Request("GET", "http://test"),
                    response=response,
                )
            return "success"

        result = timeout_func()
        assert result == "success"

    def test_exponential_backoff(self, mocker: "MockerFixture") -> None:
        """Should use exponential backoff with jitter."""
        from utils.retry import with_retry

        sleep_mock = mocker.patch("time.sleep")
        mocker.patch("random.uniform", side_effect=lambda a, b: (a + b) / 2)

        call_count = 0

        @with_retry(max_retries=3, base_delay=1.0, max_delay=10.0)
        def always_fails() -> str:
            nonlocal call_count
            call_count += 1
            response = httpx.Response(500)
            raise httpx.HTTPStatusError(
                "Server error",
                request=httpx.Request("GET", "http://test"),
                response=response,
            )

        with pytest.raises(httpx.HTTPStatusError):
            always_fails()

        # Verify exponential backoff: 1, 2, 4 (base * 2^attempt)
        # With jitter, delays should be around: 0.5-1.5, 1-3, 2-6
        assert sleep_mock.call_count == 3
        delays = [call[0][0] for call in sleep_mock.call_args_list]
        # First delay should be less than second, second less than third
        assert delays[0] < delays[1] < delays[2]

    def test_success_on_first_try(self) -> None:
        """Should return immediately on success without retrying."""
        from utils.retry import with_retry

        call_count = 0

        @with_retry(max_retries=3, base_delay=0.1)
        def succeeds() -> str:
            nonlocal call_count
            call_count += 1
            return "success"

        result = succeeds()
        assert result == "success"
        assert call_count == 1

    def test_retry_on_connection_error(self, mocker: "MockerFixture") -> None:
        """Should retry on connection errors."""
        from utils.retry import with_retry

        mocker.patch("time.sleep")

        call_count = 0

        @with_retry(max_retries=3, base_delay=0.1)
        def connection_error_func() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise httpx.ConnectError("Connection failed")
            return "success"

        result = connection_error_func()
        assert result == "success"
        assert call_count == 2

    def test_preserves_function_metadata(self) -> None:
        """Should preserve the decorated function's name and docstring."""
        from utils.retry import with_retry

        @with_retry(max_retries=3)
        def my_function() -> str:
            """My docstring."""
            return "result"

        assert my_function.__name__ == "my_function"
        assert my_function.__doc__ == "My docstring."
