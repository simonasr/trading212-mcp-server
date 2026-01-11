"""Retry decorator with exponential backoff.

This module provides a retry decorator for handling transient failures
when making API requests.
"""

import functools
import logging
import random
import time
from collections.abc import Callable
from typing import ParamSpec, TypeVar

import httpx

__all__ = ["with_retry"]

logger = logging.getLogger(__name__)

P = ParamSpec("P")
T = TypeVar("T")

# HTTP status codes that should trigger a retry
RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}

# HTTP status codes that should NOT be retried (client errors except rate limit)
NON_RETRYABLE_STATUS_CODES = {400, 401, 403, 404}


def with_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    retryable_statuses: set[int] | None = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Decorator that retries a function with exponential backoff.

    This decorator will retry a function if it raises certain HTTP errors
    or connection errors, using exponential backoff with jitter.

    Args:
        max_retries: Maximum number of retry attempts (default: 3).
        base_delay: Initial delay in seconds between retries (default: 1.0).
        max_delay: Maximum delay in seconds between retries (default: 60.0).
        retryable_statuses: Set of HTTP status codes to retry on.
            Defaults to {408, 429, 500, 502, 503, 504}.

    Returns:
        A decorator function.

    Example:
        >>> @with_retry(max_retries=3, base_delay=1.0)
        ... def fetch_data():
        ...     return httpx.get("https://api.example.com/data")
    """
    if retryable_statuses is None:
        retryable_statuses = RETRYABLE_STATUS_CODES

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            last_exception: Exception | None = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except httpx.HTTPStatusError as e:
                    # Check if status code is retryable
                    status_code = e.response.status_code

                    if status_code not in retryable_statuses:
                        # Don't retry client errors (except rate limit)
                        raise

                    last_exception = e

                    if attempt < max_retries:
                        delay = _calculate_delay(attempt, base_delay, max_delay)
                        logger.warning(
                            "Request failed with status %d, retrying in %.2fs "
                            "(attempt %d/%d)",
                            status_code,
                            delay,
                            attempt + 1,
                            max_retries,
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            "Request failed with status %d after %d retries",
                            status_code,
                            max_retries,
                        )
                        raise

                except (httpx.ConnectError, httpx.TimeoutException) as e:
                    # Retry connection errors
                    last_exception = e

                    if attempt < max_retries:
                        delay = _calculate_delay(attempt, base_delay, max_delay)
                        logger.warning(
                            "Connection error: %s, retrying in %.2fs (attempt %d/%d)",
                            type(e).__name__,
                            delay,
                            attempt + 1,
                            max_retries,
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            "Connection error after %d retries: %s",
                            max_retries,
                            e,
                        )
                        raise

            # This should never be reached, but just in case
            if last_exception:
                raise last_exception
            raise RuntimeError("Retry loop exited unexpectedly")

        return wrapper

    return decorator


def _calculate_delay(attempt: int, base_delay: float, max_delay: float) -> float:
    """
    Calculate the delay for the next retry attempt.

    Uses exponential backoff with full jitter:
    delay = random(0, min(max_delay, base_delay * 2^attempt))

    Args:
        attempt: The current attempt number (0-indexed).
        base_delay: Base delay in seconds.
        max_delay: Maximum delay in seconds.

    Returns:
        Delay in seconds to wait before the next retry.
    """
    # Exponential backoff: base_delay * 2^attempt
    exponential_delay = base_delay * (2**attempt)

    # Cap at max_delay
    capped_delay = min(exponential_delay, max_delay)

    # Add jitter (full jitter strategy)
    return random.uniform(0, capped_delay)
