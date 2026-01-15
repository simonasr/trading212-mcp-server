"""Configuration management for Trading212 MCP server.

This module loads and provides access to configuration values from environment
variables.
"""

import logging
import os

from dotenv import find_dotenv, load_dotenv

logger = logging.getLogger(__name__)

__all__ = [
    "TRADING212_API_KEY",
    "TRADING212_API_SECRET",
    "ENVIRONMENT",
    "TRANSPORT",
    "ENABLE_LOCAL_CACHE",
    "DATABASE_PATH",
    "CACHE_FRESHNESS_MINUTES",
]

load_dotenv(find_dotenv())

# Trading212 API credentials
TRADING212_API_KEY: str | None = os.getenv("TRADING212_API_KEY")
TRADING212_API_SECRET: str | None = os.getenv("TRADING212_API_SECRET")

# Environment: "demo" or "live"
ENVIRONMENT: str = os.getenv("ENVIRONMENT", "demo")

# MCP transport: "stdio" or "http"
TRANSPORT: str = os.getenv("TRANSPORT", "stdio")

# Local cache settings (opt-in)
# Set ENABLE_LOCAL_CACHE=true to enable SQLite caching for historical data
ENABLE_LOCAL_CACHE: bool = os.getenv("ENABLE_LOCAL_CACHE", "false").lower() == "true"

# Path to SQLite database file
DATABASE_PATH: str = os.getenv("DATABASE_PATH", "./data/trading212.db")

# Cache freshness threshold in minutes
# If cache was synced within this time, skip API calls and use cached data
# Set to 0 to always sync, -1 to never auto-sync (manual only)
_DEFAULT_FRESHNESS_MINUTES = 60


def _parse_freshness_minutes() -> int:
    """Parse CACHE_FRESHNESS_MINUTES with error handling."""
    value = os.getenv("CACHE_FRESHNESS_MINUTES", str(_DEFAULT_FRESHNESS_MINUTES))
    try:
        return int(value)
    except ValueError:
        logger.warning(
            "Invalid CACHE_FRESHNESS_MINUTES value '%s', using default %d",
            value,
            _DEFAULT_FRESHNESS_MINUTES,
        )
        return _DEFAULT_FRESHNESS_MINUTES


CACHE_FRESHNESS_MINUTES: int = _parse_freshness_minutes()
