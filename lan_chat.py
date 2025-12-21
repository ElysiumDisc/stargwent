import pygame
from typing import List, Optional
from lan_session import LanSession
from lan_protocol import LanMessageType, build_chat_message, parse_message


class LanChatPanel:
    """Reusable chat panel for LAN matches."""

    def __init__(self, session: LanSession, role: str, *, max_lines: int = 20, on_message=None):
        self.session = session
        self.role = role
        self.max_lines = max_lines
        self.chat_log: List[dict] = []
        self.input_text = ""
        self.font = pygame.font.SysFont("Consolas", 24)
        self.title_font = pygame.font.SysFont("Arial", 28)
        self.font_small = pygame.font.SysFont("Arial", 14, bold=True)
        self.active = True
        self.on_message = on_message # Callback(prefix, text, color)
        
        # Typing indicator state
        self.peer_is_typing = False
        self.local_is_typing = False
        self.last_local_input_time = 0
        self.typing_timeout = 2000  # Send "stopped typing" after 2s of inactivity

    def add_message(self, prefix: str, text: str, color: Optional[tuple] = None):
        if color is None:
            # Default colors based on prefix
            if prefix == "System":
                color = (255, 215, 0)  # Gold for system
            elif prefix == "You":
                color = (100, 255, 100) # Greenish for self
            else:
                color = (220, 220, 255) # White/Blue for others

        # If callback exists, delegate to it (e.g. to Game History)
        if self.on_message:
            self.on_message(prefix, text, color)
        
        # Keep local log as backup/fallback
        self.chat_log.append({"text": f"{prefix}: {text}", "color": color})
        if len(self.chat_log) > self.max_lines:
            self.chat_log.pop(0)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and self.active:
            self.last_local_input_time = pygame.time.get_ticks()
            
            if event.key == pygame.K_RETURN:
                cleaned = self.input_text.strip()
                if cleaned:
                    self.session.send(LanMessageType.CHAT.value, {"text": cleaned})
                    self.add_message("You", cleaned)
                self.input_text = ""
                # Stop typing status immediately on send
                if self.local_is_typing:
                    self.local_is_typing = False
                    self.session.send(LanMessageType.TYPING.value, {"typing": False})
            elif event.key == pygame.K_BACKSPACE:
                self.input_text = self.input_text[:-1]
                # If text becomes empty, we technically stopped typing "content"
                if not self.input_text and self.local_is_typing:
                    self.local_is_typing = False
                    self.session.send(LanMessageType.TYPING.value, {"typing": False})
            else:
                self.input_text += event.unicode
                # Started typing
                if not self.local_is_typing and self.input_text:
                    self.local_is_typing = True
                    self.session.send(LanMessageType.TYPING.value, {"typing": True})

    def poll_session(self):
        # Check local typing timeout
        if self.local_is_typing:
            if pygame.time.get_ticks() - self.last_local_input_time > self.typing_timeout:
                self.local_is_typing = False
                self.session.send(LanMessageType.TYPING.value, {"typing": False})

        msg = self.session.receive()
        if not msg:
            return

        try:
            parsed = parse_message(msg)
        except ValueError:
            return

        msg_type = parsed.get("type")
        payload = parsed.get("payload", {})
        
        if msg_type == LanMessageType.CHAT.value:
            self.add_message("Peer", payload.get("text", ""))
            # If we receive a message, they clearly stopped typing (or sent it)
            self.peer_is_typing = False
        elif msg_type == LanMessageType.TYPING.value:
            self.peer_is_typing = payload.get("typing", False)
        elif msg_type == "disconnect":
            self.add_message("System", "Peer disconnected.")
            self.active = False
            self.peer_is_typing = False
        else:
            # Put non-chat messages back so game logic can consume them
            self.session.inbox.put(parsed)

    def _draw_typing_indicator(self, surface, input_rect):
        """Draw 'Dialing...' text and animated chevrons."""
        # Position above the input box
        base_x = input_rect.x + 10
        base_y = input_rect.y - 25
        
        # 1. "Dialing..." text
        text_surf = self.font_small.render("Incoming Wormhole...", True, (100, 200, 255))
        surface.blit(text_surf, (base_x, base_y))
        
        # 2. Animated Chevrons (>>>)
        text_width = text_surf.get_width()
        chevron_start_x = base_x + text_width + 10
        
        # Animation cycle: 3 chevrons lighting up over 1.5s
        now = pygame.time.get_ticks()
        cycle = now % 1500
        active_chevron = (cycle // 500)  # 0, 1, or 2
        
        for i in range(3):
            # Color: Bright Orange if active, Dim Red if inactive
            if i == active_chevron:
                color = (255, 160, 50)  # Bright Amber
            else:
                color = (80, 40, 30)    # Dim Rust
            
            # Draw Chevron shape (pointing right)
            cx = chevron_start_x + i * 15
            cy = base_y + 8
            points = [
                (cx, cy - 6),
                (cx + 8, cy),
                (cx, cy + 6),
                (cx + 4, cy) # Inner notch
            ]
            pygame.draw.polygon(surface, color, points)

    def draw(self, surface, rect: pygame.Rect, title: Optional[str] = None):
        pygame.draw.rect(surface, (25, 30, 50), rect)
        pygame.draw.rect(surface, (80, 120, 160), rect, 2)
        if title:
            title_surf = self.title_font.render(title, True, (220, 220, 220))
            surface.blit(title_surf, (rect.x + 10, rect.y - 30))
        y = rect.y + 10
        for entry in self.chat_log:
            # Handle legacy string entries if any exist (though unlikely with fresh start)
            if isinstance(entry, str):
                text = entry
                color = (220, 220, 220)
            else:
                text = entry["text"]
                color = entry["color"]
            
            surf = self.font.render(text, True, color)
            surface.blit(surf, (rect.x + 10, y))
            y += 24
        
        input_rect = pygame.Rect(rect.x, rect.bottom + 10, rect.width, 40)
        
        # Draw typing indicator if peer is typing
        if self.peer_is_typing:
            self._draw_typing_indicator(surface, input_rect)
            
        pygame.draw.rect(surface, (30, 35, 60), input_rect)
        pygame.draw.rect(surface, (80, 120, 160), input_rect, 2)
        placeholder = self.input_text or "Type message..."
        surf = self.font.render(placeholder, True, (200, 200, 200))
        surface.blit(surf, (input_rect.x + 8, input_rect.y + 8))
