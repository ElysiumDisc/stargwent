import json
import time
from collections import deque

from touch_support import is_web_platform

if not is_web_platform():
    import queue
    import socket
    import threading
else:
    queue = None
    socket = None
    threading = None


class ProtocolVersionMismatch(Exception):
    """Raised when LAN peers speak incompatible protocol versions."""

    def __init__(self, local_version, peer_version, peer_game_version=None):
        self.local_version = local_version
        self.peer_version = peer_version
        self.peer_game_version = peer_game_version
        super().__init__(
            f"Protocol version mismatch: local={local_version}, peer={peer_version}"
            + (f" (peer game {peer_game_version})" if peer_game_version else "")
        )


class LanSession:
    """LAN session supporting TCP host/join + JSON messages with robustness features."""

    def __init__(self):
        if queue is None or threading is None:
            raise RuntimeError("LAN multiplayer is not available on this platform")
        self.sock = None
        self.thread = None
        self.keepalive_thread = None
        # deque with maxlen auto-drops oldest on overflow; append/popleft are
        # atomic under CPython's GIL (single-producer reader thread pattern).
        self.inbox = deque(maxlen=1000)
        self.chat_inbox = queue.Queue(maxsize=100)  # Bounded to prevent memory growth
        self.stop_event = threading.Event()
        self.last_received = 0
        self.connection_timeout = 30  # seconds without message = disconnect
        self.keepalive_interval = 5   # send keepalive every 5 seconds

        # Thread safety: lock for all socket send/recv/close operations
        self._sock_lock = threading.Lock()
        # Prevent duplicate disconnect messages from reader + keepalive threads
        self._disconnect_sent = False

        # JSON error recovery (consecutive strikes = disconnect)
        self.parse_error_count = 0
        self.max_parse_errors = 5

        # Buffer size limit to prevent OOM from malicious peers (1 MB)
        self.max_buffer_size = 1024 * 1024

        # Ping/latency tracking
        self.current_rtt = 0  # milliseconds
        self.last_ping_time = 0
        self._ping_id = 0

        # Protocol handshake (L1): populated by the reader thread as soon
        # as the peer's HELLO message arrives so the main thread can
        # block on it without touching the inbox deque.
        self.peer_hello = None
        # Signalled by the reader thread when peer_hello is populated, so
        # handshake() can wait without burning CPU on a sleep poll.
        self._peer_hello_event = threading.Event()

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
        self.last_received = time.monotonic()

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
                self.last_received = time.monotonic()
                buffer += data
                # Prevent OOM: drop connection if buffer grows beyond limit
                # (peer sending data without newline delimiters)
                if len(buffer) > self.max_buffer_size:
                    print(f"[LanSession] Buffer overflow ({len(buffer)} bytes) — disconnecting")
                    break
            except socket.timeout:
                # Check if we've timed out waiting for any message
                if time.monotonic() - self.last_received > self.connection_timeout:
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

                    # Capture HELLO handshake directly (L1) — the main
                    # thread waits on _peer_hello_event rather than scanning
                    # the inbox deque or polling on sleep.
                    if msg_type == "hello":
                        self.peer_hello = payload.get("payload", {})
                        self._peer_hello_event.set()
                        continue

                    # Handle ping/pong for latency measurement
                    if msg_type == "ping":
                        # Respond with pong containing the same timestamp and id
                        ping_payload = payload.get("payload", {})
                        self.send("pong", {"timestamp": ping_payload.get("timestamp", 0), "id": ping_payload.get("id", 0)})
                        continue
                    elif msg_type == "pong":
                        # Calculate RTT from the timestamp, only if ping_id matches
                        pong_payload = payload.get("payload", {})
                        if pong_payload.get("id") == self._ping_id:
                            timestamp = pong_payload.get("timestamp", 0)
                            if timestamp:
                                self.current_rtt = int((time.monotonic() - timestamp) * 1000)
                        continue

                    # Route chat-related messages to dedicated queue
                    if msg_type in ("chat", "chat_ack", "typing"):
                        try:
                            self.chat_inbox.put_nowait(payload)
                        except queue.Full:
                            pass  # Discard overflow — stale chat messages are acceptable to drop
                    else:
                        self.inbox.append(payload)
                except json.JSONDecodeError as e:
                    with self._sock_lock:
                        self.parse_error_count += 1
                        error_count = self.parse_error_count
                    # Log corrupted data for debugging (truncated to avoid spam)
                    corrupted_preview = line[:100].decode("utf-8", errors="replace")
                    print(f"[LanSession] JSON parse error #{error_count}: {e}")
                    print(f"[LanSession] Corrupted data preview: {corrupted_preview}...")

                    if error_count >= self.max_parse_errors:
                        print("[LanSession] Too many parse errors, disconnecting")
                        self.stop_event.set()
                        break
                    continue  # Try next message instead of disconnecting

        self.stop_event.set()
        # Send disconnect to queues only once (reader or keepalive, whichever exits first)
        with self._sock_lock:
            if not self._disconnect_sent:
                self._disconnect_sent = True
                self.inbox.append({"type": "disconnect"})
                self._send_disconnect_to_chat()

    def _send_disconnect_to_chat(self):
        """Push a disconnect sentinel into chat_inbox without blocking.

        If the queue is full, drop the oldest entry to make room — the
        disconnect message must reach the UI even when chat is saturated.
        """
        sentinel = {"type": "disconnect"}
        try:
            self.chat_inbox.put_nowait(sentinel)
        except queue.Full:
            try:
                self.chat_inbox.get_nowait()
            except queue.Empty:
                pass
            try:
                self.chat_inbox.put_nowait(sentinel)
            except queue.Full:
                pass  # Best-effort; UI will see disconnect via inbox anyway

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
                    self._ping_id += 1
                    self.last_ping_time = time.monotonic()
                    ping_packet = json.dumps({
                        "type": "ping",
                        "payload": {"timestamp": self.last_ping_time, "id": self._ping_id}
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
                            self.inbox.append({"type": "disconnect"})
                            self._send_disconnect_to_chat()
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
            return self.inbox.popleft()
        except IndexError:
            return None

    def send(self, message_type, payload=None):
        if self.stop_event.is_set():
            return False
        try:
            packet = json.dumps({"type": message_type, "payload": payload}).encode("utf-8") + b"\n"
        except (TypeError, ValueError) as e:
            print(f"[LanSession] Failed to serialize message '{message_type}': {e}")
            return False
        try:
            with self._sock_lock:
                if not self.sock:
                    return False
                self.sock.sendall(packet)
            return True
        except OSError:
            return False

    def handshake(self, game_version, role, player_name=None, timeout=5.0):
        """Exchange HELLO packets with the peer and verify protocol compatibility.

        Called after host/join connects but before any game messages are
        sent. Both sides send their HELLO immediately; both sides then
        wait for the peer's HELLO to arrive (captured by the reader
        into ``self.peer_hello``).

        Args:
            game_version: Local game version string (e.g. "11.0.0").
            role: "host" or "client".
            player_name: Optional custom player name.
            timeout: Seconds to wait for peer HELLO before giving up.

        Returns:
            The peer's HELLO payload dict on success:
            ``{"protocol_version", "game_version", "role", "player_name"?}``.

        Raises:
            ProtocolVersionMismatch: Peer speaks a different PROTOCOL_VERSION.
            TimeoutError: Peer did not send HELLO within *timeout* seconds.
            OSError: Underlying socket error.
        """
        # Import here to avoid a hard lan_protocol dependency at module
        # load time (the web build stubs out socket support).
        from lan_protocol import build_hello_message, PROTOCOL_VERSION

        hello = build_hello_message(game_version, role, player_name=player_name)
        if not self.send(hello["type"], hello["payload"]):
            raise OSError("Failed to send HELLO handshake")

        # Block on the reader-set event with bounded waits so we still
        # notice a connection close without spinning on sleep().
        deadline = time.monotonic() + timeout
        while self.peer_hello is None:
            if self.stop_event.is_set():
                raise OSError("Connection closed during handshake")
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("Peer did not send HELLO within timeout")
            # Poll stop_event at 250ms granularity so close() doesn't wedge.
            self._peer_hello_event.wait(timeout=min(0.25, remaining))

        peer = self.peer_hello
        peer_version = peer.get("protocol_version")
        if peer_version != PROTOCOL_VERSION:
            raise ProtocolVersionMismatch(
                local_version=PROTOCOL_VERSION,
                peer_version=peer_version,
                peer_game_version=peer.get("game_version"),
            )
        return peer

    def close(self):
        self.stop_event.set()
        with self._sock_lock:
            sock = self.sock
            self.sock = None
        # Wake any handshake waiter so it doesn't sit on its 250ms tick.
        self._peer_hello_event.set()
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