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
    "evaluate_ticker_prompt",
    "review_position_prompt",
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


@mcp.prompt("evaluate_ticker")
def evaluate_ticker_prompt(ticker: str) -> str:
    """
    Evaluate if a ticker is worth adding to your portfolio.

    This prompt validates the ticker exists on Trading212, provides current
    portfolio context, and instructs the LLM to research fundamentals via
    web search for a comprehensive portfolio fit analysis.

    Args:
        ticker: The ticker symbol to evaluate (e.g., 'AAPL', 'MSFT', 'TSLA')

    Returns:
        A prompt string with ticker evaluation context and instructions.
    """
    # Search for the instrument to validate it exists
    instruments = client.get_instruments()
    matching = [
        i for i in instruments
        if i.ticker and ticker.upper() in i.ticker.upper()
    ]

    # Find exact match or best match
    exact_match = next(
        (i for i in matching if i.ticker and i.ticker.upper() == ticker.upper()),
        None
    )
    instrument = exact_match or (matching[0] if matching else None)

    # Build instrument info section
    if instrument:
        instrument_info = dedent(f"""
            Instrument Found:
            - Ticker: {instrument.ticker}
            - Name: {instrument.name or 'N/A'}
            - Type: {instrument.type.value if instrument.type else 'N/A'}
            - Currency: {instrument.currencyCode or 'N/A'}
            - ISIN: {instrument.isin or 'N/A'}
        """).strip()
    else:
        instrument_info = f"WARNING: Ticker '{ticker}' not found on Trading212."
        if matching:
            similar = ", ".join(i.ticker or "" for i in matching[:5])
            instrument_info += f"\nSimilar tickers found: {similar}"

    # Fetch portfolio context
    try:
        account_info = client.get_account_info()
        account_cash = client.get_account_cash()
        positions = client.get_account_positions()
        currency = account_info.currencyCode

        # Build holdings summary
        holdings_summary = []
        for pos in positions[:20]:  # Limit to 20 for prompt size
            ticker_str = pos.ticker or "Unknown"
            value = (pos.currentPrice or 0) * (pos.quantity or 0)
            holdings_summary.append(f"- {ticker_str}: {value:.0f} {currency}")

        holdings_text = "\n".join(holdings_summary) if holdings_summary else "No positions"

        # Check if already held
        already_held = next(
            (p for p in positions if p.ticker and ticker.upper() in p.ticker.upper()),
            None
        )
        if already_held:
            held_info = dedent(f"""
                NOTE: You already hold this ticker!
                - Quantity: {already_held.quantity}
                - Avg Price: {already_held.averagePrice:.2f}
                - Current Price: {already_held.currentPrice:.2f}
                - P/L: {already_held.ppl:.2f} {currency}
            """).strip()
        else:
            held_info = "You do not currently hold this ticker."

        portfolio_context = dedent(f"""
            Portfolio Context:
            - Account Currency: {currency}
            - Total Portfolio Value: {account_cash.total:.2f} {currency}
            - Available Cash: {account_cash.free:.2f} {currency}
            - Number of Holdings: {len(positions)}

            {held_info}

            Current Holdings (top 20 by position):
            {holdings_text}
        """).strip()

    except Exception as e:
        logger.warning("Failed to fetch portfolio data for ticker evaluation: %s", e)
        portfolio_context = "Portfolio context unavailable."

    return dedent(f"""
        You are a financial analyst evaluating whether to add a ticker to
        the user's Trading212 portfolio.

        {instrument_info}

        {portfolio_context}

        IMPORTANT INSTRUCTIONS:

        1. **Use Web Search** to gather current information about this ticker:
           - Current P/E ratio and valuation metrics
           - Recent earnings results and guidance
           - Analyst ratings and price targets
           - Recent news and developments
           - Dividend yield (if applicable)

        2. **Assess Portfolio Fit**:
           - Does this add diversification or overlap with existing holdings?
           - What sector does it belong to vs current sector exposure?
           - Currency exposure impact (if different from account currency)
           - Would this create concentration risk?

        3. **Risk Assessment**:
           - Company fundamentals (debt, cash flow, profitability)
           - Market cap and liquidity
           - Volatility and beta
           - Any red flags from recent news?

        4. **Provide a Recommendation**:
           - BUY: Good fit, attractive valuation, adds value to portfolio
           - WAIT: Interesting but not the right time (overvalued, better entry point)
           - PASS: Poor fit, too risky, or overlaps with existing holdings

        Include specific reasoning for your recommendation.
        Be conservative - this is real money in the user's portfolio.

        Special currency codes:
        GBX represents pence (p) which is 1/100 of a British Pound Sterling (GBP)
    """).strip()


@mcp.prompt("review_position")
def review_position_prompt(ticker: str) -> str:
    """
    Review an existing position to decide whether to add more, hold, trim, or sell.

    This prompt analyzes a position you already hold, providing detailed metrics
    and context to help decide on next actions for that specific holding.

    Args:
        ticker: The ticker symbol of a position you hold (e.g., 'AAPL_US_EQ')

    Returns:
        A prompt string with position review context and instructions.
    """
    try:
        account_info = client.get_account_info()
        account_cash = client.get_account_cash()
        positions = client.get_account_positions()
        currency = account_info.currencyCode
        total_value = account_cash.total or 0.0
    except Exception as e:
        logger.warning("Failed to fetch account data for position review: %s", e)
        return f"Error: Could not fetch account data. {e}"

    # Find the position
    position = next(
        (p for p in positions if p.ticker and ticker.upper() in p.ticker.upper()),
        None
    )

    if not position:
        # List similar positions if not found
        similar = [p.ticker for p in positions if p.ticker][:10]
        return dedent(f"""
            Position '{ticker}' not found in your portfolio.

            Your current holdings include:
            {', '.join(similar)}

            Please use the exact ticker symbol (e.g., 'AAPL_US_EQ' not 'AAPL').
        """).strip()

    # Calculate position metrics
    current_value = (position.currentPrice or 0) * (position.quantity or 0)
    cost_basis = (position.averagePrice or 0) * (position.quantity or 0)
    pnl_pct = ((position.ppl or 0) / cost_basis * 100) if cost_basis > 0 else 0
    portfolio_weight = (current_value / total_value * 100) if total_value > 0 else 0

    # Determine if position is in profit or loss
    if (position.ppl or 0) > 0:
        pnl_status = "PROFIT"
    elif (position.ppl or 0) < 0:
        pnl_status = "LOSS"
    else:
        pnl_status = "BREAKEVEN"

    # Check for any open orders on this ticker
    try:
        orders = client.get_orders()
        related_orders = [o for o in orders if o.ticker == position.ticker]
        if related_orders:
            orders_info = "\n".join([
                f"- {o.type} {o.quantity} shares @ {o.limitPrice or o.stopPrice or 'market'}"
                for o in related_orders
            ])
            orders_section = f"Open Orders on this ticker:\n{orders_info}"
        else:
            orders_section = "No open orders on this ticker."
    except Exception:
        orders_section = "Could not fetch open orders."

    # Build position details
    position_details = dedent(f"""
        Position Details for {position.ticker}:
        - Quantity: {position.quantity} shares
        - Average Cost: {position.averagePrice:.2f} {currency}
        - Current Price: {position.currentPrice:.2f} {currency}
        - Cost Basis: {cost_basis:.2f} {currency}
        - Current Value: {current_value:.2f} {currency}
        - Unrealized P/L: {position.ppl:.2f} {currency} ({pnl_pct:+.1f}%)
        - FX Impact: {position.fxPpl or 0:.2f} {currency} (if applicable)
        - Portfolio Weight: {portfolio_weight:.1f}%
        - Status: {pnl_status}
        - First Purchased: {position.initialFillDate or 'Unknown'}

        {orders_section}

        Portfolio Context:
        - Total Portfolio Value: {total_value:.2f} {currency}
        - Available Cash: {account_cash.free:.2f} {currency}
        - Total Positions: {len(positions)}
    """).strip()

    return dedent(f"""
        You are a portfolio analyst reviewing an existing position to recommend
        whether to ADD MORE, HOLD, TRIM, or SELL.

        {position_details}

        IMPORTANT INSTRUCTIONS:

        1. **Use Web Search** to gather current information:
           - Recent earnings and guidance vs when position was opened
           - Any material news or developments since purchase
           - Current analyst ratings and price targets
           - Valuation metrics (P/E, forward P/E) vs historical average
           - Sector/industry trends affecting this stock

        2. **Position Analysis**:
           - Is the original investment thesis still valid?
           - How has the stock performed vs the broader market?
           - Is the position size appropriate ({portfolio_weight:.1f}% of portfolio)?
           - Cost basis of {position.averagePrice:.2f} - is averaging up/down smart here?

        3. **Risk Considerations**:
           - If in LOSS: Is this a value trap or temporary setback?
           - If in PROFIT: Take profits or let winners run?
           - Concentration risk if adding more?
           - Better opportunities elsewhere for this capital?

        4. **Provide a Recommendation**:
           - ADD MORE: Thesis intact, good entry point, not overweight
           - HOLD: Thesis intact but wait for better entry to add
           - TRIM: Take partial profits or reduce overweight position
           - SELL: Thesis broken, better opportunities elsewhere, cut losses

        Include specific reasoning and suggested action size if applicable.
        (e.g., "Add 10 more shares" or "Trim 50% of position")

        Special currency codes:
        GBX represents pence (p) which is 1/100 of a British Pound Sterling (GBP)
    """).strip()
