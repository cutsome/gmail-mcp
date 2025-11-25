"""Unit tests for gmail_client.py"""

from unittest.mock import Mock, patch

import pytest
from googleapiclient.errors import HttpError

from mcp_gmail_server.gmail_client import GmailClient
from mcp_gmail_server.models import (
    Attachment,
    AttachmentData,
    Message,
    MessageSearchResult,
)


class TestGmailClientInit:
    """Tests for GmailClient.__init__"""

    @patch("mcp_gmail_server.gmail_client.build")
    def test_init_builds_service(self, mock_build):
        """Should build service correctly"""
        mock_credentials = Mock()
        mock_service = Mock()
        mock_build.return_value = mock_service

        client = GmailClient(mock_credentials)

        assert client.service == mock_service
        mock_build.assert_called_once_with("gmail", "v1", credentials=mock_credentials)


class TestGmailClientSearchMessages:
    """Tests for GmailClient.search_messages"""

    def test_search_messages_success(self):
        """Message search should succeed"""
        mock_service = Mock()
        mock_messages_list = Mock()
        mock_messages_list.execute.return_value = {
            "messages": [
                {"id": "msg1", "threadId": "thread1"},
                {"id": "msg2", "threadId": "thread2"},
            ]
        }
        mock_service.users.return_value.messages.return_value.list.return_value = (
            mock_messages_list
        )

        client = GmailClient(Mock())
        client.service = mock_service

        results = client.search_messages("test query", max_results=10)

        assert len(results) == 2
        assert isinstance(results[0], MessageSearchResult)
        assert results[0].message_id == "msg1"
        assert results[0].thread_id == "thread1"
        assert results[1].message_id == "msg2"
        assert results[1].thread_id == "thread2"

        mock_service.users.return_value.messages.return_value.list.assert_called_once_with(
            userId="me", q="test query", maxResults=10
        )

    def test_search_messages_empty_result(self):
        """Should return empty list when search results are empty"""
        mock_service = Mock()
        mock_messages_list = Mock()
        mock_messages_list.execute.return_value = {"messages": []}
        mock_service.users.return_value.messages.return_value.list.return_value = (
            mock_messages_list
        )

        client = GmailClient(Mock())
        client.service = mock_service

        results = client.search_messages("test query")

        assert len(results) == 0
        assert isinstance(results, list)

    def test_search_messages_without_thread_id(self):
        """Should use empty string when threadId is not present"""
        mock_service = Mock()
        mock_messages_list = Mock()
        mock_messages_list.execute.return_value = {"messages": [{"id": "msg1"}]}
        mock_service.users.return_value.messages.return_value.list.return_value = (
            mock_messages_list
        )

        client = GmailClient(Mock())
        client.service = mock_service

        results = client.search_messages("test query")

        assert len(results) == 1
        assert results[0].thread_id == ""

    def test_search_messages_http_error(self):
        """Should raise RuntimeError when HttpError occurs"""
        mock_service = Mock()
        mock_messages_list = Mock()
        mock_error = HttpError(Mock(status=500), b"Error")
        mock_messages_list.execute.side_effect = mock_error
        mock_service.users.return_value.messages.return_value.list.return_value = (
            mock_messages_list
        )

        client = GmailClient(Mock())
        client.service = mock_service

        with pytest.raises(RuntimeError) as exc_info:
            client.search_messages("test query")

        assert "Gmail API error" in str(exc_info.value)


class TestGmailClientGetMessage:
    """Tests for GmailClient.get_message"""

    @patch("mcp_gmail_server.gmail_client.MessagePayload")
    @patch("mcp_gmail_server.gmail_client.parse_date")
    def test_get_message_success(self, mock_parse_date, mock_message_payload_class):
        """Message retrieval should succeed"""
        mock_service = Mock()
        mock_message_get = Mock()
        mock_message_get.execute.return_value = {
            "id": "msg1",
            "threadId": "thread1",
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Test Subject"},
                    {"name": "From", "value": "sender@example.com"},
                    {"name": "To", "value": "receiver@example.com"},
                    {"name": "Date", "value": "Mon, 1 Jan 2025 12:00:00 +0900"},
                ],
                "mimeType": "text/plain",
                "body": {"data": "dGVzdA=="},
            },
        }
        mock_service.users.return_value.messages.return_value.get.return_value = (
            mock_message_get
        )

        mock_payload = Mock()
        mock_payload.extract_body_text.return_value = "test body"
        mock_message_payload_class.model_validate.return_value = mock_payload

        mock_parse_date.return_value = "2025-01-01T12:00:00+09:00"

        client = GmailClient(Mock())
        client.service = mock_service

        result = client.get_message("msg1")

        assert isinstance(result, Message)
        assert result.message_id == "msg1"
        assert result.thread_id == "thread1"
        assert result.subject == "Test Subject"
        assert result.from_ == "sender@example.com"
        assert result.to == "receiver@example.com"
        assert result.body_text == "test body"

        mock_service.users.return_value.messages.return_value.get.assert_called_once_with(
            userId="me", id="msg1", format="full"
        )

    def test_get_message_http_error(self):
        """Should raise RuntimeError when HttpError occurs"""
        mock_service = Mock()
        mock_message_get = Mock()
        mock_error = HttpError(Mock(status=404), b"Not Found")
        mock_message_get.execute.side_effect = mock_error
        mock_service.users.return_value.messages.return_value.get.return_value = (
            mock_message_get
        )

        client = GmailClient(Mock())
        client.service = mock_service

        with pytest.raises(RuntimeError) as exc_info:
            client.get_message("invalid_id")

        assert "Gmail API error" in str(exc_info.value)


class TestGmailClientGetAttachments:
    """Tests for GmailClient.get_attachments"""

    @patch("mcp_gmail_server.gmail_client.MessagePayload")
    def test_get_attachments_success(self, mock_message_payload_class):
        """Attachment list retrieval should succeed"""
        mock_service = Mock()
        mock_message_get = Mock()
        mock_message_get.execute.return_value = {
            "payload": {
                "mimeType": "multipart/mixed",
                "parts": [],
            }
        }
        mock_service.users.return_value.messages.return_value.get.return_value = (
            mock_message_get
        )

        mock_payload = Mock()
        mock_attachment = Attachment(
            attachment_id="att1",
            file_name="test.pdf",
            mime_type="application/pdf",
            size=1024,
        )
        mock_payload.extract_attachments.return_value = [mock_attachment]
        mock_message_payload_class.model_validate.return_value = mock_payload

        client = GmailClient(Mock())
        client.service = mock_service

        results = client.get_attachments("msg1")

        assert len(results) == 1
        assert isinstance(results[0], Attachment)
        assert results[0].attachment_id == "att1"
        assert results[0].file_name == "test.pdf"

    def test_get_attachments_http_error(self):
        """Should raise RuntimeError when HttpError occurs"""
        mock_service = Mock()
        mock_message_get = Mock()
        mock_error = HttpError(Mock(status=500), b"Error")
        mock_message_get.execute.side_effect = mock_error
        mock_service.users.return_value.messages.return_value.get.return_value = (
            mock_message_get
        )

        client = GmailClient(Mock())
        client.service = mock_service

        with pytest.raises(RuntimeError) as exc_info:
            client.get_attachments("msg1")

        assert "Gmail API error" in str(exc_info.value)


class TestGmailClientGetAttachmentData:
    """Tests for GmailClient.get_attachment_data"""

    def test_get_attachment_data_success(self):
        """Attachment data retrieval should succeed"""
        mock_service = Mock()
        mock_attachment_get = Mock()
        mock_attachment_get.execute.return_value = {
            "data": "dGVzdCBkYXRh",
            "size": 9,
        }
        mock_service.users.return_value.messages.return_value.attachments.return_value.get.return_value = mock_attachment_get

        client = GmailClient(Mock())
        client.service = mock_service

        result = client.get_attachment_data("msg1", "att1")

        assert isinstance(result, AttachmentData)
        assert result.attachment_id == "att1"
        assert result.data == "dGVzdCBkYXRh"
        assert result.size == 9

        mock_service.users.return_value.messages.return_value.attachments.return_value.get.assert_called_once_with(
            userId="me", messageId="msg1", id="att1"
        )

    def test_get_attachment_data_without_size(self):
        """Should use 0 when size is not present"""
        mock_service = Mock()
        mock_attachment_get = Mock()
        mock_attachment_get.execute.return_value = {
            "data": "dGVzdCBkYXRh",
        }
        mock_service.users.return_value.messages.return_value.attachments.return_value.get.return_value = mock_attachment_get

        client = GmailClient(Mock())
        client.service = mock_service

        result = client.get_attachment_data("msg1", "att1")

        assert result.size == 0

    def test_get_attachment_data_http_error(self):
        """Should raise RuntimeError when HttpError occurs"""
        mock_service = Mock()
        mock_attachment_get = Mock()
        mock_error = HttpError(Mock(status=404), b"Not Found")
        mock_attachment_get.execute.side_effect = mock_error
        mock_service.users.return_value.messages.return_value.attachments.return_value.get.return_value = mock_attachment_get

        client = GmailClient(Mock())
        client.service = mock_service

        with pytest.raises(RuntimeError) as exc_info:
            client.get_attachment_data("msg1", "invalid_att")

        assert "Gmail API error" in str(exc_info.value)
