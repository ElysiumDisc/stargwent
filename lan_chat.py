import pygame
from typing import List, Optional
from lan_session import LanSession
from lan_protocol import LanMessageType, build_chat_message, parse_message


class LanChatPanel:
    """Reusable chat panel for LAN matches."""

    def __init__(self, session: LanSession, role: str, *, max_lines: int = 20):
        self.session = session
        self.role = role
        self.max_lines = max_lines
        self.chat_log: List[str] = []
        self.input_text = ""
        self.font = pygame.font.SysFont("Consolas", 24)
        self.title_font = pygame.font.SysFont("Arial", 28)
        self.active = True

    def add_message(self, prefix: str, text: str):
        self.chat_log.append(f"{prefix}: {text}")
        if len(self.chat_log) > self.max_lines:
            self.chat_log.pop(0)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_RETURN:
                cleaned = self.input_text.strip()
                if cleaned:
                    self.session.send(LanMessageType.CHAT.value, {"text": cleaned})
                    self.add_message("You", cleaned)
                self.input_text = ""
            elif event.key == pygame.K_BACKSPACE:
                self.input_text = self.input_text[:-1]
            else:
                self.input_text += event.unicode

    def poll_session(self):
        msg = self.session.receive()
        if msg:
            parsed = parse_message(msg)
            if parsed["type"] == LanMessageType.CHAT.value:
                payload = parsed.get("payload", {})
                self.add_message("Peer", payload.get("text", ""))
            elif parsed["type"] == "disconnect":
                self.add_message("System", "Peer disconnected.")
                self.active = False

    def draw(self, surface, rect: pygame.Rect, title: Optional[str] = None):
        pygame.draw.rect(surface, (25, 30, 50), rect)
        pygame.draw.rect(surface, (80, 120, 160), rect, 2)
        if title:
            title_surf = self.title_font.render(title, True, (220, 220, 220))
            surface.blit(title_surf, (rect.x + 10, rect.y - 30))
        y = rect.y + 10
        for line in self.chat_log:
            surf = self.font.render(line, True, (220, 220, 220))
            surface.blit(surf, (rect.x + 10, y))
            y += 24
        input_rect = pygame.Rect(rect.x, rect.bottom + 10, rect.width, 40)
        pygame.draw.rect(surface, (30, 35, 60), input_rect)
        pygame.draw.rect(surface, (80, 120, 160), input_rect, 2)
        placeholder = self.input_text or "Type message..."
        surf = self.font.render(placeholder, True, (200, 200, 200))
        surface.blit(surf, (input_rect.x + 8, input_rect.y + 8))
