import json
import time

from touch_support import is_web_platform

if not is_web_platform():
    import queue
    import socket
    import threading
else:
    queue = None
    socket = None
    threading = None


class LanSession:
    """LAN session supporting TCP host/join + JSON messages with robustness features."""

    def __init__(self):
        if queue is None or threading is None:
            raise RuntimeError("LAN multiplayer is not available on this platform")
        self.sock = None
        self.thread = None
        self.keepalive_thread = None
        self.inbox = queue.Queue()
        self.chat_inbox = queue.Queue(maxsize=100)  # Bounded to prevent memory growth
        self.stop_event = threading.Event()
        self.last_received = 0
        self.connection_timeout = 30  # seconds without message = disconnect
        self.keepalive_interval = 5   # send keepalive every 5 seconds

        # Thread safety: lock for all socket send/recv/close operations
        self._sock_lock = threading.Lock()
        # Prevent duplicate disconnect messages from reader + keepalive threads
        self._disconnect_sent = False

        # JSON error recovery (10 consecutive strikes = disconnect)
        self.parse_error_count = 0
        self.max_parse_errors = 10

        # Ping/latency tracking
        self.current_rtt = 0  # milliseconds
        self.last_ping_time = 0

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
        try:
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if timeout:
                listener.settimeout(timeout)
            listener.bind(("", port))
            listener.listen(1)
            conn, addr = listener.accept()
        except Exception:
            listener.close()
            raise
        else:
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
        try:
            conn.settimeout(timeout)
            conn.connect((host_ip, port))
            conn.settimeout(None)  # Remove timeout after successful connection
            self._start(conn)
        except Exception:
            conn.close()
            raise

    def _start(self, conn):
        self.sock = conn
        # Set TCP keepalive at OS level
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        # Disable Nagle's algorithm — critical for low-latency small packets (co-op 20Hz snapshots)
        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
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
                # No lock needed for recv — TCP supports concurrent send+recv on separate threads.
                # Locking recv would block send() for up to 1s (the socket timeout).
                sock = self.sock
                if not sock:
                    break
                data = sock.recv(4096)
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
                    # Reset error counter on successful parse
                    self.parse_error_count = 0

                    msg_type = payload.get("type")

                    # Filter out keepalive messages (don't put in inbox)
                    if msg_type == "keepalive":
                        continue

                    # Handle ping/pong for latency measurement
                    if msg_type == "ping":
                        # Respond with pong containing the same timestamp
                        timestamp = payload.get("payload", {}).get("timestamp", 0)
                        self.send("pong", {"timestamp": timestamp})
                        continue
                    elif msg_type == "pong":
                        # Calculate RTT from the timestamp
                        timestamp = payload.get("payload", {}).get("timestamp", 0)
                        if timestamp:
                            self.current_rtt = int((time.time() - timestamp) * 1000)
                        continue

                    # Route chat-related messages to dedicated queue
                    if msg_type in ("chat", "chat_ack", "typing"):
                        try:
                            self.chat_inbox.put_nowait(payload)
                        except queue.Full:
                            pass  # Discard overflow — stale chat messages are acceptable to drop
                    else:
                        self.inbox.put(payload)
                except json.JSONDecodeError as e:
                    self.parse_error_count += 1
                    # Log corrupted data for debugging (truncated to avoid spam)
                    corrupted_preview = line[:100].decode("utf-8", errors="replace")
                    print(f"[LanSession] JSON parse error #{self.parse_error_count}: {e}")
                    print(f"[LanSession] Corrupted data preview: {corrupted_preview}...")

                    if self.parse_error_count >= self.max_parse_errors:
                        print("[LanSession] Too many parse errors, disconnecting")
                        self.stop_event.set()
                        break
                    continue  # Try next message instead of disconnecting

        self.stop_event.set()
        # Send disconnect to queues only once (reader or keepalive, whichever exits first)
        with self._sock_lock:
            if not self._disconnect_sent:
                self._disconnect_sent = True
                self.inbox.put({"type": "disconnect"})
                self.chat_inbox.put({"type": "disconnect"})

    def _keepalive_sender(self):
        """Send periodic ping messages to keep connection alive and measure latency.

        The ping/pong already serves as a keepalive — no need for a separate
        keepalive packet.  This halves idle network overhead.
        """
        while not self.stop_event.is_set():
            time.sleep(self.keepalive_interval)
            if not self.stop_event.is_set():
                try:
                    # Ping doubles as keepalive — pong response keeps connection alive
                    self.last_ping_time = time.time()
                    ping_packet = json.dumps({
                        "type": "ping",
                        "payload": {"timestamp": self.last_ping_time}
                    }).encode("utf-8") + b"\n"
                    with self._sock_lock:
                        if self.sock:
                            self.sock.sendall(ping_packet)
                except OSError:
                    # Connection lost — send disconnect only once
                    self.stop_event.set()
                    with self._sock_lock:
                        if not self._disconnect_sent:
                            self._disconnect_sent = True
                            self.inbox.put({"type": "disconnect"})
                            self.chat_inbox.put({"type": "disconnect"})
                    break

    def is_connected(self):
        """Check if the session is still connected."""
        return not self.stop_event.is_set() and self.sock is not None

    def get_latency(self):
        """Get the current round-trip time in milliseconds."""
        return self.current_rtt

    def get_latency_status(self):
        """Get latency status as a tuple (color, label).

        Returns:
            tuple: (color_rgb, label_string)
                - Green (0, 255, 0): <50ms "Good"
                - Yellow (255, 255, 0): 50-150ms "Fair"
                - Red (255, 0, 0): >150ms "Poor"
        """
        rtt = self.current_rtt
        if rtt < 50:
            return ((100, 255, 100), "Good")
        elif rtt < 150:
            return ((255, 255, 100), "Fair")
        else:
            return ((255, 100, 100), "Poor")

    def receive(self):
        """
        Retrieve a message from the inbox queue (non-blocking).

        Returns:
            Message dict if available, None otherwise
        """
        try:
            return self.inbox.get_nowait()
        except queue.Empty:
            return None

    def send(self, message_type, payload=None):
        if self.stop_event.is_set():
            return False
        packet = json.dumps({"type": message_type, "payload": payload}).encode("utf-8") + b"\n"
        try:
            with self._sock_lock:
                if not self.sock:
                    return False
                self.sock.sendall(packet)
            return True
        except OSError:
            return False

    def close(self):
        self.stop_event.set()
        with self._sock_lock:
            sock = self.sock
            self.sock = None
        if sock:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            sock.close()
        # Join threads to ensure clean shutdown
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=3)
        if self.keepalive_thread and self.keepalive_thread.is_alive():
            self.keepalive_thread.join(timeout=3)