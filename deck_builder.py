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
from abilities import is_hero
from game_settings import get_settings
import board_renderer

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
    """Deck builder interface with Accordion Preview and Split Layout."""
    
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
        self.pool_scroll_offset = 0  # Horizontal scroll for bottom accordion
        self.inspected_card_id = None  # Card being inspected with spacebar
        self.card_pool_ids = []  # Available cards for the faction
        self.current_tab = "all"  # Current card type tab
        self.keyword_filter = None  # Filter by keyword (Spy, Medic, Hero)
        self.filter_rects = {}  # Clickable areas for filter buttons
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
        self.drag_current_x = 0  # Smoothed position
        self.drag_current_y = 0  # Smoothed position
        self.drag_target_x = 0  # Mouse target position
        self.drag_target_y = 0  # Mouse target position
        self.drag_from_pool = False  # True if dragging from pool, False if from deck
        self.drag_smoothing = 0.25  # Lerp factor for smooth movement (lower = smoother)

        # HOVER PREVIEW STATE
        self.hovered_card_id = None  # Card ID being hovered over for preview
        self.deck_remove_buttons = {}  # Track remove button positions for click detection
        
        # ACCORDION STATE (for bottom panel animation)
        self.accordion_hover_card_id = None  # Card being hovered in accordion
        self.accordion_lift_amount = {}  # Per-card lift animation state

        # KEYBOARD NAVIGATION STATE
        self.keyboard_pool_cursor = -1  # -1 = none, 0+ = index in filtered pool
        self.keyboard_deck_cursor = -1  # -1 = none, 0+ = index in deck list
        self.keyboard_focus = "pool"  # "pool" or "deck" - which panel has focus

        # IMAGE CACHE for scaled card images (avoid loading from disk every frame)
        self._scaled_image_cache = {}  # (card_id, width, height) -> pygame.Surface

        # Fonts
        self.title_font = pygame.font.SysFont("Arial", 64, bold=True)
        self.subtitle_font = pygame.font.SysFont("Arial", 36, bold=True)
        self.desc_font = pygame.font.SysFont("Arial", 24)
        self.button_font = pygame.font.SysFont("Arial", 28, bold=True)
        self.small_font = pygame.font.SysFont("Arial", 20)
        self.stat_font = pygame.font.SysFont("Arial", 22)
        # Additional cached fonts for hover preview
        self.power_font = pygame.font.SysFont("Arial", 24, bold=True)
        self.preview_name_font = pygame.font.SysFont("Arial", 18, bold=True)
        self.preview_type_font = pygame.font.SysFont("Arial", 14)
        self.preview_desc_font = pygame.font.SysFont("Arial", 14)
        
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
            FACTION_LUCIAN: (200, 100, 255),    # Pink
            FACTION_ASGARD: (100, 255, 255),    # Cyan
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
        self.load_tab_icons()
        self.tab_rects = {}
        
        # Layout
        self.setup_layout()

    def load_tab_icons(self):
        """Load icons for deck builder tabs."""
        self.tab_icons = {}
        icon_mappings = {
            "all": "icons/all.png",
            "close": "icons/close.png",
            "ranged": "icons/ranged.png",
            "siege": "icons/siege.png",
            "agile": "icons/agile.png",
            "weather": "icons/weather.png",
            "legendary": "icons/Legendary commander.png",
            "neutral": "icons/neutral.png",
            "special": "icons/special.png"
        }
        
        for tab_type, filename in icon_mappings.items():
            path = os.path.join("assets", filename)
            if os.path.exists(path):
                try:
                    img = pygame.image.load(path).convert_alpha()
                    # Store original image for high-quality scaling during draw
                    self.tab_icons[tab_type] = img
                except Exception as e:
                    print(f"Failed to load tab icon {filename}: {e}")

    def _get_scaled_card_image(self, card, width, height):
        """Get a cached scaled card image. Loads from disk only once per size."""
        cache_key = (card.id, width, height)
        if cache_key not in self._scaled_image_cache:
            try:
                if hasattr(card, 'image_path') and os.path.exists(card.image_path):
                    original = pygame.image.load(card.image_path).convert_alpha()
                    self._scaled_image_cache[cache_key] = pygame.transform.smoothscale(original, (width, height))
                else:
                    self._scaled_image_cache[cache_key] = pygame.transform.smoothscale(card.image, (width, height))
            except Exception:
                return None
        return self._scaled_image_cache[cache_key]

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
        """Calculate layout positions for the new Witcher-style UI."""
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
        
        # === NEW DECK REVIEW LAYOUT ===
        # Back button (Top Left - DHD styled)
        self.back_button = pygame.Rect(20, 20, 80, 104)  # DHD button size

        # Stats Box (Top Left below back button - Holographic style)
        self.stats_box_rect = pygame.Rect(20, 130, 320, 180)
        
        # Deck List Panel (Right Side - vertical list)
        deck_list_width = 380
        deck_list_top = 100
        self.deck_list_rect = pygame.Rect(
            self.screen_width - deck_list_width - 20, 
            deck_list_top, 
            deck_list_width, 
            self.screen_height - deck_list_top - 420  # Leave room for accordion
        )
        
        # Bottom Accordion Area (2x size cards horizontal scroll)
        accordion_height = 380
        self.accordion_area_rect = pygame.Rect(
            0, 
            self.screen_height - accordion_height, 
            self.screen_width, 
            accordion_height
        )
        
        # Save button (for deck building mode) - positioned above accordion
        self.save_button = pygame.Rect(
            self.screen_width // 2 - 100,
            self.screen_height - accordion_height - 60,
            200,
            50
        )
        
        # Faction tabs positioning (Top Center)
        self.faction_tab_rects = {}

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

            # If dragging, update target position for smooth interpolation
            if self.dragging_card:
                self.drag_target_x = mouse_pos[0]
                self.drag_target_y = mouse_pos[1]
            
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

            # Update hover preview for cards in deck review (new layout)
            elif self.state == "deck_review":
                # Reset hovered card (will be set by draw methods)
                self.hovered_card_id = None
                self.accordion_hover_card_id = None

                # Don't show hover preview while dragging or inspecting
                if self.dragging_card or self.inspected_card_id:
                    return
        
        elif event.type == pygame.MOUSEBUTTONUP:
            # Complete drag and drop for new layout
            if self.dragging_card and event.button == 1:
                mouse_pos = event.pos
                
                # Dropped on Deck List (right side) - add to deck
                if self.deck_list_rect.collidepoint(mouse_pos) and self.drag_from_pool:
                    if len(self.deck_preview_ids or []) < MAX_DECK_SIZE:
                        if self.deck_preview_ids is None:
                            self.deck_preview_ids = []
                        if self.dragging_card not in self.deck_preview_ids:
                            self.deck_preview_ids.append(self.dragging_card)
                
                # Dropped on Accordion (bottom) - remove from deck (if dragging from deck)
                elif self.accordion_area_rect.collidepoint(mouse_pos) and not self.drag_from_pool:
                    if self.deck_preview_ids and self.dragging_card in self.deck_preview_ids:
                        self.deck_preview_ids.remove(self.dragging_card)
                
                # Dropped anywhere else outside deck list while dragging from deck = remove
                elif not self.deck_list_rect.collidepoint(mouse_pos) and not self.drag_from_pool:
                    if self.deck_preview_ids and self.dragging_card in self.deck_preview_ids:
                        self.deck_preview_ids.remove(self.dragging_card)
                
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
                        current_idx = all_card_ids.index(self.inspected_card_id) if self.inspected_card_id in all_card_ids else 0
                        if event.y > 0:  # Scroll up = previous card
                            new_idx = (current_idx - 1) % len(all_card_ids)
                            self.inspected_card_id = all_card_ids[new_idx]
                        elif event.y < 0:  # Scroll down = next card
                            new_idx = (current_idx + 1) % len(all_card_ids)
                            self.inspected_card_id = all_card_ids[new_idx]
                else:
                    # Determine which area to scroll based on mouse position
                    mouse_pos = pygame.mouse.get_pos()
                    
                    # Bottom Accordion - HORIZONTAL scroll (use event.x if available, or map y to horizontal)
                    if self.accordion_area_rect.collidepoint(mouse_pos):
                        # Calculate max scroll based on pool size
                        pool_ids = get_cards_by_type_and_strength(self.card_pool_ids, self.current_tab, self.keyword_filter)
                        card_w = 160
                        spacing = 15
                        max_scroll = max(0, len(pool_ids) * (card_w + spacing) - self.screen_width + 80)
                        # Horizontal scroll using vertical wheel
                        self.pool_scroll_offset = max(0, min(max_scroll, self.pool_scroll_offset - event.y * 80))
                    
                    # Deck List (right side) - VERTICAL scroll
                    elif self.deck_list_rect.collidepoint(mouse_pos):
                        self.deck_scroll_offset = max(0, self.deck_scroll_offset - event.y * 40)
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
                        # Use proper rect-based collision detection (same as modern handler)
                        # Bottom Accordion - HORIZONTAL scroll
                        if self.accordion_area_rect.collidepoint(mouse_pos):
                            pool_ids = get_cards_by_type_and_strength(self.card_pool_ids, self.current_tab, self.keyword_filter)
                            card_w = 160
                            spacing = 15
                            max_scroll = max(0, len(pool_ids) * (card_w + spacing) - self.screen_width + 80)
                            if event.button == 4:
                                self.pool_scroll_offset = max(0, self.pool_scroll_offset - 80)
                            elif event.button == 5:
                                self.pool_scroll_offset = min(max_scroll, self.pool_scroll_offset + 80)
                        # Deck List (right side) - VERTICAL scroll
                        elif self.deck_list_rect.collidepoint(mouse_pos):
                            if event.button == 4:
                                self.deck_scroll_offset = max(0, self.deck_scroll_offset - 40)
                            elif event.button == 5:
                                self.deck_scroll_offset += 40
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
            # Keyboard navigation in deck review
            if self.state == "deck_review":
                if self.inspected_card_id and self.deck_preview_ids:
                    # Navigate between cards with arrow keys when zoomed
                    try:
                        current_idx = self.deck_preview_ids.index(self.inspected_card_id)
                    except ValueError:
                        current_idx = 0
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
                    elif event.key == pygame.K_ESCAPE:
                        self.inspected_card_id = None
                else:
                    pool_ids = get_cards_by_type_and_strength(self.card_pool_ids, self.current_tab, self.keyword_filter)
                    pool_count = len(pool_ids) if pool_ids else 0

                    if event.key == pygame.K_TAB:
                        if self.keyboard_focus == "pool":
                            self.keyboard_focus = "deck"
                            self.keyboard_deck_cursor = 0 if self.deck_preview_ids else -1
                        else:
                            self.keyboard_focus = "pool"
                            self.keyboard_pool_cursor = 0 if pool_count > 0 else -1

                    elif event.key in [pygame.K_LEFT, pygame.K_a]:
                        if self.keyboard_focus == "pool" and pool_count > 0:
                            if self.keyboard_pool_cursor < 0:
                                self.keyboard_pool_cursor = 0
                            else:
                                self.keyboard_pool_cursor = (self.keyboard_pool_cursor - 1) % pool_count
                            card_w = 175
                            if self.keyboard_pool_cursor < self.pool_scroll_offset // card_w:
                                self.pool_scroll_offset = max(0, self.keyboard_pool_cursor * card_w)

                    elif event.key in [pygame.K_RIGHT, pygame.K_d]:
                        if self.keyboard_focus == "pool" and pool_count > 0:
                            if self.keyboard_pool_cursor < 0:
                                self.keyboard_pool_cursor = 0
                            else:
                                self.keyboard_pool_cursor = (self.keyboard_pool_cursor + 1) % pool_count
                            card_w = 175
                            cards_visible = max(1, (self.screen_width - 350) // card_w)
                            if self.keyboard_pool_cursor >= (self.pool_scroll_offset // card_w) + cards_visible:
                                self.pool_scroll_offset = (self.keyboard_pool_cursor - cards_visible + 1) * card_w

                    elif event.key in [pygame.K_UP, pygame.K_w]:
                        if self.keyboard_focus == "deck" and self.deck_preview_ids:
                            unique_count = len(set(self.deck_preview_ids))
                            if unique_count > 0:
                                self.keyboard_deck_cursor = max(0, self.keyboard_deck_cursor - 1) if self.keyboard_deck_cursor > 0 else unique_count - 1
                        else:
                            tabs = ["all", "close", "ranged", "siege", "agile", "legendary", "special", "weather", "neutral"]
                            idx = tabs.index(self.current_tab) if self.current_tab in tabs else 0
                            self.current_tab = tabs[(idx - 1) % len(tabs)]
                            self.pool_scroll_offset = 0
                            self.keyboard_pool_cursor = 0

                    elif event.key in [pygame.K_DOWN, pygame.K_s]:
                        if self.keyboard_focus == "deck" and self.deck_preview_ids:
                            unique_count = len(set(self.deck_preview_ids))
                            if unique_count > 0:
                                self.keyboard_deck_cursor = (self.keyboard_deck_cursor + 1) % unique_count
                        else:
                            tabs = ["all", "close", "ranged", "siege", "agile", "legendary", "special", "weather", "neutral"]
                            idx = tabs.index(self.current_tab) if self.current_tab in tabs else 0
                            self.current_tab = tabs[(idx + 1) % len(tabs)]
                            self.pool_scroll_offset = 0
                            self.keyboard_pool_cursor = 0

                    elif event.key in [pygame.K_f, pygame.K_RETURN] and self.keyboard_focus == "pool":
                        if pool_ids and 0 <= self.keyboard_pool_cursor < len(pool_ids):
                            if self.deck_preview_ids is None:
                                self.deck_preview_ids = []
                            self.deck_preview_ids.append(pool_ids[self.keyboard_pool_cursor])

                    elif event.key in [pygame.K_DELETE, pygame.K_BACKSPACE] and self.keyboard_focus == "deck":
                        if self.deck_preview_ids and self.keyboard_deck_cursor >= 0:
                            from collections import Counter
                            unique_ids = sorted(list(set(self.deck_preview_ids)), key=lambda x: (ALL_CARDS[x].row, -ALL_CARDS[x].power))
                            if self.keyboard_deck_cursor < len(unique_ids):
                                self.deck_preview_ids.remove(unique_ids[self.keyboard_deck_cursor])
                                if self.keyboard_deck_cursor >= len(set(self.deck_preview_ids)):
                                    self.keyboard_deck_cursor = max(0, len(set(self.deck_preview_ids)) - 1)

                    elif event.key == pygame.K_SPACE:
                        if self.inspected_card_id:
                            self.inspected_card_id = None
                        elif self.keyboard_focus == "pool" and pool_ids and 0 <= self.keyboard_pool_cursor < len(pool_ids):
                            self.inspected_card_id = pool_ids[self.keyboard_pool_cursor]
                        elif self.keyboard_focus == "deck" and self.deck_preview_ids:
                            unique_ids = sorted(list(set(self.deck_preview_ids)), key=lambda x: (ALL_CARDS[x].row, -ALL_CARDS[x].power))
                            if 0 <= self.keyboard_deck_cursor < len(unique_ids):
                                self.inspected_card_id = unique_ids[self.keyboard_deck_cursor]
            
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
            # Keyboard navigation in deck review
            if self.state == "deck_review":
                if self.inspected_card_id and self.deck_preview_ids:
                    # Navigate between cards with arrow keys when zoomed
                    try:
                        current_idx = self.deck_preview_ids.index(self.inspected_card_id)
                    except ValueError:
                        current_idx = 0
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
                    elif event.key == pygame.K_ESCAPE:
                        self.inspected_card_id = None
                else:
                    pool_ids = get_cards_by_type_and_strength(self.card_pool_ids, self.current_tab, self.keyword_filter)
                    pool_count = len(pool_ids) if pool_ids else 0

                    if event.key == pygame.K_TAB:
                        if self.keyboard_focus == "pool":
                            self.keyboard_focus = "deck"
                            self.keyboard_deck_cursor = 0 if self.deck_preview_ids else -1
                        else:
                            self.keyboard_focus = "pool"
                            self.keyboard_pool_cursor = 0 if pool_count > 0 else -1

                    elif event.key in [pygame.K_LEFT, pygame.K_a]:
                        if self.keyboard_focus == "pool" and pool_count > 0:
                            if self.keyboard_pool_cursor < 0:
                                self.keyboard_pool_cursor = 0
                            else:
                                self.keyboard_pool_cursor = (self.keyboard_pool_cursor - 1) % pool_count
                            card_w = 175
                            if self.keyboard_pool_cursor < self.pool_scroll_offset // card_w:
                                self.pool_scroll_offset = max(0, self.keyboard_pool_cursor * card_w)

                    elif event.key in [pygame.K_RIGHT, pygame.K_d]:
                        if self.keyboard_focus == "pool" and pool_count > 0:
                            if self.keyboard_pool_cursor < 0:
                                self.keyboard_pool_cursor = 0
                            else:
                                self.keyboard_pool_cursor = (self.keyboard_pool_cursor + 1) % pool_count
                            card_w = 175
                            cards_visible = max(1, (self.screen_width - 350) // card_w)
                            if self.keyboard_pool_cursor >= (self.pool_scroll_offset // card_w) + cards_visible:
                                self.pool_scroll_offset = (self.keyboard_pool_cursor - cards_visible + 1) * card_w

                    elif event.key in [pygame.K_UP, pygame.K_w]:
                        if self.keyboard_focus == "deck" and self.deck_preview_ids:
                            unique_count = len(set(self.deck_preview_ids))
                            if unique_count > 0:
                                self.keyboard_deck_cursor = max(0, self.keyboard_deck_cursor - 1) if self.keyboard_deck_cursor > 0 else unique_count - 1
                        else:
                            tabs = ["all", "close", "ranged", "siege", "agile", "legendary", "special", "weather", "neutral"]
                            idx = tabs.index(self.current_tab) if self.current_tab in tabs else 0
                            self.current_tab = tabs[(idx - 1) % len(tabs)]
                            self.pool_scroll_offset = 0
                            self.keyboard_pool_cursor = 0

                    elif event.key in [pygame.K_DOWN, pygame.K_s]:
                        if self.keyboard_focus == "deck" and self.deck_preview_ids:
                            unique_count = len(set(self.deck_preview_ids))
                            if unique_count > 0:
                                self.keyboard_deck_cursor = (self.keyboard_deck_cursor + 1) % unique_count
                        else:
                            tabs = ["all", "close", "ranged", "siege", "agile", "legendary", "special", "weather", "neutral"]
                            idx = tabs.index(self.current_tab) if self.current_tab in tabs else 0
                            self.current_tab = tabs[(idx + 1) % len(tabs)]
                            self.pool_scroll_offset = 0
                            self.keyboard_pool_cursor = 0

                    elif event.key in [pygame.K_f, pygame.K_RETURN] and self.keyboard_focus == "pool":
                        if pool_ids and 0 <= self.keyboard_pool_cursor < len(pool_ids):
                            if self.deck_preview_ids is None:
                                self.deck_preview_ids = []
                            self.deck_preview_ids.append(pool_ids[self.keyboard_pool_cursor])

                    elif event.key in [pygame.K_DELETE, pygame.K_BACKSPACE] and self.keyboard_focus == "deck":
                        if self.deck_preview_ids and self.keyboard_deck_cursor >= 0:
                            from collections import Counter
                            unique_ids = sorted(list(set(self.deck_preview_ids)), key=lambda x: (ALL_CARDS[x].row, -ALL_CARDS[x].power))
                            if self.keyboard_deck_cursor < len(unique_ids):
                                self.deck_preview_ids.remove(unique_ids[self.keyboard_deck_cursor])
                                if self.keyboard_deck_cursor >= len(set(self.deck_preview_ids)):
                                    self.keyboard_deck_cursor = max(0, len(set(self.deck_preview_ids)) - 1)

                    elif event.key == pygame.K_SPACE:
                        if self.inspected_card_id:
                            self.inspected_card_id = None
                        elif self.keyboard_focus == "pool" and pool_ids and 0 <= self.keyboard_pool_cursor < len(pool_ids):
                            self.inspected_card_id = pool_ids[self.keyboard_pool_cursor]
                        elif self.keyboard_focus == "deck" and self.deck_preview_ids:
                            unique_ids = sorted(list(set(self.deck_preview_ids)), key=lambda x: (ALL_CARDS[x].row, -ALL_CARDS[x].power))
                            if 0 <= self.keyboard_deck_cursor < len(unique_ids):
                                self.inspected_card_id = unique_ids[self.keyboard_deck_cursor]
            
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
                # Back button in faction select (only for standalone deck builder)
                if not self.for_new_game and self.back_button.collidepoint(mouse_pos):
                    self.return_to_menu = True
                    return
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
            
            # Deck review - NEW LAYOUT (Bottom Accordion + Right Deck List)
            elif self.state == "deck_review":
                # Check filter button clicks
                if event.button == 1 and self.filter_rects:
                    for kw, rect in self.filter_rects.items():
                        if rect.collidepoint(mouse_pos):
                            if kw == "CLEAR":
                                self.keyword_filter = None
                            elif self.keyword_filter == kw:
                                self.keyword_filter = None  # Toggle off
                            else:
                                self.keyword_filter = kw
                            self.pool_scroll_offset = 0
                            return

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
                        else:
                            # Go back to faction select, not main menu
                            self.save_current_deck("Deck saved")
                            self.state = "faction_select"
                            self.selected_faction = None
                            self.selected_leader = None
                        self.deck_scroll_offset = 0
                        self.inspected_card_id = None
                        self.keyboard_pool_cursor = -1
                        self.keyboard_deck_cursor = -1
                        return
                    
                    if self.for_new_game and self.continue_button.collidepoint(mouse_pos):
                        self.save_current_deck("Deck saved before starting the game")
                        self.state = "complete"
                        return
                    
                    if not self.for_new_game and self.save_button.collidepoint(mouse_pos):
                        self.save_current_deck()
                        return
                
                # RIGHT CLICK = ZOOM/INSPECT (works on accordion and deck list)
                if event.button == 3:  # Right click
                    # Close inspection if already open
                    if self.inspected_card_id:
                        self.inspected_card_id = None
                        return
                    
                    # Check cards in Bottom Accordion
                    if self.accordion_area_rect.collidepoint(mouse_pos):
                        pool_ids = get_cards_by_type_and_strength(self.card_pool_ids, self.current_tab, self.keyword_filter)
                        card_w, card_h = 160, 240
                        spacing = 15
                        start_x = 40 - self.pool_scroll_offset
                        card_y = self.accordion_area_rect.y + 60
                        
                        for i, card_id in enumerate(pool_ids):
                            card_x = start_x + i * (card_w + spacing)
                            if card_x + card_w < 0 or card_x > self.screen_width:
                                continue
                            card_rect = pygame.Rect(card_x, card_y, card_w, card_h)
                            if card_rect.collidepoint(mouse_pos):
                                self.inspected_card_id = card_id
                                return
                    
                    # Check cards in Deck List (right panel) - right-click on list item
                    elif self.deck_list_rect.collidepoint(mouse_pos) and self.deck_preview_ids:
                        from collections import Counter
                        counts = Counter(self.deck_preview_ids)
                        unique_ids = sorted(list(counts.keys()), key=lambda x: (ALL_CARDS[x].row, -ALL_CARDS[x].power))
                        
                        row_height = 38
                        y_offset = self.deck_list_rect.y + 15 - self.deck_scroll_offset
                        
                        for cid in unique_ids:
                            row_rect = pygame.Rect(
                                self.deck_list_rect.x + 8, 
                                y_offset, 
                                self.deck_list_rect.width - 16, 
                                row_height - 4
                            )
                            if row_rect.collidepoint(mouse_pos):
                                self.inspected_card_id = cid
                                return
                            y_offset += row_height
                    return
                
                # LEFT CLICK = DRAG or REMOVE (only if not inspecting)
                if event.button == 1 and not self.inspected_card_id:
                    # First check for remove button clicks in deck list
                    if hasattr(self, 'deck_remove_buttons') and self.deck_remove_buttons:
                        for card_id, btn_rect in self.deck_remove_buttons.items():
                            if btn_rect.collidepoint(mouse_pos):
                                # Remove card from deck
                                if card_id in self.deck_preview_ids:
                                    self.deck_preview_ids.remove(card_id)
                                return

                    # Check cards in Bottom Accordion (drag to add to deck)
                    if self.accordion_area_rect.collidepoint(mouse_pos):
                        pool_ids = get_cards_by_type_and_strength(self.card_pool_ids, self.current_tab, self.keyword_filter)
                        card_w, card_h = 160, 240
                        spacing = 15
                        start_x = 40 - self.pool_scroll_offset
                        card_y = self.accordion_area_rect.y + 60
                        
                        for i, card_id in enumerate(pool_ids):
                            card_x = start_x + i * (card_w + spacing)
                            if card_x + card_w < 0 or card_x > self.screen_width:
                                continue
                            # Account for lift animation
                            lift = self.accordion_lift_amount.get(card_id, 0)
                            card_rect = pygame.Rect(card_x, card_y - int(lift), card_w, card_h)
                            if card_rect.collidepoint(mouse_pos):
                                # Start dragging from pool
                                self.dragging_card = card_id
                                self.drag_from_pool = True
                                self.drag_current_x = mouse_pos[0]
                                self.drag_current_y = mouse_pos[1]
                                self.drag_target_x = mouse_pos[0]
                                self.drag_target_y = mouse_pos[1]
                                return

                    # Check Deck List (clicking on a row could start drag to remove)
                    elif self.deck_list_rect.collidepoint(mouse_pos) and self.deck_preview_ids:
                        from collections import Counter
                        counts = Counter(self.deck_preview_ids)
                        unique_ids = sorted(list(counts.keys()), key=lambda x: (ALL_CARDS[x].row, -ALL_CARDS[x].power))
                        
                        row_height = 38
                        y_offset = self.deck_list_rect.y + 15 - self.deck_scroll_offset
                        
                        for cid in unique_ids:
                            row_rect = pygame.Rect(
                                self.deck_list_rect.x + 8, 
                                y_offset, 
                                self.deck_list_rect.width - 16, 
                                row_height - 4
                            )
                            if row_rect.collidepoint(mouse_pos):
                                # Start dragging from deck
                                self.dragging_card = cid
                                self.drag_from_pool = False
                                self.drag_current_x = mouse_pos[0]
                                self.drag_current_y = mouse_pos[1]
                                self.drag_target_x = mouse_pos[0]
                                self.drag_target_y = mouse_pos[1]
                                return
                            y_offset += row_height
                
    
    def update(self, delta_time=0.016):
        """Update animations and smooth movement (delta_time in seconds)."""
        # Smooth card drag position using lerp
        if self.dragging_card:
            # Lerp toward target position for smooth movement
            self.drag_current_x += (self.drag_target_x - self.drag_current_x) * self.drag_smoothing
            self.drag_current_y += (self.drag_target_y - self.drag_current_y) * self.drag_smoothing

    def draw(self, surface):
        """Draw the deck builder UI."""
        # Update smooth animations
        self.update()

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
        
        # Draw dragging card (follows mouse smoothly)
        if self.dragging_card:
            card = ALL_CARDS[self.dragging_card]
            card_width = 130  # Slightly larger when dragging
            card_height = 195

            # Draw shadow behind card for depth
            shadow_offset = 8
            shadow_surf = pygame.Surface((card_width + 10, card_height + 10), pygame.SRCALPHA)
            pygame.draw.rect(shadow_surf, (0, 0, 0, 80), shadow_surf.get_rect(), border_radius=10)
            surface.blit(shadow_surf, (int(self.drag_current_x) - card_width // 2 + shadow_offset,
                                      int(self.drag_current_y) - card_height // 2 + shadow_offset))

            # Draw card image
            scaled_image = pygame.transform.scale(card.image, (card_width, card_height))
            scaled_image.set_alpha(240)  # Slightly transparent
            surface.blit(scaled_image, (int(self.drag_current_x) - card_width // 2,
                                       int(self.drag_current_y) - card_height // 2))

            # Glowing border to show it's being dragged
            card_rect = pygame.Rect(int(self.drag_current_x) - card_width // 2,
                                   int(self.drag_current_y) - card_height // 2,
                                   card_width, card_height)
            pygame.draw.rect(surface, (255, 220, 100), card_rect, width=4, border_radius=8)
            pygame.draw.rect(surface, (255, 255, 150), card_rect, width=2, border_radius=8)
        
        # Draw inspected card overlay (on top of everything)
        if self.inspected_card_id:
            card = ALL_CARDS[self.inspected_card_id]
            self.draw_card_inspection(surface, card)
    
    def draw_faction_select(self, surface):
        """Draw faction selection screen."""
        # Back button (only for standalone deck builder)
        if not self.for_new_game:
            self.draw_back_button(surface)

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
        
        # Back button (DHD style)
        self.back_button = board_renderer.draw_dhd_back_button(surface, 20, 20, 80)

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
    
    def draw_filter_buttons(self, surface, x, y):
        """Draw keyword filter buttons."""
        filters = ["Spy", "Medic", "Hero", "Bond", "Muster", "Scorch"]
        button_width = 70
        button_height = 30
        spacing = 8
        self.filter_rects = {}
        
        # Label
        label = self.small_font.render("Filter:", True, (180, 180, 180))
        surface.blit(label, (x, y + 5))
        current_x = x + 60
        
        for kw in filters:
            rect = pygame.Rect(current_x, y, button_width, button_height)
            is_active = (self.keyword_filter == kw)
            
            # Draw button
            color = (100, 200, 100) if is_active else (60, 60, 70)
            pygame.draw.rect(surface, color, rect, border_radius=15)
            pygame.draw.rect(surface, (200, 200, 200), rect, width=1, border_radius=15)
            
            # Text
            text = self.small_font.render(kw, True, (255, 255, 255))
            text_rect = text.get_rect(center=rect.center)
            surface.blit(text, text_rect)
            
            self.filter_rects[kw] = rect
            current_x += button_width + spacing
            
        # Clear button if filter active
        if self.keyword_filter:
            clear_rect = pygame.Rect(current_x, y, 25, 25)
            pygame.draw.circle(surface, (200, 50, 50), clear_rect.center, 12)
            x_text = self.small_font.render("X", True, (255, 255, 255))
            surface.blit(x_text, x_text.get_rect(center=clear_rect.center))
            self.filter_rects["CLEAR"] = clear_rect

    def draw_deck_review(self, surface):
        """Draw the new High-End Witcher-style Deck Builder UI."""
        # Clear remove button positions from previous frame
        self.deck_remove_buttons = {}

        # 1. Background
        if self.deck_building_bg:
            surface.blit(self.deck_building_bg, (0, 0))
        elif self.selected_faction:
            surface.fill(self.faction_bg_colors.get(self.selected_faction, self.bg_color))
        else:
            surface.fill(self.bg_color)
        
        faction_color = self.faction_colors.get(self.selected_faction, self.highlight_color)

        # 2. Top Navigation & Tabs
        self.draw_card_type_tabs(surface, faction_color)
        self.draw_back_button(surface)

        # 3. Top Left Stats Box ("Holographic UI")
        self.draw_stats_hologram(surface, faction_color)

        # 4. Right Side Deck List (Text-based with right-click preview)
        self.draw_vertical_deck_list(surface, faction_color)

        # 5. Bottom Accordion Card Pool (2x Sized Cards)
        self.draw_bottom_accordion(surface, faction_color)

        # 6. Save/Action Buttons (positioned above accordion)
        if self.for_new_game:
            # START GAME button - positioned above accordion on the right
            start_btn_rect = pygame.Rect(
                self.screen_width - 220, 
                self.accordion_area_rect.top - 70, 
                200, 50
            )
            pygame.draw.rect(surface, (50, 200, 50), start_btn_rect, border_radius=8)
            pygame.draw.rect(surface, (100, 255, 100), start_btn_rect, width=2, border_radius=8)
            start_text = self.button_font.render("START GAME", True, (255, 255, 255))
            surface.blit(start_text, start_text.get_rect(center=start_btn_rect.center))
            self.continue_button = start_btn_rect
        else:
            # SAVE DECK button
            pygame.draw.rect(surface, (50, 180, 50), self.save_button, border_radius=8)
            pygame.draw.rect(surface, (100, 255, 100), self.save_button, width=2, border_radius=8)
            save_text = self.button_font.render("SAVE DECK", True, (255, 255, 255))
            surface.blit(save_text, save_text.get_rect(center=self.save_button.center))
            
            # Show temporary confirmation message near the save button
            if self.last_save_message and pygame.time.get_ticks() - self.last_save_time < 3000:
                confirm_text = self.small_font.render(self.last_save_message, True, (200, 255, 200))
                confirm_rect = confirm_text.get_rect(midtop=(self.save_button.centerx, self.save_button.bottom + 10))
                surface.blit(confirm_text, confirm_rect)
        
        # Instructions at bottom of deck list area
        if self.inspected_card_id:
            instructions = self.small_font.render("Press SPACE or Click to close", True, (255, 255, 100))
            inst_rect = instructions.get_rect(midbottom=(self.deck_list_rect.centerx, self.deck_list_rect.bottom - 10))
            surface.blit(instructions, inst_rect)

    def draw_back_button(self, surface):
        """Draws a DHD-style back button (Top Left)."""
        self.back_button = board_renderer.draw_dhd_back_button(surface, 20, 20, 80)

    def draw_stats_hologram(self, surface, faction_color):
        """Draws a cool, translucent stats box in the top left."""
        # Backdrop with transparency
        s = pygame.Surface((self.stats_box_rect.width, self.stats_box_rect.height), pygame.SRCALPHA)
        pygame.draw.rect(s, (20, 30, 50, 200), s.get_rect(), border_radius=15)
        pygame.draw.rect(s, faction_color, s.get_rect(), width=3, border_radius=15)
        surface.blit(s, self.stats_box_rect.topleft)

        # Title with glow effect
        title = self.subtitle_font.render("DECK STATS", True, self.highlight_color)
        surface.blit(title, (self.stats_box_rect.x + 20, self.stats_box_rect.y + 10))
        
        # Calculate stats
        deck_cards = [ALL_CARDS[id] for id in (self.deck_preview_ids or [])]
        unit_count = len([c for c in deck_cards if c.row in ["close", "ranged", "siege", "agile"]])
        special_count = len([c for c in deck_cards if c.row == "special"])
        weather_count = len([c for c in deck_cards if c.row == "weather"])
        neutral_count = len([c for c in deck_cards if c.faction == FACTION_NEUTRAL])
        total_power = sum(c.power for c in deck_cards if c.row not in ["special", "weather"])
        
        # Deck validity check
        is_valid, status_msg = validate_deck(deck_cards)
        
        # Check for Mercenary Tax (Neutral Penalty)
        mercenary_tax = False
        if len(deck_cards) > 0 and neutral_count > len(deck_cards) / 2:
            mercenary_tax = True
        
        stats = [
            (f"Total Cards: {len(deck_cards)} / {MAX_DECK_SIZE}", (255, 255, 255)),
            (f"Unit Cards: {unit_count} (Min 15)", (100, 255, 100) if unit_count >= 15 else (255, 100, 100)),
            (f"Spec: {special_count} | Weath: {weather_count} | Neut: {neutral_count}", (200, 200, 200)),
            (f"Total Strength: {total_power}", (255, 215, 0)),
        ]
        
        if mercenary_tax:
            stats.append(("! MERCENARY TAX ACTIVE !", (255, 50, 50)))
            stats.append(("(-25% Final Score)", (255, 100, 100)))

        y_offset = self.stats_box_rect.y + 55
        for text, color in stats:
            txt_surf = self.stat_font.render(text, True, color)
            surface.blit(txt_surf, (self.stats_box_rect.x + 20, y_offset))
            y_offset += 28
        
        # Status indicator
        status_color = (100, 255, 100) if is_valid else (255, 100, 100)
        status_icon = "✓" if is_valid else "!"
        status_surf = self.stat_font.render(f"{status_icon} {status_msg}", True, status_color)
        surface.blit(status_surf, (self.stats_box_rect.x + 20, y_offset + 5))

    def draw_vertical_deck_list(self, surface, faction_color):
        """Draws a sleek vertical list of card names on the right side."""
        # Panel Background with transparency
        panel_surf = pygame.Surface((self.deck_list_rect.width, self.deck_list_rect.height), pygame.SRCALPHA)
        pygame.draw.rect(panel_surf, (15, 18, 25, 220), panel_surf.get_rect(), border_radius=12)
        surface.blit(panel_surf, self.deck_list_rect.topleft)
        pygame.draw.rect(surface, faction_color, self.deck_list_rect, width=3, border_radius=12)
        
        # Header
        header = self.subtitle_font.render("YOUR REGIMENT", True, faction_color)
        surface.blit(header, (self.deck_list_rect.x + 15, self.deck_list_rect.y - 45))
        
        # Card count badge
        if self.deck_preview_ids:
            count_text = self.button_font.render(f"{len(self.deck_preview_ids)}", True, (255, 255, 255))
            count_bg = pygame.Rect(self.deck_list_rect.right - 50, self.deck_list_rect.y - 40, 40, 30)
            pygame.draw.rect(surface, faction_color, count_bg, border_radius=8)
            surface.blit(count_text, count_text.get_rect(center=count_bg.center))

        if not self.deck_preview_ids:
            empty_text = self.desc_font.render("Drag cards here...", True, (100, 100, 100))
            surface.blit(empty_text, empty_text.get_rect(center=self.deck_list_rect.center))
            return

        # Sort and group cards
        from collections import Counter
        counts = Counter(self.deck_preview_ids)
        unique_ids = sorted(list(counts.keys()), key=lambda x: (ALL_CARDS[x].row, -ALL_CARDS[x].power))

        # Create clip rect for scrolling
        clip_rect = pygame.Rect(
            self.deck_list_rect.x + 5, 
            self.deck_list_rect.y + 10, 
            self.deck_list_rect.width - 10, 
            self.deck_list_rect.height - 20
        )
        surface.set_clip(clip_rect)

        row_height = 38
        y_offset = self.deck_list_rect.y + 15 - self.deck_scroll_offset
        mouse_pos = pygame.mouse.get_pos()

        for idx, cid in enumerate(unique_ids):
            card = ALL_CARDS[cid]
            row_rect = pygame.Rect(
                self.deck_list_rect.x + 8,
                y_offset,
                self.deck_list_rect.width - 16,
                row_height - 4
            )

            # Skip if outside visible area
            if row_rect.bottom < self.deck_list_rect.y or row_rect.top > self.deck_list_rect.bottom:
                y_offset += row_height
                continue

            # Check if this card is keyboard-selected
            is_keyboard_selected = (self.keyboard_focus == "deck" and
                                   self.keyboard_deck_cursor == idx)

            # Hover or keyboard selection effect
            is_hovered = row_rect.collidepoint(mouse_pos) and self.deck_list_rect.collidepoint(mouse_pos)
            if is_hovered or is_keyboard_selected:
                # Use cyan for keyboard selection, faction color for hover
                highlight_color = (0, 200, 255) if is_keyboard_selected and not is_hovered else faction_color
                hover_color = (*highlight_color[:3], 80)
                hover_surf = pygame.Surface((row_rect.width, row_rect.height), pygame.SRCALPHA)
                pygame.draw.rect(hover_surf, hover_color, hover_surf.get_rect(), border_radius=6)
                surface.blit(hover_surf, row_rect.topleft)
                pygame.draw.rect(surface, highlight_color, row_rect, width=2 if is_keyboard_selected else 1, border_radius=6)
                if is_hovered:
                    self.hovered_card_id = cid
            
            # Row type color indicator (left edge)
            row_colors = {
                "close": (200, 50, 50),
                "ranged": (50, 150, 200),
                "siege": (200, 150, 50),
                "agile": (100, 200, 100),
                "special": (180, 100, 200),
                "weather": (100, 100, 150)
            }
            indicator_color = row_colors.get(card.row, (100, 100, 100))
            indicator_rect = pygame.Rect(row_rect.x, row_rect.y + 4, 4, row_rect.height - 8)
            pygame.draw.rect(surface, indicator_color, indicator_rect, border_radius=2)
            
            # Power Icon (circle)
            if card.row not in ["special", "weather"]:
                power_center = (row_rect.x + 25, row_rect.centery)
                pygame.draw.circle(surface, (0, 0, 0), power_center, 14)
                pygame.draw.circle(surface, self.highlight_color, power_center, 14, width=2)
                pwr_txt = self.small_font.render(str(card.power), True, (255, 255, 255))
                surface.blit(pwr_txt, pwr_txt.get_rect(center=power_center))
                name_x = row_rect.x + 48
            else:
                # Special/Weather icon
                icon_text = "★" if card.row == "special" else "☁"
                icon_surf = self.small_font.render(icon_text, True, indicator_color)
                surface.blit(icon_surf, (row_rect.x + 15, row_rect.centery - 10))
                name_x = row_rect.x + 40
            
            # Card Name (truncated if too long)
            max_name_width = row_rect.width - 100
            name_txt = self.small_font.render(card.name, True, (255, 255, 255))
            if name_txt.get_width() > max_name_width:
                # Truncate name
                truncated = card.name
                while self.small_font.size(truncated + "...")[0] > max_name_width and len(truncated) > 3:
                    truncated = truncated[:-1]
                name_txt = self.small_font.render(truncated + "...", True, (255, 255, 255))
            surface.blit(name_txt, (name_x, row_rect.centery - 10))
            
            # Quantity badge (right side)
            if counts[cid] > 1:
                qty_txt = self.small_font.render(f"x{counts[cid]}", True, faction_color)
                surface.blit(qty_txt, (row_rect.right - 35, row_rect.centery - 10))
            
            # Quick remove button on hover
            if is_hovered:
                remove_btn = pygame.Rect(row_rect.right - 25, row_rect.centery - 10, 20, 20)
                pygame.draw.rect(surface, (180, 50, 50), remove_btn, border_radius=4)
                x_txt = self.small_font.render("×", True, (255, 255, 255))
                surface.blit(x_txt, x_txt.get_rect(center=remove_btn.center))
                self.deck_remove_buttons[cid] = remove_btn
            
            y_offset += row_height

        surface.set_clip(None)

    def draw_bottom_accordion(self, surface, faction_color):
        """Draws the 2x size cards in a horizontal accordion at the bottom."""
        # Background strip with gradient effect
        strip_bg = pygame.Surface((self.screen_width, self.accordion_area_rect.height), pygame.SRCALPHA)
        
        # Create gradient from transparent to opaque
        for i in range(50):
            alpha = int(i * 5)
            pygame.draw.line(strip_bg, (0, 0, 0, alpha), 
                           (0, i), (self.screen_width, i))
        strip_bg.fill((10, 12, 18, 230), pygame.Rect(0, 50, self.screen_width, self.accordion_area_rect.height - 50))
        surface.blit(strip_bg, self.accordion_area_rect.topleft)
        
        # Top border line (glowing effect)
        pygame.draw.line(surface, faction_color, 
                        (0, self.accordion_area_rect.top), 
                        (self.screen_width, self.accordion_area_rect.top), 3)
        
        # Filter and sort pool cards
        pool_ids = get_cards_by_type_and_strength(self.card_pool_ids, self.current_tab, self.keyword_filter)
        
        if not pool_ids:
            no_cards_txt = self.desc_font.render("No cards match current filter", True, (100, 100, 100))
            surface.blit(no_cards_txt, no_cards_txt.get_rect(center=self.accordion_area_rect.center))
            return
        
        # 2x Size dimensions
        card_w, card_h = 160, 240
        spacing = 15
        lift_amount = 25  # How much cards lift on hover
        
        # Calculate starting position with scroll offset
        start_x = 40 - self.pool_scroll_offset
        card_y = self.accordion_area_rect.y + 60

        mouse_pos = pygame.mouse.get_pos()
        
        for i, cid in enumerate(pool_ids):
            card = ALL_CARDS[cid]
            card_x = start_x + i * (card_w + spacing)
            
            # Only process cards that are potentially visible
            if card_x + card_w < -50 or card_x > self.screen_width + 50:
                continue
            
            target_rect = pygame.Rect(card_x, card_y, card_w, card_h)

            # Check if this card is keyboard-selected (need this before lift animation)
            is_keyboard_selected = (self.keyboard_focus == "pool" and
                                   self.keyboard_pool_cursor == i)

            # Hover detection and lift animation
            is_hovered = target_rect.collidepoint(mouse_pos) and self.accordion_area_rect.collidepoint(mouse_pos)

            # Smooth lift animation (lift on hover OR keyboard selection)
            current_lift = self.accordion_lift_amount.get(cid, 0)
            target_lift = lift_amount if (is_hovered or is_keyboard_selected) else 0
            new_lift = current_lift + (target_lift - current_lift) * 0.3
            self.accordion_lift_amount[cid] = new_lift

            draw_y = card_y - int(new_lift)
            
            # Draw card shadow
            shadow_offset = 5 + int(new_lift * 0.3)
            shadow_surf = pygame.Surface((card_w + 10, card_h + 10), pygame.SRCALPHA)
            pygame.draw.rect(shadow_surf, (0, 0, 0, 100), shadow_surf.get_rect(), border_radius=10)
            surface.blit(shadow_surf, (card_x - 5 + shadow_offset, draw_y + shadow_offset))
            
            # Draw card image (cached for performance)
            large_img = self._get_scaled_card_image(card, card_w, card_h)
            if large_img:
                surface.blit(large_img, (card_x, draw_y))
            else:
                pygame.draw.rect(surface, (60, 60, 70), pygame.Rect(card_x, draw_y, card_w, card_h), border_radius=8)

            # Border (glowing on hover or keyboard selection)
            if is_hovered or is_keyboard_selected:
                # Outer glow - use cyan for keyboard, yellow for hover
                glow_color = (0, 200, 255) if is_keyboard_selected and not is_hovered else self.highlight_color
                glow_rect = pygame.Rect(card_x - 4, draw_y - 4, card_w + 8, card_h + 8)
                pygame.draw.rect(surface, glow_color, glow_rect, width=4, border_radius=12)
                if is_hovered:
                    self.accordion_hover_card_id = cid
            else:
                pygame.draw.rect(surface, (100, 100, 100), pygame.Rect(card_x, draw_y, card_w, card_h), width=2, border_radius=8)
            
            # Power badge (top-left corner)
            if card.row not in ["special", "weather"]:
                badge_center = (card_x + 25, draw_y + 25)
                pygame.draw.circle(surface, (0, 0, 0), badge_center, 20)
                pygame.draw.circle(surface, faction_color, badge_center, 20, width=3)
                p_text = self.button_font.render(str(card.power), True, (255, 255, 255))
                surface.blit(p_text, p_text.get_rect(center=badge_center))
            
            # Card name below (if hovered or keyboard selected)
            if is_hovered or is_keyboard_selected:
                name_bg = pygame.Surface((card_w + 20, 30), pygame.SRCALPHA)
                name_bg.fill((0, 0, 0, 180))
                surface.blit(name_bg, (card_x - 10, draw_y + card_h + 5))

                name_color = (0, 200, 255) if is_keyboard_selected and not is_hovered else (255, 255, 255)
                name_txt = self.small_font.render(card.name, True, name_color)
                name_rect = name_txt.get_rect(center=(card_x + card_w // 2, draw_y + card_h + 20))
                surface.blit(name_txt, name_rect)
        
        # Draw scroll indicators
        if self.pool_scroll_offset > 0:
            # Left arrow
            arrow_surf = self.subtitle_font.render("◀", True, faction_color)
            surface.blit(arrow_surf, (10, self.accordion_area_rect.centery - 20))
        
        max_scroll = max(0, len(pool_ids) * (card_w + spacing) - self.screen_width + 80)
        if self.pool_scroll_offset < max_scroll:
            # Right arrow
            arrow_surf = self.subtitle_font.render("▶", True, faction_color)
            surface.blit(arrow_surf, (self.screen_width - 35, self.accordion_area_rect.centery - 20))
        
        # Pool count indicator
        count_text = self.small_font.render(f"Pool: {len(pool_ids)} cards", True, (180, 180, 180))
        surface.blit(count_text, (20, self.accordion_area_rect.top + 15))


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
        
        # Draw card image (cached for performance)
        large_card_image = self._get_scaled_card_image(card, card_display_width, card_display_height)
        if large_card_image:
            surface.blit(large_card_image, (card_x, card_y))
        else:
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
        """Draw hover preview card - positioned above the hovered card in accordion or next to deck list."""
        if not self.hovered_card_id:
            return

        card = ALL_CARDS[self.hovered_card_id]
        
        # Preview card dimensions (larger for detail)
        preview_card_width = 200
        preview_card_height = 300
        text_area_height = 100
        total_height = preview_card_height + text_area_height

        # Position: Center above the stats box for deck list hover
        # or in a floating panel for accordion hover
        preview_x = self.stats_box_rect.right + 20
        preview_y = self.stats_box_rect.y

        # Draw semi-transparent background
        bg_surface = pygame.Surface((preview_card_width + 20, total_height + 20), pygame.SRCALPHA)
        bg_surface.fill((15, 18, 25, 240))
        surface.blit(bg_surface, (preview_x - 10, preview_y - 10))
        
        # Border
        border_rect = pygame.Rect(preview_x - 10, preview_y - 10, preview_card_width + 20, total_height + 20)
        faction_color = self.faction_colors.get(self.selected_faction, self.highlight_color)
        pygame.draw.rect(surface, faction_color, border_rect, width=3, border_radius=12)

        # Draw the card image scaled to preview size
        try:
            scaled_image = pygame.transform.scale(card.image, (preview_card_width, preview_card_height))
            surface.blit(scaled_image, (preview_x, preview_y))
        except:
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
        pygame.draw.rect(surface, border_color, pygame.Rect(preview_x, preview_y, preview_card_width, preview_card_height), width=3, border_radius=8)

        # Draw power overlay for unit cards
        if card.row not in ["special", "weather"]:
            power_text = self.power_font.render(str(card.power), True, (255, 255, 255))
            power_rect = power_text.get_rect(center=(preview_x + preview_card_width // 2, preview_y + preview_card_height - 20))
            bg_rect = power_rect.inflate(12, 6)
            pygame.draw.rect(surface, (0, 0, 0), bg_rect, border_radius=3)
            surface.blit(power_text, power_rect)

        # Text Info Below Image
        text_start_y = preview_y + preview_card_height + 8
        center_x = preview_x + preview_card_width // 2

        # Card Name
        name_text = self.preview_name_font.render(card.name, True, (255, 215, 0))
        name_rect = name_text.get_rect(center=(center_x, text_start_y + 10))
        surface.blit(name_text, name_rect)

        # Row / Type
        row_str = card.row.capitalize()
        if card.row == "close": row_str = "Melee"
        elif card.row == "ranged": row_str = "Ranged"
        elif card.row == "siege": row_str = "Siege"

        type_text = self.preview_type_font.render(f"{row_str} • {card.faction}", True, (180, 180, 180))
        type_rect = type_text.get_rect(center=(center_x, text_start_y + 30))
        surface.blit(type_text, type_rect)

        # Ability Description (truncated)
        if card.ability:
            ability_text = card.ability[:40] + "..." if len(card.ability) > 40 else card.ability
            ability_surf = self.preview_desc_font.render(ability_text, True, (200, 200, 200))
            ability_rect = ability_surf.get_rect(center=(center_x, text_start_y + 50))
            surface.blit(ability_surf, ability_rect)

    def draw_card_type_tabs(self, surface, faction_color):
        """Draw tabs for filtering cards by type."""
        tabs = [
            ("All", "all"),
            ("Close", "close"),
            ("Ranged", "ranged"),
            ("Siege", "siege"),
            ("Agile", "agile"),
            ("Legendary", "legendary"),
            ("Special", "special"),
            ("Weather", "weather"),
            ("Neutral", "neutral")
        ]
        
        tab_radius = 38
        tab_diameter = tab_radius * 2
        tab_spacing = 10
        total_width = len(tabs) * tab_diameter + (len(tabs) - 1) * tab_spacing
        start_x = (self.screen_width - total_width) // 2
        tab_y = 80  # Center Y coordinate
        
        self.tab_rects = {}
        
        mouse_pos = pygame.mouse.get_pos()
        
        for i, (label, tab_type) in enumerate(tabs):
            center_x = start_x + i * (tab_diameter + tab_spacing) + tab_radius
            center = (center_x, tab_y)
            
            # Bounding box for clicks (used in event loop)
            tab_rect = pygame.Rect(center_x - tab_radius, tab_y - tab_radius, tab_diameter, tab_diameter)
            self.tab_rects[tab_type] = tab_rect
            
            is_hovered = tab_rect.collidepoint(mouse_pos)
            
            # Color based on selection
            if self.current_tab == tab_type:
                bg_color = faction_color
                border_color = (255, 255, 255)
                # Draw outer glow for selection
                pygame.draw.circle(surface, (255, 255, 255), center, tab_radius + 4, width=3)
            else:
                bg_color = (30, 35, 50)
                border_color = (80, 80, 90)
                if is_hovered:
                    border_color = (220, 220, 220)
                    bg_color = (50, 55, 70)
            
            # Draw circle background
            pygame.draw.circle(surface, bg_color, center, tab_radius)
            
            # Draw content (Icon or Text)
            if hasattr(self, 'tab_icons') and tab_type in self.tab_icons:
                icon = self.tab_icons[tab_type]
                # Scale icon to FILL the circle entirely
                icon_size = tab_diameter
                scaled_icon = pygame.transform.smoothscale(icon, (icon_size, icon_size))
                icon_rect = scaled_icon.get_rect(center=center)
                surface.blit(scaled_icon, icon_rect)
            else:
                # Fallback to text if icon missing
                short_label = label[:3]
                label_text = self.small_font.render(short_label, True, (200, 200, 200))
                label_rect = label_text.get_rect(center=center)
                surface.blit(label_text, label_rect)
            
            # Draw border on top of icon for consistent look
            pygame.draw.circle(surface, border_color, center, tab_radius, width=2)
            
            # Draw tooltip if hovered
            if is_hovered:
                text = self.small_font.render(label, True, (255, 255, 255))
                text_rect = text.get_rect(midtop=(center_x, tab_y + tab_radius + 8))
                
                # Small background for tooltip
                bg_rect = text_rect.inflate(10, 4)
                pygame.draw.rect(surface, (20, 20, 25), bg_rect, border_radius=4)
                pygame.draw.rect(surface, (100, 100, 100), bg_rect, width=1, border_radius=4)
                
                surface.blit(text, text_rect)
    
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
        and not is_hero(card)
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


def get_cards_by_type_and_strength(card_id_list, card_type=None, keyword=None):
    """
    Filter cards by type/keyword and sort by strength (power).
    card_type can be: 'close', 'ranged', 'siege', 'agile', 'special', 'weather', 'neutral', or None for all.
    keyword can be: 'Spy', 'Medic', 'Hero' (Legendary Commander), or None.
    Returns sorted list of card IDs.
    """
    filtered_ids = card_id_list
    
    # 1. Filter by Type
    if card_type and card_type != "all":
        if card_type == "neutral":
            filtered_ids = [id for id in filtered_ids if ALL_CARDS[id].faction == FACTION_NEUTRAL]
        elif card_type == "legendary":
            filtered_ids = [
                id for id in filtered_ids 
                if "legendary commander" in (ALL_CARDS[id].ability or "").lower() 
                or (ALL_CARDS[id].power >= 10 and ALL_CARDS[id].row not in ["special", "weather"])
            ]
        else:
            filtered_ids = [id for id in filtered_ids if ALL_CARDS[id].row == card_type]
    
    # 2. Filter by Keyword
    if keyword:
        keyword_lower = keyword.lower()
        new_filtered = []
        for id in filtered_ids:
            card = ALL_CARDS[id]
            ability = (card.ability or "").lower()
            
            match = False
            if keyword_lower == "hero":
                if "legendary commander" in ability or (card.power >= 10 and card.row not in ["special", "weather"]) or card.row == "special":
                    match = True
            elif keyword_lower == "spy":
                if "deep cover agent" in ability:
                    match = True
            elif keyword_lower == "medic":
                if "medical evac" in ability:
                    match = True
            elif keyword_lower == "bond":
                if "tactical formation" in ability:
                    match = True
            elif keyword_lower == "muster":
                if "gate reinforcement" in ability:
                    match = True
            elif keyword_lower == "scorch":
                if "naquadah overload" in ability:
                    match = True
            
            if match:
                new_filtered.append(id)
        filtered_ids = new_filtered
    
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
                    elif deck_builder.state == "deck_review" and deck_builder.inspected_card_id:
                        # Close inspection instead of exiting
                        deck_builder.inspected_card_id = None
                    else:
                        stop_faction_theme()
                        return None
                elif event.key == pygame.K_F11:
                    if toggle_fullscreen_callback:
                        toggle_fullscreen_callback()
                    else:
                        import display_manager; display_manager.toggle_fullscreen_mode()
                    reload_card_images()
                    screen = pygame.display.get_surface()
                    deck_builder.refresh_for_surface(screen)
                else:
                    # Pass other keyboard events to deck builder for navigation
                    deck_builder.handle_event(event)
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
        clock.tick(144)  # Higher FPS for buttery smooth card movement
    
    return None
