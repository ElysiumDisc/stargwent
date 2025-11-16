"""
Improved LAN Waiting Lobby with Chat
Players can chat while waiting to start the match
"""
import pygame
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
        self.title_font = pygame.font.SysFont("Arial", 48, bold=True)
        self.header_font = pygame.font.SysFont("Arial", 32)
        self.info_font = pygame.font.SysFont("Consolas", 24)

        # Chat panel (bottom half of screen)
        chat_rect_height = screen_height // 2 - 100
        self.chat_panel = LanChatPanel(session, role, max_lines=15)
        self.chat_panel.add_message("System", f"Connected as {role.upper()}. Type to chat!")
        self.chat_panel.add_message("System", "Click 'READY' when you're ready to choose your deck.")

        # Ready states
        self.local_ready = False
        self.remote_ready = False
        self.both_ready = False

        # UI Rects
        self.ready_button_rect = pygame.Rect(
            screen_width // 2 - 150,
            screen_height // 2 - 180,
            300,
            60
        )
        self.start_button_rect = pygame.Rect(
            screen_width // 2 - 200,
            screen_height // 2 - 100,
            400,
            80
        )

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

    def update(self):
        """Poll for network messages."""
        self.chat_panel.poll_session()

        # Check for ready check messages
        msg = self.session.receive()
        if msg:
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

    def _check_both_ready(self):
        """Check if both players are ready."""
        self.both_ready = self.local_ready and self.remote_ready
        if self.both_ready:
            self.chat_panel.add_message("System", "🎮 Both players ready! Click START MATCH!")

    def draw(self, surface):
        """Draw the lobby UI."""
        # Background
        surface.fill((10, 15, 30))

        # Title
        title_text = "LAN MULTIPLAYER LOBBY"
        title_surf = self.title_font.render(title_text, True, (100, 200, 255))
        title_rect = title_surf.get_rect(center=(self.screen_width // 2, 50))
        surface.blit(title_surf, title_rect)

        # Connection info
        role_text = f"You are: {self.role.upper()}"
        role_surf = self.header_font.render(role_text, True, (200, 200, 200))
        role_rect = role_surf.get_rect(center=(self.screen_width // 2, 120))
        surface.blit(role_surf, role_rect)

        # Ready status panel
        panel_y = 180
        panel_rect = pygame.Rect(self.screen_width // 2 - 300, panel_y, 600, 200)
        pygame.draw.rect(surface, (20, 25, 40), panel_rect)
        pygame.draw.rect(surface, (80, 120, 160), panel_rect, 3)

        # Player status
        you_status = "✓ READY" if self.local_ready else "✗ Not Ready"
        opp_status = "✓ READY" if self.remote_ready else "✗ Not Ready"

        you_color = (100, 255, 100) if self.local_ready else (255, 100, 100)
        opp_color = (100, 255, 100) if self.remote_ready else (255, 100, 100)

        you_surf = self.info_font.render(f"You ({self.role}): {you_status}", True, you_color)
        opp_surf = self.info_font.render(f"Opponent: {opp_status}", True, opp_color)

        surface.blit(you_surf, (panel_rect.x + 30, panel_y + 40))
        surface.blit(opp_surf, (panel_rect.x + 30, panel_y + 80))

        # Ready button
        button_color = (80, 180, 80) if not self.local_ready else (180, 80, 80)
        button_text = "READY" if not self.local_ready else "NOT READY"
        pygame.draw.rect(surface, button_color, self.ready_button_rect)
        pygame.draw.rect(surface, (255, 255, 255), self.ready_button_rect, 3)
        button_surf = self.header_font.render(button_text, True, (255, 255, 255))
        button_rect = button_surf.get_rect(center=self.ready_button_rect.center)
        surface.blit(button_surf, button_rect)

        # Start button (only if both ready)
        if self.both_ready:
            start_color = (100, 255, 100)
            pygame.draw.rect(surface, start_color, self.start_button_rect)
            pygame.draw.rect(surface, (255, 255, 255), self.start_button_rect, 4)
            start_surf = self.title_font.render("START MATCH", True, (0, 50, 0))
            start_rect = start_surf.get_rect(center=self.start_button_rect.center)
            surface.blit(start_surf, start_rect)

        # Instructions
        instr_text = "Press ESC to cancel | Type to chat with opponent"
        instr_surf = self.info_font.render(instr_text, True, (150, 150, 150))
        instr_rect = instr_surf.get_rect(center=(self.screen_width // 2, panel_y + 160))
        surface.blit(instr_surf, instr_rect)

        # Chat panel (lower half)
        chat_y = panel_y + 220
        chat_rect = pygame.Rect(50, chat_y, self.screen_width - 100, self.screen_height - chat_y - 80)
        self.chat_panel.draw(surface, chat_rect, title="CHAT")


def run_lan_lobby(screen, session: LanSession, role: str) -> bool:
    """
    Run the LAN lobby waiting room.

    Returns:
        True if players are ready to start, False if cancelled
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

        lobby.update()
        lobby.draw(screen)

        pygame.display.flip()
        clock.tick(60)

    return False
