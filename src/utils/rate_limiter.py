"""Per-endpoint rate limiter for Trading212 API.

This module provides a rate limiter that tracks API usage per endpoint
using the x-ratelimit-* response headers from the Trading212 API.
"""

import logging
import time
from collections.abc import Mapping
from dataclasses import dataclass

__all__ = ["RateLimiter", "EndpointLimit"]

logger = logging.getLogger(__name__)


@dataclass
class EndpointLimit:
    """Rate limit state for a specific endpoint.

    Attributes:
        limit: Maximum requests allowed in the period.
        remaining: Requests remaining in the current period.
        reset_time: Unix timestamp when the limit resets.
    """

    limit: int
    remaining: int
    reset_time: float


class RateLimiter:
    """Per-endpoint rate limiter using Trading212 API response headers.

    This class tracks rate limits for each API endpoint independently,
    using the x-ratelimit-* headers returned by the Trading212 API.

    Example:
        >>> limiter = RateLimiter()
        >>> # After a request, update with response headers
        >>> limiter.update_from_headers("/equity/account/info", response.headers)
        >>> # Before next request, check if we should wait
        >>> limiter.wait_if_needed("/equity/account/info")
    """

    def __init__(self) -> None:
        """Initialize the rate limiter with empty endpoint tracking."""
        self._endpoints: dict[str, EndpointLimit] = {}

    def update_from_headers(self, endpoint: str, headers: Mapping[str, str]) -> None:
        """
        Update rate limit state from response headers.

        Args:
            endpoint: The API endpoint path (e.g., "/equity/account/info").
            headers: Response headers containing x-ratelimit-* values.
        """
        try:
            limit_str = headers.get("x-ratelimit-limit")
            remaining_str = headers.get("x-ratelimit-remaining")
            reset_str = headers.get("x-ratelimit-reset")

            # Skip if no rate limit headers present
            if not all([limit_str, remaining_str, reset_str]):
                return

            self._endpoints[endpoint] = EndpointLimit(
                limit=int(limit_str),  # type: ignore[arg-type]
                remaining=int(remaining_str),  # type: ignore[arg-type]
                reset_time=float(reset_str),  # type: ignore[arg-type]
            )

            logger.debug(
                "Updated rate limit for %s: %d/%d remaining, resets at %s",
                endpoint,
                self._endpoints[endpoint].remaining,
                self._endpoints[endpoint].limit,
                self._endpoints[endpoint].reset_time,
            )
        except (ValueError, TypeError) as e:
            logger.warning(
                "Failed to parse rate limit headers for %s: %s",
                endpoint,
                e,
            )

    def can_make_request(self, endpoint: str) -> bool:
        """
        Check if a request can be made to the endpoint.

        Args:
            endpoint: The API endpoint path.

        Returns:
            True if the request is allowed, False if rate limited.
        """
        if endpoint not in self._endpoints:
            return True

        limit_info = self._endpoints[endpoint]

        # Check if reset time has passed
        if time.time() >= limit_info.reset_time:
            return True

        # Check if requests remaining
        return limit_info.remaining > 0

    def get_wait_time(self, endpoint: str) -> float:
        """
        Get the time to wait before making a request.

        Args:
            endpoint: The API endpoint path.

        Returns:
            Seconds to wait, or 0 if no wait is needed.
        """
        if endpoint not in self._endpoints:
            return 0.0

        limit_info = self._endpoints[endpoint]

        # No wait needed if requests available
        if limit_info.remaining > 0:
            return 0.0

        # No wait needed if reset time has passed
        current_time = time.time()
        if current_time >= limit_info.reset_time:
            return 0.0

        # Calculate wait time
        return limit_info.reset_time - current_time

    def wait_if_needed(self, endpoint: str) -> None:
        """
        Wait if necessary before making a request.

        This method blocks until the rate limit allows a request to be made.

        Args:
            endpoint: The API endpoint path.
        """
        wait_time = self.get_wait_time(endpoint)
        if wait_time > 0:
            logger.info(
                "Rate limited on %s, waiting %.2f seconds",
                endpoint,
                wait_time,
            )
            time.sleep(wait_time)
