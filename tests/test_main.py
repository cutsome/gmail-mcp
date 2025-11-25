"""Unit tests for main.py"""

import json
from unittest.mock import patch

import pytest

# Import module to mock module-level variables
import mcp_gmail_server.main as main_module


class TestListTools:
    """Tests for list_tools function"""

    @pytest.mark.asyncio
    async def test_list_tools_returns_all_tools(self):
        """All tools should be returned"""
        tools = await main_module.list_tools()

        assert len(tools) == 5

        tool_names = [tool.name for tool in tools]
        assert "gmail.search_messages" in tool_names
        assert "gmail.get_message" in tool_names
        assert "gmail.get_messages_batch" in tool_names
        assert "gmail.get_attachments" in tool_names
        assert "gmail.get_attachment_data" in tool_names

    @pytest.mark.asyncio
    async def test_list_tools_search_messages_schema(self):
        """gmail.search_messages schema should be correct"""
        tools = await main_module.list_tools()
        search_tool = next(t for t in tools if t.name == "gmail.search_messages")

        assert "query" in search_tool.inputSchema["properties"]
        assert "max_results" in search_tool.inputSchema["properties"]
        assert "query" in search_tool.inputSchema["required"]
        assert search_tool.inputSchema["properties"]["max_results"]["default"] == 100

    @pytest.mark.asyncio
    async def test_list_tools_get_message_schema(self):
        """gmail.get_message schema should be correct"""
        tools = await main_module.list_tools()
        get_message_tool = next(t for t in tools if t.name == "gmail.get_message")

        assert "message_id" in get_message_tool.inputSchema["properties"]
        assert "message_id" in get_message_tool.inputSchema["required"]

    @pytest.mark.asyncio
    async def test_list_tools_get_attachments_schema(self):
        """gmail.get_attachments schema should be correct"""
        tools = await main_module.list_tools()
        get_attachments_tool = next(
            t for t in tools if t.name == "gmail.get_attachments"
        )

        assert "message_id" in get_attachments_tool.inputSchema["properties"]
        assert "message_id" in get_attachments_tool.inputSchema["required"]

    @pytest.mark.asyncio
    async def test_list_tools_get_attachment_data_schema(self):
        """gmail.get_attachment_data schema should be correct"""
        tools = await main_module.list_tools()
        get_attachment_data_tool = next(
            t for t in tools if t.name == "gmail.get_attachment_data"
        )

        assert "message_id" in get_attachment_data_tool.inputSchema["properties"]
        assert "attachment_id" in get_attachment_data_tool.inputSchema["properties"]
        assert "message_id" in get_attachment_data_tool.inputSchema["required"]
        assert "attachment_id" in get_attachment_data_tool.inputSchema["required"]


class TestCallTool:
    """Tests for call_tool function"""

    @pytest.mark.asyncio
    @patch.object(main_module, "gmail_client")
    async def test_call_tool_search_messages(self, mock_gmail_client):
        """gmail.search_messages tool should work correctly"""
        from mcp_gmail_server.models import MessageSearchResult

        mock_result = [
            MessageSearchResult(message_id="msg1", thread_id="thread1"),
            MessageSearchResult(message_id="msg2", thread_id="thread2"),
        ]
        mock_gmail_client.search_messages.return_value = mock_result

        arguments = {"query": "test query", "max_results": 10}
        result = await main_module.call_tool("gmail.search_messages", arguments)

        assert len(result) == 1
        assert result[0].type == "text"
        data = json.loads(result[0].text)
        assert len(data) == 2
        assert data[0]["message_id"] == "msg1"
        mock_gmail_client.search_messages.assert_called_once_with("test query", 10)

    @pytest.mark.asyncio
    @patch.object(main_module, "gmail_client")
    async def test_call_tool_search_messages_default_max_results(
        self, mock_gmail_client
    ):
        """Should use default value when max_results is not specified"""
        mock_gmail_client.search_messages.return_value = []

        arguments = {"query": "test query"}
        await main_module.call_tool("gmail.search_messages", arguments)

        mock_gmail_client.search_messages.assert_called_once_with("test query", 100)

    @pytest.mark.asyncio
    @patch.object(main_module, "gmail_client")
    async def test_call_tool_get_message(self, mock_gmail_client):
        """gmail.get_message tool should work correctly"""
        from mcp_gmail_server.models import Message

        mock_message = Message(
            message_id="msg1",
            thread_id="thread1",
            subject="Test",
            from_="sender@example.com",
            to="receiver@example.com",
            received_at="2025-01-01T12:00:00+09:00",
            body_text="Test body",
        )
        mock_gmail_client.get_message.return_value = mock_message

        arguments = {"message_id": "msg1"}
        result = await main_module.call_tool("gmail.get_message", arguments)

        assert len(result) == 1
        assert result[0].type == "text"
        data = json.loads(result[0].text)
        assert data["message_id"] == "msg1"
        assert data["subject"] == "Test"
        mock_gmail_client.get_message.assert_called_once_with("msg1")

    @pytest.mark.asyncio
    @patch.object(main_module, "gmail_client")
    async def test_call_tool_get_message_missing_message_id(self, mock_gmail_client):
        """Should raise ValueError when message_id is not specified"""
        arguments = {}
        result = await main_module.call_tool("gmail.get_message", arguments)

        assert len(result) == 1
        assert result[0].type == "text"
        error_data = json.loads(result[0].text)
        assert "error" in error_data
        assert "message_id is required" in error_data["error"]

    @pytest.mark.asyncio
    @patch.object(main_module, "gmail_client")
    async def test_call_tool_get_attachments(self, mock_gmail_client):
        """gmail.get_attachments tool should work correctly"""
        from mcp_gmail_server.models import Attachment

        mock_attachments = [
            Attachment(
                attachment_id="att1",
                file_name="test.pdf",
                mime_type="application/pdf",
                size=1024,
            )
        ]
        mock_gmail_client.get_attachments.return_value = mock_attachments

        arguments = {"message_id": "msg1"}
        result = await main_module.call_tool("gmail.get_attachments", arguments)

        assert len(result) == 1
        assert result[0].type == "text"
        data = json.loads(result[0].text)
        assert len(data) == 1
        assert data[0]["attachment_id"] == "att1"
        mock_gmail_client.get_attachments.assert_called_once_with("msg1")

    @pytest.mark.asyncio
    @patch.object(main_module, "gmail_client")
    async def test_call_tool_get_attachment_data(self, mock_gmail_client):
        """gmail.get_attachment_data tool should work correctly"""
        from mcp_gmail_server.models import AttachmentData

        mock_attachment_data = AttachmentData(
            attachment_id="att1",
            data="dGVzdCBkYXRh",
            size=9,
        )
        mock_gmail_client.get_attachment_data.return_value = mock_attachment_data

        arguments = {"message_id": "msg1", "attachment_id": "att1"}
        result = await main_module.call_tool("gmail.get_attachment_data", arguments)

        assert len(result) == 1
        assert result[0].type == "text"
        data = json.loads(result[0].text)
        assert data["attachment_id"] == "att1"
        assert data["data"] == "dGVzdCBkYXRh"
        mock_gmail_client.get_attachment_data.assert_called_once_with("msg1", "att1")

    @pytest.mark.asyncio
    @patch.object(main_module, "gmail_client")
    async def test_call_tool_get_attachment_data_missing_params(
        self, mock_gmail_client
    ):
        """Should raise ValueError when message_id or attachment_id is not specified"""
        arguments = {"message_id": "msg1"}
        result = await main_module.call_tool("gmail.get_attachment_data", arguments)

        assert len(result) == 1
        assert result[0].type == "text"
        error_data = json.loads(result[0].text)
        assert "error" in error_data
        assert "message_id and attachment_id are required" in error_data["error"]

    @pytest.mark.asyncio
    async def test_call_tool_unknown_tool(self):
        """Should raise ValueError for unknown tool name"""
        arguments = {}
        result = await main_module.call_tool("unknown_tool", arguments)

        assert len(result) == 1
        assert result[0].type == "text"
        error_data = json.loads(result[0].text)
        assert "error" in error_data
        assert "Unknown tool" in error_data["error"]

    @pytest.mark.asyncio
    @patch.object(main_module, "gmail_client")
    async def test_call_tool_none_arguments(self, mock_gmail_client):
        """Should treat None arguments as empty dictionary"""
        mock_gmail_client.search_messages.return_value = []

        result = await main_module.call_tool("gmail.search_messages", None)

        # Error should occur (query is required)
        assert len(result) == 1
        assert result[0].type == "text"

    @pytest.mark.asyncio
    @patch.object(main_module, "gmail_client")
    @patch.object(main_module, "logger")
    async def test_call_tool_exception_handling(self, mock_logger, mock_gmail_client):
        """Should return error message when exception occurs"""
        mock_gmail_client.get_message.side_effect = RuntimeError("API Error")

        arguments = {"message_id": "msg1"}
        result = await main_module.call_tool("gmail.get_message", arguments)

        assert len(result) == 1
        assert result[0].type == "text"
        error_data = json.loads(result[0].text)
        assert "error" in error_data
        assert "API Error" in error_data["error"]
        mock_logger.error.assert_called_once()
