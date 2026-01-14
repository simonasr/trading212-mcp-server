"""Tests for MCP prompts."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from prompts import (
    analyse_trading212_data_prompt,
    dividend_income_analysis_prompt,
    open_orders_review_prompt,
    portfolio_risk_assessment_prompt,
)


class TestPromptExports:
    """Tests for prompt module exports."""

    def test_all_prompts_are_exported(self) -> None:
        """All prompts should be in __all__."""
        from prompts import __all__

        expected_prompts = [
            "analyse_trading212_data_prompt",
            "dividend_income_analysis_prompt",
            "portfolio_risk_assessment_prompt",
            "open_orders_review_prompt",
        ]

        for prompt in expected_prompts:
            assert prompt in __all__, f"Prompt {prompt} not in __all__"


class TestAnalyseDataPrompt:
    """Tests for analyse_trading212_data_prompt."""

    def test_returns_string(self) -> None:
        """Should return a string."""
        result = analyse_trading212_data_prompt()
        assert isinstance(result, str)

    def test_contains_financial_context(self) -> None:
        """Should contain financial analysis context."""
        result = analyse_trading212_data_prompt()
        assert "financial" in result.lower()
        assert "GBX" in result


class TestDividendIncomeAnalysisPrompt:
    """Tests for dividend_income_analysis_prompt."""

    def test_returns_string(self) -> None:
        """Should return a string."""
        result = dividend_income_analysis_prompt()
        assert isinstance(result, str)

    def test_contains_dividend_context(self) -> None:
        """Should contain dividend analysis context."""
        result = dividend_income_analysis_prompt()
        assert "dividend" in result.lower()
        assert "income" in result.lower()

    def test_contains_analysis_points(self) -> None:
        """Should contain key analysis points."""
        result = dividend_income_analysis_prompt()
        assert "yield" in result.lower()
        assert "12 months" in result


class TestPortfolioRiskAssessmentPrompt:
    """Tests for portfolio_risk_assessment_prompt."""

    def test_returns_string(self) -> None:
        """Should return a string."""
        result = portfolio_risk_assessment_prompt()
        assert isinstance(result, str)

    def test_contains_risk_context(self) -> None:
        """Should contain risk assessment context."""
        result = portfolio_risk_assessment_prompt()
        assert "risk" in result.lower()
        assert "diversification" in result.lower()

    def test_contains_risk_categories(self) -> None:
        """Should contain risk category analysis."""
        result = portfolio_risk_assessment_prompt()
        assert "Concentration" in result
        assert "Currency" in result
        assert "Sector" in result


class TestOpenOrdersReviewPrompt:
    """Tests for open_orders_review_prompt."""

    def test_returns_string(self) -> None:
        """Should return a string."""
        result = open_orders_review_prompt()
        assert isinstance(result, str)

    def test_contains_orders_context(self) -> None:
        """Should contain order review context."""
        result = open_orders_review_prompt()
        assert "order" in result.lower()
        assert "limit" in result.lower()

    def test_contains_recommendation_categories(self) -> None:
        """Should contain recommendation categories."""
        result = open_orders_review_prompt()
        assert "KEEP" in result
        assert "REVIEW" in result
        assert "CANCEL" in result

    def test_contains_analysis_criteria(self) -> None:
        """Should contain analysis criteria."""
        result = open_orders_review_prompt()
        assert "Price Relevance" in result
        assert "Position Context" in result
