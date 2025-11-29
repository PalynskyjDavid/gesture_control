import socket
import json


class GestureServer:
    def __init__(self, host="127.0.0.1", port=5555, blocking=True):
        self.host = host
        self.port = port
        self.blocking = blocking

        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((self.host, self.port))
        self.server.listen(1)
        print(f"[PY] Waiting for C++ client on {self.host}:{self.port} ...")
        self.conn, addr = self.server.accept()
        print("[PY] Client connected:", addr)
        self.conn.setblocking(self.blocking)

    def send_hands(self, hands, fps=None):
        """
        hands: list of HandData
        Sends a JSON document newline-terminated.
        """
        json_hands = [h.to_dict() for h in hands]
        msg = json.dumps({"hands": [h.to_dict() for h in hands], "fps": fps}) + "\n"
        try:
            self.conn.sendall(msg.encode("utf-8"))
        except Exception as e:
            print("[PY] Send failed:", e)
            # For now exit; you may want to implement reconnect/retry
            raise
