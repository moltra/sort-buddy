import argparse
import os
import signal
import sys
from typing import Any
from colorama import Fore, Style, init as colorama_init  # type: ignore[import-untyped]
from datetime import datetime
from dotenv import load_dotenv
from loguru import logger
from email_fetcher import EmailFetcher
from json_email_fetcher import JSONEmailFetcher
from ai import get_ai_response_from_message, configure_openai
from util import get_stripped_folder_list, save_results_to_json, signal_handler, print_line, configure_audit_logger

from accounts_config import AccountsConfig
from account_processor import process_account

load_dotenv()


def _run_single_account(
    dry_run: bool,
    show_prompt: bool,
    no_color: bool,
    limit: int | None,
    save_to_json: str | None,
    use_json: str | None,
    show_rate_limits: bool,
) -> dict[str, Any]:
    """Process a single account using legacy environment-based config."""
    configure_openai()
    colorama_init(strip=no_color)

    fetcher: EmailFetcher | JSONEmailFetcher
    if use_json:
        fetcher = JSONEmailFetcher(use_json)
        dry_run = True
    else:
        fetcher = EmailFetcher(dry_run)

    print_line()
    print(f"Fetching list of folders that start with {os.getenv('FOLDER_PREFIX')}...")
    ai_folders = fetcher.list_ai_folders()

    formatted_inboxes = get_stripped_folder_list(ai_folders)
    messages: list[dict[str, Any]] = []
    print(f"Found {len(ai_folders)} folders: {ai_folders}")

    count = 0
    while fetcher.has_more_messages():
        if limit is not None and count >= limit:
            break

        message = fetcher.fetch_next_message()
        if not message:
            continue

        print_line()
        print(f"{Fore.BLUE}From:{Style.RESET_ALL} {Fore.CYAN}{message['from']}{Style.RESET_ALL}")
        print(f"{Fore.BLUE}Subject:{Style.RESET_ALL} {Fore.CYAN}{message['subject']}{Style.RESET_ALL}")

        folder, explanation = get_ai_response_from_message(message, formatted_inboxes, show_prompt, show_rate_limits)

        logger.info(
            f"message_id={message['id']} from={message['from']} "
            f"subject={message['subject']} folder={folder} explanation={explanation}"
        )

        print(f" --> {Fore.GREEN}{folder}{Style.RESET_ALL}: {Fore.WHITE}{explanation}{Style.RESET_ALL}")

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
                print("Leaving message in inbox.")

            elif folder == "invalid":
                print("AI failure: Leaving message in inbox.")

            elif folder in formatted_inboxes:
                fetcher.move_message(message["id"], f"{os.getenv('FOLDER_PREFIX')}{folder}")
                logger.info(f"message_id={message['id']} action=move target_folder={folder}")

            else:
                print("Received invalid response, please review manually.")

        count += 1

    fetcher.close()

    print_line()
    print(f"Processed {count} messages.")
    print_line()

    if save_to_json:
        save_results_to_json(ai_folders, messages, save_to_json)
        print(f"Results saved to {save_to_json}")

    return {
        "messages_processed": count,
        "ai_folders": ai_folders,
        "messages": messages,
    }


def _run_multi_account(
    accounts_file: str,
    account_name: str | None,
    dry_run: bool,
    show_prompt: bool,
    no_color: bool,
    limit: int | None,
    save_to_json: str | None,
    show_rate_limits: bool,
) -> None:
    """Process one or more accounts from an accounts configuration file."""
    configure_openai()
    colorama_init(strip=no_color)

    try:
        accounts = AccountsConfig.from_yaml(accounts_file)
    except Exception as exc:
        print(f"Error loading accounts file: {exc}")
        sys.exit(1)

    if account_name:
        account = accounts.get_account(account_name)
        if account is None:
            print(f"Account not found or disabled: {account_name}")
            sys.exit(1)
        accounts_to_process = [account]
    else:
        accounts_to_process = accounts.get_enabled_accounts()

    for account in accounts_to_process:
        try:
            stats = process_account(
                account,
                dry_run=dry_run,
                limit=limit,
                show_prompt=show_prompt,
                show_rate_limits=show_rate_limits,
                save_to_json=save_to_json,
            )
            print(f"[{account.name}] Done. Processed {stats['messages_processed']} messages.")
        except Exception:
            logger.exception("[%s] Account processing failed", account.name)


def main(
        dry_run: bool = False,
        show_prompt: bool = False,
        no_color: bool = False,
        limit: int | None = None,
        save_to_json: str | None = None,
        use_json: str | None = None,
        show_rate_limits: bool = False,
        accounts_file: str | None = None,
        account_name: str | None = None) -> None:

    configure_audit_logger()

    if accounts_file:
        _run_multi_account(
            accounts_file,
            account_name,
            dry_run,
            show_prompt,
            no_color,
            limit,
            save_to_json,
            show_rate_limits,
        )
    else:
        _run_single_account(
            dry_run,
            show_prompt,
            no_color,
            limit,
            save_to_json,
            use_json,
            show_rate_limits,
        )


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)

    parser = argparse.ArgumentParser(description="Parse emails and process them.")
    parser.add_argument("--dry-run", action="store_true", help="Only print prompts and messages without processing them.")
    parser.add_argument("--show-prompt", action="store_true", help="Show the prompt, minus the body of the email.")
    parser.add_argument("--no-color", action="store_true", help="Disable color output.")
    parser.add_argument("--limit", type=int, help="Limit the number of messages to process.")
    parser.add_argument("--save-to-json", type=str, help="Save the results to a JSON file.")
    parser.add_argument("--use-json", type=str, help="Use a JSON file for input instead of connecting to IMAP.")
    parser.add_argument("--print-rate-limits", action="store_true", help="Show the rate limits header from the OpenAI API response.")
    parser.add_argument("--accounts", type=str, help="Path to a multi-account YAML configuration file.")
    parser.add_argument("--account", type=str, help="Process only the named account from the accounts file.")
    args = parser.parse_args()

    logger.remove()
    logger.add(sys.stderr, level="INFO")

    main(
        dry_run=args.dry_run,
        show_prompt=args.show_prompt,
        no_color=args.no_color,
        limit=args.limit,
        save_to_json=args.save_to_json,
        use_json=args.use_json,
        show_rate_limits=args.print_rate_limits,
        accounts_file=args.accounts,
        account_name=args.account,
    )
