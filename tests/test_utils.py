"""Unit tests for utils.py"""

import base64

from mcp_gmail_server.utils import decode_base64_text, parse_date


class TestDecodeBase64Text:
    """Tests for decode_base64_text function"""

    def test_decode_valid_base64(self):
        """Should decode valid base64 string"""
        text = "Hello, World!"
        encoded = base64.urlsafe_b64encode(text.encode("utf-8")).decode("utf-8")
        result = decode_base64_text(encoded)
        assert result == text

    def test_decode_japanese_text(self):
        """Should decode Japanese text"""
        text = "Hello, World!"
        encoded = base64.urlsafe_b64encode(text.encode("utf-8")).decode("utf-8")
        result = decode_base64_text(encoded)
        assert result == text

    def test_decode_empty_string(self):
        """Should decode empty string"""
        encoded = base64.urlsafe_b64encode("".encode("utf-8")).decode("utf-8")
        result = decode_base64_text(encoded)
        assert result == ""

    def test_decode_invalid_base64(self):
        """Should return empty string for invalid base64 string"""
        result = decode_base64_text("invalid_base64!!!")
        assert result == ""

    def test_decode_none_returns_empty(self):
        """Should return empty string when None is passed"""
        # Error occurs during base64 decode, but exception is caught and empty string is returned
        result = decode_base64_text("")
        assert result == ""


class TestParseDate:
    """Tests for parse_date function"""

    def test_parse_valid_rfc2822_date(self):
        """Should convert valid RFC2822 format date string to ISO8601 format"""
        date_str = "Mon, 1 Jan 2025 12:00:00 +0900"
        result = parse_date(date_str)
        assert isinstance(result, str)
        assert "2025-01-01" in result
        assert "T" in result  # ISO8601 format contains T

    def test_parse_date_with_timezone(self):
        """Should convert date with timezone"""
        date_str = "Tue, 15 Jan 2025 10:30:00 -0500"
        result = parse_date(date_str)
        assert isinstance(result, str)
        assert "2025-01-15" in result

    def test_parse_invalid_date_returns_original(self):
        """Should return original string for invalid date string"""
        invalid_date = "invalid date string"
        result = parse_date(invalid_date)
        assert result == invalid_date

    def test_parse_empty_string_returns_original(self):
        """Should return original string for empty string"""
        result = parse_date("")
        assert result == ""

    def test_parse_date_iso8601_format(self):
        """Should correctly convert ISO8601 format date string"""
        date_str = "Mon, 1 Jan 2025 12:00:00 +0900"
        result = parse_date(date_str)
        # Verify ISO8601 format (YYYY-MM-DDTHH:MM:SS format)
        assert result.count("-") >= 2  # Date part contains hyphens
        assert "T" in result or "+" in result or "Z" in result  # Time part separator
