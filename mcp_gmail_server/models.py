"""Gmail API response type definitions"""

from __future__ import annotations

import re
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from .utils import decode_base64_text, decode_rfc2047_filename


class MessageSearchResult(BaseModel):
    """Type definition for message search results"""

    message_id: str = Field(..., description="Message ID")
    thread_id: str = Field(..., description="Thread ID")


class Message(BaseModel):
    """Type definition for message information"""

    model_config = ConfigDict(populate_by_name=True)

    message_id: str = Field(..., description="Message ID")
    thread_id: str = Field(..., description="Thread ID")
    subject: str = Field(default="", description="Subject")
    from_: str = Field(..., alias="from", description="Sender")
    to: str = Field(default="", description="Recipient")
    received_at: str = Field(..., description="Received date and time (ISO8601 format)")
    body_text: str = Field(default="", description="Message body")


class Attachment(BaseModel):
    """Type definition for attachment information"""

    attachment_id: str = Field(..., description="Attachment ID")
    file_name: str = Field(..., description="File name")
    mime_type: str = Field(..., description="MIME type")
    size: int = Field(..., description="File size (bytes)")


class AttachmentData(BaseModel):
    """Type definition for attachment data"""

    attachment_id: str = Field(..., description="Attachment ID")
    data: str = Field(..., description="Base64 encoded file data")
    size: int = Field(..., description="File size (bytes)")


class PayloadBody(BaseModel):
    """Body part of Gmail API payload"""

    model_config = ConfigDict(populate_by_name=True)

    attachment_id: Optional[str] = Field(
        default=None, alias="attachmentId", description="Attachment ID"
    )
    data: Optional[str] = Field(default=None, description="Base64 encoded data")
    size: int = Field(default=0, description="Size (bytes)")


class MessagePayload(BaseModel):
    """Part of Gmail API payload (recursive structure)"""

    mime_type: str = Field(..., alias="mimeType", description="MIME type")
    filename: Optional[str] = Field(default=None, description="File name")
    body: PayloadBody = Field(..., description="Body information")
    parts: Optional[list["MessagePayload"]] = Field(
        default=None, description="Sub-parts (for multipart messages)"
    )
    headers: Optional[list[dict[str, str]]] = Field(
        default=None, description="Header array"
    )

    model_config = ConfigDict(populate_by_name=True)

    def is_text_plain(self) -> bool:
        return self.mime_type == "text/plain"

    def is_text_html(self) -> bool:
        return self.mime_type == "text/html"

    def decode_body_data(self) -> str:
        if self.body.data:
            return decode_base64_text(self.body.data)
        return ""

    def extract_filename_from_headers(self) -> Optional[str]:
        """
        Extract filename from header array

        Returns:
            Extracted filename (None if not found)
        """
        if not self.headers:
            return None

        header_dict = {
            h.get("name", "").lower(): h.get("value", "") for h in self.headers
        }

        # Extract filename from Content-Disposition header (priority)
        content_disposition = header_dict.get("content-disposition", "")
        if content_disposition:
            match = re.search(
                r'filename[*]?=(?:"([^"]+)"|([^;]+))',
                content_disposition,
                re.IGNORECASE,
            )
            if match:
                filename = match.group(1) or match.group(2)
                if filename:
                    return decode_rfc2047_filename(filename.strip())

        # Extract name parameter from Content-Type header (fallback)
        content_type = header_dict.get("content-type", "")
        if content_type:
            match = re.search(
                r'name[*]?=(?:"([^"]+)"|([^;]+))', content_type, re.IGNORECASE
            )
            if match:
                filename = match.group(1) or match.group(2)
                if filename:
                    return decode_rfc2047_filename(filename.strip())

        return None

    def create_attachment(self) -> Attachment | None:
        """
        Create an Attachment object from this part

        Returns:
            Attachment object (None if cannot be created)
        """
        if not self.body.attachment_id:
            return None

        # Get filename (either directly specified or extracted from headers)
        filename = self.filename
        if not filename and self.headers:
            filename = self.extract_filename_from_headers()

        if not filename:
            return None

        return Attachment(
            attachment_id=self.body.attachment_id,
            file_name=filename,
            mime_type=self.mime_type,
            size=self.body.size,
        )

    def extract_body_text(self) -> str:
        """
        Extract message body text from this part (recursive processing)

        Returns:
            Extracted message body text
        """
        # For multipart messages, process recursively
        if self.parts:
            plain_text = ""
            html_text = ""

            for part in self.parts:
                # Skip attachments
                if part.body.attachment_id:
                    continue

                # Recursively get text
                part_text = part.extract_body_text()

                # Add if directly text/plain or text/html
                if part.is_text_plain():
                    plain_text += part_text
                elif part.is_text_html():
                    html_text += part_text
                # For multipart/alternative etc., use recursively obtained result
                elif part_text:
                    # If nothing has been obtained yet, return the obtained text
                    if not plain_text and not html_text:
                        return part_text
                    # If already obtained, add (shouldn't normally happen, but just in case)
                    plain_text += part_text

            # Prefer plain text, use HTML if not available
            return plain_text or html_text

        # For simple messages
        if self.is_text_plain() or self.is_text_html():
            return self.decode_body_data()

        return ""

    def extract_attachments(self) -> list[Attachment]:
        """
        Recursively extract attachment information from this part

        Returns:
            List of extracted attachment information
        """
        attachments: list[Attachment] = []

        # If this part itself is an attachment
        if attachment := self.create_attachment():
            attachments.append(attachment)

        # Recursively process sub-parts
        if self.parts:
            for sub_part in self.parts:
                attachments.extend(sub_part.extract_attachments())

        return attachments
