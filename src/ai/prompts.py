"""Prompt templates and response parsing for AI clients."""

from __future__ import annotations

from util import get_stripped_folder_list, remove_prefix


FOLDER_DEFINITIONS: dict[str, str] = {
    "Important": "Genuinely time-sensitive or personal mail that requires prompt attention.",
    "Spam": "Unwanted, unsolicited, or suspicious bulk mail.",
    "Newsletters": "Marketing, promotions, newsletters, coupons, and recurring mass mail.",
    "Mailing-List": "Mailing-list or group-list messages and discussions.",
    "Work": "Professional, job-related, or business correspondence.",
    "Personal": "Private, non-work, or individually addressed messages.",
}

SYSTEM_PROMPT_TEMPLATE = (
    "You are an email classifier. Pick exactly one folder for the email below.\n\n"
    "Available folders:\n"
    "{folder_list}\n"
    "Use Inbox only when the email is too ambiguous to classify.\n\n"
    "Rules:\n"
    "- Respond with exactly this format and nothing else: <Folder>: <brief explanation>\n"
    "- Do not include introductions, conclusions, code blocks, quotes, or extra lines.\n"
    "- Marketing, promotions, newsletters, coupons, and unsolicited mass mail "
    "belong in Newsletters or Spam, never in Important.\n"
    "- Important is only for genuinely time-sensitive or personal mail.\n"
    "- If none of the folders clearly fit and the email is not ambiguous, choose Inbox.\n"
    "- Do NOT rewrite or summarize the email body.\n\n"
    "Examples (respond with exactly one line like these):\n"
    "Newsletters: This is a regular industry newsletter with multiple article links and a sponsor section.\n"
    "Notifications: This is an automated statement or account alert from a service the recipient uses.\n"
    "Spam: This is an unsolicited promotional message with suspicious links and excessive discount claims.\n"
    "Important: This is a personal or time-sensitive message from a known contact that requires prompt attention.\n"
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


def generate_prompt(
    message: dict[str, str],
    folders: list[str],
    show_prompt: bool = False,
) -> tuple[str, str]:
    """Build the system and user prompts for an email message."""
    stripped_folders = get_stripped_folder_list(folders)

    folder_list = _folder_definitions(stripped_folders)
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(folder_list=folder_list)

    prompt = f"Email Subject: {message['subject']}\n"
    prompt += f"Email From: {message['from']}\n"
    prompt += f"Email Body: {message['body']}\n"

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
        return (folder_map[short], explanation)

    return (f'invalid: "{raw_folder}"', explanation)
