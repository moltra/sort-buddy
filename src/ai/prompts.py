"""Prompt templates and response parsing for AI clients."""

from __future__ import annotations

from util import get_stripped_folder_list


SYSTEM_PROMPT_TEMPLATE = (
    "You are an email classifier.  I will give you an email, "
    "and you will respond with the name of the best folder "
    "for that email, followed by a colon and a space.  If an "
    "email seems genuine, or too hard, please respond with "
    "'Inbox'.  After the colon and space, please provide a "
    "brief explanation of why you chose that folder. "
    "The available folders are: {folders} and Inbox\n"
)


def generate_prompt(
    message: dict[str, str],
    folders: list[str],
    show_prompt: bool = False,
) -> tuple[str, str]:
    """Build the system and user prompts for an email message."""
    stripped_folders = get_stripped_folder_list(folders)

    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(folders=", ".join(stripped_folders))

    prompt = f"Email Subject: {message['subject']}\n"
    prompt += f"Email From: {message['from']}\n"
    prompt += f"Email Body: {message['body']}\n"

    if show_prompt:
        print(system_prompt)
        print(prompt)

    return system_prompt, prompt


def parse_classification(content: str, folders: list[str]) -> tuple[str, str]:
    """Parse a raw classification response into (folder, explanation)."""
    try:
        folder, explanation = content.split(":", 1)
    except ValueError:
        return ("invalid", "could not split response")

    folder = folder.strip()
    explanation = explanation.strip()

    if folder == "Inbox":
        return (folder, explanation)

    if folder not in folders:
        return (f'invalid: "{folder}"', explanation)

    return (folder, explanation)
