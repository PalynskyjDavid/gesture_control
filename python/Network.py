import socket
import json


# ==========================================
# 3. NETWORK ENGINE
# ==========================================
class NetworkBridge:
    def __init__(self, host="127.0.0.1", port=5555):
        self.addr = (host, port)
        self.sock = None
        self.conn = None
        self._setup_server()

    def _setup_server(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind(self.addr)
            self.sock.listen(1)
            self.sock.setblocking(False)  # Non-blocking accept
            print(f"[NET] Listening on {self.addr}...")
        except Exception as e:
            print(f"[NET] Init Error: {e}")

    def update(self):
        """Check for new connections non-blockingly"""
        if self.conn is None:
            try:
                self.conn, addr = self.sock.accept()
                self.conn.setblocking(True)  # Blocking sends
                print(f"[NET] Connected: {addr}")
            except BlockingIOError:
                pass

    def send_event(self, event_data):
        if not self.conn:
            return
        try:
            # Create lightweight JSON payload
            msg = json.dumps(event_data) + "\n"
            self.conn.sendall(msg.encode("utf-8"))
        except (BrokenPipeError, ConnectionResetError):
            print("[NET] Client disconnected")
            self.conn = None
