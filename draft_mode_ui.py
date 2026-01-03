"""
STARGWENT - DRAFT MODE UI

Handles all rendering and interaction for Draft Mode (Arena).
"""

import pygame
import math
import os
from typing import List, Dict, Optional, Tuple
from cards import Card, ALL_CARDS, FACTION_TAURI, FACTION_GOAULD, FACTION_JAFFA, FACTION_LUCIAN, FACTION_ASGARD, FACTION_NEUTRAL
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

# Faction Colors
FACTION_COLORS = {
    FACTION_TAURI: (100, 150, 255),    # Blue
    FACTION_GOAULD: (200, 160, 50),    # Gold
    FACTION_JAFFA: (200, 100, 50),     # Orange/Rust
    FACTION_LUCIAN: (200, 100, 255),   # Pink/Purple
    FACTION_ASGARD: (100, 255, 255),   # Cyan
    FACTION_NEUTRAL: (150, 150, 150)   # Gray
}


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
        self.review_scroll_y = 0  # For scrolling in review phase
        self.draft_scroll_y = 0   # For scrolling in draft sidebar

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

    def draw_back_button(self, surface: pygame.Surface) -> pygame.Rect:
        """
        Draw a back button in the top left corner.
        
        Args:
            surface: Pygame surface to draw on
            
        Returns:
            Button rect
        """
        btn_width = int(120 * self.scale)
        btn_height = int(40 * self.scale)
        btn_rect = pygame.Rect(20, 20, btn_width, btn_height)
        
        # Hover effect handled by caller checking rect later, but we can check mouse here for visual
        mouse_pos = pygame.mouse.get_pos()
        is_hovered = btn_rect.collidepoint(mouse_pos)
        
        color = (60, 80, 100) if is_hovered else (40, 50, 70)
        border_color = COLOR_ACCENT_BLUE if is_hovered else COLOR_TEXT_SECONDARY
        
        pygame.draw.rect(surface, color, btn_rect, border_radius=8)
        pygame.draw.rect(surface, border_color, btn_rect, width=2, border_radius=8)
        
        text = self.font_small.render("BACK", True, COLOR_TEXT_PRIMARY)
        text_rect = text.get_rect(center=btn_rect.center)
        surface.blit(text, text_rect)
        
        return btn_rect

    def draw_startup_menu(self, surface: pygame.Surface) -> Tuple[pygame.Rect, pygame.Rect]:
        """
        Draw the startup menu (New vs Continue).
        
        Returns:
            Tuple of (continue_rect, new_draft_rect)
        """
        if self.draft_bg:
            surface.blit(self.draft_bg, (0, 0))
        else:
            surface.fill(COLOR_DARK_BG)
            
        # Title
        title = self.font_title.render("DRAFT MODE", True, COLOR_ACCENT_GOLD)
        title_rect = title.get_rect(center=(self.screen_width // 2, self.screen_height // 3))
        surface.blit(title, title_rect)
        
        btn_width = int(300 * self.scale)
        btn_height = int(80 * self.scale)
        spacing = int(40 * self.scale)
        
        center_x = self.screen_width // 2
        start_y = self.screen_height // 2
        
        # Continue Button
        continue_rect = pygame.Rect(0, 0, btn_width, btn_height)
        continue_rect.center = (center_x, start_y)
        
        # New Draft Button
        new_rect = pygame.Rect(0, 0, btn_width, btn_height)
        new_rect.center = (center_x, start_y + btn_height + spacing)
        
        mouse_pos = pygame.mouse.get_pos()
        
        # Draw Continue
        is_hovered = continue_rect.collidepoint(mouse_pos)
        color = (60, 100, 60) if is_hovered else (40, 80, 40)
        pygame.draw.rect(surface, color, continue_rect, border_radius=15)
        pygame.draw.rect(surface, (100, 200, 100), continue_rect, width=3, border_radius=15)
        
        cont_text = self.font_header.render("CONTINUE DRAFT", True, COLOR_TEXT_PRIMARY)
        cont_text_rect = cont_text.get_rect(center=continue_rect.center)
        surface.blit(cont_text, cont_text_rect)
        
        # Draw New
        is_hovered = new_rect.collidepoint(mouse_pos)
        color = (100, 60, 60) if is_hovered else (80, 40, 40)
        pygame.draw.rect(surface, color, new_rect, border_radius=15)
        pygame.draw.rect(surface, (200, 100, 100), new_rect, width=3, border_radius=15)
        
        new_text = self.font_header.render("NEW DRAFT", True, COLOR_TEXT_PRIMARY)
        new_text_rect = new_text.get_rect(center=new_rect.center)
        surface.blit(new_text, new_text_rect)
        
        return continue_rect, new_rect

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

                # Draw leader name and ability at bottom with semi-transparent background
                name_bg_height = 110
                name_bg = pygame.Surface((self.card_width, name_bg_height), pygame.SRCALPHA)
                name_bg.fill((0, 0, 0, 200))  # Slightly darker for readability
                surface.blit(name_bg, (x, y + self.card_height - name_bg_height))

                faction_color = self._get_faction_color(leader.get('faction'))
                name = self.font_body.render(leader['name'], True, faction_color)
                name_rect = name.get_rect(center=(x + self.card_width // 2, y + self.card_height - 90))
                surface.blit(name, name_rect)
                
                # Draw ability description
                ability = leader.get('ability_desc') or leader.get('ability', '')
                self._draw_wrapped_text(surface, ability, 
                                      (x + 10, y + self.card_height - 65), 
                                      self.card_width - 20, 
                                      self.font_small, (200, 200, 200))
            else:
                # Fallback: draw colored rectangle with text (old behavior)
                pygame.draw.rect(surface, color, rect, border_radius=10)
                pygame.draw.rect(surface, COLOR_ACCENT_BLUE, rect, width=3, border_radius=10)

                # Leader name
                faction_color = self._get_faction_color(leader.get('faction'))
                name = self.font_header.render(leader['name'], True, faction_color)
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
                        current_pick: int, total_picks: int, drafted_cards: List[Card],
                        synergy_scores: List[Dict] = None, can_undo: bool = False) -> List[pygame.Rect]:
        """
        Draw card drafting screen.

        Args:
            surface: Pygame surface to draw on
            choices: List of 3 card choices
            current_pick: Current pick number (0-indexed)
            total_picks: Total number of picks needed
            drafted_cards: Cards already drafted
            synergy_scores: Optional list of synergy score dicts for each choice
            can_undo: Whether undo is available

        Returns:
            List of clickable rects for each choice
        """
        # Use background image if available, otherwise fill with color
        if self.draft_bg:
            surface.blit(self.draft_bg, (0, 0))
        else:
            surface.fill(COLOR_DARK_BG)

        # Progress bar (moved to bottom)
        bar_width = int(600 * self.scale)
        bar_height = int(20 * self.scale)
        bar_x = (self.screen_width - bar_width) // 2
        bar_y = self.screen_height - int(100 * self.scale)

        # Background
        pygame.draw.rect(surface, COLOR_PANEL_BG, (bar_x, bar_y, bar_width, bar_height), border_radius=10)
        # Fill
        fill_width = int(bar_width * (current_pick / total_picks))
        if fill_width > 0:
            pygame.draw.rect(surface, COLOR_ACCENT_BLUE, (bar_x, bar_y, fill_width, bar_height), border_radius=10)

        # Progress header text (above bar)
        progress_text = f"PICK {current_pick + 1} of {total_picks}"
        progress = self.font_header.render(progress_text, True, COLOR_ACCENT_GOLD)
        progress_rect = progress.get_rect(center=(self.screen_width // 2, bar_y - 30))
        surface.blit(progress, progress_rect)

        # Undo hint
        if can_undo:
            undo_text = self.font_small.render("Press Z to undo last pick", True, COLOR_TEXT_SECONDARY)
            surface.blit(undo_text, (bar_x, bar_y + bar_height + 5))

        # Draw card choices
        choice_rects = []
        start_x = (self.screen_width - (self.card_width * 3 + self.card_spacing * 2)) // 2
        start_y = int(100 * self.scale)

        for i, card in enumerate(choices):
            x = start_x + i * (self.card_width + self.card_spacing)
            y = start_y

            rect = pygame.Rect(x, y, self.card_width, int(self.card_height * 1.2))
            
            # Get synergy info
            synergy = synergy_scores[i] if synergy_scores and i < len(synergy_scores) else None
            synergy_score = synergy['score'] if synergy else 0

            # Display actual card image from assets
            if card.image:
                # Scale card image to fit
                card_image = pygame.transform.smoothscale(card.image, (self.card_width, int(self.card_height * 1.2)))
                surface.blit(card_image, (x, y))

                # Add border based on state - highlight synergy cards
                if i == self.selected_index:
                    border_color = COLOR_ACCENT_GOLD
                    border_width = 5
                elif synergy_score >= 3:
                    border_color = (100, 255, 100)  # Green for good synergy
                    border_width = 4
                elif i == self.hovered_index:
                    border_color = self._get_faction_color(card.faction)
                    border_width = 3
                else:
                    border_color = COLOR_TEXT_SECONDARY
                    border_width = 2
                pygame.draw.rect(surface, border_color, rect, width=border_width, border_radius=10)

                # Add semi-transparent info overlay at bottom
                info_height = 95
                info_bg = pygame.Surface((self.card_width, info_height), pygame.SRCALPHA)
                info_bg.fill((0, 0, 0, 220))
                surface.blit(info_bg, (x, y + int(self.card_height * 1.2) - info_height))

                # Card name
                name = self.font_small.render(card.name[:18], True, COLOR_TEXT_PRIMARY)
                name_rect = name.get_rect(center=(x + self.card_width // 2, y + int(self.card_height * 1.2) - info_height + 15))
                surface.blit(name, name_rect)

                # Power and row (no emoji)
                info_text = f"[{card.power}] {card.row.upper()}"
                info = self.font_small.render(info_text, True, COLOR_ACCENT_GOLD)
                info_rect = info.get_rect(center=(x + self.card_width // 2, y + int(self.card_height * 1.2) - info_height + 38))
                surface.blit(info, info_rect)
                
                # Synergy indicator
                if synergy and synergy_score != 0:
                    if synergy_score > 0:
                        syn_color = (100, 255, 100)
                        syn_text = f"+{synergy_score} Synergy"
                    else:
                        syn_color = (255, 100, 100)
                        syn_text = f"{synergy_score} Synergy"
                    
                    syn_surf = self.font_small.render(syn_text, True, syn_color)
                    syn_rect = syn_surf.get_rect(center=(x + self.card_width // 2, y + int(self.card_height * 1.2) - info_height + 62))
                    surface.blit(syn_surf, syn_rect)
                    
                    # Show reason on hover
                    if i == self.hovered_index and synergy.get('reasons'):
                        reason = synergy['reasons'][0][:28]
                        reason_surf = self.font_small.render(reason, True, (180, 180, 200))
                        reason_rect = reason_surf.get_rect(center=(x + self.card_width // 2, y + int(self.card_height * 1.2) - 12))
                        surface.blit(reason_surf, reason_rect)

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
        leader_card_width = int(180 * self.scale)
        leader_card_height = int(270 * self.scale)

        # Draw a backdrop for the whole left panel
        left_panel_rect = pygame.Rect(30, 100, 400, self.screen_height - 250)
        left_panel_bg = pygame.Surface((left_panel_rect.width, left_panel_rect.height), pygame.SRCALPHA)
        left_panel_bg.fill((0, 0, 0, 160)) # Semi-transparent black
        surface.blit(left_panel_bg, left_panel_rect.topleft)
        pygame.draw.rect(surface, COLOR_ACCENT_BLUE, left_panel_rect, width=2, border_radius=10)

        # Try to load leader image (_leader.png variant)
        leader_card_id = drafted_leader.get('card_id')
        leader_image = None

        if leader_card_id:
            leader_image_path = os.path.join("assets", f"{leader_card_id}_leader.png")
            if os.path.exists(leader_image_path):
                try:
                    leader_image = pygame.image.load(leader_image_path).convert_alpha()
                    leader_image = pygame.transform.smoothscale(leader_image, (leader_card_width, leader_card_height))
                except Exception:
                    leader_image = None

            if leader_image is None and leader_card_id in ALL_CARDS:
                leader_card = ALL_CARDS[leader_card_id]
                leader_image = pygame.transform.smoothscale(leader_card.image, (leader_card_width, leader_card_height))

        if leader_image:
            image_x = left_panel_rect.centerx - leader_card_width // 2
            surface.blit(leader_image, (image_x, leader_y))
            leader_rect_border = pygame.Rect(image_x, leader_y, leader_card_width, leader_card_height)
            pygame.draw.rect(surface, COLOR_ACCENT_GOLD, leader_rect_border, width=3, border_radius=8)

            leader_name = self.font_body.render(drafted_leader['name'], True, COLOR_ACCENT_GOLD)
            leader_name_rect = leader_name.get_rect(center=(left_panel_rect.centerx, leader_y + leader_card_height + 30))
            surface.blit(leader_name, leader_name_rect)
        else:
            leader_name = self.font_header.render(f"Leader: {drafted_leader['name']}", True, COLOR_ACCENT_GOLD)
            leader_name_rect = leader_name.get_rect(center=(left_panel_rect.centerx, leader_y + 40))
            surface.blit(leader_name, leader_name_rect)

        # Stats section
        stats_x = left_panel_rect.x + 30
        stats_y = leader_y + leader_card_height + 80 if leader_image else leader_y + 100
        
        stats_header = self.font_body.render("DECK STATISTICS", True, COLOR_ACCENT_BLUE)
        surface.blit(stats_header, (stats_x, stats_y))
        
        stats_texts = [
            f"Total Cards: {stats['total_cards']}",
            f"Total Power: {stats['total_power']}",
            f"Average Power: {stats['avg_power']:.1f}",
            f"Abilities: {stats['ability_count']}"
        ]

        for i, text in enumerate(stats_texts):
            stat_surf = self.font_body.render(text, True, COLOR_TEXT_PRIMARY)
            surface.blit(stat_surf, (stats_x + 10, stats_y + 40 + i * 35))

        # Faction breakdown (bottom left of left panel)
        faction_y = stats_y + 40 + len(stats_texts) * 35 + 30
        faction_title = self.font_body.render("FACTIONS", True, COLOR_ACCENT_BLUE)
        surface.blit(faction_title, (stats_x, faction_y))

        for i, (faction, count) in enumerate(stats['faction_breakdown'].items()):
            color = self._get_faction_color(faction)
            text = self.font_small.render(f"• {faction}: {count}", True, color)
            surface.blit(text, (stats_x + 10, faction_y + 35 + i * 25))

        # Buttons - Better Alignment
        button_width = int(400 * self.scale)
        button_height = int(80 * self.scale)
        
        # Start Battle button (large, centered)
        battle_rect = pygame.Rect(0, 0, button_width, button_height)
        battle_rect.center = (self.screen_width // 2, self.screen_height - 120)
        
        # Hover effect for button
        battle_color = (60, 100, 200) if self.hovered_index == 0 else COLOR_ACCENT_BLUE
        pygame.draw.rect(surface, battle_color, battle_rect, border_radius=15)
        pygame.draw.rect(surface, COLOR_TEXT_PRIMARY, battle_rect, width=3, border_radius=15)
        
        battle_text = self.font_header.render("START BATTLE", True, COLOR_TEXT_PRIMARY)
        battle_text_rect = battle_text.get_rect(center=battle_rect.center)
        surface.blit(battle_text, battle_text_rect)

        # Redraft button (smaller, below or to the side)
        redraft_rect = pygame.Rect(0, 0, int(200 * self.scale), int(50 * self.scale))
        redraft_rect.center = (self.screen_width // 2, self.screen_height - 40)
        
        redraft_color = (80, 40, 40) if self.hovered_index == 1 else COLOR_PANEL_BG
        pygame.draw.rect(surface, redraft_color, redraft_rect, border_radius=10)
        pygame.draw.rect(surface, (200, 100, 100), redraft_rect, width=2, border_radius=10)
        
        redraft_text = self.font_body.render("Redraft", True, (200, 150, 150))
        redraft_text_rect = redraft_text.get_rect(center=redraft_rect.center)
        surface.blit(redraft_text, redraft_text_rect)

        # Card List (Right side, grouped and scrollable)
        self._draw_deck_list_scrollable(surface, drafted_cards)

        return battle_rect, redraft_rect

    def _draw_deck_preview(self, surface: pygame.Surface, cards: List[Card]):
        """Draw compact deck preview on the right side."""
        preview_x = self.screen_width - 250
        preview_y = 160
        preview_width = 230
        # Extend to bottom of screen with some padding
        preview_height = self.screen_height - preview_y - 20

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

        # Aggregate cards
        card_counts = {}
        for card in cards:
            if card.name in card_counts:
                card_counts[card.name]['count'] += 1
            else:
                card_counts[card.name] = {
                    'count': 1,
                    'card': card
                }
        
        # Sort by power desc
        sorted_cards = sorted(card_counts.values(), key=lambda x: x['card'].power, reverse=True)

        # List cards with clip
        list_y = preview_y + 90
        
        # Clip area for list (leaves space at bottom of panel)
        # Content height is calculated for clamping elsewhere
        clip_rect = pygame.Rect(preview_x + 5, list_y, preview_width - 10, preview_height - 100)
        original_clip = surface.get_clip()
        surface.set_clip(clip_rect)
        
        y_offset = 0
        line_height = 25
        
        for item in sorted_cards:
            card = item['card']
            count = item['count']
            
            # Apply scroll offset
            current_y = list_y + y_offset + self.draft_scroll_y
            
            # Optimization: Skip if off-screen
            if current_y + line_height < list_y or current_y > list_y + clip_rect.height:
                y_offset += line_height
                continue

            # Row indicator color
            row_code = card.row[0].upper() if card.row else "?"
            row_color = {
                'close': (200, 50, 50),   # Red
                'ranged': (50, 200, 50),  # Green
                'siege': (200, 200, 200), # Gray/White
                'agile': (200, 200, 50),  # Yellow
            }.get(card.row, COLOR_TEXT_SECONDARY)
            
            # Draw row indicator
            row_surf = self.font_small.render(f"[{row_code}]", True, row_color)
            surface.blit(row_surf, (preview_x + 10, current_y))
            
            # Draw name and count
            name_str = f"{card.power} {card.name[:13]}"
            if count > 1:
                name_str += f" x{count}"
                
            text_surf = self.font_small.render(name_str, True, COLOR_TEXT_PRIMARY)
            surface.blit(text_surf, (preview_x + 40, current_y))
            
            y_offset += line_height
            
        surface.set_clip(original_clip)
        
        # Draw scroll hint if content overflows
        content_height = len(sorted_cards) * line_height
        if content_height > clip_rect.height:
             hint = self.font_small.render("▼", True, COLOR_TEXT_SECONDARY)
             surface.blit(hint, (preview_x + preview_width // 2, preview_y + preview_height - 15))

    def _draw_deck_list_scrollable(self, surface: pygame.Surface, cards: List[Card]):
        """Draw full deck as a grouped list with scrolling support."""
        list_rect = pygame.Rect(self.screen_width - 500, 100, 450, self.screen_height - 250)
        
        # Backdrop
        list_bg = pygame.Surface((list_rect.width, list_rect.height), pygame.SRCALPHA)
        list_bg.fill((0, 0, 0, 160))
        surface.blit(list_bg, list_rect.topleft)
        pygame.draw.rect(surface, COLOR_ACCENT_BLUE, list_rect, width=2, border_radius=10)
        
        # Title
        title = self.font_body.render("DECK COMPOSITION", True, COLOR_ACCENT_GOLD)
        surface.blit(title, (list_rect.x + 20, list_rect.y + 20))
        
        # Group cards
        card_counts = {}
        for card in cards:
            if card.name in card_counts:
                card_counts[card.name]['count'] += 1
            else:
                card_counts[card.name] = {'count': 1, 'card': card}
        
        # Sort by power desc, then name
        sorted_items = sorted(card_counts.values(), key=lambda x: (x['card'].power, x['card'].name), reverse=True)
        
        # Clipping area for the list
        content_rect = pygame.Rect(list_rect.x + 10, list_rect.y + 60, list_rect.width - 20, list_rect.height - 80)
        old_clip = surface.get_clip()
        surface.set_clip(content_rect)
        
        line_height = 40
        for i, item in enumerate(sorted_items):
            card = item['card']
            count = item['count']
            
            y_pos = content_rect.y + i * line_height + self.review_scroll_y
            
            # Skip if out of view
            if y_pos + line_height < content_rect.y or y_pos > content_rect.bottom:
                continue
                
            # Row icon/code
            row_code = card.row[0].upper() if card.row else "?"
            row_color = {
                'close': (200, 80, 80),
                'ranged': (80, 200, 80),
                'siege': (180, 180, 180),
                'agile': (200, 200, 80),
            }.get(card.row, COLOR_TEXT_SECONDARY)
            
            row_surf = self.font_body.render(f"[{row_code}]", True, row_color)
            surface.blit(row_surf, (content_rect.x + 10, y_pos))
            
            # Name and power
            name_text = f"{card.power} - {card.name}"
            name_surf = self.font_body.render(name_text, True, COLOR_TEXT_PRIMARY)
            surface.blit(name_surf, (content_rect.x + 70, y_pos))
            
            # Count (if > 1)
            if count > 1:
                count_surf = self.font_body.render(f"x{count}", True, COLOR_ACCENT_GOLD)
                surface.blit(count_surf, (content_rect.right - 60, y_pos))
        
        surface.set_clip(old_clip)
        
        # Scroll instructions if many cards
        if len(sorted_items) * line_height > content_rect.height:
            hint = self.font_small.render("Use mouse wheel to scroll", True, COLOR_TEXT_SECONDARY)
            surface.blit(hint, (list_rect.right - 180, list_rect.bottom + 10))

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
        return FACTION_COLORS.get(faction, COLOR_TEXT_SECONDARY)

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