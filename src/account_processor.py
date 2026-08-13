"""Single-account processing orchestration."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

from colorama import Fore, Style  # type: ignore[import-untyped]
from loguru import logger

from accounts_config import AccountConfig
from ai import get_ai_response_from_message
from config import EmailConfig
from email_fetcher import EmailFetcher
from util import get_stripped_folder_list, print_line, save_results_to_json


def process_account(
    account: AccountConfig,
    *,
    dry_run: bool = False,
    limit: int | None = None,
    show_prompt: bool = False,
    show_rate_limits: bool = False,
    save_to_json: str | None = None,
) -> dict[str, Any]:
    """Process a single account and return stats.

    Args:
        account: The account configuration to process.
        dry_run: If True, do not move messages.
        limit: Maximum number of messages to process.
        show_prompt: Print the prompt sent to the AI.
        show_rate_limits: Print rate limit headers from the AI response.
        save_to_json: Optional base path for saving results.

    Returns:
        A dictionary with processing stats.
    """
    print(f"[{account.name}] Processing...")

    email_config = EmailConfig.from_account_config(account)
    fetcher = EmailFetcher(dry_run=dry_run, email_config=email_config)

    ai_folders: list[str] = []
    messages: list[dict[str, Any]] = []
    count = 0
    errors = 0

    try:
        print_line()
        print(
            f"[{account.name}] Fetching folders starting with {email_config.folder_prefix}..."
        )
        ai_folders = fetcher.list_ai_folders()
        formatted_inboxes = get_stripped_folder_list(
            ai_folders, prefix=email_config.folder_prefix
        )
        print(f"[{account.name}] Found {len(ai_folders)} folders: {ai_folders}")

        while fetcher.has_more_messages():
            if limit is not None and count >= limit:
                break

            message = fetcher.fetch_next_message()
            if not message:
                continue

            print_line()
            print(
                f"[{account.name}] {Fore.BLUE}From:{Style.RESET_ALL} "
                f"{Fore.CYAN}{message['from']}{Style.RESET_ALL}"
            )
            print(
                f"[{account.name}] {Fore.BLUE}Subject:{Style.RESET_ALL} "
                f"{Fore.CYAN}{message['subject']}{Style.RESET_ALL}"
            )

            try:
                folder, explanation = get_ai_response_from_message(
                    message,
                    formatted_inboxes,
                    show_prompt,
                    show_rate_limits,
                )
            except Exception:
                logger.exception("[%s] AI failed for message", account.name)
                errors += 1
                continue

            print(
                f"[{account.name}] --> {Fore.GREEN}{folder}{Style.RESET_ALL}: "
                f"{Fore.WHITE}{explanation}{Style.RESET_ALL}"
            )

            response_data = {
                "datetime": datetime.now().isoformat(),
                "model": os.getenv("OPENAI_MODEL"),
                "folder": folder,
                "explanation": explanation,
            }

            message["responses"].append(response_data)
            messages.append(message)

            if not dry_run:
                if folder == "Inbox":
                    print(f"[{account.name}] Leaving message in inbox.")
                elif folder == "invalid":
                    print(f"[{account.name}] AI failure: Leaving message in inbox.")
                elif folder in formatted_inboxes:
                    fetcher.move_message(
                        message["id"],
                        f"{email_config.folder_prefix}{folder}",
                    )
                else:
                    print(
                        f"[{account.name}] Received invalid response, please review manually."
                    )

            count += 1
    finally:
        fetcher.close()

    print_line()
    print(f"[{account.name}] Processed {count} messages.")
    print_line()

    if save_to_json:
        output_path = f"{save_to_json}-{account.name}.json"
        save_results_to_json(ai_folders, messages, output_path)
        print(f"[{account.name}] Results saved to {output_path}")

    return {
        "account_name": account.name,
        "messages_processed": count,
        "errors": errors,
        "ai_folders": ai_folders,
        "messages": messages,
    }
