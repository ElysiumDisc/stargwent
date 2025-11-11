"""
Main Menu System for Stargwent
Includes main menu, deck customization, and deck management.
Also includes Stargate opening animation (merged from stargate_opening.py).
"""
import pygame
import json
import os
import math
import random
from cards import ALL_CARDS, FACTION_TAURI, FACTION_GOAULD, FACTION_JAFFA, FACTION_LUCIAN, FACTION_ASGARD, FACTION_NEUTRAL, reload_card_images
from deck_builder import FACTION_LEADERS, MIN_DECK_SIZE, MAX_DECK_SIZE, validate_deck
from unlocks import CardUnlockSystem, UNLOCKABLE_CARDS

# Save file for custom decks
CUSTOM_DECKS_FILE = "player_decks.json"


class DeckManager:
    """Manages custom deck configurations for each faction."""
    
    def __init__(self, unlock_system):
        self.unlock_system = unlock_system
        self.custom_decks = {}
        self.load_decks()
    
    def load_decks(self):
        """Load saved custom decks from file."""
        if os.path.exists(CUSTOM_DECKS_FILE):
            try:
                with open(CUSTOM_DECKS_FILE, 'r') as f:
                    self.custom_decks = json.load(f)
            except:
                self.custom_decks = {}
        else:
            self.custom_decks = {}
    
    def save_decks(self):
        """Save custom decks to file."""
        with open(CUSTOM_DECKS_FILE, 'w') as f:
            json.dump(self.custom_decks, f, indent=2)
    
    def get_deck(self, faction):
        """Get custom deck for faction, or None if using default."""
        return self.custom_decks.get(faction, None)
    
    def set_deck(self, faction, card_ids):
        """Set custom deck for faction."""
        self.custom_decks[faction] = card_ids
        self.save_decks()
    
    def get_available_cards_for_faction(self, faction):
        """Get all cards available for a faction (base + unlocked + neutral)."""
        available = []
        
        # Faction cards
        for card_id, card in ALL_CARDS.items():
            if card.faction == faction:
                available.append({'id': card_id, 'card': card, 'source': 'faction'})
        
        # Neutral cards
        for card_id, card in ALL_CARDS.items():
            if card.faction == FACTION_NEUTRAL:
                available.append({'id': card_id, 'card': card, 'source': 'neutral'})
        
        # Unlocked cards (that match faction or are neutral)
        for card_id in self.unlock_system.unlocked_cards:
            if card_id in UNLOCKABLE_CARDS:
                card_data = UNLOCKABLE_CARDS[card_id]
                if card_data['faction'] == faction or card_data['faction'] == 'Neutral':
                    available.append({'id': card_id, 'card': None, 'data': card_data, 'source': 'unlocked'})
        
        return available


class MainMenu:
    """Main menu screen."""
    
    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.selected_option = 0
        
        # Load background
        self.background = None
        self.load_background()
        
        # Fonts - Make title HUGE and impressive
        try:
            self.title_font = pygame.font.Font(None, 180)  # Much larger!
        except:
            self.title_font = pygame.font.SysFont("Impact, Arial Black, Arial", 160, bold=True)
        
        try:
            self.subtitle_font = pygame.font.SysFont("Courier New, Consolas, Monospace", 38)
        except:
            self.subtitle_font = pygame.font.SysFont("Arial", 36)
        
        try:
            self.button_font = pygame.font.SysFont("Impact, Arial Black, Arial", 46, bold=True)
        except:
            self.button_font = pygame.font.SysFont("Arial", 42, bold=True)
        
        # Colors
        self.bg_color = (10, 15, 30)
        self.button_color = (40, 60, 100)
        self.button_hover_color = (60, 90, 150)
        self.button_selected_color = (80, 120, 180)
        self.text_color = (255, 255, 255)
        self.highlight_color = (100, 200, 255)  # Stargate blue
        
        # Menu options
        self.options = [
            {'text': 'NEW GAME', 'action': 'new_game'},
            {'text': 'DECK BUILDING', 'action': 'deck_building'},
            {'text': 'QUIT', 'action': 'quit'}
        ]
        
        self.setup_buttons()
    
    def load_background(self):
        """Load menu background image."""
        try:
            self.background = pygame.image.load("assets/menu_background.png").convert()
            # Scale to screen size if needed
            if self.background.get_size() != (self.screen_width, self.screen_height):
                self.background = pygame.transform.scale(self.background, (self.screen_width, self.screen_height))
        except:
            self.background = None
    
    def setup_buttons(self):
        """Setup menu button positions."""
        button_width = 400
        button_height = 80
        spacing = 30
        start_x = (self.screen_width - button_width) // 2
        start_y = self.screen_height // 2 - 50
        
        for i, option in enumerate(self.options):
            y = start_y + i * (button_height + spacing)
            option['rect'] = pygame.Rect(start_x, y, button_width, button_height)
            option['hovered'] = False
    
    def handle_event(self, event):
        """Handle input events."""
        if event.type == pygame.MOUSEMOTION:
            mouse_pos = event.pos
            for i, option in enumerate(self.options):
                option['hovered'] = option['rect'].collidepoint(mouse_pos)
                if option['hovered']:
                    self.selected_option = i
        
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = event.pos
            for option in self.options:
                if option['rect'].collidepoint(mouse_pos):
                    return option['action']
        
        elif event.type == pygame.KEYDOWN:
            if event.key in [pygame.K_UP, pygame.K_w]:
                self.selected_option = (self.selected_option - 1) % len(self.options)
            elif event.key in [pygame.K_DOWN, pygame.K_s]:
                self.selected_option = (self.selected_option + 1) % len(self.options)
            elif event.key == pygame.K_RETURN:
                return self.options[self.selected_option]['action']
            elif event.key == pygame.K_ESCAPE:
                return 'quit'
        
        return None
    
    def draw(self, surface):
        """Draw the main menu."""
        # Draw background
        if self.background:
            surface.blit(self.background, (0, 0))
        else:
            surface.fill(self.bg_color)
        
        # IMPRESSIVE TITLE with multiple effects
        title_y = 180  # Move down a bit for larger title
        
        # Create gradient effect - draw multiple layers
        title_text = "STARGWENT"
        
        # Shadow layers (black, offset)
        for offset in range(8, 0, -2):
            shadow = self.title_font.render(title_text, True, (0, 0, 0))
            shadow_rect = shadow.get_rect(center=(self.screen_width // 2 + offset, title_y + offset))
            surface.blit(shadow, shadow_rect)
        
        # Outer glow (blue/cyan)
        glow_surf = pygame.Surface((self.screen_width, 300), pygame.SRCALPHA)
        for i in range(6, 0, -1):
            glow_color = (*self.highlight_color, 30)
            glow_text = self.title_font.render(title_text, True, glow_color)
            glow_rect = glow_text.get_rect(center=(self.screen_width // 2 + i, title_y + i))
            glow_surf.blit(glow_text, (glow_rect.x, glow_rect.y - title_y + 50))
        surface.blit(glow_surf, (0, title_y - 50))
        
        # Inner glow (brighter)
        inner_glow_color = (255, 255, 200, 80)
        inner_glow = self.title_font.render(title_text, True, inner_glow_color)
        inner_rect = inner_glow.get_rect(center=(self.screen_width // 2, title_y))
        surface.blit(inner_glow, inner_rect)
        
        # Main title (gold/yellow)
        main_title = self.title_font.render(title_text, True, self.highlight_color)
        main_rect = main_title.get_rect(center=(self.screen_width // 2, title_y))
        surface.blit(main_title, main_rect)
        
        # Highlight edge (white)
        highlight = self.title_font.render(title_text, True, (255, 255, 255))
        highlight_rect = highlight.get_rect(center=(self.screen_width // 2 - 2, title_y - 2))
        highlight.set_alpha(150)
        surface.blit(highlight, highlight_rect)
        
        # Menu buttons
        for i, option in enumerate(self.options):
            is_selected = (i == self.selected_option)
            
            if is_selected:
                color = self.button_selected_color
            elif option['hovered']:
                color = self.button_hover_color
            else:
                color = self.button_color
            
            # Draw button
            pygame.draw.rect(surface, color, option['rect'], border_radius=10)
            if is_selected:
                pygame.draw.rect(surface, self.highlight_color, option['rect'], width=4, border_radius=10)
            else:
                pygame.draw.rect(surface, (100, 100, 120), option['rect'], width=2, border_radius=10)
            
            # Draw text
            text = self.button_font.render(option['text'], True, self.text_color)
            text_rect = text.get_rect(center=option['rect'].center)
            surface.blit(text, text_rect)


class DeckCustomizationUI:
    """UI for customizing decks for each faction."""
    
    def __init__(self, screen_width, screen_height, deck_manager):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.deck_manager = deck_manager
        self.selected_faction = FACTION_TAURI
        self.current_deck = []
        self.available_cards = []
        self.scroll_offset = 0
        self.deck_scroll_offset = 0
        self.selected_card = None
        
        # Load deck building background
        self.deck_building_bg = None
        self.load_deck_building_bg()
        
        # Fonts
        self.title_font = pygame.font.SysFont("Arial", 48, bold=True)
        self.subtitle_font = pygame.font.SysFont("Arial", 28)
        self.small_font = pygame.font.SysFont("Arial", 20)
        
        # Colors
        self.bg_color = (15, 15, 25)
        self.text_color = (255, 255, 255)
        self.highlight_color = (255, 215, 0)
        
        # Faction tabs
        self.faction_tabs = [
            FACTION_TAURI, FACTION_GOAULD, FACTION_JAFFA, 
            FACTION_LUCIAN, FACTION_ASGARD
        ]
        
        self.setup_ui()
        self.load_faction_deck(self.selected_faction)
    
    def load_deck_building_bg(self):
        """Load deck building background image."""
        import os
        bg_path = os.path.join("assets", "deck_building_bg.png")
        
        if os.path.exists(bg_path):
            try:
                bg_image = pygame.image.load(bg_path).convert()
                self.deck_building_bg = pygame.transform.scale(bg_image, (self.screen_width, self.screen_height))
                print("✓ Loaded deck_building_bg.png for deck customization")
            except Exception as e:
                print(f"Warning: Could not load {bg_path}: {e}")
                self.deck_building_bg = None
        else:
            self.deck_building_bg = None
    
    def setup_ui(self):
        """Setup UI elements."""
        # Faction tabs at top
        self.tab_rects = []
        tab_width = 250
        tab_height = 50
        spacing = 10
        total_width = len(self.faction_tabs) * tab_width + (len(self.faction_tabs) - 1) * spacing
        start_x = (self.screen_width - total_width) // 2
        
        for i, faction in enumerate(self.faction_tabs):
            x = start_x + i * (tab_width + spacing)
            rect = pygame.Rect(x, 10, tab_width, tab_height)
            self.tab_rects.append({'faction': faction, 'rect': rect})
        
        # Back button
        self.back_button = pygame.Rect(20, self.screen_height - 70, 150, 50)
        
        # Save button
        self.save_button = pygame.Rect(self.screen_width - 170, self.screen_height - 70, 150, 50)
        
        # Reset to default button
        self.reset_button = pygame.Rect(self.screen_width - 350, self.screen_height - 70, 170, 50)
    
    def load_faction_deck(self, faction):
        """Load deck for selected faction."""
        self.selected_faction = faction
        
        # Load custom deck or create default
        saved_deck = self.deck_manager.get_deck(faction)
        if saved_deck:
            # Load saved deck
            self.current_deck = saved_deck[:]
        else:
            # Create default deck from faction cards (limited to 40 max)
            import random
            self.current_deck = []
            faction_card_ids = [card_id for card_id, card in ALL_CARDS.items() if card.faction == faction]
            
            # If faction has more than 35 cards, randomly select 35 to leave room for neutrals
            if len(faction_card_ids) > 35:
                faction_card_ids = random.sample(faction_card_ids, 35)
            
            self.current_deck.extend(faction_card_ids)
            
            # Add some neutrals (up to 5, but respect 40 card limit)
            neutral_card_ids = [card_id for card_id, card in ALL_CARDS.items() if card.faction == FACTION_NEUTRAL]
            neutral_count = min(5, 40 - len(self.current_deck))
            if neutral_card_ids and neutral_count > 0:
                selected_neutrals = random.sample(neutral_card_ids, min(neutral_count, len(neutral_card_ids)))
                self.current_deck.extend(selected_neutrals)
            
            # Ensure we don't exceed 40 cards
            if len(self.current_deck) > 40:
                self.current_deck = self.current_deck[:40]
        
        # Load available cards
        self.available_cards = self.deck_manager.get_available_cards_for_faction(faction)
        self.scroll_offset = 0
        self.deck_scroll_offset = 0
    
    def handle_event(self, event):
        """Handle input events."""
        if event.type == pygame.MOUSEMOTION:
            # Update hover states if needed
            pass
        
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button in [4, 5]:  # Mouse wheel
                # Scroll available cards area
                if event.button == 4:
                    self.scroll_offset = max(0, self.scroll_offset - 50)
                else:
                    self.scroll_offset += 50
                return None
            
            mouse_pos = event.pos
            
            # Check faction tabs
            for tab in self.tab_rects:
                if tab['rect'].collidepoint(mouse_pos):
                    self.load_faction_deck(tab['faction'])
                    return None
            
            # Check back button
            if self.back_button.collidepoint(mouse_pos):
                return 'back'
            
            # Check save button
            if self.save_button.collidepoint(mouse_pos):
                is_valid, message = validate_deck(self.get_deck_cards())
                if is_valid:
                    self.deck_manager.set_deck(self.selected_faction, self.current_deck)
                    return 'back'
                else:
                    print(f"Cannot save: {message}")
                return None
            
            # Check reset button
            if self.reset_button.collidepoint(mouse_pos):
                self.current_deck = []
                self.deck_manager.set_deck(self.selected_faction, None)
                self.load_faction_deck(self.selected_faction)
                return None
            
            # Check card clicks (add/remove from deck)
            # Available cards area (left side)
            card_area_rect = pygame.Rect(20, 120, self.screen_width // 2 - 40, self.screen_height - 220)
            if card_area_rect.collidepoint(mouse_pos):
                self.handle_available_card_click(mouse_pos)
            
            # Current deck area (right side)
            deck_area_rect = pygame.Rect(self.screen_width // 2 + 20, 120, self.screen_width // 2 - 40, self.screen_height - 220)
            if deck_area_rect.collidepoint(mouse_pos):
                self.handle_deck_card_click(mouse_pos)
        
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return 'back'
        
        return None
    
    def handle_available_card_click(self, mouse_pos):
        """Handle click on available cards."""
        card_width = 100
        card_height = 150
        cards_per_row = 4
        spacing = 15
        start_x = 30
        start_y = 150 - self.scroll_offset
        
        for i, card_info in enumerate(self.available_cards):
            row = i // cards_per_row
            col = i % cards_per_row
            x = start_x + col * (card_width + spacing)
            y = start_y + row * (card_height + spacing)
            card_rect = pygame.Rect(x, y, card_width, card_height)
            
            if card_rect.collidepoint(mouse_pos):
                # Add card to deck if not at max
                if len(self.current_deck) < MAX_DECK_SIZE:
                    self.current_deck.append(card_info['id'])
                break
    
    def handle_deck_card_click(self, mouse_pos):
        """Handle click on deck cards (remove)."""
        card_width = 100
        card_height = 150
        cards_per_row = 4
        spacing = 15
        start_x = self.screen_width // 2 + 30
        start_y = 150 - self.deck_scroll_offset
        
        for i, card_id in enumerate(self.current_deck):
            row = i // cards_per_row
            col = i % cards_per_row
            x = start_x + col * (card_width + spacing)
            y = start_y + row * (card_height + spacing)
            card_rect = pygame.Rect(x, y, card_width, card_height)
            
            if card_rect.collidepoint(mouse_pos):
                # Remove card from deck
                self.current_deck.pop(i)
                break
    
    def get_deck_cards(self):
        """Convert deck IDs to Card objects for validation."""
        deck_cards = []
        for card_id in self.current_deck:
            if card_id in ALL_CARDS:
                deck_cards.append(ALL_CARDS[card_id])
        return deck_cards
    
    def draw(self, surface):
        """Draw the deck customization UI."""
        # Use deck building background if available
        if self.deck_building_bg:
            surface.blit(self.deck_building_bg, (0, 0))
        else:
            surface.fill(self.bg_color)
        
        # Title
        title = self.title_font.render("DECK CUSTOMIZATION", True, self.highlight_color)
        surface.blit(title, (self.screen_width // 2 - title.get_width() // 2, 70))
        
        # Faction tabs
        for tab in self.tab_rects:
            is_selected = (tab['faction'] == self.selected_faction)
            color = (80, 120, 180) if is_selected else (40, 60, 100)
            pygame.draw.rect(surface, color, tab['rect'], border_radius=5)
            if is_selected:
                pygame.draw.rect(surface, self.highlight_color, tab['rect'], width=3, border_radius=5)
            
            text = self.subtitle_font.render(tab['faction'], True, self.text_color)
            text_rect = text.get_rect(center=tab['rect'].center)
            surface.blit(text, text_rect)
        
        # Draw available cards (left) and current deck (right)
        self.draw_available_cards(surface)
        self.draw_current_deck(surface)
        
        # Buttons
        pygame.draw.rect(surface, (60, 60, 80), self.back_button, border_radius=5)
        back_text = self.subtitle_font.render("BACK", True, self.text_color)
        surface.blit(back_text, (self.back_button.centerx - back_text.get_width() // 2, self.back_button.centery - back_text.get_height() // 2))
        
        pygame.draw.rect(surface, (50, 150, 50), self.save_button, border_radius=5)
        save_text = self.subtitle_font.render("SAVE", True, self.text_color)
        surface.blit(save_text, (self.save_button.centerx - save_text.get_width() // 2, self.save_button.centery - save_text.get_height() // 2))
        
        pygame.draw.rect(surface, (150, 50, 50), self.reset_button, border_radius=5)
        reset_text = self.small_font.render("RESET DEFAULT", True, self.text_color)
        surface.blit(reset_text, (self.reset_button.centerx - reset_text.get_width() // 2, self.reset_button.centery - reset_text.get_height() // 2))
    
    def draw_available_cards(self, surface):
        """Draw available cards pool."""
        header = self.subtitle_font.render("Available Cards (Click to Add)", True, self.text_color)
        surface.blit(header, (30, 125))
        
        # Draw card grid (simplified - showing card names)
        card_width = 100
        card_height = 150
        cards_per_row = 4
        spacing = 15
        start_x = 30
        start_y = 150 - self.scroll_offset
        
        for i, card_info in enumerate(self.available_cards):
            row = i // cards_per_row
            col = i % cards_per_row
            x = start_x + col * (card_width + spacing)
            y = start_y + row * (card_height + spacing)
            
            # Only draw if visible
            if y + card_height < 120 or y > self.screen_height - 100:
                continue
            
            # Draw card placeholder
            pygame.draw.rect(surface, (60, 60, 80), (x, y, card_width, card_height), border_radius=5)
            pygame.draw.rect(surface, (100, 100, 120), (x, y, card_width, card_height), width=2, border_radius=5)
            
            # Draw card name (truncated)
            if card_info['card']:
                name = card_info['card'].name[:12]
            else:
                name = card_info['data']['name'][:12]
            
            name_text = self.small_font.render(name, True, self.text_color)
            surface.blit(name_text, (x + 5, y + 5))
    
    def draw_current_deck(self, surface):
        """Draw current deck."""
        deck_cards = self.get_deck_cards()
        is_valid, message = validate_deck(deck_cards)
        
        color = (100, 255, 100) if is_valid else (255, 100, 100)
        header = self.subtitle_font.render(f"Current Deck: {len(self.current_deck)}/{MIN_DECK_SIZE}-{MAX_DECK_SIZE}", True, color)
        surface.blit(header, (self.screen_width // 2 + 30, 125))
        
        if not is_valid:
            error_text = self.small_font.render(message, True, (255, 100, 100))
            surface.blit(error_text, (self.screen_width // 2 + 30, 155))
        
        # Draw deck grid
        card_width = 100
        card_height = 150
        cards_per_row = 4
        spacing = 15
        start_x = self.screen_width // 2 + 30
        start_y = 180 - self.deck_scroll_offset
        
        for i, card_id in enumerate(self.current_deck):
            row = i // cards_per_row
            col = i % cards_per_row
            x = start_x + col * (card_width + spacing)
            y = start_y + row * (card_height + spacing)
            
            # Only draw if visible
            if y + card_height < 120 or y > self.screen_height - 100:
                continue
            
            # Draw card placeholder
            pygame.draw.rect(surface, (80, 80, 100), (x, y, card_width, card_height), border_radius=5)
            pygame.draw.rect(surface, (150, 150, 170), (x, y, card_width, card_height), width=2, border_radius=5)
            
            # Draw card name
            if card_id in ALL_CARDS:
                name = ALL_CARDS[card_id].name[:12]
            else:
                name = "Unknown"
            
            name_text = self.small_font.render(name, True, self.text_color)
            surface.blit(name_text, (x + 5, y + 5))


def run_main_menu(screen, unlock_system):
    """Run the main menu loop."""
    # CRITICAL: Reload card images at menu start to ensure proper loading
    print("Main Menu: Reloading card images for current screen size...")
    reload_card_images()
    print("Main Menu: Card images loaded!")
    
    deck_manager = DeckManager(unlock_system)
    main_menu = MainMenu(screen.get_width(), screen.get_height())
    clock = pygame.time.Clock()
    
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:
                    # Toggle fullscreen
                    pygame.display.toggle_fullscreen()
            
            action = main_menu.handle_event(event)
            if action == 'new_game':
                return 'new_game'
            elif action == 'deck_building':
                # Use the GOOD deck builder from deck_builder.py
                from deck_builder import run_deck_builder
                result = run_deck_builder(screen, for_new_game=False)  # Not for new game, just deck customization
                # If result is None, user clicked MAIN MENU or ESC - just continue showing main menu
                # (Don't return None here, that would quit the game!)
            elif action == 'quit':
                return None
        
        main_menu.draw(screen)
        pygame.display.flip()
        clock.tick(60)
    
    return None


def run_deck_customization(screen, deck_manager):
    """Run the deck customization UI."""
    deck_ui = DeckCustomizationUI(screen.get_width(), screen.get_height(), deck_manager)
    clock = pygame.time.Clock()
    
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            
            result = deck_ui.handle_event(event)
            if result == 'back':
                return 'back'
        
        deck_ui.draw(screen)
        pygame.display.flip()
        clock.tick(60)
    
    return None


# ===== STARGATE OPENING ANIMATION (MERGED FROM stargate_opening.py) =====

class StargateOpeningAnimation:
    """Dramatic Stargate opening animation."""
    
    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.center_x = screen_width // 2
        self.center_y = screen_height // 2
        self.progress = 0.0
        self.duration = 8000  # 8 seconds (added 3 more seconds for vortex)
        self.elapsed = 0
        
        # Gate properties
        self.gate_radius = min(screen_width, screen_height) // 3
        self.inner_radius = self.gate_radius - 40
        
        # Chevrons
        self.chevrons = []
        for i in range(9):
            angle = i * 40 - 90  # Start at top
            self.chevrons.append({
                'angle': angle,
                'locked': False,
                'lock_time': 500 + i * 400,  # Stagger locks
                'glow': 0
            })
        
        # Event horizon particles
        self.horizon_particles = []
        for _ in range(100):
            self.horizon_particles.append({
                'angle': random.uniform(0, 360),
                'distance': 0,
                'speed': random.uniform(2, 5),
                'size': random.randint(2, 4),
                'alpha': 0
            })
        
        # Outward vortex particles (KAWOOSH!)
        self.vortex_particles = []
        for _ in range(200):
            self.vortex_particles.append({
                'angle': random.uniform(0, 360),
                'distance': 0,
                'speed': random.uniform(15, 30),  # Fast outward burst
                'size': random.randint(3, 8),
                'alpha': 255,
                'lifetime': random.uniform(0.5, 1.5)  # How long it lives
            })
    
    def update(self, dt):
        """Update animation."""
        self.elapsed += dt
        self.progress = min(1.0, self.elapsed / self.duration)
        
        # Lock chevrons progressively
        for chevron in self.chevrons:
            if self.elapsed >= chevron['lock_time'] and not chevron['locked']:
                chevron['locked'] = True
                chevron['glow'] = 255
            
            # Fade glow
            if chevron['glow'] > 50:
                chevron['glow'] = max(50, chevron['glow'] - dt * 0.3)
        
        # Update event horizon particles (after chevrons lock)
        if self.progress > 0.5:
            for particle in self.horizon_particles:
                particle['distance'] += particle['speed'] * (dt / 16.0)
                particle['alpha'] = min(255, particle['alpha'] + 5)
                
                # Reset if too far
                if particle['distance'] > self.inner_radius:
                    particle['distance'] = 0
                    particle['angle'] = random.uniform(0, 360)
        
        # Update VORTEX particles (KAWOOSH at 70% progress, lasts longer)
        if self.progress > 0.7:
            for particle in self.vortex_particles:
                particle['distance'] += particle['speed'] * (dt / 16.0)
                particle['lifetime'] -= dt / 1000.0
                particle['alpha'] = max(0, int(255 * particle['lifetime']))
                
                # Reset when dead
                if particle['lifetime'] <= 0:
                    particle['distance'] = 0
                    particle['angle'] = random.uniform(0, 360)
                    particle['lifetime'] = random.uniform(0.5, 1.5)
                    particle['alpha'] = 255
        
        return self.progress < 1.0
    
    def draw(self, surface):
        """Draw the Stargate opening animation."""
        # Dark background
        surface.fill((5, 5, 15))
        
        # Outer ring (stone)
        pygame.draw.circle(surface, (80, 80, 100), (self.center_x, self.center_y), self.gate_radius, 20)
        pygame.draw.circle(surface, (120, 120, 140), (self.center_x, self.center_y), self.gate_radius, 3)
        pygame.draw.circle(surface, (60, 60, 80), (self.center_x, self.center_y), self.gate_radius - 20, 3)
        
        # Inner ring
        pygame.draw.circle(surface, (40, 40, 60), (self.center_x, self.center_y), self.inner_radius, 15)
        
        # Draw chevrons
        for chevron in self.chevrons:
            angle_rad = math.radians(chevron['angle'])
            x = self.center_x + math.cos(angle_rad) * self.gate_radius
            y = self.center_y + math.sin(angle_rad) * self.gate_radius
            
            # Chevron symbol (triangle)
            size = 20
            points = [
                (x, y - size),
                (x - size // 2, y + size // 2),
                (x + size // 2, y + size // 2)
            ]
            
            if chevron['locked']:
                # Locked chevron - glowing orange
                glow = int(chevron['glow'])
                color = (255, min(255, 140 + glow // 2), 0)
                
                # Glow effect
                if chevron['glow'] > 100:
                    glow_surf = pygame.Surface((size * 4, size * 4), pygame.SRCALPHA)
                    glow_color = (255, 180, 0, int(chevron['glow'] * 0.6))
                    pygame.draw.circle(glow_surf, glow_color, (size * 2, size * 2), size * 2)
                    surface.blit(glow_surf, (int(x - size * 2), int(y - size * 2)))
                
                pygame.draw.polygon(surface, color, points)
            else:
                # Inactive chevron
                pygame.draw.polygon(surface, (60, 60, 70), points)
            
            pygame.draw.polygon(surface, (200, 200, 200), points, 2)
        
        # Event horizon (after chevrons start locking)
        if self.progress > 0.3:
            # Base event horizon glow
            horizon_alpha = int(min(255, (self.progress - 0.3) * 400))
            horizon_surf = pygame.Surface((self.inner_radius * 2, self.inner_radius * 2), pygame.SRCALPHA)
            
            # Blue vortex
            for i in range(5):
                radius = self.inner_radius - i * 15
                alpha = horizon_alpha // (i + 1)
                color = (50, 150 + i * 20, 255, alpha)
                pygame.draw.circle(horizon_surf, color, (self.inner_radius, self.inner_radius), radius)
            
            surface.blit(horizon_surf, (self.center_x - self.inner_radius, self.center_y - self.inner_radius))
            
            # Swirling particles
            for particle in self.horizon_particles:
                if particle['alpha'] > 0:
                    angle_rad = math.radians(particle['angle'])
                    x = self.center_x + math.cos(angle_rad) * particle['distance']
                    y = self.center_y + math.sin(angle_rad) * particle['distance']
                    
                    particle_surf = pygame.Surface((particle['size'] * 2, particle['size'] * 2), pygame.SRCALPHA)
                    color = (150, 200, 255, int(particle['alpha']))
                    pygame.draw.circle(particle_surf, color, (particle['size'], particle['size']), particle['size'])
                    surface.blit(particle_surf, (int(x - particle['size']), int(y - particle['size'])))
        
        # OUTWARD VORTEX (KAWOOSH!) at 70%
        if self.progress > 0.7:
            for particle in self.vortex_particles:
                if particle['alpha'] > 0 and particle['distance'] < self.gate_radius * 2 and particle['size'] > 0:
                    angle_rad = math.radians(particle['angle'])
                    x = self.center_x + math.cos(angle_rad) * particle['distance']
                    y = self.center_y + math.sin(angle_rad) * particle['distance']
                    
                    size = max(1, int(particle['size']))  # Ensure size is at least 1
                    alpha = max(0, min(255, int(particle['alpha'])))  # Clamp alpha
                    
                    particle_surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
                    # Bright white/blue vortex particles
                    color = (255, 255, 255, alpha)
                    pygame.draw.circle(particle_surf, color, (size, size), size)
                    surface.blit(particle_surf, (int(x - size), int(y - size)))
        
        # Title text (fades in at end)
        if self.progress > 0.7:
            title_alpha = int(min(255, (self.progress - 0.7) * 850))
            title_font = pygame.font.SysFont("Arial", 72, bold=True)
            title_text = title_font.render("STARGWENT", True, (255, 255, 255))
            title_text.set_alpha(title_alpha)
            title_rect = title_text.get_rect(center=(self.center_x, self.screen_height - 150))
            surface.blit(title_text, title_rect)
            
            # Subtitle
            if self.progress > 0.85:
                sub_alpha = int(min(255, (self.progress - 0.85) * 1700))
                sub_font = pygame.font.SysFont("Arial", 32)
                sub_text = sub_font.render("Prepare for Battle", True, (100, 200, 255))
                sub_text.set_alpha(sub_alpha)
                sub_rect = sub_text.get_rect(center=(self.center_x, self.screen_height - 100))
                surface.blit(sub_text, sub_rect)


def show_stargate_opening(screen):
    """Show the Stargate opening animation."""
    animation = StargateOpeningAnimation(screen.get_width(), screen.get_height())
    clock = pygame.time.Clock()
    
    running = True
    while running:
        dt = clock.tick(60)
        
        # Handle events (allow skip)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
                return True  # Skip animation
        
        # Update and draw
        if not animation.update(dt):
            running = False
        
        animation.draw(screen)
        pygame.display.flip()
    
    return True

