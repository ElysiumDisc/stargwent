"""
Deck Builder Menu System for Stargwent
Allows players to select a faction and build their deck before starting a game.
"""
import os
import pygame
import random
from cards import (
    ALL_CARDS, FACTION_TAURI, FACTION_GOAULD, FACTION_JAFFA,
    FACTION_LUCIAN, FACTION_ASGARD, FACTION_NEUTRAL, reload_card_images
)
from unlocks import CardUnlockSystem, UNLOCKABLE_CARDS
from game_settings import get_settings

# Faction theme music paths for hover preview
FACTION_THEME_MUSIC = {
    FACTION_TAURI: os.path.join("assets", "audio", "tauri_theme.ogg"),
    FACTION_GOAULD: os.path.join("assets", "audio", "goauld_theme.ogg"),
    FACTION_JAFFA: os.path.join("assets", "audio", "jaffa_theme.ogg"),
    FACTION_LUCIAN: os.path.join("assets", "audio", "lucian_theme.ogg"),
    FACTION_ASGARD: os.path.join("assets", "audio", "asgard_theme.ogg"),
}

# Track currently playing faction theme
_current_faction_theme = None
_faction_theme_start_time = 0
_FACTION_THEME_DURATION_MS = 10000  # Restart theme every 10 seconds


def _get_faction_theme_volume() -> float:
    """Get preview volume scaled by current settings."""
    settings = get_settings()
    try:
        volume = settings.get_effective_music_volume()
    except AttributeError:
        volume = settings.get_master_volume()
    return max(0.0, min(1.0, volume))


def _play_faction_theme(faction):
    """Play faction theme music when hovering over faction button."""
    global _current_faction_theme, _faction_theme_start_time

    if faction == _current_faction_theme:
        # Check if we need to restart (10 second loop)
        if faction and pygame.time.get_ticks() - _faction_theme_start_time >= _FACTION_THEME_DURATION_MS:
            _faction_theme_start_time = pygame.time.get_ticks()
            try:
                pygame.mixer.music.set_volume(_get_faction_theme_volume())
                pygame.mixer.music.play(0)  # Play once, will restart on next check
            except pygame.error:
                pass
        return

    _current_faction_theme = faction
    _faction_theme_start_time = pygame.time.get_ticks()

    if not faction:
        pygame.mixer.music.stop()
        return

    theme_path = FACTION_THEME_MUSIC.get(faction)
    if theme_path and os.path.exists(theme_path):
        try:
            pygame.mixer.music.load(theme_path)
            pygame.mixer.music.set_volume(_get_faction_theme_volume())
            pygame.mixer.music.play(0)  # Play once (will restart every 10s)
        except pygame.error as e:
            print(f"[audio] Failed to play faction theme: {e}")

def stop_faction_theme():
    """Stop faction theme music."""
    global _current_faction_theme
    _current_faction_theme = None
    try:
        pygame.mixer.music.stop()
    except pygame.error:
        pass
from content_registry import (
    BASE_FACTION_LEADERS,
    UNLOCKABLE_LEADERS,
    LEADER_COLOR_OVERRIDES,
)
from deck_persistence import save_player_deck, load_player_deck, save_leader_choice, load_leader_choice, get_persistence

# Available factions
AVAILABLE_FACTIONS = [
    FACTION_TAURI,
    FACTION_GOAULD,
    FACTION_JAFFA,
    FACTION_LUCIAN,
    FACTION_ASGARD
]

# Leader cards for each faction (alternate leaders)
FACTION_LEADERS = BASE_FACTION_LEADERS

FACTION_BACKGROUND_ASSET_IDS = {
    FACTION_TAURI: "tauri",
    FACTION_GOAULD: "goauld",
    FACTION_JAFFA: "jaffa",
    FACTION_LUCIAN: "lucian",
    FACTION_ASGARD: "asgard",
}


class DeckBuilderUI:
    """Deck builder interface for selecting faction and leader."""
    
    def __init__(self, screen_width, screen_height, for_new_game=True, *, unlock_override=False, unlock_system=None):
        reload_card_images()
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.for_new_game = for_new_game  # Track if this is for new game or deck customization
        self.unlock_override = unlock_override
        self.unlock_system = unlock_system or CardUnlockSystem()
        self.selected_faction = None
        self.selected_leader = None
        self.state = "faction_select"  # faction_select, leader_select, deck_review, complete
        self.deck_preview_ids = None
        self.custom_deck_ids = []  # Player's custom deck being built
        self.deck_scroll_offset = 0
        self.pool_scroll_offset = 0  # Separate scroll for card pool
        self.inspected_card_id = None  # Card being inspected with spacebar
        self.card_pool_ids = []  # Available cards for the faction
        self.current_tab = "all"  # Current card type tab: close, ranged, siege, agile, special, weather, neutral, all
        self.tab_rects = {}
        self.return_to_menu = False  # Flag for when user clicks MAIN MENU button
        self.leader_scroll_offset = 0
        self.leader_scroll_limit = 0
        self.leader_area_rect = None
        self.last_save_message = ""
        self.last_save_time = 0

        # DRAG AND DROP STATE
        self.dragging_card = None  # Card ID being dragged
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.drag_from_pool = False  # True if dragging from pool, False if from deck

        # HOVER PREVIEW STATE
        self.hovered_card_id = None  # Card ID being hovered over for preview
        
        # Fonts
        self.title_font = pygame.font.SysFont("Arial", 64, bold=True)
        self.subtitle_font = pygame.font.SysFont("Arial", 36, bold=True)
        self.desc_font = pygame.font.SysFont("Arial", 24)
        self.button_font = pygame.font.SysFont("Arial", 28, bold=True)
        self.small_font = pygame.font.SysFont("Arial", 18)
        
        # Colors
        self.bg_color = (15, 15, 25)
        self.current_bg_color = (15, 15, 25)  # Track current background for smooth transitions
        self.button_color = (40, 60, 100)
        self.button_hover_color = (60, 90, 150)
        self.button_selected_color = (100, 150, 200)
        self.text_color = (255, 255, 255)
        self.highlight_color = (255, 215, 0)
        
        # Faction colors for visual distinction
        self.faction_colors = {
            FACTION_TAURI: (100, 150, 255),     # Blue
            FACTION_GOAULD: (200, 50, 50),      # Red
            FACTION_JAFFA: (150, 100, 50),      # Brown/Gold
            FACTION_LUCIAN: (150, 50, 150),     # Purple
            FACTION_ASGARD: (50, 200, 150),     # Cyan
        }
        
        # Background colors for factions (darker versions)
        self.faction_bg_colors = {
            FACTION_TAURI: (15, 25, 45),        # Dark Blue
            FACTION_GOAULD: (35, 15, 15),       # Dark Red
            FACTION_JAFFA: (30, 20, 10),        # Dark Brown/Gold
            FACTION_LUCIAN: (30, 15, 30),       # Dark Purple
            FACTION_ASGARD: (10, 30, 25),       # Dark Cyan
        }
        
        # Leader-specific background colors (slightly different shades) - FALLBACK if images not found
        self.leader_bg_colors = dict(LEADER_COLOR_OVERRIDES)
        
        # Background image cache (load leader backgrounds)
        self.faction_bg_images = {}
        self.leader_bg_images = {}  # Cache for loaded leader background images
        self.current_bg_image = None  # Currently displayed background image
        self.deck_building_bg = None  # Background for deck building view
        self.load_faction_backgrounds()
        self.load_leader_backgrounds()
        self.load_deck_building_bg()
        self.tab_rects = {}
        
        # Layout
        self.setup_layout()

    def get_leader_pool(self, faction):
        """Return base leaders plus any unlocked/override leaders for the faction."""
        leaders = list(FACTION_LEADERS.get(faction, []))
        if faction in UNLOCKABLE_LEADERS:
            persistence = get_persistence()
            for unlockable_leader in UNLOCKABLE_LEADERS[faction]:
                if self.unlock_override or persistence.is_leader_unlocked(unlockable_leader['card_id']):
                    leaders.append(unlockable_leader)
        return leaders

    def _leader_button_display_rect(self, base_rect):
        rect = base_rect.copy()
        rect.y -= self.leader_scroll_offset
        return rect

    def _ensure_leader_visible(self, index):
        if not self.leader_area_rect or index < 0 or index >= len(self.leader_buttons):
            return
        base_rect = self.leader_buttons[index]['rect']
        display_rect = self._leader_button_display_rect(base_rect)
        area_top = self.leader_area_rect.top
        area_bottom = self.leader_area_rect.bottom
        if display_rect.top < area_top:
            delta = area_top - display_rect.top
            self.leader_scroll_offset = max(0, self.leader_scroll_offset - delta)
        elif display_rect.bottom > area_bottom:
            delta = display_rect.bottom - area_bottom
            self.leader_scroll_offset = min(self.leader_scroll_limit, self.leader_scroll_offset + delta)
    
    def get_card_layout_params(self, panel_width):
        """Calculate card layout parameters to match drawing code."""
        cards_per_row = 3  # 3 cards per row
        spacing = 15
        available_width = panel_width - (spacing * (cards_per_row + 1))
        card_width = min(available_width // cards_per_row, 150)  # Cap at 150px width
        card_height = int(card_width * 1.5)  # Maintain aspect ratio
        return cards_per_row, spacing, card_width, card_height
        
    def setup_layout(self):
        """Calculate layout positions."""
        # Faction selection buttons - STACK VERTICALLY to avoid overlap
        self.faction_buttons = []
        button_width = 400
        button_height = 100
        spacing = 20
        start_x = (self.screen_width - button_width) // 2  # Center horizontally
        start_y = 200  # Start below title
        
        for i, faction in enumerate(AVAILABLE_FACTIONS):
            y = start_y + i * (button_height + spacing)
            rect = pygame.Rect(start_x, y, button_width, button_height)
            self.faction_buttons.append({
                'rect': rect,
                'faction': faction,
                'hovered': False
            })
        
        # Leader selection buttons
        self.leader_buttons = []
        
        # Continue button
        self.continue_button = pygame.Rect(
            self.screen_width // 2 - 150,
            self.screen_height - 100,
            300,
            60
        )
        
        # Review Deck button
        self.review_deck_button = pygame.Rect(
            self.screen_width - 250,
            self.screen_height - 100,
            200,
            60
        )
        
        # Back button
        self.back_button = pygame.Rect(
            50,
            self.screen_height - 80,
            150,
            50
        )
        
        # Save button (for deck building mode)
        self.save_button = pygame.Rect(
            self.screen_width // 2 - 100,
            self.screen_height - 100,
            200,
            50
        )

    def save_current_deck(self, reason=""):
        """Persist the current deck configuration and show feedback to the player."""
        if not self.selected_faction or not self.selected_leader or not self.deck_preview_ids:
            return False
        card_ids = list(self.deck_preview_ids)
        save_player_deck(self.selected_faction, self.selected_leader['card_id'], card_ids)
        save_leader_choice(self.selected_faction, self.selected_leader['card_id'])
        self.last_save_message = f"Saved deck for {self.selected_faction}: {len(card_ids)} cards"
        self.last_save_time = pygame.time.get_ticks()
        if reason:
            print(f"✓ {reason} | {self.last_save_message}")
        else:
            print(f"✓ Deck saved: {self.selected_faction} with {len(card_ids)} cards")
        return True

    def refresh_for_surface(self, screen):
        """Rebuild layout when the display surface size changes."""
        prev_state = self.state
        prev_faction = self.selected_faction
        prev_leader_id = self.selected_leader.get('card_id') if self.selected_leader else None
        prev_deck = list(self.deck_preview_ids) if self.deck_preview_ids else None
        prev_card_pool = list(self.card_pool_ids) if self.card_pool_ids else None
        prev_tab = self.current_tab
        prev_pool_scroll = self.pool_scroll_offset
        prev_deck_scroll = self.deck_scroll_offset
        prev_inspected = self.inspected_card_id

        self.screen_width = screen.get_width()
        self.screen_height = screen.get_height()

        self.setup_layout()
        self.load_faction_backgrounds()
        self.load_leader_backgrounds()
        self.load_deck_building_bg()

        self.selected_faction = prev_faction
        self.current_tab = prev_tab
        self.pool_scroll_offset = prev_pool_scroll
        self.deck_scroll_offset = prev_deck_scroll
        self.deck_preview_ids = prev_deck
        self.card_pool_ids = prev_card_pool if prev_card_pool else []

        if prev_faction:
            self.set_faction_background(prev_faction)
            self.setup_leader_buttons()
        else:
            self.set_faction_background(None)

        self.selected_leader = None
        if prev_leader_id and self.leader_buttons:
            for idx, button in enumerate(self.leader_buttons):
                leader = button['leader']
                if leader.get('card_id') == prev_leader_id:
                    self.selected_leader = leader
                    self._ensure_leader_visible(idx)
                    self.set_leader_background(prev_leader_id)
                    break

        if prev_state == "deck_review" and prev_inspected and self.deck_preview_ids:
            if prev_inspected in self.deck_preview_ids:
                self.inspected_card_id = prev_inspected
            else:
                self.inspected_card_id = None
    
    def load_faction_backgrounds(self):
        """Load faction selection backgrounds (scaled to window)."""
        self.faction_bg_images = {}
        assets_dir = "assets"
        for faction, asset_id in FACTION_BACKGROUND_ASSET_IDS.items():
            bg_path = os.path.join(assets_dir, f"faction_bg_{asset_id}.png")
            if not os.path.exists(bg_path):
                continue
            try:
                bg_image = pygame.image.load(bg_path).convert()
                scaled_bg = pygame.transform.scale(bg_image, (self.screen_width, self.screen_height))
                self.faction_bg_images[faction] = scaled_bg
            except Exception as e:
                print(f"Warning: Could not load {bg_path}: {e}")

    def load_leader_backgrounds(self):
        """Load all leader background images into cache."""
        import os
        assets_dir = "assets"
        
        # Try to load each leader background
        for leader_id in self.leader_bg_colors.keys():
            bg_filename = f"leader_bg_{leader_id}.png"
            bg_path = os.path.join(assets_dir, bg_filename)
            
            if os.path.exists(bg_path):
                try:
                    # Load and scale to screen size
                    bg_image = pygame.image.load(bg_path).convert()
                    scaled_bg = pygame.transform.scale(bg_image, (self.screen_width, self.screen_height))
                    self.leader_bg_images[leader_id] = scaled_bg
                except Exception as e:
                    print(f"Warning: Could not load {bg_path}: {e}")
            else:
                # Background image doesn't exist, will use solid color fallback
                pass
    
    def load_deck_building_bg(self):
        """Load deck building background image."""
        import os
        bg_path = os.path.join("assets", "deck_building_bg.png")

        if os.path.exists(bg_path):
            try:
                bg_image = pygame.image.load(bg_path).convert()
                self.deck_building_bg = pygame.transform.scale(bg_image, (self.screen_width, self.screen_height))
                print("✓ Loaded deck_building_bg.png")
            except Exception as e:
                print(f"Warning: Could not load {bg_path}: {e}")
                self.deck_building_bg = None
        else:
            self.deck_building_bg = None

    def set_leader_background(self, leader_id):
        """Swap the background to the supplied leader id or fallback to faction theme."""
        if leader_id and leader_id in self.leader_bg_images:
            self.current_bg_image = self.leader_bg_images[leader_id]
            self.current_bg_color = None
        elif leader_id:
            self.current_bg_image = None
            self.current_bg_color = self.leader_bg_colors.get(
                leader_id,
                self.faction_bg_colors.get(self.selected_faction, self.bg_color)
            )
        else:
            self.set_faction_background(self.selected_faction)

    def set_faction_background(self, faction):
        """Apply faction background image or fallback color."""
        if faction and faction in self.faction_bg_images:
            self.current_bg_image = self.faction_bg_images[faction]
            self.current_bg_color = None
        elif faction:
            self.current_bg_image = None
            self.current_bg_color = self.faction_bg_colors.get(faction, self.bg_color)
        else:
            self.current_bg_image = None
            self.current_bg_color = self.bg_color

    def setup_leader_buttons(self):
        """Setup leader selection buttons based on selected faction."""
        self.leader_buttons = []
        if not self.selected_faction:
            return
        self.leader_scroll_offset = 0
        
        # Build leader pool respecting unlocks/override
        all_leaders = self.get_leader_pool(self.selected_faction)
        
        button_width = min(420, self.screen_width - 160)
        spacing = max(12, int(self.screen_height * 0.015))
        start_y = int(self.screen_height * 0.22)
        area_height = max(200, self.screen_height - start_y - int(self.screen_height * 0.12))
        visible_slots = max(3, min(5, len(all_leaders) or 1))
        button_height = min(180, max(110, int((area_height - spacing * (visible_slots - 1)) / visible_slots)))
        area_height = max(button_height + 10, area_height)
        self.leader_area_rect = pygame.Rect(self.screen_width // 2 - button_width // 2, start_y, button_width, area_height)
        content_height = max(0, len(all_leaders) * (button_height + spacing) - spacing)
        self.leader_scroll_limit = max(0, content_height - self.leader_area_rect.height)
        self.leader_scroll_offset = max(0, min(self.leader_scroll_offset, self.leader_scroll_limit))
        
        cursor_y = start_y
        for leader in all_leaders:
            rect = pygame.Rect(self.leader_area_rect.x, cursor_y, button_width, button_height)
            self.leader_buttons.append({
                'rect': rect,
                'leader': leader,
                'hovered': False
            })
            cursor_y += button_height + spacing
    
    def handle_event(self, event):
        """Handle input events."""
        if event.type == pygame.MOUSEMOTION:
            mouse_pos = event.pos
            
            # If dragging, update drag position
            if self.dragging_card:
                self.drag_start_x = mouse_pos[0]
                self.drag_start_y = mouse_pos[1]
            
            # Update hover states for faction buttons and change background
            if self.state == "faction_select":
                hovered_faction = None
                for button in self.faction_buttons:
                    is_hovered = button['rect'].collidepoint(mouse_pos)
                    button['hovered'] = is_hovered
                    if is_hovered:
                        hovered_faction = button['faction']

                # Update background and music based on hover
                if hovered_faction:
                    self.set_faction_background(hovered_faction)
                    _play_faction_theme(hovered_faction)
                else:
                    self.set_faction_background(self.selected_faction)
                    _play_faction_theme(None)  # Stop music when not hovering
            
            # Update hover states for leader buttons and change background
            elif self.state == "leader_select":
                hovered_leader = None
                for button in self.leader_buttons:
                    display_rect = self._leader_button_display_rect(button['rect'])
                    is_hovered = display_rect.collidepoint(mouse_pos)
                    button['hovered'] = bool(is_hovered and (not self.leader_area_rect or self.leader_area_rect.collidepoint(mouse_pos)))
                    if button['hovered']:
                        hovered_leader = button['leader'].get('card_id')

                if hovered_leader:
                    self.set_leader_background(hovered_leader)
                else:
                    selected_id = self.selected_leader.get('card_id') if self.selected_leader else None
                    self.set_leader_background(selected_id)

            # Update hover preview for cards in deck review
            elif self.state == "deck_review":
                # Reset hovered card
                self.hovered_card_id = None

                # Don't show hover preview while dragging or inspecting
                if self.dragging_card or self.inspected_card_id:
                    return

                # Calculate panel dimensions (same as in draw_deck_review)
                panel_padding = 20
                divider_x = self.screen_width // 2
                left_panel_x = panel_padding
                left_panel_width = divider_x - panel_padding * 2
                left_panel_y = 120
                left_panel_height = self.screen_height - 180
                right_panel_x = divider_x + panel_padding
                right_panel_width = self.screen_width - right_panel_x - panel_padding
                right_panel_y = 120
                right_panel_height = self.screen_height - 180

                left_panel_rect = pygame.Rect(left_panel_x, left_panel_y, left_panel_width, left_panel_height)
                right_panel_rect = pygame.Rect(right_panel_x, right_panel_y, right_panel_width, right_panel_height)

                # Check hover in LEFT panel (card pool)
                if left_panel_rect.collidepoint(mouse_pos) and self.card_pool_ids:
                    sorted_pool = get_cards_by_type_and_strength(self.card_pool_ids, self.current_tab)
                    cards_per_row, spacing, card_width, card_height = self.get_card_layout_params(left_panel_width)
                    start_x = left_panel_x + spacing
                    start_y = left_panel_y + 15 - self.pool_scroll_offset

                    for i, card_id in enumerate(sorted_pool):
                        row_idx = i // cards_per_row
                        col_idx = i % cards_per_row
                        x = start_x + col_idx * (card_width + spacing)
                        y = start_y + row_idx * (card_height + spacing)

                        card_rect = pygame.Rect(x, y, card_width, card_height)
                        if card_rect.collidepoint(mouse_pos):
                            self.hovered_card_id = card_id
                            break

                # Check hover in RIGHT panel (deck)
                elif right_panel_rect.collidepoint(mouse_pos) and self.deck_preview_ids:
                    deck_filter_type = None if self.current_tab == "all" else self.current_tab
                    visible_deck_ids = get_cards_by_type_and_strength(self.deck_preview_ids, deck_filter_type)
                    cards_per_row, spacing, card_width, card_height = self.get_card_layout_params(right_panel_width)
                    start_x = right_panel_x + spacing
                    start_y = right_panel_y + 15 - self.deck_scroll_offset

                    for i, card_id in enumerate(visible_deck_ids):
                        row_idx = i // cards_per_row
                        col_idx = i % cards_per_row
                        x = start_x + col_idx * (card_width + spacing)
                        y = start_y + row_idx * (card_height + spacing)

                        card_rect = pygame.Rect(x, y, card_width, card_height)
                        if card_rect.collidepoint(mouse_pos):
                            self.hovered_card_id = card_id
                            break
        
        elif event.type == pygame.MOUSEBUTTONUP:
            # Complete drag and drop
            if self.dragging_card and event.button == 1:
                mouse_pos = event.pos
                divider_x = self.screen_width // 2
                
                # Dropped on LEFT side (pool) - remove from deck
                if mouse_pos[0] < divider_x and not self.drag_from_pool:
                    if self.dragging_card in self.deck_preview_ids:
                        self.deck_preview_ids.remove(self.dragging_card)
                
                # Dropped on RIGHT side (deck) - add to deck
                elif mouse_pos[0] >= divider_x and self.drag_from_pool:
                    if len(self.deck_preview_ids) < MAX_DECK_SIZE:
                        if self.dragging_card not in self.deck_preview_ids:
                            self.deck_preview_ids.append(self.dragging_card)
                
                # Reset drag state
                self.dragging_card = None
                self.drag_from_pool = False
        
        elif event.type == pygame.MOUSEWHEEL:
            # Modern pygame mouse wheel handling
            if self.state == "leader_select" and self.leader_scroll_limit > 0:
                if not self.leader_area_rect or self.leader_area_rect.collidepoint(pygame.mouse.get_pos()):
                    self.leader_scroll_offset = max(
                        0,
                        min(self.leader_scroll_limit, self.leader_scroll_offset - event.y * 40)
                    )
                    return
            if self.state == "deck_review":
                if self.inspected_card_id:
                    # Browse through cards with mouse wheel when zoomed
                    all_card_ids = self.deck_preview_ids if self.deck_preview_ids else []
                    if all_card_ids:
                        current_idx = all_card_ids.index(self.inspected_card_id)
                        if event.y > 0:  # Scroll up = previous card
                            new_idx = (current_idx - 1) % len(all_card_ids)
                            self.inspected_card_id = all_card_ids[new_idx]
                        elif event.y < 0:  # Scroll down = next card
                            new_idx = (current_idx + 1) % len(all_card_ids)
                            self.inspected_card_id = all_card_ids[new_idx]
                else:
                    # Determine which panel to scroll based on mouse position
                    mouse_pos = pygame.mouse.get_pos()
                    divider_x = self.screen_width // 2
                    
                    if mouse_pos[0] < divider_x:
                        # Left panel (card pool) scroll
                        self.pool_scroll_offset = max(0, self.pool_scroll_offset - event.y * 50)
                    else:
                        # Right panel (deck) scroll
                        self.deck_scroll_offset = max(0, self.deck_scroll_offset - event.y * 50)
            return  # Don't process mouse wheel as clicks
        
        elif event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = event.pos
            # Legacy mouse wheel support (for older pygame versions)
            if event.button in [4, 5]:  # Mouse wheel up/down
                if self.state == "leader_select" and self.leader_scroll_limit > 0:
                    if not self.leader_area_rect or self.leader_area_rect.collidepoint(mouse_pos):
                        delta = 40 if event.button == 4 else -40
                        self.leader_scroll_offset = max(
                            0,
                            min(self.leader_scroll_limit, self.leader_scroll_offset - delta)
                        )
                        return
                if self.state == "deck_review":
                    if self.inspected_card_id:
                        # Browse through cards with mouse wheel when zoomed
                        all_card_ids = self.deck_preview_ids if self.deck_preview_ids else []
                        if all_card_ids and self.inspected_card_id in all_card_ids:
                            current_idx = all_card_ids.index(self.inspected_card_id)
                            if event.button == 4:  # Scroll up = previous card
                                new_idx = (current_idx - 1) % len(all_card_ids)
                                self.inspected_card_id = all_card_ids[new_idx]
                            elif event.button == 5:  # Scroll down = next card
                                new_idx = (current_idx + 1) % len(all_card_ids)
                                self.inspected_card_id = all_card_ids[new_idx]
                    else:
                        divider_x = self.screen_width // 2
                        if mouse_pos[0] < divider_x:
                            if event.button == 4:
                                self.pool_scroll_offset = max(0, self.pool_scroll_offset - 50)
                            elif event.button == 5:
                                self.pool_scroll_offset += 50
                        else:
                            if event.button == 4:
                                self.deck_scroll_offset = max(0, self.deck_scroll_offset - 50)
                            elif event.button == 5:
                                self.deck_scroll_offset += 50
                return

            # For faction and leader select, only handle left clicks
            if self.state in ["faction_select", "leader_select"] and event.button != 1:
                return

            if self.state == "faction_select":
                for button in self.faction_buttons:
                    if button['rect'].collidepoint(mouse_pos):
                        self.selected_faction = button['faction']
                        self.current_bg_color = self.faction_bg_colors.get(self.selected_faction, self.bg_color)
                        # Keep faction theme playing during leader selection
                        _play_faction_theme(self.selected_faction)
                        if self.for_new_game:
                            self.state = "leader_select"
                            self.setup_leader_buttons()
                        else:
                            saved_leader_id = load_leader_choice(self.selected_faction)
                            available_leaders = self.get_leader_pool(self.selected_faction)
                            if saved_leader_id:
                                for leader in available_leaders:
                                    if leader['card_id'] == saved_leader_id:
                                        self.selected_leader = leader
                                        break
                            if not self.selected_leader and available_leaders:
                                self.selected_leader = available_leaders[0]
                            self.deck_preview_ids = build_faction_deck(self.selected_faction, self.selected_leader)
                            self.card_pool_ids = get_faction_card_pool(self.selected_faction, self.unlock_system, self.unlock_override)
                            self.current_tab = "all"
                            self.inspected_card_id = None
                            self.state = "deck_review"
                            self.deck_scroll_offset = 0
                            self.pool_scroll_offset = 0
                        return

            elif self.state == "leader_select":
                if self.back_button.collidepoint(mouse_pos):
                    self.state = "faction_select"
                    self.selected_leader = None
                    self.deck_preview_ids = None
                    # Music will continue based on hover in faction_select
                    return
                for idx, button in enumerate(self.leader_buttons):
                    display_rect = self._leader_button_display_rect(button['rect'])
                    if self.leader_area_rect and not self.leader_area_rect.collidepoint(mouse_pos):
                        continue
                    if display_rect.collidepoint(mouse_pos):
                        self.selected_leader = button['leader']
                        leader_id = self.selected_leader.get('card_id')
                        self.set_leader_background(leader_id)
                        self._ensure_leader_visible(idx)
                        self.deck_preview_ids = build_faction_deck(self.selected_faction, self.selected_leader)
                        return
                review_rect = self._leader_button_display_rect(self.review_deck_button)
                if self.selected_leader and review_rect.collidepoint(mouse_pos):
                    stop_faction_theme()  # Stop music when entering deck review
                    self.state = "deck_review"
                    if not self.deck_preview_ids:
                        self.deck_preview_ids = build_faction_deck(self.selected_faction, self.selected_leader)
                    self.card_pool_ids = get_faction_card_pool(self.selected_faction, self.unlock_system, self.unlock_override)
                    self.current_tab = "all"
                    self.inspected_card_id = None
                    self.deck_scroll_offset = 0
                    self.pool_scroll_offset = 0
                    return
                continue_rect = self._leader_button_display_rect(self.continue_button)
                if self.selected_leader and continue_rect.collidepoint(mouse_pos):
                    stop_faction_theme()  # Stop music when completing
                    save_leader_choice(self.selected_faction, self.selected_leader['card_id'])
                    print(f"✓ Leader choice saved: {self.selected_faction} -> {self.selected_leader['name']}")
                    self.state = "complete"
                    return

        elif event.type == pygame.KEYDOWN:
            # Handle spacebar for card inspection
            if event.key == pygame.K_SPACE and self.state == "deck_review":
                # Close inspection if already open
                if self.inspected_card_id:
                    self.inspected_card_id = None
            
            # Scroll in deck review with arrow keys OR WASD
            elif self.state == "deck_review":
                if self.inspected_card_id and self.deck_preview_ids:
                    # Navigate between cards with arrow keys when zoomed
                    current_idx = self.deck_preview_ids.index(self.inspected_card_id)
                    if event.key in [pygame.K_LEFT, pygame.K_a]:
                        new_idx = (current_idx - 1) % len(self.deck_preview_ids)
                        self.inspected_card_id = self.deck_preview_ids[new_idx]
                    elif event.key in [pygame.K_RIGHT, pygame.K_d]:
                        new_idx = (current_idx + 1) % len(self.deck_preview_ids)
                        self.inspected_card_id = self.deck_preview_ids[new_idx]
                    elif event.key in [pygame.K_UP, pygame.K_w]:
                        new_idx = (current_idx - 1) % len(self.deck_preview_ids)
                        self.inspected_card_id = self.deck_preview_ids[new_idx]
                    elif event.key in [pygame.K_DOWN, pygame.K_s]:
                        new_idx = (current_idx + 1) % len(self.deck_preview_ids)
                        self.inspected_card_id = self.deck_preview_ids[new_idx]
                else:
                    # Scroll the deck grid when not zoomed
                    if event.key in [pygame.K_UP, pygame.K_w]:
                        self.deck_scroll_offset = max(0, self.deck_scroll_offset - 50)
                    elif event.key in [pygame.K_DOWN, pygame.K_s]:
                        self.deck_scroll_offset += 50
            
            # Navigate between leaders with arrow keys
            elif self.state == "leader_select" and self.leader_buttons:
                if event.key in [pygame.K_UP, pygame.K_w]:
                    # Find current selection
                    current_idx = -1
                    if self.selected_leader:
                        for i, btn in enumerate(self.leader_buttons):
                            if btn['leader'] == self.selected_leader:
                                current_idx = i
                                break
                    # Move up
                    new_idx = max(0, current_idx - 1) if current_idx > 0 else len(self.leader_buttons) - 1
                    self.selected_leader = self.leader_buttons[new_idx]['leader']
                    self._ensure_leader_visible(new_idx)
                    if not self.deck_preview_ids:
                        self.deck_preview_ids = build_faction_deck(self.selected_faction, self.selected_leader)
                
                elif event.key in [pygame.K_DOWN, pygame.K_s]:
                    # Find current selection
                    current_idx = -1
                    if self.selected_leader:
                        for i, btn in enumerate(self.leader_buttons):
                            if btn['leader'] == self.selected_leader:
                                current_idx = i
                                break
                    # Move down
                    new_idx = (current_idx + 1) % len(self.leader_buttons)
                    self.selected_leader = self.leader_buttons[new_idx]['leader']
                    self._ensure_leader_visible(new_idx)
                    if not self.deck_preview_ids:
                        self.deck_preview_ids = build_faction_deck(self.selected_faction, self.selected_leader)
                
                elif event.key == pygame.K_RETURN and self.selected_leader:
                    # Enter to confirm and start
                    self.state = "complete"
            
            # Navigate between factions with arrow keys
            elif self.state == "faction_select":
                current_idx = -1
                if self.selected_faction:
                    for i, btn in enumerate(self.faction_buttons):
                        if btn['faction'] == self.selected_faction:
                            current_idx = i
                            break
                
                if event.key in [pygame.K_UP, pygame.K_w]:
                    new_idx = max(0, current_idx - 1) if current_idx > 0 else len(self.faction_buttons) - 1
                    self.selected_faction = self.faction_buttons[new_idx]['faction']
                
                elif event.key in [pygame.K_DOWN, pygame.K_s]:
                    new_idx = (current_idx + 1) % len(self.faction_buttons) if current_idx >= 0 else 0
                    self.selected_faction = self.faction_buttons[new_idx]['faction']
                
                elif event.key == pygame.K_RETURN and self.selected_faction:
                    # Enter to confirm faction
                    if self.for_new_game:
                        # NEW GAME: Go to leader selection
                        self.state = "leader_select"
                        self.setup_leader_buttons()
                    else:
                        # DECK BUILDING: Load saved leader and go directly to deck review
                        saved_leader_id = load_leader_choice(self.selected_faction)
                        available_leaders = self.get_leader_pool(self.selected_faction)
                        if saved_leader_id:
                            for leader in available_leaders:
                                if leader['card_id'] == saved_leader_id:
                                    self.selected_leader = leader
                                    break
                        if not self.selected_leader and available_leaders:
                            # Default to first leader if none saved
                            self.selected_leader = available_leaders[0]
                        
                        # Generate deck and go to review
                        self.deck_preview_ids = build_faction_deck(self.selected_faction, self.selected_leader)
                        self.card_pool_ids = get_faction_card_pool(self.selected_faction, self.unlock_system, self.unlock_override)
                        self.current_tab = "all"
                        self.inspected_card_id = None
                        self.state = "deck_review"
                        self.deck_scroll_offset = 0
                        self.pool_scroll_offset = 0
        
        elif event.type == pygame.KEYDOWN:
            # Handle spacebar for card inspection
            if event.key == pygame.K_SPACE and self.state == "deck_review":
                # Close inspection if already open
                if self.inspected_card_id:
                    self.inspected_card_id = None
            
            # Scroll in deck review with arrow keys OR WASD
            elif self.state == "deck_review":
                if self.inspected_card_id and self.deck_preview_ids:
                    # Navigate between cards with arrow keys when zoomed
                    current_idx = self.deck_preview_ids.index(self.inspected_card_id)
                    if event.key in [pygame.K_LEFT, pygame.K_a]:
                        new_idx = (current_idx - 1) % len(self.deck_preview_ids)
                        self.inspected_card_id = self.deck_preview_ids[new_idx]
                    elif event.key in [pygame.K_RIGHT, pygame.K_d]:
                        new_idx = (current_idx + 1) % len(self.deck_preview_ids)
                        self.inspected_card_id = self.deck_preview_ids[new_idx]
                    elif event.key in [pygame.K_UP, pygame.K_w]:
                        new_idx = (current_idx - 1) % len(self.deck_preview_ids)
                        self.inspected_card_id = self.deck_preview_ids[new_idx]
                    elif event.key in [pygame.K_DOWN, pygame.K_s]:
                        new_idx = (current_idx + 1) % len(self.deck_preview_ids)
                        self.inspected_card_id = self.deck_preview_ids[new_idx]
                else:
                    # Scroll the deck grid when not zoomed
                    if event.key in [pygame.K_UP, pygame.K_w]:
                        self.deck_scroll_offset = max(0, self.deck_scroll_offset - 50)
                    elif event.key in [pygame.K_DOWN, pygame.K_s]:
                        self.deck_scroll_offset += 50
            
            # Navigate between leaders with arrow keys
            elif self.state == "leader_select" and self.leader_buttons:
                if event.key in [pygame.K_UP, pygame.K_w]:
                    # Find current selection
                    current_idx = -1
                    if self.selected_leader:
                        for i, btn in enumerate(self.leader_buttons):
                            if btn['leader'] == self.selected_leader:
                                current_idx = i
                                break
                    # Move up
                    new_idx = max(0, current_idx - 1) if current_idx > 0 else len(self.leader_buttons) - 1
                    self.selected_leader = self.leader_buttons[new_idx]['leader']
                    self._ensure_leader_visible(new_idx)
                    if not self.deck_preview_ids:
                        self.deck_preview_ids = build_faction_deck(self.selected_faction, self.selected_leader)
                
                elif event.key in [pygame.K_DOWN, pygame.K_s]:
                    # Find current selection
                    current_idx = -1
                    if self.selected_leader:
                        for i, btn in enumerate(self.leader_buttons):
                            if btn['leader'] == self.selected_leader:
                                current_idx = i
                                break
                    # Move down
                    new_idx = (current_idx + 1) % len(self.leader_buttons)
                    self.selected_leader = self.leader_buttons[new_idx]['leader']
                    self._ensure_leader_visible(new_idx)
                    if not self.deck_preview_ids:
                        self.deck_preview_ids = build_faction_deck(self.selected_faction, self.selected_leader)
                
                elif event.key == pygame.K_RETURN and self.selected_leader:
                    # Enter to confirm and start
                    self.state = "complete"
            
            # Navigate between factions with arrow keys
            elif self.state == "faction_select":
                current_idx = -1
                if self.selected_faction:
                    for i, btn in enumerate(self.faction_buttons):
                        if btn['faction'] == self.selected_faction:
                            current_idx = i
                            break
                
                if event.key in [pygame.K_UP, pygame.K_w]:
                    new_idx = max(0, current_idx - 1) if current_idx > 0 else len(self.faction_buttons) - 1
                    self.selected_faction = self.faction_buttons[new_idx]['faction']
                
                elif event.key in [pygame.K_DOWN, pygame.K_s]:
                    new_idx = (current_idx + 1) % len(self.faction_buttons) if current_idx >= 0 else 0
                    self.selected_faction = self.faction_buttons[new_idx]['faction']
                
                elif event.key == pygame.K_RETURN and self.selected_faction:
                    # Enter to confirm faction
                    if self.for_new_game:
                        # NEW GAME: Go to leader selection
                        self.state = "leader_select"
                        self.setup_leader_buttons()
                    else:
                        # DECK BUILDING: Load saved leader and go directly to deck review
                        saved_leader_id = load_leader_choice(self.selected_faction)
                        available_leaders = self.get_leader_pool(self.selected_faction)
                        if saved_leader_id:
                            for leader in available_leaders:
                                if leader['card_id'] == saved_leader_id:
                                    self.selected_leader = leader
                                    break
                        if not self.selected_leader and available_leaders:
                            # Default to first leader if none saved
                            self.selected_leader = available_leaders[0]
                        
                        # Generate deck and go to review
                        self.deck_preview_ids = build_faction_deck(self.selected_faction, self.selected_leader)
                        self.card_pool_ids = get_faction_card_pool(self.selected_faction, self.unlock_system, self.unlock_override)
                        self.current_tab = "all"
                        self.inspected_card_id = None
                        self.state = "deck_review"
                        self.deck_scroll_offset = 0
                        self.pool_scroll_offset = 0
        
        # Handle mouse clicks for faction/leader selection (outside keyboard handler)
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = event.pos
            
            # Faction selection (LEFT CLICK ONLY)
            if self.state == "faction_select" and event.button == 1:
                for button in self.faction_buttons:
                    if button['rect'].collidepoint(mouse_pos):
                        self.selected_faction = button['faction']
                        # Update background to faction color
                        self.set_faction_background(self.selected_faction)
                        if self.for_new_game:
                            # NEW GAME: Go to leader selection
                            self.state = "leader_select"
                            self.setup_leader_buttons()
                        else:
                            # DECK BUILDING: Load saved leader and go directly to deck review
                            saved_leader_id = load_leader_choice(self.selected_faction)
                            available_leaders = self.get_leader_pool(self.selected_faction)
                            if saved_leader_id:
                                for leader in available_leaders:
                                    if leader['card_id'] == saved_leader_id:
                                        self.selected_leader = leader
                                        break
                            if not self.selected_leader and available_leaders:
                                # Default to first leader if none saved
                                self.selected_leader = available_leaders[0]
                            
                            # Generate deck and go to review
                            self.deck_preview_ids = build_faction_deck(self.selected_faction, self.selected_leader)
                            self.card_pool_ids = get_faction_card_pool(self.selected_faction, self.unlock_system, self.unlock_override)
                            self.current_tab = "all"
                            self.inspected_card_id = None
                            self.state = "deck_review"
                            self.deck_scroll_offset = 0
                            self.pool_scroll_offset = 0
                        return
            
            # Leader selection (LEFT CLICK ONLY)
            if self.state == "leader_select" and event.button == 1:
                # Back button
                if self.back_button.collidepoint(mouse_pos):
                    self.state = "faction_select"
                    self.selected_leader = None
                    self.deck_preview_ids = None
                    self.set_faction_background(self.selected_faction)
                    return
                
                # Leader buttons
                for idx, button in enumerate(self.leader_buttons):
                    display_rect = self._leader_button_display_rect(button['rect'])
                    if self.leader_area_rect and not self.leader_area_rect.collidepoint(mouse_pos):
                        continue
                    if display_rect.collidepoint(mouse_pos):
                        self.selected_leader = button['leader']
                        leader_id = self.selected_leader.get('card_id')
                        self.set_leader_background(leader_id)
                        self._ensure_leader_visible(idx)

                        # Generate deck preview
                        self.deck_preview_ids = build_faction_deck(self.selected_faction, self.selected_leader)
                        return

                # Review deck button
                review_rect = self._leader_button_display_rect(self.review_deck_button)
                if self.selected_leader and review_rect.collidepoint(mouse_pos):
                    self.state = "deck_review"
                    if not self.deck_preview_ids:
                        self.deck_preview_ids = build_faction_deck(self.selected_faction, self.selected_leader)
                    # Build card pool (all available cards for faction)
                    self.card_pool_ids = get_faction_card_pool(self.selected_faction, self.unlock_system, self.unlock_override)
                    self.current_tab = "all"
                    self.inspected_card_id = None
                    self.deck_scroll_offset = 0
                    self.pool_scroll_offset = 0
                    return
                
                # Continue button (if leader selected)
                continue_rect = self._leader_button_display_rect(self.continue_button)
                if self.selected_leader and continue_rect.collidepoint(mouse_pos):
                    # Save the selected leader before completing
                    save_leader_choice(self.selected_faction, self.selected_leader['card_id'])
                    print(f"✓ Leader choice saved: {self.selected_faction} -> {self.selected_leader['name']}")
                    self.state = "complete"
                    return
            
            # Deck review
            elif self.state == "deck_review":
                panel_padding = 20
                divider_x = self.screen_width // 2
                left_panel_x = panel_padding
                left_panel_width = divider_x - panel_padding * 2
                left_panel_y = 120  # Match draw code
                left_panel_height = self.screen_height - 180
                right_panel_x = divider_x + panel_padding
                right_panel_width = self.screen_width - right_panel_x - panel_padding
                right_panel_y = 120  # Match draw code
                right_panel_height = self.screen_height - 180
                left_panel_rect = pygame.Rect(left_panel_x, left_panel_y, left_panel_width, left_panel_height)
                right_panel_rect = pygame.Rect(right_panel_x, right_panel_y, right_panel_width, right_panel_height)
                deck_filter_type = None if self.current_tab == "all" else self.current_tab
                visible_deck_ids = get_cards_by_type_and_strength(self.deck_preview_ids, deck_filter_type) if self.deck_preview_ids else []
                
                # Check if clicking on tabs (LEFT CLICK)
                if event.button == 1 and self.tab_rects:
                    for tab_type, tab_rect in self.tab_rects.items():
                        if tab_rect.collidepoint(mouse_pos):
                            self.current_tab = tab_type
                            self.pool_scroll_offset = 0  # Reset scroll when changing tabs
                            return
                
                # Handle buttons before interacting with cards
                if event.button == 1:
                    if self.back_button.collidepoint(mouse_pos):
                        if self.for_new_game:
                            self.state = "leader_select"
                            self.deck_scroll_offset = 0
                            self.inspected_card_id = None
                        else:
                            self.save_current_deck("Deck saved before returning to main menu")
                            self.return_to_menu = True
                        return
                    
                    if self.for_new_game and self.continue_button.collidepoint(mouse_pos):
                        self.save_current_deck("Deck saved before starting the game")
                        self.state = "complete"
                        return
                    
                    if not self.for_new_game and self.save_button.collidepoint(mouse_pos):
                        self.save_current_deck()
                        return
                
                # RIGHT CLICK = ZOOM/INSPECT
                if event.button == 3:  # Right click
                    # Close inspection if already open
                    if self.inspected_card_id:
                        self.inspected_card_id = None
                        return
                    
                    # Find card under mouse to inspect
                    # Check cards in POOL (left panel)
                    if left_panel_rect.collidepoint(mouse_pos):
                        sorted_pool = get_cards_by_type_and_strength(self.card_pool_ids, self.current_tab)
                        cards_per_row, spacing, card_width, card_height = self.get_card_layout_params(left_panel_width)
                        start_x = left_panel_x + spacing
                        start_y = left_panel_y + 15 - self.pool_scroll_offset
                        
                        for i, card_id in enumerate(sorted_pool):
                            row_idx = i // cards_per_row
                            col_idx = i % cards_per_row
                            x = start_x + col_idx * (card_width + spacing)
                            y = start_y + row_idx * (card_height + spacing)
                            
                            card_rect = pygame.Rect(x, y, card_width, card_height)
                            if card_rect.collidepoint(mouse_pos):
                                self.inspected_card_id = card_id
                                return
                    
                    # Check cards in DECK (right panel)
                    elif right_panel_rect.collidepoint(mouse_pos):
                        if visible_deck_ids:
                            cards_per_row, spacing, card_width, card_height = self.get_card_layout_params(right_panel_width)
                            start_x = right_panel_x + spacing
                            start_y = right_panel_y + 15 - self.deck_scroll_offset
                            
                            for i, card_id in enumerate(visible_deck_ids):
                                row_idx = i // cards_per_row
                                col_idx = i % cards_per_row
                                x = start_x + col_idx * (card_width + spacing)
                                y = start_y + row_idx * (card_height + spacing)
                                
                                card_rect = pygame.Rect(x, y, card_width, card_height)
                                if card_rect.collidepoint(mouse_pos):
                                    self.inspected_card_id = card_id
                                    return
                    return
                
                # LEFT CLICK = DRAG (only if not inspecting)
                if event.button == 1 and not self.inspected_card_id:
                    # Check cards in POOL (left panel)
                    if left_panel_rect.collidepoint(mouse_pos):
                        sorted_pool = get_cards_by_type_and_strength(self.card_pool_ids, self.current_tab)
                        cards_per_row, spacing, card_width, card_height = self.get_card_layout_params(left_panel_width)
                        start_x = left_panel_x + spacing
                        start_y = left_panel_y + 15 - self.pool_scroll_offset
                        
                        for i, card_id in enumerate(sorted_pool):
                            row_idx = i // cards_per_row
                            col_idx = i % cards_per_row
                            x = start_x + col_idx * (card_width + spacing)
                            y = start_y + row_idx * (card_height + spacing)
                            
                            card_rect = pygame.Rect(x, y, card_width, card_height)
                            if card_rect.collidepoint(mouse_pos):
                                # Start dragging from pool
                                self.dragging_card = card_id
                                self.drag_from_pool = True
                                self.drag_start_x = mouse_pos[0]
                                self.drag_start_y = mouse_pos[1]
                                return
                    
                    # Check cards in DECK (right panel)
                    elif right_panel_rect.collidepoint(mouse_pos):
                        if visible_deck_ids:
                            cards_per_row, spacing, card_width, card_height = self.get_card_layout_params(right_panel_width)
                            start_x = right_panel_x + spacing
                            start_y = right_panel_y + 15 - self.deck_scroll_offset
                            
                            for i, card_id in enumerate(visible_deck_ids):
                                row_idx = i // cards_per_row
                                col_idx = i % cards_per_row
                                x = start_x + col_idx * (card_width + spacing)
                                y = start_y + row_idx * (card_height + spacing)
                                
                                card_rect = pygame.Rect(x, y, card_width, card_height)
                                if card_rect.collidepoint(mouse_pos):
                                    # Start dragging from deck
                                    self.dragging_card = card_id
                                    self.drag_from_pool = False
                                    self.drag_start_x = mouse_pos[0]
                                    self.drag_start_y = mouse_pos[1]
                                    return
                
    
    def draw(self, surface):
        """Draw the deck builder UI."""
        # Draw background - use image if available, otherwise use solid color
        if self.current_bg_image is not None:
            surface.blit(self.current_bg_image, (0, 0))
        else:
            surface.fill(self.current_bg_color)
        
        if self.state == "faction_select":
            self.draw_faction_select(surface)
        elif self.state == "leader_select":
            self.draw_leader_select(surface)
        elif self.state == "deck_review":
            self.draw_deck_review(surface)
        
        # Draw dragging card (follows mouse)
        if self.dragging_card:
            card = ALL_CARDS[self.dragging_card]
            card_width = 120
            card_height = 180
            scaled_image = pygame.transform.scale(card.image, (card_width, card_height))
            # Draw slightly transparent
            scaled_image.set_alpha(200)
            surface.blit(scaled_image, (self.drag_start_x - card_width // 2, self.drag_start_y - card_height // 2))
            # Bright border to show it's being dragged
            pygame.draw.rect(surface, (255, 255, 0), 
                           pygame.Rect(self.drag_start_x - card_width // 2, self.drag_start_y - card_height // 2, 
                                     card_width, card_height), width=4)
        
        # Draw inspected card overlay (on top of everything)
        if self.inspected_card_id:
            card = ALL_CARDS[self.inspected_card_id]
            self.draw_card_inspection(surface, card)
    
    def draw_faction_select(self, surface):
        """Draw faction selection screen."""
        # Title
        title = self.title_font.render("SELECT YOUR FACTION", True, self.highlight_color)
        title_rect = title.get_rect(center=(self.screen_width // 2, 100))
        surface.blit(title, title_rect)
        
        # Subtitle
        subtitle = self.desc_font.render("Choose which faction you want to command", True, self.text_color)
        subtitle_rect = subtitle.get_rect(center=(self.screen_width // 2, 160))
        surface.blit(subtitle, subtitle_rect)
        
        # Faction buttons
        for button in self.faction_buttons:
            # Determine button color
            if button['hovered']:
                color = self.button_hover_color
            else:
                color = self.button_color
            
            # Draw button with faction color accent
            pygame.draw.rect(surface, color, button['rect'], border_radius=10)
            faction_color = self.faction_colors[button['faction']]
            pygame.draw.rect(surface, faction_color, button['rect'], width=4, border_radius=10)
            
            # Draw faction name
            text = self.button_font.render(button['faction'], True, self.text_color)
            text_rect = text.get_rect(midleft=(button['rect'].left + 20, button['rect'].centery - 10))
            surface.blit(text, text_rect)
            
            # Draw faction description on same button (below name)
            desc = self.get_faction_description(button['faction'])
            desc_text = self.small_font.render(desc, True, (180, 180, 180))
            desc_rect = desc_text.get_rect(midleft=(button['rect'].left + 20, button['rect'].centery + 15))
            surface.blit(desc_text, desc_rect)
    
    def draw_leader_select(self, surface):
        """Draw leader selection screen."""
        # Title
        faction_color = self.faction_colors.get(self.selected_faction, self.highlight_color)
        title = self.title_font.render(f"{self.selected_faction}", True, faction_color)
        title_rect = title.get_rect(center=(self.screen_width // 2, 80))
        surface.blit(title, title_rect)
        
        # Subtitle
        subtitle = self.subtitle_font.render("Choose Your Leader", True, self.text_color)
        subtitle_rect = subtitle.get_rect(center=(self.screen_width // 2, 150))
        surface.blit(subtitle, subtitle_rect)
        
        # Leader buttons (scrollable list)
        if self.leader_area_rect:
            surface.set_clip(self.leader_area_rect)
        for button in self.leader_buttons:
            draw_rect = self._leader_button_display_rect(button['rect'])
            if self.leader_area_rect:
                if draw_rect.bottom < self.leader_area_rect.top or draw_rect.top > self.leader_area_rect.bottom:
                    continue
            # Determine button color
            is_selected = (self.selected_leader == button['leader'])
            if is_selected:
                color = self.button_selected_color
            elif button['hovered']:
                color = self.button_hover_color
            else:
                color = self.button_color
            
            # Draw button
            pygame.draw.rect(surface, color, draw_rect, border_radius=10)
            if is_selected:
                pygame.draw.rect(surface, self.highlight_color, draw_rect, width=5, border_radius=10)
            else:
                pygame.draw.rect(surface, faction_color, draw_rect, width=3, border_radius=10)
            
            # Draw leader name
            name_text = self.button_font.render(button['leader']['name'], True, self.text_color)
            name_rect = name_text.get_rect(center=(draw_rect.centerx, draw_rect.centery - 30))
            surface.blit(name_text, name_rect)
            
            # Draw ability description (wrapped to fit in button)
            ability = button['leader']['ability']
            max_width = draw_rect.width - 40  # Padding
            wrapped_lines = self.wrap_text(f"Ability: {ability}", self.desc_font, max_width)
            
            # Draw each line
            line_y = draw_rect.centery + 10
            for line in wrapped_lines:
                line_text = self.desc_font.render(line, True, (200, 200, 200))
                line_rect = line_text.get_rect(center=(draw_rect.centerx, line_y))
                surface.blit(line_text, line_rect)
                line_y += 25  # Line spacing
        if self.leader_area_rect:
            surface.set_clip(None)
            pygame.draw.rect(surface, (255, 255, 255), self.leader_area_rect, width=2, border_radius=12)
        
        # Back button
        pygame.draw.rect(surface, self.button_color, self.back_button, border_radius=5)
        back_text = self.button_font.render("< Back", True, self.text_color)
        back_rect = back_text.get_rect(center=self.back_button.center)
        surface.blit(back_text, back_rect)
        
        # Review Deck button (if leader selected)
        if self.selected_leader:
            review_rect = self._leader_button_display_rect(self.review_deck_button)
            pygame.draw.rect(surface, (100, 100, 200), review_rect, border_radius=10)
            review_text = self.button_font.render("Review Deck", True, self.text_color)
            surface.blit(review_text, review_text.get_rect(center=review_rect.center))
        
        # Continue button (if leader selected)
        if self.selected_leader:
            continue_rect = self._leader_button_display_rect(self.continue_button)
            pygame.draw.rect(surface, (50, 200, 50), continue_rect, border_radius=10)
            continue_text = self.button_font.render("START GAME", True, self.text_color)
            surface.blit(continue_text, continue_text.get_rect(center=continue_rect.center))
    
    def draw_deck_review(self, surface):
        """Draw deck review screen with two-panel layout and card type tabs."""
        # Full background (use deck_building_bg.png if available)
        if self.deck_building_bg:
            surface.blit(self.deck_building_bg, (0, 0))
        elif self.selected_faction:
            surface.fill(self.faction_bg_colors.get(self.selected_faction, self.bg_color))
        else:
            surface.fill(self.bg_color)
        
        # Title
        faction_color = self.faction_colors.get(self.selected_faction, self.highlight_color)
        title = self.subtitle_font.render(f"Deck Builder - {self.selected_faction}", True, faction_color)
        title_rect = title.get_rect(center=(self.screen_width // 2, 30))
        surface.blit(title, title_rect)
        
        # Draw card type tabs at the top
        self.draw_card_type_tabs(surface, faction_color)
        
        # Split screen into two panels
        panel_padding = 20
        divider_x = self.screen_width // 2
        
        # LEFT PANEL: Available cards (card pool)
        left_panel_x = panel_padding
        left_panel_width = divider_x - panel_padding * 2
        left_panel_y = 120  # Adjusted for tabs (was 80)
        left_panel_height = self.screen_height - 180  # Adjusted for tabs
        
        # LEFT PANEL HEADER
        left_header = self.desc_font.render("Available Cards (Card Pool)", True, self.highlight_color)
        surface.blit(left_header, (left_panel_x, left_panel_y - 30))
        
        # Draw left panel background (semi-transparent)
        panel_surf = pygame.Surface((left_panel_width, left_panel_height), pygame.SRCALPHA)
        panel_surf.fill((25, 25, 35, 120))  # Semi-transparent dark background
        surface.blit(panel_surf, (left_panel_x, left_panel_y))
        pygame.draw.rect(surface, faction_color, pygame.Rect(left_panel_x, left_panel_y, left_panel_width, left_panel_height), width=3, border_radius=10)
        
        # Draw card pool in LEFT panel
        if self.card_pool_ids:
            # Filter and sort cards by current tab
            sorted_pool_ids = get_cards_by_type_and_strength(self.card_pool_ids, self.current_tab)
            
            # Cards in 3 columns with better sizing
            cards_per_row, spacing, card_width, card_height = self.get_card_layout_params(left_panel_width)
            start_x = left_panel_x + spacing
            start_y = left_panel_y + 15 - self.pool_scroll_offset
            
            # Create clip rect for scrolling
            clip_rect = pygame.Rect(left_panel_x, left_panel_y, left_panel_width, left_panel_height)
            surface.set_clip(clip_rect)
            
            for i, card_id in enumerate(sorted_pool_ids):
                card = ALL_CARDS[card_id]
                row_idx = i // cards_per_row
                col_idx = i % cards_per_row
                x = start_x + col_idx * (card_width + spacing)
                y = start_y + row_idx * (card_height + spacing)
                
                # Only draw if visible
                if y + card_height >= left_panel_y and y <= left_panel_y + left_panel_height:
                    # Draw card
                    try:
                        scaled_image = pygame.transform.scale(card.image, (card_width, card_height))
                        surface.blit(scaled_image, (x, y))
                    except:
                        pygame.draw.rect(surface, (60, 60, 70), pygame.Rect(x, y, card_width, card_height), border_radius=5)
                    
                    pygame.draw.rect(surface, (150, 150, 150), pygame.Rect(x, y, card_width, card_height), width=2, border_radius=5)
                    
                    # Power overlay
                    if card.row not in ["special", "weather"]:
                        power_font = pygame.font.SysFont("Arial", 18, bold=True)
                        power_text = power_font.render(str(card.power), True, (255, 255, 255))
                        power_rect = power_text.get_rect(center=(x + card_width // 2, y + card_height - 15))
                        pygame.draw.rect(surface, (0, 0, 0), power_rect.inflate(4, 2))
                        surface.blit(power_text, power_rect)
            
            surface.set_clip(None)
            
            # Card pool stats below header
            pool_cards = [ALL_CARDS[id] for id in self.card_pool_ids]
            pool_unit_cards = [c for c in pool_cards if c.row in ["close", "ranged", "siege", "agile"]]
            pool_special_cards = [c for c in pool_cards if c.row == "special"]
            pool_weather_cards = [c for c in pool_cards if c.row == "weather"]
            
            pool_stats_text = self.small_font.render(
                f"Total: {len(self.card_pool_ids)} | Units: {len(pool_unit_cards)} | Special: {len(pool_special_cards)} | Weather: {len(pool_weather_cards)}", 
                True, (180, 180, 180)
            )
            surface.blit(pool_stats_text, (left_panel_x, left_panel_y - 55))
        
        # RIGHT PANEL: Current deck
        right_panel_x = divider_x + panel_padding
        right_panel_width = self.screen_width - right_panel_x - panel_padding
        right_panel_y = 120  # Adjusted for tabs (was 80)
        right_panel_height = self.screen_height - 180  # Adjusted for tabs
        
        # RIGHT PANEL HEADER with deck count
        if self.deck_preview_ids:
            right_header = self.desc_font.render(f"Your Deck ({len(self.deck_preview_ids)} cards)", True, self.highlight_color)
        else:
            right_header = self.desc_font.render("Your Deck (0 cards)", True, self.highlight_color)
        surface.blit(right_header, (right_panel_x, right_panel_y - 30))
        
        # Draw right panel background (semi-transparent)
        deck_panel_surf = pygame.Surface((right_panel_width, right_panel_height), pygame.SRCALPHA)
        deck_panel_surf.fill((25, 25, 35, 120))  # Semi-transparent dark background
        surface.blit(deck_panel_surf, (right_panel_x, right_panel_y))
        pygame.draw.rect(surface, (50, 200, 50), pygame.Rect(right_panel_x, right_panel_y, right_panel_width, right_panel_height), width=3, border_radius=10)
        
        # Draw deck sorted by type in RIGHT panel
        if self.deck_preview_ids:
            deck_filter_type = None if self.current_tab == "all" else self.current_tab
            sorted_deck_ids = get_cards_by_type_and_strength(self.deck_preview_ids, deck_filter_type)
            
            # Cards in 3 columns with better sizing
            cards_per_row, spacing, card_width, card_height = self.get_card_layout_params(right_panel_width)
            start_x = right_panel_x + spacing
            start_y = right_panel_y + 15 - self.deck_scroll_offset
            
            # Create clip rect for scrolling
            clip_rect = pygame.Rect(right_panel_x, right_panel_y, right_panel_width, right_panel_height)
            surface.set_clip(clip_rect)
            
            for i, card_id in enumerate(sorted_deck_ids):
                card = ALL_CARDS[card_id]
                row_idx = i // cards_per_row
                col_idx = i % cards_per_row
                x = start_x + col_idx * (card_width + spacing)
                y = start_y + row_idx * (card_height + spacing)
                
                # Only draw if visible
                if y + card_height >= right_panel_y and y <= right_panel_y + right_panel_height:
                    # Draw card
                    try:
                        scaled_image = pygame.transform.scale(card.image, (card_width, card_height))
                        surface.blit(scaled_image, (x, y))
                    except:
                        pygame.draw.rect(surface, (80, 80, 90), pygame.Rect(x, y, card_width, card_height), border_radius=5)
                    
                    pygame.draw.rect(surface, (255, 255, 255), pygame.Rect(x, y, card_width, card_height), width=2, border_radius=5)
                    
                    # Power overlay
                    if card.row not in ["special", "weather"]:
                        power_font = pygame.font.SysFont("Arial", 18, bold=True)
                        power_text = power_font.render(str(card.power), True, (255, 255, 255))
                        power_rect = power_text.get_rect(center=(x + card_width // 2, y + card_height - 15))
                        pygame.draw.rect(surface, (0, 0, 0), power_rect.inflate(4, 2))
                        surface.blit(power_text, power_rect)
            
            surface.set_clip(None)
            
            # Deck stats below header
            deck_cards = [ALL_CARDS[id] for id in self.deck_preview_ids]
            unit_cards = [c for c in deck_cards if c.row in ["close", "ranged", "siege", "agile"]]
            special_cards = [c for c in deck_cards if c.row == "special"]
            weather_cards = [c for c in deck_cards if c.row == "weather"]
            
            stats_text = self.small_font.render(
                f"Units: {len(unit_cards)} | Special: {len(special_cards)} | Weather: {len(weather_cards)}", 
                True, (180, 180, 180)
            )
            surface.blit(stats_text, (right_panel_x, right_panel_y - 55))
        
        # Instructions at top center
        if self.inspected_card_id:
            instructions = self.small_font.render("Click or Spacebar to close inspection", True, (200, 200, 200))
        else:
            instructions = self.small_font.render("Scroll each panel independently | Click cards to inspect", True, (200, 200, 200))
        inst_rect = instructions.get_rect(center=(self.screen_width // 2, 60))
        surface.blit(instructions, inst_rect)
        
        # Main Menu button (for deck building) or Back button (for new game)
        if self.for_new_game:
            # NEW GAME: Show "< Back" to go back to leader selection
            pygame.draw.rect(surface, self.button_color, self.back_button, border_radius=5)
            back_text = self.button_font.render("< Back", True, self.text_color)
            back_rect = back_text.get_rect(center=self.back_button.center)
            surface.blit(back_text, back_rect)
            
            # Show START GAME button
            pygame.draw.rect(surface, (50, 200, 50), self.continue_button, border_radius=10)
            continue_text = self.button_font.render("START GAME", True, self.text_color)
            continue_rect = continue_text.get_rect(center=self.continue_button.center)
            surface.blit(continue_text, continue_rect)
        else:
            # DECK BUILDING: Show "MAIN MENU" to return to menu
            pygame.draw.rect(surface, (80, 120, 180), self.back_button, border_radius=5)
            menu_text = self.button_font.render("MAIN MENU", True, self.text_color)
            menu_rect = menu_text.get_rect(center=self.back_button.center)
            surface.blit(menu_text, menu_rect)
            
            # Show SAVE DECK button
            pygame.draw.rect(surface, (50, 180, 50), self.save_button, border_radius=5)
            save_text = self.button_font.render("SAVE DECK", True, self.text_color)
            save_rect = save_text.get_rect(center=self.save_button.center)
            surface.blit(save_text, save_rect)
            
            # Show temporary confirmation message near the save button
            if self.last_save_message and pygame.time.get_ticks() - self.last_save_time < 3000:
                confirm_text = self.small_font.render(self.last_save_message, True, (200, 255, 200))
                confirm_rect = confirm_text.get_rect(midtop=(self.save_button.centerx, self.save_button.bottom + 10))
                surface.blit(confirm_text, confirm_rect)

        # Draw hover preview (if not inspecting or dragging)
        if self.hovered_card_id and not self.inspected_card_id and not self.dragging_card:
            self.draw_hover_preview(surface)


    def draw_card_inspection(self, surface, card):
        """Draw zoomed card inspection overlay."""
        # Semi-transparent background
        overlay = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        surface.blit(overlay, (0, 0))
        
        # Large card display
        card_display_width = 400
        card_display_height = 600
        card_x = (self.screen_width - card_display_width) // 2
        card_y = (self.screen_height - card_display_height) // 2 - 50
        
        # Draw card image (scaled up)
        try:
            large_card_image = pygame.transform.scale(card.image, (card_display_width, card_display_height))
            surface.blit(large_card_image, (card_x, card_y))
        except:
            pygame.draw.rect(surface, (80, 80, 90), pygame.Rect(card_x, card_y, card_display_width, card_display_height))
        
        pygame.draw.rect(surface, (255, 215, 0), pygame.Rect(card_x, card_y, card_display_width, card_display_height), width=5)
        
        # Card details panel
        details_y = card_y + card_display_height + 20
        details_x = card_x
        
        # Card name
        name_text = self.subtitle_font.render(card.name, True, self.highlight_color)
        surface.blit(name_text, (details_x, details_y))
        
        # Card stats
        stats_y = details_y + 40
        power_text = self.desc_font.render(f"Power: {card.power}", True, self.text_color)
        surface.blit(power_text, (details_x, stats_y))
        
        row_text = self.desc_font.render(f"Row: {card.row.capitalize()}", True, self.text_color)
        surface.blit(row_text, (details_x + 200, stats_y))
        
        faction_text = self.desc_font.render(f"Faction: {card.faction}", True, self.text_color)
        surface.blit(faction_text, (details_x, stats_y + 30))
        
        # Ability (wrapped to fit screen)
        if card.ability:
            ability_y = stats_y + 60
            max_width = self.screen_width - details_x - 100  # Leave margin
            wrapped_lines = self.wrap_text(f"Ability: {card.ability}", self.desc_font, max_width)
            
            for line in wrapped_lines:
                line_text = self.desc_font.render(line, True, (150, 255, 150))
                surface.blit(line_text, (details_x, ability_y))
                ability_y += 30
        
        # Close instruction
        close_text = self.small_font.render("Arrow Keys / Mouse Wheel to browse | SPACE or Click to close", True, (200, 200, 200))
        close_rect = close_text.get_rect(center=(self.screen_width // 2, self.screen_height - 30))
        surface.blit(close_text, close_rect)
    
    def draw_hover_preview(self, surface):
        """Draw hover preview card in top right corner of left panel."""
        if not self.hovered_card_id:
            return

        card = ALL_CARDS[self.hovered_card_id]

        # Calculate panel dimensions
        panel_padding = 20
        divider_x = self.screen_width // 2
        left_panel_x = panel_padding
        left_panel_width = divider_x - panel_padding * 2
        left_panel_y = 120

        # Get normal card dimensions and double them
        _, _, normal_card_width, normal_card_height = self.get_card_layout_params(left_panel_width)
        preview_card_width = normal_card_width * 2
        preview_card_height = normal_card_height * 2
        
        # Text area height
        text_area_height = 140
        total_height = preview_card_height + text_area_height

        # Position in top right corner of left panel with some padding
        preview_padding = 15
        preview_x = left_panel_x + left_panel_width - preview_card_width - preview_padding
        preview_y = left_panel_y + preview_padding

        # Draw semi-transparent background
        bg_surface = pygame.Surface((preview_card_width + 10, total_height + 10), pygame.SRCALPHA)
        bg_surface.fill((10, 10, 15, 230))  # Darker, more opaque background for readability
        surface.blit(bg_surface, (preview_x - 5, preview_y - 5))

        # Draw the card image scaled to preview size
        try:
            scaled_image = pygame.transform.scale(card.image, (preview_card_width, preview_card_height))
            surface.blit(scaled_image, (preview_x, preview_y))
        except:
            # Fallback: draw a colored rectangle if image fails
            pygame.draw.rect(surface, (80, 80, 90), pygame.Rect(preview_x, preview_y, preview_card_width, preview_card_height), border_radius=8)

        # Determine border color based on card type/rarity
        border_color = (205, 127, 50)  # Bronze (default for units)
        
        is_hero = False
        if card.ability and "Legendary" in card.ability:
            is_hero = True
        elif card.power >= 10 and card.row not in ["special", "weather"]:
            is_hero = True
            
        if is_hero:
            border_color = (255, 215, 0)  # Gold for Heroes
        elif card.row in ["special", "weather"]:
            border_color = (192, 192, 192)  # Silver for Special/Weather
            
        # Draw border around the IMAGE only
        pygame.draw.rect(surface, border_color, pygame.Rect(preview_x, preview_y, preview_card_width, preview_card_height), width=4, border_radius=8)

        # Draw power overlay for unit cards (on the image)
        if card.row not in ["special", "weather"]:
            power_font = pygame.font.SysFont("Arial", 28, bold=True)
            power_text = power_font.render(str(card.power), True, (255, 255, 255))
            power_rect = power_text.get_rect(center=(preview_x + preview_card_width // 2, preview_y + preview_card_height - 25))
            # Black background for power text
            bg_rect = power_rect.inflate(16, 8)
            pygame.draw.rect(surface, (0, 0, 0), bg_rect, border_radius=3)
            pygame.draw.rect(surface, (200, 200, 200), bg_rect, width=1, border_radius=3)
            surface.blit(power_text, power_rect)
            
        # --- Draw Text Info Below Image ---
        text_start_y = preview_y + preview_card_height + 10
        center_x = preview_x + preview_card_width // 2
        
        # 1. Card Name
        name_font = pygame.font.SysFont("Arial", 20, bold=True)
        name_text = name_font.render(card.name, True, (255, 215, 0)) # Gold color
        name_rect = name_text.get_rect(center=(center_x, text_start_y + 10))
        surface.blit(name_text, name_rect)
        
        # 2. Row / Type
        type_font = pygame.font.SysFont("Arial", 16, italic=True)
        row_str = card.row.capitalize()
        if card.row == "close": row_str = "Melee Combat"
        elif card.row == "ranged": row_str = "Ranged Combat"
        elif card.row == "siege": row_str = "Siege Combat"
        
        type_text = type_font.render(f"{row_str} • {card.faction}", True, (180, 180, 180))
        type_rect = type_text.get_rect(center=(center_x, text_start_y + 32))
        surface.blit(type_text, type_rect)
        
        # 3. Ability Description
        if card.ability:
            desc_font = pygame.font.SysFont("Arial", 16)
            # Wrap text
            wrapped_lines = self.wrap_text(card.ability, desc_font, preview_card_width - 10)
            line_y = text_start_y + 55
            for line in wrapped_lines:
                line_text = desc_font.render(line, True, (220, 220, 220))
                line_rect = line_text.get_rect(center=(center_x, line_y))
                surface.blit(line_text, line_rect)
                line_y += 18
        else:
            # No ability text
            desc_font = pygame.font.SysFont("Arial", 16)
            no_ab_text = desc_font.render("No special ability.", True, (100, 100, 100))
            no_ab_rect = no_ab_text.get_rect(center=(center_x, text_start_y + 60))
            surface.blit(no_ab_text, no_ab_rect)

    def draw_card_type_tabs(self, surface, faction_color):
        """Draw tabs for filtering cards by type."""
        tabs = [
            ("All", "all"),
            ("Close", "close"),
            ("Ranged", "ranged"),
            ("Siege", "siege"),
            ("Agile", "agile"),
            ("Special", "special"),
            ("Weather", "weather"),
            ("Neutral", "neutral")
        ]
        
        tab_width = 100
        tab_height = 40
        tab_spacing = 5
        total_width = len(tabs) * tab_width + (len(tabs) - 1) * tab_spacing
        start_x = (self.screen_width - total_width) // 2
        tab_y = 70
        self.tab_rects = {}
        
        for i, (label, tab_type) in enumerate(tabs):
            tab_x = start_x + i * (tab_width + tab_spacing)
            tab_rect = pygame.Rect(tab_x, tab_y, tab_width, tab_height)
            
            # Color based on selection
            if self.current_tab == tab_type:
                color = faction_color
                text_color = (255, 255, 255)
            else:
                color = (60, 60, 70)
                text_color = (150, 150, 150)
            
            # Draw tab
            pygame.draw.rect(surface, color, tab_rect, border_radius=5)
            pygame.draw.rect(surface, faction_color, tab_rect, width=2, border_radius=5)
            
            # Draw label
            label_text = self.small_font.render(label, True, text_color)
            label_rect = label_text.get_rect(center=tab_rect.center)
            surface.blit(label_text, label_rect)
            
            # Store rect for click detection
            self.tab_rects[tab_type] = tab_rect
    
    def get_faction_description(self, faction):
        """Get a short description for each faction."""
        descriptions = {
            FACTION_TAURI: "Earth's defenders - balanced and versatile",
            FACTION_GOAULD: "Ancient parasites - overwhelming numbers",
            FACTION_JAFFA: "Freedom fighters - agile warriors",
            FACTION_LUCIAN: "Space pirates - cunning and deceptive",
            FACTION_ASGARD: "Advanced aliens - technological superiority",
        }
        return descriptions.get(faction, "")
    
    def wrap_text(self, text, font, max_width):
        """Wrap text to fit within max_width. Returns list of lines."""
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
        
        return lines if lines else [text]
    
    def is_complete(self):
        """Check if deck building is complete."""
        return self.state == "complete"
    
    def get_selection(self):
        """Get the selected faction and leader."""
        return {
            'faction': self.selected_faction,
            'leader': self.selected_leader,
            'deck_ids': self.deck_preview_ids
        }


# Gwent deck rules
MIN_DECK_SIZE = 25  # Minimum cards required in a deck (Gwent standard)
MAX_DECK_SIZE = 40  # Maximum cards allowed (optional limit)


def validate_deck(deck):
    """Validate deck meets Gwent requirements."""
    if len(deck) < MIN_DECK_SIZE:
        return False, f"Deck too small: {len(deck)}/{MIN_DECK_SIZE} cards minimum"
    if len(deck) > MAX_DECK_SIZE:
        return False, f"Deck too large: {len(deck)}/{MAX_DECK_SIZE} cards maximum"
    
    # Count card types for balance
    unit_cards = [c for c in deck if c.row in ["close", "ranged", "siege", "agile"]]
    special_cards = [c for c in deck if c.row == "special"]
    
    if len(unit_cards) < 15:
        return False, f"Need at least 15 unit cards (have {len(unit_cards)})"
    
    return True, "Deck valid"


def build_faction_deck(faction, leader=None, *, unlock_system=None, unlock_override=False):
    """
    Build a deck for the specified faction following Gwent rules.
    First checks if there's a saved deck, otherwise creates a new random one.
    Returns a list of card IDs from the faction.
    Ensures minimum deck size of 25 cards and maximum of 40 cards.
    """
    # First, try to load saved deck
    saved_deck_data = load_player_deck(faction)
    if saved_deck_data and saved_deck_data.get("cards"):
        print(f"✓ Loading saved deck for {faction} ({len(saved_deck_data['cards'])} cards)")
        return list(saved_deck_data["cards"])
    
    # No saved deck found, build a new random one
    print(f"Building new default deck for {faction}...")
    
    unlock_system = unlock_system or CardUnlockSystem()

    # Get all card IDs from the selected faction (respect unlocks)
    faction_card_ids = [
        card.id for card in ALL_CARDS.values()
        if card.faction == faction and is_card_available(card.id, unlock_system, unlock_override)
    ]
    
    # If faction has more than 40 cards, randomly select 35 of them to leave room for neutrals
    if len(faction_card_ids) > 35:
        faction_card_ids = random.sample(faction_card_ids, 35)
    
    # Add some neutral cards (randomly select 3-5 neutral card IDs)
    neutral_card_ids = [
        card.id for card in ALL_CARDS.values()
        if card.faction == FACTION_NEUTRAL
        and "Legendary Commander" not in (card.ability or "")
        and is_card_available(card.id, unlock_system, unlock_override)
    ]
    # Filter out Legendary Commander neutrals to keep balance, but allow all rows
    useful_neutrals = neutral_card_ids
    num_neutrals = min(5, len(useful_neutrals))
    selected_neutrals = random.sample(useful_neutrals, num_neutrals) if useful_neutrals else []
    
    # Combine faction card IDs with neutral card IDs
    deck_ids = faction_card_ids + selected_neutrals
    
    # Ensure we don't exceed maximum
    if len(deck_ids) > MAX_DECK_SIZE:
        # Trim to max size, keeping a good balance
        deck_ids = random.sample(deck_ids, MAX_DECK_SIZE)
    
    # Ensure minimum deck size
    if len(deck_ids) < MIN_DECK_SIZE:
        # Add more neutral cards if needed to reach minimum
        remaining_neutrals = [id for id in neutral_card_ids if id not in selected_neutrals]
        needed = MIN_DECK_SIZE - len(deck_ids)
        if remaining_neutrals and needed > 0:
            additional = random.sample(remaining_neutrals, min(needed, len(remaining_neutrals)))
            deck_ids.extend(additional)
    
    # Final safety check
    if len(deck_ids) > MAX_DECK_SIZE:
        deck_ids = deck_ids[:MAX_DECK_SIZE]
    
    # Shuffle the deck
    random.shuffle(deck_ids)
    
    # Validate deck
    deck = [ALL_CARDS[id] for id in deck_ids]
    is_valid, message = validate_deck(deck)
    if not is_valid:
        print(f"Warning: {message}")
    else:
        print(f"Deck built for {faction}: {len(deck_ids)} cards")
    
    return deck_ids


def is_card_available(card_id: str, unlock_system, unlock_override: bool) -> bool:
    """Return True if the card is usable given unlock state/override."""
    if unlock_override:
        return True
    if card_id not in UNLOCKABLE_CARDS:
        return True
    if unlock_system:
        return unlock_system.is_unlocked(card_id)
    return False


def get_faction_card_pool(faction, unlock_system=None, unlock_override=False):
    """
    Get all available cards for a faction (card pool).
    Returns a list of card IDs including all neutral cards, filtered by unlocks.
    """
    unlock_system = unlock_system or CardUnlockSystem()
    faction_card_ids = [
        card.id for card in ALL_CARDS.values()
        if card.faction == faction and is_card_available(card.id, unlock_system, unlock_override)
    ]
    neutral_card_ids = [
        card.id for card in ALL_CARDS.values()
        if card.faction == FACTION_NEUTRAL and is_card_available(card.id, unlock_system, unlock_override)
    ]

    # Combine and deduplicate
    card_pool_ids = list(dict.fromkeys(faction_card_ids + neutral_card_ids))
    return card_pool_ids


def get_cards_by_type_and_strength(card_id_list, card_type=None):
    """
    Filter cards by type and sort by strength (power).
    card_type can be: 'close', 'ranged', 'siege', 'agile', 'special', 'weather', 'neutral', or None for all.
    Returns sorted list of card IDs.
    """
    filtered_ids = card_id_list
    if card_type and card_type != "all":
        if card_type == "neutral":
            filtered_ids = [id for id in card_id_list if ALL_CARDS[id].faction == FACTION_NEUTRAL]
        else:
            filtered_ids = [id for id in card_id_list if ALL_CARDS[id].row == card_type]
    
    # Sort by type first, then by power (descending)
    def sort_key(card_id):
        card = ALL_CARDS[card_id]
        # Type priority order
        type_priority = {
            "close": 0,
            "ranged": 1,
            "siege": 2,
            "agile": 3,
            "special": 4,
            "weather": 5
        }
        neutral_priority = -1 if card.faction == FACTION_NEUTRAL else 0
        return (type_priority.get(card.row, 99), neutral_priority, -card.power)
    
    sorted_ids = sorted(filtered_ids, key=sort_key)
    return sorted_ids


def run_deck_builder(screen, for_new_game=True, *, unlock_override=False, unlock_system=None, toggle_fullscreen_callback=None):
    """
    Run the deck builder interface.
    Args:
        screen: Pygame screen surface
        for_new_game: If True, full flow with leader selection for starting a new game.
                     If False, skip directly to deck customization (from main menu deck building).
    Returns the selected faction and leader, or None if cancelled.
    """
    # CRITICAL: Reload card images to ensure they're loaded with proper screen dimensions
    print("Deck Builder: Reloading card images...")
    reload_card_images()
    print("Deck Builder: Card images reloaded successfully!")
    
    screen_width = screen.get_width()
    screen_height = screen.get_height()
    
    deck_builder = DeckBuilderUI(
        screen_width,
        screen_height,
        for_new_game=for_new_game,
        unlock_override=unlock_override,
        unlock_system=unlock_system
    )
    clock = pygame.time.Clock()
    
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                stop_faction_theme()
                return None
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if deck_builder.state == "leader_select":
                        deck_builder.state = "faction_select"
                        deck_builder.selected_leader = None
                    else:
                        stop_faction_theme()
                        return None
                elif event.key == pygame.K_F11 or (event.key == pygame.K_RETURN and (event.mod & pygame.KMOD_ALT)):
                    if toggle_fullscreen_callback:
                        toggle_fullscreen_callback()
                    else:
                        pygame.display.toggle_fullscreen()
                    reload_card_images()
                    screen = pygame.display.get_surface()
                    deck_builder.refresh_for_surface(screen)
            else:
                deck_builder.handle_event(event)
        
        # Check if deck building is complete
        if deck_builder.is_complete():
            stop_faction_theme()
            return deck_builder.get_selection()

        # Check if user clicked MAIN MENU button from deck building
        if deck_builder.return_to_menu:
            print("✓ Returning to main menu from deck builder")
            stop_faction_theme()
            return None
        
        # Draw
        deck_builder.draw(screen)
        pygame.display.flip()
        clock.tick(60)
    
    return None
