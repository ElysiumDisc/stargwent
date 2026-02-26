import asyncio
import pygame
import display_manager
import re
import time
from touch_support import is_web_platform
from lan_session import LanSession

if not is_web_platform():
    import threading
    import socket
    import subprocess
else:
    threading = None
    socket = None
    subprocess = None

FONT_CACHE = {}


def get_font(size):
    if size not in FONT_CACHE:
        FONT_CACHE[size] = pygame.font.SysFont("Consolas", size)
    return FONT_CACHE[size]


def draw_text(surface, text, y, color=(200, 200, 200), size=24, center_x=None):
    """Draw text, optionally centered horizontally."""
    lines = text.split("\n")
    font = get_font(size)
    for idx, line in enumerate(lines):
        surf = font.render(line, True, color)
        if center_x is not None:
            x = center_x - surf.get_width() // 2
        else:
            x = 40
        surface.blit(surf, (x, y + idx * (size + 6)))


def draw_text_left(surface, text, x, y, color=(200, 200, 200), size=24):
    """Draw text at specific x position."""
    font = get_font(size)
    surf = font.render(text, True, color)
    surface.blit(surf, (x, y))


def get_local_ips():
    """Get all local IP addresses, prioritizing Tailscale and useful interfaces."""
    ips = {}  # ip -> priority (lower is better)

    # Method 1: Use 'ip addr' command to get all interfaces (most reliable on Linux)
    try:
        result = subprocess.run(['ip', 'addr'], capture_output=True, text=True, timeout=2)
        if result.returncode == 0:
            # Parse ip addr output for inet addresses
            current_iface = ""
            for line in result.stdout.split('\n'):
                # Match interface line like "2: eth0: <BROADCAST..."
                iface_match = re.match(r'\d+:\s+(\S+):', line)
                if iface_match:
                    current_iface = iface_match.group(1)
                # Match inet line like "    inet 192.168.1.100/24 brd..."
                inet_match = re.search(r'inet\s+(\d+\.\d+\.\d+\.\d+)', line)
                if inet_match:
                    ip = inet_match.group(1)
                    if ip.startswith("127."):
                        continue
                    # Prioritize Tailscale (100.x.x.x range, usually on tailscale0)
                    if ip.startswith("100.") or "tailscale" in current_iface.lower():
                        ips[ip] = 1  # Highest priority
                    elif ip.startswith("192.168.") or ip.startswith("10."):
                        ips[ip] = 2  # Local network
                    elif ip.startswith("172."):
                        # Check if it's in private range (172.16.0.0 - 172.31.255.255)
                        second_octet = int(ip.split('.')[1])
                        if 16 <= second_octet <= 31:
                            ips[ip] = 2
                        else:
                            ips[ip] = 3
                    else:
                        ips[ip] = 3  # Other IPs
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        pass

    # Method 2: Connect to external address to find default route IP
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.1)
        # Connect to Tailscale's coordination server to prefer Tailscale interface
        s.connect(("100.100.100.100", 80))
        tailscale_ip = s.getsockname()[0]
        s.close()
        if not tailscale_ip.startswith("127."):
            ips[tailscale_ip] = 0  # Absolute highest priority
    except (socket.error, OSError):
        pass

    # Method 3: Connect to public DNS to find default route
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.1)
        s.connect(("8.8.8.8", 80))
        default_ip = s.getsockname()[0]
        s.close()
        if not default_ip.startswith("127.") and default_ip not in ips:
            ips[default_ip] = 2
    except (socket.error, OSError):
        pass

    # Method 4: Fallback to original method
    try:
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        if not ip.startswith("127.") and ip not in ips:
            ips[ip] = 4
    except socket.error:
        pass

    try:
        for info in socket.getaddrinfo(socket.gethostname(), None):
            ip = info[4][0]
            if ":" not in ip and not ip.startswith("127.") and ip not in ips:
                ips[ip] = 4
    except socket.error:
        pass

    if not ips:
        return ["127.0.0.1"]

    # Sort by priority, then by IP
    sorted_ips = sorted(ips.keys(), key=lambda x: (ips[x], x))
    return sorted_ips


# ============================================================================
# ROOM CODE SYSTEM - Human-readable codes for LAN IPs
# ============================================================================
# Character set excluding confusing chars: 0/O, 1/I/L
ROOM_CODE_CHARS = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"


def ip_to_room_code(ip: str, port: int = 4765) -> str:
    """Convert IP address to human-readable room code.

    Encodes the IP as a GATE-XXXX code for easy sharing.
    Only works reliably on same subnet (last two octets encoded).

    Args:
        ip: IP address string (e.g., "192.168.1.42")
        port: Port number (unused for now, reserved for future)

    Returns:
        Room code string (e.g., "GATE-7K3M")
    """
    try:
        parts = [int(x) for x in ip.split('.')]
        if len(parts) != 4:
            return "GATE-????"

        # Encode last two octets (most likely to vary on LAN)
        # Using a simple base conversion with our character set
        value = parts[2] * 256 + parts[3]  # 0-65535 range

        code_chars = []
        base = len(ROOM_CODE_CHARS)
        for _ in range(4):
            code_chars.append(ROOM_CODE_CHARS[value % base])
            value //= base

        return f"GATE-{''.join(reversed(code_chars))}"
    except (ValueError, IndexError):
        return "GATE-????"


def room_code_to_ip(code: str, network_prefix: str = None) -> tuple:
    """Convert room code back to IP address.

    Args:
        code: Room code string (e.g., "GATE-7K3M")
        network_prefix: First two octets of network (e.g., "192.168")
                       If None, uses common LAN prefixes

    Returns:
        tuple: (ip_string, port) or (None, None) if invalid
    """
    try:
        # Strip prefix and normalize
        code = code.upper().replace("GATE-", "").replace("-", "")
        if len(code) != 4:
            return (None, None)

        # Decode from our character set
        base = len(ROOM_CODE_CHARS)
        value = 0
        for char in code:
            idx = ROOM_CODE_CHARS.find(char)
            if idx < 0:
                return (None, None)
            value = value * base + idx

        # Extract octets
        octet3 = value // 256
        octet4 = value % 256

        if octet3 > 255 or octet4 > 255:
            return (None, None)

        # Determine network prefix (try to auto-detect from local IPs)
        if not network_prefix:
            local_ips = get_local_ips()
            if local_ips:
                parts = local_ips[0].split('.')
                if len(parts) >= 2:
                    network_prefix = f"{parts[0]}.{parts[1]}"
            if not network_prefix:
                network_prefix = "192.168"

        ip = f"{network_prefix}.{octet3}.{octet4}"
        return (ip, 4765)
    except (ValueError, IndexError):
        return (None, None)


def draw_button(surface, rect, text, font_size=32, hover=False, color_normal=(50, 100, 180), color_hover=(70, 130, 220)):
    """Draw a styled button with hover effect."""
    color = color_hover if hover else color_normal

    # Draw button background with border
    pygame.draw.rect(surface, color, rect, border_radius=8)
    pygame.draw.rect(surface, (100, 150, 230), rect, 3, border_radius=8)

    # Draw text centered
    font = get_font(font_size)
    text_surf = font.render(text, True, (255, 255, 255))
    text_x = rect.centerx - text_surf.get_width() // 2
    text_y = rect.centery - text_surf.get_height() // 2
    surface.blit(text_surf, (text_x, text_y))


async def run_lan_menu(screen):
    # Preload lobby background if available
    lobby_background = None
    try:
        bg_image = pygame.image.load("assets/lobby_background.png")
        lobby_background = pygame.transform.scale(bg_image, screen.get_size())
    except pygame.error:
        lobby_background = None

    clock = pygame.time.Clock()
    state = "menu"
    session = None
    join_ip = ""
    status_lines = []
    host_thread = None
    host_error = None
    host_cancelled = False
    host_start_time = None
    host_timeout = 120  # seconds
    connected = False
    role = None

    # Get screen dimensions for centering
    screen_w, screen_h = screen.get_size()
    center_x = screen_w // 2

    # Define button dimensions - MUCH LARGER
    button_width = 400
    button_height = 70
    button_x = center_x - button_width // 2

    # Define button rects
    host_btn = pygame.Rect(button_x, 220, button_width, button_height)
    join_btn = pygame.Rect(button_x, 320, button_width, button_height)
    connect_btn = pygame.Rect(button_x, 420, button_width, button_height)
    back_btn = pygame.Rect(button_x, 520, button_width, 50)
    start_btn = pygame.Rect(button_x, 480, button_width, button_height)
    coop_btn = pygame.Rect(button_x, 480 + button_height + 15, button_width, 50)

    def add_status(msg):
        status_lines.append(msg)
        while len(status_lines) > 6:
            status_lines.pop(0)

    running = True
    while running:
        # Draw background (image if available, fallback gradient)
        if lobby_background:
            screen.blit(lobby_background, (0, 0))
        else:
            for y in range(screen_h):
                ratio = y / screen_h
                r = int(10 + ratio * 15)
                g = int(15 + ratio * 20)
                b = int(30 + ratio * 40)
                pygame.draw.line(screen, (r, g, b), (0, y), (screen_w, y))

        mx, my = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if state in ("join", "hosting"):
                        if state == "hosting":
                            host_cancelled = True
                        state = "menu"
                        if session:
                            session.close()
                            session = None
                    else:
                        running = False
                elif state == "join":
                    if event.key == pygame.K_BACKSPACE:
                        join_ip = join_ip[:-1]
                    elif event.key == pygame.K_RETURN and join_ip:
                        # Check if it's a room code or IP address
                        target_ip = join_ip
                        target_port = 4765

                        # Try to decode as room code if it looks like one
                        if join_ip.upper().startswith("GATE") or (len(join_ip) == 4 and not "." in join_ip):
                            decoded_ip, decoded_port = room_code_to_ip(join_ip)
                            if decoded_ip:
                                target_ip = decoded_ip
                                target_port = decoded_port
                                add_status(f"Room code decoded: {target_ip}")
                            else:
                                add_status("Invalid room code format")
                                continue

                        # Connect on Enter
                        session = LanSession()
                        add_status(f"Connecting to {target_ip}:{target_port}...")
                        try:
                            session.join(target_ip, target_port)
                            state = "chat"
                            role = "client"
                            add_status("Connected successfully!")
                            session.send("status", "Joined Stargwent LAN!")
                        except OSError as exc:
                            add_status(f"Connection failed: {exc}")
                            session = None
                    elif event.unicode and event.unicode.isprintable():
                        join_ip += event.unicode
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if state == "menu":
                    if host_btn.collidepoint(mx, my):
                        # Host Game
                        state = "hosting"
                        session = LanSession()
                        status_lines.clear()
                        add_status("Waiting for connection on port 4765...")
                        role = "host"
                        host_start_time = time.time()
                        host_cancelled = False

                        def wait_for_client():
                            nonlocal connected, host_error, host_cancelled
                            try:
                                # Use timeout to allow periodic cancel checks
                                addr = session.host(4765, timeout=host_timeout)
                                if not host_cancelled:
                                    connected = True
                                    add_status(f"Client connected: {addr[0]}")
                                    session.send("status", "Welcome to Stargwent LAN!")
                            except socket.timeout:
                                if not host_cancelled:
                                    host_error = "Connection timeout - no client connected within 2 minutes"
                            except OSError as exc:
                                if not host_cancelled:
                                    host_error = str(exc)

                        host_thread = threading.Thread(target=wait_for_client, daemon=True)
                        host_thread.start()
                    elif join_btn.collidepoint(mx, my):
                        state = "join"
                        join_ip = ""
                        status_lines.clear()
                elif state == "join":
                    if connect_btn.collidepoint(mx, my) and join_ip:
                        # Check if it's a room code or IP address
                        target_ip = join_ip
                        target_port = 4765

                        # Try to decode as room code if it looks like one
                        if join_ip.upper().startswith("GATE") or (len(join_ip) == 4 and not "." in join_ip):
                            decoded_ip, decoded_port = room_code_to_ip(join_ip)
                            if decoded_ip:
                                target_ip = decoded_ip
                                target_port = decoded_port
                                add_status(f"Room code decoded: {target_ip}")
                            else:
                                add_status("Invalid room code format")
                                continue

                        session = LanSession()
                        add_status(f"Connecting to {target_ip}:{target_port}...")
                        try:
                            session.join(target_ip, target_port)
                            state = "chat"
                            role = "client"
                            add_status("Connected successfully!")
                            session.send("status", "Joined Stargwent LAN!")
                        except OSError as exc:
                            add_status(f"Connection failed: {exc}")
                            session = None
                    elif back_btn.collidepoint(mx, my):
                        state = "menu"
                elif state == "hosting":
                    if back_btn.collidepoint(mx, my):
                        host_cancelled = True
                        state = "menu"
                        if session:
                            session.close()
                            session = None
                elif state == "chat":
                    if start_btn.collidepoint(mx, my) and session and role:
                        return {"session": session, "role": role}
                    if coop_btn.collidepoint(mx, my) and session and role:
                        # Launch co-op arcade directly
                        from lan_coop_arcade import run_lan_coop_arcade
                        await run_lan_coop_arcade(screen, session, role)
                        # After arcade, return to chat state (don't close session)

        # Draw UI based on state
        if state == "menu":
            # Title
            draw_text(screen, "LAN MULTIPLAYER", 80, (255, 255, 255), 48, center_x)
            draw_text(screen, "Play with friends on your local network", 140, (150, 150, 180), 20, center_x)

            # Host button
            host_hover = host_btn.collidepoint(mx, my)
            draw_button(screen, host_btn, "HOST GAME", 36, host_hover, (40, 120, 80), (60, 160, 100))

            # Join button
            join_hover = join_btn.collidepoint(mx, my)
            draw_button(screen, join_btn, "JOIN GAME", 36, join_hover, (50, 100, 180), (70, 130, 220))

            # Instructions
            draw_text(screen, "Press ESC to return to main menu", screen_h - 60, (120, 120, 140), 18, center_x)

        elif state == "hosting":
            # Title
            draw_text(screen, "HOSTING GAME", 60, (100, 255, 150), 42, center_x)

            # Calculate elapsed time
            elapsed_seconds = int(time.time() - host_start_time) if host_start_time else 0
            remaining_seconds = max(0, host_timeout - elapsed_seconds)

            # IP addresses box
            ips = get_local_ips()

            # Generate room code from first IP
            room_code = ip_to_room_code(ips[0]) if ips else "GATE-????"

            box_y = 130
            box_height = 80 + len(ips) * 35  # Extra space for room code
            ip_box = pygame.Rect(center_x - 280, box_y, 560, box_height)
            pygame.draw.rect(screen, (30, 40, 50), ip_box, border_radius=8)
            pygame.draw.rect(screen, (80, 180, 120), ip_box, 2, border_radius=8)

            # Room code display (large and prominent)
            draw_text(screen, f"Room Code: {room_code}", box_y + 15, (255, 215, 0), 28, center_x)
            draw_text(screen, "Or share this IP with your opponent:", box_y + 50, (150, 150, 180), 18, center_x)

            for idx, ip in enumerate(ips):
                ip_color = (100, 255, 150) if idx == 0 else (180, 180, 180)
                label = "★ RECOMMENDED" if idx == 0 else f"  Alternative {idx}"
                draw_text_left(screen, f"{label}:  {ip}", center_x - 250, box_y + 85 + idx * 35, ip_color, 22)

            # Status messages with elapsed time
            status_y = box_y + box_height + 30
            wait_text = f"Waiting for connection... ({elapsed_seconds}s / {host_timeout}s)"
            draw_text(screen, wait_text, status_y, (255, 200, 100), 20, center_x)

            for idx, msg in enumerate(status_lines[-3:]):
                if "Waiting" not in msg:  # Skip generic waiting message
                    color = (100, 255, 150) if "connected" in msg.lower() else (180, 180, 180)
                    draw_text(screen, msg, status_y + 30 + idx * 28, color, 20, center_x)

            # Error handling
            if host_error:
                draw_text(screen, f"Error: {host_error}", status_y + 120, (255, 120, 120), 20, center_x)
                state = "menu"
                session = None
            elif connected:
                state = "chat"
                add_status("Ready to start match!")

            # Back button
            back_hover = back_btn.collidepoint(mx, my)
            draw_button(screen, back_btn, "← CANCEL (ESC)", 24, back_hover, (120, 60, 60), (160, 80, 80))

        elif state == "join":
            # Title
            draw_text(screen, "JOIN GAME", 60, (100, 180, 255), 42, center_x)
            draw_text(screen, "Enter room code or IP address", 115, (150, 150, 180), 20, center_x)

            # IP input box
            input_box = pygame.Rect(center_x - 250, 180, 500, 60)
            pygame.draw.rect(screen, (40, 50, 60), input_box, border_radius=8)
            pygame.draw.rect(screen, (100, 150, 230), input_box, 3, border_radius=8)

            # Input text or placeholder
            if join_ip:
                draw_text(screen, join_ip, 195, (255, 255, 255), 28, center_x)
            else:
                draw_text(screen, "GATE-XXXX or 192.168.x.x", 195, (100, 100, 120), 28, center_x)

            # Cursor blink
            if pygame.time.get_ticks() % 1000 < 500:
                font = get_font(28)
                cursor_x = center_x + font.size(join_ip)[0] // 2 if join_ip else center_x + font.size("GATE-XXXX or 192.168.x.x")[0] // 2
                pygame.draw.rect(screen, (255, 255, 255), (cursor_x + 5, 195, 2, 28))

            # Hint text
            draw_text(screen, "Press ENTER to connect (room codes: GATE-XXXX)", 260, (120, 120, 140), 16, center_x)

            # Connect button
            connect_hover = connect_btn.collidepoint(mx, my)
            btn_color_normal = (50, 100, 180) if join_ip else (60, 60, 70)
            btn_color_hover = (70, 130, 220) if join_ip else (60, 60, 70)
            draw_button(screen, connect_btn, "CONNECT", 32, connect_hover and join_ip, btn_color_normal, btn_color_hover)

            # Status messages
            for idx, msg in enumerate(status_lines[-3:]):
                color = (255, 120, 120) if "failed" in msg.lower() else (255, 200, 100)
                draw_text(screen, msg, 500 + idx * 28, color, 18, center_x)

            # Back button
            back_hover = back_btn.collidepoint(mx, my)
            draw_button(screen, back_btn, "← BACK", 24, back_hover, (80, 80, 90), (100, 100, 120))

        elif state == "chat":
            # Title
            draw_text(screen, "CONNECTED!", 60, (100, 255, 150), 42, center_x)
            role_text = "You are the HOST" if role == "host" else "You are the CLIENT"
            draw_text(screen, role_text, 115, (180, 180, 200), 22, center_x)

            # Status box
            status_box = pygame.Rect(center_x - 300, 160, 600, 200)
            pygame.draw.rect(screen, (30, 40, 50), status_box, border_radius=8)
            pygame.draw.rect(screen, (80, 180, 120), status_box, 2, border_radius=8)

            draw_text(screen, "Connection Status:", 175, (150, 150, 180), 18, center_x)
            for idx, msg in enumerate(status_lines[-5:]):
                draw_text(screen, msg, 210 + idx * 28, (200, 200, 200), 18, center_x)

            # Start Match button - BIG and prominent
            start_hover = start_btn.collidepoint(mx, my)
            draw_button(screen, start_btn, "START MATCH", 36, start_hover, (40, 150, 80), (60, 200, 100))

            draw_text(screen, "Both players will proceed to deck selection", 560, (120, 120, 140), 16, center_x)

            # Co-op Arcade button
            coop_hover = coop_btn.collidepoint(mx, my)
            draw_button(screen, coop_btn, "CO-OP ARCADE", 24, coop_hover, (100, 50, 130), (140, 70, 180))
            draw_text(screen, "Fight together in the space shooter mini-game!", coop_btn.bottom + 8, (140, 130, 180), 16, center_x)

            # Check for messages
            if session:
                msg = session.receive()
                if msg:
                    payload = msg.get("payload")
                    mtype = msg.get("type")
                    add_status(f"[{mtype}] {payload}")

        display_manager.gpu_flip()
        clock.tick(60)
        await asyncio.sleep(0)

    if session:
        session.close()
    return None


async def run_lan_rematch(screen, session, role):
    """
    Handle rematch flow after a LAN game ends.
    Both players stay connected and can choose new factions/leaders.
    Returns dict with session info if both ready, None to exit.
    """
    clock = pygame.time.Clock()
    screen_w, screen_h = screen.get_size()
    center_x = screen_w // 2
    
    status_lines = ["Game Over - Rematch?", "Waiting for opponent's decision..."]
    peer_ready = False
    local_ready = False
    
    # Button definitions
    button_width = 350
    button_height = 60
    button_x = center_x - button_width // 2
    
    rematch_btn = pygame.Rect(button_x, 300, button_width, button_height)
    disconnect_btn = pygame.Rect(button_x, 400, button_width, button_height)
    
    def add_status(msg):
        status_lines.append(msg)
        while len(status_lines) > 6:
            status_lines.pop(0)
    
    running = True
    while running:
        # Draw gradient background
        for y in range(screen_h):
            ratio = y / screen_h
            r = int(15 + ratio * 20)
            g = int(20 + ratio * 25)
            b = int(40 + ratio * 50)
            pygame.draw.line(screen, (r, g, b), (0, y), (screen_w, y))
        
        mx, my = pygame.mouse.get_pos()
        
        # Check for peer messages
        if session and session.is_connected():
            msg = session.receive()
            if msg:
                mtype = msg.get("type")
                payload = msg.get("payload", {})
                
                if mtype == "play_again":
                    if payload.get("request"):
                        add_status("Opponent wants to play again!")
                        peer_ready = True
                    elif payload.get("decline"):
                        add_status("Opponent declined rematch.")
                        running = False
                        session.close()
                        return None
                elif mtype == "disconnect":
                    add_status("Opponent disconnected.")
                    running = False
                    return None
        else:
            add_status("Connection lost!")
            running = False
            return None
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                if session:
                    session.send("play_again", {"decline": True})
                    session.close()
                running = False
                return None
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if session:
                        session.send("play_again", {"decline": True})
                        session.close()
                    running = False
                    return None
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if rematch_btn.collidepoint(mx, my):
                    local_ready = True
                    session.send("play_again", {"request": True})
                    add_status("You are ready for rematch!")
                elif disconnect_btn.collidepoint(mx, my):
                    session.send("play_again", {"decline": True})
                    session.close()
                    running = False
                    return None
        
        # Check if both players ready
        if local_ready and peer_ready:
            add_status("Both players ready! Starting new match...")
            pygame.time.wait(500)  # Brief pause
            return {"session": session, "role": role}
        
        # Draw UI
        draw_text(screen, "REMATCH?", 100, (255, 215, 0), 48, center_x)
        draw_text(screen, "Stay connected and play again with new decks", 160, (150, 150, 180), 20, center_x)
        
        # Status box
        status_box = pygame.Rect(center_x - 300, 200, 600, 80)
        pygame.draw.rect(screen, (30, 40, 50), status_box, border_radius=8)
        pygame.draw.rect(screen, (80, 120, 160), status_box, 2, border_radius=8)
        
        # Show ready status
        local_status = "✓ You: READY" if local_ready else "○ You: Waiting..."
        peer_status = "✓ Opponent: READY" if peer_ready else "○ Opponent: Waiting..."
        local_color = (100, 255, 100) if local_ready else (150, 150, 150)
        peer_color = (100, 255, 100) if peer_ready else (150, 150, 150)
        
        draw_text(screen, local_status, 215, local_color, 20, center_x - 120)
        draw_text(screen, peer_status, 245, peer_color, 20, center_x - 120)
        
        # Rematch button
        rematch_hover = rematch_btn.collidepoint(mx, my)
        if local_ready:
            draw_button(screen, rematch_btn, "✓ READY!", 32, False, (60, 120, 60), (60, 120, 60))
        else:
            draw_button(screen, rematch_btn, "PLAY AGAIN", 32, rematch_hover, (40, 120, 80), (60, 160, 100))
        
        # Disconnect button
        disconnect_hover = disconnect_btn.collidepoint(mx, my)
        draw_button(screen, disconnect_btn, "DISCONNECT", 32, disconnect_hover, (120, 60, 60), (160, 80, 80))
        
        # Instructions
        draw_text(screen, "Press ESC to disconnect", screen_h - 60, (120, 120, 140), 16, center_x)
        
        display_manager.gpu_flip()
        clock.tick(60)
        await asyncio.sleep(0)

    return None
