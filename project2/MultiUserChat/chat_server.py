import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "core"))

from core.server_classes import ChatServer

HOST = "0.0.0.0"
CHAT_PORT = 9999

if __name__ == "__main__":

    if len(sys.argv) > 1:
        try:
            CHAT_PORT = int(sys.argv[1])
        except ValueError:
            print("Invalid port number provided. Using default 9999.")

    ADMIN_PASS = "admin123"

    print("-" * 40)
    print(f"Starting Chat Server on {HOST}:{CHAT_PORT}")
    print(f"Admin Password: {ADMIN_PASS}")
    print("-" * 40)

    server = ChatServer(host=HOST, chat_port=CHAT_PORT, admin_pass=ADMIN_PASS)
    server.start()
