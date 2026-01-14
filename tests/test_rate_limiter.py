"""Tests for the rate limiter.

This module contains tests for the per-endpoint rate limiter that tracks
API usage and enforces rate limits.
"""

import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

if TYPE_CHECKING:
    from pytest_mock.plugin import MockerFixture


class TestRateLimiter:
    """Tests for the RateLimiter class."""

    def test_update_from_headers(self) -> None:
        """Should parse x-ratelimit-* headers correctly."""
        from utils.rate_limiter import RateLimiter

        limiter = RateLimiter()
        endpoint = "/equity/account/info"

        headers = {
            "x-ratelimit-limit": "1",
            "x-ratelimit-remaining": "0",
            "x-ratelimit-reset": str(int(time.time()) + 30),
        }

        limiter.update_from_headers(endpoint, headers)

        # Verify the limits were recorded
        assert endpoint in limiter._endpoints
        assert limiter._endpoints[endpoint].limit == 1
        assert limiter._endpoints[endpoint].remaining == 0

    def test_respects_per_endpoint_limits(self) -> None:
        """Each endpoint should have independent limits."""
        from utils.rate_limiter import RateLimiter

        limiter = RateLimiter()

        # Update two different endpoints
        headers1 = {
            "x-ratelimit-limit": "1",
            "x-ratelimit-remaining": "0",
            "x-ratelimit-reset": str(int(time.time()) + 30),
        }
        headers2 = {
            "x-ratelimit-limit": "5",
            "x-ratelimit-remaining": "4",
            "x-ratelimit-reset": str(int(time.time()) + 60),
        }

        limiter.update_from_headers("/equity/account/info", headers1)
        limiter.update_from_headers("/equity/orders", headers2)

        # Verify independent tracking
        assert limiter._endpoints["/equity/account/info"].remaining == 0
        assert limiter._endpoints["/equity/orders"].remaining == 4

    def test_can_make_request_returns_false_when_limited(self) -> None:
        """Should return False when rate limit is exhausted."""
        from utils.rate_limiter import RateLimiter

        limiter = RateLimiter()
        endpoint = "/equity/account/info"

        # Set up exhausted limit
        headers = {
            "x-ratelimit-limit": "1",
            "x-ratelimit-remaining": "0",
            "x-ratelimit-reset": str(int(time.time()) + 30),
        }
        limiter.update_from_headers(endpoint, headers)

        assert limiter.can_make_request(endpoint) is False

    def test_can_make_request_returns_true_when_available(self) -> None:
        """Should return True when requests are available."""
        from utils.rate_limiter import RateLimiter

        limiter = RateLimiter()
        endpoint = "/equity/account/info"

        # Set up available limit
        headers = {
            "x-ratelimit-limit": "10",
            "x-ratelimit-remaining": "5",
            "x-ratelimit-reset": str(int(time.time()) + 30),
        }
        limiter.update_from_headers(endpoint, headers)

        assert limiter.can_make_request(endpoint) is True

    def test_can_make_request_returns_true_for_unknown_endpoint(self) -> None:
        """Should return True for endpoints without recorded limits."""
        from utils.rate_limiter import RateLimiter

        limiter = RateLimiter()

        # New endpoint with no recorded limits
        assert limiter.can_make_request("/new/endpoint") is True

    def test_can_make_request_returns_true_after_reset(self) -> None:
        """Should return True after the reset time has passed."""
        from utils.rate_limiter import RateLimiter

        limiter = RateLimiter()
        endpoint = "/equity/account/info"

        # Set up limit that has already reset
        headers = {
            "x-ratelimit-limit": "1",
            "x-ratelimit-remaining": "0",
            "x-ratelimit-reset": str(int(time.time()) - 10),  # Reset 10 seconds ago
        }
        limiter.update_from_headers(endpoint, headers)

        assert limiter.can_make_request(endpoint) is True

    def test_get_wait_time_returns_seconds_until_reset(self) -> None:
        """Should return the number of seconds until rate limit resets."""
        from utils.rate_limiter import RateLimiter

        limiter = RateLimiter()
        endpoint = "/equity/account/info"

        reset_time = int(time.time()) + 30
        headers = {
            "x-ratelimit-limit": "1",
            "x-ratelimit-remaining": "0",
            "x-ratelimit-reset": str(reset_time),
        }
        limiter.update_from_headers(endpoint, headers)

        wait_time = limiter.get_wait_time(endpoint)
        assert 25 <= wait_time <= 31  # Allow some tolerance

    def test_get_wait_time_returns_zero_when_available(self) -> None:
        """Should return 0 when requests are available."""
        from utils.rate_limiter import RateLimiter

        limiter = RateLimiter()
        endpoint = "/equity/account/info"

        headers = {
            "x-ratelimit-limit": "10",
            "x-ratelimit-remaining": "5",
            "x-ratelimit-reset": str(int(time.time()) + 30),
        }
        limiter.update_from_headers(endpoint, headers)

        assert limiter.get_wait_time(endpoint) == 0

    def test_get_wait_time_returns_zero_for_unknown_endpoint(self) -> None:
        """Should return 0 for endpoints without recorded limits."""
        from utils.rate_limiter import RateLimiter

        limiter = RateLimiter()

        assert limiter.get_wait_time("/unknown/endpoint") == 0

    def test_wait_if_needed_blocks_when_limited(
        self,
        mocker: "MockerFixture",
    ) -> None:
        """Should block (sleep) when rate limit is exhausted."""
        from utils.rate_limiter import RateLimiter

        limiter = RateLimiter()
        endpoint = "/equity/account/info"

        # Set up exhausted limit with short reset time
        reset_time = int(time.time()) + 1
        headers = {
            "x-ratelimit-limit": "1",
            "x-ratelimit-remaining": "0",
            "x-ratelimit-reset": str(reset_time),
        }
        limiter.update_from_headers(endpoint, headers)

        # Mock time.sleep
        sleep_mock = mocker.patch("time.sleep")

        limiter.wait_if_needed(endpoint)

        # Verify sleep was called
        sleep_mock.assert_called_once()
        # Should sleep for approximately the wait time
        call_args = sleep_mock.call_args[0][0]
        assert 0 <= call_args <= 2

    def test_wait_if_needed_does_not_block_when_available(
        self,
        mocker: "MockerFixture",
    ) -> None:
        """Should not block when requests are available."""
        from utils.rate_limiter import RateLimiter

        limiter = RateLimiter()
        endpoint = "/equity/account/info"

        # Set up available limit
        headers = {
            "x-ratelimit-limit": "10",
            "x-ratelimit-remaining": "5",
            "x-ratelimit-reset": str(int(time.time()) + 30),
        }
        limiter.update_from_headers(endpoint, headers)

        # Mock time.sleep
        sleep_mock = mocker.patch("time.sleep")

        limiter.wait_if_needed(endpoint)

        # Verify sleep was NOT called
        sleep_mock.assert_not_called()

    def test_handles_missing_headers_gracefully(self) -> None:
        """Should not crash when headers are missing."""
        from utils.rate_limiter import RateLimiter

        limiter = RateLimiter()
        endpoint = "/equity/account/info"

        # Empty headers
        limiter.update_from_headers(endpoint, {})

        # Should still work without recorded limits
        assert limiter.can_make_request(endpoint) is True

    def test_handles_invalid_header_values_gracefully(self) -> None:
        """Should handle invalid header values without crashing."""
        from utils.rate_limiter import RateLimiter

        limiter = RateLimiter()
        endpoint = "/equity/account/info"

        # Invalid header values
        headers = {
            "x-ratelimit-limit": "invalid",
            "x-ratelimit-remaining": "not_a_number",
            "x-ratelimit-reset": "also_invalid",
        }
        limiter.update_from_headers(endpoint, headers)

        # Should still work with defaults
        assert limiter.can_make_request(endpoint) is True
