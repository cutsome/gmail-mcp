.PHONY: help install install-dev test test-verbose test-coverage lint format clean run debug-inspector

# Default target
.DEFAULT_GOAL := help

# Python and uv paths (adjust as needed)
PYTHON := python
UV := uv

# Project name
PROJECT_NAME := mcp-gmail-server

help: ## Display this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	$(UV) sync

install-dev: ## Install dependencies including dev dependencies
	$(UV) sync --extra dev

test: ## Run tests
	$(UV) run pytest

test-verbose: ## Run tests with verbose output
	$(UV) run pytest -v

test-coverage: ## Run tests with coverage
	$(UV) run pytest --cov=mcp_gmail_server --cov-report=html --cov-report=term-missing

lint: ## Run linter (using ruff)
	$(UV) run ruff check mcp_gmail_server tests

format: ## Format code (using ruff)
	$(UV) run ruff format mcp_gmail_server tests

format-check: ## Check formatting (without making changes)
	$(UV) run ruff format --check mcp_gmail_server tests

clean: ## Remove temporary files and caches
	find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -r {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -r {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -r {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -r {} + 2>/dev/null || true
	@echo "Cleanup completed"

run: ## Run MCP server
	$(UV) run mcp-gmail-server

debug: ## Debug server with MCP Inspector
	@echo "Starting MCP Inspector..."
	@echo "Browser will open automatically."
	npx @modelcontextprotocol/inspector $(UV) run mcp-gmail-server

check: lint format-check test ## Run linter, format check, and tests

ci: install-dev check ## For CI: install dependencies, check, and run tests
