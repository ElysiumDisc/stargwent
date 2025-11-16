import random
import copy
import time
from cards import ALL_CARDS, FACTION_TAURI, FACTION_GOAULD, FACTION_JAFFA, FACTION_LUCIAN, FACTION_ASGARD

# ===== STARGATE MECHANICS (MERGED FROM stargate_mechanics.py) =====

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
            "Your non-Hero units get +1 power when you have a Hero on board"
        )
    
    def apply_to_score(self, player):
        """Called during score calculation."""
        # Check if player has any Hero on board
        has_hero = False
        for row in player.board.values():
            for card in row:
                if "Hero" in (card.ability or ""):
                    has_hero = True
                    break
            if has_hero:
                break
        
        if has_hero:
            # Add +1 to all non-Hero units
            for row in player.board.values():
                for card in row:
                    if "Hero" not in (card.ability or ""):
                        card.displayed_power += 1


class JaffarAbility(FactionAbility):
    """Jaffa: 'Brotherhood' - Units get +1 for each other unit in the same row (max +3)."""
    def __init__(self):
        super().__init__(
            "Brotherhood",
            "Each unit gets +1 power for each other unit in the same row (max +3)"
        )
    
    def apply_to_score(self, player):
        """Called during score calculation."""
        for row_name, row_cards in player.board.items():
            non_hero_units = [c for c in row_cards if "Hero" not in (c.ability or "")]
            if len(non_hero_units) > 1:
                bonus = min(3, len(non_hero_units) - 1)  # Max +3 to prevent abuse
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
    FACTION_JAFFA: JaffarAbility(),
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
    
    def use(self, player):
        """Use DHD to retrieve a random card from discard."""
        if self.can_use() and player.discard_pile:
            self.used_this_round = True
            # Get random non-Hero, non-Special card from discard
            eligible_cards = [
                c for c in player.discard_pile 
                if "Hero" not in (c.ability or "") and c.row not in ["special", "weather"]
            ]
            if eligible_cards:
                card = random.choice(eligible_cards)
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


class GameHistoryEntry:
    """Data container describing a single log entry for the HUD history feed."""
    def __init__(self, event_type, description, owner, card_ref=None, icon=None, row=None):
        self.event_type = event_type
        self.description = description
        self.owner = owner  # 'player' or 'ai'
        self.card_ref = card_ref
        self.icon = icon
        self.row = row
        self.timestamp = time.time()
    
    def apply_effect(self, game, player):
        """Apply the artifact's effect."""
        self.effect_func(game, player)


# Artifact definitions
ARTIFACTS = {
    "ancient_control_chair": Artifact(
        "Ancient Control Chair",
        "Your Neutral cards get +2 power",
        lambda g, p: [
            setattr(card, 'displayed_power', card.displayed_power + 2)
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
        "Scorch activates at 8+ power instead of highest",
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
        """Apply the alliance bonus."""
        if self.check_active(player):
            # Add bonus to all cards in the alliance
            for row in player.board.values():
                for card in row:
                    if card.name in self.required_cards:
                        card.displayed_power += self.bonus


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
]


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
}

# ===== END OF MERGED STARGATE MECHANICS =====

class Player:
    """Represents a player in the game."""
    def __init__(self, name, faction, custom_deck=None, leader=None):
        self.name = name
        self.faction = faction
        self.leader = leader  # Leader selection with special ability
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
        self.reveal_next_round = False  # Pending reveal flag for Yu ability
        self.plays_this_turn = 0  # Track plays for Rak'nor ability
        
        # Stargate mechanics
        self.faction_ability = FACTION_ABILITIES.get(faction, None)
        self.dhd_mechanic = DHDMechanic()
        self.iris_defense = IrisDefense()
        
        # Faction-specific special abilities (separate from Faction Powers)
        from power import RingTransportation
        self.ring_transportation = RingTransportation() if faction == "Goa'uld" else None
        
        # Faction Power (imported at runtime to avoid circular dependency)
        self.faction_power = None  # Faction-specific power (once per game)
        self.power_used = False  # Track faction power usage (once per game)

    def build_deck(self):
        """Builds a starting deck for the player based on their faction."""
        deck = [card for card in ALL_CARDS.values() if card.faction == self.faction]
        random.shuffle(deck)
        return deck

    def calculate_score(self):
        """Calculates the player's total score, applying all abilities and effects."""
        # First, reset all card powers to their base value
        for row_name, row_cards in self.board.items():
            for card in row_cards:
                card.displayed_power = card.power

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
                        if "Legendary Commander" in (card.ability or ""):
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
                        if "Gate Reinforcement" in (card.ability or ""):
                            card.displayed_power += 2
            
            # Aegir: Legendary Commanders get +2 power
            elif "Aegir" in leader_name:
                for row_cards in self.board.values():
                    for card in row_cards:
                        if "Legendary Commander" in (card.ability or ""):
                            card.displayed_power += 2
            
            # Rya'c: Draw 2 extra cards at start of round 3
            elif "Rya'c" in leader_name:
                if getattr(self, 'round_number', 1) == 3 and not getattr(player, '_ryac_triggered', False):
                    player.draw_cards(2)
                    player._ryac_triggered = True  # Only trigger once
                    self.add_history_event(
                        "ability",
                        f"{player.name} (Rya'c) drew 2 cards - Hope for Tomorrow!",
                        self._owner_label(player)
                    )

            # (Master Bra'tac removed - duplicate)
            elif False:  # Old Master Bra'tac code
                if getattr(self, 'current_round_number', 1) == 3:
                    for row_cards in self.board.values():
                        for card in row_cards:
                            card.displayed_power += 3
            
            # Loki: Steal 1 power from opponent's strongest (done per turn, tracked separately)
            # This is applied when card is played, not in score calculation

        # Apply Tactical Formation ability
        for row_name, row_cards in self.board.items():
            bond_groups = {}
            for card in row_cards:
                if "Tactical Formation" in (card.ability or ""):
                    if card.name not in bond_groups:
                        bond_groups[card.name] = []
                    bond_groups[card.name].append(card)
            
            for name, cards in bond_groups.items():
                if len(cards) > 1:
                    for card in cards:
                        # If weather affected, tight bond applies after weather
                        if self.weather_effects[row_name] and "Legendary Commander" not in (card.ability or ""):
                            card.displayed_power = len(cards)  # 1 * len(cards)
                        else:
                            card.displayed_power = card.power * len(cards)

        # Apply Inspiring Leadership adjacency bonus
        for row_name, row_cards in self.board.items():
            for idx, card in enumerate(row_cards):
                if "Inspiring Leadership" in (card.ability or ""):
                    if idx > 0:
                        left_card = row_cards[idx - 1]
                        if "Legendary Commander" not in (left_card.ability or ""):
                            left_card.displayed_power += 1
                    if idx < len(row_cards) - 1:
                        right_card = row_cards[idx + 1]
                        if "Legendary Commander" not in (right_card.ability or ""):
                            right_card.displayed_power += 1

        # Apply Commander's Horn (doubles non-Legendary Commander units)
        for row_name, row_cards in self.board.items():
            if self.horn_effects[row_name]:
                for card in row_cards:
                    if "Legendary Commander" not in (card.ability or ""):
                        card.displayed_power *= 2
        
        # Apply Faction Abilities that affect score
        if self.faction_ability:
            if hasattr(self.faction_ability, 'apply_to_score'):
                self.faction_ability.apply_to_score(self)
        
        # Apply Alliance Combos
        for alliance in ALLIANCE_COMBOS:
            if alliance.check_active(self):
                alliance.apply_bonus(self)
        
        # Apply Artifact Effects
        for artifact in self.artifacts:
            artifact.apply_effect(None, self)

        # Apply weather effects last so nothing can override them
        for row_name, row_cards in self.board.items():
            if self.weather_effects[row_name]:
                for card in row_cards:
                    if "Legendary Commander" in (card.ability or ""):
                        continue
                    if "Survival Instinct" in (card.ability or ""):
                        card.displayed_power = card.power + 2
                    else:
                        card.displayed_power = 1

        # Sum the final scores
        self.score = 0
        for row in self.board.values():
            for card in row:
                self.score += card.displayed_power

    def draw_cards(self, num=1):
        """Draws a number of cards from the deck to the hand."""
        for _ in range(num):
            if self.deck:
                self.hand.append(self.deck.pop())

    def spawn_oneill_clone(self):
        """Summon a temporary Jack O'Neill clone token to the close row."""
        if self.faction != FACTION_TAURI:
            return
        from cards import Card
        clone = Card(
            "token_oneill_clone",
            "Jack O'Neill Clone",
            self.faction,
            6,
            "close",
            "Temporary Clone",
        )
        clone.is_oneill_clone = True
        clone.clone_turns_remaining = 4  # removed when about to take 4th turn
        self.board["close"].append(clone)

    def decrement_clone_tokens(self):
        """Reduce lifetime on O'Neill clones and remove expired ones."""
        for row_name, row_cards in self.board.items():
            for card in list(row_cards):
                if getattr(card, "is_oneill_clone", False):
                    card.clone_turns_remaining -= 1
                    if card.clone_turns_remaining <= 1:
                        row_cards.remove(card)
                        self.discard_pile.append(card)

class Game:
    """Manages the overall game state and logic."""
    def __init__(self, player1_faction=FACTION_TAURI, player1_deck=None, player1_leader=None,
                 player2_faction=FACTION_GOAULD, player2_deck=None, player2_leader=None):
        self.player1 = Player("Player 1", player1_faction, player1_deck, player1_leader)
        self.player2 = Player("Player 2", player2_faction, player2_deck, player2_leader)
        
        # Randomize who goes first (50/50 coin toss)
        self.current_player = random.choice([self.player1, self.player2])
        
        self.round_number = 1
        self.game_state = "mulligan"  # Start with mulligan phase
        self.weather_active = {"close": False, "ranged": False, "siege": False}
        self.current_weather_types = {"close": None, "ranged": None, "siege": None}  # Track weather type per row
        self.weather_row_targets = {"close": None, "ranged": None, "siege": None}  # Which player's lane is affected
        self.weather_cards_on_board = {"close": None, "ranged": None, "siege": None}  # Weather visuals per row
        self.winner = None
        self.round_winner = None  # Track who won last round for missions
        self.last_scorch_positions = []  # Track where Naquadah Overload destroyed cards (player, row_name)
        self.history = []
        self.history_dirty = False
        
        # Leader ability tracking
        self.cards_played_this_round = {self.player1: 0, self.player2: 0}
        self.leader_ability_used = {self.player1: False, self.player2: False}
        self.last_turn_actor = None

    def _owner_label(self, player):
        return "player" if player == self.player1 else "ai"

    def add_history_event(self, event_type, description, owner, card_ref=None, icon=None, row=None):
        """Append a new entry to the history log."""
        entry = GameHistoryEntry(event_type, description, owner, card_ref=card_ref, icon=icon, row=row)
        self.history.append(entry)
        if len(self.history) > 200:
            self.history.pop(0)
        self.history_dirty = True
        return entry

    def _log_card_play(self, player, card, row_name=None, note=None):
        """Helper to log standard card plays."""
        desc = f"{player.name} played {card.name}"
        if row_name:
            desc += f" → {row_name.title()}"
        if note:
            desc += f" ({note})"
        self.add_history_event("card_play", desc, self._owner_label(player), card_ref=card, row=row_name)

    def _apply_leader_round_start_effects(self, player):
        """Handle leader-specific triggers that occur at round start."""
        if not player.leader:
            return
        leader_name = player.leader.get('name', '')
        if "O'Neill" in leader_name:
            player.spawn_oneill_clone()

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
        random.shuffle(player.deck)
        player.draw_cards(len(cards_to_redraw))
    
    def end_mulligan_phase(self):
        """Ends mulligan phase and starts the game."""
        self.game_state = "playing"
        for player in [self.player1, self.player2]:
            self._apply_leader_round_start_effects(player)

    def switch_turn(self):
        """Switches the turn to the other player, handling passed players."""
        if self.last_turn_actor:
            self.last_turn_actor.decrement_clone_tokens()
            self.last_turn_actor = None
        if self.player1.has_passed and self.player2.has_passed:
            self.end_round()
            return

        if self.current_player == self.player1:
            self.current_player = self.player2
        else:
            self.current_player = self.player1
        
        # Reset plays this turn counter when switching turns
        self.current_player.plays_this_turn = 0
        
        if self.current_player.has_passed:
            self.switch_turn() # Skip player if they have passed

    def play_card(self, card, row_name, target_side=None):
        """Plays a card from the current player's hand to the board."""
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
        if opponent.iris_defense.is_active():
            # Card is blocked and destroyed
            self.current_player.hand.remove(card)
            self.current_player.discard_pile.append(card)
            opponent.iris_defense.deactivate()
            self.switch_turn()
            return

        if card in self.current_player.hand:
            self.current_player.hand.remove(card)
            self.last_turn_actor = player
            
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
                self.player1.calculate_score()
                self.player2.calculate_score()
                player.plays_this_turn += 1
                self.switch_turn()
                return
            
            # Handle special cards
            if card.row == "special":
                self.apply_special_effect(card, row_name)
                self.current_player.discard_pile.append(card)
                self._log_card_play(player, card, row_name=row_name, note="Special")
                self.player1.calculate_score()
                self.player2.calculate_score()
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
            is_spy = "Deep Cover Agent" in (card.ability or "")
            
            # Deep Cover Agent ability logic with Lucian faction bonus and Vulkar leader ability
            if is_spy:
                if self.current_player == self.player1:
                    target_player = self.player2
                else:
                    target_player = self.player1
                
                # Check for Lucian piracy bonus OR Vulkar leader ability
                draw_amount = 2
                if player.faction_ability and hasattr(player.faction_ability, 'get_spy_draw_amount'):
                    draw_amount = player.faction_ability.get_spy_draw_amount()
                # Vulkar leader ability: Spy cards draw 3 instead of 2
                elif player.leader and "Vulkar" in player.leader.get('name', ''):
                    draw_amount = 3
                player.draw_cards(draw_amount)

            target_player.board[row_name].append(card)
            self._log_card_play(player, card, row_name=row_name)
            
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
            
            # Loki ability: Steal 1 power from opponent's strongest unit
            if player.leader and "Loki" in player.leader.get('name', ''):
                opponent = self.player2 if player == self.player1 else self.player1
                all_opponent_units = []
                for row_cards in opponent.board.values():
                    all_opponent_units.extend([c for c in row_cards if "Legendary Commander" not in (c.ability or "")])
                if all_opponent_units:
                    strongest = max(all_opponent_units, key=lambda c: c.displayed_power)
                    if strongest.displayed_power > 1:
                        strongest.power -= 1
                        # Add power to a random friendly unit
                        friendly_units = [c for row in player.board.values() for c in row if "Legendary Commander" not in (c.ability or "")]
                        if friendly_units:
                            random.choice(friendly_units).power += 1
                        print(f"Loki stole 1 power from {strongest.name} (now {strongest.power})")


            # Trigger Gate Reinforcement ability
            if "Gate Reinforcement" in (card.ability or ""):
                self.trigger_muster(card, target_player, row_name)
            
            # Trigger Deploy Clones
            if "Deploy Clones" in (card.ability or ""):
                self.trigger_summon_shield_maidens(target_player, row_name)
            
            # Trigger Activate Combat Protocol
            if "Activate Combat Protocol" in (card.ability or ""):
                self.trigger_summon_avenger(target_player, row_name)
            
            # Trigger Genetic Enhancement (transforms weakest units)
            if "Genetic Enhancement" in (card.ability or ""):
                self.trigger_mardroeme(target_player)
            
            # Trigger Medical Evac ability - Check if player should choose
            if "Medical Evac" in (card.ability or ""):
                # Don't trigger yet - will be handled by medic selection UI
                # Just mark that medic ability is pending
                pass
            else:
                # Non-medic cards switch turn normally
                self.player1.calculate_score()
                self.player2.calculate_score()
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
                # Lord Yu: Reveal opponent's hand when you pass
                elif "Yu" in leader_name:
                    opponent = self.player2 if passing_player == self.player1 else self.player1
                    opponent.reveal_next_round = True
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

        # Life Force Drain siphons enemy strength and boosts the muster group
        if "Life Force Drain" in (played_card.ability or ""):
            self.trigger_life_force_drain(player, played_card, total_mustered)
        
        # System Lord's Curse weakens the opposing row after the muster resolves
        if "System Lord's Curse" in (played_card.ability or ""):
            self.trigger_system_lords_curse(player, row_name)
        
        # Check for Vampire ability (life steal)
        if "Vampire" in (played_card.ability or ""):
            self.trigger_vampire(player, total_mustered)
        
        # Check for Crone ability (weaken opponent)
        if "Crone" in (played_card.ability or ""):
            self.trigger_crone(player, row_name)
    
    def trigger_vampire(self, player, num_cards):
        """Vampire: Steal 1 power from random opponent unit for each mustered card."""
        opponent = self.player2 if player == self.player1 else self.player1
        
        for _ in range(num_cards):
            # Find all opponent units with power > 1
            drainable_units = []
            for row_cards in opponent.board.values():
                for card in row_cards:
                    if card.displayed_power > 1 and "Legendary Commander" not in (card.ability or ""):
                        drainable_units.append(card)
            
            if drainable_units:
                # Drain power from random unit
                import random
                target = random.choice(drainable_units)
                new_power = max(1, target.power - 1)
                target.power = new_power
                target.displayed_power = new_power
    
    def trigger_crone(self, player, row_name):
        """Crone: Weaken all opponent units in the same row by 1 (min 1)."""
        opponent = self.player2 if player == self.player1 else self.player1
        
        # Weaken all opponent units in same row
        for card in opponent.board.get(row_name, []):
            if "Legendary Commander" not in (card.ability or ""):
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
                    if "Legendary Commander" in (card.ability or ""):
                        continue
                    if card.power > 1:
                        drainable_units.append(card)
            if not drainable_units:
                break
            target = random.choice(drainable_units)
            target.power = max(1, target.power - 1)
            target.displayed_power = min(target.displayed_power, target.power)
            
            recipient = random.choice(muster_group)
            recipient.power += 1
            recipient.displayed_power += 1
    
    def trigger_system_lords_curse(self, player, row_name):
        """System Lord's Curse: weaken opposing units in the mirrored row by 1 (min 1)."""
        opponent = self.player2 if player == self.player1 else self.player1
        for card in opponent.board.get(row_name, []):
            if "Legendary Commander" in (card.ability or ""):
                continue
            new_power = max(1, card.power - 1)
            card.power = new_power
            card.displayed_power = min(card.displayed_power, new_power)
    
    def trigger_summon_shield_maidens(self, player, row_name):
        """Deploy Clones: Add 2 Shield Maiden tokens (2 power each) to the row."""
        # Create token cards (not in deck, just spawned)
        from cards import Card
        maiden1 = Card("token_maiden_1", "Shield Maiden", player.faction, 2, row_name, None)
        maiden2 = Card("token_maiden_2", "Shield Maiden", player.faction, 2, row_name, None)
        
        player.board[row_name].append(maiden1)
        player.board[row_name].append(maiden2)
    
    def trigger_summon_avenger(self, player, row_name):
        """Activate Combat Protocol: Add 1 Avenger token (5 power) to the row."""
        from cards import Card
        avenger = Card("token_avenger", "Asgard Avenger", player.faction, 5, row_name, None)
        player.board[row_name].append(avenger)
    
    def trigger_mardroeme(self, player):
        """Genetic Enhancement: Transform weakest unit in each row into a 8-power berserker."""
        for row_name, row_cards in player.board.items():
            if not row_cards:
                continue
            
            # Find weakest non-Legendary Commander unit
            weakest = None
            for card in row_cards:
                if "Legendary Commander" not in (card.ability or ""):
                    if weakest is None or card.displayed_power < weakest.displayed_power:
                        weakest = card
            
            if weakest:
                # Transform into berserker
                weakest.power = 8
                weakest.displayed_power = 8
                if weakest.ability:
                    if "Survival Instinct" not in weakest.ability:
                        weakest.ability += ", Survival Instinct"
                else:
                    weakest.ability = "Survival Instinct"
    
    def trigger_medic(self, player, selected_card=None):
        """Revives a non-Legendary Commander unit card from discard pile."""
        valid_cards = [c for c in player.discard_pile if "Legendary Commander" not in (c.ability or "") and c.row in ["close", "ranged", "siege", "agile"]]
        
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
        return revived
    
    def get_medic_valid_cards(self, player):
        """Get list of valid cards that can be revived by medic."""
        return [c for c in player.discard_pile if "Legendary Commander" not in (c.ability or "") and c.row in ["close", "ranged", "siege", "agile"]]
    
    def apply_weather_effect(self, card, target_row=None, target_side="both"):
        """Applies weather effects to rows and returns affected row names."""
        ability = card.ability or ""
        affected_rows = []
        acting_player = self.current_player
        opponent = self.player2 if acting_player == self.player1 else self.player1

        def has_leader(player, name):
            return player.leader and name in player.leader.get('name', '')

        if "Wormhole Stabilization" in ability:
            # Clears all weather
            self.discard_active_weather_cards()
            self.weather_active = {"close": False, "ranged": False, "siege": False}
            self.current_weather_types = {"close": "Wormhole Stabilization", "ranged": "Wormhole Stabilization", "siege": "Wormhole Stabilization"}
            self.weather_row_targets = {"close": None, "ranged": None, "siege": None}
            for p in [self.player1, self.player2]:
                p.weather_effects = {"close": False, "ranged": False, "siege": False}
            return affected_rows

        # Asgard shielding: opponent can block the first enemy weather each round
        if acting_player != opponent:
            faction_ability = getattr(opponent, "faction_ability", None)
            if faction_ability and hasattr(faction_ability, "can_block_weather"):
                if faction_ability.can_block_weather():
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
        if result:
            self.leader_ability_used[player] = True
            self.player1.calculate_score()
            self.player2.calculate_score()
        return result

    def _activate_apophis_weather(self, player):
        """Apophis: unleash a random battlefield weather once per game."""
        weather_rows = ["close", "ranged", "siege"]
        options = [
            ("Ice Planet Hazard", "close"),
            ("Nebula Interference", "ranged"),
            ("Asteroid Storm", "siege"),
            ("Electromagnetic Pulse", random.choice(weather_rows))
        ]
        ability_name, chosen_row = random.choice(options)
        template_candidates = [
            c for c in ALL_CARDS.values()
            if c.row == "weather" and (c.ability or "") == ability_name
        ]
        if not template_candidates:
            return None
        weather_card = copy.deepcopy(random.choice(template_candidates))
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

    def apply_special_effect(self, card, row_name):
        """Applies special card effects."""
        ability = card.ability or ""
        
        if "Command Network" in ability:
            # Apply horn to specified row for current player
            if row_name in ["close", "ranged", "siege"]:
                self.current_player.horn_effects[row_name] = True
                self.current_player.horn_slots[row_name] = card
                self.add_history_event(
                    "horn",
                    f"{self.current_player.name} activated a Horn on {row_name.title()}",
                    self._owner_label(self.current_player),
                    card_ref=card,
                    row=row_name
                )
        
        elif "Naquadah Overload" in ability:
            opponent = self.player2 if self.current_player == self.player1 else self.player1
            # Ancient Drone variant: destroy the lowest enemy unit only
            if "Destroy lowest enemy unit" in ability:
                destroyed_rows = self.destroy_lowest_enemy_unit(opponent)
                self.last_scorch_positions = [(opponent, row) for row in destroyed_rows]
            # Merlin's Weapon (one-sided scorch)
            elif "Merlin" in card.name or "Anti-Ori" in card.name:
                destroyed_rows = self.apply_scorch_to_player(opponent)
                self.last_scorch_positions = [(opponent, row) for row in destroyed_rows]
            else:
                # Normal scorch - both sides
                self.last_scorch_positions = self.apply_scorch()
        
        elif "Ring Transport" in ability:
            # Ring Transport is handled in main.py with UI selection
            # Just mark that decoy effect is pending
            pass
        
        # === NEW SPECIAL CARD ABILITIES ===
        
        elif "Thor's Hammer" in card.name or "Remove all Goa'uld" in ability:
            # Remove all Goa'uld faction units from both boards
            for player in [self.player1, self.player2]:
                for row_name in ["close", "ranged", "siege"]:
                    player.board[row_name] = [c for c in player.board[row_name] 
                                             if c.faction != "Goa'uld"]
        
        elif "Zero Point Module" in card.name or "ZPM" in card.name or "Double all your siege" in ability:
            # Double all siege units for current player this round
            for siege_card in self.current_player.board.get("siege", []):
                siege_card.displayed_power = siege_card.power * 2
        
        elif "Communication Device" in card.name or "Reveal opponent's hand" in ability:
            # Set a flag to reveal opponent's hand for this round
            opponent = self.player2 if self.current_player == self.player1 else self.player1
            opponent.hand_revealed = True
            # Will be displayed in UI
        
        elif "Sodan" in card.name and "Look at opponent's hand" in ability:
            # Similar to Communication Device but for when unit is played
            opponent = self.player2 if self.current_player == self.player1 else self.player1
            opponent.hand_revealed = True
    
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
        
        return True
    
    def get_decoy_valid_cards(self):
        """Get list of valid cards that can be targeted by decoy (all non-Legendary Commander units on both boards)."""
        valid_cards = []
        for player in [self.player1, self.player2]:
            for row_name, row_cards in player.board.items():
                for card in row_cards:
                    if "Legendary Commander" not in (card.ability or ""):
                        valid_cards.append(card)
        return valid_cards
    
    def apply_scorch(self):
        """Destroys the highest power non-Legendary Commander units (on both boards if tied).
        Returns: List of (player, row_name) tuples where cards were destroyed."""
        all_units = []
        for player in [self.player1, self.player2]:
            for row_name, row_cards in player.board.items():
                for card in row_cards:
                    if "Legendary Commander" not in (card.ability or ""):
                        all_units.append((card, player, row_name))
        
        if not all_units:
            return []
        
        max_power = max(card.displayed_power for card, _, _ in all_units)
        units_to_destroy = [(card, player, row) for card, player, row in all_units 
                           if card.displayed_power == max_power]
        
        destroyed_positions = []
        for card, player, row_name in units_to_destroy:
            if card in player.board[row_name]:
                player.board[row_name].remove(card)
                player.discard_pile.append(card)
                destroyed_positions.append((player, row_name))
        
        return destroyed_positions
    
    def apply_scorch_to_player(self, target_player):
        """Destroys the highest power non-Legendary Commander units for one player only.
        Returns: List of row_name strings where cards were destroyed."""
        all_units = []
        for row_name, row_cards in target_player.board.items():
            for card in row_cards:
                if "Legendary Commander" not in (card.ability or ""):
                    all_units.append((card, row_name))
        
        if not all_units:
            return []
        
        max_power = max(card.displayed_power for card, _ in all_units)
        units_to_destroy = [(card, row) for card, row in all_units 
                           if card.displayed_power == max_power]
        
        destroyed_rows = []
        for card, row_name in units_to_destroy:
            if card in target_player.board[row_name]:
                target_player.board[row_name].remove(card)
                target_player.discard_pile.append(card)
                destroyed_rows.append(row_name)
        
        return destroyed_rows
    
    def destroy_lowest_enemy_unit(self, target_player):
        """Destroy the single lowest-power non-Hero unit for a targeted player."""
        eligible = []
        for row_name, row_cards in target_player.board.items():
            for card in row_cards:
                if "Legendary Commander" in (card.ability or ""):
                    continue
                eligible.append((card, row_name))
        if not eligible:
            return []
        min_power = min(card.displayed_power for card, _ in eligible)
        lowest = [(card, row) for card, row in eligible if card.displayed_power == min_power]
        victim, victim_row = random.choice(lowest)
        if victim in target_player.board[victim_row]:
            target_player.board[victim_row].remove(victim)
            target_player.discard_pile.append(victim)
            return [victim_row]
        return []

    def end_round(self):
        """Ends the round, determines winner, and resets for the next."""
        # Determine winner
        if self.player1.score > self.player2.score:
            self.player1.rounds_won += 1
            self.round_winner = self.player1
        elif self.player2.score > self.player1.score:
            self.player2.rounds_won += 1
            self.round_winner = self.player2
        else: # Draw - both players get a point
            self.player1.rounds_won += 1
            self.player2.rounds_won += 1
            self.round_winner = None
        
        # Anubis leader ability: Auto-scorch in rounds 2 & 3
        for player in [self.player1, self.player2]:
            if player.leader and "Anubis" in player.leader.get('name', ''):
                if self.round_number >= 2:  # Rounds 2 and 3
                    self.apply_scorch()  # Trigger scorch effect

        self.round_number = min(self.round_number + 1, 3)
        
        # Reset turn counters for new round
        self.cards_played_this_round = {self.player1: 0, self.player2: 0}

        # Check for game over (first to 2 round wins)
        if self.player1.rounds_won >= 2:
            self.game_state = "game_over"
            self.winner = self.player1
            return
        elif self.player2.rounds_won >= 2:
            self.game_state = "game_over"
            self.winner = self.player2
            return

        # Move all board cards to discard pile
        for p in [self.player1, self.player2]:
            for row_cards in p.board.values():
                # Clear leader ability boost flags before moving to discard
                for card in row_cards:
                    if hasattr(card, 'hammond_boosted'):
                        delattr(card, 'hammond_boosted')
                    if hasattr(card, 'kalel_boosted'):
                        delattr(card, 'kalel_boosted')
                p.discard_pile.extend(row_cards)
            
            # Reset for next round
            p.board = { "close": [], "ranged": [], "siege": [] }
            p.has_passed = False
            p.weather_effects = {"close": False, "ranged": False, "siege": False}
            p.horn_effects = {"close": False, "ranged": False, "siege": False}
            p.horn_slots = {"close": None, "ranged": None, "siege": None}
            p.weather_cards_played = 0
            p.current_round_number = self.round_number  # Update player's round number
            p.units_played_this_round = 0  # Reset unit counter
            pending_reveal = getattr(p, "reveal_next_round", False)
            p.hand_revealed = pending_reveal  # Carry Yu intel into next round
            p.reveal_next_round = False
            
            # Reset Ring Transportation for new round (Goa'uld)
            if p.ring_transportation:
                p.ring_transportation.reset_round()
            
            p.calculate_score()
        
        # Clear weather cards from board and move to discard
        self.discard_active_weather_cards()
        self.weather_active = {"close": False, "ranged": False, "siege": False}
        self.weather_row_targets = {"close": None, "ranged": None, "siege": None}
        self.current_weather_types = {"close": None, "ranged": None, "siege": None}
        self.weather_cards_on_board = {"close": None, "ranged": None, "siege": None}
        
        # Draw cards for new round
        for p in [self.player1, self.player2]:
            base_draw = 2
            
            # Apply leader abilities - card draw bonuses
            if p.leader:
                leader_name = p.leader.get('name', '')
                # Col. Jack O'Neill: Draw 1 extra card at round start
                if "O'Neill" in leader_name and self.round_number > 1:
                    base_draw += 1
                # Teal'c: Draw 1 card when winning a round (if just won)
                elif "Teal'c" in leader_name and self.round_winner == p:
                    base_draw += 1
                # NEW: Dr. McKay: Draw 2 cards when you pass
                # (Handled in pass_turn method)
                # NEW: Gerak: Draw 1 card for every 2 units played
                # (Handled in play_card method)
                # NEW: Penegal: Revive 1 unit at start of rounds 2 and 3
                elif "Penegal" in leader_name and self.round_number > 1:
                    if p.discard_pile:
                        revived = random.choice(p.discard_pile)
                        p.discard_pile.remove(revived)
                        # Place in appropriate row
                        if revived.row in ["close", "ranged", "siege"]:
                            p.board[revived.row].append(revived)
                        elif revived.row == "agile":
                            # Place agile in random valid row
                            p.board[random.choice(["close", "ranged", "siege"])].append(revived)
                # NEW: Netan: Add random Neutral card each round
                elif "Netan" in leader_name:
                    # Add a random neutral card to hand (simplified - just draw extra)
                    base_draw += 1
                # NEW: Anateo: Free Medical Evac at start of each round
                elif "Anateo" in leader_name and self.round_number > 1:
                    # Auto-trigger medic ability if discard has valid cards
                    valid_cards = [c for c in p.discard_pile 
                                  if "Legendary Commander" not in (c.ability or "") 
                                  and c.row in ["close", "ranged", "siege", "agile"]]
                    if valid_cards:
                        # Revive highest power card
                        revived = max(valid_cards, key=lambda c: c.power)
                        p.discard_pile.remove(revived)
                        target_row = revived.row if revived.row != "agile" else "close"
                        p.board[target_row].append(revived)
            
            # Draw base cards for the round
            p.draw_cards(base_draw)

            # Apply faction round-start abilities (draw bonuses etc.)
            if p.faction_ability and hasattr(p.faction_ability, 'apply_round_start'):
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
        
        # Reset turn to player 1
        self.current_player = self.player1
