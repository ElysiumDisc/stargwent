"""
Improved LAN Waiting Lobby with Chat
Players can chat while waiting to start the match
"""
import pygame
import os
import display_manager
from typing import Optional
from lan_session import LanSession
from lan_chat import LanChatPanel
from lan_protocol import LanMessageType, parse_message


class LanLobby:
    """Enhanced waiting lobby with chat and ready status."""

    def __init__(self, session: LanSession, role: str, screen_width: int, screen_height: int):
        self.session = session
        self.role = role
        self.screen_width = screen_width
        self.screen_height = screen_height

        # UI Fonts
        self.title_font = pygame.font.SysFont("Arial", 60, bold=True)
        self.header_font = pygame.font.SysFont("Arial", 36, bold=True)
        self.info_font = pygame.font.SysFont("Arial", 28)
        self.small_font = pygame.font.SysFont("Arial", 20)

        # Load background
        self.background = self._load_background()

        # Chat panel (bottom half of screen)
        self.chat_panel = LanChatPanel(session, role, max_lines=12)
        self.chat_panel.add_message("System", f"Connected as {role.upper()}. Type to chat!")
        self.chat_panel.add_message("System", "Click 'READY' when you're ready to choose your deck.")

        # Ready states
        self.local_ready = False
        self.remote_ready = False
        self.both_ready = False

        # Calculate UI positions (center everything properly)
        self.title_y = 80
        self.role_y = 160
        self.panel_y = 240
        self.panel_width = 700
        self.panel_height = 280

        # Center the main panel
        self.panel_rect = pygame.Rect(
            screen_width // 2 - self.panel_width // 2,
            self.panel_y,
            self.panel_width,
            self.panel_height
        )

        # Ready button (inside panel)
        self.ready_button_rect = pygame.Rect(
            self.panel_rect.centerx - 180,
            self.panel_rect.bottom - 80,
            360,
            60
        )

        # Start button (below panel, only shows when both ready)
        self.start_button_rect = pygame.Rect(
            screen_width // 2 - 250,
            self.panel_rect.bottom + 30,
            500,
            90
        )

        # Chat area (bottom portion)
        self.chat_y = self.panel_rect.bottom + 150
        self.chat_rect = pygame.Rect(
            80,
            self.chat_y,
            screen_width - 160,
            screen_height - self.chat_y - 80
        )

    def _load_background(self):
        """Load lobby background image if it exists."""
        bg_path = "assets/lobby_background.png"
        if os.path.exists(bg_path):
            try:
                bg = pygame.image.load(bg_path)
                return pygame.transform.scale(bg, (self.screen_width, self.screen_height))
            except:
                pass
        return None

    def handle_event(self, event) -> Optional[str]:
        """
        Handle pygame events.
        Returns: "start" if both players ready and start clicked, None otherwise
        """
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.ready_button_rect.collidepoint(event.pos):
                if not self.local_ready:
                    self.local_ready = True
                    self.session.send(LanMessageType.READY_CHECK.value, {"ready": True})
                    self.chat_panel.add_message("You", "I'm ready!")
                else:
                    self.local_ready = False
                    self.session.send(LanMessageType.READY_CHECK.value, {"ready": False})
                    self.chat_panel.add_message("You", "Not ready yet...")
                self._check_both_ready()

            elif self.both_ready and self.start_button_rect.collidepoint(event.pos):
                # Both ready, start the match
                return "start"

        # Pass event to chat panel
        self.chat_panel.handle_event(event)
        return None

    def update(self) -> Optional[str]:
        """
        Poll for network messages.

        Returns:
            "disconnect" if connection lost, None otherwise
        """
        # Check for disconnect
        if not self.session.is_connected():
            return "disconnect"

        self.chat_panel.poll_session()

        # Check for ready check messages
        msg = self.session.receive()
        if msg:
            # Check for disconnect message
            if msg.get("type") == "disconnect":
                return "disconnect"

            try:
                parsed = parse_message(msg)
                if parsed["type"] == LanMessageType.READY_CHECK.value:
                    payload = parsed.get("payload", {})
                    self.remote_ready = payload.get("ready", False)
                    status = "ready!" if self.remote_ready else "not ready"
                    self.chat_panel.add_message("Opponent", f"I'm {status}")
                    self._check_both_ready()
            except ValueError:
                pass

        return None

    def _check_both_ready(self):
        """Check if both players are ready."""
        self.both_ready = self.local_ready and self.remote_ready
        if self.both_ready:
            self.chat_panel.add_message("System", "🎮 Both players ready! Click START MATCH!")

    def draw(self, surface):
        """Draw the improved lobby UI."""
        # Background
        if self.background:
            surface.blit(self.background, (0, 0))
        else:
            # Gradient background
            for y in range(self.screen_height):
                progress = y / self.screen_height
                color = (
                    int(10 + progress * 20),
                    int(15 + progress * 25),
                    int(35 + progress * 45)
                )
                pygame.draw.line(surface, color, (0, y), (self.screen_width, y))

        # Title with shadow effect
        title_text = "⚡ LAN MULTIPLAYER LOBBY ⚡"
        # Shadow
        title_shadow = self.title_font.render(title_text, True, (0, 0, 0))
        title_shadow_rect = title_shadow.get_rect(center=(self.screen_width // 2 + 3, self.title_y + 3))
        surface.blit(title_shadow, title_shadow_rect)
        # Main title
        title_surf = self.title_font.render(title_text, True, (100, 200, 255))
        title_rect = title_surf.get_rect(center=(self.screen_width // 2, self.title_y))
        surface.blit(title_surf, title_rect)

        # Role indicator
        role_text = f"Connected as: {self.role.upper()}"
        role_surf = self.header_font.render(role_text, True, (180, 220, 255))
        role_rect = role_surf.get_rect(center=(self.screen_width // 2, self.role_y))
        surface.blit(role_surf, role_rect)

        # Main status panel with rounded effect (simulated)
        # Dark panel background
        panel_bg = pygame.Surface((self.panel_width, self.panel_height), pygame.SRCALPHA)
        panel_bg.fill((15, 20, 35, 240))
        surface.blit(panel_bg, (self.panel_rect.x, self.panel_rect.y))

        # Panel border with glow
        pygame.draw.rect(surface, (60, 140, 220), self.panel_rect, 4)
        pygame.draw.rect(surface, (100, 180, 255), self.panel_rect, 2)

        # Panel title
        panel_title = "READY STATUS"
        panel_title_surf = self.header_font.render(panel_title, True, (150, 200, 255))
        panel_title_rect = panel_title_surf.get_rect(center=(self.panel_rect.centerx, self.panel_rect.y + 35))
        surface.blit(panel_title_surf, panel_title_rect)

        # Divider line
        line_y = self.panel_rect.y + 70
        pygame.draw.line(surface, (80, 140, 200),
                        (self.panel_rect.x + 40, line_y),
                        (self.panel_rect.right - 40, line_y), 2)

        # Player status indicators
        status_y_start = self.panel_rect.y + 100

        # Your status
        you_status = "✓ READY" if self.local_ready else "✗ NOT READY"
        you_color = (100, 255, 100) if self.local_ready else (255, 120, 120)
        you_label = self.info_font.render(f"You ({self.role}):", True, (200, 200, 200))
        you_status_surf = self.info_font.render(you_status, True, you_color)
        surface.blit(you_label, (self.panel_rect.x + 50, status_y_start))
        surface.blit(you_status_surf, (self.panel_rect.centerx + 20, status_y_start))

        # Status indicator circle for you
        circle_x = self.panel_rect.right - 60
        pygame.draw.circle(surface, you_color, (circle_x, status_y_start + 15), 12)
        pygame.draw.circle(surface, (255, 255, 255), (circle_x, status_y_start + 15), 12, 2)

        # Opponent status
        opp_status = "✓ READY" if self.remote_ready else "✗ NOT READY"
        opp_color = (100, 255, 100) if self.remote_ready else (255, 120, 120)
        opp_label = self.info_font.render("Opponent:", True, (200, 200, 200))
        opp_status_surf = self.info_font.render(opp_status, True, opp_color)
        surface.blit(opp_label, (self.panel_rect.x + 50, status_y_start + 50))
        surface.blit(opp_status_surf, (self.panel_rect.centerx + 20, status_y_start + 50))

        # Status indicator circle for opponent
        pygame.draw.circle(surface, opp_color, (circle_x, status_y_start + 65), 12)
        pygame.draw.circle(surface, (255, 255, 255), (circle_x, status_y_start + 65), 12, 2)

        # Ready toggle button
        button_color = (60, 160, 60) if not self.local_ready else (180, 60, 60)
        button_hover_color = (80, 200, 80) if not self.local_ready else (220, 80, 80)

        # Check if mouse is over button
        mouse_pos = pygame.mouse.get_pos()
        is_hover = self.ready_button_rect.collidepoint(mouse_pos)
        current_color = button_hover_color if is_hover else button_color

        pygame.draw.rect(surface, current_color, self.ready_button_rect, border_radius=8)
        pygame.draw.rect(surface, (255, 255, 255), self.ready_button_rect, 3, border_radius=8)

        button_text = "✓ I'M READY" if not self.local_ready else "✗ NOT READY"
        button_surf = self.header_font.render(button_text, True, (255, 255, 255))
        button_rect = button_surf.get_rect(center=self.ready_button_rect.center)
        surface.blit(button_surf, button_rect)

        # Start button (only if both ready) with pulsing effect
        if self.both_ready:
            import time
            pulse = abs(int((time.time() * 2) % 2 - 1) * 30)  # Pulsing effect
            start_color = (70 + pulse, 200 + pulse, 70 + pulse)

            is_start_hover = self.start_button_rect.collidepoint(mouse_pos)
            if is_start_hover:
                start_color = (120, 255, 120)

            pygame.draw.rect(surface, start_color, self.start_button_rect, border_radius=10)
            pygame.draw.rect(surface, (255, 255, 255), self.start_button_rect, 5, border_radius=10)

            start_text = "⚡ START MATCH ⚡"
            start_surf = self.title_font.render(start_text, True, (0, 80, 0))
            start_rect = start_surf.get_rect(center=self.start_button_rect.center)
            surface.blit(start_surf, start_rect)

        # Instructions
        instr_text = "Press ESC to cancel • Type to chat with your opponent"
        instr_surf = self.small_font.render(instr_text, True, (140, 180, 220))
        instr_rect = instr_surf.get_rect(center=(self.screen_width // 2, self.panel_rect.bottom + (self.chat_y - self.panel_rect.bottom) // 2))
        surface.blit(instr_surf, instr_rect)

        # Chat panel with improved title
        self.chat_panel.draw(surface, self.chat_rect, title="💬 CHAT WITH OPPONENT")


def run_lan_lobby(screen, session: LanSession, role: str) -> bool:
    """
    Run the LAN lobby waiting room.

    Returns:
        True if players are ready to start, False if cancelled or disconnected
    """
    clock = pygame.time.Clock()
    lobby = LanLobby(session, role, screen.get_width(), screen.get_height())

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False

            result = lobby.handle_event(event)
            if result == "start":
                return True

        update_result = lobby.update()
        if update_result == "disconnect":
            # Show disconnect message
            _show_disconnect_message(screen)
            return False

        lobby.draw(screen)

        display_manager.gpu_flip()
        clock.tick(60)

    return False


def _show_disconnect_message(screen):
    """Show disconnect overlay message."""
    screen_width = screen.get_width()
    screen_height = screen.get_height()

    # Dark overlay
    overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 200))
    screen.blit(overlay, (0, 0))

    # Fonts
    font_large = pygame.font.SysFont("Arial", 60, bold=True)
    font_small = pygame.font.SysFont("Arial", 30)

    # Disconnect message
    text1 = font_large.render("CONNECTION LOST", True, (255, 100, 100))
    text2 = font_small.render("Your opponent has disconnected", True, (200, 200, 200))
    text3 = font_small.render("Press any key to return", True, (150, 150, 150))

    screen.blit(text1, (screen_width // 2 - text1.get_width() // 2, screen_height // 2 - 80))
    screen.blit(text2, (screen_width // 2 - text2.get_width() // 2, screen_height // 2))
    screen.blit(text3, (screen_width // 2 - text3.get_width() // 2, screen_height // 2 + 60))

    display_manager.gpu_flip()

    # Wait for key press
    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                import sys
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
                waiting = False
