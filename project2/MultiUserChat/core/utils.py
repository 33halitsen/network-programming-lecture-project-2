import json
import os
import time
import hashlib
import asyncio
from datetime import datetime


class UserDatabase:

    def __init__(self, db_file="user_db.json"):
        self.db_file = db_file
        self.users = self._load_users()

    def _load_users(self):
        if os.path.exists(self.db_file):
            try:
                with open(self.db_file, "r") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return {}
        return {}

    def _save_users(self):
        with open(self.db_file, "w") as f:
            json.dump(self.users, f, indent=4)

    def _hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()

    def register_user(self, nickname, password):

        if nickname in self.users:
            return False

        if nickname.startswith("*"):
            return False

        hashed_password = self._hash_password(password)
        self.users[nickname] = {
            "password": hashed_password,
            "registered_at": datetime.now().isoformat(),
        }
        self._save_users()
        return True

    def is_user_registered(self, nickname):
        return nickname in self.users

    def authenticate_user(self, nickname, password):

        if nickname not in self.users:
            return False

        hashed_password = self._hash_password(password)
        return self.users[nickname]["password"] == hashed_password

    def get_all_users(self):
        return list(self.users.keys())


LOG_BASE_PATH = "log"
USER_DATA_PATH = os.path.join(LOG_BASE_PATH, "user_data")


class Logger:
    def __init__(self, server_instance=None, base_path=LOG_BASE_PATH):
        self.server_instance = server_instance
        self.base_path = base_path
        os.makedirs(self.base_path, exist_ok=True)
        self.user_data_path = USER_DATA_PATH
        os.makedirs(self.user_data_path, exist_ok=True)
        self.system_log_file = os.path.join(self.base_path, "system_events.log")

    def _get_chat_file_path(self, user1, user2):
        sender_dir = os.path.join(self.user_data_path, user1)
        os.makedirs(sender_dir, exist_ok=True)
        chat_dir = os.path.join(sender_dir, user2)
        os.makedirs(chat_dir, exist_ok=True)
        today_str = datetime.now().strftime("%Y%m%d")
        return os.path.join(chat_dir, f"{today_str}.log")

    def _write_log(self, file_path, log_entry):
        try:
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(f"{log_entry}\n")
        except Exception as e:
            print(f"[FATAL LOG ERROR] Failed to write log to {file_path}: {e}")

    def log_event(self, level, message):
        timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        log_entry = f"{timestamp} [{level.upper()}]: {message}"
        print(log_entry)
        self._write_log(self.system_log_file, log_entry)
        if (
            self.server_instance
            and self.server_instance.web_server_thread
            and self.server_instance.web_server_thread.loop
        ):

            asyncio.run_coroutine_threadsafe(
                self.server_instance.publish_log_to_websockets(log_entry),
                self.server_instance.web_server_thread.loop,
            )

    def log_public(self, sender, content):
        self.log_event("PUBLIC_MSG", f"<{sender}>: {content}")

    def log_private(self, sender, recipient, content):
        timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        log_entry = f"{timestamp} <{sender} -> {recipient}>: {content}"
        sender_path = self._get_chat_file_path(sender, recipient)
        self._write_log(sender_path, log_entry)
        recipient_path = self._get_chat_file_path(recipient, sender)
        self._write_log(recipient_path, log_entry)


class RateLimiter:
    def __init__(self, max_messages=5, window_seconds=5):
        self.max_messages = max_messages
        self.window_seconds = window_seconds
        self.message_timestamps = {}

    def check_and_update(self, nickname):
        current_time = time.time()

        if nickname not in self.message_timestamps:
            self.message_timestamps[nickname] = []

        timestamps = self.message_timestamps[nickname]

        timestamps[:] = [
            t for t in timestamps if t > current_time - self.window_seconds
        ]

        if len(timestamps) >= self.max_messages:
            return True
        else:
            timestamps.append(current_time)
            return False
