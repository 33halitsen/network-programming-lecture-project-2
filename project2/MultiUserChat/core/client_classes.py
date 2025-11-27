import threading
import time
import socket
import sys
import os
from .protocol import MessageProtocol


class MessageListener(threading.Thread):
    def __init__(self, client_instance, client_socket):
        super().__init__()
        self.client = client_instance
        self.socket = client_socket
        self.running = True

    def run(self):
        while self.running:
            try:
                data = self.socket.recv(4096)
                if not data:
                    print("\n[SYSTEM] Server closed the connection.")
                    self.client.disconnect(is_remote=True)
                    break

                msg_type, data_dict = MessageProtocol.decode_message(data)

                if msg_type:
                    self.client.display_message(msg_type, data_dict)

            except ConnectionAbortedError:
                break
            except ConnectionResetError:
                print("\n[SYSTEM] Connection with server was lost.")
                self.client.disconnect(is_remote=True)
                break
            except Exception:
                break


class ChatClient:
    def __init__(self, host="127.0.0.1", port=9999):
        self.host = host
        self.port = port
        self.socket = None
        self.nickname = None
        self.is_connected = False
        self.listener = None
        self.chat_focus = None
        self.auth_event = threading.Event()

    def _handle_auth_prompt(self):

        while self.is_connected and not self.nickname:
            sys.stdout.write("Auth> ")
            sys.stdout.flush()

            try:
                auth_input = sys.stdin.readline().strip()
                if not auth_input:
                    continue

                self.send_raw_data((auth_input + "\n").encode(MessageProtocol.ENCODING))

                self.auth_event.wait()
                self.auth_event.clear()

                if self.nickname:
                    break

            except EOFError:
                self.disconnect()
                break
            except Exception:
                break

        return self.nickname is not None

    def re_prompt(self):
        """Thread-safe prompt writing."""
        if self.nickname and self.is_connected:
            prompt = f"[{self.chat_focus}]> " if self.chat_focus else "You> "
            sys.stdout.write(f"\r{prompt}")
            sys.stdout.flush()

    def display_message(self, msg_type, data):
        content = data.get("content", "Unknown message.")

        sys.stdout.write("\n")

        if msg_type == MessageProtocol.TYPE_AUTH_REQ:
            print(f"[AUTH REQUIRED] {content}")

        elif msg_type == MessageProtocol.TYPE_AUTH_FAIL:
            print(f"[AUTH FAILED] {content}")
            self.auth_event.set()

        elif msg_type == MessageProtocol.TYPE_AUTH_SUCCESS:
            print(f"[AUTH SUCCESS] {content}")
            try:
                if "Welcome back, " in content:
                    nickname_part = content.split("Welcome back, ")[1]
                    extracted_nick = nickname_part.split("!")[0].strip()
                    if extracted_nick:
                        self.nickname = extracted_nick
            except Exception:
                pass
            self.auth_event.set()

        elif msg_type == MessageProtocol.TYPE_PUBLIC:
            print(f"{content}")

        elif msg_type == MessageProtocol.TYPE_PRIVATE:
            print(f"{content}")

        elif msg_type == MessageProtocol.TYPE_LIST:
            users = data.get("users", [])
            count = data.get("count", 0)
            print(f"--- ACTIVE USERS ({count}) ---")
            print(" | ".join(users))
            print("---------------------------")

        elif msg_type == MessageProtocol.TYPE_SYSTEM:
            print(f"[SYSTEM] {content}")

        if self.nickname:
            self.re_prompt()

    def send_raw_data(self, data):
        try:
            if self.is_connected:
                self.socket.sendall(data)
        except Exception as e:
            print(f"\n[SYSTEM] Failed to send data: {e}")
            self.disconnect()

    def handle_user_input(self):
        self.re_prompt()

        while self.is_connected and self.nickname:
            try:
                text_input = sys.stdin.readline().strip()

                if not text_input:
                    self.re_prompt()
                    continue

                if text_input.startswith("/"):
                    if text_input.upper() == "/EXIT":
                        self.disconnect()
                        break

                    parts = text_input[1:].split(" ", 2)
                    command = parts[0].upper()

                    if command in ["MSG", "FOCUS"]:
                        if len(parts) >= 2:
                            target = parts[1]
                            if target.upper() == "PUBLIC":
                                self.chat_focus = None
                                print("[SYSTEM] Focus reset to Public Chat.")
                            else:
                                self.chat_focus = target
                                print(f"[SYSTEM] Chat focus set to {self.chat_focus}.")

                            self.re_prompt()
                            if len(parts) == 2:
                                continue
                        else:
                            print("[SYSTEM] Invalid format. Use: /msg <nick> <msg>")
                            self.re_prompt()
                            continue

                final_target = self.chat_focus
                final_input = text_input

                if final_target:
                    if not text_input.startswith("/"):
                        final_input = f"/msg {final_target} {text_input}"

                self.send_raw_data(
                    (final_input + "\n").encode(MessageProtocol.ENCODING)
                )
            except Exception as e:
                print(f"\n[ERROR] Input handling error: {e}")
                self.disconnect()
                break

    def connect(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.is_connected = True
            print(f"[SYSTEM] Connected to server at {self.host}:{self.port}")

            self.listener = MessageListener(self, self.socket)
            self.listener.start()
            return True

        except ConnectionRefusedError:
            print("[ERROR] Connection refused. Make sure the server is running.")
            return False
        except Exception as e:
            print(f"[ERROR] Connection error: {e}")
            return False

    def disconnect(self, is_remote=False):
        if self.is_connected:
            self.is_connected = False

            if not is_remote and self.socket:
                try:
                    self.socket.sendall(
                        ("/EXIT" + "\n").encode(MessageProtocol.ENCODING)
                    )
                    time.sleep(0.2)
                except Exception:
                    pass

            if self.listener:
                self.listener.running = False

            try:
                self.socket.close()
            except:
                pass

            print("\n[SYSTEM] Connection closed. Application terminating.")
            os._exit(0)

    def start(self):
        if self.connect():
            if self._handle_auth_prompt():
                print(
                    "\n--- You are now in the main chat. Available commands: /list /msg <nick> /exit ---"
                )
                self.handle_user_input()
