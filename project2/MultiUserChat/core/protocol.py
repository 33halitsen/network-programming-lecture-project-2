import json


class MessageProtocol:
    MSG_SEPARATOR = "|"
    ENCODING = "utf-8"

    TYPE_AUTH_REQ = "AUTH_REQ"
    TYPE_AUTH_FAIL = "AUTH_FAIL"
    TYPE_AUTH_SUCCESS = "AUTH_SUCCESS"
    TYPE_PUBLIC = "PUBLIC"
    TYPE_PRIVATE = "PRIVATE"
    TYPE_SYSTEM = "SYSTEM"
    TYPE_LIST = "LIST"
    TYPE_LIST_REQ = "LIST_REQ"

    CMD_EXIT = "EXIT"

    @staticmethod
    def encode_message(msg_type, data):
        data_json = json.dumps(data)
        return f"{msg_type}{MessageProtocol.MSG_SEPARATOR}{data_json}".encode(
            MessageProtocol.ENCODING
        )

    @staticmethod
    def decode_message(raw_data):
        try:
            raw_str = raw_data.decode(MessageProtocol.ENCODING).strip()
            if not raw_str:
                return None, None

            parts = raw_str.split(MessageProtocol.MSG_SEPARATOR, 1)
            msg_type = parts[0]

            data_dict = json.loads(parts[1]) if len(parts) > 1 else {}

            return msg_type, data_dict

        except (ValueError, IndexError, json.JSONDecodeError, UnicodeDecodeError):
            return None, None

    @staticmethod
    def parse_client_command(text_input):
        text_input = text_input.strip()

        if not text_input.startswith("/"):
            # Public message
            return MessageProtocol.TYPE_PUBLIC, None, text_input

        parts = text_input[1:].split(" ", 2)
        command = parts[0].upper()

        if command == "MSG" and len(parts) >= 2:
            target = parts[1]
            content = parts[2] if len(parts) == 3 else ""
            return MessageProtocol.TYPE_PRIVATE, target, content

        if command == "LIST":
            return MessageProtocol.TYPE_LIST_REQ, None, None

        if command == "EXIT":
            return MessageProtocol.CMD_EXIT, None, None

        return "UNKNOWN_CMD", None, None
