from __future__ import annotations

import json
from typing import Any

class JSONEmailFetcher:
    def __init__(self, json_file: str) -> None:
        with open(json_file, 'r') as file:
            self.data: dict[str, Any] = json.load(file)
        self.ai_folders: list[str] = self.data.get("ai_folders", [])
        self.messages: list[dict[str, Any]] = self.data.get("messages", [])
        self.current_index: int = 0

    def list_ai_folders(self) -> list[str]:
        return self.ai_folders

    def fetch_next_message(self) -> dict[str, Any] | None:
        if self.current_index >= len(self.messages):
            return None

        message = self.messages[self.current_index]
        self.current_index += 1
        return {
            "id": message["id"],
            "from": message["from"],
            "subject": message["subject"],
            "body": message["body"],
            "responses": message.get("responses", [])
        }

    def has_more_messages(self) -> bool:
        return self.current_index < len(self.messages)

    def set_unseen(self, message_id: int) -> None:
        # No-op for JSON data, but could log or print an action
        print(f"Message {message_id} would be marked as unseen in a real environment.")

    def move_message(self, message_id: int, target_folder: str) -> None:
        # No-op for JSON data, but could log or print an action
        print(f"Message {message_id} would be moved to {target_folder} in a real environment.")

    def close(self) -> None:
        # No-op for JSON data, but could log or print an action
        print("Closing JSON email fetcher.")
