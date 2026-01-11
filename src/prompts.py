"""MCP prompts for Trading212 data analysis.

This module provides prompt templates that can be used through the MCP protocol
for analyzing Trading212 data.
"""

import logging
from textwrap import dedent

from mcp_server import client, mcp

__all__ = ["analyse_trading212_data_prompt"]

logger = logging.getLogger(__name__)


@mcp.prompt("analyse_trading212_data")
def analyse_trading212_data_prompt() -> str:
    """
    Generate a prompt for analyzing Trading212 data.

    This prompt provides context for professional financial analysis, including
    the account's currency for proper value interpretation.

    Returns:
        A prompt string with financial analysis context.
    """
    base_prompt = dedent(
        """You are a professional financial expert analysing the user's
        financial data using Trading212. You should be extremely cautious when
        giving financial advice. Use the currency from the account info if the
        currency of the instrument is not given.

        Special currency codes:
        GBX represents pence (p) which is 1/100 of a British Pound Sterling (GBP)
        """
    )

    try:
        account_info = client.get_account_info()
        return dedent(
            f"""
            {base_prompt}
            Currency: {account_info.currencyCode}
            """
        )
    except Exception as e:
        logger.warning("Failed to fetch account info for prompt: %s", e)
        return base_prompt
