"""Prompt templates and response parsing for AI clients."""

from __future__ import annotations

import json

from util import get_stripped_folder_list, remove_prefix


FOLDER_DEFINITIONS: dict[str, str] = {
    "Important": "Genuinely time-sensitive or personal mail that requires prompt attention.",
    "Newsletters": "Marketing, promotions, newsletters, coupons, and recurring mass mail.",
    "Notifications": "Automated alerts, statements, receipts, and account updates from services.",
    "Other": "Anything that does not match the other categories.",
    "Personal": "Private, non-work, or individually addressed messages.",
    "Spam": "Unwanted, unsolicited, or suspicious bulk mail.",
}

VALID_FOLDERS: frozenset[str] = frozenset(FOLDER_DEFINITIONS.keys())

SYSTEM_PROMPT_TEMPLATE = (
    "You are an email classifier. Pick exactly one folder for the email below.\n\n"
    "Available folders:\n"
    "{folder_list}\n\n"
    "Rules:\n"
    "- You MUST use exactly one of these folder names: Important, Newsletters, Notifications, Other, Personal, Spam. Do NOT use Work, Mailing-List, or any other name.\n"
    "- Respond with exactly this format and nothing else: <Folder>: <brief explanation>\n"
    "- Do not include introductions, conclusions, code blocks, quotes, or extra lines.\n"
    "- Important is only for genuinely time-sensitive or personal mail.\n"
    "- Newsletters is for marketing, promotions, newsletters, coupons, and recurring mass mail. "
    "These belong in Newsletters or Spam, never in Important.\n"
    "- Notifications is for automated alerts, statements, receipts, and account updates from services.\n"
    "- If the sender contains postmaster, no-reply, noreply, notifications, alerts, jobalerts, or is an automated service message, classify as Notifications unless the subject is about a payment due, account security, or other urgent personal matter.\n"
    "- Other is for anything that does not clearly match the other categories.\n"
    "- Personal is for private, non-work, or individually addressed messages.\n"
    "- Spam is for unwanted, unsolicited, or suspicious bulk mail.\n"
    "- Do NOT rewrite or summarize the email body.\n\n"
    "Examples (respond with exactly one line like these):\n"
    "Important: This is a personal, time-sensitive message from a known contact that requires prompt attention.\n"
    "Newsletters: This is a regular industry newsletter with multiple article links and a sponsor section.\n"
    "Notifications: This is an automated statement or account alert from a service the recipient uses.\n"
    "Notifications: This is a job alert from LinkedIn about a new position matching the recipient's profile.\n"
    "Other: This is an email that does not clearly belong to any other category.\n"
    "Personal: This is a private, individually addressed message from a friend or family member.\n"
    "Personal: This is a LinkedIn connection request from a known contact.\n"
    "Spam: This is an unsolicited promotional message with suspicious links and excessive discount claims.\n\n"
    "Negative examples (do NOT respond like these):\n"
    '- "I think this email is important because..." (no essays or explanations outside the format)\n'
    "- Multi-paragraph summaries\n"
    "- Markdown code blocks, JSON, or quoted email text\n"
)

SYSTEM_PROMPT_JSON_TEMPLATE = (
    "You are an email classifier. Respond with a single JSON object and no other text.\n\n"
    "The JSON object must have exactly this format:\n"
    '{{"folder": "<one of the folders>", "explanation": "<brief explanation>"}}\n\n'
    "Available folders:\n"
    "{folder_list}\n\n"
    "Rules:\n"
    "- You MUST use exactly one of these folder names: Important, Newsletters, Notifications, Other, Personal, Spam. Do NOT use Work, Mailing-List, or any other name.\n"
    "- Output only valid JSON. Do not wrap it in Markdown code blocks or add extra text.\n"
    "- Choose exactly one folder from the list above.\n"
    "- explanation must be a brief one-sentence reason for the choice.\n"
    "- Important is only for genuinely time-sensitive or personal mail.\n"
    "- Newsletters is for marketing, promotions, newsletters, coupons, and recurring mass mail. "
    "These belong in Newsletters or Spam, never in Important.\n"
    "- Notifications is for automated alerts, statements, receipts, and account updates from services.\n"
    "- If the sender contains postmaster, no-reply, noreply, notifications, alerts, jobalerts, or is an automated service message, classify as Notifications unless the subject is about a payment due, account security, or other urgent personal matter.\n"
    "- Other is for anything that does not clearly match the other categories.\n"
    "- Personal is for private, non-work, or individually addressed messages.\n"
    "- Spam is for unwanted, unsolicited, or suspicious bulk mail.\n\n"
    "Examples:\n"
    '{{"folder": "Important", "explanation": "This is a personal, time-sensitive message from a known contact."}}\n'
    '{{"folder": "Newsletters", "explanation": "This is a regular industry newsletter with article links."}}\n'
    '{{"folder": "Notifications", "explanation": "This is an automated statement from a service."}}\n'
    '{{"folder": "Notifications", "explanation": "This is a job alert from LinkedIn about a new position."}}\n'
    '{{"folder": "Other", "explanation": "This email does not clearly belong to any other category."}}\n'
    '{{"folder": "Personal", "explanation": "This is a private message from a friend or family member."}}\n'
    '{{"folder": "Personal", "explanation": "This is a LinkedIn connection request from a known contact."}}\n'
    '{{"folder": "Spam", "explanation": "This is an unsolicited promotional message with suspicious links."}}\n'
)


def _folder_definitions(folders: list[str]) -> str:
    """Build a one-sentence definition line for each available folder."""
    lines = []
    for folder in folders:
        definition = FOLDER_DEFINITIONS.get(folder, "Use the name as a guide and classify accordingly.")
        lines.append(f"- {folder}: {definition}")
    return "\n".join(lines)


def _clean_folder_name(folder: str) -> str:
    """Strip surrounding whitespace, quotes, and backticks from a folder name."""
    folder = folder.strip()
    while len(folder) >= 2 and folder[0] in ('"', "'", "`") and folder[-1] == folder[0]:
        folder = folder[1:-1].strip()
    return folder


def _truncate_email_body(body: str, max_len: int = 2000) -> str:
    """Return the body clipped to max_len, with a truncation marker if shortened."""
    if len(body) <= max_len:
        return body
    return body[:max_len] + "\n\n[... content truncated for brevity ...]"


def generate_prompt(
    message: dict[str, str],
    folders: list[str],
    show_prompt: bool = False,
) -> tuple[str, str]:
    """Build the system and user prompts for an email message."""
    stripped_folders = get_stripped_folder_list(folders)

    folder_list = _folder_definitions(stripped_folders)
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(folder_list=folder_list)

    body = _truncate_email_body(message["body"])
    prompt = f"Email Subject: {message['subject']}\n"
    prompt += f"Email From: {message['from']}\n"
    prompt += f"Email Body: {body}\n"

    if show_prompt:
        print(system_prompt)
        print(prompt)

    return system_prompt, prompt


def generate_json_prompt(
    message: dict[str, str],
    folders: list[str],
    show_prompt: bool = False,
) -> tuple[str, str]:
    """Build the system and user prompts for JSON mode."""
    stripped_folders = get_stripped_folder_list(folders)

    folder_list = _folder_definitions(stripped_folders)
    system_prompt = SYSTEM_PROMPT_JSON_TEMPLATE.format(folder_list=folder_list)

    body = _truncate_email_body(message["body"])
    prompt = f"Email Subject: {message['subject']}\n"
    prompt += f"Email From: {message['from']}\n"
    prompt += f"Email Body: {body}\n"

    if show_prompt:
        print(system_prompt)
        print(prompt)

    return system_prompt, prompt


def parse_classification(content: str, folders: list[str]) -> tuple[str, str]:
    """Parse a raw classification response into (folder, explanation)."""
    if ":" not in content:
        return ("invalid", "could not split response")

    before, _, after = content.partition(":")

    # The model may prefix the answer with an essay; the folder is the last
    # non-empty line before the first colon.
    pre_lines = [line.strip() for line in before.splitlines() if line.strip()]
    if not pre_lines:
        return ("invalid", "could not split response")

    raw_folder = _clean_folder_name(pre_lines[-1])
    explanation = after.strip()

    if raw_folder.lower() == "inbox":
        return ("Inbox", explanation)

    # Match either the full folder name or the short name (without the prefix).
    folder_map = {remove_prefix(folder).lower(): folder for folder in folders}
    short = remove_prefix(raw_folder).lower()

    if short in folder_map:
        folder = folder_map[short]
        # Validate against VALID_FOLDERS
        if remove_prefix(folder) not in VALID_FOLDERS:
            return (f'invalid: "{raw_folder}"', explanation)
        return (folder, explanation)

    return (f'invalid: "{raw_folder}"', explanation)


def _strip_markdown_code_fence(text: str) -> str:
    """Remove a surrounding Markdown code fence if present."""
    text = text.strip()
    if not text.startswith("```"):
        return text
    lines = text.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()


def parse_json_classification(content: str, folders: list[str]) -> tuple[str, str]:
    """Parse a JSON classification response, falling back to text parsing."""
    text = _strip_markdown_code_fence(content)
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return parse_classification(content, folders)

    if not isinstance(data, dict) or "folder" not in data or "explanation" not in data:
        return parse_classification(content, folders)

    raw_folder = _clean_folder_name(str(data["folder"]))
    explanation = str(data["explanation"]).strip()

    if raw_folder.lower() == "inbox":
        return ("Inbox", explanation)

    folder_map = {remove_prefix(folder).lower(): folder for folder in folders}
    short = remove_prefix(raw_folder).lower()

    if short in folder_map:
        folder = folder_map[short]
        # Validate against VALID_FOLDERS
        if remove_prefix(folder) not in VALID_FOLDERS:
            return (f'invalid: "{raw_folder}"', explanation)
        return (folder, explanation)

    return (f'invalid: "{raw_folder}"', explanation)
