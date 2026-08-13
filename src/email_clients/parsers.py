"""Email parsing utilities."""

from __future__ import annotations

import email
from email.message import Message
from typing import Any

from bs4 import BeautifulSoup
from imapclient.response_types import Envelope

from util import limit_consecutive_linefeeds, safe_decode


def extract_text_from_email(email_message: Message) -> str:
    """Extract plain text content from an email.Message object."""
    text_content = ""
    if email_message.is_multipart():
        for part in email_message.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                payload = part.get_payload(decode=True)
                if payload is not None:
                    text_content += safe_decode(payload)
            elif content_type == "text/html":
                payload = part.get_payload(decode=True)
                if payload is not None:
                    html = safe_decode(payload)
                    text_content += BeautifulSoup(html, "html.parser").get_text()
    else:
        content_type = email_message.get_content_type()
        if content_type == "text/plain":
            payload = email_message.get_payload(decode=True)
            text_content = safe_decode(payload) if payload is not None else ""
        elif content_type == "text/html":
            payload = email_message.get_payload(decode=True)
            html = safe_decode(payload) if payload is not None else ""
            text_content = BeautifulSoup(html, "html.parser").get_text()

    return limit_consecutive_linefeeds(text_content.strip())


def format_from_address(envelope: Envelope) -> str:
    """Format the from address from an IMAP envelope."""
    if not envelope.from_:
        return "(Unknown Sender)"
    addr = envelope.from_[0]
    mailbox = safe_decode(addr.mailbox) if addr.mailbox else ""
    host = safe_decode(addr.host) if addr.host else ""
    if host:
        return f"{mailbox}@{host}"
    return mailbox


def build_message_dict(
    msg_id: int, envelope: Envelope, rfc822_bytes: bytes
) -> dict[str, Any]:
    """Build a sort-buddy message dictionary from IMAP fetch data."""
    email_message = email.message_from_bytes(rfc822_bytes)
    subject = "(No Subject)"
    if envelope.subject is not None and envelope.subject != b"":
        subject = safe_decode(envelope.subject)
    return {
        "id": msg_id,
        "subject": subject,
        "from": format_from_address(envelope),
        "body": extract_text_from_email(email_message),
        "responses": [],
    }
