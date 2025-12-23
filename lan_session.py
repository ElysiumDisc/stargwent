import json
import queue
import socket
import threading
import time


class LanSession:
    """LAN session supporting TCP host/join + JSON messages with robustness features."""

    def __init__(self):
        self.sock = None
        self.thread = None
        self.keepalive_thread = None
        self.inbox = queue.Queue()
        self.stop_event = threading.Event()
        self.last_received = 0
        self.connection_timeout = 30  # seconds without message = disconnect
        self.keepalive_interval = 5   # send keepalive every 5 seconds

    def host(self, port=4765, timeout=None):
        """
        Host a game on the specified port.

        Args:
            port: Port to listen on
            timeout: Optional timeout in seconds (None = block forever)

        Returns:
            Client address tuple (ip, port)

        Raises:
            socket.timeout: If timeout expires before client connects
            OSError: If port is unavailable
        """
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if timeout:
            listener.settimeout(timeout)
        listener.bind(("", port))
        listener.listen(1)
        try:
            conn, addr = listener.accept()
        finally:
            listener.close()
        self._start(conn)
        return addr

    def join(self, host_ip, port=4765, timeout=10):
        """
        Join a hosted game.

        Args:
            host_ip: Host's IP address
            port: Port to connect to
            timeout: Connection timeout in seconds

        Raises:
            socket.timeout: If connection times out
            ConnectionRefusedError: If host is not listening
        """
        conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        conn.settimeout(timeout)
        conn.connect((host_ip, port))
        conn.settimeout(None)  # Remove timeout after successful connection
        self._start(conn)

    def _start(self, conn):
        self.sock = conn
        # Set TCP keepalive at OS level
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        # Set socket timeout for recv
        self.sock.settimeout(1.0)  # 1 second timeout for recv

        self.stop_event.clear()
        self.last_received = time.time()

        self.thread = threading.Thread(target=self._reader, daemon=True)
        self.thread.start()

        self.keepalive_thread = threading.Thread(target=self._keepalive_sender, daemon=True)
        self.keepalive_thread.start()

    def _reader(self):
        buffer = b""
        while not self.stop_event.is_set():
            try:
                data = self.sock.recv(4096)
                if not data:
                    # Connection closed cleanly
                    break
                self.last_received = time.time()
                buffer += data
            except socket.timeout:
                # Check if we've timed out waiting for any message
                if time.time() - self.last_received > self.connection_timeout:
                    print(f"[LanSession] Connection timeout - no data for {self.connection_timeout}s")
                    break
                continue
            except OSError as e:
                print(f"[LanSession] Socket error: {e}")
                break

            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                if not line:
                    continue
                try:
                    payload = json.loads(line.decode("utf-8"))
                    # Filter out keepalive messages (don't put in inbox)
                    if payload.get("type") != "keepalive":
                        self.inbox.put(payload)
                except json.JSONDecodeError:
                    print("[LanSession] Error: Received malformed JSON. Closing connection to prevent state corruption.")
                    self.stop_event.set()
                    break

        self.stop_event.set()
        self.inbox.put({"type": "disconnect"})

    def _keepalive_sender(self):
        """Send periodic keepalive messages to detect dead connections."""
        while not self.stop_event.is_set():
            time.sleep(self.keepalive_interval)
            if not self.stop_event.is_set():
                try:
                    # Send minimal keepalive packet
                    packet = json.dumps({"type": "keepalive"}).encode("utf-8") + b"\n"
                    self.sock.sendall(packet)
                except OSError:
                    # Connection lost
                    self.stop_event.set()
                    self.inbox.put({"type": "disconnect"})
                    break

    def is_connected(self):
        """Check if the session is still connected."""
        return not self.stop_event.is_set() and self.sock is not None

    def send(self, message_type, payload=None):
        if self.stop_event.is_set() or not self.sock:
            return False
        packet = json.dumps({"type": message_type, "payload": payload}).encode("utf-8") + b"\n"
        try:
            self.sock.sendall(packet)
            return True
        except OSError:
            return False

    def close(self):
        self.stop_event.set()
        if self.sock:
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            self.sock.close()
            self.sock = None