import json
import queue
import socket
import threading


class LanSession:
    """Minimal LAN session supporting TCP host/join + JSON messages."""

    def __init__(self):
        self.sock = None
        self.thread = None
        self.inbox = queue.Queue()
        self.running = False

    def host(self, port=4765):
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("", port))
        listener.listen(1)
        conn, addr = listener.accept()
        listener.close()
        self._start(conn)
        return addr

    def join(self, host_ip, port=4765):
        conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        conn.connect((host_ip, port))
        self._start(conn)

    def _start(self, conn):
        self.sock = conn
        self.running = True
        self.thread = threading.Thread(target=self._reader, daemon=True)
        self.thread.start()

    def _reader(self):
        buffer = b""
        while self.running:
            try:
                data = self.sock.recv(4096)
            except OSError:
                break
            if not data:
                break
            buffer += data
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                if not line:
                    continue
                try:
                    payload = json.loads(line.decode("utf-8"))
                    self.inbox.put(payload)
                except json.JSONDecodeError:
                    continue
        self.running = False
        self.inbox.put({"type": "disconnect"})

    def send(self, message_type, payload=None):
        if not self.running or not self.sock:
            return False
        packet = json.dumps({"type": message_type, "payload": payload}).encode("utf-8") + b"\n"
        try:
            self.sock.sendall(packet)
            return True
        except OSError:
            return False

    def receive(self):
        try:
            return self.inbox.get_nowait()
        except queue.Empty:
            return None

    def close(self):
        self.running = False
        if self.sock:
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            self.sock.close()
            self.sock = None
