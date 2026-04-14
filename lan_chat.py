import queue
import pygame
import uuid
from datetime import datetime
from typing import List, Optional, Dict
from lan_session import LanSession
from lan_protocol import LanMessageType, build_chat_message, parse_message
import game_config as cfg


MAX_MESSAGE_LENGTH = 200

# Quick chat messages (number keys 1-0)
QUICK_CHATS = {
    pygame.K_1: "Good game!",
    pygame.K_2: "Nice play!",
    pygame.K_3: "Good luck!",
    pygame.K_4: "One moment...",
    pygame.K_5: "Well played!",
    pygame.K_6: "Impressive!",
    pygame.K_7: "Indeed.",
    pygame.K_8: "For the glory of the System Lords!",
    pygame.K_9: "Kree!",
    pygame.K_0: "Undomesticated equines could not drag me away",
}


class LanChatPanel:
    """Reusable chat panel for LAN matches with scrolling, notifications, and quick chat."""

    def __init__(self, session: LanSession, role: str, *, max_lines: int = 20, on_message=None, peer_name: str = "Peer"):
        self.session = session
        self.role = role
        self.peer_name = peer_name
        self.max_lines = max_lines  # Visible lines
        self.max_history = 100  # Total messages kept in memory
        self.full_history: List[dict] = []  # All messages
        self.input_text = ""
        self.font = pygame.font.SysFont("Consolas", 22)
        self.timestamp_font = pygame.font.SysFont("Consolas", 16)
        self.title_font = pygame.font.SysFont("Arial", 28)
        self.font_small = pygame.font.SysFont("Arial", 14, bold=True)
        self.active = True
        self.on_message = on_message  # Callback(prefix, text, color)

        # Visibility state for unread tracking
        self.is_visible = True
        self.unread_count = 0

        # Scrolling state
        self.scroll_offset = 0  # 0 = showing latest, positive = scrolled up
        self.has_new_messages = False  # True if scrolled up and new messages arrived

        # Typing indicator state
        self.peer_is_typing = False
        self.local_is_typing = False
        self.last_local_input_time = 0
        self.typing_timeout = cfg.TYPING_TIMEOUT  # Send "stopped typing" after 2s of inactivity
        self._last_typing_sent = 0  # Throttle: ms timestamp of last typing=True send

        # Message delivery confirmation
        self.pending_acks: Dict[str, float] = {}  # msg_id -> send_time
        self.ack_timeout = 5.0  # seconds before marking as unconfirmed

        # Sound manager (lazy loaded)
        self._sound_manager = None

    def _get_sound_manager(self):
        """Lazy load sound manager to avoid circular imports."""
        if self._sound_manager is None:
            from sound_manager import get_sound_manager
            self._sound_manager = get_sound_manager()
        return self._sound_manager

    def _get_timestamp(self):
        """Get current time as HH:MM format."""
        return datetime.now().strftime("%H:%M")

    def _generate_msg_id(self) -> str:
        """Generate a unique message ID."""
        return str(uuid.uuid4())[:8]

    def add_message(self, prefix: str, text: str, color: Optional[tuple] = None,
                    msg_id: Optional[str] = None, confirmed: bool = True,
                    raw_text: Optional[str] = None):
        """Add a message to the chat log.

        Args:
            prefix: Message sender ("You", "Peer", "System")
            text: Message content
            color: Optional color override
            msg_id: Optional message ID for delivery tracking
            confirmed: Whether the message delivery is confirmed
            raw_text: Original payload text (without "Prefix: " framing)
                used for retry; falls back to *text* if not supplied.
        """
        if color is None:
            # Default colors based on prefix
            if prefix == "System":
                color = cfg.GOLD  # Gold for system
            elif prefix == "You":
                color = cfg.HIGHLIGHT_GREEN  # Greenish for self
            else:
                color = cfg.TEXT_LIGHT  # White/Blue for others

        # If callback exists, delegate to it (e.g. to Game History)
        if self.on_message:
            self.on_message(prefix, text, color)

        # Keep local log with timestamp
        timestamp = self._get_timestamp()
        entry = {
            "text": f"{prefix}: {text}",
            "raw_text": raw_text if raw_text is not None else text,
            "color": color,
            "timestamp": timestamp,
            "msg_id": msg_id,
            "confirmed": confirmed,
            "prefix": prefix,
        }
        self.full_history.append(entry)

        # Trim old messages
        if len(self.full_history) > self.max_history:
            self.full_history.pop(0)
            # Adjust scroll offset if we're scrolled up
            if self.scroll_offset > 0:
                self.scroll_offset = max(0, self.scroll_offset - 1)

        # Track new messages if scrolled up
        if self.scroll_offset > 0 and prefix != "You":
            self.has_new_messages = True

        # Track unread if not visible
        if not self.is_visible and prefix != "You":
            self.unread_count += 1

        # Play notification sound for peer messages
        if prefix == self.peer_name:
            self._get_sound_manager().play_chat_notification("peer", volume=0.4)
        elif prefix == "System":
            self._get_sound_manager().play_chat_notification("system", volume=0.3)

    def send_message(self, text: str):
        """Send a chat message with delivery confirmation tracking."""
        msg_id = self._generate_msg_id()

        # Send first; only track for ACK if the send actually went out.
        # Otherwise a failed send leaves a pending_acks entry that
        # times out and "fails" a message that was never transmitted.
        sent = self.session.send(LanMessageType.CHAT.value, {"text": text, "msg_id": msg_id})
        if sent:
            self.pending_acks[msg_id] = pygame.time.get_ticks() / 1000.0
            self.add_message("You", text, msg_id=msg_id, confirmed=False, raw_text=text)
        else:
            # Surface the failure immediately rather than waiting for ACK timeout
            self.add_message("You", text, msg_id=msg_id, confirmed=False, raw_text=text)
            self._mark_failed(msg_id)

    def send_quick_chat(self, key: int):
        """Send a quick chat message if the key is a quick chat key."""
        if key in QUICK_CHATS:
            text = QUICK_CHATS[key]
            self.send_message(text)
            return True
        return False

    def _send_ack(self, msg_id: str):
        """Send acknowledgment for a received message."""
        self.session.send("chat_ack", {"msg_id": msg_id})

    def _mark_confirmed(self, msg_id: str):
        """Mark a message as confirmed."""
        for entry in self.full_history:
            if entry.get("msg_id") == msg_id:
                entry["confirmed"] = True
                break
        # Remove from pending
        self.pending_acks.pop(msg_id, None)

    def _mark_failed(self, msg_id: str):
        """Mark a message as failed (ACK timeout), retry once before giving up."""
        # Find the message entry
        entry = None
        for e in self.full_history:
            if e.get("msg_id") == msg_id:
                entry = e
                break
        if entry and not entry.get("_retried"):
            # Retry once — resend the original payload and reset the ACK timer.
            # Use stored raw_text so messages containing ": " aren't mangled
            # by trying to parse the display string.
            entry["_retried"] = True
            raw = entry.get("raw_text")
            if raw is None:
                # Legacy entry without raw_text — fall back to display parse.
                text = entry.get("text", "")
                colon_idx = text.find(": ")
                if colon_idx != -1 and colon_idx < 20:
                    text = text[colon_idx + 2:]
                raw = text
            sent = self.session.send(LanMessageType.CHAT.value,
                                     {"text": raw, "msg_id": msg_id})
            if sent:
                self.pending_acks[msg_id] = pygame.time.get_ticks() / 1000.0
                return
            # Send failed on retry — fall through to permanent-fail state
        # Already retried or not found — mark as permanently failed
        if entry:
            entry["failed"] = True
            entry["confirmed"] = False
        # Remove from pending
        self.pending_acks.pop(msg_id, None)

    def set_visible(self, visible: bool):
        """Set chat visibility state."""
        self.is_visible = visible
        if visible:
            self.unread_count = 0

    def get_unread_count(self) -> int:
        """Get the number of unread messages."""
        return self.unread_count

    def scroll_up(self, lines: int = 3):
        """Scroll chat history up."""
        max_scroll = max(0, len(self.full_history) - self.max_lines)
        self.scroll_offset = min(max_scroll, self.scroll_offset + lines)

    def scroll_down(self, lines: int = 3):
        """Scroll chat history down."""
        self.scroll_offset = max(0, self.scroll_offset - lines)
        if self.scroll_offset == 0:
            self.has_new_messages = False

    def scroll_to_bottom(self):
        """Scroll to the latest messages."""
        self.scroll_offset = 0
        self.has_new_messages = False

    def handle_event(self, event):
        """Handle keyboard/mouse events for chat input."""
        if event.type == pygame.KEYDOWN and self.active:
            self.last_local_input_time = pygame.time.get_ticks()

            # Quick chat keys (1-5) - only when not typing
            if not self.input_text and event.key in QUICK_CHATS:
                self.send_quick_chat(event.key)
                return

            if event.key == pygame.K_RETURN:
                cleaned = self.input_text.strip()
                if cleaned:
                    self.send_message(cleaned)
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
            elif event.key == pygame.K_PAGEUP:
                self.scroll_up(5)
            elif event.key == pygame.K_PAGEDOWN:
                self.scroll_down(5)
            elif event.key == pygame.K_HOME:
                # Scroll to oldest
                self.scroll_offset = max(0, len(self.full_history) - self.max_lines)
            elif event.key == pygame.K_END:
                self.scroll_to_bottom()
            elif event.unicode and event.unicode.isprintable():
                if len(self.input_text) < MAX_MESSAGE_LENGTH:
                    self.input_text += event.unicode
                    # Started typing — throttle to max 1 send per 500ms
                    if self.input_text:
                        now = pygame.time.get_ticks()
                        if not self.local_is_typing or now - self._last_typing_sent >= 500:
                            self.local_is_typing = True
                            self._last_typing_sent = now
                            self.session.send(LanMessageType.TYPING.value, {"typing": True})

        elif event.type == pygame.MOUSEWHEEL and self.active:
            # Mouse wheel scrolling
            if event.y > 0:
                self.scroll_up(2)
            elif event.y < 0:
                self.scroll_down(2)

    def poll_session(self):
        """Poll for incoming messages and update state."""
        # Check local typing timeout
        if self.local_is_typing:
            if pygame.time.get_ticks() - self.last_local_input_time > self.typing_timeout:
                self.local_is_typing = False
                self.session.send(LanMessageType.TYPING.value, {"typing": False})

        # Check for timed out pending ACKs — mark as failed (not confirmed)
        current_time = pygame.time.get_ticks() / 1000.0
        timed_out = [mid for mid, send_time in self.pending_acks.items()
                     if current_time - send_time > self.ack_timeout]
        for msg_id in timed_out:
            self._mark_failed(msg_id)

        # Read from dedicated chat_inbox — drain all queued messages per frame
        while True:
            try:
                msg = self.session.chat_inbox.get_nowait()
            except queue.Empty:
                break

            msg_type = msg.get("type")
            payload = msg.get("payload", {})

            if msg_type == LanMessageType.CHAT.value:
                text = payload.get("text", "")[:MAX_MESSAGE_LENGTH]
                msg_id = payload.get("msg_id")
                self.add_message(self.peer_name, text, msg_id=msg_id)
                # Send ACK if message has ID
                if msg_id:
                    self._send_ack(msg_id)
                # If we receive a message, they clearly stopped typing (or sent it)
                self.peer_is_typing = False
            elif msg_type == "chat_ack":
                # Message delivery confirmed
                msg_id = payload.get("msg_id")
                if msg_id:
                    self._mark_confirmed(msg_id)
            elif msg_type == LanMessageType.TYPING.value:
                self.peer_is_typing = payload.get("typing", False)
            elif msg_type == "disconnect":
                self.add_message("System", f"{self.peer_name} disconnected.")
                self.active = False
                self.peer_is_typing = False
                break

    def _draw_typing_indicator(self, surface, input_rect):
        """Draw 'Incoming Wormhole...' text and animated chevrons."""
        # Position above the input box
        base_x = input_rect.x + 10
        base_y = input_rect.y - 25

        # 1. Typing indicator text with peer name
        text_surf = self.font_small.render(f"{self.peer_name} is dialing...", True, cfg.HIGHLIGHT_CYAN)
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
                color = cfg.CHEVRON_ACTIVE  # Bright Amber
            else:
                color = (80, 40, 30)  # Dim Rust

            # Draw Chevron shape (pointing right)
            cx = chevron_start_x + i * 15
            cy = base_y + 8
            points = [
                (cx, cy - 6),
                (cx + 8, cy),
                (cx, cy + 6),
                (cx + 4, cy)  # Inner notch
            ]
            pygame.draw.polygon(surface, color, points)

    def _draw_quick_chat_hints(self, surface, rect):
        """Draw quick chat key hints below chat in two rows."""
        hint_y = rect.bottom + 55
        row1 = "[1-5] GG | Nice! | GL | Wait | WP"
        row2 = "[6-0] Impressive | Indeed | Glory | Kree! | Equines"
        hint_surf1 = self.font_small.render(row1, True, cfg.TEXT_MUTED)
        hint_surf2 = self.font_small.render(row2, True, cfg.TEXT_MUTED)
        surface.blit(hint_surf1, (rect.x + 5, hint_y))
        surface.blit(hint_surf2, (rect.x + 5, hint_y + 16))

    def _draw_scroll_indicator(self, surface, rect):
        """Draw scroll indicator showing new messages below."""
        if self.has_new_messages and self.scroll_offset > 0:
            indicator_rect = pygame.Rect(rect.x, rect.bottom - 25, rect.width, 20)
            pygame.draw.rect(surface, (50, 80, 120), indicator_rect)
            text = self.font_small.render("New messages below (End to jump)", True, cfg.HIGHLIGHT_CYAN)
            surface.blit(text, (rect.centerx - text.get_width() // 2, indicator_rect.y + 2))

    def draw(self, surface, rect: pygame.Rect, title: Optional[str] = None):
        """Draw the chat panel."""
        pygame.draw.rect(surface, (25, 30, 50), rect)
        pygame.draw.rect(surface, cfg.BG_BORDER, rect, 2)

        if title:
            title_surf = self.title_font.render(title, True, cfg.TEXT_LIGHT)
            surface.blit(title_surf, (rect.x + 10, rect.y - 30))

        # Calculate visible messages based on scroll
        total_messages = len(self.full_history)
        visible_count = min(self.max_lines, total_messages)

        if total_messages > 0:
            # End index is the latest message minus scroll offset
            end_idx = total_messages - self.scroll_offset
            start_idx = max(0, end_idx - visible_count)
            visible_messages = self.full_history[start_idx:end_idx]
        else:
            visible_messages = []

        y = rect.y + 10
        bubble_margin = 8
        bubble_padding_x = 10
        bubble_padding_y = 4
        max_bubble_width = rect.width - 40
        line_height = 32

        # Bubble background colors
        bubble_colors = {
            "You": (30, 60, 90),
            "System": (50, 50, 30),
        }
        # Border colors matching message text color
        border_colors = {
            "You": cfg.HIGHLIGHT_GREEN,
            "System": cfg.GOLD,
        }
        default_bubble_color = (40, 40, 60)  # Peer
        default_border_color = cfg.TEXT_LIGHT

        prev_prefix = None
        for entry in visible_messages:
            if isinstance(entry, str):
                text = entry
                color = cfg.TEXT_LIGHT
                timestamp = ""
                confirmed = True
                prefix = "System"
            else:
                text = entry["text"]
                color = entry["color"]
                timestamp = entry.get("timestamp", "")
                confirmed = entry.get("confirmed", True)
                prefix = entry.get("prefix", "System")

            failed = entry.get("failed", False) if isinstance(entry, dict) else False

            # Dim unconfirmed messages, tint failed red
            if failed:
                color = (255, 100, 100)
            elif not confirmed:
                color = tuple(max(0, c - 80) for c in color[:3])

            # Strip "Prefix: " from display text to show in bubble
            display_text = text
            colon_idx = text.find(": ")
            if colon_idx != -1 and colon_idx < 20:
                display_text = text[colon_idx + 2:]

            # Render display text
            text_surf = self.font.render(display_text, True, color)
            text_w = min(text_surf.get_width(), max_bubble_width - 2 * bubble_padding_x)
            bubble_w = text_w + 2 * bubble_padding_x
            bubble_h = text_surf.get_height() + 2 * bubble_padding_y

            bg_color = bubble_colors.get(prefix, default_bubble_color)
            brd_color = border_colors.get(prefix, default_border_color)

            # Draw sender name above bubble group when sender changes
            if prefix != prev_prefix and prefix != "System":
                sender_name = "You" if prefix == "You" else self.peer_name
                name_surf = self.font_small.render(sender_name, True, color)
                if prefix == "You":
                    surface.blit(name_surf, (rect.right - bubble_margin - name_surf.get_width() - 4, y))
                else:
                    surface.blit(name_surf, (rect.x + bubble_margin + 4, y))
                y += 14

            if prefix == "System":
                # System: centered bubble
                bx = rect.x + (rect.width - bubble_w) // 2
            elif prefix == "You":
                # You: right-aligned
                bx = rect.right - bubble_margin - bubble_w
            else:
                # Peer: left-aligned
                bx = rect.x + bubble_margin

            bubble_rect = pygame.Rect(bx, y, bubble_w, bubble_h)
            pygame.draw.rect(surface, bg_color, bubble_rect, border_radius=8)
            pygame.draw.rect(surface, brd_color, bubble_rect, width=1, border_radius=8)

            # Clip text to bubble width
            surface.blit(text_surf, (bx + bubble_padding_x, y + bubble_padding_y), area=pygame.Rect(0, 0, text_w, text_surf.get_height()))

            # Timestamp + confirmation in corner
            if timestamp:
                ts_text = f"[{timestamp}]"
                if prefix == "You":
                    if failed:
                        ts_text += " !"
                    elif confirmed:
                        ts_text += " v"
                    else:
                        ts_text += " ..."
                ts_color = (255, 80, 80) if failed else cfg.TEXT_TIMESTAMP
                ts_surf = self.timestamp_font.render(ts_text, True, ts_color)
                if prefix == "You":
                    surface.blit(ts_surf, (bubble_rect.x - ts_surf.get_width() - 4, y + bubble_padding_y + 2))
                else:
                    surface.blit(ts_surf, (bubble_rect.right + 4, y + bubble_padding_y + 2))

            prev_prefix = prefix
            y += line_height

        # Draw scroll indicator if scrolled up and new messages
        self._draw_scroll_indicator(surface, rect)

        # Input box
        input_rect = pygame.Rect(rect.x, rect.bottom + 10, rect.width, 40)

        # Draw typing indicator if peer is typing
        if self.peer_is_typing:
            self._draw_typing_indicator(surface, input_rect)

        pygame.draw.rect(surface, (30, 35, 60), input_rect)
        pygame.draw.rect(surface, cfg.BG_BORDER, input_rect, 2)
        placeholder = self.input_text or "Type message... (1-0 for quick chat)"
        text_color = cfg.TEXT_LIGHT if self.input_text else cfg.TEXT_DIM
        surf = self.font.render(placeholder, True, text_color)
        surface.blit(surf, (input_rect.x + 8, input_rect.y + 8))

        # Character counter
        if self.input_text:
            char_count = len(self.input_text)
            counter_text = f"{char_count}/{MAX_MESSAGE_LENGTH}"
            if char_count >= 180:
                counter_color = cfg.HIGHLIGHT_RED
            elif char_count >= 150:
                counter_color = cfg.GOLD
            else:
                counter_color = cfg.TEXT_MUTED
            counter_surf = self.font_small.render(counter_text, True, counter_color)
            surface.blit(counter_surf, (input_rect.right - counter_surf.get_width() - 8, input_rect.y + 12))

        # Draw scroll position indicator if scrolled
        if self.scroll_offset > 0:
            scroll_text = f"[{self.scroll_offset} up]"
            scroll_surf = self.font_small.render(scroll_text, True, cfg.TEXT_MUTED)
            surface.blit(scroll_surf, (rect.right - scroll_surf.get_width() - 5, rect.y + 2))

        # Draw quick chat hints
        self._draw_quick_chat_hints(surface, rect)

    def draw_unread_badge(self, surface, x: int, y: int):
        """Draw unread message badge at specified position.

        Args:
            surface: Pygame surface to draw on
            x: X position for badge
            y: Y position for badge
        """
        if self.unread_count <= 0:
            return

        # Draw badge background
        badge_text = str(min(self.unread_count, 99))
        if self.unread_count > 99:
            badge_text = "99+"

        text_surf = self.font_small.render(badge_text, True, (255, 255, 255))

        padding = 4
        badge_width = max(20, text_surf.get_width() + padding * 2)
        badge_height = text_surf.get_height() + padding

        badge_rect = pygame.Rect(x, y, badge_width, badge_height)
        pygame.draw.rect(surface, (200, 60, 60), badge_rect, border_radius=10)
        pygame.draw.rect(surface, (255, 100, 100), badge_rect, 1, border_radius=10)

        surface.blit(text_surf, (badge_rect.centerx - text_surf.get_width() // 2,
                                  badge_rect.centery - text_surf.get_height() // 2))
