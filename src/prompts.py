"""MCP prompts for Trading212 data analysis.

This module provides prompt templates that can be used through the MCP protocol
for analyzing Trading212 data.
"""

import logging
from textwrap import dedent

from mcp_server import client, mcp

__all__ = [
    "analyse_trading212_data_prompt",
    "dividend_income_analysis_prompt",
    "portfolio_risk_assessment_prompt",
    "open_orders_review_prompt",
]

logger = logging.getLogger(__name__)


@mcp.prompt("analyse_trading212_data")
def analyse_trading212_data_prompt() -> str:
    """
    Generate a prompt for analyzing Trading212 data.

    This prompt provides context for professional financial analysis, including
    the account's currency and cash summary for accurate totals.

    Returns:
        A prompt string with financial analysis context.
    """
    base_prompt = dedent(
        """You are a professional financial expert analysing the user's
        financial data using Trading212. You should be extremely cautious when
        giving financial advice.

        IMPORTANT: Always use get_account_cash for accurate portfolio totals.
        Do NOT manually calculate totals from positions - use the API values:
        - invested: Total amount invested
        - ppl: Unrealized profit/loss
        - result: Realized profit/loss
        - total: Total portfolio value
        - free: Available cash
        - blocked: Cash blocked for pending orders

        Special currency codes:
        GBX represents pence (p) which is 1/100 of a British Pound Sterling (GBP)
        """
    )

    try:
        account_info = client.get_account_info()
        account_cash = client.get_account_cash()
        return dedent(
            f"""
            {base_prompt}

            Account Summary:
            - Currency: {account_info.currencyCode}
            - Total Value: {account_cash.total:.2f} {account_info.currencyCode}
            - Invested: {account_cash.invested:.2f} {account_info.currencyCode}
            - Unrealized P/L: {account_cash.ppl:.2f} {account_info.currencyCode}
            - Realized P/L: {account_cash.result:.2f} {account_info.currencyCode}
            - Free Cash: {account_cash.free:.2f} {account_info.currencyCode}
            - Blocked Cash: {account_cash.blocked:.2f} {account_info.currencyCode}
            """
        )
    except Exception as e:
        logger.warning("Failed to fetch account data for prompt: %s", e)
        return base_prompt


@mcp.prompt("dividend_income_analysis")
def dividend_income_analysis_prompt() -> str:
    """
    Generate a prompt for analyzing dividend income.

    This prompt focuses on dividend yield, income projections, and
    optimizing the portfolio for income generation.

    Returns:
        A prompt string with dividend analysis context.
    """
    try:
        account_info = client.get_account_info()
        account_cash = client.get_account_cash()
        currency = account_info.currencyCode
        portfolio_value = f"{account_cash.total:.2f} {currency}"
    except Exception as e:
        logger.warning("Failed to fetch account data for dividend prompt: %s", e)
        currency = "unknown"
        portfolio_value = "unknown"

    return dedent(f"""
        You are a dividend income specialist analyzing the user's Trading212 portfolio.
        Account currency: {currency}
        Total portfolio value: {portfolio_value}

        IMPORTANT: Use get_dividends to fetch dividend history for analysis.

        Please analyze:
        1. Total dividend income received (monthly, quarterly, annually)
        2. Current portfolio dividend yield (dividends / portfolio value)
        3. Top dividend-paying holdings
        4. Project next 12 months of expected dividend income
        5. Identify any dividend cuts or increases in holdings
        6. Suggest improvements for income optimization

        Use the dividend history, positions, and account data to provide actionable insights.
        Be conservative with projections - past dividends don't guarantee future payments.

        Special currency codes:
        GBX represents pence (p) which is 1/100 of a British Pound Sterling (GBP)
    """).strip()


@mcp.prompt("portfolio_risk_assessment")
def portfolio_risk_assessment_prompt() -> str:
    """
    Generate a prompt for assessing portfolio risk.

    This prompt analyzes concentration, currency exposure, diversification,
    and identifies high-risk positions.

    Returns:
        A prompt string with risk assessment context.
    """
    try:
        account_info = client.get_account_info()
        account_cash = client.get_account_cash()
        currency = account_info.currencyCode
        total_value = account_cash.total
    except Exception as e:
        logger.warning("Failed to fetch account data for risk prompt: %s", e)
        currency = "unknown"
        total_value = None

    total_str = f"{total_value:.2f} {currency}" if total_value else "unknown"

    return dedent(f"""
        You are a risk analyst evaluating the user's Trading212 portfolio.
        Account currency: {currency}
        Total portfolio value: {total_str}

        IMPORTANT: Use get_positions for holdings and get_account_cash for totals.

        Please analyze:
        1. **Concentration Risk**: Identify positions >10% of portfolio value
        2. **Sector Exposure**: Group holdings by sector/industry
        3. **Currency Risk**: Calculate USD/EUR/GBP exposure and FX P/L impact
        4. **Near-Zero Positions**: Flag holdings that have lost >90% of value
        5. **Volatility Assessment**: Identify high-beta or speculative holdings
        6. **Diversification Score**: Rate overall diversification (1-10)

        Provide specific, actionable recommendations to reduce risk.
        Be direct about problematic positions but avoid specific buy/sell recommendations.

        Special currency codes:
        GBX represents pence (p) which is 1/100 of a British Pound Sterling (GBP)
    """).strip()


@mcp.prompt("open_orders_review")
def open_orders_review_prompt() -> str:
    """
    Generate a prompt for reviewing open/pending orders.

    This prompt evaluates whether open limit orders are still relevant
    based on current prices, market conditions, and position sizes.

    Returns:
        A prompt string with order review context.
    """
    try:
        account_info = client.get_account_info()
        account_cash = client.get_account_cash()
        currency = account_info.currencyCode
        blocked = account_cash.blocked
    except Exception as e:
        logger.warning("Failed to fetch account data for orders prompt: %s", e)
        currency = "unknown"
        blocked = None

    blocked_str = f"{blocked:.2f} {currency}" if blocked else "unknown"

    return dedent(f"""
        You are a trading analyst reviewing the user's open/pending orders on Trading212.
        Account currency: {currency}
        Blocked cash (for pending orders): {blocked_str}

        IMPORTANT: Use get_orders to fetch open orders and get_positions for context.

        Fetch and analyze ALL open orders against current positions and prices.

        For each order, evaluate:
        1. **Price Relevance**: Compare limit price to current market price
           - How far is the limit from current price (% difference)?
           - Is it realistic to expect this price in near term?

        2. **Position Context**: Check if user already holds this stock
           - For SELL orders: Does user have enough shares?
           - For BUY orders: Would this create concentration risk?

        3. **Order Age Indicators**: Look for signs of stale orders
           - Limit prices that are unrealistically far from market
           - Multiple orders on same ticker at different prices

        4. **Problematic Orders**: Flag orders that should be reviewed
           - SELL orders on near-zero positions (penny stocks)
           - BUY orders for positions already at target allocation
           - Limit prices that may never be reached

        Provide a summary table with:
        | Ticker | Type | Limit | Current | Gap% | Recommendation |

        Categorize orders as:
        - ✅ KEEP: Reasonable and likely to execute
        - ⚠️ REVIEW: Consider adjusting price or cancelling
        - ❌ CANCEL: Unrealistic or no longer relevant

        Be practical - some limit orders are intentionally set far from market
        to catch volatility spikes. Focus on clearly problematic orders.

        Special currency codes:
        GBX represents pence (p) which is 1/100 of a British Pound Sterling (GBP)
    """).strip()
