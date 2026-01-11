"""MCP server setup for Trading212.

This module initializes the FastMCP server and Trading212 client that are
shared across tools, resources, and prompts.
"""

from dotenv import find_dotenv, load_dotenv
from mcp.server.fastmcp import FastMCP

from utils.client import Trading212Client

__all__ = ["mcp", "client"]

load_dotenv(find_dotenv())

mcp = FastMCP(
    name="Trading212",
    dependencies=["hishel", "pydantic"],
    stateless_http=True,
    host="127.0.0.1",
    port=8000,
)

client = Trading212Client()
