# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MCP (Model Context Protocol) server that wraps the Gmail API. Provides 4 tools for searching and retrieving Gmail messages and attachments.

## Development Commands

```bash
# Install dependencies
uv sync

# Install with dev dependencies
uv sync --extra dev

# Run MCP server
uv run mcp-gmail-server

# Run tests
uv run pytest
uv run pytest -v                    # verbose
uv run pytest tests/test_models.py  # single file

# Test coverage
uv run pytest --cov=mcp_gmail_server --cov-report=html --cov-report=term-missing

# Lint & format (ruff)
uv run ruff check mcp_gmail_server tests
uv run ruff format mcp_gmail_server tests

# Debug with MCP Inspector (browser UI)
npx @modelcontextprotocol/inspector uv run mcp-gmail-server
```

## Architecture

```
mcp_gmail_server/
├── main.py         # MCP server entry point, tool definitions and handlers
├── gmail_auth.py   # OAuth2 authentication (GmailAuth class)
├── gmail_client.py # Gmail API wrapper (GmailClient class)
├── models.py       # Pydantic models for API responses
└── utils.py        # Base64 decoding, date parsing, RFC2047 filename decoding
```

### Key Components

- **main.py**: Registers 4 MCP tools (`gmail.search_messages`, `gmail.get_message`, `gmail.get_attachments`, `gmail.get_attachment_data`) via `@server.list_tools()` and `@server.call_tool()` decorators
- **GmailAuth**: Handles OAuth2 flow with automatic token refresh. Looks for `client_secret.json` in project root or via `GOOGLE_CLIENT_SECRET_PATH` env var
- **GmailClient**: Wraps `googleapiclient` calls, returns typed Pydantic models
- **MessagePayload**: Recursive Pydantic model that handles multipart MIME structure for body text and attachment extraction

### Data Flow

1. MCP client calls tool → `main.py:call_tool()`
2. `GmailClient` method called → Gmail API request
3. Response parsed into Pydantic models → JSON serialized back to client

## Environment Variables

- `GOOGLE_CLIENT_SECRET_PATH`: Path to OAuth credentials file (default: `./client_secret.json`)
- `GOOGLE_TOKEN_PATH`: Path to store OAuth token (default: `./token.json`)

## Testing

Tests use `pytest-asyncio` with `asyncio_mode = "auto"`. Test files mirror source structure in `tests/` directory.
