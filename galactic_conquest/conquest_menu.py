"""
STARGWENT - GALACTIC CONQUEST - Conquest Submenu

Entry screen: New Run / Resume / Customize Run / Back.
CRT-themed Stargate terminal UI with scanline overlay.
"""

import asyncio
import pygame
import os
import math
import display_manager

from .campaign_persistence import (has_campaign_save, load_campaign,
                                    load_conquest_settings, save_conquest_settings)
from .galaxy_map import ALL_FACTIONS


# CRT UI colors
CRT_AMBER = (255, 200, 80)
CRT_CYAN = (100, 220, 255)
CRT_GREEN = (80, 255, 140)
CRT_BORDER = (80, 140, 100)
CRT_BTN_BG = (15, 25, 18)
CRT_BTN_HOVER = (30, 60, 40)
CRT_BTN_BORDER = (60, 160, 90)
CRT_BTN_BORDER_HOVER = (100, 255, 140)
CRT_TEXT = (180, 255, 200)
CRT_TEXT_DIM = (60, 90, 70)

FACTION_DISPLAY_COLORS = {
    "Tau'ri": (80, 160, 255),
    "Goa'uld": (255, 80, 80),
    "Jaffa Rebellion": (255, 220, 80),
    "Lucian Alliance": (255, 120, 220),
    "Asgard": (140, 220, 255),
}

# Pre-rendered scanline surface (created lazily)
_scanline_cache = {}


def _get_scanline_overlay(width, height, alpha=25):
    """Get or create a cached CRT scanline overlay surface."""
    key = (width, height, alpha)
    if key not in _scanline_cache:
        surf = pygame.Surface((width, height), pygame.SRCALPHA)
        line = pygame.Surface((width, 2), pygame.SRCALPHA)
        line.fill((0, 0, 0, alpha))
        for y in range(0, height, 4):
            surf.blit(line, (0, y))
        _scanline_cache[key] = surf
    return _scanline_cache[key]


class ConquestMenu:
    """Submenu for Galactic Conquest — CRT terminal UI."""

    def __init__(self, screen_width, screen_height):
        self.sw = screen_width
        self.sh = screen_height
        self.frame_count = 0

        # Load background
        self.background = None
        bg_path = os.path.join("assets", "conquest_menu_bg.png")
        if not os.path.exists(bg_path):
            bg_path = os.path.join("assets", "conquest.png")
        try:
            raw = pygame.image.load(bg_path).convert()
            self.background = pygame.transform.smoothscale(raw, (self.sw, self.sh))
        except (pygame.error, FileNotFoundError):
            self.background = pygame.Surface((self.sw, self.sh))
            self.background.fill((8, 12, 10))

        # Fonts
        self.title_font = pygame.font.SysFont("Impact, Arial", max(72, self.sh // 12), bold=True)
        self.button_font = pygame.font.SysFont("Impact, Arial Black, Arial",
                                                max(28, self.sh // 36), bold=True)
        self.info_font = pygame.font.SysFont("Arial", max(15, self.sh // 65))

        # Buttons — clean vertical stack, no panel
        btn_w = int(self.sw * 0.28)
        btn_h = int(self.sh * 0.065)
        btn_x = self.sw // 2 - btn_w // 2
        btn_y_start = int(self.sh * 0.40)
        btn_spacing = int(self.sh * 0.08)

        self.buttons = []
        labels = [
            ("NEW CAMPAIGN", "new_run"),
            ("RESUME", "resume"),
            ("CUSTOMIZE RUN", "customize_run"),
            ("UNLOCKS", "unlocks"),
            ("BACK", "back"),
        ]
        for i, (label, action) in enumerate(labels):
            rect = pygame.Rect(btn_x, btn_y_start + i * btn_spacing, btn_w, btn_h)
            self.buttons.append({"label": label, "action": action, "rect": rect})

        self.hovered = -1
        self._last_hovered = -1

        # Hover sound
        self._hover_sound = None
        try:
            snd_path = os.path.join("assets", "audio", "conquest_menu_select.ogg")
            if os.path.exists(snd_path):
                self._hover_sound = pygame.mixer.Sound(snd_path)
        except pygame.error:
            pass

        self.has_save = has_campaign_save()

        # Load save info for display
        self.save_info = None
        if self.has_save:
            try:
                state = load_campaign()
                if state:
                    self.save_info = {
                        "faction": state.player_faction,
                        "turn": state.turn_number,
                        "naquadah": state.naquadah,
                        "deck_size": len(state.current_deck),
                    }
            except Exception:
                pass

    def handle_event(self, event):
        """Handle input. Returns action string or None."""
        if event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            self.hovered = -1
            for i, btn in enumerate(self.buttons):
                if btn["rect"].collidepoint(mx, my):
                    self.hovered = i
                    break
            # Play hover sound when entering a new button
            if self.hovered != self._last_hovered and self.hovered >= 0:
                if self._hover_sound:
                    try:
                        from game_settings import get_settings
                        vol = get_settings().get_effective_sfx_volume()
                        self._hover_sound.set_volume(vol)
                        self._hover_sound.play()
                    except (pygame.error, Exception):
                        pass
            self._last_hovered = self.hovered

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            for i, btn in enumerate(self.buttons):
                if btn["rect"].collidepoint(mx, my):
                    action = btn["action"]
                    if action == "resume" and not self.has_save:
                        return None
                    return action

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return "back"

        return None

    def draw(self, screen):
        """Render the conquest menu with CRT scanline effect."""
        self.frame_count += 1

        # Background
        screen.blit(self.background, (0, 0))

        # Dark overlay
        overlay = pygame.Surface((self.sw, self.sh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        screen.blit(overlay, (0, 0))

        # Title with pulse
        pulse = 0.85 + 0.15 * math.sin(self.frame_count * 0.03)
        title_color = tuple(int(c * pulse) for c in CRT_AMBER)
        title1 = self.title_font.render("GALACTIC", True, title_color)
        title2 = self.title_font.render("CONQUEST", True, title_color)
        t1_y = int(self.sh * 0.08)
        screen.blit(title1, (self.sw // 2 - title1.get_width() // 2, t1_y))
        screen.blit(title2, (self.sw // 2 - title2.get_width() // 2,
                             t1_y + title1.get_height() - 5))

        # Decorative line
        line_y = t1_y + title1.get_height() + title2.get_height()
        line_w = int(self.sw * 0.3)
        line_color = tuple(int(c * pulse) for c in CRT_BORDER)
        pygame.draw.line(screen, line_color,
                         (self.sw // 2 - line_w // 2, line_y),
                         (self.sw // 2 + line_w // 2, line_y), 2)

        # Meta-progression stats
        from .meta_progression import load_meta
        meta = load_meta()
        cp = meta.get("total_cp", 0)
        played = meta.get("campaigns_played", 0)
        won = meta.get("campaigns_won", 0)
        perks = len(meta.get("unlocked_perks", []))
        meta_text = f"CP: {cp}  |  Campaigns: {played}  |  Wins: {won}  |  Perks: {perks}/5"
        meta_surf = self.info_font.render(meta_text, True, CRT_CYAN)
        screen.blit(meta_surf, (self.sw // 2 - meta_surf.get_width() // 2, line_y + 8))

        # Buttons
        for i, btn in enumerate(self.buttons):
            rect = btn["rect"]
            action = btn["action"]

            enabled = True
            if action == "resume" and not self.has_save:
                enabled = False

            if not enabled:
                bg_color = (10, 12, 10)
                border_color = (30, 40, 30)
                text_color = CRT_TEXT_DIM
            elif i == self.hovered:
                bg_color = CRT_BTN_HOVER
                border_color = CRT_BTN_BORDER_HOVER
                text_color = (255, 255, 255)
            else:
                bg_color = CRT_BTN_BG
                border_color = CRT_BTN_BORDER
                text_color = CRT_TEXT

            btn_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            btn_surf.fill((*bg_color, 220))
            screen.blit(btn_surf, rect.topleft)
            pygame.draw.rect(screen, border_color, rect, 2)

            if i == self.hovered and enabled:
                glow = pygame.Surface((rect.width + 6, rect.height + 6), pygame.SRCALPHA)
                glow.fill((*CRT_BTN_BORDER_HOVER, 20))
                screen.blit(glow, (rect.x - 3, rect.y - 3))

            label = self.button_font.render(btn["label"], True, text_color)
            screen.blit(label, (rect.centerx - label.get_width() // 2,
                                rect.centery - label.get_height() // 2))

            # Resume save info
            if action == "resume":
                if not self.has_save:
                    no_save = self.info_font.render("(No save found)", True, CRT_TEXT_DIM)
                    screen.blit(no_save, (rect.centerx - no_save.get_width() // 2,
                                          rect.bottom + 4))
                elif self.save_info and i != self.hovered:
                    info = self.save_info
                    save_text = (f"Turn {info['turn']} | {info['faction']} | "
                                 f"{info['deck_size']} cards | {info['naquadah']} naq")
                    save_surf = self.info_font.render(save_text, True, CRT_TEXT_DIM)
                    screen.blit(save_surf, (rect.centerx - save_surf.get_width() // 2,
                                            rect.bottom + 4))

        # CRT scanlines overlay
        scanlines = _get_scanline_overlay(self.sw, self.sh, alpha=25)
        screen.blit(scanlines, (0, 0))

        # Bottom bar
        bar_h = int(self.sh * 0.035)
        bar_rect = pygame.Rect(0, self.sh - bar_h, self.sw, bar_h)
        bar_surf = pygame.Surface((bar_rect.width, bar_rect.height), pygame.SRCALPHA)
        bar_surf.fill((0, 0, 0, 180))
        screen.blit(bar_surf, bar_rect.topleft)
        status = self.info_font.render("ESC to return", True, CRT_TEXT_DIM)
        screen.blit(status, (int(self.sw * 0.04), bar_rect.centery - status.get_height() // 2))


class CustomizeRunScreen:
    """Settings screen for customizing campaign parameters before starting a run."""

    def __init__(self, screen_width, screen_height):
        self.sw = screen_width
        self.sh = screen_height
        self.frame_count = 0

        # Load current settings
        self.settings = load_conquest_settings()

        # Faction options: None + all 5 factions
        self.faction_options = [None] + list(ALL_FACTIONS)
        # Neutral event count options
        self.neutral_options = [3, 5, 7, 9]
        # Difficulty options
        from .difficulty import DIFFICULTY_ORDER, DIFFICULTIES
        self.difficulty_options = DIFFICULTY_ORDER
        self.difficulty_data = DIFFICULTIES

        # Current indices
        self.faction_index = 0
        ff = self.settings.get("friendly_faction")
        if ff in self.faction_options:
            self.faction_index = self.faction_options.index(ff)

        self.neutral_index = 1  # default 5
        nc = self.settings.get("neutral_count", 5)
        if nc in self.neutral_options:
            self.neutral_index = self.neutral_options.index(nc)

        self.difficulty_index = 1  # default "normal"
        diff = self.settings.get("difficulty", "normal")
        if diff in self.difficulty_options:
            self.difficulty_index = self.difficulty_options.index(diff)

        # Enemy leader settings per faction
        self.enemy_leaders = dict(self.settings.get("enemy_leaders", {}))
        self._load_faction_leaders()

        # Background
        self.background = None
        bg_path = os.path.join("assets", "conquest_menu_bg.png")
        if not os.path.exists(bg_path):
            bg_path = os.path.join("assets", "conquest.png")
        try:
            raw = pygame.image.load(bg_path).convert()
            self.background = pygame.transform.smoothscale(raw, (self.sw, self.sh))
        except (pygame.error, FileNotFoundError):
            self.background = pygame.Surface((self.sw, self.sh))
            self.background.fill((8, 12, 10))

        # Fonts
        self.title_font = pygame.font.SysFont("Impact, Arial", max(48, self.sh // 18), bold=True)
        self.label_font = pygame.font.SysFont("Arial", max(22, self.sh // 42), bold=True)
        self.value_font = pygame.font.SysFont("Impact, Arial", max(24, self.sh // 40), bold=True)
        self.info_font = pygame.font.SysFont("Arial", max(14, self.sh // 70))

        # Build layout rects
        self._build_layout()

        self.hovered_btn = None

    def _load_faction_leaders(self):
        """Load available leaders for each faction."""
        from content_registry import get_all_leaders_for_faction
        self.faction_leaders = {}  # faction → list of leader names
        self.faction_leader_index = {}  # faction → current index

        for faction in ALL_FACTIONS:
            leaders = get_all_leaders_for_faction(faction)
            names = ["Random"] + [l.get("name", "?") for l in leaders]
            self.faction_leaders[faction] = names

            # Set initial index from settings
            current = self.enemy_leaders.get(faction)
            if current and current in names:
                self.faction_leader_index[faction] = names.index(current)
            else:
                self.faction_leader_index[faction] = 0  # "Random"

    def _build_layout(self):
        """Build UI element rectangles."""
        arrow_w = int(self.sw * 0.025)
        arrow_h = int(self.sh * 0.035)

        # Friendly Faction row
        row_y = int(self.sh * 0.22)
        self.friendly_left = pygame.Rect(
            int(self.sw * 0.30), row_y, arrow_w, arrow_h)
        self.friendly_right = pygame.Rect(
            int(self.sw * 0.70) - arrow_w, row_y, arrow_w, arrow_h)

        # Neutral Events row
        row_y2 = int(self.sh * 0.30)
        self.neutral_left = pygame.Rect(
            int(self.sw * 0.30), row_y2, arrow_w, arrow_h)
        self.neutral_right = pygame.Rect(
            int(self.sw * 0.70) - arrow_w, row_y2, arrow_w, arrow_h)

        # Difficulty row
        row_y3 = int(self.sh * 0.38)
        self.difficulty_left = pygame.Rect(
            int(self.sw * 0.30), row_y3, arrow_w, arrow_h)
        self.difficulty_right = pygame.Rect(
            int(self.sw * 0.70) - arrow_w, row_y3, arrow_w, arrow_h)

        # Enemy leader rows (up to 5 factions)
        self.leader_rows = {}
        base_y = int(self.sh * 0.50)
        spacing = int(self.sh * 0.065)
        for i, faction in enumerate(ALL_FACTIONS):
            y = base_y + i * spacing
            self.leader_rows[faction] = {
                "y": y,
                "left": pygame.Rect(int(self.sw * 0.55), y, arrow_w, arrow_h),
                "right": pygame.Rect(int(self.sw * 0.82) - arrow_w, y, arrow_w, arrow_h),
            }

        # Apply / Back buttons
        btn_w = int(self.sw * 0.15)
        btn_h = int(self.sh * 0.055)
        btn_y = int(self.sh * 0.88)
        self.apply_rect = pygame.Rect(self.sw // 2 - btn_w - 20, btn_y, btn_w, btn_h)
        self.back_rect = pygame.Rect(self.sw // 2 + 20, btn_y, btn_w, btn_h)

    def handle_event(self, event):
        """Handle input. Returns 'back' to close, None to continue."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos

            # Friendly faction arrows
            if self.friendly_left.collidepoint(mx, my):
                self.faction_index = (self.faction_index - 1) % len(self.faction_options)
            elif self.friendly_right.collidepoint(mx, my):
                self.faction_index = (self.faction_index + 1) % len(self.faction_options)

            # Neutral event arrows
            elif self.neutral_left.collidepoint(mx, my):
                self.neutral_index = (self.neutral_index - 1) % len(self.neutral_options)
            elif self.neutral_right.collidepoint(mx, my):
                self.neutral_index = (self.neutral_index + 1) % len(self.neutral_options)

            # Difficulty arrows
            elif self.difficulty_left.collidepoint(mx, my):
                self.difficulty_index = (self.difficulty_index - 1) % len(self.difficulty_options)
            elif self.difficulty_right.collidepoint(mx, my):
                self.difficulty_index = (self.difficulty_index + 1) % len(self.difficulty_options)

            # Leader arrows
            else:
                for faction, row in self.leader_rows.items():
                    if row["left"].collidepoint(mx, my):
                        names = self.faction_leaders.get(faction, ["Random"])
                        idx = self.faction_leader_index.get(faction, 0)
                        self.faction_leader_index[faction] = (idx - 1) % len(names)
                        break
                    elif row["right"].collidepoint(mx, my):
                        names = self.faction_leaders.get(faction, ["Random"])
                        idx = self.faction_leader_index.get(faction, 0)
                        self.faction_leader_index[faction] = (idx + 1) % len(names)
                        break

            # Apply
            if self.apply_rect.collidepoint(mx, my):
                self._save_settings()
                return "back"
            # Back
            if self.back_rect.collidepoint(mx, my):
                return "back"

        elif event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            self.hovered_btn = None
            if self.apply_rect.collidepoint(mx, my):
                self.hovered_btn = "apply"
            elif self.back_rect.collidepoint(mx, my):
                self.hovered_btn = "back"

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return "back"

        return None

    def _save_settings(self):
        """Save current settings to disk."""
        # Build enemy leaders dict (only non-Random)
        leaders = {}
        for faction in ALL_FACTIONS:
            idx = self.faction_leader_index.get(faction, 0)
            names = self.faction_leaders.get(faction, ["Random"])
            if idx > 0 and idx < len(names):
                leaders[faction] = names[idx]

        self.settings = {
            "friendly_faction": self.faction_options[self.faction_index],
            "neutral_count": self.neutral_options[self.neutral_index],
            "difficulty": self.difficulty_options[self.difficulty_index],
            "enemy_leaders": leaders,
        }
        save_conquest_settings(self.settings)

    def draw(self, screen):
        """Render the customize run screen with CRT aesthetic."""
        self.frame_count += 1

        # Background
        screen.blit(self.background, (0, 0))
        overlay = pygame.Surface((self.sw, self.sh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))

        # Title
        pulse = 0.85 + 0.15 * math.sin(self.frame_count * 0.03)
        title_color = tuple(int(c * pulse) for c in CRT_AMBER)
        title = self.title_font.render("CUSTOMIZE RUN", True, title_color)
        screen.blit(title, (self.sw // 2 - title.get_width() // 2, int(self.sh * 0.06)))

        # Decorative line
        line_y = int(self.sh * 0.06) + title.get_height() + 8
        line_w = int(self.sw * 0.25)
        pygame.draw.line(screen, tuple(int(c * pulse) for c in CRT_BORDER),
                         (self.sw // 2 - line_w // 2, line_y),
                         (self.sw // 2 + line_w // 2, line_y), 2)

        # --- Friendly Faction ---
        self._draw_option_row(screen, "FRIENDLY FACTION",
                              "Allied faction — their territory starts as yours",
                              self._get_faction_text(), self._get_faction_color(),
                              int(self.sh * 0.18), self.friendly_left, self.friendly_right)

        # --- Neutral Events ---
        nc_val = self.neutral_options[self.neutral_index]
        self._draw_option_row(screen, "NEUTRAL EVENTS",
                              f"Number of neutral planets with text events (max {self.neutral_options[-1]})",
                              str(nc_val), CRT_CYAN,
                              int(self.sh * 0.26), self.neutral_left, self.neutral_right)

        # --- Difficulty ---
        diff_key = self.difficulty_options[self.difficulty_index]
        diff_data = self.difficulty_data[diff_key]
        self._draw_option_row(screen, "DIFFICULTY",
                              diff_data["description"],
                              diff_data["name"], diff_data["color"],
                              int(self.sh * 0.34), self.difficulty_left, self.difficulty_right)

        # --- Enemy Leaders Section ---
        section_y = int(self.sh * 0.44)
        section_label = self.label_font.render("ENEMY LEADERS", True, CRT_AMBER)
        screen.blit(section_label, (self.sw // 2 - section_label.get_width() // 2, section_y))
        desc = self.info_font.render("Homeworld defenders — choose or leave random", True, CRT_TEXT_DIM)
        screen.blit(desc, (self.sw // 2 - desc.get_width() // 2, section_y + section_label.get_height() + 2))

        friendly = self.faction_options[self.faction_index]
        for faction in ALL_FACTIONS:
            row = self.leader_rows[faction]
            y = row["y"]
            is_friendly = (faction == friendly)

            # Faction name
            faction_color = FACTION_DISPLAY_COLORS.get(faction, CRT_TEXT)
            if is_friendly:
                faction_color = CRT_TEXT_DIM
            fname = self.label_font.render(faction, True, faction_color)
            screen.blit(fname, (int(self.sw * 0.15), y + 4))

            if is_friendly:
                tag = self.info_font.render("(Allied)", True, CRT_GREEN)
                screen.blit(tag, (int(self.sw * 0.15) + fname.get_width() + 10, y + 8))
                continue

            # Leader name with arrows
            idx = self.faction_leader_index.get(faction, 0)
            names = self.faction_leaders.get(faction, ["Random"])
            leader_name = names[idx] if idx < len(names) else "Random"
            leader_color = CRT_TEXT if idx == 0 else (255, 255, 255)

            # Left arrow
            self._draw_arrow(screen, row["left"], "left", CRT_BTN_BORDER)
            # Right arrow
            self._draw_arrow(screen, row["right"], "right", CRT_BTN_BORDER)
            # Leader name centered between arrows
            lname = self.value_font.render(leader_name, True, leader_color)
            center_x = (row["left"].right + row["right"].left) // 2
            screen.blit(lname, (center_x - lname.get_width() // 2, y + 3))

        # --- Apply / Back buttons ---
        for rect, label_text, key in [(self.apply_rect, "APPLY", "apply"),
                                       (self.back_rect, "BACK", "back")]:
            hovered = (self.hovered_btn == key)
            bg_color = CRT_BTN_HOVER if hovered else CRT_BTN_BG
            border_color = CRT_BTN_BORDER_HOVER if hovered else CRT_BTN_BORDER

            btn_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            btn_surf.fill((*bg_color, 220))
            screen.blit(btn_surf, rect.topleft)
            pygame.draw.rect(screen, border_color, rect, 2)

            label = self.label_font.render(label_text, True,
                                           (255, 255, 255) if hovered else CRT_TEXT)
            screen.blit(label, (rect.centerx - label.get_width() // 2,
                                rect.centery - label.get_height() // 2))

        # CRT scanlines
        scanlines = _get_scanline_overlay(self.sw, self.sh, alpha=25)
        screen.blit(scanlines, (0, 0))

    def _draw_option_row(self, screen, label_text, desc_text, value_text, value_color,
                         y, left_rect, right_rect):
        """Draw a labeled option row with left/right arrows and a centered value."""
        # Label
        label = self.label_font.render(label_text, True, CRT_TEXT)
        screen.blit(label, (self.sw // 2 - label.get_width() // 2, y))
        # Description
        desc = self.info_font.render(desc_text, True, CRT_TEXT_DIM)
        screen.blit(desc, (self.sw // 2 - desc.get_width() // 2, y + label.get_height() + 2))
        # Value row
        val_y = y + label.get_height() + desc.get_height() + 8
        # Left arrow
        lr = pygame.Rect(left_rect.x, val_y, left_rect.width, left_rect.height)
        left_rect.y = val_y
        self._draw_arrow(screen, lr, "left", CRT_BTN_BORDER)
        # Right arrow
        rr = pygame.Rect(right_rect.x, val_y, right_rect.width, right_rect.height)
        right_rect.y = val_y
        self._draw_arrow(screen, rr, "right", CRT_BTN_BORDER)
        # Value centered
        val = self.value_font.render(value_text, True, value_color)
        center_x = (lr.right + rr.left) // 2
        screen.blit(val, (center_x - val.get_width() // 2, val_y + 2))

    def _draw_arrow(self, screen, rect, direction, color):
        """Draw a triangle arrow (left or right)."""
        cx, cy = rect.center
        hw = rect.width // 3
        hh = rect.height // 3
        if direction == "left":
            points = [(cx + hw, cy - hh), (cx - hw, cy), (cx + hw, cy + hh)]
        else:
            points = [(cx - hw, cy - hh), (cx + hw, cy), (cx - hw, cy + hh)]
        pygame.draw.polygon(screen, color, points)

    def _get_faction_text(self):
        """Get display text for current friendly faction selection."""
        val = self.faction_options[self.faction_index]
        return val if val else "NONE"

    def _get_faction_color(self):
        """Get display color for current friendly faction selection."""
        val = self.faction_options[self.faction_index]
        if val:
            return FACTION_DISPLAY_COLORS.get(val, CRT_TEXT)
        return CRT_TEXT_DIM


async def run_conquest_menu(screen, unlock_system, toggle_fullscreen_callback=None):
    """
    Run the Galactic Conquest submenu.

    Returns:
        'new_run' | 'resume' | 'customize_run' | 'back' | None (quit)
    """
    clock = pygame.time.Clock()
    menu = ConquestMenu(screen.get_width(), screen.get_height())

    while True:
        clock.tick(60)
        await asyncio.sleep(0)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None

            # Handle fullscreen toggle
            if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                if toggle_fullscreen_callback:
                    toggle_fullscreen_callback()
                else:
                    display_manager.toggle_fullscreen_mode()
                screen = display_manager.screen
                menu = ConquestMenu(screen.get_width(), screen.get_height())
                pygame.event.clear()
                break

            action = menu.handle_event(event)
            if action:
                return action

        menu.draw(screen)
        display_manager.gpu_flip()


async def run_customize_screen(screen, toggle_fullscreen_callback=None):
    """
    Run the Customize Run settings screen.

    Returns when player clicks Apply or Back.
    """
    clock = pygame.time.Clock()
    customize = CustomizeRunScreen(screen.get_width(), screen.get_height())

    while True:
        clock.tick(60)
        await asyncio.sleep(0)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return

            if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                if toggle_fullscreen_callback:
                    toggle_fullscreen_callback()
                else:
                    display_manager.toggle_fullscreen_mode()
                screen = display_manager.screen
                customize = CustomizeRunScreen(screen.get_width(), screen.get_height())
                pygame.event.clear()
                break

            action = customize.handle_event(event)
            if action == "back":
                return

        customize.draw(screen)
        display_manager.gpu_flip()


async def run_unlocks_screen(screen, toggle_fullscreen_callback=None):
    """Show the meta-progression unlocks screen where players spend CP on perks."""
    from .meta_progression import load_meta, get_all_perks_display, unlock_perk, load_high_scores

    sw, sh = screen.get_width(), screen.get_height()
    clock = pygame.time.Clock()

    title_font = pygame.font.SysFont("Impact, Arial", max(48, sh // 18), bold=True)
    section_font = pygame.font.SysFont("Impact, Arial", max(24, sh // 38), bold=True)
    perk_font = pygame.font.SysFont("Arial", max(18, sh // 50), bold=True)
    info_font = pygame.font.SysFont("Arial", max(15, sh // 65))
    hint_font = pygame.font.SysFont("Arial", max(14, sh // 70))

    # Perk button layout
    perk_w = int(sw * 0.55)
    perk_h = int(sh * 0.065)
    perk_x = sw // 2 - perk_w // 2
    perk_y_start = int(sh * 0.22)
    perk_spacing = int(sh * 0.08)

    frame_count = 0
    message = ""
    message_timer = 0
    hovered_perk = -1

    # Load background
    background = None
    bg_path = os.path.join("assets", "conquest_menu_bg.png")
    if not os.path.exists(bg_path):
        bg_path = os.path.join("assets", "conquest.png")
    try:
        raw = pygame.image.load(bg_path).convert()
        background = pygame.transform.smoothscale(raw, (sw, sh))
    except (pygame.error, FileNotFoundError):
        background = pygame.Surface((sw, sh))
        background.fill((8, 12, 10))

    running = True
    while running:
        clock.tick(60)
        await asyncio.sleep(0)
        frame_count += 1
        if message_timer > 0:
            message_timer -= 1

        perks = get_all_perks_display()
        meta = load_meta()
        total_cp = meta.get("total_cp", 0)

        # Build perk rects
        perk_rects = []
        for i in range(len(perks)):
            perk_rects.append(pygame.Rect(perk_x, perk_y_start + i * perk_spacing, perk_w, perk_h))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_F11:
                    if toggle_fullscreen_callback:
                        toggle_fullscreen_callback()
                    else:
                        display_manager.toggle_fullscreen_mode()
                    screen = display_manager.screen
                    sw, sh = screen.get_width(), screen.get_height()
                    pygame.event.clear()
                    break

            elif event.type == pygame.MOUSEMOTION:
                mx, my = event.pos
                hovered_perk = -1
                for i, rect in enumerate(perk_rects):
                    if rect.collidepoint(mx, my):
                        hovered_perk = i
                        break

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                for i, rect in enumerate(perk_rects):
                    if rect.collidepoint(mx, my) and i < len(perks):
                        pid, name, desc, cost, icon, is_unlocked = perks[i]
                        if not is_unlocked:
                            success, msg = unlock_perk(pid)
                            message = msg
                            message_timer = 120
                        else:
                            message = f"{name} is already unlocked!"
                            message_timer = 60

        # Draw
        screen.blit(background, (0, 0))
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))

        # Title
        pulse = 0.85 + 0.15 * math.sin(frame_count * 0.03)
        title_color = tuple(int(c * pulse) for c in CRT_AMBER)
        title = title_font.render("CONQUEST UNLOCKS", True, title_color)
        screen.blit(title, (sw // 2 - title.get_width() // 2, int(sh * 0.04)))

        # CP display
        cp_text = section_font.render(f"Conquest Points: {total_cp}", True, CRT_CYAN)
        screen.blit(cp_text, (sw // 2 - cp_text.get_width() // 2, int(sh * 0.13)))

        # Perks
        for i, (pid, name, desc, cost, icon, is_unlocked) in enumerate(perks):
            if i >= len(perk_rects):
                break
            rect = perk_rects[i]

            if is_unlocked:
                bg_color = (20, 50, 30)
                border_color = CRT_GREEN
                text_color = CRT_GREEN
            elif i == hovered_perk:
                bg_color = CRT_BTN_HOVER
                border_color = CRT_BTN_BORDER_HOVER
                text_color = (255, 255, 255)
            else:
                bg_color = CRT_BTN_BG
                border_color = CRT_BTN_BORDER
                text_color = CRT_TEXT

            btn_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            btn_surf.fill((*bg_color, 220))
            screen.blit(btn_surf, rect.topleft)
            pygame.draw.rect(screen, border_color, rect, 2)

            # Icon + name
            label_text = f"{icon} {name}"
            if is_unlocked:
                label_text += " [UNLOCKED]"
            else:
                affordable = " " if total_cp >= cost else " (need more CP) "
                label_text += f" — {cost} CP{affordable}"
            label = perk_font.render(label_text, True, text_color)
            screen.blit(label, (rect.x + 12, rect.y + 6))

            # Description below
            desc_surf = info_font.render(desc, True, CRT_TEXT_DIM if is_unlocked else CRT_TEXT)
            screen.blit(desc_surf, (rect.x + 12, rect.y + rect.height - desc_surf.get_height() - 4))

        # High scores section
        scores_y = perk_y_start + len(perks) * perk_spacing + int(sh * 0.03)
        scores_title = section_font.render("HIGH SCORES", True, CRT_AMBER)
        screen.blit(scores_title, (sw // 2 - scores_title.get_width() // 2, scores_y))
        scores_y += scores_title.get_height() + 8

        high_scores = load_high_scores()
        if high_scores:
            for j, entry in enumerate(high_scores[:5]):
                score_text = (f"#{j+1}  {entry.get('score', 0)} pts — "
                              f"{entry.get('faction', '?')} ({entry.get('leader', '?')}) — "
                              f"{entry.get('difficulty', '?').title()} — "
                              f"T{entry.get('turns', '?')} — +{entry.get('cp_earned', 0)} CP")
                color = CRT_AMBER if j == 0 else CRT_TEXT
                s = info_font.render(score_text, True, color)
                screen.blit(s, (sw // 2 - s.get_width() // 2, scores_y))
                scores_y += s.get_height() + 4
        else:
            no_scores = info_font.render("No campaigns completed yet.", True, CRT_TEXT_DIM)
            screen.blit(no_scores, (sw // 2 - no_scores.get_width() // 2, scores_y))

        # Message
        if message and message_timer > 0:
            msg_surf = perk_font.render(message, True, (100, 255, 200))
            screen.blit(msg_surf, (sw // 2 - msg_surf.get_width() // 2, int(sh * 0.92)))

        # CRT scanlines
        scanlines = _get_scanline_overlay(sw, sh, alpha=25)
        screen.blit(scanlines, (0, 0))

        # Bottom bar
        bar_h = int(sh * 0.035)
        bar_rect = pygame.Rect(0, sh - bar_h, sw, bar_h)
        bar_surf = pygame.Surface((bar_rect.width, bar_rect.height), pygame.SRCALPHA)
        bar_surf.fill((0, 0, 0, 180))
        screen.blit(bar_surf, bar_rect.topleft)
        hint = hint_font.render("ESC to return  |  Click a perk to unlock", True, CRT_TEXT_DIM)
        screen.blit(hint, (int(sw * 0.04), bar_rect.centery - hint.get_height() // 2))

        display_manager.gpu_flip()
