"""Custom exceptions for Trading212 API client.

This module defines a hierarchy of exceptions for handling various error
conditions when interacting with the Trading212 API.
"""

__all__ = [
    "Trading212Error",
    "AuthenticationError",
    "AuthorizationError",
    "NotFoundError",
    "RateLimitError",
    "ValidationError",
    "TimeoutError",
    "ServerError",
]


class Trading212Error(Exception):
    """Base exception for all Trading212 API errors.

    All Trading212-specific exceptions inherit from this class, making it
    easy to catch all API-related errors with a single except clause.

    Attributes:
        message: Human-readable error description.
        status_code: HTTP status code if applicable.
    """

    def __init__(self, message: str, status_code: int | None = None) -> None:
        """
        Initialize a Trading212 error.

        Args:
            message: Human-readable error description.
            status_code: HTTP status code if applicable.
        """
        super().__init__(message)
        self.message = message
        self.status_code = status_code

    def __str__(self) -> str:
        """Return string representation of the error."""
        if self.status_code:
            return f"[{self.status_code}] {self.message}"
        return self.message


class AuthenticationError(Trading212Error):
    """Invalid or missing API credentials (HTTP 401).

    Raised when the API key or secret is invalid or missing.

    Example:
        >>> raise AuthenticationError("Invalid API credentials")
    """

    def __init__(self, message: str = "Invalid API credentials") -> None:
        """
        Initialize an authentication error.

        Args:
            message: Error description.
        """
        super().__init__(message, status_code=401)


class AuthorizationError(Trading212Error):
    """Missing scope or permission for the requested operation (HTTP 403).

    Raised when the API key doesn't have the required scope/permission
    for the requested endpoint.

    Attributes:
        required_scope: The scope that was required but missing.
    """

    def __init__(
        self,
        message: str = "Missing required permission",
        required_scope: str | None = None,
    ) -> None:
        """
        Initialize an authorization error.

        Args:
            message: Error description.
            required_scope: The scope that was required but missing.
        """
        super().__init__(message, status_code=403)
        self.required_scope = required_scope


class NotFoundError(Trading212Error):
    """Requested resource not found (HTTP 404).

    Raised when the requested resource (order, position, pie, etc.)
    doesn't exist.

    Attributes:
        resource_type: Type of resource that wasn't found.
        resource_id: ID of the resource that wasn't found.
    """

    def __init__(
        self,
        message: str = "Resource not found",
        resource_type: str | None = None,
        resource_id: str | int | None = None,
    ) -> None:
        """
        Initialize a not found error.

        Args:
            message: Error description.
            resource_type: Type of resource that wasn't found.
            resource_id: ID of the resource that wasn't found.
        """
        super().__init__(message, status_code=404)
        self.resource_type = resource_type
        self.resource_id = resource_id


class RateLimitError(Trading212Error):
    """Rate limit exceeded (HTTP 429).

    Raised when too many requests have been made in a short time period.

    Attributes:
        retry_after: Number of seconds to wait before retrying.
        limit: The rate limit that was exceeded.
        remaining: Number of requests remaining (typically 0).
    """

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: float | None = None,
        limit: int | None = None,
        remaining: int | None = None,
    ) -> None:
        """
        Initialize a rate limit error.

        Args:
            message: Error description.
            retry_after: Seconds to wait before retrying.
            limit: The rate limit that was exceeded.
            remaining: Number of requests remaining.
        """
        super().__init__(message, status_code=429)
        self.retry_after = retry_after
        self.limit = limit
        self.remaining = remaining


class ValidationError(Trading212Error):
    """Request validation failed (HTTP 400).

    Raised when the request parameters are invalid, such as when
    placing an order with invalid ticker or quantity.

    Attributes:
        code: Error code from the API (e.g., 'InsufficientResources').
        clarification: Additional explanation of the error.
    """

    def __init__(
        self,
        message: str = "Validation error",
        code: str | None = None,
        clarification: str | None = None,
    ) -> None:
        """
        Initialize a validation error.

        Args:
            message: Error description.
            code: Error code from the API.
            clarification: Additional explanation.
        """
        super().__init__(message, status_code=400)
        self.code = code
        self.clarification = clarification


class TimeoutError(Trading212Error):
    """Request timed out (HTTP 408).

    Raised when the API request took too long to complete.
    """

    def __init__(self, message: str = "Request timed out") -> None:
        """
        Initialize a timeout error.

        Args:
            message: Error description.
        """
        super().__init__(message, status_code=408)


class ServerError(Trading212Error):
    """Server-side error (HTTP 5xx).

    Raised when the Trading212 API encounters an internal error.
    These errors are typically transient and can be retried.

    Attributes:
        original_status_code: The actual 5xx status code received.
    """

    def __init__(
        self,
        message: str = "Server error",
        status_code: int = 500,
    ) -> None:
        """
        Initialize a server error.

        Args:
            message: Error description.
            status_code: The actual HTTP status code (5xx).
        """
        super().__init__(message, status_code=status_code)
