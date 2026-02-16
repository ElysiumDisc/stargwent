"""
Card Unlock System for Stargwent
Manages unlockable cards, leaders, and post-victory rewards.
Tracks consecutive wins for leader unlocks.
"""
import pygame
import random
import json
import os
import display_manager
from cards import Card, FACTION_NEUTRAL
from content_registry import UNLOCKABLE_LEADERS
from save_paths import get_unlock_save_path, ensure_migration

# Ensure legacy saves are migrated to XDG directory on first access
ensure_migration()

# File to persist unlocked cards and stats (using XDG Base Directory path)
UNLOCK_DATA_FILE = get_unlock_save_path()

# Define unlockable cards (cards that can be earned through gameplay)
UNLOCKABLE_CARDS = {
    "asgard_mothership": {
        "name": "Asgard Mothership",
        "faction": "Asgard",
        "row": "siege",
        "power": 10,
        "ability": "Draw 2 cards when played",
        "description": "Advanced Asgard vessel with superior firepower",
        "rarity": "epic"
    },
    "ancient_drone": {
        "name": "Ancient Drone chair",
        "faction": "Neutral",
        "row": "ranged",
        "power": 8,
        "ability": "Naquadah Overload: Destroy lowest enemy unit",
        "description": "Ancient technology of immense power",
        "rarity": "rare"
    },
    "replicator_swarm_1": {
        "name": "Replicator Swarm",
        "faction": "Neutral",
        "row": "close",
        "power": 4,
        "ability": "Tactical Formation",
        "description": "Self-replicating menace that grows stronger in numbers",
        "rarity": "rare"
    },
    "replicator_swarm_2": {
        "name": "Replicator Swarm",
        "faction": "Neutral",
        "row": "close",
        "power": 4,
        "ability": "Tactical Formation",
        "description": "Self-replicating menace that grows stronger in numbers",
        "rarity": "rare"
    },
    "replicator_swarm_3": {
        "name": "Replicator Swarm",
        "faction": "Neutral",
        "row": "close",
        "power": 4,
        "ability": "Tactical Formation",
        "description": "Self-replicating menace that grows stronger in numbers",
        "rarity": "rare"
    },
    "wraith_hive_1": {
        "name": "Wraith Hive Ship",
        "faction": "Neutral",
        "row": "siege",
        "power": 9,
        "ability": "Gate Reinforcement",
        "description": "Summons all Wraith Hives from deck and hand to board",
        "rarity": "epic"
    },
    "wraith_hive_2": {
        "name": "Wraith Hive Ship",
        "faction": "Neutral",
        "row": "siege",
        "power": 9,
        "ability": "Gate Reinforcement",
        "description": "Summons all Wraith Hives from deck and hand to board",
        "rarity": "epic"
    },
    "wraith_hive_3": {
        "name": "Wraith Hive Ship",
        "faction": "Neutral",
        "row": "siege",
        "power": 9,
        "ability": "Gate Reinforcement",
        "description": "Summons all Wraith Hives from deck and hand to board",
        "rarity": "epic"
    },
    "ori_warship": {
        "name": "Ori Warship",
        "faction": "Neutral",
        "row": "siege",
        "power": 11,
        "ability": "Legendary Commander",
        "description": "Powered by religious fervor and Ancient knowledge",
        "rarity": "legendary"
    },
    "atlantis_city": {
        "name": "City of Atlantis",
        "faction": "Neutral",
        "row": "siege",
        "power": 10,
        "ability": "Legendary Commander, Inspiring Leadership",
        "description": "Ancient city ship with shield technology",
        "rarity": "legendary"
    },
    "super_soldier": {
        "name": "Anubis Super Soldier",
        "faction": "Goa'uld",
        "row": "close",
        "power": 7,
        "ability": "Survival Instinct",
        "description": "Nearly indestructible warrior enhanced by Ancient technology",
        "rarity": "epic"
    },
    "prometheus_x303": {
        "name": "Prometheus X-303",
        "faction": "Tau'ri",
        "row": "siege",
        "power": 8,
        "ability": "Draw 1 card when played",
        "description": "Earth's first deep-space capital ship",
        "rarity": "rare"
    },
    "kull_warrior": {
        "name": "Kull Warrior Elite",
        "faction": "Goa'uld",
        "row": "close",
        "power": 8,
        "ability": "Legendary Commander, Survival Instinct",
        "description": "Anubis's ultimate creation with impenetrable armor",
        "rarity": "epic"
    },
    "puddle_jumper": {
        "name": "Puddle Jumper",
        "faction": "Neutral",
        "row": "agile",
        "power": 5,
        "ability": "Ring Transport: Return to hand to replay",
        "description": "Ancient ship with cloaking and versatile deployment",
        "rarity": "rare"
    },
    # NEW CARDS - Strategic and Balanced
    "sodan_warrior": {
        "name": "Sodan Cloaked Warrior",
        "faction": "Lucian Alliance",
        "row": "close",
        "power": 6,
        "ability": "When played: Look at opponent's hand for 30s",
        "description": "Invisible warrior reveals enemy secrets for a limited time",
        "rarity": "epic"
    },
    "tok_ra_operative": {
        "name": "Tok'ra Deep Cover Operative",
        "faction": "Tau'ri",
        "row": "ranged",
        "power": 4,
        "ability": "Deep Cover Agent",
        "description": "Enhanced spy that draws 2 cards (or 3 with faction bonus)",
        "rarity": "epic"
    },
    "asgard_hammer": {
        "name": "Thor's Hammer Device",
        "faction": "Asgard",
        "row": "special",
        "power": 0,
        "ability": "Remove all Goa'uld units from both boards",
        "description": "Ancient Asgard anti-Goa'uld technology",
        "rarity": "legendary"
    },
    "zpm_power": {
        "name": "Zero Point Module",
        "faction": "Neutral",
        "row": "special",
        "power": 0,
        "ability": "Double all your siege units this round",
        "description": "Nearly infinite Ancient power source",
        "rarity": "legendary"
    },
    "merlin_device": {
        "name": "Merlin's Anti-Ori Weapon",
        "faction": "Neutral",
        "row": "special",
        "power": 0,
        "ability": "Naquadah Overload",
        "description": "One-sided Naquadah Overload that only destroys opponent's strongest units",
        "rarity": "legendary"
    },
    "dakara_superweapon": {
        "name": "Dakara Superweapon",
        "faction": "Jaffa Rebellion",
        "row": "siege",
        "power": 12,
        "ability": "Legendary Commander",
        "description": "Massive ancient superweapon - immune to all effects",
        "rarity": "legendary"
    },
    "replicator_carter": {
        "name": "Replicator Carter",
        "faction": "Neutral",
        "row": "close",
        "power": 7,
        "ability": "Survival Instinct",
        "description": "Gains +2 power when weather affects her row",
        "rarity": "epic"
    },
    "ancient_communication_stones": {
        "name": "Ancient Communication Device",
        "faction": "Neutral",
        "row": "special",
        "power": 0,
        "ability": "Reveal opponent's hand for 30 seconds",
        "description": "See through enemy eyes - reveals all cards in opponent's hand for a limited time",
        "rarity": "rare"
    },
    "asuran_warship": {
        "name": "Asuran Aurora-class",
        "faction": "Neutral",
        "row": "siege",
        "power": 10,
        "ability": "Deploy Clones, Tactical Formation",
        "description": "Ancient warship",
        "rarity": "epic"
    },
    "destiny_ship": {
        "name": "Ancient Ship Destiny",
        "faction": "Neutral",
        "row": "siege",
        "power": 15,
        "ability": "Legendary Commander",
        "description": "Most powerful Ancient warship - massive firepower, immune to all effects",
        "rarity": "legendary"
    },
}
class CardUnlockSystem:
    """Manages card unlocking, leader unlocking, and player's card collection."""
    
    def __init__(self):
        self.unlocked_cards = set()
        self.unlocked_leaders = {}  # faction -> list of unlocked leader IDs
        self.consecutive_wins = 0
        self.total_wins = 0
        self.total_games = 0
        self.unlock_override_enabled = False
        self.load_unlocks()
    
    def load_unlocks(self):
        """Load unlocked cards and stats from file."""
        if os.path.exists(UNLOCK_DATA_FILE):
            try:
                with open(UNLOCK_DATA_FILE, 'r') as f:
                    data = json.load(f)
                    self.unlocked_cards = set(data.get('unlocked', []))
                    self.unlocked_leaders = data.get('unlocked_leaders', {})
                    self.consecutive_wins = data.get('consecutive_wins', 0)
                    self.total_wins = data.get('total_wins', 0)
                    self.total_games = data.get('total_games', 0)
                    self.unlock_override_enabled = data.get('unlock_override_enabled', False)
            except (json.JSONDecodeError, OSError, KeyError):
                self.unlocked_cards = set()
                self.unlocked_leaders = {}
                self.consecutive_wins = 0
                self.total_wins = 0
                self.total_games = 0
                self.unlock_override_enabled = False
        else:
            # Start with no unlocked cards
            self.unlocked_cards = set()
            self.unlocked_leaders = {}
            self.consecutive_wins = 0
            self.total_wins = 0
            self.total_games = 0
            self.unlock_override_enabled = False
    
    def save_unlocks(self):
        """Save unlocked cards and stats to file, preserving existing data."""
        # Load existing data to preserve stats from deck_persistence
        existing_data = {}
        if os.path.exists(UNLOCK_DATA_FILE):
            try:
                with open(UNLOCK_DATA_FILE, 'r') as f:
                    existing_data = json.load(f)
            except (json.JSONDecodeError, OSError):
                existing_data = {}
        
        # Update with our data (preserving other keys like top_cards, matchups, etc.)
        existing_data.update({
            'unlocked': list(self.unlocked_cards),
            'unlocked_leaders': self.unlocked_leaders,
            'consecutive_wins': self.consecutive_wins,
            'total_wins': self.total_wins,
            'total_games': self.total_games,
            'unlock_override_enabled': self.unlock_override_enabled,
        })
        
        with open(UNLOCK_DATA_FILE, 'w') as f:
            json.dump(existing_data, f, indent=2)
    
    def record_game_result(self, won):
        """Record game result and update consecutive wins."""
        self.total_games += 1
        if won:
            self.total_wins += 1
            self.consecutive_wins += 1
        else:
            self.consecutive_wins = 0
        self.save_unlocks()
    
    def unlock_card(self, card_id):
        """Unlock a specific card."""
        self.unlocked_cards.add(card_id)
        self.save_unlocks()
    
    def unlock_leader(self, faction, leader_id):
        """Unlock a specific leader for a faction."""
        if faction not in self.unlocked_leaders:
            self.unlocked_leaders[faction] = []
        if leader_id not in self.unlocked_leaders[faction]:
            self.unlocked_leaders[faction].append(leader_id)
        self.save_unlocks()
    
    def is_unlocked(self, card_id):
        """Check if a card is unlocked."""
        if self.unlock_override_enabled:
            return True
        return card_id in self.unlocked_cards

    def is_leader_unlocked(self, faction, leader_id):
        """Check if a leader is unlocked."""
        if self.unlock_override_enabled:
            return True
        return leader_id in self.unlocked_leaders.get(faction, [])

    def is_unlock_override_enabled(self) -> bool:
        """Return True if the global unlock-all override is enabled."""
        return self.unlock_override_enabled

    def set_unlock_override(self, enabled: bool):
        """Persistently enable/disable the unlock-all override toggle."""
        enabled = bool(enabled)
        if self.unlock_override_enabled == enabled:
            return
        self.unlock_override_enabled = enabled
        self.save_unlocks()

    def toggle_unlock_override(self):
        """Invert the unlock-all override toggle."""
        self.set_unlock_override(not self.unlock_override_enabled)
    
    def get_unlocked_leaders_for_faction(self, faction):
        """Get list of unlocked leader IDs for a faction."""
        if self.unlock_override_enabled:
            if faction in UNLOCKABLE_LEADERS:
                return [leader['card_id'] for leader in UNLOCKABLE_LEADERS[faction]]
            return []
        return self.unlocked_leaders.get(faction, [])

    def should_offer_leader_unlock(self):
        """Check if player qualifies for leader unlock (3 consecutive wins)."""
        if self.unlock_override_enabled:
            return False
        return self.consecutive_wins >= 3
    
    def get_available_leader_unlocks(self, faction):
        """Get leaders available to unlock for a faction."""
        if self.unlock_override_enabled:
            return []
        if faction not in UNLOCKABLE_LEADERS:
            return []
        
        unlocked_for_faction = self.unlocked_leaders.get(faction, [])
        available = []
        
        for leader in UNLOCKABLE_LEADERS[faction]:
            if leader['card_id'] not in unlocked_for_faction:
                available.append(leader)
        
        return available
    
    def get_available_unlocks(self, count=3, faction=None):
        """Get random cards available to unlock, optionally filtered by faction."""
        if self.unlock_override_enabled:
            return []
        locked_cards = [cid for cid in UNLOCKABLE_CARDS.keys() 
                       if cid not in self.unlocked_cards]
        
        # Filter by faction if provided (include Neutral cards too)
        if faction:
            locked_cards = [cid for cid in locked_cards 
                          if UNLOCKABLE_CARDS[cid]['faction'] in [faction, 'Neutral']]
        
        if not locked_cards:
            return []  # All cards unlocked!
        
        return random.sample(locked_cards, min(count, len(locked_cards)))
    
    def create_card_instance(self, card_id):
        """Create a Card instance from unlockable card data."""
        if card_id not in UNLOCKABLE_CARDS:
            return None
        
        data = UNLOCKABLE_CARDS[card_id]
        card = Card(
            name=data['name'],
            faction=data['faction'],
            row=data['row'],
            power=data['power'],
            ability=data.get('ability', None)
        )
        return card


class CardRewardUI:
    """UI for selecting reward cards after winning."""
    
    def __init__(self, screen_width, screen_height, card_ids, unlock_system):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.card_ids = card_ids
        self.unlock_system = unlock_system
        self.selected_card = None
        self.card_buttons = []
        
        # Fonts
        self.title_font = pygame.font.SysFont("Arial", 56, bold=True)
        self.desc_font = pygame.font.SysFont("Arial", 24)
        self.rarity_font = pygame.font.SysFont("Arial", 20, bold=True)
        
        # Colors
        self.bg_color = (15, 15, 25)
        self.text_color = (255, 255, 255)
        self.highlight_color = (255, 215, 0)
        
        # Rarity colors
        self.rarity_colors = {
            'common': (200, 200, 200),
            'rare': (100, 150, 255),
            'epic': (200, 100, 255),
            'legendary': (255, 200, 50)
        }
        
        self.setup_layout()
    
    def setup_layout(self):
        """Setup card display layout."""
        card_width = 300
        card_height = 450
        spacing = 60
        total_width = len(self.card_ids) * card_width + (len(self.card_ids) - 1) * spacing
        start_x = (self.screen_width - total_width) // 2
        start_y = (self.screen_height - card_height) // 2
        
        for i, card_id in enumerate(self.card_ids):
            x = start_x + i * (card_width + spacing)
            self.card_buttons.append({
                'rect': pygame.Rect(x, start_y, card_width, card_height),
                'card_id': card_id,
                'hovered': False
            })
    
    def handle_event(self, event):
        """Handle input events."""
        if event.type == pygame.MOUSEMOTION:
            mouse_pos = event.pos
            for button in self.card_buttons:
                button['hovered'] = button['rect'].collidepoint(mouse_pos)
        
        elif event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = event.pos
            for button in self.card_buttons:
                if button['rect'].collidepoint(mouse_pos):
                    self.selected_card = button['card_id']
                    self.unlock_system.unlock_card(self.selected_card)
                    return True
        
        elif event.type == pygame.KEYDOWN:
            # Number keys to select cards
            if event.key == pygame.K_1 and len(self.card_ids) > 0:
                self.selected_card = self.card_ids[0]
                self.unlock_system.unlock_card(self.selected_card)
                return True
            elif event.key == pygame.K_2 and len(self.card_ids) > 1:
                self.selected_card = self.card_ids[1]
                self.unlock_system.unlock_card(self.selected_card)
                return True
            elif event.key == pygame.K_3 and len(self.card_ids) > 2:
                self.selected_card = self.card_ids[2]
                self.unlock_system.unlock_card(self.selected_card)
                return True
        
        return False
    
    def draw(self, surface):
        """Draw the card reward UI."""
        # Semi-transparent background
        overlay = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 220))
        surface.blit(overlay, (0, 0))
        
        # Title
        title = self.title_font.render("VICTORY! CHOOSE A NEW CARD", True, self.highlight_color)
        title_rect = title.get_rect(center=(self.screen_width // 2, 100))
        surface.blit(title, title_rect)
        
        # Subtitle
        subtitle = self.desc_font.render("Click a card or press 1/2/3 to add it to your collection", True, self.text_color)
        subtitle_rect = subtitle.get_rect(center=(self.screen_width // 2, 160))
        surface.blit(subtitle, subtitle_rect)
        
        # Draw cards
        for i, button in enumerate(self.card_buttons):
            card_id = button['card_id']
            card_data = UNLOCKABLE_CARDS[card_id]
            rect = button['rect']
            
            # Card background
            if button['hovered']:
                bg_color = (60, 60, 80)
                border_color = self.highlight_color
                border_width = 5
            else:
                bg_color = (40, 40, 60)
                border_color = self.rarity_colors[card_data['rarity']]
                border_width = 3
            
            pygame.draw.rect(surface, bg_color, rect, border_radius=15)
            pygame.draw.rect(surface, border_color, rect, width=border_width, border_radius=15)
            
            # Placeholder art area
            art_rect = pygame.Rect(rect.x + 20, rect.y + 20, rect.width - 40, 200)
            pygame.draw.rect(surface, (80, 80, 100), art_rect, border_radius=10)
            
            # "NEW CARD" text on placeholder
            new_text = self.rarity_font.render("NEW CARD", True, self.highlight_color)
            new_rect = new_text.get_rect(center=art_rect.center)
            surface.blit(new_text, new_rect)
            
            # Card name
            name_text = self.desc_font.render(card_data['name'], True, self.text_color)
            name_rect = name_text.get_rect(center=(rect.centerx, rect.y + 240))
            surface.blit(name_text, name_rect)
            
            # Rarity
            rarity_text = self.rarity_font.render(card_data['rarity'].upper(), True, self.rarity_colors[card_data['rarity']])
            rarity_rect = rarity_text.get_rect(center=(rect.centerx, rect.y + 270))
            surface.blit(rarity_text, rarity_rect)
            
            # Power and row
            stats_text = self.desc_font.render(f"Power: {card_data['power']} | {card_data['row'].capitalize()}", True, (200, 200, 200))
            stats_rect = stats_text.get_rect(center=(rect.centerx, rect.y + 300))
            surface.blit(stats_text, stats_rect)
            
            # Ability (wrapped)
            if card_data.get('ability'):
                ability_lines = self.wrap_text(card_data['ability'], rect.width - 40)
                y_offset = 330
                for line in ability_lines:
                    ability_text = pygame.font.SysFont("Arial", 18).render(line, True, (150, 255, 150))
                    ability_rect = ability_text.get_rect(center=(rect.centerx, rect.y + y_offset))
                    surface.blit(ability_text, ability_rect)
                    y_offset += 22
            
            # Number indicator
            number_text = self.title_font.render(str(i + 1), True, self.text_color)
            surface.blit(number_text, (rect.x + 10, rect.y + 10))
    
    def wrap_text(self, text, max_width):
        """Wrap text to fit within max_width."""
        words = text.split(' ')
        lines = []
        current_line = []
        
        font = pygame.font.SysFont("Arial", 18)
        for word in words:
            current_line.append(word)
            line_text = ' '.join(current_line)
            if font.size(line_text)[0] > max_width:
                if len(current_line) > 1:
                    current_line.pop()
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    lines.append(line_text)
                    current_line = []
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines


class LeaderRewardUI:
    """UI for selecting reward leaders after 3 consecutive wins."""
    
    def __init__(self, screen_width, screen_height, faction, leaders, unlock_system):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.faction = faction
        self.leaders = leaders
        self.unlock_system = unlock_system
        self.selected_leader = None
        self.leader_buttons = []
        
        # Fonts
        self.title_font = pygame.font.SysFont("Arial", 64, bold=True)
        self.subtitle_font = pygame.font.SysFont("Arial", 32, bold=True)
        self.desc_font = pygame.font.SysFont("Arial", 24)
        self.small_font = pygame.font.SysFont("Arial", 20)
        
        # Colors
        self.bg_color = (15, 15, 25)
        self.text_color = (255, 255, 255)
        self.highlight_color = (255, 215, 0)
        self.faction_color = (100, 150, 255)
        
        self.setup_layout()
    
    def setup_layout(self):
        """Setup leader display layout."""
        leader_width = 350
        leader_height = 500
        spacing = 60
        total_width = len(self.leaders) * leader_width + (len(self.leaders) - 1) * spacing
        start_x = (self.screen_width - total_width) // 2
        start_y = (self.screen_height - leader_height) // 2
        
        for i, leader in enumerate(self.leaders):
            x = start_x + i * (leader_width + spacing)
            self.leader_buttons.append({
                'rect': pygame.Rect(x, start_y, leader_width, leader_height),
                'leader': leader,
                'hovered': False
            })
    
    def handle_event(self, event):
        """Handle input events."""
        if event.type == pygame.MOUSEMOTION:
            mouse_pos = event.pos
            for button in self.leader_buttons:
                button['hovered'] = button['rect'].collidepoint(mouse_pos)
        
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = event.pos
            for button in self.leader_buttons:
                if button['rect'].collidepoint(mouse_pos):
                    self.selected_leader = button['leader']
                    self.unlock_system.unlock_leader(self.faction, self.selected_leader['card_id'])
                    self.unlock_system.consecutive_wins = 0  # Reset streak after claiming
                    self.unlock_system.save_unlocks()
                    return True
        
        elif event.type == pygame.KEYDOWN:
            # Number keys to select leaders
            if event.key == pygame.K_1 and len(self.leaders) > 0:
                self.selected_leader = self.leaders[0]
                self.unlock_system.unlock_leader(self.faction, self.selected_leader['card_id'])
                self.unlock_system.consecutive_wins = 0
                self.unlock_system.save_unlocks()
                return True
            elif event.key == pygame.K_2 and len(self.leaders) > 1:
                self.selected_leader = self.leaders[1]
                self.unlock_system.unlock_leader(self.faction, self.selected_leader['card_id'])
                self.unlock_system.consecutive_wins = 0
                self.unlock_system.save_unlocks()
                return True
            elif event.key == pygame.K_3 and len(self.leaders) > 2:
                self.selected_leader = self.leaders[2]
                self.unlock_system.unlock_leader(self.faction, self.selected_leader['card_id'])
                self.unlock_system.consecutive_wins = 0
                self.unlock_system.save_unlocks()
                return True
            elif event.key == pygame.K_ESCAPE:
                # Skip without resetting streak
                return True
        
        return False
    
    def draw(self, surface):
        """Draw the leader reward UI."""
        # Semi-transparent background
        overlay = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 230))
        surface.blit(overlay, (0, 0))
        
        # Title
        title = self.title_font.render("3 WINS IN A ROW!", True, self.highlight_color)
        title_rect = title.get_rect(center=(self.screen_width // 2, 80))
        surface.blit(title, title_rect)
        
        # Subtitle
        subtitle = self.subtitle_font.render(f"UNLOCK NEW {self.faction.upper()} LEADER", True, self.faction_color)
        subtitle_rect = subtitle.get_rect(center=(self.screen_width // 2, 140))
        surface.blit(subtitle, subtitle_rect)
        
        # Instructions
        instructions = self.desc_font.render("Choose 1 leader to replace your current leader", True, self.text_color)
        inst_rect = instructions.get_rect(center=(self.screen_width // 2, 190))
        surface.blit(instructions, inst_rect)
        
        # Draw leaders
        for i, button in enumerate(self.leader_buttons):
            leader = button['leader']
            rect = button['rect']
            
            # Leader background
            if button['hovered']:
                bg_color = (70, 70, 100)
                border_color = self.highlight_color
                border_width = 6
            else:
                bg_color = (45, 45, 70)
                border_color = self.faction_color
                border_width = 4
            
            pygame.draw.rect(surface, bg_color, rect, border_radius=15)
            pygame.draw.rect(surface, border_color, rect, width=border_width, border_radius=15)
            
            # Portrait placeholder area (top)
            portrait_rect = pygame.Rect(rect.x + 25, rect.y + 25, rect.width - 50, 250)
            pygame.draw.rect(surface, (80, 80, 100), portrait_rect, border_radius=10)
            
            # Golden "LEADER" badge
            leader_badge = self.small_font.render("NEW LEADER", True, self.highlight_color)
            badge_rect = leader_badge.get_rect(center=(portrait_rect.centerx, portrait_rect.centery))
            surface.blit(leader_badge, badge_rect)
            
            # Leader name
            name_text = self.subtitle_font.render(leader['name'], True, self.text_color)
            name_rect = name_text.get_rect(center=(rect.centerx, rect.y + 300))
            surface.blit(name_text, name_rect)
            
            # Ability (wrapped)
            ability_y = 340
            ability_lines = self.wrap_text(leader['ability'], rect.width - 30)
            for line in ability_lines:
                ability_text = self.desc_font.render(line, True, (150, 255, 150))
                ability_rect = ability_text.get_rect(center=(rect.centerx, rect.y + ability_y))
                surface.blit(ability_text, ability_rect)
                ability_y += 30
            
            # Number indicator
            number_bg = pygame.Rect(rect.x + 10, rect.y + 10, 40, 40)
            pygame.draw.circle(surface, self.highlight_color, number_bg.center, 25)
            number_text = self.subtitle_font.render(str(i + 1), True, (0, 0, 0))
            number_rect = number_text.get_rect(center=number_bg.center)
            surface.blit(number_text, number_rect)
        
        # Bottom instruction
        bottom_text = self.small_font.render("Press 1/2/3 or Click to select | ESC to skip", True, (180, 180, 180))
        bottom_rect = bottom_text.get_rect(center=(self.screen_width // 2, self.screen_height - 40))
        surface.blit(bottom_text, bottom_rect)
    
    def wrap_text(self, text, max_width):
        """Wrap text to fit within max_width."""
        words = text.split(' ')
        lines = []
        current_line = []
        
        font = self.desc_font
        for word in words:
            current_line.append(word)
            line_text = ' '.join(current_line)
            if font.size(line_text)[0] > max_width:
                if len(current_line) > 1:
                    current_line.pop()
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    lines.append(line_text)
                    current_line = []
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines


def show_leader_reward_screen(screen, unlock_system, faction):
    """Show leader reward selection screen after 3 consecutive wins."""
    available_leaders = unlock_system.get_available_leader_unlocks(faction)
    
    if not available_leaders:
        # All leaders for this faction unlocked
        return None
    
    # Show up to 3 leaders
    leaders_to_show = available_leaders[:3]
    
    reward_ui = LeaderRewardUI(screen.get_width(), screen.get_height(), 
                               faction, leaders_to_show, unlock_system)
    
    clock = pygame.time.Clock()
    running = True
    
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            
            if reward_ui.handle_event(event):
                return reward_ui.selected_leader
        
        reward_ui.draw(screen)
        display_manager.gpu_flip()
        clock.tick(60)
    
    return None


def show_card_reward_screen(screen, unlock_system, faction=None):
    """Show card reward selection screen after victory."""
    available_cards = unlock_system.get_available_unlocks(3, faction=faction)
    
    if not available_cards:
        # All cards unlocked - show congratulations
        return None
    
    reward_ui = CardRewardUI(screen.get_width(), screen.get_height(), 
                            available_cards, unlock_system)
    
    clock = pygame.time.Clock()
    running = True
    
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    # Skip reward
                    return None
            
            if reward_ui.handle_event(event):
                return reward_ui.selected_card
        
        reward_ui.draw(screen)
        display_manager.gpu_flip()
        clock.tick(60)
    
    return None
