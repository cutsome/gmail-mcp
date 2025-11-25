"""Utility functions"""

import base64
from email.header import decode_header
from email.utils import parsedate_to_datetime


def decode_base64_text(data: str) -> str:
    try:
        return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
    except Exception:
        return ""


def parse_date(date_str: str) -> str:
    try:
        dt = parsedate_to_datetime(date_str)
        return dt.isoformat()
    except Exception:
        return date_str


def decode_rfc2047_filename(filename: str) -> str:
    try:
        # Decode RFC 2047 format (=?charset?encoding?text?=)
        decoded_parts = decode_header(filename)
        decoded_strings = []
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                decoded_strings.append(
                    part.decode(encoding or "utf-8", errors="ignore")
                )
            else:
                decoded_strings.append(part)
        return "".join(decoded_strings)
    except Exception:
        return filename
