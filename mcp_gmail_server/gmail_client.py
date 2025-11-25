"""Gmail API client wrapper"""

import logging

from google.auth.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .models import (
    Attachment,
    AttachmentData,
    Message,
    MessagePayload,
    MessageSearchResult,
)
from .utils import parse_date

logger = logging.getLogger(__name__)


class GmailClient:
    """Client for interacting with Gmail API"""

    def __init__(self, credentials: Credentials) -> None:
        logger.info("Initializing Gmail API service")
        self.service = build("gmail", "v1", credentials=credentials)
        logger.info("Gmail API service initialization completed")

    def search_messages(
        self, query: str, max_results: int = 100
    ) -> list[MessageSearchResult]:
        """
        Search for messages and retrieve a list of message IDs

        Args:
            query: Gmail search query (e.g., "after:2025/1/1")
            max_results: Maximum number of results

        Returns:
            List of MessageSearchResult containing message_id and thread_id
        """
        logger.info(
            f"Starting message search: query={query}, max_results={max_results}"
        )
        try:
            results = (
                self.service.users()
                .messages()
                .list(userId="me", q=query, maxResults=max_results)
                .execute()
            )
            messages = results.get("messages", [])
            result_count = len(messages)

            logger.info(f"Message search completed: {result_count} messages found")
            if result_count == 0:
                logger.warning(f"Search returned 0 results: query={query}")

            return [
                MessageSearchResult(
                    message_id=msg["id"],
                    thread_id=msg.get("threadId", ""),
                )
                for msg in messages
            ]
        except HttpError as error:
            logger.error(
                f"Error occurred during message search: query={query}, error={error}",
                exc_info=True,
            )
            raise RuntimeError(f"Gmail API error: {error}") from error

    def get_message(self, message_id: str) -> Message:
        """
        Retrieve detailed information for a message

        Args:
            message_id: Message ID

        Returns:
            Message object containing message information
        """
        logger.info(f"Retrieving message details: message_id={message_id}")
        try:
            message = (
                self.service.users()
                .messages()
                .get(userId="me", id=message_id, format="full")
                .execute()
            )

            headers = message["payload"].get("headers", [])
            header_dict = {h["name"]: h["value"] for h in headers}
            subject = header_dict.get("Subject", "")
            from_addr = header_dict.get("From", "")

            # Convert payload to model and extract body text
            payload = MessagePayload.model_validate(message["payload"])
            body_text = payload.extract_body_text()
            body_length = len(body_text)

            logger.info(
                f"Message details retrieved: message_id={message_id}, "
                f"subject={subject[:50]}{'...' if len(subject) > 50 else ''}, "
                f"from={from_addr}, body_length={body_length}"
            )

            return Message(
                message_id=message["id"],
                thread_id=message.get("threadId", ""),
                subject=subject,
                **{"from_": from_addr},
                to=header_dict.get("To", ""),
                received_at=parse_date(header_dict.get("Date", "")),
                body_text=body_text,
            )
        except HttpError as error:
            logger.error(
                f"Error occurred while retrieving message details: message_id={message_id}, error={error}",
                exc_info=True,
            )
            raise RuntimeError(f"Gmail API error: {error}") from error

    def get_messages_batch(self, message_ids: list[str]) -> list[Message]:
        """
        Retrieve detailed information for multiple messages using batch request

        Args:
            message_ids: List of message IDs

        Returns:
            List of Message objects containing message information
        """
        logger.info(
            f"Starting batch message retrieval: message_count={len(message_ids)}"
        )
        if not message_ids:
            logger.warning("Empty message_ids list provided")
            return []

        # Store results in a dictionary keyed by request_id
        results: dict[str, Message] = {}
        errors: dict[str, Exception] = {}

        def callback(
            request_id: str, response: dict | None, exception: Exception | None
        ) -> None:
            """Callback function for batch request"""
            if exception is not None:
                logger.error(
                    f"Error in batch request for message_id={request_id}: {exception}",
                    exc_info=True,
                )
                errors[request_id] = exception
                return

            if response is None:
                logger.warning(f"Empty response for message_id={request_id}")
                return

            try:
                # Parse message response similar to get_message
                headers = response["payload"].get("headers", [])
                header_dict = {h["name"]: h["value"] for h in headers}
                subject = header_dict.get("Subject", "")
                from_addr = header_dict.get("From", "")

                # Convert payload to model and extract body text
                payload = MessagePayload.model_validate(response["payload"])
                body_text = payload.extract_body_text()

                message = Message(
                    message_id=response["id"],
                    thread_id=response.get("threadId", ""),
                    subject=subject,
                    **{"from_": from_addr},
                    to=header_dict.get("To", ""),
                    received_at=parse_date(header_dict.get("Date", "")),
                    body_text=body_text,
                )
                results[request_id] = message
            except Exception as e:
                logger.error(
                    f"Error parsing batch response for message_id={request_id}: {e}",
                    exc_info=True,
                )
                errors[request_id] = e

        try:
            # Create batch request using service's new_batch_http_request method
            # This ensures the correct endpoint is used
            batch = self.service.new_batch_http_request(callback=callback)

            # Add each message.get request to the batch
            # Use format="full" to include body text
            for message_id in message_ids:
                request = (
                    self.service.users()
                    .messages()
                    .get(userId="me", id=message_id, format="full")
                )
                batch.add(request, request_id=message_id)

            # Execute batch request
            batch.execute()

            # Check for errors
            if errors:
                error_count = len(errors)
                logger.warning(
                    f"Batch request completed with {error_count} errors out of {len(message_ids)} requests"
                )
                # Raise an error if all requests failed
                if len(results) == 0:
                    first_error = next(iter(errors.values()))
                    raise RuntimeError(
                        f"All batch requests failed. First error: {first_error}"
                    ) from first_error

            # Return results in the same order as input message_ids
            ordered_results: list[Message] = []
            for message_id in message_ids:
                if message_id in results:
                    ordered_results.append(results[message_id])
                # Skip messages that failed (already logged)

            logger.info(
                f"Batch message retrieval completed: "
                f"successful={len(ordered_results)}, failed={len(errors)}, "
                f"total={len(message_ids)}"
            )

            return ordered_results

        except HttpError as error:
            logger.error(
                f"Error occurred during batch message retrieval: error={error}",
                exc_info=True,
            )
            raise RuntimeError(f"Gmail API error: {error}") from error
        except Exception as error:
            logger.error(
                f"Unexpected error during batch message retrieval: error={error}",
                exc_info=True,
            )
            raise RuntimeError(f"Batch request error: {error}") from error

    def get_attachments(self, message_id: str) -> list[Attachment]:
        """
        Retrieve a list of attachments for a message

        Args:
            message_id: Message ID

        Returns:
            List of Attachment objects containing attachment information
        """
        logger.info(f"Retrieving attachment list: message_id={message_id}")
        try:
            message = (
                self.service.users()
                .messages()
                .get(userId="me", id=message_id, format="full")
                .execute()
            )

            # Convert payload to model and extract attachment information
            payload = MessagePayload.model_validate(message["payload"])
            attachments = payload.extract_attachments()
            attachment_count = len(attachments)

            logger.info(
                f"Attachment list retrieved: message_id={message_id}, "
                f"attachment_count={attachment_count}"
            )
            if attachment_count == 0:
                logger.debug(f"No attachments found: message_id={message_id}")

            return attachments
        except HttpError as error:
            logger.error(
                f"Error occurred while retrieving attachment list: message_id={message_id}, error={error}",
                exc_info=True,
            )
            raise RuntimeError(f"Gmail API error: {error}") from error

    def get_attachment_data(
        self, message_id: str, attachment_id: str
    ) -> AttachmentData:
        """
        Retrieve attachment data

        Args:
            message_id: Message ID
            attachment_id: Attachment ID

        Returns:
            AttachmentData object containing attachment data (base64 encoded)
        """
        logger.info(
            f"Retrieving attachment data: message_id={message_id}, "
            f"attachment_id={attachment_id}"
        )
        try:
            attachment = (
                self.service.users()
                .messages()
                .attachments()
                .get(userId="me", messageId=message_id, id=attachment_id)
                .execute()
            )

            size = attachment.get("size", 0)
            data_length = len(attachment["data"])

            logger.info(
                f"Attachment data retrieved: message_id={message_id}, "
                f"attachment_id={attachment_id}, size={size} bytes, "
                f"data_length={data_length} characters"
            )

            return AttachmentData(
                attachment_id=attachment_id,
                data=attachment["data"],
                size=size,
            )
        except HttpError as error:
            logger.error(
                f"Error occurred while retrieving attachment data: "
                f"message_id={message_id}, attachment_id={attachment_id}, error={error}",
                exc_info=True,
            )
            raise RuntimeError(f"Gmail API error: {error}") from error
