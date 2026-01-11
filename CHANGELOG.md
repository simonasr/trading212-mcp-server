# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-01-11

### Breaking Changes

- **Authentication**: Now requires both `TRADING212_API_KEY` and `TRADING212_API_SECRET` environment variables (Basic authentication)
- **Tool names**: Standardized all tool names for consistency:
  - `fetch_pies` → `get_pies`
  - `fetch_all_orders` → `get_orders`
  - `fetch_historical_order_data` → `get_order_history`
  - `fetch_paid_out_dividends` → `get_dividends`
  - `fetch_instruments` → `search_instruments`
  - `fetch_exchanges` → `search_exchanges`

### Added

- **Per-endpoint rate limiting** with automatic waiting when limits are reached
  - Tracks `x-ratelimit-*` response headers
  - Automatically waits before requests when rate limited
- **Retry logic** with exponential backoff for transient failures
  - Retries on 429, 408, and 5xx errors
  - Configurable max retries and delays
- **Custom exception hierarchy** for better error handling:
  - `Trading212Error` (base)
  - `AuthenticationError` (401)
  - `AuthorizationError` (403)
  - `NotFoundError` (404)
  - `RateLimitError` (429)
  - `ValidationError` (400)
  - `TimeoutError` (408)
  - `ServerError` (5xx)
- **Auto-pagination helpers**:
  - `get_all_dividends()` - fetches all dividend pages
  - `get_all_transactions()` - fetches all transaction pages
- **Live environment validation** - raises `ValidationError` when placing limit/stop/stop-limit orders in live environment (only market orders are supported)
- **Comprehensive test suite** with mocked responses
- **GitHub Actions CI/CD** workflow for linting, type checking, and testing
- **`.env.example`** template for environment variables

### Fixed

- **Removed dangerous POST request caching** - only GET requests are now cached
- **Proper error handling** for all HTTP status codes
- **Rate limiter integration** in the client

### Changed

- **Modern Python 3.11+ syntax** throughout (`X | None` instead of `Optional[X]`)
- **Explicit imports** instead of wildcard imports
- **Updated pyproject.toml** with proper metadata, dev dependencies, and tool configs

## [0.1.0] - Initial Release

Initial release of Trading212 MCP server with basic functionality.
