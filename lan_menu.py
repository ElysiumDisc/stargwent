import threading
import pygame
import socket
from lan_session import LanSession

FONT_CACHE = {}


def get_font(size):
    if size not in FONT_CACHE:
        FONT_CACHE[size] = pygame.font.SysFont("Consolas", size)
    return FONT_CACHE[size]


def draw_text(surface, text, y, color=(200, 200, 200), size=24):
    lines = text.split("\n")
    font = get_font(size)
    x = 40
    for idx, line in enumerate(lines):
        surf = font.render(line, True, color)
        surface.blit(surf, (x, y + idx * (size + 6)))


def get_local_ips():
    ips = set()
    try:
        hostname = socket.gethostname()
        ips.add(socket.gethostbyname(hostname))
    except socket.error:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None):
            ip = info[4][0]
            if ":" not in ip and not ip.startswith("127."):
                ips.add(ip)
    except socket.error:
        pass
    if not ips:
        ips.add("127.0.0.1")
    return sorted(ips)


def run_lan_menu(screen):
    clock = pygame.time.Clock()
    state = "menu"
    session = None
    join_ip = ""
    status_lines = []
    host_thread = None
    host_error = None
    connected = False
    role = None

    def add_status(msg):
        status_lines.append(msg)
        while len(status_lines) > 6:
            status_lines.pop(0)

    running = True
    while running:
        screen.fill((10, 15, 25))
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif state == "join":
                    if event.key == pygame.K_BACKSPACE:
                        join_ip = join_ip[:-1]
                    elif event.key == pygame.K_RETURN:
                        pass
                    else:
                        join_ip += event.unicode
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                if state == "menu":
                    if 100 < mx < 360:
                        if 200 <= my <= 240:
                            # Host
                            state = "hosting"
                            session = LanSession()
                            status_lines.clear()
                            add_status("Waiting for connection on port 4765...")

                            role = "host"

                            def wait_for_client():
                                nonlocal connected, host_error
                                try:
                                    addr = session.host(4765)
                                    connected = True
                                    add_status(f"Client connected: {addr[0]}")
                                    session.send("status", "Welcome to Stargwent LAN beta!")
                                except OSError as exc:
                                    host_error = str(exc)

                            host_thread = threading.Thread(target=wait_for_client, daemon=True)
                            host_thread.start()
                        elif 260 <= my <= 300:
                            state = "join"
                            join_ip = ""
                    elif 380 < mx < 640 and 260 <= my <= 300:
                        pass
                elif state == "join":
                    if 100 < mx < 360 and 340 <= my <= 380 and join_ip:
                        session = LanSession()
                        add_status(f"Connecting to {join_ip}:4765...")
                        try:
                            session.join(join_ip, 4765)
                            state = "chat"
                            role = "client"
                            add_status("Connected! Type is not implemented yet, but link is live.")
                            session.send("status", "Joined Stargwent LAN beta!")
                        except OSError as exc:
                            add_status(f"Connection failed: {exc}")
                            session = None

        if state == "menu":
            draw_text(screen, "LAN MULTIPLAYER", 40, (255, 255, 255), 36)
            pygame.draw.rect(screen, (70, 120, 190), pygame.Rect(100, 200, 260, 40))
            draw_text(screen, "Host Game", 205, (0, 0, 0))
            pygame.draw.rect(screen, (70, 120, 190), pygame.Rect(100, 260, 260, 40))
            draw_text(screen, "Join Game", 265, (0, 0, 0))
            draw_text(screen, "Press ESC to return", 500)
        elif state == "hosting":
            draw_text(screen, "Hosting LAN Game", 40)
            draw_text(screen, "Share one of these IPs with your opponent:", 90)
            for idx, ip in enumerate(get_local_ips()):
                draw_text(screen, f"{idx + 1}. {ip}", 130 + idx * 28)
            draw_text(screen, "\n".join(status_lines), 280)
            if host_error:
                draw_text(screen, f"Error: {host_error}", 420, (255, 120, 120))
                state = "menu"
                session = None
            elif connected:
                state = "chat"
                add_status("Ready to exchange messages.")
        elif state == "join":
            draw_text(screen, "Join LAN Game", 40)
            draw_text(screen, "Enter host IP:", 90)
            pygame.draw.rect(screen, (30, 30, 30), pygame.Rect(100, 130, 400, 40))
            draw_text(screen, join_ip or "192.168.x.x", 138)
            pygame.draw.rect(screen, (70, 120, 190), pygame.Rect(100, 340, 260, 40))
            draw_text(screen, "Connect", 345, (0, 0, 0))
            draw_text(screen, "\n".join(status_lines[-3:]), 420)
        elif state == "chat":
            draw_text(screen, "LAN Session Active (prototype)", 40)
            draw_text(screen, "Current messages:", 90)
            draw_text(screen, "\n".join(status_lines), 130)
            pygame.draw.rect(screen, (80, 160, 80), pygame.Rect(100, 500, 320, 40))
            draw_text(screen, "Start Match", 510, (0, 0, 0))
            if pygame.mouse.get_pressed()[0]:
                mx, my = pygame.mouse.get_pos()
                if 100 < mx < 420 and 500 <= my <= 540 and session and role:
                    return {"session": session, "role": role}
            if session:
                msg = session.receive()
                if msg:
                    payload = msg.get("payload")
                    mtype = msg.get("type")
                    add_status(f"{mtype}: {payload}")

        pygame.display.flip()
        clock.tick(60)

    if session:
        session.close()
    return None
