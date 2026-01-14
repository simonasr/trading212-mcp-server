.PHONY: install dev lint format typecheck test check clean help

# Default target
help:
	@echo "Trading212 MCP Server - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install     Install production dependencies"
	@echo "  make dev         Install all dependencies (including dev)"
	@echo ""
	@echo "Quality:"
	@echo "  make lint        Run ruff linter"
	@echo "  make format      Run ruff formatter (auto-fix)"
	@echo "  make format-check Check formatting without fixing"
	@echo "  make typecheck   Run mypy type checker"
	@echo ""
	@echo "Testing:"
	@echo "  make test        Run all tests"
	@echo "  make test-cov    Run tests with coverage report"
	@echo ""
	@echo "All-in-one:"
	@echo "  make check       Run all checks (lint, format-check, typecheck, test)"
	@echo "  make ci          Run CI checks (same as check)"
	@echo ""
	@echo "Utilities:"
	@echo "  make clean       Remove cache files and build artifacts"
	@echo "  make run         Run the MCP server"

# Setup
install:
	uv sync

dev:
	uv sync --all-extras

# Linting
lint:
	uv run ruff check src tests

lint-fix:
	uv run ruff check src tests --fix

# Formatting
format:
	uv run ruff format src tests

format-check:
	uv run ruff format --check src tests

# Type checking
typecheck:
	uv run mypy src

# Testing
test:
	uv run pytest tests/ -v --tb=short

test-cov:
	uv run pytest tests/ --cov=src --cov-report=term-missing --cov-report=html

test-fast:
	uv run pytest tests/ -x -q

# All checks (for CI or pre-commit)
check: lint format-check typecheck test
	@echo "✅ All checks passed!"

ci: check

# Run the server
run:
	uv run src/server.py

# Clean up
clean:
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf coverage.xml
	rm -rf dist
	rm -rf build
	rm -rf *.egg-info
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "🧹 Cleaned up cache files"
