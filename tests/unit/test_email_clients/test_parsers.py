"""Unit tests for email parsing utilities."""

from __future__ import annotations

import email
from email.message import EmailMessage
from unittest.mock import MagicMock

import pytest

from email_clients.parsers import build_message_dict, extract_text_from_email, format_from_address


def _plain_email_bytes(body: str = "This is a plain text body.") -> bytes:
    msg = EmailMessage()
    msg.set_content(body)
    return msg.as_bytes()


def _multipart_email_bytes() -> bytes:
    msg = EmailMessage()
    msg.set_content("plain text part")
    msg.add_alternative("<html><body>html part</body></html>", subtype="html")
    return msg.as_bytes()


def _make_envelope(subject: bytes = b"Test Subject", mailbox: bytes = b"sender", host: bytes = b"example.com") -> MagicMock:
    envelope = MagicMock()
    envelope.subject = subject
    addr = MagicMock()
    addr.mailbox = mailbox
    addr.host = host
    envelope.from_ = [addr]
    return envelope


def test_extract_text_plain() -> None:
    email_message = EmailMessage()
    email_message.set_content("plain body")
    assert extract_text_from_email(email_message) == "plain body"


def test_extract_text_multipart() -> None:
    raw = _multipart_email_bytes()
    email_message = email.message_from_bytes(raw)
    text = extract_text_from_email(email_message)
    assert "plain text part" in text
    assert "html part" in text


def test_format_from_address() -> None:
    envelope = _make_envelope()
    assert format_from_address(envelope) == "sender@example.com"


def test_format_from_address_unknown() -> None:
    envelope = MagicMock()
    envelope.from_ = []
    assert format_from_address(envelope) == "(Unknown Sender)"


def test_build_message_dict() -> None:
    envelope = _make_envelope()
    raw = _plain_email_bytes("Email body here.")
    msg = build_message_dict(1, envelope, raw)
    assert msg["id"] == 1
    assert msg["subject"] == "Test Subject"
    assert msg["from"] == "sender@example.com"
    assert "Email body here." in msg["body"]
    assert msg["responses"] == []


def test_build_message_dict_empty_subject() -> None:
    envelope = _make_envelope(subject=b"")
    raw = _plain_email_bytes("Email body here.")
    msg = build_message_dict(2, envelope, raw)
    assert msg["subject"] == "(No Subject)"


def test_build_message_dict_missing_host() -> None:
    envelope = _make_envelope(host=b"")
    raw = _plain_email_bytes("Email body here.")
    msg = build_message_dict(3, envelope, raw)
    assert msg["from"] == "sender"


def test_format_from_address_missing_host() -> None:
    envelope = _make_envelope(host=b"")
    assert format_from_address(envelope) == "sender"


def test_extract_text_empty_body() -> None:
    email_message = EmailMessage()
    email_message.set_content("")
    assert extract_text_from_email(email_message) == ""


def test_extract_text_non_text_html() -> None:
    raw = b"Content-Type: application/json\n\n{\"x\": 1}"
    email_message = email.message_from_bytes(raw)
    assert extract_text_from_email(email_message) == ""
