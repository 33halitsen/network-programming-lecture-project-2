import threading
import socket
import time
import os
import json
import asyncio
from websockets.server import serve as serve_websocket
from http.server import SimpleHTTPRequestHandler, HTTPServer
from .protocol import MessageProtocol
from .utils import Logger, UserDatabase, RateLimiter


class WebServerThread(threading.Thread):
    def __init__(self, server_instance, http_port, websocket_port):
        super().__init__()
        self.server_instance = server_instance
        self.http_port = http_port
        self.websocket_port = websocket_port
        self.running = True
        self.httpd = None
        self.websocket_server = None
        self.connected_websockets = set()
        self.loop = None

    def _start_http_server(self):
        try:
            static_dir = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "..", "static"
            )

            original_dir = os.getcwd()
            os.chdir(static_dir)

            handler = SimpleHTTPRequestHandler
            self.httpd = HTTPServer(("", self.http_port), handler)
            self.server_instance.logger.log_event(
                "WEB", f"HTTP Server listening on port {self.http_port}"
            )

            self.httpd.serve_forever()

        except Exception as e:
            self.server_instance.logger.log_event(
                "CRITICAL_HTTP", f"HTTP Server error: {e}"
            )
        finally:
            try:
                os.chdir(original_dir)
            except:
                pass

    async def _handle_websocket_connection(self, websocket):
        self.connected_websockets.add(websocket)
        self.server_instance.logger.log_event(
            "WEBSOCKET", f"New connection from {websocket.remote_address}"
        )

        try:
            password = await websocket.recv()
            if password != self.server_instance.admin_password:
                await websocket.send("Authentication Failed. Connection closed.")
                self.server_instance.logger.log_event(
                    "WEBSOCKET_FAIL",
                    f"Failed authentication attempt from {websocket.remote_address}",
                )
                await websocket.close()
                return

            await websocket.send("Authentication Success. Receiving live logs.")
            self.server_instance.logger.log_event(
                "WEBSOCKET_AUTH", f"Client authenticated successfully."
            )

            await websocket.wait_closed()

        except Exception:
            pass
        finally:
            self.connected_websockets.remove(websocket)
            self.server_instance.logger.log_event("WEBSOCKET", f"Connection closed.")

    async def _start_websocket_server(self):
        self.websocket_server = serve_websocket(
            self._handle_websocket_connection, "0.0.0.0", self.websocket_port
        )
        async with self.websocket_server as server:
            await server.serve_forever()

    def run(self):
        self.logger = self.server_instance.logger

        http_thread = threading.Thread(target=self._start_http_server)
        http_thread.daemon = True
        http_thread.start()

        try:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.logger.log_event(
                "WEB", f"WebSocket Server starting on port {self.websocket_port}"
            )

            self.loop.run_until_complete(self._start_websocket_server())

        except Exception as e:
            self.logger.log_event("CRITICAL_WEB", f"Async Loop error: {e}")

    def stop(self):
        self.running = False
        if self.httpd:
            self.httpd.shutdown()
        if self.loop:
            self.loop.stop()


class ClientHandler(threading.Thread):
    def __init__(self, client_socket, address, server_instance):
        super().__init__()
        self.socket = client_socket
        self.address = address
        self.server = server_instance
        self.nickname = None
        self.logger = self.server.logger
        self.running = True

    def send_data(self, data):
        try:
            self.socket.sendall(data)
        except Exception as e:
            self.logger.log_event(
                "ERROR", f"Failed to send data to {self.nickname}: {e}"
            )
            self.close_connection()

    def close_connection(self):
        if self.running:
            self.running = False
            try:
                self.socket.shutdown(socket.SHUT_RDWR)
            except:
                pass
            self.socket.close()
            self.server.remove_client(self.nickname)

    def _handle_initial_auth(self):
        auth_req_msg = MessageProtocol.encode_message(
            MessageProtocol.TYPE_AUTH_REQ,
            {
                "content": "Welcome! Please register or login. Format: <nickname> <password>"
            },
        )
        self.send_data(auth_req_msg)

        while self.running and not self.nickname:
            try:
                raw_data = self.socket.recv(1024)
                if not raw_data:
                    break

                auth_str = raw_data.decode(MessageProtocol.ENCODING).strip()
                if not auth_str:
                    continue

                parts = auth_str.split(" ", 1)

                if len(parts) != 2:
                    error_msg = MessageProtocol.encode_message(
                        MessageProtocol.TYPE_AUTH_FAIL,
                        {"content": "Invalid format. Use: <nickname> <password>"},
                    )
                    self.send_data(error_msg)
                    continue

                requested_nick, password = parts

                if self.server.is_nickname_active(requested_nick):
                    self.logger.log_event(
                        "WARN",
                        f"Nickname '{requested_nick}' is already active. Forcing cleanup for new login.",
                    )
                    self.server.remove_client(requested_nick)
                    time.sleep(0.1)

                if self.server.user_db.authenticate_user(requested_nick, password):
                    self.nickname = requested_nick
                    self.logger.log_event(
                        "LOGIN",
                        f"User {self.nickname} logged in from {self.address[0]}",
                    )
                    return True

                elif self.server.user_db.register_user(requested_nick, password):
                    self.nickname = requested_nick
                    self.logger.log_event(
                        "REGISTER",
                        f"New user {self.nickname} registered and logged in from {self.address[0]}",
                    )
                    return True

                else:
                    error_msg = MessageProtocol.encode_message(
                        MessageProtocol.TYPE_AUTH_FAIL,
                        {
                            "content": "Authentication failed (Wrong password or nickname reserved)."
                        },
                    )
                    self.send_data(error_msg)

            except Exception as e:
                self.logger.log_event(
                    "AUTH_ERROR", f"Authentication processing error: {e}"
                )
                break

        return False

    def run(self):
        self.logger.log_event(
            "CONNECT", f"Attempting connection from {self.address[0]}:{self.address[1]}"
        )

        if not self._handle_initial_auth():
            self.close_connection()
            return

        self.server.add_client(self.nickname, self.socket, self.address, self)

        welcome_msg = MessageProtocol.encode_message(
            MessageProtocol.TYPE_AUTH_SUCCESS,
            {"content": f"Welcome back, {self.nickname}! You are now connected."},
        )
        self.send_data(welcome_msg)

        self.server.broadcast_notification(
            f"User {self.nickname} has joined the chat.", exclude_nick=self.nickname
        )

        while self.running:
            try:
                data = self.socket.recv(4096)
                if not data:
                    break

                messages = data.decode(MessageProtocol.ENCODING).split("\n")

                for msg_str in messages:
                    if msg_str.strip():
                        if self.server.rate_limiter.check_and_update(self.nickname):
                            self.server.send_system_message(
                                self.nickname,
                                "WARNING: Message rate limit exceeded. Please slow down.",
                            )
                            continue

                        msg_type, target, content = (
                            MessageProtocol.parse_client_command(msg_str)
                        )

                        if msg_type == MessageProtocol.TYPE_PUBLIC:
                            self.server.broadcast_public(self.nickname, content)
                            self.logger.log_public(self.nickname, content)

                        elif msg_type == MessageProtocol.TYPE_LIST_REQ:
                            self.server.send_active_list(self.nickname)

                        elif msg_type == MessageProtocol.CMD_EXIT:
                            self.running = False
                            break

                        elif msg_type == MessageProtocol.TYPE_PRIVATE:
                            if target and content:
                                self.server.send_private(self.nickname, target, content)
                            else:
                                self.server.send_system_message(
                                    self.nickname,
                                    "Invalid /msg format. Use: /msg <nickname> <content>",
                                )

                        else:
                            self.server.send_system_message(
                                self.nickname,
                                f"Unknown command or invalid format: {msg_str}",
                            )

            except ConnectionResetError:
                break
            except Exception as e:
                self.logger.log_event(
                    "ERROR", f"Client handler error ({self.nickname}): {e}"
                )
                break

        self.close_connection()
        self.logger.log_event("DISCONNECT", f"User {self.nickname} disconnected.")


class ChatServer:
    def __init__(
        self,
        host="0.0.0.0",
        chat_port=9999,
        http_port=8000,
        websocket_port=8001,
        admin_pass="admin123",
    ):
        self.host = host
        self.chat_port = chat_port
        self.admin_password = admin_pass

        self.clients = {}
        self.client_handlers = {}

        self.running = False

        self.logger = None
        self.user_db = UserDatabase()
        self.rate_limiter = RateLimiter()
        self.websocket_port = websocket_port
        self.http_port = http_port
        self.web_server_thread = None

    def notify_all_clients_of_list_update(self):
        active_nicks = self.get_active_nicks()

        encoded_msg = MessageProtocol.encode_message(
            MessageProtocol.TYPE_LIST,
            {"users": active_nicks, "count": len(active_nicks)},
        )

        for handler in list(self.client_handlers.values()):
            handler.send_data(encoded_msg)

    def add_client(self, nickname, client_socket, address, handler):
        if nickname and client_socket:
            self.clients[nickname] = client_socket
            self.client_handlers[nickname] = handler
            self.notify_all_clients_of_list_update()

    def remove_client(self, nickname):
        if nickname in self.clients:
            del self.clients[nickname]
        if nickname in self.client_handlers:
            del self.client_handlers[nickname]

        if nickname:
            self.broadcast_notification(f"User {nickname} has left the chat.")
            self.notify_all_clients_of_list_update()
            self.logger.log_event(
                "DISCONNECT", f"Client {nickname} removed from active list."
            )

    def is_nickname_active(self, nickname):
        return nickname in self.clients

    def get_active_nicks(self):
        return list(self.clients.keys())

    def send_system_message(self, target_nick, message):
        handler = self.client_handlers.get(target_nick)
        if handler:
            encoded_msg = MessageProtocol.encode_message(
                MessageProtocol.TYPE_SYSTEM, {"content": message}
            )
            handler.send_data(encoded_msg)

    def broadcast_notification(self, message, exclude_nick=None):
        encoded_msg = MessageProtocol.encode_message(
            MessageProtocol.TYPE_SYSTEM, {"content": message}
        )
        for handler in list(self.client_handlers.values()):
            if handler.nickname != exclude_nick:
                handler.send_data(encoded_msg)

    def broadcast_public(self, sender_nick, content):
        timestamp = time.strftime("%H:%M:%S")
        display_msg = f"[{timestamp}] <{sender_nick}>: {content}"

        encoded_msg = MessageProtocol.encode_message(
            MessageProtocol.TYPE_PUBLIC,
            {"sender": sender_nick, "content": display_msg},
        )

        for handler in list(self.client_handlers.values()):
            handler.send_data(encoded_msg)

    def send_private(self, sender_nick, target_nick, content):
        target_handler = self.client_handlers.get(target_nick)

        if not self.user_db.is_user_registered(target_nick):
            self.send_system_message(
                sender_nick, f"Error: User '{target_nick}' is not registered."
            )
            return

        self.logger.log_private(sender_nick, target_nick, content)

        if target_handler:
            timestamp = time.strftime("%H:%M:%S")
            display_msg = f"[{timestamp}] [PRIVATE from {sender_nick}]: {content}"

            encoded_msg = MessageProtocol.encode_message(
                MessageProtocol.TYPE_PRIVATE,
                {"sender": sender_nick, "content": display_msg},
            )
            target_handler.send_data(encoded_msg)

            self.send_system_message(
                sender_nick, f"[Private message sent to {target_nick}]"
            )
        else:
            self.send_system_message(
                sender_nick,
                f"Warning: User '{target_nick}' is currently offline. Message logged but not delivered.",
            )

    def send_active_list(self, target_nick):
        active_nicks = self.get_active_nicks()
        encoded_msg = MessageProtocol.encode_message(
            MessageProtocol.TYPE_LIST,
            {"users": active_nicks, "count": len(active_nicks)},
        )
        handler = self.client_handlers.get(target_nick)
        if handler:
            handler.send_data(encoded_msg)

    async def publish_log_to_websockets(self, log_entry):
        if self.web_server_thread and self.web_server_thread.connected_websockets:
            message = json.dumps({"type": "log", "content": log_entry})
            if self.web_server_thread.connected_websockets:
                await asyncio.gather(
                    *[
                        ws.send(message)
                        for ws in self.web_server_thread.connected_websockets
                    ]
                )

    def start(self):
        self.logger = Logger(server_instance=self)

        self.web_server_thread = WebServerThread(
            self, self.http_port, self.websocket_port
        )
        self.web_server_thread.start()

        self.running = True

        try:
            chat_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            chat_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            chat_socket.bind((self.host, self.chat_port))
            chat_socket.listen(5)
            self.logger.log_event(
                "SERVER", f"Server listening on {self.host}:{self.chat_port}"
            )

            while self.running:
                client_socket, address = chat_socket.accept()
                handler = ClientHandler(client_socket, address, self)
                handler.start()

        except Exception as e:
            self.logger.log_event("CRITICAL", f"Server error: {e}")
        finally:
            self.running = False
            self.logger.log_event("SERVER", "Server shutting down...")
            if self.web_server_thread:
                self.web_server_thread.stop()

            for handler in list(self.client_handlers.values()):
                handler.close_connection()
