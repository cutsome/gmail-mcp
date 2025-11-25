"""Main entry point for MCP Gmail server"""

import asyncio
import json
import logging
import sys
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from .gmail_auth import GmailAuth
from .gmail_client import GmailClient

# Logging configuration
logging.basicConfig(
    filename="mcp_gmail_server.log",
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Gmail authentication and client instances
gmail_auth = GmailAuth()
credentials = gmail_auth.get_credentials()
gmail_client = GmailClient(credentials)

# MCP server instance
server = Server("mcp-gmail-server")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """Return a list of available tools"""
    return [
        Tool(
            name="gmail.search_messages",
            description="Search Gmail and retrieve a list of message IDs. Supports AND conditions (space-separated) and OR conditions (using 'OR' keyword).",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Gmail search query. Examples: 'after:2025/1/1', 'from:example@gmail.com'. AND conditions: space-separated (e.g., 'from:example@gmail.com subject:test'). OR conditions: use 'OR' keyword (e.g., 'from:example@gmail.com OR from:another@gmail.com').",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results (default: 100)",
                        "default": 100,
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="gmail.get_message",
            description="Retrieve detailed information for the specified message ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "message_id": {
                        "type": "string",
                        "description": "ID of the message to retrieve",
                    },
                },
                "required": ["message_id"],
            },
        ),
        Tool(
            name="gmail.get_messages_batch",
            description="Retrieve detailed information for multiple messages using batch request. Efficient for retrieving many messages at once.",
            inputSchema={
                "type": "object",
                "properties": {
                    "message_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of message IDs to retrieve",
                    },
                },
                "required": ["message_ids"],
            },
        ),
        Tool(
            name="gmail.get_attachments",
            description="Retrieve a list of attachments for the specified message.",
            inputSchema={
                "type": "object",
                "properties": {
                    "message_id": {
                        "type": "string",
                        "description": "ID of the message to retrieve attachments from",
                    },
                },
                "required": ["message_id"],
            },
        ),
        Tool(
            name="gmail.get_attachment_data",
            description="Retrieve attachment data for the specified attachment (base64 encoded).",
            inputSchema={
                "type": "object",
                "properties": {
                    "message_id": {
                        "type": "string",
                        "description": "ID of the message containing the attachment",
                    },
                    "attachment_id": {
                        "type": "string",
                        "description": "ID of the attachment to retrieve",
                    },
                },
                "required": ["message_id", "attachment_id"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any] | None) -> list[TextContent]:
    """Handle tool calls"""
    if arguments is None:
        arguments = {}

    try:
        if name == "gmail.search_messages":
            query = arguments.get("query", "")
            max_results = arguments.get("max_results", 100)
            results = gmail_client.search_messages(query, max_results)
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        [r.model_dump(by_alias=True) for r in results],
                        ensure_ascii=False,
                        indent=2,
                    ),
                )
            ]

        elif name == "gmail.get_message":
            message_id = arguments.get("message_id", "")
            if not message_id:
                raise ValueError("message_id is required")
            result = gmail_client.get_message(message_id)
            return [
                TextContent(
                    type="text",
                    text=result.model_dump_json(by_alias=True, indent=2),
                )
            ]

        elif name == "gmail.get_messages_batch":
            message_ids = arguments.get("message_ids", [])
            if not message_ids:
                raise ValueError("message_ids is required and must not be empty")
            if not isinstance(message_ids, list):
                raise ValueError("message_ids must be a list")
            results = gmail_client.get_messages_batch(message_ids)
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        [r.model_dump(by_alias=True) for r in results],
                        ensure_ascii=False,
                        indent=2,
                    ),
                )
            ]

        elif name == "gmail.get_attachments":
            message_id = arguments.get("message_id", "")
            if not message_id:
                raise ValueError("message_id is required")
            results = gmail_client.get_attachments(message_id)
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        [r.model_dump() for r in results],
                        ensure_ascii=False,
                        indent=2,
                    ),
                )
            ]

        elif name == "gmail.get_attachment_data":
            message_id = arguments.get("message_id", "")
            attachment_id = arguments.get("attachment_id", "")
            if not message_id or not attachment_id:
                raise ValueError("message_id and attachment_id are required")
            result = gmail_client.get_attachment_data(message_id, attachment_id)
            return [
                TextContent(
                    type="text",
                    text=result.model_dump_json(indent=2),
                )
            ]

        else:
            raise ValueError(f"Unknown tool: {name}")

    except Exception as e:
        logger.error(f"Tool call error: {e}", exc_info=True)
        error_msg = json.dumps({"error": str(e)}, ensure_ascii=False)
        return [TextContent(type="text", text=error_msg)]


async def main() -> None:
    """Start the MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def run() -> None:
    """Start the MCP server (synchronous wrapper for entry point)"""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down server")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    run()
