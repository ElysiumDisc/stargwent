"""
Deck Builder Menu System for Stargwent
Allows players to select a faction and build their deck before starting a game.
"""
import pygame
import random
from cards import (
    ALL_CARDS, FACTION_TAURI, FACTION_GOAULD, FACTION_JAFFA, 
    FACTION_LUCIAN, FACTION_ASGARD, FACTION_NEUTRAL, reload_card_images
)
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


class DeckBuilderUI:
    """Deck builder interface for selecting faction and leader."""
    
    def __init__(self, screen_width, screen_height, for_new_game=True):
        reload_card_images()
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.for_new_game = for_new_game  # Track if this is for new game or deck customization
        self.selected_faction = None
        self.selected_leader = None
        self.state = "faction_select"  # faction_select, leader_select, deck_review, complete
        self.deck_preview_ids = None
        self.custom_deck_ids = []  # Player's custom deck being built
        self.deck_scroll_offset = 0
        self.pool_scroll_offset = 0  # Separate scroll for card pool
        self.inspected_card_id = None  # Card being inspected with spacebar
        self.card_pool_ids = []  # Available cards for the faction
        self.current_tab = "close"  # Current card type tab: close, ranged, siege, agile, special, weather, all
        self.return_to_menu = False  # Flag for when user clicks MAIN MENU button
        
        # DRAG AND DROP STATE
        self.dragging_card = None  # Card ID being dragged
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.drag_from_pool = False  # True if dragging from pool, False if from deck
        
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
        self.leader_bg_images = {}  # Cache for loaded leader background images
        self.current_bg_image = None  # Currently displayed background image
        self.deck_building_bg = None  # Background for deck building view
        self.load_leader_backgrounds()
        self.load_deck_building_bg()
        
        # Layout
        self.setup_layout()
    
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
    
    def setup_leader_buttons(self):
        """Setup leader selection buttons based on selected faction."""
        self.leader_buttons = []
        if not self.selected_faction:
            return
        
        # Get base leaders for faction
        leaders = FACTION_LEADERS[self.selected_faction]
        
        # Get unlocked leaders for this faction from persistence
        persistence = get_persistence()
        all_leaders = list(leaders)  # Start with base leaders
        
        # Add unlocked leaders
        if self.selected_faction in UNLOCKABLE_LEADERS:
            for unlockable_leader in UNLOCKABLE_LEADERS[self.selected_faction]:
                if persistence.is_leader_unlocked(unlockable_leader['card_id']):
                    all_leaders.append(unlockable_leader)
        
        button_width = 400
        button_height = 150
        spacing = 30
        start_y = self.screen_height // 3
        
        for i, leader in enumerate(all_leaders):
            x = self.screen_width // 2 - button_width // 2
            y = start_y + i * (button_height + spacing)
            rect = pygame.Rect(x, y, button_width, button_height)
            self.leader_buttons.append({
                'rect': rect,
                'leader': leader,
                'hovered': False
            })
    
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
                
                # Update background based on hover (no images for faction select)
                if hovered_faction:
                    self.current_bg_image = None  # Clear any image
                    self.current_bg_color = self.faction_bg_colors.get(hovered_faction, self.bg_color)
                else:
                    self.current_bg_image = None  # Clear any image
                    self.current_bg_color = self.bg_color
            
            # Update hover states for leader buttons and change background
            elif self.state == "leader_select":
                hovered_leader = None
                for button in self.leader_buttons:
                    is_hovered = button['rect'].collidepoint(mouse_pos)
                    button['hovered'] = is_hovered
                    if is_hovered:
                        hovered_leader = button['leader'].get('card_id')
                
                # Update background based on hover - USE IMAGE if available
                if hovered_leader:
                    # Try to use leader background image first
                    if hovered_leader in self.leader_bg_images:
                        self.current_bg_image = self.leader_bg_images[hovered_leader]
                        self.current_bg_color = None  # Use image instead of color
                    else:
                        # Fallback to solid color
                        self.current_bg_image = None
                        self.current_bg_color = self.leader_bg_colors.get(hovered_leader, self.faction_bg_colors.get(self.selected_faction, self.bg_color))
                else:
                    # Fall back to faction color when not hovering any leader
                    self.current_bg_image = None
                    self.current_bg_color = self.faction_bg_colors.get(self.selected_faction, self.bg_color)
        
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
            # Legacy mouse wheel support (for older pygame versions)
            if event.button in [4, 5]:  # Mouse wheel up/down
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
                        # Determine which panel to scroll based on mouse position
                        mouse_pos = event.pos
                        divider_x = self.screen_width // 2
                        
                        if mouse_pos[0] < divider_x:
                            # Left panel (card pool) scroll
                            if event.button == 4:  # Scroll up
                                self.pool_scroll_offset = max(0, self.pool_scroll_offset - 50)
                            elif event.button == 5:  # Scroll down
                                self.pool_scroll_offset += 50
                        else:
                            # Right panel (deck) scroll
                            if event.button == 4:  # Scroll up
                                self.deck_scroll_offset = max(0, self.deck_scroll_offset - 50)
                            elif event.button == 5:  # Scroll down
                                self.deck_scroll_offset += 50
                return  # Don't process mouse wheel as clicks
            
            # Regular mouse clicks (button 1 = left click)
            mouse_pos = event.pos
        
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
                        if saved_leader_id:
                            # Find the leader object
                            for leader in FACTION_LEADERS[self.selected_faction]:
                                if leader['card_id'] == saved_leader_id:
                                    self.selected_leader = leader
                                    break
                        if not self.selected_leader:
                            # Default to first leader if none saved
                            self.selected_leader = FACTION_LEADERS[self.selected_faction][0]
                        
                        # Generate deck and go to review
                        self.deck_preview_ids = build_faction_deck(self.selected_faction, self.selected_leader)
                        self.card_pool_ids = get_faction_card_pool(self.selected_faction)
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
                        self.current_bg_color = self.faction_bg_colors.get(self.selected_faction, self.bg_color)
                        if self.for_new_game:
                            # NEW GAME: Go to leader selection
                            self.state = "leader_select"
                            self.setup_leader_buttons()
                        else:
                            # DECK BUILDING: Load saved leader and go directly to deck review
                            saved_leader_id = load_leader_choice(self.selected_faction)
                            if saved_leader_id:
                                # Find the leader object
                                for leader in FACTION_LEADERS[self.selected_faction]:
                                    if leader['card_id'] == saved_leader_id:
                                        self.selected_leader = leader
                                        break
                            if not self.selected_leader:
                                # Default to first leader if none saved
                                self.selected_leader = FACTION_LEADERS[self.selected_faction][0]
                            
                            # Generate deck and go to review
                            self.deck_preview_ids = build_faction_deck(self.selected_faction, self.selected_leader)
                            self.card_pool_ids = get_faction_card_pool(self.selected_faction)
                            self.state = "deck_review"
                            self.deck_scroll_offset = 0
                            self.pool_scroll_offset = 0
                        return
            
            # Leader selection (LEFT CLICK ONLY)
            elif self.state == "leader_select" and event.button == 1:
                # Back button
                if self.back_button.collidepoint(mouse_pos):
                    self.state = "faction_select"
                    self.selected_leader = None
                    self.deck_preview_ids = None
                    return
                
                # Leader buttons
                for button in self.leader_buttons:
                    if button['rect'].collidepoint(mouse_pos):
                        self.selected_leader = button['leader']
                        leader_id = self.selected_leader.get('card_id')
                        
                        # Update background to leader-specific IMAGE or color (persists after click)
                        if leader_id in self.leader_bg_images:
                            self.current_bg_image = self.leader_bg_images[leader_id]
                            self.current_bg_color = None
                        else:
                            self.current_bg_image = None
                            self.current_bg_color = self.leader_bg_colors.get(
                                leader_id,
                                self.faction_bg_colors.get(self.selected_faction, self.bg_color)
                            )
                        
                        # Generate deck preview
                        self.deck_preview_ids = build_faction_deck(self.selected_faction, self.selected_leader)
                        return
                
                # Review deck button
                if self.selected_leader and self.review_deck_button.collidepoint(mouse_pos):
                    self.state = "deck_review"
                    if not self.deck_preview_ids:
                        self.deck_preview_ids = build_faction_deck(self.selected_faction, self.selected_leader)
                    # Build card pool (all available cards for faction)
                    self.card_pool_ids = get_faction_card_pool(self.selected_faction)
                    self.deck_scroll_offset = 0
                    self.pool_scroll_offset = 0
                    return
                
                # Continue button (if leader selected)
                if self.selected_leader and self.continue_button.collidepoint(mouse_pos):
                    # Save the selected leader before completing
                    save_leader_choice(self.selected_faction, self.selected_leader['card_id'])
                    print(f"✓ Leader choice saved: {self.selected_faction} -> {self.selected_leader['name']}")
                    self.state = "complete"
                    return
            
            # Deck review
            elif self.state == "deck_review":
                # Check if clicking on tabs (LEFT CLICK)
                if event.button == 1 and hasattr(self, 'tab_rects'):
                    for tab_type, tab_rect in self.tab_rects.items():
                        if tab_rect.collidepoint(mouse_pos):
                            self.current_tab = tab_type
                            self.pool_scroll_offset = 0  # Reset scroll when changing tabs
                            return
                
                # RIGHT CLICK = ZOOM/INSPECT
                if event.button == 3:  # Right click
                    # Close inspection if already open
                    if self.inspected_card_id:
                        self.inspected_card_id = None
                        return
                    
                    # Find card under mouse to inspect
                    divider_x = self.screen_width // 2
                    panel_padding = 20
                    left_panel_x = panel_padding
                    left_panel_width = divider_x - panel_padding * 2
                    left_panel_y = 120  # Match draw code
                    right_panel_x = divider_x + panel_padding
                    right_panel_width = self.screen_width - right_panel_x - panel_padding
                    right_panel_y = 120  # Match draw code
                    
                    # Check cards in POOL (left panel)
                    if mouse_pos[0] < divider_x:
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
                    else:
                        if self.deck_preview_ids:
                            # Sort cards SAME way as draw code
                            sorted_deck_ids = sorted(self.deck_preview_ids, key=lambda id: (
                                0 if ALL_CARDS[id].row == "close" else
                                1 if ALL_CARDS[id].row == "ranged" else
                                2 if ALL_CARDS[id].row == "siege" else
                                3 if ALL_CARDS[id].row == "agile" else
                                4 if ALL_CARDS[id].row == "special" else
                                5 if ALL_CARDS[id].row == "weather" else 6
                            ))
                            
                            cards_per_row, spacing, card_width, card_height = self.get_card_layout_params(right_panel_width)
                            start_x = right_panel_x + spacing
                            start_y = right_panel_y + 15 - self.deck_scroll_offset
                            
                            for i, card_id in enumerate(sorted_deck_ids):
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
                    divider_x = self.screen_width // 2
                    panel_padding = 20
                    left_panel_x = panel_padding
                    left_panel_width = divider_x - panel_padding * 2
                    left_panel_y = 120  # Match draw code
                    right_panel_x = divider_x + panel_padding
                    right_panel_width = self.screen_width - right_panel_x - panel_padding
                    right_panel_y = 120  # Match draw code
                    
                    # Check cards in POOL (left panel)
                    if mouse_pos[0] < divider_x:
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
                    else:
                        if self.deck_preview_ids:
                            # Sort cards SAME way as draw code
                            sorted_deck_ids = sorted(self.deck_preview_ids, key=lambda id: (
                                0 if ALL_CARDS[id].row == "close" else
                                1 if ALL_CARDS[id].row == "ranged" else
                                2 if ALL_CARDS[id].row == "siege" else
                                3 if ALL_CARDS[id].row == "agile" else
                                4 if ALL_CARDS[id].row == "special" else
                                5 if ALL_CARDS[id].row == "weather" else 6
                            ))
                            
                            cards_per_row, spacing, card_width, card_height = self.get_card_layout_params(right_panel_width)
                            start_x = right_panel_x + spacing
                            start_y = right_panel_y + 15 - self.deck_scroll_offset
                            
                            for i, card_id in enumerate(sorted_deck_ids):
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
                
                # Back/Main Menu button (LEFT CLICK)
                if event.button == 1 and self.back_button.collidepoint(mouse_pos):
                    if self.for_new_game:
                        # NEW GAME: Go back to leader selection
                        self.state = "leader_select"
                        self.deck_scroll_offset = 0
                        self.inspected_card_id = None
                    else:
                        # DECK BUILDING: Save and return to main menu
                        # Save the current deck configuration
                        card_ids = [card_id for card_id in self.deck_preview_ids]
                        save_player_deck(self.selected_faction, self.selected_leader['card_id'], card_ids)
                        print(f"✓ Deck saved: {self.selected_faction} with {len(card_ids)} cards")
                        # Set flag to exit
                        self.return_to_menu = True
                    return
                
                # Continue button (LEFT CLICK) - Only for new game
                if event.button == 1 and self.for_new_game and self.continue_button.collidepoint(mouse_pos):
                    # Save the current deck configuration before completing
                    card_ids = [card_id for card_id in self.deck_preview_ids]
                    save_player_deck(self.selected_faction, self.selected_leader['card_id'], card_ids)
                    print(f"✓ Deck saved: {self.selected_faction} with {len(card_ids)} cards")
                    self.state = "complete"
                    return
                
                # Save button (LEFT CLICK) - Only for deck building mode
                if event.button == 1 and not self.for_new_game and self.save_button.collidepoint(mouse_pos):
                    # Save the current deck configuration
                    card_ids = [card_id for card_id in self.deck_preview_ids]
                    save_player_deck(self.selected_faction, self.selected_leader['card_id'], card_ids)
                    print(f"✓ Deck saved: {self.selected_faction} with {len(card_ids)} cards")
                    # Show visual confirmation (could add a message popup later)
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
        
        # Leader buttons
        for button in self.leader_buttons:
            # Determine button color
            is_selected = (self.selected_leader == button['leader'])
            if is_selected:
                color = self.button_selected_color
            elif button['hovered']:
                color = self.button_hover_color
            else:
                color = self.button_color
            
            # Draw button
            pygame.draw.rect(surface, color, button['rect'], border_radius=10)
            if is_selected:
                pygame.draw.rect(surface, self.highlight_color, button['rect'], width=5, border_radius=10)
            else:
                pygame.draw.rect(surface, faction_color, button['rect'], width=3, border_radius=10)
            
            # Draw leader name
            name_text = self.button_font.render(button['leader']['name'], True, self.text_color)
            name_rect = name_text.get_rect(center=(button['rect'].centerx, button['rect'].centery - 30))
            surface.blit(name_text, name_rect)
            
            # Draw ability description (wrapped to fit in button)
            ability = button['leader']['ability']
            max_width = button['rect'].width - 40  # Padding
            wrapped_lines = self.wrap_text(f"Ability: {ability}", self.desc_font, max_width)
            
            # Draw each line
            line_y = button['rect'].centery + 10
            for line in wrapped_lines:
                line_text = self.desc_font.render(line, True, (200, 200, 200))
                line_rect = line_text.get_rect(center=(button['rect'].centerx, line_y))
                surface.blit(line_text, line_rect)
                line_y += 25  # Line spacing
        
        # Back button
        pygame.draw.rect(surface, self.button_color, self.back_button, border_radius=5)
        back_text = self.button_font.render("< Back", True, self.text_color)
        back_rect = back_text.get_rect(center=self.back_button.center)
        surface.blit(back_text, back_rect)
        
        # Review Deck button (if leader selected)
        if self.selected_leader:
            pygame.draw.rect(surface, (100, 100, 200), self.review_deck_button, border_radius=10)
            review_text = self.button_font.render("Review Deck", True, self.text_color)
            review_rect = review_text.get_rect(center=self.review_deck_button.center)
            surface.blit(review_text, review_rect)
        
        # Continue button (if leader selected)
        if self.selected_leader:
            pygame.draw.rect(surface, (50, 200, 50), self.continue_button, border_radius=10)
            continue_text = self.button_font.render("START GAME", True, self.text_color)
            continue_rect = continue_text.get_rect(center=self.continue_button.center)
            surface.blit(continue_text, continue_rect)
    
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
            # Sort cards by type
            sorted_deck_ids = sorted(self.deck_preview_ids, key=lambda id: (
                0 if ALL_CARDS[id].row == "close" else
                1 if ALL_CARDS[id].row == "ranged" else
                2 if ALL_CARDS[id].row == "siege" else
                3 if ALL_CARDS[id].row == "agile" else
                4 if ALL_CARDS[id].row == "special" else
                5 if ALL_CARDS[id].row == "weather" else 6
            ))
            
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
    
    def draw_card_type_tabs(self, surface, faction_color):
        """Draw tabs for filtering cards by type."""
        tabs = [
            ("All", "all"),
            ("Close", "close"),
            ("Ranged", "ranged"),
            ("Siege", "siege"),
            ("Agile", "agile"),
            ("Special", "special"),
            ("Weather", "weather")
        ]
        
        tab_width = 100
        tab_height = 40
        tab_spacing = 5
        total_width = len(tabs) * tab_width + (len(tabs) - 1) * tab_spacing
        start_x = (self.screen_width - total_width) // 2
        tab_y = 70
        
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
            if not hasattr(self, 'tab_rects'):
                self.tab_rects = {}
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


def build_faction_deck(faction, leader=None):
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
        return saved_deck_data["cards"]
    
    # No saved deck found, build a new random one
    print(f"Building new default deck for {faction}...")
    
    # Get all card IDs from the selected faction
    faction_card_ids = [card.id for card in ALL_CARDS.values() if card.faction == faction]
    
    # If faction has more than 40 cards, randomly select 35 of them to leave room for neutrals
    if len(faction_card_ids) > 35:
        faction_card_ids = random.sample(faction_card_ids, 35)
    
    # Add some neutral cards (randomly select 3-5 neutral card IDs)
    neutral_card_ids = [card.id for card in ALL_CARDS.values() if card.faction == FACTION_NEUTRAL]
    # Filter out heroes and limit to useful neutral cards
    useful_neutrals = [id for id in neutral_card_ids if ALL_CARDS[id].row in ["special", "weather"]]
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


def get_faction_card_pool(faction):
    """
    Get all available cards for a faction (card pool).
    Returns a list of card IDs.
    """
    # Get all card IDs from the selected faction
    faction_card_ids = [card.id for card in ALL_CARDS.values() if card.faction == faction]
    
    # Add some neutral card IDs
    neutral_card_ids = [card.id for card in ALL_CARDS.values() if card.faction == FACTION_NEUTRAL]
    useful_neutrals = [id for id in neutral_card_ids if ALL_CARDS[id].row in ["special", "weather"]]
    
    # Combine and return the full pool
    card_pool_ids = faction_card_ids + useful_neutrals
    
    return card_pool_ids


def get_cards_by_type_and_strength(card_id_list, card_type=None):
    """
    Filter cards by type and sort by strength (power).
    card_type can be: 'close', 'ranged', 'siege', 'agile', 'special', 'weather', or None for all.
    Returns sorted list of card IDs.
    """
    # Filter by type if specified
    if card_type and card_type != "all":
        filtered_ids = [id for id in card_id_list if ALL_CARDS[id].row == card_type]
    else:
        filtered_ids = card_id_list
    
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
        return (type_priority.get(card.row, 99), -card.power)
    
    sorted_ids = sorted(filtered_ids, key=sort_key)
    return sorted_ids


def run_deck_builder(screen, for_new_game=True):
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
    
    deck_builder = DeckBuilderUI(screen_width, screen_height, for_new_game=for_new_game)
    clock = pygame.time.Clock()
    
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if deck_builder.state == "leader_select":
                        deck_builder.state = "faction_select"
                        deck_builder.selected_leader = None
                    else:
                        return None
            else:
                deck_builder.handle_event(event)
        
        # Check if deck building is complete
        if deck_builder.is_complete():
            return deck_builder.get_selection()
        
        # Check if user clicked MAIN MENU button from deck building
        if deck_builder.return_to_menu:
            print("✓ Returning to main menu from deck builder")
            return None
        
        # Draw
        deck_builder.draw(screen)
        pygame.display.flip()
        clock.tick(60)
    
    return None
