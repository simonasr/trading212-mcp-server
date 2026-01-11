"""Entry point for the Trading212 MCP server.

This module starts the MCP server with the configured transport.
"""

import os

from dotenv import find_dotenv, load_dotenv

import prompts  # noqa: F401
import resources  # noqa: F401

# Import tools, prompts, and resources to register them with the MCP server
import tools  # noqa: F401
from mcp_server import mcp

load_dotenv(find_dotenv())


def main() -> None:
    """Start the Trading212 MCP server."""
    transport = os.getenv("TRANSPORT", "stdio")
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
