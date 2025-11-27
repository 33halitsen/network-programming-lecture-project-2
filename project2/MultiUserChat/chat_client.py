import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "core"))

from core.client_classes import ChatClient

HOST = "127.0.0.1"
PORT = 9999

if __name__ == "__main__":

    if len(sys.argv) > 1:
        HOST = sys.argv[1]
    if len(sys.argv) > 2:
        try:
            PORT = int(sys.argv[2])
        except ValueError:
            print("Invalid port number provided. Using default 9999.")

    print("-" * 40)
    print(f"Attempting connection to {HOST}:{PORT}")
    print("-" * 40)

    client = ChatClient(host=HOST, port=PORT)
    client.start()
