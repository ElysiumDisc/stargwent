"""
STARGWENT - DRAFT MODE UI

Handles all rendering and interaction for Draft Mode (Arena).
"""

import pygame
import math
import os
from typing import List, Dict, Optional, Tuple
from cards import Card, ALL_CARDS
from animations import get_scale_factor


# Colors
COLOR_DARK_BG = (15, 15, 25)
COLOR_PANEL_BG = (25, 30, 45)
COLOR_CARD_BG = (35, 40, 60)
COLOR_CARD_HOVER = (50, 60, 90)
COLOR_CARD_SELECTED = (70, 100, 180)
COLOR_TEXT_PRIMARY = (220, 220, 230)
COLOR_TEXT_SECONDARY = (150, 160, 180)
COLOR_ACCENT_GOLD = (255, 215, 0)
COLOR_ACCENT_BLUE = (100, 150, 255)


class DraftModeUI:
    """Manages Draft Mode UI rendering and interaction."""

    def __init__(self, screen_width: int, screen_height: int):
        """
        Initialize Draft Mode UI.

        Args:
            screen_width: Screen width in pixels
            screen_height: Screen height in pixels
        """
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.scale = get_scale_factor(screen_height)

        # UI element dimensions
        self.card_width = int(200 * self.scale)
        self.card_height = int(300 * self.scale)
        self.card_spacing = int(40 * self.scale)

        # Fonts
        self.font_title = pygame.font.Font(None, int(72 * self.scale))
        self.font_header = pygame.font.Font(None, int(48 * self.scale))
        self.font_body = pygame.font.Font(None, int(32 * self.scale))
        self.font_small = pygame.font.Font(None, int(24 * self.scale))

        # Hover state
        self.hovered_index = None
        self.selected_index = None

        # Load draft mode background
        self.draft_bg = None
        draft_bg_path = os.path.join("assets", "draft_mode_bg.png")
        if os.path.exists(draft_bg_path):
            try:
                self.draft_bg = pygame.image.load(draft_bg_path).convert()
                self.draft_bg = pygame.transform.scale(self.draft_bg, (screen_width, screen_height))
                print(f"✓ Loaded draft mode background from {draft_bg_path}")
            except Exception as e:
                print(f"Warning: Could not load draft background: {e}")
                self.draft_bg = None
        else:
            print(f"Draft mode background not found at {draft_bg_path}")

    def draw_leader_selection(self, surface: pygame.Surface, leaders: List[Dict]) -> List[pygame.Rect]:
        """
        Draw leader selection screen.

        Args:
            surface: Pygame surface to draw on
            leaders: List of leader choices

        Returns:
            List of clickable rects for each leader
        """
        # Use background image if available, otherwise fill with color
        if self.draft_bg:
            surface.blit(self.draft_bg, (0, 0))
        else:
            surface.fill(COLOR_DARK_BG)

        # Title
        title = self.font_title.render("SELECT YOUR LEADER", True, COLOR_ACCENT_GOLD)
        title_rect = title.get_rect(center=(self.screen_width // 2, int(80 * self.scale)))
        surface.blit(title, title_rect)

        # Subtitle
        subtitle = self.font_body.render("Choose wisely - your leader's ability is crucial!", True, COLOR_TEXT_SECONDARY)
        subtitle_rect = subtitle.get_rect(center=(self.screen_width // 2, int(140 * self.scale)))
        surface.blit(subtitle, subtitle_rect)

        # Draw leader cards
        leader_rects = []
        start_x = (self.screen_width - (self.card_width * 3 + self.card_spacing * 2)) // 2
        start_y = int(220 * self.scale)

        for i, leader in enumerate(leaders):
            x = start_x + i * (self.card_width + self.card_spacing)
            y = start_y

            # Card background with glow effect for hover/selection
            color = COLOR_CARD_SELECTED if i == self.selected_index else \
                    COLOR_CARD_HOVER if i == self.hovered_index else \
                    COLOR_CARD_BG

            rect = pygame.Rect(x, y, self.card_width, self.card_height)

            # Try to load and display leader card image (prefer _leader.png variant)
            leader_card_id = leader.get('card_id')
            leader_image = None

            if leader_card_id:
                # First try loading the _leader.png variant for better portrait art
                leader_image_path = os.path.join("assets", f"{leader_card_id}_leader.png")
                if os.path.exists(leader_image_path):
                    try:
                        leader_image = pygame.image.load(leader_image_path).convert_alpha()
                        leader_image = pygame.transform.smoothscale(leader_image, (self.card_width, self.card_height))
                    except Exception as e:
                        print(f"Warning: Could not load {leader_image_path}: {e}")
                        leader_image = None

                # Fallback to card in ALL_CARDS if _leader.png doesn't exist
                if leader_image is None and leader_card_id in ALL_CARDS:
                    leader_card = ALL_CARDS[leader_card_id]
                    leader_image = pygame.transform.smoothscale(leader_card.image, (self.card_width, self.card_height))

            if leader_image:
                surface.blit(leader_image, (x, y))

                # Add border
                border_color = COLOR_ACCENT_GOLD if i == self.selected_index else \
                              COLOR_ACCENT_BLUE if i == self.hovered_index else \
                              COLOR_TEXT_SECONDARY
                border_width = 5 if i == self.selected_index else 3
                pygame.draw.rect(surface, border_color, rect, width=border_width, border_radius=10)

                # Draw leader name at bottom with semi-transparent background
                name_bg_height = 60
                name_bg = pygame.Surface((self.card_width, name_bg_height), pygame.SRCALPHA)
                name_bg.fill((0, 0, 0, 180))
                surface.blit(name_bg, (x, y + self.card_height - name_bg_height))

                name = self.font_body.render(leader['name'], True, COLOR_ACCENT_GOLD)
                name_rect = name.get_rect(center=(x + self.card_width // 2, y + self.card_height - 30))
                surface.blit(name, name_rect)
            else:
                # Fallback: draw colored rectangle with text (old behavior)
                pygame.draw.rect(surface, color, rect, border_radius=10)
                pygame.draw.rect(surface, COLOR_ACCENT_BLUE, rect, width=3, border_radius=10)

                # Leader name
                name = self.font_header.render(leader['name'], True, COLOR_TEXT_PRIMARY)
                name_rect = name.get_rect(center=(x + self.card_width // 2, y + 40))
                surface.blit(name, name_rect)

                # Leader faction
                faction_text = self.font_small.render(f"Faction: {leader.get('faction', 'Unknown')}", True, COLOR_TEXT_SECONDARY)
                faction_rect = faction_text.get_rect(center=(x + self.card_width // 2, y + 80))
                surface.blit(faction_text, faction_rect)

                # Ability description (wrapped)
                ability = leader.get('ability_desc', '')
                self._draw_wrapped_text(surface, ability, (x + 10, y + 120), self.card_width - 20,
                                       self.font_small, COLOR_TEXT_PRIMARY)

            leader_rects.append(rect)

        # Instructions
        instructions = self.font_body.render("Click a leader to begin drafting", True, COLOR_ACCENT_GOLD)
        instructions_rect = instructions.get_rect(center=(self.screen_width // 2, self.screen_height - 60))
        surface.blit(instructions, instructions_rect)

        return leader_rects

    def draw_draft_phase(self, surface: pygame.Surface, choices: List[Card],
                        current_pick: int, total_picks: int, drafted_cards: List[Card]) -> List[pygame.Rect]:
        """
        Draw card drafting screen.

        Args:
            surface: Pygame surface to draw on
            choices: List of 3 card choices
            current_pick: Current pick number (0-indexed)
            total_picks: Total number of picks needed
            drafted_cards: Cards already drafted

        Returns:
            List of clickable rects for each choice
        """
        # Use background image if available, otherwise fill with color
        if self.draft_bg:
            surface.blit(self.draft_bg, (0, 0))
        else:
            surface.fill(COLOR_DARK_BG)

        # Progress header
        progress_text = f"PICK {current_pick + 1} of {total_picks}"
        progress = self.font_header.render(progress_text, True, COLOR_ACCENT_GOLD)
        progress_rect = progress.get_rect(center=(self.screen_width // 2, 40))
        surface.blit(progress, progress_rect)

        # Progress bar
        bar_width = int(600 * self.scale)
        bar_height = int(20 * self.scale)
        bar_x = (self.screen_width - bar_width) // 2
        bar_y = int(90 * self.scale)

        # Background
        pygame.draw.rect(surface, COLOR_PANEL_BG, (bar_x, bar_y, bar_width, bar_height), border_radius=10)
        # Fill
        fill_width = int(bar_width * (current_pick / total_picks))
        if fill_width > 0:
            pygame.draw.rect(surface, COLOR_ACCENT_BLUE, (bar_x, bar_y, fill_width, bar_height), border_radius=10)

        # Draw card choices
        choice_rects = []
        start_x = (self.screen_width - (self.card_width * 3 + self.card_spacing * 2)) // 2
        start_y = int(160 * self.scale)

        for i, card in enumerate(choices):
            x = start_x + i * (self.card_width + self.card_spacing)
            y = start_y

            rect = pygame.Rect(x, y, self.card_width, self.card_height * 1.2)

            # Display actual card image from assets
            if card.image:
                # Scale card image to fit
                card_image = pygame.transform.smoothscale(card.image, (self.card_width, int(self.card_height * 1.2)))
                surface.blit(card_image, (x, y))

                # Add border based on state
                border_color = COLOR_ACCENT_GOLD if i == self.selected_index else \
                              self._get_faction_color(card.faction) if i == self.hovered_index else \
                              COLOR_TEXT_SECONDARY
                border_width = 5 if i == self.selected_index else 3
                pygame.draw.rect(surface, border_color, rect, width=border_width, border_radius=10)

                # Add semi-transparent info overlay at bottom
                info_height = 80
                info_bg = pygame.Surface((self.card_width, info_height), pygame.SRCALPHA)
                info_bg.fill((0, 0, 0, 200))
                surface.blit(info_bg, (x, y + int(self.card_height * 1.2) - info_height))

                # Card name
                name = self.font_small.render(card.name[:18], True, COLOR_TEXT_PRIMARY)
                name_rect = name.get_rect(center=(x + self.card_width // 2, y + int(self.card_height * 1.2) - 60))
                surface.blit(name, name_rect)

                # Power and row
                info_text = f"⚡{card.power}  {card.row.upper()}"
                info = self.font_small.render(info_text, True, COLOR_ACCENT_GOLD)
                info_rect = info.get_rect(center=(x + self.card_width // 2, y + int(self.card_height * 1.2) - 35))
                surface.blit(info, info_rect)

            else:
                # Fallback to colored rectangle with text (old behavior)
                color = COLOR_CARD_SELECTED if i == self.selected_index else \
                        COLOR_CARD_HOVER if i == self.hovered_index else \
                        COLOR_CARD_BG

                pygame.draw.rect(surface, color, rect, border_radius=10)
                pygame.draw.rect(surface, self._get_faction_color(card.faction), rect, width=3, border_radius=10)

                # Card name
                name = self.font_body.render(card.name, True, COLOR_TEXT_PRIMARY)
                name_rect = name.get_rect(center=(x + self.card_width // 2, y + 30))
                surface.blit(name, name_rect)

                # Power
                power_text = self.font_header.render(str(card.power), True, COLOR_ACCENT_GOLD)
                power_rect = power_text.get_rect(center=(x + self.card_width // 2, y + 80))
                surface.blit(power_text, power_rect)

                # Row
                row_text = self.font_small.render(f"{card.row.upper()}", True, COLOR_TEXT_SECONDARY)
                row_rect = row_text.get_rect(center=(x + self.card_width // 2, y + 130))
                surface.blit(row_text, row_rect)

                # Ability (if present)
                if card.ability:
                    ability_y = y + 170
                    self._draw_wrapped_text(surface, card.ability, (x + 10, ability_y),
                                          self.card_width - 20, self.font_small, COLOR_ACCENT_BLUE)

            choice_rects.append(rect)

        # Deck preview sidebar
        self._draw_deck_preview(surface, drafted_cards)

        # Instructions
        instructions = self.font_body.render("Click a card to add it to your deck", True, COLOR_TEXT_SECONDARY)
        instructions_rect = instructions.get_rect(center=(self.screen_width // 2, self.screen_height - 40))
        surface.blit(instructions, instructions_rect)

        return choice_rects

    def draw_review_phase(self, surface: pygame.Surface, drafted_leader: Dict,
                         drafted_cards: List[Card], stats: Dict) -> Tuple[pygame.Rect, pygame.Rect]:
        """
        Draw deck review screen before battle.

        Args:
            surface: Pygame surface to draw on
            drafted_leader: Selected leader
            drafted_cards: All drafted cards
            stats: Deck statistics

        Returns:
            Tuple of (start_battle_rect, redraft_rect)
        """
        # Use background image if available, otherwise fill with color
        if self.draft_bg:
            surface.blit(self.draft_bg, (0, 0))
        else:
            surface.fill(COLOR_DARK_BG)

        # Title
        title = self.font_title.render("YOUR DRAFTED DECK", True, COLOR_ACCENT_GOLD)
        title_rect = title.get_rect(center=(self.screen_width // 2, 50))
        surface.blit(title, title_rect)

        # Leader display with image
        leader_x = 50
        leader_y = 120
        leader_card_width = int(150 * self.scale)
        leader_card_height = int(225 * self.scale)

        # Try to load leader image (_leader.png variant)
        leader_card_id = drafted_leader.get('card_id')
        leader_image = None

        if leader_card_id:
            # First try loading the _leader.png variant
            leader_image_path = os.path.join("assets", f"{leader_card_id}_leader.png")
            if os.path.exists(leader_image_path):
                try:
                    leader_image = pygame.image.load(leader_image_path).convert_alpha()
                    leader_image = pygame.transform.smoothscale(leader_image, (leader_card_width, leader_card_height))
                except Exception as e:
                    print(f"Warning: Could not load {leader_image_path}: {e}")
                    leader_image = None

            # Fallback to ALL_CARDS
            if leader_image is None and leader_card_id in ALL_CARDS:
                leader_card = ALL_CARDS[leader_card_id]
                leader_image = pygame.transform.smoothscale(leader_card.image, (leader_card_width, leader_card_height))

        if leader_image:
            surface.blit(leader_image, (leader_x, leader_y))
            # Draw border
            leader_rect_border = pygame.Rect(leader_x, leader_y, leader_card_width, leader_card_height)
            pygame.draw.rect(surface, COLOR_ACCENT_GOLD, leader_rect_border, width=3, border_radius=8)

            # Leader name below image
            leader_name = self.font_body.render(drafted_leader['name'], True, COLOR_TEXT_PRIMARY)
            leader_name_rect = leader_name.get_rect(topleft=(leader_x, leader_y + leader_card_height + 10))
            surface.blit(leader_name, leader_name_rect)
        else:
            # Fallback: just text
            leader_name = self.font_header.render(f"Leader: {drafted_leader['name']}", True, COLOR_TEXT_PRIMARY)
            leader_name_rect = leader_name.get_rect(topleft=(leader_x, leader_y))
            surface.blit(leader_name, leader_name_rect)

        # Stats panel (positioned below leader image)
        stats_x = 50
        stats_y = leader_y + leader_card_height + 60 if leader_image else 200
        stats_texts = [
            f"Total Cards: {stats['total_cards']}",
            f"Total Power: {stats['total_power']}",
            f"Average Power: {stats['avg_power']:.1f}",
            f"Cards with Abilities: {stats['ability_count']}"
        ]

        for i, text in enumerate(stats_texts):
            stat_surf = self.font_body.render(text, True, COLOR_TEXT_SECONDARY)
            surface.blit(stat_surf, (stats_x, stats_y + i * 40))

        # Faction breakdown
        faction_y = stats_y + len(stats_texts) * 40 + 40
        faction_title = self.font_body.render("Faction Breakdown:", True, COLOR_ACCENT_BLUE)
        surface.blit(faction_title, (stats_x, faction_y))

        for i, (faction, count) in enumerate(stats['faction_breakdown'].items()):
            text = self.font_small.render(f"  {faction}: {count} cards", True, COLOR_TEXT_SECONDARY)
            surface.blit(text, (stats_x + 20, faction_y + 40 + i * 30))

        # Buttons
        button_width = 300
        button_height = 60
        button_y = self.screen_height - 120

        # Start Battle button
        battle_rect = pygame.Rect((self.screen_width // 2 - button_width - 20, button_y, button_width, button_height))
        pygame.draw.rect(surface, COLOR_ACCENT_BLUE, battle_rect, border_radius=10)
        battle_text = self.font_header.render("START BATTLE", True, COLOR_TEXT_PRIMARY)
        battle_text_rect = battle_text.get_rect(center=battle_rect.center)
        surface.blit(battle_text, battle_text_rect)

        # Redraft button
        redraft_rect = pygame.Rect((self.screen_width // 2 + 20, button_y, button_width, button_height))
        pygame.draw.rect(surface, COLOR_PANEL_BG, redraft_rect, border_radius=10)
        pygame.draw.rect(surface, COLOR_TEXT_SECONDARY, redraft_rect, width=2, border_radius=10)
        redraft_text = self.font_body.render("Redraft", True, COLOR_TEXT_SECONDARY)
        redraft_text_rect = redraft_text.get_rect(center=redraft_rect.center)
        surface.blit(redraft_text, redraft_text_rect)

        # Card grid preview (right side)
        self._draw_full_deck_grid(surface, drafted_cards)

        return battle_rect, redraft_rect

    def _draw_deck_preview(self, surface: pygame.Surface, cards: List[Card]):
        """Draw compact deck preview on the right side."""
        preview_x = self.screen_width - 250
        preview_y = 160
        preview_width = 230
        preview_height = 400

        # Background panel
        panel_rect = pygame.Rect(preview_x, preview_y, preview_width, preview_height)
        pygame.draw.rect(surface, COLOR_PANEL_BG, panel_rect, border_radius=10)
        pygame.draw.rect(surface, COLOR_ACCENT_BLUE, panel_rect, width=2, border_radius=10)

        # Title
        title = self.font_body.render("Your Deck", True, COLOR_ACCENT_GOLD)
        title_rect = title.get_rect(center=(preview_x + preview_width // 2, preview_y + 25))
        surface.blit(title, title_rect)

        # Card count
        count_text = self.font_small.render(f"{len(cards)} / 30", True, COLOR_TEXT_SECONDARY)
        count_rect = count_text.get_rect(center=(preview_x + preview_width // 2, preview_y + 55))
        surface.blit(count_text, count_rect)

        # List recent cards
        list_y = preview_y + 90
        max_display = 8
        display_cards = cards[-max_display:] if len(cards) > max_display else cards

        for i, card in enumerate(display_cards):
            card_text = self.font_small.render(f"{card.power} - {card.name[:15]}", True, COLOR_TEXT_PRIMARY)
            surface.blit(card_text, (preview_x + 10, list_y + i * 30))

        if len(cards) > max_display:
            more_text = self.font_small.render(f"... +{len(cards) - max_display} more", True, COLOR_TEXT_SECONDARY)
            surface.blit(more_text, (preview_x + 10, list_y + max_display * 30))

    def _draw_full_deck_grid(self, surface: pygame.Surface, cards: List[Card]):
        """Draw full deck as a grid on the review screen."""
        grid_x = self.screen_width // 2 + 50
        grid_y = 200
        card_w = 80
        card_h = 30
        cols = 6
        spacing = 5

        for i, card in enumerate(cards):
            row = i // cols
            col = i % cols
            x = grid_x + col * (card_w + spacing)
            y = grid_y + row * (card_h + spacing)

            # Mini card
            rect = pygame.Rect(x, y, card_w, card_h)
            pygame.draw.rect(surface, COLOR_CARD_BG, rect, border_radius=3)
            pygame.draw.rect(surface, self._get_faction_color(card.faction), rect, width=1, border_radius=3)

            # Power
            power_text = self.font_small.render(str(card.power), True, COLOR_ACCENT_GOLD)
            surface.blit(power_text, (x + 5, y + 7))

            # Name (truncated)
            name_text = self.font_small.render(card.name[:8], True, COLOR_TEXT_PRIMARY)
            surface.blit(name_text, (x + 25, y + 7))

    def _draw_wrapped_text(self, surface: pygame.Surface, text: str, pos: Tuple[int, int],
                          max_width: int, font: pygame.font.Font, color: Tuple[int, int, int]):
        """Draw text with word wrapping."""
        words = text.split(' ')
        lines = []
        current_line = []

        for word in words:
            test_line = ' '.join(current_line + [word])
            if font.size(test_line)[0] <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]

        if current_line:
            lines.append(' '.join(current_line))

        y = pos[1]
        for line in lines[:5]:  # Max 5 lines
            line_surf = font.render(line, True, color)
            surface.blit(line_surf, (pos[0], y))
            y += font.get_height() + 2

    def _get_faction_color(self, faction: str) -> Tuple[int, int, int]:
        """Get color for a faction."""
        faction_colors = {
            "Tau'ri": (100, 150, 255),
            "Goa'uld": (200, 150, 50),
            "Jaffa Rebellion": (150, 100, 200),
            "Lucian Alliance": (200, 50, 50),
            "Asgard": (50, 200, 200),
            "Neutral": (150, 150, 150)
        }
        return faction_colors.get(faction, COLOR_TEXT_SECONDARY)

    def handle_mouse_motion(self, pos: Tuple[int, int], clickable_rects: List[pygame.Rect]):
        """
        Update hover state based on mouse position.

        Args:
            pos: Mouse (x, y) position
            clickable_rects: List of clickable rectangles
        """
        self.hovered_index = None
        for i, rect in enumerate(clickable_rects):
            if rect.collidepoint(pos):
                self.hovered_index = i
                break

    def handle_click(self, pos: Tuple[int, int], clickable_rects: List[pygame.Rect]) -> Optional[int]:
        """
        Handle mouse click on clickable elements.

        Args:
            pos: Mouse (x, y) position
            clickable_rects: List of clickable rectangles

        Returns:
            Index of clicked element, or None
        """
        for i, rect in enumerate(clickable_rects):
            if rect.collidepoint(pos):
                self.selected_index = i
                return i
        return None
