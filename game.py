import random
import copy
import time
import pygame
import logging
from cards import ALL_CARDS, FACTION_TAURI, FACTION_GOAULD, FACTION_JAFFA, FACTION_LUCIAN, FACTION_ASGARD, FACTION_NEUTRAL, Card
from abilities import Ability, has_ability, is_hero, is_spy, is_medic, can_be_targeted
from sound_manager import get_sound_manager

# Configure logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ===== STARGATE MECHANICS (MERGED FROM stargate_mechanics.py) =====

# ===== BALANCE CONFIGURATION =====

BALANCE_CONFIG = {
    # Faction ability limits
    "jaffa_brotherhood_max": 3,  # Max bonus from Brotherhood
    "goauld_command_bonus": 1,   # Bonus per unit with Hero

    # Alliance bonuses (kept moderate)
    "alliance_bonus_range": (3, 5),  # Min and max alliance bonuses

    # DHD limit
    "dhd_uses_per_round": 1,    # Can only dial home once per round

    # Artifact power
    "artifact_neutral_bonus": 2,  # Ancient Chair bonus
    "artifact_scorch_threshold": 8,  # Asgard Beam threshold

    # Naquadah budget system
    "naquadah_budget": 230,  # Max Naquadah for a deck
    "ori_corruption_penalty": 0.5,  # 50% power reduction for over-budget decks
}

# ===== FACTION ABILITIES =====

class FactionAbility:
    """Base class for faction passive abilities."""
    def __init__(self, name, description):
        self.name = name
        self.description = description
    
    def apply(self, game, player):
        """Override this to implement the ability."""
        pass


class TauriAbility(FactionAbility):
    """Tau'ri: 'Resourcefulness' - Draw 1 extra card at start of rounds 2 and 3."""
    def __init__(self):
        super().__init__(
            "Resourcefulness",
            "Draw 1 extra card at the start of rounds 2 and 3"
        )
    
    def apply_round_start(self, game, player):
        """Called at round start."""
        if game.round_number > 1:
            player.draw_cards(1)


class GoauldAbility(FactionAbility):
    """Goa'uld: 'System Lord's Command' - Non-Hero units get +1 if you have a Hero on board."""
    def __init__(self):
        super().__init__(
            "System Lord's Command",
            f"Your non-Hero units get +{BALANCE_CONFIG['goauld_command_bonus']} power when you have a Hero on board"
        )

    def apply_to_score(self, player):
        """Called during score calculation."""
        # Check if player has any Legendary Commander on board
        board_has_hero = False
        for row in player.board.values():
            for card in row:
                if is_hero(card):
                    board_has_hero = True
                    break
            if board_has_hero:
                break

        if board_has_hero:
            # Add bonus to all non-Legendary Commander units
            for row in player.board.values():
                for card in row:
                    if not is_hero(card):
                        card.displayed_power += BALANCE_CONFIG["goauld_command_bonus"]


class JaffaAbility(FactionAbility):
    """Jaffa: 'Brotherhood' - Units get +1 for each other unit in the same row (max +3)."""
    def __init__(self):
        super().__init__(
            "Brotherhood",
            f"Each unit gets +1 power for each other unit in the same row (max +{BALANCE_CONFIG['jaffa_brotherhood_max']})"
        )

    def apply_to_score(self, player):
        """Called during score calculation."""
        for row_name, row_cards in player.board.items():
            non_hero_units = [c for c in row_cards if not is_hero(c)]
            if len(non_hero_units) > 1:
                bonus = min(BALANCE_CONFIG["jaffa_brotherhood_max"], len(non_hero_units) - 1)
                for card in non_hero_units:
                    card.displayed_power += bonus


class AsgardAbility(FactionAbility):
    """Asgard: 'Superior Shielding' - Immune to first weather card each round."""
    def __init__(self):
        super().__init__(
            "Superior Shielding",
            "Immune to the first weather card played each round"
        )
        self.weather_immunity_used = False
    
    def reset_round(self):
        """Called at round start."""
        self.weather_immunity_used = False
    
    def can_block_weather(self):
        """Check if can block weather this round."""
        if not self.weather_immunity_used:
            self.weather_immunity_used = True
            return True
        return False


class LucianAbility(FactionAbility):
    """Lucian: 'Piracy' - First Spy card each round draws 3 instead of 2."""
    def __init__(self):
        super().__init__(
            "Piracy",
            "Your first Spy card each round draws 3 cards instead of 2"
        )
        self.spy_bonus_used = False
    
    def reset_round(self):
        """Called at round start."""
        self.spy_bonus_used = False
    
    def get_spy_draw_amount(self):
        """Get the number of cards to draw for spy."""
        if not self.spy_bonus_used:
            self.spy_bonus_used = True
            return 3
        return 2


# Faction ability mapping
FACTION_ABILITIES = {
    FACTION_TAURI: TauriAbility(),
    FACTION_GOAULD: GoauldAbility(),
    FACTION_JAFFA: JaffaAbility(),
    FACTION_ASGARD: AsgardAbility(),
    FACTION_LUCIAN: LucianAbility(),
}


# ===== DHD (DIAL HOME DEVICE) MECHANIC =====

class DHDMechanic:
    """Allows retrieving a card from discard once per round."""
    def __init__(self):
        self.used_this_round = False
    
    def reset_round(self):
        """Reset for new round."""
        self.used_this_round = False
    
    def can_use(self):
        """Check if DHD can be used."""
        return not self.used_this_round
    
    def use(self, player, rng=None):
        """Use DHD to retrieve a random card from discard."""
        if self.can_use() and player.discard_pile:
            self.used_this_round = True
            # Get random non-Hero, non-Special card from discard
            eligible_cards = [
                c for c in player.discard_pile 
                if "Hero" not in (c.ability or "") and c.row not in ["special", "weather"]
            ]
            if eligible_cards:
                rand = rng or random
                card = rand.choice(eligible_cards)
                player.discard_pile.remove(card)
                player.hand.append(card)
                return card
        return None


# ===== IRIS DEFENSE MECHANIC =====

class IrisDefense:
    """One-time ability to block opponent's next card."""
    def __init__(self):
        self.available = True
        self.active = False
    
    def activate(self):
        """Activate iris defense."""
        if self.available:
            self.available = False
            self.active = True
            # Play iris sound effect
            from sound_manager import get_sound_manager
            sound_manager = get_sound_manager()
            sound_manager.play_iris_sound(volume=0.7)
            return True
        return False
    
    def is_active(self):
        """Check if iris is currently blocking."""
        return self.active
    
    def deactivate(self):
        """Deactivate after blocking one card."""
        self.active = False
    
    def is_available(self):
        """Check if iris defense is still available."""
        return self.available


# ===== ARTIFACT CARDS =====

class Artifact:
    """Persistent effect that stays across rounds."""
    def __init__(self, name, description, effect_func):
        self.name = name
        self.description = description
        self.effect_func = effect_func

    def apply_effect(self, game, player):
        """Apply the artifact's effect."""
        self.effect_func(game, player)


class GameHistoryEntry:
    """Data container describing a single log entry for the HUD history feed."""
    
    # Default icons for event types (ASCII-safe for pygame-ce compatibility)
    EVENT_ICONS = {
        "card_play": ">",
        "pass": "||",
        "round_start": "=",
        "round_end": "#",
        "game_over": "*",
        "scorch": "X",
        "destroy": "X",
        "weather": "~",
        "clear_weather": "O",
        "horn": "!",
        "medic": "+",
        "spy": "?",
        "ability": "*",
        "hero": "*",
        "faction_power": "@",
        "muster": ">>",
        "bond": "&",
        "decoy": "<>",
        "steal": "->",
        "draw": "v",
        "discard": "^",
        "chat": "\"",
        "special": "*",
        "iris": "[#]",
        "transport": "o",
    }
    
    def __init__(self, event_type, description, owner, card_ref=None, icon=None, row=None, delta=0, targets=None, turn_number=0, scores=None):
        self.event_type = event_type
        self.description = description
        self.owner = owner  # 'player' or 'ai'
        self.card_ref = card_ref
        # Auto-assign icon if not provided
        self.icon = icon if icon else self.EVENT_ICONS.get(event_type, ">")
        self.row = row
        self.delta = delta      # How much the score changed (e.g., +5 or -10)
        self.targets = targets  # List of cards/rows affected
        self.turn_number = turn_number  # Which turn this event occurred on
        self.scores = scores    # Tuple of (player1_score, player2_score) at time of event
        self.timestamp = time.time()


# Artifact definitions
ARTIFACTS = {
    "ancient_control_chair": Artifact(
        "Ancient Control Chair",
        f"Your Neutral cards get +{BALANCE_CONFIG['artifact_neutral_bonus']} power",
        lambda g, p: [
            setattr(card, 'displayed_power', card.displayed_power + BALANCE_CONFIG['artifact_neutral_bonus'])
            for row in p.board.values()
            for card in row
            if card.faction == "Neutral" and "Hero" not in (card.ability or "")
        ]
    ),
    "communication_stones": Artifact(
        "Communication Stones",
        "Draw 1 card when opponent passes",
        lambda g, p: p.draw_cards(1) if g.current_player != p and g.current_player.has_passed else None
    ),
    "asgard_beam": Artifact(
        "Asgard Beam",
        f"Scorch activates at {BALANCE_CONFIG['artifact_scorch_threshold']}+ power instead of highest",
        lambda g, p: None  # Handled in scorch logic
    ),
}


# ===== STARGATE PORTAL CARD =====

def stargate_portal_effect(game, player, card_to_move, target_row):
    """Move a card from any row to any other row."""
    # Find the card on the board
    for row_name, row_cards in player.board.items():
        if card_to_move in row_cards:
            # Remove from current row
            row_cards.remove(card_to_move)
            # Add to target row
            if target_row in player.board:
                player.board[target_row].append(card_to_move)
                return True
    return False


# ===== SYMBIOTE HOST MECHANIC =====

def symbiote_host_effect(game, player, host_card, target_card):
    """Absorb target card's power into host card."""
    # Find target on board
    for row_name, row_cards in player.board.items():
        if target_card in row_cards:
            # Add target's power to host
            host_card.power += target_card.power
            host_card.displayed_power = host_card.power
            # Remove target card
            row_cards.remove(target_card)
            player.discard_pile.append(target_card)
            return True
    return False


# ===== ALLIANCE COMBO SYSTEM =====

class AllianceCombo:
    """Represents a multi-card combo for bonus power."""
    def __init__(self, name, required_cards, bonus, description):
        self.name = name
        self.required_cards = required_cards  # List of card names
        self.bonus = bonus
        self.description = description

    def check_active(self, player):
        """Check if all required cards are on the board."""
        cards_on_board = set()
        for row in player.board.values():
            for card in row:
                cards_on_board.add(card.name)

        return all(required in cards_on_board for required in self.required_cards)

    def apply_bonus(self, player):
        """Apply the alliance bonus. Returns True if combo was active."""
        if self.check_active(player):
            # Add bonus to all cards in the alliance
            for row in player.board.values():
                for card in row:
                    if card.name in self.required_cards:
                        card.displayed_power += self.bonus
            return True
        return False


class FactionAllianceCombo:
    """Alliance combo based on faction unit count (e.g., 3+ Asgard heroes)."""
    def __init__(self, name, faction, min_count, bonus, description, hero_only=False):
        self.name = name
        self.faction = faction  # Faction to count
        self.min_count = min_count  # Minimum units required
        self.bonus = bonus  # Power bonus to apply
        self.description = description
        self.hero_only = hero_only  # If True, only count heroes

    def check_active(self, player):
        """Check if enough units of the faction are on board."""
        count = 0
        for row in player.board.values():
            for card in row:
                if card.faction == self.faction:
                    if self.hero_only:
                        if is_hero(card):
                            count += 1
                    else:
                        count += 1
        return count >= self.min_count

    def apply_bonus(self, player):
        """Apply bonus to all faction units. Returns True if combo was active."""
        if self.check_active(player):
            for row in player.board.values():
                for card in row:
                    if card.faction == self.faction:
                        card.displayed_power += self.bonus
            return True
        return False


class JaffaUprisingCombo:
    """Special combo for Jaffa Uprising: 5+ Jaffa units = +1 power to ALL units."""
    def __init__(self):
        self.name = "Jaffa Uprising"
        self.min_count = 5
        self.bonus = 1
        self.description = "When 5+ Jaffa units are on board, ALL your units get +1 power"

    def check_active(self, player):
        """Check if 5+ Jaffa units on board."""
        count = 0
        for row in player.board.values():
            for card in row:
                if card.faction == FACTION_JAFFA:
                    count += 1
        return count >= self.min_count

    def apply_bonus(self, player):
        """Apply +1 to ALL units if active. Returns True if combo was active."""
        if self.check_active(player):
            for row in player.board.values():
                for card in row:
                    card.displayed_power += self.bonus
            return True
        return False


class LucianNetworkCombo:
    """Lucian Network: 2+ spies played this round = draw 1 card.
    Note: The draw effect is triggered separately, not in score calculation."""
    def __init__(self):
        self.name = "Lucian Network"
        self.min_spies = 2
        self.description = "When 2+ spies are played in a round, draw 1 card"
        self.triggered_this_round = False  # Track if already triggered

    def check_active(self, player):
        """Check if 2+ spies were played this round."""
        spies_this_round = getattr(player, 'spies_played_this_round', 0)
        return spies_this_round >= self.min_spies and not self.triggered_this_round

    def apply_bonus(self, player):
        """Draw effect is handled separately. Returns True if should trigger draw."""
        if self.check_active(player):
            self.triggered_this_round = True
            return True
        return False

    def reset_round(self):
        """Reset the trigger flag for new round."""
        self.triggered_this_round = False


# Alliance combo definitions
ALLIANCE_COMBOS = [
    AllianceCombo(
        "SG-1 United",
        ["Col. Jack O'Neill", "Dr. Samantha Carter", "Dr. Daniel Jackson", "V. Teal'c"],
        5,  # +5 to each member (balanced: requires 4 specific heroes)
        "SG-1 team members each get +5 power"
    ),
    AllianceCombo(
        "Tok'ra Alliance",
        ["Dr. Samantha Carter", "Tok'ra Operative"],
        3,  # +3 to both
        "Tau'ri and Tok'ra working together get +3 power"
    ),
    AllianceCombo(
        "System Lords Summit",
        ["Apophis", "Yu the Great", "Sokar"],
        4,  # +4 to each
        "System Lords united get +4 power each"
    ),
    # NEW: Faction-based alliance combos
    FactionAllianceCombo(
        "Asgard High Council",
        FACTION_ASGARD,
        3,  # 3+ Asgard heroes
        2,  # +2 to all Asgard units
        "When 3+ Asgard heroes are on board, all Asgard units get +2 power",
        hero_only=True
    ),
    JaffaUprisingCombo(),  # 5+ Jaffa = +1 to ALL units
]

# Special combo that triggers card draw (handled separately from score calculation)
LUCIAN_NETWORK_COMBO = LucianNetworkCombo()


# ===== END OF MERGED STARGATE MECHANICS =====

class Player:
    """Represents a player in the game."""
    def __init__(self, name, faction, custom_deck=None, leader=None, rng=None, is_ai=False, exempt_penalties=False):
        self.name = name
        self.faction = faction
        self.leader = leader  # Leader selection with special ability
        self._rng = rng if rng is not None else random
        self.is_ai = is_ai  # True if this player is controlled by AI (skips Mercenary Tax/Ori Corruption)
        self.exempt_penalties = exempt_penalties  # True for draft mode (cross-faction by design)
        self.deck = custom_deck if custom_deck else self.build_deck()
        self.hand = []
        self.board = { "close": [], "ranged": [], "siege": [] }
        self.discard_pile = []
        self.artifacts = []  # Persistent artifacts
        self.score = 0
        self.rounds_won = 0
        self.has_passed = False
        self.weather_effects = {"close": False, "ranged": False, "siege": False}
        self.horn_effects = {"close": False, "ranged": False, "siege": False}
        self.horn_slots = {"close": None, "ranged": None, "siege": None}
        self.weather_cards_played = 0  # Track for missions
        self.current_round_number = 1  # Track round for leader abilities
        self.units_played_this_round = 0  # Track for Gerak and Ka'lel abilities
        self.hand_revealed = False  # Track if opponent can see this player's hand
        self.hand_reveal_timer = 0  # Timer for hand reveal (in seconds)
        self.reveal_next_round = False  # Pending reveal flag for Yu ability
        self.yu_ability_used = False  # Track if Lord Yu's ability has been used (once per game)
        self.plays_this_turn = 0  # Track plays for Rak'nor ability
        self.zpm_active = False  # Track if ZPM was played this round
        self.spies_played_this_round = 0  # Track spies for Lucian Network combo
        
        # Stargate mechanics - create fresh instances per player (avoid shared mutable state)
        _ability_classes = {
            FACTION_TAURI: TauriAbility,
            FACTION_GOAULD: GoauldAbility,
            FACTION_JAFFA: JaffaAbility,
            FACTION_ASGARD: AsgardAbility,
            FACTION_LUCIAN: LucianAbility,
        }
        self.faction_ability = _ability_classes[faction]() if faction in _ability_classes else None
        self.dhd_mechanic = DHDMechanic()

        # Check for Neutral Penalty (Mercenary Tax)
        # If deck has > 50% neutral cards, apply 25% power penalty
        # AI players and draft mode players are exempt (curated/cross-faction by design)
        self.neutral_penalty_active = False
        if self.deck and not self.is_ai and not self.exempt_penalties:
            neutral_count = sum(1 for c in self.deck if c.faction == FACTION_NEUTRAL)
            if neutral_count > len(self.deck) / 2:
                self.neutral_penalty_active = True

        # Check for Ori Corruption (Naquadah over-budget penalty)
        # If deck exceeds Naquadah budget, apply 50% power reduction
        # AI players and draft mode players are exempt (curated/cross-faction by design)
        self.ori_corrupted = False
        if self.deck and not self.is_ai and not self.exempt_penalties:
            total_naquadah = sum(c.naquadah_cost for c in self.deck)
            if total_naquadah > BALANCE_CONFIG["naquadah_budget"]:
                self.ori_corrupted = True
        
        # Iris Defense (Tau'ri Only)
        if faction == FACTION_TAURI:
            self.iris_defense = IrisDefense()
        
        # Faction-specific special abilities (separate from Faction Powers)
        from power import RingTransportation
        self.ring_transportation = RingTransportation() if faction == "Goa'uld" else None
        
        # Faction Power (imported at runtime to avoid circular dependency)
        self.faction_power = None  # Faction-specific power (once per game)
        self.power_used = False  # Track faction power usage (once per game)

    def build_deck(self):
        """Builds a starting deck for the player based on their faction."""
        # Deep copy cards to prevent shared state between players
        deck = [copy.deepcopy(card) for card in ALL_CARDS.values() if card.faction == self.faction]
        self._rng.shuffle(deck)
        return deck

    def calculate_score(self, game=None):
        """Calculates the player's total score, applying all abilities and effects.
        Returns list of activated alliance combos for history logging."""
        # First, reset all card powers to their base value
        for row_name, row_cards in self.board.items():
            for card in row_cards:
                card.displayed_power = card.power

        # Track activated alliance combos
        activated_combos = []

        # Apply Hammond ability bonus (first unit each round gets +3)
        if self.leader and "Hammond" in self.leader.get('name', ''):
            for row_name, row_cards in self.board.items():
                for card in row_cards:
                    if hasattr(card, 'hammond_boosted') and card.hammond_boosted:
                        card.displayed_power += 3
        
        # Apply Ka'lel ability bonus (first 3 units each round get +2)
        if self.leader and "Ka'lel" in self.leader.get('name', ''):
            for row_name, row_cards in self.board.items():
                for card in row_cards:
                    if hasattr(card, 'kalel_boosted') and card.kalel_boosted:
                        card.displayed_power += 2

        # Apply leader ability - power bonuses (BEFORE weather)
        if self.leader:
            leader_name = self.leader.get('name', '')

            # Hathor: Steal lowest power card from opponent (handled separately in trigger_hathor_ability)
            # This is just a placeholder - the actual stealing happens in trigger_hathor_ability
            
            # Dr. Samantha Carter: +2 power to all Siege units
            if "Carter" in leader_name:
                for card in self.board.get('siege', []):
                    card.displayed_power += 2
            
            # Sokar: +1 power to all Close Combat units
            elif "Sokar" in leader_name:
                for card in self.board.get('close', []):
                    card.displayed_power += 1
            
            # Ba'al Clone: +2 power to all Ranged units
            elif "Ba'al Clone" in leader_name:
                for card in self.board.get('ranged', []):
                    card.displayed_power += 2
            
            # Bra'tac: All Agile cards gain +1 power
            elif "Bra'tac" in leader_name:
                for row_cards in self.board.values():
                    for card in row_cards:
                        if card.row == "agile":
                            card.displayed_power += 1
            
            # Sodan Master: +3 to highest unit in each row
            elif "Sodan Master" in leader_name:
                for row_name, row_cards in self.board.items():
                    if row_cards:
                        highest = max(row_cards, key=lambda c: c.displayed_power)
                        highest.displayed_power += 3
            
            # Heimdall: Legendary Commanders get +3 power
            elif "Heimdall" in leader_name:
                for row_cards in self.board.values():
                    for card in row_cards:
                        if is_hero(card):
                            card.displayed_power += 3
            
            # NEW UNLOCKABLE LEADERS - Power Bonuses
            
            # Cronus: Units get +1/+2/+3 per round number
            elif "Cronus" in leader_name:
                round_bonus = getattr(self, 'current_round_number', 1)
                for row_cards in self.board.values():
                    for card in row_cards:
                        card.displayed_power += round_bonus
            
            # Ishta: Gate Reinforcement units get +2 power
            elif "Ishta" in leader_name:
                for row_cards in self.board.values():
                    for card in row_cards:
                        if has_ability(card, Ability.GATE_REINFORCEMENT):
                            card.displayed_power += 2
            
            # Aegir: Draw 1 card when playing Siege units (handled in play_card())
            # Aegir has no passive scoring bonus - it's a draw ability

            # Gen. Landry: Units get +1 in row with most units
            elif "Landry" in leader_name:
                # Find row with most units
                max_count = 0
                max_row = None
                for row_name, row_cards in self.board.items():
                    if len(row_cards) > max_count:
                        max_count = len(row_cards)
                        max_row = row_name
                # Apply +1 to all units in that row
                if max_row:
                    for card in self.board[max_row]:
                        card.displayed_power += 1

            # Kiva: First unit each round gets +4 power
            elif "Kiva" in leader_name:
                for row_name, row_cards in self.board.items():
                    for card in row_cards:
                        if hasattr(card, 'kiva_boosted') and card.kiva_boosted:
                            card.displayed_power += 4

            # Thor Supreme Commander: Mothership cards get +3 power
            elif "Thor Supreme Commander" in leader_name:
                for row_cards in self.board.values():
                    for card in row_cards:
                        if "Mothership" in card.name or "O'Neill-Class" in card.name:
                            card.displayed_power += 3
            
            # Rya'c: Draw 2 extra cards at start of round 3 (handled in end_round())

            # Loki: Steal 1 power from opponent's strongest (done per turn, tracked separately)
            # This is applied when card is played, not in score calculation

        # Apply Tactical Formation ability
        for row_name, row_cards in self.board.items():
            bond_groups = {}
            for card in row_cards:
                if has_ability(card, Ability.TACTICAL_FORMATION):
                    if card.name not in bond_groups:
                        bond_groups[card.name] = []
                    bond_groups[card.name].append(card)

            for name, cards in bond_groups.items():
                if len(cards) > 1:
                    multiplier = len(cards)
                    for card in cards:
                        # Tactical Formation multiplies the card's BASE power
                        # We need to preserve bonuses already applied
                        bonuses_applied = card.displayed_power - card.power
                        card.displayed_power = (card.power * multiplier) + bonuses_applied

        # Apply Inspiring Leadership adjacency bonus
        for row_name, row_cards in self.board.items():
            for idx, card in enumerate(row_cards):
                if has_ability(card, Ability.INSPIRING_LEADERSHIP):
                    if idx > 0:
                        left_card = row_cards[idx - 1]
                        if not is_hero(left_card):
                            left_card.displayed_power += 1
                    if idx < len(row_cards) - 1:
                        right_card = row_cards[idx + 1]
                        if not is_hero(right_card):
                            right_card.displayed_power += 1

        # Apply Commander's Horn (doubles non-Legendary Commander units)
        # Track which cards have been multiplied to avoid double-stacking with ZPM
        horn_multiplied = set()
        for row_name, row_cards in self.board.items():
            if self.horn_effects[row_name]:
                for card in row_cards:
                    if not is_hero(card):
                        card.displayed_power *= 2
                        horn_multiplied.add(id(card))

        # Apply ZPM Power (doubles ALL siege units for the round)
        # Skip cards already multiplied by horn to prevent 4x stacking
        if self.zpm_active:
            for card in self.board.get("siege", []):
                if id(card) not in horn_multiplied:
                    card.displayed_power *= 2
        
        # Apply Faction Abilities that affect score
        if self.faction_ability:
            if hasattr(self.faction_ability, 'apply_to_score'):
                self.faction_ability.apply_to_score(self)
        
        # Apply Alliance Combos
        for alliance in ALLIANCE_COMBOS:
            if alliance.apply_bonus(self):
                activated_combos.append(alliance)
        
        # Apply Artifact Effects
        for artifact in self.artifacts:
            artifact.apply_effect(game, self)

        # Apply weather effects last so nothing can override them
        # Conquest relics: weather floor modifiers
        # Ori Prior Staff: weather sets non-heroes to 3 instead of 1
        # Jaffa Tretonin: weather can't reduce below 3
        weather_min = 1
        if game and hasattr(game, 'conquest_relics'):
            if self == game.player1:  # Only applies to player's cards
                if "ori_prior_staff" in game.conquest_relics:
                    weather_min = 3
                if "jaffa_tretonin" in game.conquest_relics:
                    weather_min = max(weather_min, 3)
        for row_name, row_cards in self.board.items():
            if self.weather_effects[row_name]:
                for card in row_cards:
                    if is_hero(card):
                        continue
                    if has_ability(card, Ability.SURVIVAL_INSTINCT):
                        card.displayed_power = card.power + 2
                    else:
                        card.displayed_power = weather_min

        # Sum the final scores
        self.score = 0
        for row in self.board.values():
            for card in row:
                self.score += card.displayed_power
        
        # Apply Neutral Penalty (Mercenary Tax)
        if self.neutral_penalty_active:
            self.score = round(self.score * 0.75)

        # Apply Ori Corruption (Naquadah over-budget penalty)
        if self.ori_corrupted:
            self.score = round(self.score * BALANCE_CONFIG["ori_corruption_penalty"])

        return activated_combos

    def draw_cards(self, num=1, track_for_jonas=False):
        """Draws a number of cards from the deck to the hand.

        Args:
            num: Number of cards to draw
            track_for_jonas: If True, track these cards for Jonas Quinn's ability
        """
        drawn = []
        for _ in range(num):
            if self.deck:
                card = self.deck.pop()
                self.hand.append(card)
                if track_for_jonas:
                    drawn.append(card)
        return drawn

    def spawn_oneill_clone(self):
        """Summon a temporary Jack O'Neill clone token to the close row."""
        if self.faction != FACTION_TAURI:
            return
        from cards import Card
        clone = Card(
            "tauri_oneill_clone",
            "Jack O'Neill Clone",
            self.faction,
            6,
            "close",
            "Temporary Clone",
        )
        clone.is_oneill_clone = True
        clone.clone_turns_remaining = 4  # removed when about to take 4th turn

        # Load the image for the clone card
        from cards import load_card_image
        load_card_image(clone)

        self.board["close"].append(clone)

    def decrement_clone_tokens(self):
        """Reduce lifetime on O'Neill clones and remove expired ones."""
        # Check this player's board for clone tokens
        for row_name, row_cards in self.board.items():
            for card in list(row_cards):
                if getattr(card, "is_oneill_clone", False):
                    card.clone_turns_remaining -= 1
                    if card.clone_turns_remaining <= 0:
                        row_cards.remove(card)
                        self.discard_pile.append(card)

class Game:
    """Manages the overall game state and logic."""

    def _get_leader_display_name(self, leader, faction, fallback):
        """Get display name from leader, with fallback options."""
        if leader and isinstance(leader, dict):
            name = leader.get('name', '')
            if name:
                return name
        if faction:
            return f"{faction} Commander"
        return fallback

    def __init__(self, player1_faction=FACTION_TAURI, player1_deck=None, player1_leader=None,
                 player2_faction=FACTION_GOAULD, player2_deck=None, player2_leader=None, seed=None,
                 player2_is_ai=False, player1_exempt_penalties=False):
        self.seed = seed if seed is not None else random.randint(0, 2**32 - 1)
        self.rng = random.Random(self.seed)

        player1_name = self._get_leader_display_name(player1_leader, player1_faction, "Player 1")
        player2_name = self._get_leader_display_name(player2_leader, player2_faction, "Player 2")
        self.player1 = Player(player1_name, player1_faction, player1_deck, player1_leader, rng=self.rng, is_ai=False, exempt_penalties=player1_exempt_penalties)
        self.player2 = Player(player2_name, player2_faction, player2_deck, player2_leader, rng=self.rng, is_ai=player2_is_ai)

        # Store faction info for stats tracking
        self.player1_faction = player1_faction
        self.player2_faction = player2_faction

        # Randomize who goes first (50/50 coin toss)
        self.current_player = self.rng.choice([self.player1, self.player2])
        self.player_went_first = (self.current_player == self.player1)
        
        # Stats tracking
        self.turn_count = 0
        self.player_mulligan_count = 0
        self.ability_usage = {"medic": 0, "decoy": 0, "faction_power": 0, "iris_blocks": 0}
        self.cards_played_ids = []
        
        self.round_number = 1
        self.game_state = "mulligan"  # Start with mulligan phase
        self.weather_active = {"close": False, "ranged": False, "siege": False}
        self.current_weather_types = {"close": None, "ranged": None, "siege": None}  # Track weather type per row
        self.weather_row_targets = {"close": None, "ranged": None, "siege": None}  # Which player's lane is affected
        self.weather_cards_on_board = {"close": None, "ranged": None, "siege": None}  # Weather visuals per row
        self.winner = None
        self.round_winner = None  # Track who won last round for missions
        self.round_history = []  # Track winner and scores for each round
        self.last_scorch_positions = []  # Track where Naquadah Overload destroyed cards (player, row_name)
        self.history = []
        self.history_dirty = False
        
        # Leader ability tracking
        self.cards_played_this_round = {self.player1: 0, self.player2: 0}
        self.leader_ability_used = {self.player1: False, self.player2: False}
        self.last_turn_actor = None

        # Jonas Quinn ability tracking - cards drawn by opponent AFTER mulligan
        self.opponent_drawn_cards = []  # Cards drawn by player2 during gameplay (for player1's Jonas)
        self.player1_drawn_cards = []  # Cards drawn by player1 during gameplay (for AI Jonas)

    def _owner_label(self, player):
        return "player" if player == self.player1 else "ai"

    def calculate_scores_and_log(self):
        """Calculate scores for both players and log any alliance combo activations."""
        # Calculate scores and get activated combos
        combos_p1 = self.player1.calculate_score(game=self)
        combos_p2 = self.player2.calculate_score(game=self)

        # Log Mercenary Tax penalties
        if self.player1.neutral_penalty_active:
            self.add_history_event(
                "ability",
                f"{self.player1.name} suffers Mercenary Tax! Score reduced by 25%",
                self._owner_label(self.player1),
                icon="!"
            )
        
        if self.player2.neutral_penalty_active:
            self.add_history_event(
                "ability",
                f"{self.player2.name} suffers Mercenary Tax! Score reduced by 25%",
                self._owner_label(self.player2),
                icon="!"
            )

        # Log Ori Corruption penalties
        if self.player1.ori_corrupted:
            self.add_history_event(
                "ability",
                f"{self.player1.name} suffers Ori Corruption! Score reduced by 50%",
                self._owner_label(self.player1),
                icon="⚠"
            )

        if self.player2.ori_corrupted:
            self.add_history_event(
                "ability",
                f"{self.player2.name} suffers Ori Corruption! Score reduced by 50%",
                self._owner_label(self.player2),
                icon="⚠"
            )

        # Log alliance combo activations
        for combo in combos_p1:
            self.add_history_event(
                "alliance",
                f"{self.player1.name} activated {combo.name}: {combo.description}",
                self._owner_label(self.player1),
                icon="🤝"
            )

        for combo in combos_p2:
            self.add_history_event(
                "alliance",
                f"{self.player2.name} activated {combo.name}: {combo.description}",
                self._owner_label(self.player2),
                icon="🤝"
            )

    def add_history_event(self, event_type, description, owner, card_ref=None, icon=None, row=None, delta=0, targets=None):
        """Append a new entry to the history log."""
        scores = (self.player1.score, self.player2.score)
        entry = GameHistoryEntry(event_type, description, owner, card_ref=card_ref, icon=icon, row=row, delta=delta, targets=targets, turn_number=self.turn_count, scores=scores)
        self.history.append(entry)
        if len(self.history) > 200:
            self.history.pop(0)
        self.history_dirty = True
        
        # Trigger external callback (e.g. for chat/narrator)
        if hasattr(self, 'on_history_event') and self.on_history_event:
            self.on_history_event(entry)
            
        return entry

    def _log_card_play(self, player, card, row_name=None, note=None):
        """Helper to log standard card plays with power info."""
        # Include power for unit cards
        delta = 0
        if card.row in ["close", "ranged", "siege", "agile"]:
            power_str = f" [{card.power}]"
            delta = card.displayed_power if card.displayed_power else card.power
        else:
            power_str = ""

        desc = f"{player.name} deployed {card.name}{power_str}"
        if row_name:
            row_display = {"close": "Close", "ranged": "Ranged", "siege": "Siege"}.get(row_name, row_name.title())
            desc += f" → {row_display}"
        if note:
            desc += f" ({note})"

        # Select appropriate icon based on card type
        if is_hero(card):
            icon = "*"
        elif is_spy(card):
            icon = "?"
        elif card.row == "weather":
            icon = "~"
        elif card.row == "special":
            icon = "*"
        else:
            icon = ">"

        self.add_history_event("card_play", desc, self._owner_label(player), card_ref=card, row=row_name, icon=icon, delta=delta)

    def _apply_leader_round_start_effects(self, player):
        """Handle leader-specific triggers that occur at round start."""
        # First, decrement all clone tokens at round start
        self.decrement_all_clone_tokens()

        if not player.leader:
            return
        leader_name = player.leader.get('name', '')
        if "O'Neill" in leader_name:
            player.spawn_oneill_clone()
            self.add_history_event(
                "ability",
                f"{player.name} (O'Neill) summoned a 6-power clone",
                self._owner_label(player),
                icon="++"
            )

    def discard_active_weather_cards(self):
        """Move any weather cards sitting on the board into their owners' discard piles."""
        any_active = False
        for row_name, entry in self.weather_cards_on_board.items():
            if not entry:
                continue
            any_active = True
            card = entry.get("card")
            owner = entry.get("owner")
            if owner and card:
                owner.discard_pile.append(card)
            self.weather_cards_on_board[row_name] = None
        return any_active
    
    def _set_weather_slot(self, row_key, entry):
        """Place (and replace) weather card visuals for a specific row."""
        if row_key not in self.weather_cards_on_board:
            return
        existing = self.weather_cards_on_board.get(row_key)
        if existing and existing.get("card"):
            owner = existing.get("owner")
            if owner:
                owner.discard_pile.append(existing["card"])
        self.weather_cards_on_board[row_key] = entry

    def start_game(self):
        """Starts the game, deals initial hands."""
        # Draw 10 cards for mulligan phase (Tau'ri draws 11)
        for p in [self.player1, self.player2]:
            initial_cards = 11 if p.faction == FACTION_TAURI else 10
            p.draw_cards(initial_cards)
    
    def mulligan(self, player, cards_to_redraw):
        """Performs mulligan - returns selected cards to deck and draws new ones.
        Player can redraw between 2-5 cards."""
        num_cards = len(cards_to_redraw)
        
        # Enforce 2-5 card limit
        if num_cards < 2 or num_cards > 5:
            return  # Invalid mulligan
        
        for card in cards_to_redraw:
            if card in player.hand:
                player.hand.remove(card)
                player.deck.append(card)
        
        if player == self.player1:
            self.player_mulligan_count = getattr(self, "player_mulligan_count", 0) + num_cards
            
        self.rng.shuffle(player.deck)
        player.draw_cards(len(cards_to_redraw))
    
    def end_mulligan_phase(self):
        """Ends mulligan phase and starts the game."""
        self.game_state = "playing"
        for player in [self.player1, self.player2]:
            self._apply_leader_round_start_effects(player)

    def switch_turn(self):
        """Switches the turn to the other player, handling passed players."""
        # Check if Hathor's ability animation is complete
        if hasattr(self.current_player, 'hathor_ability_pending'):
            pending = self.current_player.hathor_ability_pending
            if pending:
                # Add the stolen card to the player's board
                self.current_player.board[pending['target_row']].append(pending['card'])
                self.current_player.hathor_ability_pending = None
                
                # Add history event
                self.add_history_event(
                    "ability",
                    f"{self.current_player.name} (Hathor) stole {pending['card'].name}",
                    self._owner_label(self.current_player),
                    card_ref=pending['card']
                )

                # Recalculate scores
                self.calculate_scores_and_log()
        if self.last_turn_actor:
            self.last_turn_actor = None
        if self.player1.has_passed and self.player2.has_passed:
            self.end_round()
            return

        if self.current_player == self.player1:
            self.current_player = self.player2
        else:
            self.current_player = self.player1
        # Track turn changes
        self.turn_count += 1
        
        # Reset plays this turn counter when switching turns
        self.current_player.plays_this_turn = 0
        
        if self.current_player.has_passed:
            self.switch_turn() # Skip player if they have passed

    def play_card(self, card, row_name, target_side=None, index=None):
        """Plays a card from the current player's hand to the board.
        
        Args:
            card: Card object to play
            row_name: Target row ('close', 'ranged', 'siege')
            target_side: Optional side override (e.g. for spy cards)
            index: Optional insertion index in the row
        """
        if self.current_player.has_passed:
            return # Passed players can't play cards
        
        # Check for Rak'nor ability: Can play 2 cards on first turn each round
        player = self.current_player
        max_plays_this_turn = 1
        if player.leader and "Rak'nor" in player.leader.get('name', ''):
            # Allow 2 cards on first turn of each round
            if self.cards_played_this_round[player] == 0:
                max_plays_this_turn = 2
        
        # Check if player has reached play limit for this turn
        if player.plays_this_turn >= max_plays_this_turn:
            return  # Can't play more cards this turn
        
        # Check if opponent has Iris active
        opponent = self.player2 if self.current_player == self.player1 else self.player1
        if hasattr(opponent, 'iris_defense') and opponent.iris_defense.is_active():
            # Card is blocked and destroyed
            self.current_player.hand.remove(card)
            self.discard_card(self.current_player, card, color_variant='red')
            opponent.iris_defense.deactivate()
            if opponent == self.player1:
                self.ability_usage["iris_blocks"] = self.ability_usage.get("iris_blocks", 0) + 1

            # Log the blocked card in history
            blocker_label = "player" if opponent == self.player1 else "opponent"
            self.add_history_event(
                "special",
                f"Iris blocked {card.name}!",
                blocker_label,
                card_ref=card,
                icon="[#]"
            )

            self.switch_turn()
            return

        if card in self.current_player.hand:
            self.current_player.hand.remove(card)
            self.last_turn_actor = player
            
            # Record card play for stats
            if self.current_player == self.player1:
                card_id = getattr(card, "id", None)
                if card_id:
                    self.cards_played_ids.append(card_id)
                elif hasattr(card, "name"):
                     # Fallback for dynamic cards
                    self.cards_played_ids.append(card.name)
            
            # Handle weather cards
            if card.row == "weather":
                self.current_player.weather_cards_played += 1
                ability = card.ability or ""
                affected_rows = self.apply_weather_effect(card, row_name, target_side or "both")
                if "Wormhole Stabilization" not in ability:
                    for affected_row in affected_rows:
                        self._set_weather_slot(affected_row, {"card": card, "owner": self.current_player})
                note = f"Weather → {', '.join(r.title() for r in affected_rows)}" if affected_rows else "Weather"
                self._log_card_play(player, card, note=note)
                self.calculate_scores_and_log()
                player.plays_this_turn += 1
                self.switch_turn()
                return
            
            # Handle special cards
            if card.row == "special":
                # Check if this is a Command Network (horn) card
                if has_ability(card, Ability.COMMAND_NETWORK):
                    # Apply horn effect but don't discard the card - it stays in the horn slot
                    self.apply_special_effect(card, row_name)
                    self._log_card_play(player, card, row_name=row_name, note="Horn")
                    self.calculate_scores_and_log()
                    player.plays_this_turn += 1
                    self.switch_turn()
                    return
                else:
                    # Regular special cards go to discard pile
                    self.apply_special_effect(card, row_name)
                    self.current_player.discard_pile.append(card)
                    self._log_card_play(player, card, row_name=row_name, note="Special")
                    self.calculate_scores_and_log()
                    player.plays_this_turn += 1
                    self.switch_turn()
                    return

            # Validate row placement for unit cards
            valid_rows = ["close", "ranged", "siege"]
            if card.row == "agile":
                valid_rows = ["close", "ranged"]
            elif card.row in valid_rows:
                valid_rows = [card.row]
            else:
                self.current_player.hand.append(card)  # Return card if invalid
                self.last_turn_actor = None
                return
            
            if row_name not in valid_rows:
                self.current_player.hand.append(card)  # Return card if invalid
                self.last_turn_actor = None
                return

            player = self.current_player
            target_player = self.current_player
            card_is_spy = is_spy(card)

            # Deep Cover Agent ability logic with Lucian faction bonus and Vulkar leader ability
            if card_is_spy:
                if self.current_player == self.player1:
                    target_player = self.player2
                else:
                    target_player = self.player1

                # Conquest Iris Shield relic: block first spy played against player1
                conquest_relics = getattr(self, 'conquest_relics', [])
                if (conquest_relics and "iris_shield" in conquest_relics
                        and target_player == self.player1
                        and not getattr(self, '_iris_shield_used', False)):
                    self._iris_shield_used = True
                    # Spy is blocked — card goes to discard, no board placement
                    self.current_player.discard_pile.append(card)
                    self.add_history_event(
                        "ability",
                        f"Iris Shield blocked {card.name}! Spy neutralized.",
                        self._owner_label(self.player1),
                        card_ref=card, icon="O"
                    )
                    self.calculate_scores_and_log()
                    self.last_turn_actor = self.current_player
                    self.switch_turn()
                    return

                # Track spies played this round for Lucian Network combo
                player.spies_played_this_round += 1

                # Check for Lucian Network combo (2+ spies = draw 1 extra card)
                if LUCIAN_NETWORK_COMBO.check_active(player):
                    LUCIAN_NETWORK_COMBO.apply_bonus(player)
                    player.draw_cards(1)
                    self.add_history_event(
                        "combo",
                        "Lucian Network activated! Drew 1 extra card.",
                        self._owner_label(player),
                        icon="🕵️"
                    )

                # Varro leader ability: ALL spy cards draw 3 (bypasses once-per-round limit)
                draw_amount = 2
                if player.leader and "Varro" in player.leader.get('name', ''):
                    draw_amount = 3
                elif player.faction_ability and hasattr(player.faction_ability, 'get_spy_draw_amount'):
                    draw_amount = player.faction_ability.get_spy_draw_amount()
                player.draw_cards(draw_amount)

            # Add card to board (respecting insertion index if provided)
            if index is not None and 0 <= index <= len(target_player.board[row_name]):
                target_player.board[row_name].insert(index, card)
            else:
                target_player.board[row_name].append(card)

            # Fire materialization callback (UI spawns converging-particle effect)
            if self._on_card_played:
                self._on_card_played(card, row_name, target_player)

            # Log standard play
            self._log_card_play(player, card, row_name=row_name, note="Spy" if card_is_spy else None)
            
            # Narrate specific passive abilities on play
            if has_ability(card, Ability.INSPIRING_LEADERSHIP):
                self.add_history_event(
                    "ability",
                    f"{card.name} inspires adjacent units!",
                    self._owner_label(player),
                    card_ref=card,
                    icon="💚"
                )
            if has_ability(card, Ability.SYSTEM_LORDS_CURSE):
                self.add_history_event(
                    "ability",
                    f"{card.name} curses the enemy row!",
                    self._owner_label(player),
                    card_ref=card,
                    icon="💀"
                )

            # === CARD PLAY AUDIO ===
            sound_manager = get_sound_manager()
            if is_hero(card):
                # Legendary commanders get their unique voice snippet
                sound_manager.play_commander_snippet(card.id, volume=0.7)
            elif card.id == "goauld_symbiote":
                # Symbiote has its own sound effect triggered in add_special_card_effect
                pass
            elif row_name in ('close', 'ranged', 'siege'):
                # Regular unit cards get row-type sound
                sound_manager.play_row_sound(row_name, volume=0.5)

            # Track cards played this round for leader abilities
            self.cards_played_this_round[player] += 1
            player.units_played_this_round += 1
            player.plays_this_turn += 1  # Track plays this turn for Rak'nor ability
            
            # === SIMPLE DRAW ABILITIES (when card is played) ===
            # Prometheus BC-303: Draw 1 card when played
            if "Prometheus" in card.name:
                player.draw_cards(1)
            
            # Asgard Mothership: Draw 2 cards when played
            elif "Asgard Mothership" in card.name or "Mothership" in card.name:
                player.draw_cards(2)
            
            # === LEADER ABILITIES - PER UNIT ===
            
            # Ka'lel: First 3 units each round get +2 power
            if player.leader and "Ka'lel" in player.leader.get('name', ''):
                if player.units_played_this_round <= 3:
                    # Mark card as Ka'lel boosted
                    if not hasattr(card, 'kalel_boosted'):
                        card.kalel_boosted = True
            
            # Gerak: Draw 1 card for every 2 units played
            if player.leader and "Gerak" in player.leader.get('name', ''):
                if player.units_played_this_round % 2 == 0:
                    player.draw_cards(1)
            
            # Gen. Hammond ability: First unit each round gets +3 power
            if player.leader and "Hammond" in player.leader.get('name', ''):
                if self.cards_played_this_round[player] == 1 and card.row not in ["special", "weather"]:
                    # Mark card as Hammond boosted so it survives calculate_score()
                    if not hasattr(card, 'hammond_boosted'):
                        card.hammond_boosted = True

            # Kiva: First unit each round gets +4 power
            if player.leader and "Kiva" in player.leader.get('name', ''):
                if self.cards_played_this_round[player] == 1 and card.row not in ["special", "weather"]:
                    if not hasattr(card, 'kiva_boosted'):
                        card.kiva_boosted = True
                        self.add_history_event(
                            "ability",
                            f"{player.name} (Kiva) Brutal Tactics: {card.name} gets +4 power!",
                            self._owner_label(player),
                            icon="X"
                        )

            # Aegir: Draw 1 card when playing Siege unit
            if player.leader and "Aegir" in player.leader.get('name', ''):
                if card.row == "siege":
                    player.draw_cards(1)
                    self.add_history_event(
                        "ability",
                        f"{player.name} (Aegir) Asgard Archives: Drew 1 card from siege deployment",
                        self._owner_label(player),
                        icon="+"
                    )
            
            # Loki ability: Steal 1 power from opponent's strongest unit (permanent)
            if player.leader and "Loki" in player.leader.get('name', ''):
                opponent = self.player2 if player == self.player1 else self.player1
                all_opponent_units = []
                for row_cards in opponent.board.values():
                    all_opponent_units.extend([c for c in row_cards if not is_hero(c)])
                if all_opponent_units:
                    strongest = max(all_opponent_units, key=lambda c: c.power)
                    if strongest.power > 1:
                        new_power = max(1, strongest.power - 1)
                        strongest.power = new_power
                        strongest.displayed_power = new_power
                        # Add power to a random friendly unit
                        friendly_units = [c for row in player.board.values() for c in row if not is_hero(c)]
                        if friendly_units:
                            boosted = self.rng.choice(friendly_units)
                            boosted.power += 1
                            boosted.displayed_power += 1
                        self.add_history_event(
                            "ability",
                            f"{player.name} (Loki) stole 1 power from {strongest.name}",
                            self._owner_label(player),
                            icon="⚡"
                        )


            # Trigger Gate Reinforcement ability
            if has_ability(card, Ability.GATE_REINFORCEMENT):
                self.trigger_muster(card, target_player, row_name)

            # Trigger Deploy Clones
            if has_ability(card, Ability.DEPLOY_CLONES):
                self.trigger_summon_shield_maidens(target_player, row_name)

            # Trigger Grant ZPM
            if has_ability(card, Ability.GRANT_ZPM):
                self.trigger_grant_zpm(target_player)

            # Trigger Activate Combat Protocol
            if has_ability(card, Ability.ACTIVATE_COMBAT_PROTOCOL):
                self.trigger_summon_avenger(target_player, row_name)

            # Trigger Genetic Enhancement (transforms weakest units)
            if has_ability(card, Ability.GENETIC_ENHANCEMENT):
                self.trigger_mardroeme(target_player)

            # Trigger Medical Evac ability - Check if player should choose
            if has_ability(card, Ability.MEDICAL_EVAC):
                # If there are valid revive targets, the UI will handle selection.
                # If none are available, treat as a normal play and end the turn.
                if self.get_medic_valid_cards(player):
                    return

            # Non-medic cards OR medic with no valid targets switch turn normally
            self.calculate_scores_and_log()
            self.switch_turn()

    def pass_turn(self):
        """The current player passes their turn."""
        if not self.current_player.has_passed:
            passing_player = self.current_player
            passing_player.has_passed = True
            self.add_history_event("pass", f"{passing_player.name} passed", self._owner_label(passing_player))
            
            # Apply leader abilities when passing
            if passing_player.leader:
                leader_name = passing_player.leader.get('name', '')
                # Dr. McKay: Draw 2 cards when you pass
                if "McKay" in leader_name:
                    passing_player.draw_cards(2)
                    self.add_history_event(
                        "ability",
                        f"{passing_player.name} (McKay) drew 2 cards when passing",
                        self._owner_label(passing_player),
                        icon="+2"
                    )
                # Lord Yu: Reveal opponent's hand when you pass (once per game)
                elif "Yu" in leader_name:
                    if not getattr(passing_player, 'yu_ability_used', False):
                        opponent = self.player2 if passing_player == self.player1 else self.player1
                        self.add_history_event(
                            "ability",
                            f"{passing_player.name} (Lord Yu) will see {opponent.name}'s hand next round",
                            self._owner_label(passing_player),
                            icon="👁️"
                        )
                        opponent.reveal_next_round = True
                        passing_player.yu_ability_used = True
            self.last_turn_actor = passing_player
            self.switch_turn()

    def trigger_muster(self, played_card, player, row_name):
        """Finds and plays all cards with the same name from hand and deck."""
        card_name_to_muster = played_card.name
        
        # Gate Reinforcement from hand
        cards_from_hand = [c for c in player.hand if c.name == card_name_to_muster]
        for card in cards_from_hand:
            player.hand.remove(card)
            player.board[row_name].append(card)

        # Gate Reinforcement from deck
        cards_from_deck = [c for c in player.deck if c.name == card_name_to_muster]
        for card in cards_from_deck:
            player.deck.remove(card)
            player.board[row_name].append(card)
        
        total_mustered = len(cards_from_hand) + len(cards_from_deck) + 1
        
        if total_mustered > 1:
            self.add_history_event(
                "ability",
                f"{player.name} mustered {total_mustered-1} reinforcements!",
                self._owner_label(player),
                icon=">>"
            )

        # Life Force Drain siphons enemy strength and boosts the muster group
        if has_ability(played_card, Ability.LIFE_FORCE_DRAIN):
            self.trigger_life_force_drain(player, played_card, total_mustered)

        # System Lord's Curse weakens the opposing row after the muster resolves
        if has_ability(played_card, Ability.SYSTEM_LORDS_CURSE):
            self.trigger_system_lords_curse(player, row_name)

        # Check for Vampire ability (life steal)
        if has_ability(played_card, Ability.VAMPIRE):
            self.trigger_vampire(player, total_mustered)

        # Check for Crone ability (weaken opponent)
        if has_ability(played_card, Ability.CRONE):
            self.trigger_crone(player, row_name)
    
    def trigger_vampire(self, player, num_cards):
        """Vampire: Steal 1 power from random opponent unit for each mustered card."""
        opponent = self.player2 if player == self.player1 else self.player1
        
        for _ in range(num_cards):
            # Find all opponent units with power > 1
            drainable_units = []
            for row_cards in opponent.board.values():
                for card in row_cards:
                    if card.displayed_power > 1 and not is_hero(card):
                        drainable_units.append(card)
            
            if drainable_units:
                # Drain power from random unit
                target = self.rng.choice(drainable_units)
                new_power = max(1, target.power - 1)
                target.power = new_power
                target.displayed_power = new_power
    
    def trigger_crone(self, player, row_name):
        """Crone: Weaken all opponent units in the same row by 1 (min 1)."""
        opponent = self.player2 if player == self.player1 else self.player1
        
        # Weaken all opponent units in same row
        for card in opponent.board.get(row_name, []):
            if not is_hero(card):
                new_power = max(1, card.power - 1)
                card.power = new_power
                card.displayed_power = new_power
    
    def trigger_life_force_drain(self, player, played_card, num_cards):
        """Life Force Drain: steal 1 power from random enemy unit per muster copy and funnel to the squad."""
        opponent = self.player2 if player == self.player1 else self.player1
        muster_group = []
        for row_cards in player.board.values():
            for card in row_cards:
                if card.name == played_card.name:
                    muster_group.append(card)
        if not muster_group:
            muster_group = [played_card]
        
        for _ in range(num_cards):
            drainable_units = []
            for row_cards in opponent.board.values():
                for card in row_cards:
                    if is_hero(card):
                        continue
                    if card.power > 1:
                        drainable_units.append(card)
            if not drainable_units:
                break
            target = self.rng.choice(drainable_units)
            target.power = max(1, target.power - 1)
            target.displayed_power = min(target.displayed_power, target.power)
            
            recipient = self.rng.choice(muster_group)
            recipient.power += 1
            recipient.displayed_power += 1
    
    def trigger_system_lords_curse(self, player, row_name):
        """System Lord's Curse: weaken opposing units in the mirrored row by 1 (min 1)."""
        opponent = self.player2 if player == self.player1 else self.player1
        for card in opponent.board.get(row_name, []):
            if is_hero(card):
                continue
            new_power = max(1, card.power - 1)
            card.power = new_power
            card.displayed_power = min(card.displayed_power, new_power)
    
    def trigger_summon_shield_maidens(self, player, row_name):
        """Deploy Clones: Add 2 Shield Maiden tokens (2 power each) to the row."""
        # Create token cards (not in deck, just spawned)
        from cards import Card, load_card_image
        maiden1 = Card("token_maiden_1", "Shield Maiden", player.faction, 2, row_name, None)
        maiden2 = Card("token_maiden_2", "Shield Maiden", player.faction, 2, row_name, None)
        # Load images for tokens
        load_card_image(maiden1)
        load_card_image(maiden2)
        player.board[row_name].append(maiden1)
        player.board[row_name].append(maiden2)

    def trigger_summon_avenger(self, player, row_name):
        """Activate Combat Protocol: Add 1 Avenger token (5 power) to the row."""
        from cards import Card, load_card_image
        avenger = Card("token_avenger", "Asgard Avenger", player.faction, 5, row_name, None)
        avenger.image_path = "assets/asgard_clone_incubator.png"
        load_card_image(avenger)
        player.board[row_name].append(avenger)
    
    def trigger_grant_zpm(self, player):
        """Grant ZPM: Add a Zero Point Module card to the player's hand."""
        from cards import Card, FACTION_NEUTRAL
        # Create ZPM card
        zpm = Card("zpm_power", "Zero Point Module", FACTION_NEUTRAL, 0, "special", "Double all your siege units this round")
        player.hand.append(zpm)
        self.add_history_event(
            "ability",
            f"{player.name} obtained a Zero Point Module!",
            self._owner_label(player),
            icon="⚡",
            card_ref=zpm
        )
    
    def trigger_mardroeme(self, player):
        """Genetic Enhancement: Transform weakest unit in each row into a 8-power berserker."""
        for row_name, row_cards in player.board.items():
            if not row_cards:
                continue
            
            # Find weakest non-Legendary Commander unit
            weakest = None
            for card in row_cards:
                if not is_hero(card):
                    if weakest is None or card.power < weakest.power:
                        weakest = card

            if weakest:
                # Transform into berserker
                weakest.power = 8
                weakest.displayed_power = 8
                if weakest.ability:
                    if not has_ability(weakest, Ability.SURVIVAL_INSTINCT):
                        weakest.ability += ", Survival Instinct"
                else:
                    weakest.ability = "Survival Instinct"
    
    def trigger_medic(self, player, selected_card=None):
        """Revives a non-Legendary Commander unit card from discard pile."""
        valid_cards = [c for c in player.discard_pile if not is_hero(c) and c.row in ["close", "ranged", "siege", "agile"]]
        
        if not valid_cards:
            return None  # No valid cards to revive
        
        if selected_card and selected_card in valid_cards:
            # Player manually selected a card
            revived = selected_card
        else:
            # Auto-pick first card (for AI or no selection)
            revived = valid_cards[0]
        
        player.discard_pile.remove(revived)
        # Place in appropriate row
        target_row = revived.row if revived.row != "agile" else "close"
        player.board[target_row].append(revived)
        if player == self.player1:
            self.ability_usage["medic"] = self.ability_usage.get("medic", 0) + 1
        return revived
    
    def get_medic_valid_cards(self, player):
        """Get list of valid cards that can be revived by medic."""
        return [c for c in player.discard_pile if not is_hero(c) and c.row in ["close", "ranged", "siege", "agile"]]

    def trigger_hathor_ability(self, player):
        """Trigger Hathor's ability to steal the lowest power card from opponent."""
        if not player.leader or "Hathor" not in player.leader.get('name', ''):
            return False

        opponent = self.player2 if player == self.player1 else self.player1

        # Find the lowest power card on opponent's board
        lowest_card = None
        lowest_power = float('inf')
        lowest_row = None

        for row_name, row_cards in opponent.board.items():
            for card in row_cards:
                # Skip Legendary Commanders and special cards
                if is_hero(card) or card.row in ["special", "weather"]:
                    continue

                if card.power < lowest_power:
                    lowest_power = card.power
                    lowest_card = card
                    lowest_row = row_name

        if lowest_card:
            from_index = opponent.board[lowest_row].index(lowest_card)
            # Store the card info for animation
            self.hathor_steal_info = {
                'card': lowest_card,
                'card_id': getattr(lowest_card, "id", None),
                'from_row': lowest_row,
                'from_index': from_index,
                'from_player': opponent,
                'to_player': player,
                'target_row': lowest_row if lowest_row in player.board and lowest_row not in ["special", "weather"] else "close",
                'animation_start': pygame.time.get_ticks(),
                'animation_started': False
            }

            # Remove card from opponent's board
            opponent.board[lowest_row].remove(lowest_card)

            # Add to player's board (will be done after animation)
            # Determine which row to place it in (prefer same row if possible)
            target_row = lowest_row if lowest_row in player.board and lowest_row not in ["special", "weather"] else "close"

            # Mark that Hathor's ability is being used
            player.hathor_ability_pending = {
                'card': lowest_card,
                'target_row': target_row
            }

            return True

        return False
    
    def apply_weather_effect(self, card, target_row=None, target_side="both"):
        """Applies weather effects to rows and returns affected row names."""
        ability = card.ability or ""
        affected_rows = []
        acting_player = self.current_player
        opponent = self.player2 if acting_player == self.player1 else self.player1

        def has_leader(player, name):
            return player.leader and name in player.leader.get('name', '')

        weather_sound_played = False

        if "Wormhole Stabilization" in ability:
            # Clears all weather
            self.discard_active_weather_cards()
            self.weather_active = {"close": False, "ranged": False, "siege": False}
            self.current_weather_types = {"close": None, "ranged": None, "siege": None}
            self.weather_row_targets = {"close": None, "ranged": None, "siege": None}
            for p in [self.player1, self.player2]:
                p.weather_effects = {"close": False, "ranged": False, "siege": False}
            self.add_history_event(
                "weather",
                f"{acting_player.name} cleared all weather effects!",
                self._owner_label(acting_player),
                icon="O"
            )
            try:
                get_sound_manager().play_weather_sound("clear")
                weather_sound_played = True
            except Exception as e:
                logger.warning(f"Failed to play weather clear sound: {e}")
            return affected_rows

        # Asgard shielding: opponent can block the first enemy weather each round
        if acting_player != opponent:
            faction_ability = getattr(opponent, "faction_ability", None)
            if faction_ability and hasattr(faction_ability, "can_block_weather"):
                if faction_ability.can_block_weather():
                    # Weather was blocked by Asgard Shield
                    weather_name = ability.replace("Ice Planet Hazard", "Ice Planet") \
                                          .replace("Nebula Interference", "Nebula") \
                                          .replace("Asteroid Storm", "Meteor Shower") \
                                          .replace("Electromagnetic Pulse", "EMP")
                    self.add_history_event(
                        "blocked",
                        f"{weather_name} blocked! {opponent.name}'s Asgard Shield deflected it",
                        self._owner_label(acting_player),
                        icon="🛡"
                    )
                    return affected_rows

        # Freyr leader: completely immune to weather
        freyr_owner = next((p for p in [self.player1, self.player2] if has_leader(p, "Freyr")), None)

        # Hermiod leader: weather affects only the opponent
        hermiod_targets_opponent_only = has_leader(acting_player, "Hermiod")

        def apply_row_weather(row_key, weather_type, forced_side=None):
            self.weather_active[row_key] = True
            self.current_weather_types[row_key] = weather_type
            for target in [self.player1, self.player2]:
                target.weather_effects[row_key] = False

            side_to_affect = forced_side or target_side or "both"
            if side_to_affect == "self":
                desired_targets = [acting_player]
            elif side_to_affect == "both":
                desired_targets = [acting_player, opponent]
            else:
                desired_targets = [opponent]

            if hermiod_targets_opponent_only:
                desired_targets = [opponent]

            actual_targets = []
            for target in desired_targets:
                if target == freyr_owner:
                    continue
                target.weather_effects[row_key] = True
                actual_targets.append(target)

            if not actual_targets:
                self.weather_active[row_key] = False
                self.current_weather_types[row_key] = None
                self.weather_row_targets[row_key] = None
                return False

            affects_player1 = any(t == self.player1 for t in actual_targets)
            affects_player2 = any(t == self.player2 for t in actual_targets)
            if affects_player1 and affects_player2:
                self.weather_row_targets[row_key] = "both"
            elif affects_player1:
                self.weather_row_targets[row_key] = "player1"
            else:
                self.weather_row_targets[row_key] = "player2"
            return True

        if "Ice Planet Hazard" in ability:
            if apply_row_weather("close", "Ice Planet Hazard"):
                affected_rows.append("close")
        elif "Nebula Interference" in ability:
            if apply_row_weather("ranged", "Nebula Interference"):
                affected_rows.append("ranged")
        elif "Asteroid Storm" in ability:
            if apply_row_weather("siege", "Asteroid Storm"):
                affected_rows.append("siege")
        elif "Electromagnetic Pulse" in ability:
            row_key = target_row if target_row in ["close", "ranged", "siege"] else "close"
            if apply_row_weather(row_key, "Electromagnetic Pulse"):
                affected_rows.append(row_key)

        # Add history event for weather application
        if affected_rows:
            weather_name = ability.replace("Ice Planet Hazard", "Ice Planet") \
                                  .replace("Nebula Interference", "Nebula") \
                                  .replace("Asteroid Storm", "Meteor Shower") \
                                  .replace("Electromagnetic Pulse", "EMP")
            rows_text = ", ".join([r.title() for r in affected_rows])
            self.add_history_event(
                "weather",
                f"{acting_player.name} played {weather_name} on {rows_text}",
                self._owner_label(acting_player),
                icon="~"
            )
            if not weather_sound_played:
                try:
                    sound_key = weather_name.lower().replace(" ", "_")
                    get_sound_manager().play_weather_sound(sound_key)
                except Exception as e:
                    logger.warning(f"Failed to play weather sound '{sound_key}': {e}")
        else:
            # Weather was blocked by immunity
            weather_name = ability.replace("Ice Planet Hazard", "Ice Planet") \
                                  .replace("Nebula Interference", "Nebula") \
                                  .replace("Asteroid Storm", "Meteor Shower") \
                                  .replace("Electromagnetic Pulse", "EMP")
            if freyr_owner:
                self.add_history_event(
                    "blocked",
                    f"{weather_name} blocked! {freyr_owner.name} has weather immunity (Freyr)",
                    self._owner_label(acting_player),
                    icon="🛡"
                )
            else:
                self.add_history_event(
                    "blocked",
                    f"{weather_name} had no valid targets!",
                    self._owner_label(acting_player),
                    icon="⚠"
                )

        return affected_rows

    def can_use_leader_ability(self, player):
        """Check if the player still has a leader ability available."""
        if not player or not player.leader:
            return False
        return not self.leader_ability_used.get(player, False)

    def activate_leader_ability(self, player):
        """Activate the player's once-per-game leader ability, if available."""
        if not self.can_use_leader_ability(player):
            return None
        leader_name = player.leader.get('name', '')
        result = None
        if "Apophis" in leader_name:
            result = self._activate_apophis_weather(player)
        elif "Catherine Langford" in leader_name:
            result = self._activate_catherine_knowledge(player)
        elif "Ba'al" in leader_name and "Clone" not in leader_name:
            result = self._activate_baal_resurrection(player)
        elif "Jonas Quinn" in leader_name:
            result = self._activate_jonas_memory(player)
        if result:
            # Only mark as used if the ability doesn't require UI interaction
            # UI-requiring abilities will set the flag in their completion functions
            if not isinstance(result, dict) or not result.get("requires_ui", False):
                self.leader_ability_used[player] = True
                self.calculate_scores_and_log()
        return result

    def apply_remote_leader_ability(self, player, payload):
        """Replay a peer's leader ability using provided data."""
        if not player or not payload:
            return False

        ability = payload.get("ability", "")
        if not ability:
            return False

        # Prevent double-activation locally
        if self.leader_ability_used.get(player, False):
            return False

        # Apophis: weather decree
        if ability in ("Ice Planet Hazard", "Nebula Interference", "Asteroid Storm", "Electromagnetic Pulse"):
            rows = payload.get("rows") or []
            template_candidates = [
                c for c in ALL_CARDS.values()
                if c.row == "weather" and (c.ability or "") == ability
            ]
            if not template_candidates:
                return False
            weather_card = copy.deepcopy(template_candidates[0])
            target_rows = rows or ["close"]
            for row_name in target_rows:
                self.apply_weather_effect(weather_card, row_name, target_side="both")
                self._set_weather_slot(row_name, {"card": weather_card, "owner": None})
            self.calculate_scores_and_log()
            # Mark as used only after successful completion
            self.leader_ability_used[player] = True
            return True

        # Catherine Langford: choose one of top three cards
        if ability == "Ancient Knowledge":
            revealed_ids = payload.get("revealed_ids") or []
            choice_id = payload.get("choice_id")
            top_cards = []
            if revealed_ids:
                for cid in revealed_ids:
                    card = next((c for c in player.deck if getattr(c, "id", None) == cid), None)
                    if card and card not in top_cards:
                        top_cards.append(card)
            if not top_cards:
                top_cards = list(player.deck[:min(3, len(player.deck))])

            # Remove the revealed cards from the top of the deck
            for card in top_cards:
                if card in player.deck:
                    player.deck.remove(card)

            chosen_card = next((c for c in top_cards if getattr(c, "id", None) == choice_id), None)
            if chosen_card:
                player.hand.append(chosen_card)
                self.add_history_event(
                    "ability",
                    f"{player.name} used Ancient Knowledge and drew {chosen_card.name}",
                    self._owner_label(player),
                    card_ref=chosen_card
                )
                # Mark as used only after successful completion
                self.leader_ability_used[player] = True

            # Put the rest at the bottom of the deck preserving reveal order
            for card in top_cards:
                if card != chosen_card:
                    player.deck.append(card)
            return bool(chosen_card)

        # Ba'al: resurrect from discard (baal_resurrect_card sets the flag)
        if ability == "System Lord's Cunning":
            choice_id = payload.get("choice_id")
            if not choice_id:
                return False
            chosen_card = next((c for c in player.discard_pile if getattr(c, "id", None) == choice_id), None)
            if not chosen_card:
                return False
            # Note: baal_resurrect_card sets leader_ability_used flag internally
            return self.baal_resurrect_card(player, chosen_card)

        # Jonas Quinn: copy a card
        if ability == "Eidetic Memory":
            card_id = payload.get("card_id")
            if not card_id or card_id not in ALL_CARDS:
                return False
            memorized_card = copy.deepcopy(ALL_CARDS[card_id])
            player.hand.append(memorized_card)
            self.add_history_event(
                "ability",
                f"{player.name} (Jonas Quinn) memorized {memorized_card.name} and copied it!",
                self._owner_label(player),
                card_ref=memorized_card,
                icon="🧠"
            )
            # Mark as used only after successful completion
            self.leader_ability_used[player] = True
            return True

        # Hathor: steal lowest power enemy unit (payload includes source row/index)
        if "Hathor" in ability:
            from_row = payload.get("from_row")
            from_index = payload.get("from_index")
            target_row = payload.get("target_row") or "close"
            opponent = self.player2 if player == self.player1 else self.player1
            if from_row not in opponent.board or from_index is None:
                return False
            try:
                target_card = opponent.board[from_row][from_index]
            except IndexError as e:
                logger.warning(f"Hathor steal failed - invalid index {from_index} in row {from_row}: {e}")
                return False

            # Remove from opponent board
            opponent.board[from_row].remove(target_card)

            # Store pending info so switch_turn can place it after animation
            player.hathor_ability_pending = {
                "card": target_card,
                "target_row": target_row
            }
            self.hathor_steal_info = {
                "card": target_card,
                "card_id": getattr(target_card, "id", None),
                "from_row": from_row,
                "from_index": from_index,
                "from_player": opponent,
                "to_player": player,
                "target_row": target_row,
                "animation_start": pygame.time.get_ticks(),
                "animation_started": False
            }
            # Mark as used only after successful completion
            self.leader_ability_used[player] = True
            return True

        return False

    def _activate_apophis_weather(self, player):
        """Apophis: unleash a random battlefield weather once per game."""
        weather_rows = ["close", "ranged", "siege"]
        options = [
            ("Ice Planet Hazard", "close"),
            ("Nebula Interference", "ranged"),
            ("Asteroid Storm", "siege"),
            ("Electromagnetic Pulse", self.rng.choice(weather_rows))
        ]
        ability_name, chosen_row = self.rng.choice(options)
        template_candidates = [
            c for c in ALL_CARDS.values()
            if c.row == "weather" and (c.ability or "") == ability_name
        ]
        if not template_candidates:
            return None
        weather_card = copy.deepcopy(self.rng.choice(template_candidates))
        weather_card.id = f"apophis_weather_{ability_name.replace(' ', '_').lower()}"
        weather_card.name = f"{player.leader.get('name', 'Leader')} Decree"

        # Temporarily treat Apophis as the acting player for weather logic
        original_player = self.current_player
        self.current_player = player
        affected_rows = self.apply_weather_effect(weather_card, chosen_row, target_side="both")
        self.current_player = original_player
        if not affected_rows:
            return None
        for affected_row in affected_rows:
            self._set_weather_slot(affected_row, {"card": weather_card, "owner": None})
        return {"ability": ability_name, "rows": affected_rows, "card": weather_card}

    def _activate_catherine_knowledge(self, player):
        """Catherine Langford: Look at top 3 cards of deck, play one immediately."""
        # Get top 3 cards from deck
        if len(player.deck) < 1:
            return None

        revealed_cards = player.deck[:min(3, len(player.deck))]

        # Return cards for UI selection (main.py will handle the choice)
        return {
            "ability": "Ancient Knowledge",
            "revealed_cards": revealed_cards,
            "requires_ui": True  # Signal that UI interaction is needed
        }

    def catherine_play_chosen_card(self, player, chosen_card):
        """
        Play the chosen card from Catherine's ability and move others to bottom of deck.

        Args:
            player: The player using the ability
            chosen_card: The card they chose to play
        """
        if len(player.deck) < 1:
            return

        # Get top 3 cards
        revealed_cards = player.deck[:min(3, len(player.deck))]

        if chosen_card not in revealed_cards:
            return

        # Remove all 3 from top of deck
        for card in revealed_cards:
            if card in player.deck:
                player.deck.remove(card)

        # Add chosen card to hand
        player.hand.append(chosen_card)

        # Put other cards at bottom of deck
        other_cards = [c for c in revealed_cards if c != chosen_card]
        player.deck.extend(other_cards)

        self.add_history_event(
            "ability",
            f"{player.name} used Ancient Knowledge and drew {chosen_card.name}",
            self._owner_label(player),
            card_ref=chosen_card
        )

        # Mark leader ability as used after successful completion
        self.leader_ability_used[player] = True
        self.calculate_scores_and_log()

    def _activate_baal_resurrection(self, player):
        """Ba'al: Return a destroyed unit from discard pile to hand (once per game)."""
        # Get all non-Hero units from discard pile
        eligible_cards = [
            c for c in player.discard_pile
            if not is_hero(c) and c.row in ["close", "ranged", "siege", "agile"]
        ]

        if not eligible_cards:
            return None

        # Return cards for UI selection (main.py will handle the choice)
        return {
            "ability": "System Lord's Cunning",
            "revealed_cards": eligible_cards[:10],  # Show up to 10 cards
            "requires_ui": True  # Signal that UI interaction is needed
        }

    def baal_resurrect_card(self, player, chosen_card):
        """Return chosen card from discard to hand for Ba'al's ability."""
        if chosen_card in player.discard_pile:
            player.discard_pile.remove(chosen_card)
            player.hand.append(chosen_card)
            self.add_history_event(
                "ability",
                f"{player.name} (Ba'al) resurrected {chosen_card.name} from the discard pile!",
                self._owner_label(player),
                card_ref=chosen_card,
                icon="♻️"
            )
            # Mark leader ability as used after successful completion
            self.leader_ability_used[player] = True
            self.calculate_scores_and_log()
            return True
        return False

    def _activate_jonas_memory(self, player):
        """Jonas Quinn: Look at cards opponent drew, copy one to hand (once per game)."""
        # Get cards that opponent drew during the game
        # Use correct list based on which player is using the ability
        if player == self.player1:
            drawn_cards = self.opponent_drawn_cards  # Player2's draws
        else:
            drawn_cards = self.player1_drawn_cards  # Player1's draws

        if not drawn_cards:
            self.add_history_event(
                "ability",
                f"{player.name} (Jonas Quinn) tried to use Eidetic Memory, but opponent hasn't drawn cards yet!",
                self._owner_label(player),
                icon="🧠"
            )
            return None

        # Show up to 5 random cards from what opponent drew
        revealed_cards = self.rng.sample(drawn_cards, min(5, len(drawn_cards)))

        return {
            "ability": "Eidetic Memory",
            "revealed_cards": revealed_cards,
            "requires_ui": True  # Signal that UI interaction is needed
        }

    def jonas_memorize_card(self, player, chosen_card):
        """Copy chosen card to hand for Jonas Quinn's ability."""
        # Create a copy of the card
        memorized_card = copy.deepcopy(chosen_card)
        player.hand.append(memorized_card)
        self.add_history_event(
            "ability",
            f"{player.name} (Jonas Quinn) memorized {chosen_card.name} and copied it!",
            self._owner_label(player),
            card_ref=memorized_card,
            icon="🧠"
        )
        # Mark leader ability as used after successful completion
        self.leader_ability_used[player] = True
        self.calculate_scores_and_log()
        return True

    def apply_special_effect(self, card, row_name):
        """Applies special card effects."""
        if has_ability(card, Ability.COMMAND_NETWORK):
            # Apply horn to specified row for current player
            if row_name in ["close", "ranged", "siege"]:
                self.current_player.horn_effects[row_name] = True
                self.current_player.horn_slots[row_name] = card
                try:
                    get_sound_manager().play_horn_sound()
                except Exception as e:
                    logger.warning(f"Failed to play horn sound: {e}")
                self.add_history_event(
                    "horn",
                    f"{self.current_player.name} activated a Horn on {row_name.title()}",
                    self._owner_label(self.current_player),
                    card_ref=card,
                    row=row_name
                )
        
        elif has_ability(card, Ability.NAQUADAH_OVERLOAD):
            opponent = self.player2 if self.current_player == self.player1 else self.player1
            # Ancient Drone variant: destroy the lowest enemy unit only
            if "Destroy lowest enemy unit" in (card.ability or ""):
                destroyed_rows = self.destroy_lowest_enemy_unit(opponent)
                self.last_scorch_positions = [(opponent, row) for row in destroyed_rows]
            # Merlin's Weapon (one-sided scorch)
            elif "Merlin" in card.name or "Anti-Ori" in card.name:
                destroyed_rows = self.apply_scorch_to_player(opponent)
                self.last_scorch_positions = [(opponent, row) for row in destroyed_rows]
            else:
                # Normal scorch - both sides
                self.last_scorch_positions = self.apply_scorch()
        
        elif has_ability(card, Ability.RING_TRANSPORT):
            # Ring Transport is handled in main.py with UI selection
            # Just mark that decoy effect is pending
            pass
        
        # === NEW SPECIAL CARD ABILITIES ===
        
        elif "Thor's Hammer" in card.name or "Remove all Goa'uld" in (card.ability or ""):
            # Remove all Goa'uld faction units from both boards
            removed_count = 0
            for player in [self.player1, self.player2]:
                for row_name in ["close", "ranged", "siege"]:
                    before = len(player.board[row_name])
                    player.board[row_name] = [c for c in player.board[row_name]
                                             if c.faction != "Goa'uld"]
                    removed_count += before - len(player.board[row_name])
            if removed_count > 0:
                self.add_history_event(
                    "ability",
                    f"{self.current_player.name} used Thor's Hammer - removed {removed_count} Goa'uld units",
                    self._owner_label(self.current_player),
                    icon="🔨"
                )

        elif "Zero Point Module" in card.name or "ZPM" in card.name or "Double all your siege" in (card.ability or ""):
            # Set ZPM flag - doubling happens in calculate_score()
            self.current_player.zpm_active = True
            siege_count = len(self.current_player.board.get("siege", []))
            if siege_count > 0:
                self.add_history_event(
                    "ability",
                    f"{self.current_player.name} activated ZPM - will double {siege_count} siege units",
                    self._owner_label(self.current_player),
                    icon="⚡"
                )

        elif "Communication Device" in card.name or "Reveal opponent's hand" in (card.ability or ""):
            # Set a flag to reveal opponent's hand for 30 seconds
            opponent = self.player2 if self.current_player == self.player1 else self.player1
            opponent.hand_revealed = True
            opponent.hand_reveal_timer = 30  # 30 second reveal
            self.add_history_event(
                "ability",
                f"{self.current_player.name} revealed {opponent.name}'s hand for 30s",
                self._owner_label(self.current_player),
                icon="👀"
            )
            # Will be displayed in UI
        
        elif "Sodan" in card.name and "Look at opponent's hand" in (card.ability or ""):
            # Similar to Communication Device but for when unit is played
            opponent = self.player2 if self.current_player == self.player1 else self.player1
            opponent.hand_revealed = True
            opponent.hand_reveal_timer = 30  # 30 second reveal
            self.add_history_event(
                "ability",
                f"{self.current_player.name} revealed {opponent.name}'s hand for 30s",
                self._owner_label(self.current_player),
                icon="👀"
            )
        elif "Quantum Mirror" in card.name or "Shuffle your hand into deck" in (card.ability or ""):
            # Store current hand size (+1 for the Quantum Mirror card itself that was already removed)
            hand_size = len(self.current_player.hand) + 1

            # Clear hand reveal status BEFORE shuffling/drawing so new cards stay hidden
            self.current_player.hand_revealed = False
            self.current_player.hand_reveal_timer = 0

            # Return hand to deck
            self.current_player.deck.extend(self.current_player.hand)
            self.current_player.hand.clear()

            # Shuffle deck (use seeded rng for LAN sync)
            self.rng.shuffle(self.current_player.deck)

            # Draw same number of cards (these will NOT be revealed)
            self.current_player.draw_cards(hand_size)

            self.add_history_event(
                "ability",
                f"{self.current_player.name} activated Quantum Mirror - reality shifted!",
                self._owner_label(self.current_player),
                icon="🪞"
            )
    
    def apply_decoy(self, selected_card):
        """Apply decoy effect - return selected card to current player's hand."""
        if not selected_card:
            return False
        
        # Find which player owns the card and which row it's in
        card_owner = None
        card_row = None
        
        for player in [self.player1, self.player2]:
            for row_name, row_cards in player.board.items():
                if selected_card in row_cards:
                    card_owner = player
                    card_row = row_name
                    break
            if card_owner:
                break
        
        if not card_owner or not card_row:
            return False
        
        # Remove card from board
        card_owner.board[card_row].remove(selected_card)
        
        # Add to current player's hand (who played the decoy)
        self.current_player.hand.append(selected_card)
        if self.current_player == self.player1:
            self.ability_usage["decoy"] = self.ability_usage.get("decoy", 0) + 1
        
        return True
    
    def get_decoy_valid_cards(self):
        """Get list of valid cards that can be targeted by decoy (all non-Legendary Commander units on both boards)."""
        valid_cards = []
        for player in [self.player1, self.player2]:
            for row_name, row_cards in player.board.items():
                for card in row_cards:
                    if not is_hero(card):
                        valid_cards.append(card)
        return valid_cards

    def play_ring_transport(self, ring_transport_card, target_card):
        """Return the targeted card to the current player's hand.

        Heroes (Legendary Commanders) are immune.
        """
        if not target_card:
            return False

        if is_hero(target_card):
            return False

        # Find which player owns the card and which row it's in
        card_owner = None
        card_row = None
        card_index = -1

        for player in [self.player1, self.player2]:
            for row_name, row_cards in player.board.items():
                if target_card in row_cards:
                    card_owner = player
                    card_row = row_name
                    card_index = row_cards.index(target_card)
                    break
            if card_owner:
                break

        if not card_owner or not card_row or card_index == -1:
            return False

        # Remove target card from board and add to current player's hand
        card_owner.board[card_row].remove(target_card)
        self.current_player.hand.append(target_card)

        # Load decoy image once
        if not hasattr(self, "_decoy_image"):
            try:
                self._decoy_image = pygame.image.load("assets/decoy.png").convert_alpha()
            except pygame.error:
                self._decoy_image = None
        decoy_image = self._decoy_image or getattr(ring_transport_card, "image", None)

        # Create a decoy placeholder and drop it where the target was
        decoy_token = Card(
            "ring_transport_decoy",
            "Asgard Decoy",
            FACTION_NEUTRAL,
            0,
            card_row,
            "Decoy Placeholder"
        )
        decoy_token.image = decoy_image
        card_owner.board[card_row].insert(card_index, decoy_token)

        # Consume the Ring Transport card (discard)
        if ring_transport_card in self.current_player.hand:
            self.current_player.hand.remove(ring_transport_card)
        self.current_player.discard_pile.append(ring_transport_card)

        # Play ring transport sound
        sound_manager = get_sound_manager()
        sound_manager.play_ring_transport_sound(volume=0.6)

        # Update scoreboard immediately for both players
        self.calculate_scores_and_log()

        self.add_history_event(
            "special",
            f"{self.current_player.name} used Ring Transport on {target_card.name}",
            self._owner_label(self.current_player),
            card_ref=ring_transport_card
        )

        return True
    
    def discard_card(self, player, card, animate=True, color_variant='default'):
        """Centralized discard: moves card to discard pile and optionally fires
        the on_discard callback so the UI can spawn a disintegration effect.

        Args:
            player: Player who owns the card
            card: Card to discard
            animate: If True, fire the visual callback
            color_variant: 'default' (blue-white), 'red' (scorch), 'gold' (sacrifice)
        """
        player.discard_pile.append(card)
        if animate and self._on_discard:
            self._on_discard(card, color_variant)

    # Callbacks set by main.py after game creation (avoids circular deps)
    _on_discard = None
    _on_card_played = None

    def apply_scorch(self):
        """Destroys the highest power non-Legendary Commander units (on both boards if tied).
        Returns: List of (player, row_name) tuples where cards were destroyed."""
        all_units = []
        for player in [self.player1, self.player2]:
            for row_name, row_cards in player.board.items():
                for card in row_cards:
                    if not is_hero(card):
                        all_units.append((card, player, row_name))

        if not all_units:
            return []

        # Check if either player has Asgard Beam artifact
        has_asgard_beam = False
        for player in [self.player1, self.player2]:
            for artifact in player.artifacts:
                if artifact.name == "Asgard Beam":
                    has_asgard_beam = True
                    break
            if has_asgard_beam:
                break

        # Determine scorch threshold
        if has_asgard_beam:
            # Destroy all units at or above threshold
            threshold = BALANCE_CONFIG['artifact_scorch_threshold']
            units_to_destroy = [(card, player, row) for card, player, row in all_units
                               if card.displayed_power >= threshold]
        else:
            # Normal scorch: destroy highest power units
            max_power = max(card.displayed_power for card, _, _ in all_units)
            units_to_destroy = [(card, player, row) for card, player, row in all_units
                               if card.displayed_power == max_power]

        destroyed_positions = []
        destroyed_cards = []
        total_power_lost = 0
        for card, player, row_name in units_to_destroy:
            if card in player.board[row_name]:
                total_power_lost += card.displayed_power
                player.board[row_name].remove(card)
                self.discard_card(player, card, color_variant='red')
                destroyed_positions.append((player, row_name))
                destroyed_cards.append((card.name, player.name))

        # Add history event for scorch
        if destroyed_cards:
            cards_text = ", ".join([f"{card} ({owner})" for card, owner in destroyed_cards])
            self.add_history_event(
                "scorch",
                f"Naquadah Overload destroyed: {cards_text}",
                "neutral",
                icon="X",
                delta=-total_power_lost,
                targets=[c[0] for c in destroyed_cards]
            )

        return destroyed_positions
    
    def apply_scorch_to_player(self, target_player):
        """Destroys the highest power non-Legendary Commander units for one player only.
        Returns: List of row_name strings where cards were destroyed."""
        
        # Calculate score BEFORE
        self.player1.calculate_score()
        self.player2.calculate_score()
        score_before = target_player.score

        all_units = []
        for row_name, row_cards in target_player.board.items():
            for card in row_cards:
                if not is_hero(card):
                    all_units.append((card, row_name))

        if not all_units:
            return []

        # Check if either player has Asgard Beam artifact
        has_asgard_beam = False
        for player in [self.player1, self.player2]:
            for artifact in player.artifacts:
                if artifact.name == "Asgard Beam":
                    has_asgard_beam = True
                    break
            if has_asgard_beam:
                break

        # Determine scorch threshold
        if has_asgard_beam:
            # Destroy all units at or above threshold
            threshold = BALANCE_CONFIG['artifact_scorch_threshold']
            units_to_destroy = [(card, row) for card, row in all_units
                               if card.displayed_power >= threshold]
        else:
            # Normal scorch: destroy highest power units
            max_power = max(card.displayed_power for card, _ in all_units)
            units_to_destroy = [(card, row) for card, row in all_units
                               if card.displayed_power == max_power]
        
        destroyed_rows = []
        destroyed_cards = []
        for card, row_name in units_to_destroy:
            if card in target_player.board[row_name]:
                target_player.board[row_name].remove(card)
                self.discard_card(target_player, card, color_variant='red')
                destroyed_rows.append(row_name)
                destroyed_cards.append(card)

        # Calculate score AFTER
        self.player1.calculate_score()
        self.player2.calculate_score()
        score_after = target_player.score
        
        delta = score_after - score_before

        # Log destroyed cards to history
        if destroyed_cards:
            target_label = "player" if target_player == self.player1 else "opponent"
            
            # Use specific narrator message if multiple cards
            if len(destroyed_cards) > 1:
                self.add_history_event(
                    "scorch",
                    f"Scorch vaporized {len(destroyed_cards)} units!",
                    target_label,
                    icon="X",
                    delta=delta,
                    targets=[c.name for c in destroyed_cards]
                )
            else:
                card = destroyed_cards[0]
                self.add_history_event(
                    "destroy",
                    f"Scorch destroyed {card.name}",
                    target_label,
                    card_ref=card,
                    icon="X",
                    delta=delta,
                    targets=[card.name]
                )

        return destroyed_rows
    
    def destroy_lowest_enemy_unit(self, target_player):
        """Destroy the single lowest-power non-Hero unit for a targeted player."""
        eligible = []
        for row_name, row_cards in target_player.board.items():
            for card in row_cards:
                if is_hero(card):
                    continue
                eligible.append((card, row_name))
        if not eligible:
            return []
        min_power = min(card.displayed_power for card, _ in eligible)
        lowest = [(card, row) for card, row in eligible if card.displayed_power == min_power]
        victim, victim_row = self.rng.choice(lowest)
        if victim in target_player.board[victim_row]:
            target_player.board[victim_row].remove(victim)
            self.discard_card(target_player, victim)

            # Log destroyed card to history
            target_label = "player" if target_player == self.player1 else "opponent"
            self.add_history_event(
                "destroy",
                f"Destroyed {victim.name}",
                target_label,
                card_ref=victim,
                icon="X",
                delta=-victim.displayed_power
            )

            return [victim_row]
        return []

    def _cleanup_round(self):
        """Shared cleanup logic for both end_round() and surrender()."""
        self.cards_played_this_round = {self.player1: 0, self.player2: 0}

        for p in [self.player1, self.player2]:
            for row_cards in p.board.values():
                for card in row_cards:
                    if hasattr(card, 'hammond_boosted'):
                        delattr(card, 'hammond_boosted')
                    if hasattr(card, 'kalel_boosted'):
                        delattr(card, 'kalel_boosted')
                    if hasattr(card, 'kiva_boosted'):
                        delattr(card, 'kiva_boosted')
                p.discard_pile.extend(row_cards)

            p.board = {"close": [], "ranged": [], "siege": []}
            p.has_passed = False
            p.weather_effects = {"close": False, "ranged": False, "siege": False}
            p.horn_effects = {"close": False, "ranged": False, "siege": False}
            p.horn_slots = {"close": None, "ranged": None, "siege": None}
            p.weather_cards_played = 0
            p.current_round_number = self.round_number
            p.units_played_this_round = 0
            pending_reveal = getattr(p, "reveal_next_round", False)
            p.hand_revealed = pending_reveal
            p.reveal_next_round = False
            p.zpm_active = False
            p.spies_played_this_round = 0

            if p.ring_transportation:
                p.ring_transportation.reset_round()

            p.score = 0

        LUCIAN_NETWORK_COMBO.reset_round()

        self.discard_active_weather_cards()
        self.weather_active = {"close": False, "ranged": False, "siege": False}
        self.weather_row_targets = {"close": None, "ranged": None, "siege": None}
        self.current_weather_types = {"close": None, "ranged": None, "siege": None}
        self.weather_cards_on_board = {"close": None, "ranged": None, "siege": None}

    def end_round(self):
        """Ends the round, determines winner, and resets for the next."""
        print(f"[DEBUG] end_round called: round={self.round_number}, p1_rounds_won={self.player1.rounds_won}, p2_rounds_won={self.player2.rounds_won}")
        print(f"[DEBUG] Scores: p1={self.player1.score}, p2={self.player2.score}")
        # Anubis leader ability: Auto-scorch in rounds 2 & 3 (BEFORE winner determination)
        for player in [self.player1, self.player2]:
            if player.leader and "Anubis" in player.leader.get('name', ''):
                if self.round_number >= 2:
                    destroyed = self.apply_scorch()
                    if destroyed:
                        self.add_history_event(
                            "ability",
                            f"{player.name} (Anubis) triggered Ascended Power: Naquadah Overload!",
                            self._owner_label(player),
                            icon="X"
                        )
                        # Recalculate scores after scorch
                        self.player1.calculate_score(game=self)
                        self.player2.calculate_score(game=self)

        # Generate thematic round descriptions
        score_diff = abs(self.player1.score - self.player2.score)

        # Determine narrative flavor based on score difference
        if score_diff == 0:
            battle_desc = "An intense stalemate"
        elif score_diff <= 5:
            battle_desc = "A narrow victory"
        elif score_diff <= 15:
            battle_desc = "A decisive battle"
        elif score_diff <= 30:
            battle_desc = "A crushing defeat"
        else:
            battle_desc = "Total annihilation"

        # Determine winner
        if self.player1.score > self.player2.score:
            self.player1.rounds_won += 1
            self.round_winner = self.player1
            self.round_history.append({"winner": "player1", "p1_score": self.player1.score, "p2_score": self.player2.score})
            self.add_history_event(
                "round_end",
                f"═ {battle_desc}! {self.player1.name} claims Round {self.round_number} ({self.player1.score}-{self.player2.score}) ═",
                "player",
                icon="#"
            )
        elif self.player2.score > self.player1.score:
            self.player2.rounds_won += 1
            self.round_winner = self.player2
            self.round_history.append({"winner": "player2", "p1_score": self.player1.score, "p2_score": self.player2.score})
            self.add_history_event(
                "round_end",
                f"═ {battle_desc}! {self.player2.name} claims Round {self.round_number} ({self.player2.score}-{self.player1.score}) ═",
                "ai",
                icon="#"
            )
        else: # Draw - both players get a point
            self.player1.rounds_won += 1
            self.player2.rounds_won += 1
            self.round_winner = None
            self.round_history.append({"winner": "draw", "p1_score": self.player1.score, "p2_score": self.player2.score})
            self.add_history_event(
                "round_end",
                f"═ Deadlock! Round {self.round_number} ends in a draw ({self.player1.score}-{self.player2.score}) ═",
                "neutral",
                icon="=="
            )
        
        # Check for game over BEFORE incrementing round number
        print(f"[DEBUG] After round {self.round_number}: p1_rounds_won={self.player1.rounds_won}, p2_rounds_won={self.player2.rounds_won}")
        # If both players have 2+ wins, it's a draw (e.g. 1 win each + 1 draw, or 2 draws)
        if self.player1.rounds_won >= 2 and self.player2.rounds_won >= 2:
            self.game_state = "game_over"
            self.winner = None # Draw
            self.add_history_event(
                "game_over",
                "⚠️ The Stargate shuts down! Mutual destruction.",
                "neutral",
                icon="X"
            )
            return
        elif self.player1.rounds_won >= 2:
            self.game_state = "game_over"
            self.winner = self.player1
            return
        elif self.player2.rounds_won >= 2:
            self.game_state = "game_over"
            self.winner = self.player2
            return

        self.round_number = min(self.round_number + 1, 3)

        # Conquest Sarcophagus relic: return 1 random card from player1's discard to hand
        conquest_relics = getattr(self, 'conquest_relics', [])
        if conquest_relics and "sarcophagus" in conquest_relics:
            if self.player1.discard_pile:
                import random as _rng
                revived = _rng.choice(self.player1.discard_pile)
                self.player1.discard_pile.remove(revived)
                self.player1.hand.append(revived)
                self.add_history_event(
                    "ability",
                    f"Sarcophagus revived {revived.name} from the discard pile!",
                    "player", icon="+"
                )

        self._cleanup_round()

        # Draw cards for new round
        for p in [self.player1, self.player2]:
            base_draw = 2

            # Apply leader abilities - card draw bonuses
            if p.leader:
                leader_name = p.leader.get('name', '')
                # Col. Jack O'Neill: Draw 1 extra card at round start
                if "O'Neill" in leader_name and self.round_number > 1:
                    base_draw += 1
                    self.add_history_event(
                        "ability",
                        f"{p.name} (O'Neill) draws +1 card (Resourcefulness)",
                        self._owner_label(p),
                        icon="+"
                    )
                # Teal'c: Draw 1 card when winning a round (if just won)
                elif "Teal'c" in leader_name and self.round_winner == p:
                    base_draw += 1
                    self.add_history_event(
                        "ability",
                        f"{p.name} (Teal'c) draws +1 card for winning last round",
                        self._owner_label(p),
                        icon="#"
                    )
                # Rya'c: Draw 2 extra cards at start of round 3
                elif "Rya'c" in leader_name and self.round_number == 3:
                    base_draw += 2
                    self.add_history_event(
                        "ability",
                        f"{p.name} (Rya'c) draws +2 cards - Hope for Tomorrow!",
                        self._owner_label(p),
                        icon="+"
                    )
                # Vala Mal Doran: Steal 1 random card from opponent's hand at round 2 start
                elif "Vala" in leader_name and self.round_number == 2:
                    opponent = self.player2 if p == self.player1 else self.player1
                    if opponent.hand:
                        stolen_card = self.rng.choice(opponent.hand)
                        opponent.hand.remove(stolen_card)
                        p.hand.append(stolen_card)
                        self.add_history_event(
                            "ability",
                            f"{p.name} (Vala) Thief's Luck: Stole {stolen_card.name} from {opponent.name}!",
                            self._owner_label(p),
                            icon="+"
                        )
                # Penegal: Revive 1 unit at start of rounds 2 and 3
                elif "Penegal" in leader_name and self.round_number > 1:
                    valid_units = [c for c in p.discard_pile
                                  if not is_hero(c)
                                  and c.row in ["close", "ranged", "siege", "agile"]]
                    if valid_units:
                        revived = self.rng.choice(valid_units)
                        p.discard_pile.remove(revived)
                        if revived.row in ["close", "ranged", "siege"]:
                            p.board[revived.row].append(revived)
                        elif revived.row == "agile":
                            p.board[self.rng.choice(["close", "ranged"])].append(revived)
                        self.add_history_event(
                            "ability",
                            f"{p.name} (Penegal) revived {revived.name} from discard",
                            self._owner_label(p),
                            icon="+"
                        )
                # Netan: Add random Neutral card each round
                elif "Netan" in leader_name:
                    base_draw += 1
                # Anateo: Free Medical Evac at start of each round
                elif "Anateo" in leader_name and self.round_number > 1:
                    valid_cards = [c for c in p.discard_pile
                                  if not is_hero(c)
                                  and c.row in ["close", "ranged", "siege", "agile"]]
                    if valid_cards:
                        revived = max(valid_cards, key=lambda c: c.power)
                        p.discard_pile.remove(revived)
                        target_row = revived.row if revived.row != "agile" else "close"
                        p.board[target_row].append(revived)
                        self.add_history_event(
                            "ability",
                            f"{p.name} (Anateo) used free Medical Evac on {revived.name}",
                            self._owner_label(p),
                            icon="+"
                        )

            # Draw base cards for the round
            if self.game_state == "playing" and p == self.player2:
                if self.player1.leader and "Jonas" in self.player1.leader.get('name', ''):
                    drawn = p.draw_cards(base_draw, track_for_jonas=True)
                    self.opponent_drawn_cards.extend(drawn)
                else:
                    p.draw_cards(base_draw)
            elif self.game_state == "playing" and p == self.player1:
                if self.player2.leader and "Jonas" in self.player2.leader.get('name', ''):
                    drawn = p.draw_cards(base_draw, track_for_jonas=True)
                    self.player1_drawn_cards.extend(drawn)
                else:
                    p.draw_cards(base_draw)
            else:
                p.draw_cards(base_draw)

            # Apply faction round-start abilities
            if p.faction_ability and hasattr(p.faction_ability, 'apply_round_start'):
                if self.game_state == "playing" and p == self.player2:
                    if self.player1.leader and "Jonas" in self.player1.leader.get('name', ''):
                        if p.faction == FACTION_TAURI and self.round_number > 1:
                            drawn = p.draw_cards(1, track_for_jonas=True)
                            self.opponent_drawn_cards.extend(drawn)
                        else:
                            p.faction_ability.apply_round_start(self, p)
                    else:
                        p.faction_ability.apply_round_start(self, p)
                elif self.game_state == "playing" and p == self.player1:
                    if self.player2.leader and "Jonas" in self.player2.leader.get('name', ''):
                        if p.faction == FACTION_TAURI and self.round_number > 1:
                            drawn = p.draw_cards(1, track_for_jonas=True)
                            self.player1_drawn_cards.extend(drawn)
                        else:
                            p.faction_ability.apply_round_start(self, p)
                    else:
                        p.faction_ability.apply_round_start(self, p)
                else:
                    p.faction_ability.apply_round_start(self, p)
            self._apply_leader_round_start_effects(p)

            # Reset round-specific abilities
            if p.faction_ability:
                if hasattr(p.faction_ability, 'reset_round'):
                    p.faction_ability.reset_round()
            p.dhd_mechanic.reset_round()

            # Reset Iris Power
            if p.faction_power:
                p.faction_power.reset_round()

        # Clear weather
        self.weather_active = {"close": False, "ranged": False, "siege": False}
        self.weather_row_targets = {"close": None, "ranged": None, "siege": None}
        self.current_weather_types = {"close": None, "ranged": None, "siege": None}

        # Add round start history event
        if self.round_number <= 3:
            round_themes = {
                1: "═══ Round 1: Opening Gambit ═══",
                2: "═══ Round 2: The Tide Turns ═══",
                3: "═══ Round 3: Final Confrontation ═══",
            }
            self.add_history_event(
                "round_start",
                round_themes.get(self.round_number, f"═══ Round {self.round_number} Start ═══"),
                "neutral",
                icon="=="
            )

    def surrender(self, surrendering_player):
        """Handle player surrender / give up.

        Args:
            surrendering_player: The player who is surrendering (self.player1 or self.player2)

        The opponent wins immediately with 2 rounds won.
        """
        if self.game_state == "game_over":
            return  # Already ended

        # Determine winner (opponent of surrendering player)
        if surrendering_player == self.player1:
            self.winner = self.player2
            winner_name = self.player2.name
            loser_name = self.player1.name
        else:
            self.winner = self.player1
            winner_name = self.player1.name
            loser_name = self.player2.name

        # Set game state to over
        self.game_state = "game_over"

        # Give winner 2 rounds won (minimum needed to win)
        self.winner.rounds_won = max(self.winner.rounds_won, 2)

        # Log surrender in history
        self.add_history_event(
            "surrender",
            f"{loser_name} has surrendered! {winner_name} wins by forfeit.",
            "player" if surrendering_player == self.player2 else "opponent",
            icon="X"
        )

        print(f"[game] {loser_name} surrendered. {winner_name} wins.")

        self._cleanup_round()

        # Draw cards for new round
        for p in [self.player1, self.player2]:
            base_draw = 2
            
            # Apply leader abilities - card draw bonuses
            if p.leader:
                leader_name = p.leader.get('name', '')
                # Col. Jack O'Neill: Draw 1 extra card at round start
                if "O'Neill" in leader_name and self.round_number > 1:
                    base_draw += 1
                    if self.round_number > 1:  # Only log if actually drawing extra
                        self.add_history_event(
                            "ability",
                            f"{p.name} (O'Neill) draws +1 card (Resourcefulness)",
                            self._owner_label(p),
                            icon="📖"
                        )
                # Teal'c: Draw 1 card when winning a round (if just won)
                elif "Teal'c" in leader_name and self.round_winner == p:
                    base_draw += 1
                    self.add_history_event(
                        "ability",
                        f"{p.name} (Teal'c) draws +1 card for winning last round",
                        self._owner_label(p),
                        icon="#"
                    )
                # NEW: Dr. McKay: Draw 2 cards when you pass
                # (Handled in pass_turn method)
                # NEW: Gerak: Draw 1 card for every 2 units played
                # (Handled in play_card method)
                # Rya'c: Draw 2 extra cards at start of round 3
                elif "Rya'c" in leader_name and self.round_number == 3:
                    base_draw += 2
                    self.add_history_event(
                        "ability",
                        f"{p.name} (Rya'c) draws +2 cards - Hope for Tomorrow!",
                        self._owner_label(p),
                        icon="🌟"
                    )
                # Vala Mal Doran: Steal 1 random card from opponent's hand at round 2 start
                elif "Vala" in leader_name and self.round_number == 2:
                    opponent = self.player2 if p == self.player1 else self.player1
                    if opponent.hand:
                        stolen_card = self.rng.choice(opponent.hand)
                        opponent.hand.remove(stolen_card)
                        p.hand.append(stolen_card)
                        self.add_history_event(
                            "ability",
                            f"{p.name} (Vala) Thief's Luck: Stole {stolen_card.name} from {opponent.name}!",
                            self._owner_label(p),
                            icon="🎭"
                        )
                # NEW: Penegal: Revive 1 unit at start of rounds 2 and 3
                elif "Penegal" in leader_name and self.round_number > 1:
                    valid_units = [c for c in p.discard_pile
                                  if not is_hero(c)
                                  and c.row in ["close", "ranged", "siege", "agile"]]
                    if valid_units:
                        revived = self.rng.choice(valid_units)
                        p.discard_pile.remove(revived)
                        if revived.row in ["close", "ranged", "siege"]:
                            p.board[revived.row].append(revived)
                        elif revived.row == "agile":
                            p.board[self.rng.choice(["close", "ranged"])].append(revived)
                        self.add_history_event(
                            "ability",
                            f"{p.name} (Penegal) revived {revived.name} from discard",
                            self._owner_label(p),
                            icon="+"
                        )
                # NEW: Netan: Add random Neutral card each round
                elif "Netan" in leader_name:
                    # Add a random neutral card to hand (simplified - just draw extra)
                    base_draw += 1
                # NEW: Anateo: Free Medical Evac at start of each round
                elif "Anateo" in leader_name and self.round_number > 1:
                    # Auto-trigger medic ability if discard has valid cards
                    valid_cards = [c for c in p.discard_pile
                                  if not is_hero(c)
                                  and c.row in ["close", "ranged", "siege", "agile"]]
                    if valid_cards:
                        # Revive highest power card
                        revived = max(valid_cards, key=lambda c: c.power)
                        p.discard_pile.remove(revived)
                        target_row = revived.row if revived.row != "agile" else "close"
                        p.board[target_row].append(revived)
                        self.add_history_event(
                            "ability",
                            f"{p.name} (Anateo) used free Medical Evac on {revived.name}",
                            self._owner_label(p),
                            icon="+"
                        )
            
            # Draw base cards for the round
            # Track opponent draws for Jonas Quinn (only after mulligan)
            if self.game_state == "playing" and p == self.player2:
                # Player1's Jonas Quinn: Track cards drawn by player2
                if self.player1.leader and "Jonas" in self.player1.leader.get('name', ''):
                    drawn = p.draw_cards(base_draw, track_for_jonas=True)
                    self.opponent_drawn_cards.extend(drawn)
                else:
                    p.draw_cards(base_draw)
            elif self.game_state == "playing" and p == self.player1:
                # AI Jonas Quinn: Track cards drawn by player1
                if self.player2.leader and "Jonas" in self.player2.leader.get('name', ''):
                    drawn = p.draw_cards(base_draw, track_for_jonas=True)
                    self.player1_drawn_cards.extend(drawn)
                else:
                    p.draw_cards(base_draw)
            else:
                p.draw_cards(base_draw)

            # Apply faction round-start abilities (draw bonuses etc.)
            if p.faction_ability and hasattr(p.faction_ability, 'apply_round_start'):
                # Track faction ability draws for Jonas Quinn
                if self.game_state == "playing" and p == self.player2:
                    if self.player1.leader and "Jonas" in self.player1.leader.get('name', ''):
                        # Tau'ri draws extra cards - track them
                        if p.faction == FACTION_TAURI and self.round_number > 1:
                            drawn = p.draw_cards(1, track_for_jonas=True)
                            self.opponent_drawn_cards.extend(drawn)
                        else:
                            p.faction_ability.apply_round_start(self, p)
                    else:
                        p.faction_ability.apply_round_start(self, p)
                elif self.game_state == "playing" and p == self.player1:
                    # AI Jonas Quinn: Track player1's faction ability draws
                    if self.player2.leader and "Jonas" in self.player2.leader.get('name', ''):
                        if p.faction == FACTION_TAURI and self.round_number > 1:
                            drawn = p.draw_cards(1, track_for_jonas=True)
                            self.player1_drawn_cards.extend(drawn)
                        else:
                            p.faction_ability.apply_round_start(self, p)
                    else:
                        p.faction_ability.apply_round_start(self, p)
                else:
                    p.faction_ability.apply_round_start(self, p)
            self._apply_leader_round_start_effects(p)
            
            # Reset round-specific abilities
            if p.faction_ability:
                if hasattr(p.faction_ability, 'reset_round'):
                    p.faction_ability.reset_round()
            p.dhd_mechanic.reset_round()
            
            # Reset Iris Power
            if p.faction_power:
                p.faction_power.reset_round()
        
        # Clear weather
        self.weather_active = {"close": False, "ranged": False, "siege": False}
        self.weather_row_targets = {"close": None, "ranged": None, "siege": None}
        self.current_weather_types = {"close": None, "ranged": None, "siege": None}

        # Add round start history event with thematic flavor
        if self.round_number <= 3:
            round_themes = {
                1: "═══ Round 1: Opening Gambit ═══",
                2: "═══ Round 2: The Tide Turns ═══",
                3: "═══ Round 3: Final Confrontation ═══",
            }
            self.add_history_event(
                "round_start",
                round_themes.get(self.round_number, f"═══ Round {self.round_number} Start ═══"),
                "neutral",
                icon="=="
            )

    def decrement_all_clone_tokens(self):
        """Reduce lifetime on all O'Neill clones for both players and remove expired ones."""
        # Process clone tokens for both players
        for player in [self.player1, self.player2]:
            for row_name, row_cards in player.board.items():
                for card in list(row_cards):  # Use list() to avoid modification during iteration
                    if getattr(card, "is_oneill_clone", False):
                        card.clone_turns_remaining -= 1
                        if card.clone_turns_remaining <= 0:
                            row_cards.remove(card)
                            self.discard_card(player, card, color_variant='gold')
