# Trading212 MCP Server

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-0.2.0-blue.svg)](CHANGELOG.md)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

## Overview

The Trading212 MCP server is a [Model Context Protocol](https://modelcontextprotocol.io/introduction) server implementation that provides seamless data connectivity to the Trading212 trading platform.

## Features

- **Complete Trading212 API Integration**: Account management, order placement, portfolio tracking
- **Rate Limiting**: Automatic per-endpoint rate limit tracking and waiting
- **Retry Logic**: Exponential backoff for transient failures
- **Error Handling**: Comprehensive custom exception hierarchy
- **Auto-Pagination**: Helper methods to fetch all pages of paginated data
- **Live Environment Safety**: Validation prevents unsupported order types in live trading
- **Local Cache** (opt-in): SQLite caching for historical data to bypass API rate limits

## Requirements

- Python >= 3.11
- Trading212 API Key and Secret

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/RohanAnandPandit/trading212-mcp-server.git
cd trading212-mcp-server
```

### 2. Configure Environment

Copy `.env.example` to `.env` and configure your credentials:

```bash
cp .env.example .env
```

Required environment variables:

```env
TRADING212_API_KEY=your_api_key_here
TRADING212_API_SECRET=your_api_secret_here
ENVIRONMENT=demo  # or "live"
TRANSPORT=stdio
```

### 3. Install Dependencies

```bash
uv sync
```

### 4. Run the Server

```bash
uv run src/server.py
```

## Authentication

> **Breaking Change in v0.2.0**: Authentication now requires both API key and API secret.

Trading212 uses Basic authentication. You need both:
- `TRADING212_API_KEY`: Your API key
- `TRADING212_API_SECRET`: Your API secret

Generate credentials from your [Trading212 account settings](https://helpcentre.trading212.com/hc/en-us/articles/14584770928157-How-can-I-generate-an-API-key).

## Live Environment Limitations

⚠️ **Important**: The live Trading212 environment only supports **market orders** via API.

Attempting to place limit, stop, or stop-limit orders in the live environment will raise a `ValidationError`. These order types are only available in the demo environment.

## Tools Reference

### Instruments Metadata
| Tool | Description |
|------|-------------|
| `search_instruments` | Search instruments by ticker or name |
| `search_exchanges` | Search exchanges by name or ID |

### Pies (Portfolio Buckets)
| Tool | Description |
|------|-------------|
| `get_pies` | Fetch all pies |
| `get_pie` | Fetch a specific pie by ID |
| `create_pie` | Create a new pie |
| `update_pie` | Update a pie |
| `delete_pie` | Delete a pie |
| `duplicate_pie` | Duplicate a pie |

### Equity Orders
| Tool | Description |
|------|-------------|
| `get_orders` | Fetch all active orders |
| `get_order` | Fetch a specific order by ID |
| `place_market_order` | Place a market order |
| `place_limit_order` | Place a limit order (demo only) |
| `place_stop_order` | Place a stop order (demo only) |
| `place_stop_limit_order` | Place a stop-limit order (demo only) |
| `cancel_order` | Cancel an existing order |

### Account Data
| Tool | Description |
|------|-------------|
| `get_account_info` | Fetch account metadata (ID, currency) |
| `get_account_cash` | Fetch account cash balance |

### Portfolio
| Tool | Description |
|------|-------------|
| `get_positions` | Fetch all open positions |
| `get_position` | Search for a position by ticker |

### Historical Data
| Tool | Description |
|------|-------------|
| `get_order_history` | Fetch historical orders (paginated) |
| `get_dividends` | Fetch dividend history (paginated) |
| `get_transactions` | Fetch transaction history (paginated) |
| `get_exports` | List all CSV exports |
| `create_export` | Request a new CSV export |

### Cache Management
| Tool | Description |
|------|-------------|
| `sync_historical_data` | Sync historical data from API to local cache |
| `clear_cache` | Clear local cache (all or specific table) |
| `cache_stats` | Get cache statistics (counts, sizes, sync times) |

## Resources

### Account Resources
- `trading212://account/info` - Account metadata
- `trading212://account/cash` - Cash balance
- `trading212://account/portfolio` - All positions
- `trading212://account/portfolio/{ticker}` - Position by ticker

### Order Resources
- `trading212://orders` - All orders
- `trading212://orders/{order_id}` - Order by ID

### Pie Resources
- `trading212://pies` - All pies
- `trading212://pies/{pie_id}` - Pie by ID

### Market Resources
- `trading212://instruments` - All tradeable instruments
- `trading212://exchanges` - All exchanges

### Report Resources
- `trading212://history/exports` - All CSV exports

## Claude Desktop Configuration

### Using uv

```json
{
  "mcpServers": {
    "trading212": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/path/to/trading212-mcp-server",
        "src/server.py"
      ],
      "env": {
        "TRADING212_API_KEY": "your_api_key",
        "TRADING212_API_SECRET": "your_api_secret",
        "ENVIRONMENT": "demo"
      }
    }
  }
}
```

### Using Docker

```bash
docker build -t mcp/trading212 .
```

```json
{
  "mcpServers": {
    "trading212": {
      "command": "docker",
      "args": [
        "run", "-i",
        "-e", "TRADING212_API_KEY",
        "-e", "TRADING212_API_SECRET",
        "-e", "ENVIRONMENT",
        "mcp/trading212"
      ],
      "env": {
        "TRADING212_API_KEY": "your_api_key",
        "TRADING212_API_SECRET": "your_api_secret",
        "ENVIRONMENT": "demo"
      }
    }
  }
}
```

## Error Handling

The client uses a custom exception hierarchy:

| Exception | HTTP Status | Description |
|-----------|-------------|-------------|
| `AuthenticationError` | 401 | Invalid API credentials |
| `AuthorizationError` | 403 | Missing required permission |
| `NotFoundError` | 404 | Resource not found |
| `RateLimitError` | 429 | Rate limit exceeded |
| `ValidationError` | 400 | Request validation failed |
| `TimeoutError` | 408 | Request timed out |
| `ServerError` | 5xx | Server-side error |

## Rate Limiting

The client automatically:
- Tracks rate limits per endpoint using `x-ratelimit-*` headers
- Waits when rate limits are exhausted
- Retries requests with exponential backoff on transient failures

## Local Cache (Optional)

The Trading212 MCP server includes an optional SQLite caching layer for historical data (orders, dividends, transactions). This is useful for:

- **Bypassing API rate limits**: Historical data is cached locally after initial sync
- **Richer analysis**: Access complete historical data without pagination limits
- **Offline access**: Cached data is available without API connectivity

### Enable Caching

Set the following environment variables:

```env
ENABLE_LOCAL_CACHE=true
DATABASE_PATH=./data/trading212.db     # Optional, this is the default
CACHE_FRESHNESS_MINUTES=60             # Optional, auto-sync threshold in minutes
```

### Cache Freshness

The cache includes automatic freshness checking. When you access cached data:

- If cache is **fresh** (synced within `CACHE_FRESHNESS_MINUTES`): Returns cached data immediately
- If cache is **stale**: Auto-syncs from API first, then returns data

Special values for `CACHE_FRESHNESS_MINUTES`:
- `60` (default): Cache is fresh for 1 hour
- `0`: Always sync (never use stale cache)
- `-1`: Never auto-sync (manual sync only)

### Cache Management Tools

| Tool | Description |
|------|-------------|
| `sync_historical_data` | Sync all or specific tables from API to local cache |
| `clear_cache` | Clear cached data (all or specific table) |
| `cache_stats` | Get cache statistics (record counts, sizes, sync times) |

### Usage Examples

```python
# Sync all historical data
sync_historical_data()

# Sync only orders
sync_historical_data(tables=["orders"])

# Force full resync (clears cache first)
sync_historical_data(force=True)

# Check cache statistics
cache_stats()

# Clear all cached data
clear_cache()

# Clear only dividends
clear_cache(table="dividends")
```

### How It Works

1. **First sync**: Fetches all historical data from the API
2. **Subsequent syncs**: Incremental by default - only fetches new records since last sync (for dividends/transactions)
3. **Automatic refresh**: Cache is auto-refreshed when stale (configurable via `CACHE_FRESHNESS_MINUTES`)
4. **Multi-account support**: Cache is scoped by account ID
5. **Data storage**: SQLite database at the configured path

> **Note**: To force a full resync (e.g., for troubleshooting or data validation), use `sync_historical_data(force=True)`. This clears the cache and fetches all records from the API.

## Development

A `Makefile` is provided for common development tasks:

```bash
make dev          # Install all dependencies (including dev)
make check        # Run all checks (lint, format, typecheck, test)
make test         # Run tests
make lint         # Run linter
make format       # Auto-format code
make typecheck    # Run type checker
make clean        # Remove cache files
```

### Manual Commands

If you prefer not to use `make`:

```bash
uv sync --all-extras              # Install dev dependencies
uv run pytest                     # Run tests
uv run ruff check src tests       # Lint
uv run ruff format src tests      # Format
uv run mypy src                   # Type check
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Documentation

- [Trading212 API Documentation](https://t212public-api-docs.redoc.ly/)
- [CHANGELOG](CHANGELOG.md)
- [CONTRIBUTING](CONTRIBUTING.md)

## Legal Notice

This is an unofficial implementation. Always consult official Trading212 documentation and terms of service before using this software.
