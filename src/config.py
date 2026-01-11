"""Configuration management for Trading212 MCP server.

This module loads and provides access to configuration values from environment
variables.
"""

import os

from dotenv import find_dotenv, load_dotenv

__all__ = [
    "TRADING212_API_KEY",
    "TRADING212_API_SECRET",
    "ENVIRONMENT",
    "TRANSPORT",
]

load_dotenv(find_dotenv())

# Trading212 API credentials
TRADING212_API_KEY: str | None = os.getenv("TRADING212_API_KEY")
TRADING212_API_SECRET: str | None = os.getenv("TRADING212_API_SECRET")

# Environment: "demo" or "live"
ENVIRONMENT: str = os.getenv("ENVIRONMENT", "demo")

# MCP transport: "stdio" or "http"
TRANSPORT: str = os.getenv("TRANSPORT", "stdio")
