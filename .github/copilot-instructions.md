# GitHub Copilot Custom Instructions

## Project Overview

This is a **Trading212 MCP (Model Context Protocol) Server** that exposes Trading212 API functionality as tools, prompts, and resources for AI assistants.

## Key Patterns

### Side-Effect Imports for MCP Registration

In `src/server.py`, the imports of `tools`, `prompts`, and `resources` modules are **intentional side-effect imports**. These modules use decorators (`@mcp.tool()`, `@mcp.prompt()`, `@mcp.resource()`) that register functions with the MCP server when the module is imported.

```python
# These imports are NOT unused - they register MCP handlers via decorators
import prompts  # noqa: F401
import resources  # noqa: F401
import tools  # noqa: F401
```

The `# noqa: F401` comments suppress linter warnings. Do NOT suggest removing these imports or adding `_ = module` patterns.

### MCP Decorator Pattern

Functions decorated with `@mcp.tool()`, `@mcp.prompt()`, or `@mcp.resource()` are automatically registered and do not need explicit exports or calls.

### Exception Handling with Logging

When catching exceptions that should be silently ignored (e.g., `sqlite3.IntegrityError` for duplicate records), always log a warning with context:

```python
except sqlite3.IntegrityError as exc:
    logger.warning("Failed to upsert record: %s", exc)
```

Do NOT use bare `except: pass` without logging.

### Type Hints

- All functions should have type hints
- Use `from __future__ import annotations` for forward references
- Pydantic models are used for API responses in `src/models.py`

### Testing

- Tests are in `tests/` directory
- Use `pytest` with `pytest-httpx` for HTTP mocking
- Use `pytest-mock` for general mocking
- Run tests with `make test` or `uv run pytest`

### Code Quality

- Linting: `ruff check`
- Formatting: `ruff format`
- Type checking: `mypy`
- Run all checks with `make check`

## Project Structure

```
src/
├── server.py          # Entry point, imports register MCP handlers
├── mcp_server.py      # FastMCP instance and client initialization
├── tools.py           # MCP tools (@mcp.tool decorators)
├── prompts.py         # MCP prompts (@mcp.prompt decorators)
├── resources.py       # MCP resources (@mcp.resource decorators)
├── models.py          # Pydantic models for API responses
├── config.py          # Environment configuration
├── exceptions.py      # Custom exceptions
└── utils/
    ├── client.py      # Trading212 API client
    ├── data_store.py  # SQLite cache for historical data
    ├── rate_limiter.py
    ├── retry.py
    └── hishel_config.py
```

## Environment Variables

- `TRADING212_API_KEY` - API key
- `TRADING212_API_SECRET` - API secret  
- `TRADING212_ENV` - `demo` (default) or `live`
- `ENABLE_LOCAL_CACHE` - Enable SQLite caching for historical data
- `DATABASE_PATH` - Path to SQLite database
- `CACHE_FRESHNESS_MINUTES` - Auto-sync threshold (default: 60, 0=always sync, -1=never auto-sync)

### SQLite Cache Behavior

When cache is enabled (`ENABLE_LOCAL_CACHE=true`):

- **Cache freshness**: Checked before returning cached data. Stale cache triggers auto-sync.
- **Orders**: Always full sync (API has no time-based filtering parameter)
- **Dividends/Transactions**: Incremental sync (only fetches new records since last sync)
- **Force full resync**: Use `sync_historical_data(force=True)` to clear cache and re-fetch all data

### Datetime Handling Conventions

This project uses two datetime conventions:

1. **Sync metadata timestamps** (e.g., `last_sync` in `sync_metadata` table):
   - Stored as **naive local time** via `datetime.now().isoformat()`
   - `is_cache_fresh()` defensively strips timezone info before comparison
   - Tests should use `datetime.now().isoformat()` for these values

2. **API data timestamps** (e.g., `paidOn`, `dateCreated` from Trading212 API):
   - Come from API as **timezone-aware** datetimes (typically UTC)
   - Stored in SQLite as ISO 8601 strings preserving timezone
   - Incremental sync compares datetime objects directly (not strings) for proper timezone handling
   - Tests should use `datetime(..., tzinfo=UTC)` for API-like data

The `_get_newest_record_date()` method returns ISO 8601 strings as stored (may have timezone info). Callers parse these with `datetime.fromisoformat()` and compare datetime objects directly, which handles mixed timezone representations correctly.

## Common Tasks

### Adding a New MCP Tool

1. Add function in `src/tools.py` with `@mcp.tool()` decorator
2. Add to `__all__` list
3. Tool is automatically available after server restart

### Adding a New MCP Prompt

1. Add function in `src/prompts.py` with `@mcp.prompt()` decorator
2. Add to `__all__` list
3. Prompt is automatically available after server restart
