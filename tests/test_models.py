"""Unit tests for models.py (MessagePayload class only)"""

import base64

from mcp_gmail_server.models import Attachment, MessagePayload, PayloadBody


class TestMessagePayload:
    """Tests for MessagePayload class"""

    def test_is_text_plain(self):
        """Should correctly identify text/plain MIME type"""
        payload = MessagePayload(
            mimeType="text/plain",
            body=PayloadBody(),
        )
        assert payload.is_text_plain() is True
        assert payload.is_text_html() is False

    def test_is_text_html(self):
        """Should correctly identify text/html MIME type"""
        payload = MessagePayload(
            mimeType="text/html",
            body=PayloadBody(),
        )
        assert payload.is_text_html() is True
        assert payload.is_text_plain() is False

    def test_is_not_text(self):
        """Should correctly identify non-text MIME types"""
        payload = MessagePayload(
            mimeType="image/png",
            body=PayloadBody(),
        )
        assert payload.is_text_plain() is False
        assert payload.is_text_html() is False

    def test_decode_body_data_with_data(self):
        """Should decode when body data is present"""
        text = "Hello, World!"
        encoded = base64.urlsafe_b64encode(text.encode("utf-8")).decode("utf-8")
        payload = MessagePayload(
            mimeType="text/plain",
            body=PayloadBody(data=encoded),
        )
        result = payload.decode_body_data()
        assert result == text

    def test_decode_body_data_without_data(self):
        """Should return empty string when body data is not present"""
        payload = MessagePayload(
            mimeType="text/plain",
            body=PayloadBody(data=None),
        )
        result = payload.decode_body_data()
        assert result == ""

    def test_create_attachment_with_filename_and_id(self):
        """Should create Attachment object when filename and attachment ID are present"""
        payload = MessagePayload(
            mimeType="application/pdf",
            filename="test.pdf",
            body=PayloadBody(attachment_id="att123", size=1024),
        )
        attachment = payload.create_attachment()
        assert attachment is not None
        assert isinstance(attachment, Attachment)
        assert attachment.attachment_id == "att123"
        assert attachment.file_name == "test.pdf"
        assert attachment.mime_type == "application/pdf"
        assert attachment.size == 1024

    def test_create_attachment_without_filename(self):
        """Should return None when filename is not present"""
        payload = MessagePayload(
            mimeType="application/pdf",
            filename=None,
            body=PayloadBody(attachment_id="att123", size=1024),
        )
        attachment = payload.create_attachment()
        assert attachment is None

    def test_create_attachment_without_attachment_id(self):
        """Should return None when attachment ID is not present"""
        payload = MessagePayload(
            mimeType="application/pdf",
            filename="test.pdf",
            body=PayloadBody(attachment_id=None, size=1024),
        )
        attachment = payload.create_attachment()
        assert attachment is None

    def test_extract_body_text_simple_plain(self):
        """Should extract body text from simple plain text message"""
        text = "Simple text message"
        encoded = base64.urlsafe_b64encode(text.encode("utf-8")).decode("utf-8")
        payload = MessagePayload(
            mimeType="text/plain",
            body=PayloadBody(data=encoded),
        )
        result = payload.extract_body_text()
        assert result == text

    def test_extract_body_text_simple_html(self):
        """Should extract body text from simple HTML message"""
        html = "<p>HTML message</p>"
        encoded = base64.urlsafe_b64encode(html.encode("utf-8")).decode("utf-8")
        payload = MessagePayload(
            mimeType="text/html",
            body=PayloadBody(data=encoded),
        )
        result = payload.extract_body_text()
        assert result == html

    def test_extract_body_text_multipart_plain_preferred(self):
        """Plain text should be preferred in multipart messages"""
        plain_text = "Plain text"
        html_text = "<p>HTML text</p>"
        plain_encoded = base64.urlsafe_b64encode(plain_text.encode("utf-8")).decode(
            "utf-8"
        )
        html_encoded = base64.urlsafe_b64encode(html_text.encode("utf-8")).decode(
            "utf-8"
        )

        payload = MessagePayload(
            mimeType="multipart/alternative",
            body=PayloadBody(),
            parts=[
                MessagePayload(
                    mimeType="text/plain",
                    body=PayloadBody(data=plain_encoded),
                ),
                MessagePayload(
                    mimeType="text/html",
                    body=PayloadBody(data=html_encoded),
                ),
            ],
        )
        result = payload.extract_body_text()
        assert result == plain_text

    def test_extract_body_text_multipart_html_fallback(self):
        """Should use HTML when plain text is not available in multipart messages"""
        html_text = "<p>HTML text</p>"
        html_encoded = base64.urlsafe_b64encode(html_text.encode("utf-8")).decode(
            "utf-8"
        )

        payload = MessagePayload(
            mimeType="multipart/alternative",
            body=PayloadBody(),
            parts=[
                MessagePayload(
                    mimeType="text/html",
                    body=PayloadBody(data=html_encoded),
                ),
            ],
        )
        result = payload.extract_body_text()
        assert result == html_text

    def test_extract_body_text_non_text_returns_empty(self):
        """Should return empty string for non-text MIME types"""
        payload = MessagePayload(
            mimeType="image/png",
            body=PayloadBody(),
        )
        result = payload.extract_body_text()
        assert result == ""

    def test_extract_attachments_simple(self):
        """Should extract simple attachment"""
        payload = MessagePayload(
            mimeType="application/pdf",
            filename="document.pdf",
            body=PayloadBody(attachment_id="att123", size=2048),
        )
        attachments = payload.extract_attachments()
        assert len(attachments) == 1
        assert attachments[0].attachment_id == "att123"
        assert attachments[0].file_name == "document.pdf"
        assert attachments[0].mime_type == "application/pdf"
        assert attachments[0].size == 2048

    def test_extract_attachments_multipart(self):
        """Should extract multiple attachments from multipart message"""
        payload = MessagePayload(
            mimeType="multipart/mixed",
            body=PayloadBody(),
            parts=[
                MessagePayload(
                    mimeType="application/pdf",
                    filename="doc1.pdf",
                    body=PayloadBody(attachment_id="att1", size=1024),
                ),
                MessagePayload(
                    mimeType="image/png",
                    filename="image.png",
                    body=PayloadBody(attachment_id="att2", size=2048),
                ),
            ],
        )
        attachments = payload.extract_attachments()
        assert len(attachments) == 2
        assert attachments[0].file_name == "doc1.pdf"
        assert attachments[1].file_name == "image.png"

    def test_extract_attachments_nested_multipart(self):
        """Should extract attachments from nested multipart message"""
        payload = MessagePayload(
            mimeType="multipart/mixed",
            body=PayloadBody(),
            parts=[
                MessagePayload(
                    mimeType="multipart/alternative",
                    body=PayloadBody(),
                    parts=[
                        MessagePayload(
                            mimeType="text/plain",
                            body=PayloadBody(
                                data=base64.urlsafe_b64encode(b"text").decode()
                            ),
                        ),
                    ],
                ),
                MessagePayload(
                    mimeType="application/pdf",
                    filename="nested.pdf",
                    body=PayloadBody(attachment_id="att_nested", size=1024),
                ),
            ],
        )
        attachments = payload.extract_attachments()
        assert len(attachments) == 1
        assert attachments[0].file_name == "nested.pdf"

    def test_extract_attachments_no_attachments(self):
        """Should return empty list when no attachments are present"""
        payload = MessagePayload(
            mimeType="text/plain",
            body=PayloadBody(data=base64.urlsafe_b64encode(b"text").decode()),
        )
        attachments = payload.extract_attachments()
        assert len(attachments) == 0
        assert isinstance(attachments, list)

    def test_create_attachment_from_headers(self):
        """Should extract filename from headers and create Attachment object"""
        payload = MessagePayload(
            mimeType="application/pdf",
            filename=None,  # filename is not directly specified
            body=PayloadBody(attachment_id="att123", size=1024),
            headers=[
                {
                    "name": "Content-Disposition",
                    "value": 'attachment; filename="document.pdf"',
                },
            ],
        )
        attachment = payload.create_attachment()
        assert attachment is not None
        assert isinstance(attachment, Attachment)
        assert attachment.attachment_id == "att123"
        assert attachment.file_name == "document.pdf"
        assert attachment.mime_type == "application/pdf"
        assert attachment.size == 1024

    def test_create_attachment_from_content_type_header(self):
        """Should extract filename from Content-Type header (fallback)"""
        payload = MessagePayload(
            mimeType="application/pdf",
            filename=None,
            body=PayloadBody(attachment_id="att456", size=2048),
            headers=[
                {"name": "Content-Type", "value": 'application/pdf; name="report.pdf"'},
            ],
        )
        attachment = payload.create_attachment()
        assert attachment is not None
        assert attachment.file_name == "report.pdf"

    def test_extract_attachments_with_headers(self):
        """Should extract filename from headers and detect attachments"""
        payload = MessagePayload(
            mimeType="multipart/mixed",
            body=PayloadBody(),
            parts=[
                MessagePayload(
                    mimeType="application/pdf",
                    filename=None,  # filename is not directly specified
                    body=PayloadBody(attachment_id="att1", size=1024),
                    headers=[
                        {
                            "name": "Content-Disposition",
                            "value": 'attachment; filename="file.pdf"',
                        },
                    ],
                ),
            ],
        )
        attachments = payload.extract_attachments()
        assert len(attachments) == 1
        assert attachments[0].attachment_id == "att1"
        assert attachments[0].file_name == "file.pdf"
