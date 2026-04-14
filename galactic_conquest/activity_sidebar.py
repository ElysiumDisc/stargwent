"""
STARGWENT - GALACTIC CONQUEST - Activity Log Sidebar (12.0 Pillar 3e UI)

Right-edge slide-out panel that surfaces ``campaign_state.activity_log``
entries as a scrollable historical feed of what's been happening in
the galaxy — your battles, AI-vs-AI wars, diplomatic shifts, rival
arc beats, leader actions.

Toggle with **L** on the map or click the tab on the right edge.
Stateless-ish: a single ``ActivitySidebar`` instance lives on the
``MapScreen`` and stores only its toggle + scroll state.
"""

import pygame

from . import activity_log


# Display tuning
WIDTH_FRAC = 0.26                 # of screen width
MAX_VISIBLE_ROWS = 24
ROW_H = 32


# Per-category accent colors.  Defaults fall back to a soft grey.
CATEGORY_COLORS = {
    activity_log.CAT_BATTLE:        (90, 220, 120),
    activity_log.CAT_COUNTERATTACK: (220, 140, 90),
    activity_log.CAT_AI_WAR:        (220, 100, 100),
    activity_log.CAT_DIPLOMACY:     (120, 180, 220),
    activity_log.CAT_CRISIS:        (220, 180, 90),
    activity_log.CAT_LEADER_ACTION: (200, 180, 255),
    activity_log.CAT_RIVAL_ARC:     (230, 110, 110),
    activity_log.CAT_ECONOMY:       (200, 220, 120),
    activity_log.CAT_DISCOVERY:     (180, 220, 230),
    activity_log.CAT_SYSTEM:        (160, 160, 180),
}


class ActivitySidebar:
    """Stateful wrapper — holds toggle + scroll offset across frames."""

    def __init__(self):
        self.visible = False
        self.scroll = 0  # 0 = pinned to newest; increases as user scrolls up
        # Surface + cache-key for the panel. Rebuilt only when inputs change.
        self._panel_surf = None
        self._panel_key = None
        # Surface + key for the always-drawn tab sliver.
        self._tab_surf = None
        self._tab_key = None

    def toggle(self):
        self.visible = not self.visible
        self.scroll = 0

    # --- Geometry -------------------------------------------------------

    def _compute_rect(self, mapscreen):
        sw, sh = mapscreen.sw, mapscreen.sh
        w = int(sw * WIDTH_FRAC)
        h = sh - int(sh * 0.1)
        x = sw - w - 4
        y = int(sh * 0.05)
        return pygame.Rect(x, y, w, h)

    def _tab_rect(self, mapscreen):
        """Always-visible sliver on the right edge that opens the panel."""
        sw, sh = mapscreen.sw, mapscreen.sh
        h = int(sh * 0.10)
        w = 22
        x = sw - w
        y = int(sh * 0.20)
        return pygame.Rect(x, y, w, h)

    # --- Input ----------------------------------------------------------

    def handle_event(self, event, mapscreen):
        """Return True if the event was consumed (stop propagation)."""
        if event.type == pygame.KEYDOWN and event.key == pygame.K_l:
            self.toggle()
            return True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._tab_rect(mapscreen).collidepoint(event.pos):
                self.toggle()
                return True
            if self.visible and self._compute_rect(mapscreen).collidepoint(event.pos):
                # Click inside the panel doesn't do anything yet — but
                # still consume to prevent map deselection.
                return True

        if self.visible and event.type == pygame.MOUSEWHEEL:
            self.scroll = max(0, self.scroll - event.y)
            return True

        return False

    # --- Render ---------------------------------------------------------

    def draw(self, screen, mapscreen, campaign_state):
        # Always draw the tab so the user knows the sidebar exists.
        self._draw_tab(screen, mapscreen, open_state=self.visible)

        if not self.visible:
            return

        rect = self._compute_rect(mapscreen)
        entries = campaign_state.activity_log or ()

        # Cache key: anything that changes what the panel shows.
        key = (rect.size, len(entries), self.scroll, id(entries))
        if key != self._panel_key or self._panel_surf is None:
            self._panel_surf = self._build_panel(mapscreen, rect, entries)
            self._panel_key = key

        screen.blit(self._panel_surf, rect.topleft)

    def _build_panel(self, mapscreen, rect, entries):
        font_h = mapscreen.font_btn
        font_r = mapscreen.font_info

        panel = pygame.Surface(rect.size, pygame.SRCALPHA)
        panel.fill((10, 14, 26, 235))
        pygame.draw.rect(panel, (70, 100, 150), panel.get_rect(), 1)

        header = font_h.render("ACTIVITY LOG  (L to toggle)",
                                 True, (255, 220, 130))
        panel.blit(header, (8, 6))
        pygame.draw.line(panel, (60, 80, 120), (4, 28),
                          (rect.width - 4, 28), 1)

        if not entries:
            empty = font_r.render("Nothing yet.", True, (160, 160, 180))
            panel.blit(empty, (8, 34))
            return panel

        # Newest last — reverse for display and apply scroll.
        reversed_entries = list(reversed(entries))
        start = min(self.scroll, max(0, len(reversed_entries) - 1))
        visible_count = min(MAX_VISIBLE_ROWS,
                             (rect.height - 32) // ROW_H)
        visible = reversed_entries[start:start + visible_count]

        y = 32
        for entry in visible:
            color = CATEGORY_COLORS.get(entry.get("category"), (200, 200, 220))
            # Side marker
            pygame.draw.rect(panel, color, (4, y + 4, 3, ROW_H - 8))
            # Turn prefix
            turn = entry.get("turn", 0)
            prefix = font_r.render(f"T{turn}", True, (140, 160, 190))
            panel.blit(prefix, (12, y + 6))
            # Truncate to width. Panel surface is cached, so this only
            # runs on rebuild (scroll/entry-count change), not per-frame.
            max_w = rect.width - 12 - prefix.get_width() - 8 - 8
            body = entry.get("text", "")
            if font_r.size(body)[0] > max_w:
                while body and font_r.size(body + "...")[0] > max_w:
                    body = body[:-1]
                body += "..."
            body_surf = font_r.render(body, True, color)
            panel.blit(body_surf,
                       (12 + prefix.get_width() + 8, y + 6))
            y += ROW_H

        # Scroll hint
        if start + visible_count < len(reversed_entries):
            more = font_r.render(
                f"… {len(reversed_entries) - start - visible_count} older (scroll up)",
                True, (140, 150, 170))
            panel.blit(more, (8, rect.height - more.get_height() - 6))

        return panel

    def _draw_tab(self, screen, mapscreen, open_state):
        rect = self._tab_rect(mapscreen)
        key = (rect.size, open_state)
        if key != self._tab_key or self._tab_surf is None:
            tab = pygame.Surface(rect.size, pygame.SRCALPHA)
            tab.fill((40, 60, 100, 230) if open_state else (30, 40, 70, 200))
            pygame.draw.rect(tab, (100, 140, 200), tab.get_rect(), 1)
            label_font = mapscreen.font_info
            for i, ch in enumerate("LOG"):
                s = label_font.render(ch, True, (230, 220, 180))
                tab.blit(s, ((rect.width - s.get_width()) // 2, 8 + i * 14))
            self._tab_surf = tab
            self._tab_key = key
        screen.blit(self._tab_surf, rect.topleft)
