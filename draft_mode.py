"""
STARGWENT - DRAFT MODE (ARENA)

Draft Mode is a roguelike deck-building game mode where players build a deck
from random card offerings and then battle the AI.

FLOW:
1. Leader Selection - Choose from 3 random leaders
2. Draft Phase - Build deck by choosing 1 card from 3 options (30 picks)
3. Battle Phase - Fight AI with drafted deck
4. Rewards - Earn cards/unlocks based on performance

RULES:
- Must draft exactly 30 cards
- No deck composition restrictions (can go over normal limits)
- One battle per draft run
- Higher difficulty AI for more rewards
"""

import random
import copy
from typing import List, Dict, Optional, Tuple
from cards import ALL_CARDS, Card
from content_registry import LEADER_REGISTRY


class DraftPool:
    """Manages the pool of cards available for drafting."""

    def __init__(self, unlocked_cards: List[str], unlocked_leaders: List[str]):
        """
        Initialize draft pool with player's unlocked content.

        Args:
            unlocked_cards: List of unlocked card IDs
            unlocked_leaders: List of unlocked leader names
        """
        self.available_cards = [
            card for card_id, card in ALL_CARDS.items()
            if card_id in unlocked_cards
        ]
        self.available_leaders = [
            leader for leader in LEADER_REGISTRY
            if leader['name'] in unlocked_leaders
        ]

        # Ensure we have enough content
        if len(self.available_cards) < 90:  # Need 3 options * 30 picks
            # Fallback: include all cards if player hasn't unlocked enough
            self.available_cards = list(ALL_CARDS.values())

        if len(self.available_leaders) < 3:
            # Fallback: include all leaders
            self.available_leaders = list(LEADER_REGISTRY)

    def get_leader_choices(self, count: int = 3) -> List[Dict]:
        """
        Get random leader choices.

        Args:
            count: Number of leaders to offer

        Returns:
            List of leader dictionaries
        """
        return random.sample(self.available_leaders, min(count, len(self.available_leaders)))

    def get_card_choices(self, count: int = 3, rarity_weights: Optional[Dict] = None) -> List[Card]:
        """
        Get random card choices with optional rarity weighting.

        Args:
            count: Number of cards to offer
            rarity_weights: Dict mapping rarity to weight multiplier

        Returns:
            List of card objects
        """
        if rarity_weights:
            # Weight cards by rarity
            weighted_pool = []
            for card in self.available_cards:
                power = card.power
                # Higher power = rarer = lower weight for balanced drafts
                if power >= 10:
                    weight = rarity_weights.get('legendary', 1)
                elif power >= 7:
                    weight = rarity_weights.get('epic', 2)
                elif power >= 4:
                    weight = rarity_weights.get('rare', 3)
                else:
                    weight = rarity_weights.get('common', 4)
                weighted_pool.extend([card] * weight)

            choices = random.sample(weighted_pool, min(count, len(weighted_pool)))
        else:
            choices = random.sample(self.available_cards, min(count, len(self.available_cards)))

        # Deep copy to avoid modifying originals
        return [copy.deepcopy(card) for card in choices]


class DraftRun:
    """Represents a single draft run."""

    CARDS_TO_DRAFT = 30
    CHOICES_PER_PICK = 3
    MAX_WINS = 8
    
    # Milestone constants
    MILESTONE_REDRAFT_CARDS = 3
    MILESTONE_REDRAFT_LEADER = 5

    def __init__(self, pool: DraftPool):
        """
        Initialize a new draft run.

        Args:
            pool: DraftPool instance with available content
        """
        self.pool = pool
        self.drafted_leader: Optional[Dict] = None
        self.drafted_cards: List[Card] = []
        self.current_pick = 0
        self.phase = "leader_select"  # leader_select, draft, review, battle, redraft_cards_select, redraft_cards_pick, redraft_leader
        self.pick_history: List[Tuple[Card, List[Card]]] = []  # For undo feature
        
        # Run progress
        self.wins = 0
        self.losses = 0
        self.cards_to_remove_count = 0

        # Rarity weights for balanced drafting
        # Lower weight = rarer appearance
        self.rarity_weights = {
            'legendary': 1,
            'epic': 2,
            'rare': 3,
            'common': 4
        }
    
    def to_dict(self) -> Dict:
        """Serialize run state to dictionary."""
        return {
            'wins': self.wins,
            'losses': self.losses,
            'phase': self.phase,
            'current_pick': self.current_pick,
            'leader_id': self.drafted_leader['card_id'] if self.drafted_leader else None,
            'card_ids': [c.id for c in self.drafted_cards] if hasattr(self.drafted_cards[0], 'id') else [], # Assuming cards have IDs
            # Note: We need a way to robustly save card IDs. 
            # Ideally card objects have an 'id' attribute or we map names.
            # Using a simplified list for now, relying on controller to rebuild.
        }

    @classmethod
    def from_dict(cls, data: Dict, pool: DraftPool) -> 'DraftRun':
        """Create DraftRun from serialized data."""
        run = cls(pool)
        run.wins = data.get('wins', 0)
        run.losses = data.get('losses', 0)
        run.phase = data.get('phase', 'leader_select')
        run.current_pick = data.get('current_pick', 0)
        
        # Restore leader
        leader_id = data.get('leader_id')
        if leader_id:
            for leader in pool.available_leaders:
                if leader['card_id'] == leader_id:
                    run.drafted_leader = leader
                    break
        
        # Restore cards (Logic requires persistence to store IDs properly)
        # This is a placeholder - actual restoration needs card lookup
        # We'll handle full restoration in the Controller or expanded persistence
        return run

    def select_leader(self, leader: Dict):
        """
        Select a leader and advance to draft phase.

        Args:
            leader: Selected leader dictionary
        """
        self.drafted_leader = leader
        if self.phase == "redraft_leader":
            self.phase = "review"  # Done redrafting leader
        else:
            self.phase = "draft"

    def get_current_choices(self) -> List[Card]:
        """
        Get card choices for current pick.

        Returns:
            List of 3 card options
        """
        if self.phase not in ["draft", "redraft_cards_pick"]:
            return []

        return self.pool.get_card_choices(
            count=self.CHOICES_PER_PICK,
            rarity_weights=self.rarity_weights
        )

    def pick_card(self, card: Card, all_choices: List[Card] = None):
        """
        Pick a card and advance to next pick.

        Args:
            card: Selected card
            all_choices: All choices shown (for undo history)
        """
        if self.phase == "draft":
            # Store history for undo
            if all_choices:
                self.pick_history.append((copy.deepcopy(card), [copy.deepcopy(c) for c in all_choices]))

            self.drafted_cards.append(copy.deepcopy(card))
            self.current_pick += 1

            if self.current_pick >= self.CARDS_TO_DRAFT:
                self.phase = "review"
        
        elif self.phase == "redraft_cards_pick":
            self.drafted_cards.append(copy.deepcopy(card))
            self.cards_to_remove_count -= 1
            if self.cards_to_remove_count <= 0:
                self.phase = "review"
                self.cards_to_remove_count = 0

    def start_card_redraft(self):
        """Enter phase to remove 5 cards."""
        self.phase = "redraft_cards_select"
        self.cards_to_remove_count = 5

    def remove_card_for_redraft(self, index: int):
        """Remove a card during redraft selection."""
        if self.phase != "redraft_cards_select":
            return
        if 0 <= index < len(self.drafted_cards):
            self.drafted_cards.pop(index)
            self.cards_to_remove_count -= 1
            if self.cards_to_remove_count <= 0:
                self.phase = "redraft_cards_pick"
                self.cards_to_remove_count = 5 # Now we need to pick 5

    def start_leader_redraft(self):
        """Enter phase to maybe swap leader."""
        self.phase = "redraft_leader"

    def undo_last_pick(self) -> Optional[List[Card]]:
        """
        Undo the last pick and return to previous state.
        
        Returns:
            The previous choices if undo successful, None otherwise
        """
        if not self.pick_history or self.phase != "draft":
            return None
        
        # Pop last pick from history
        _, previous_choices = self.pick_history.pop()
        
        # Remove last drafted card
        if self.drafted_cards:
            self.drafted_cards.pop()
            self.current_pick -= 1
        
        return previous_choices

    def is_draft_complete(self) -> bool:
        """Check if drafting is complete."""
        return len(self.drafted_cards) >= self.CARDS_TO_DRAFT

    def get_synergy_score(self, card: Card) -> Dict:
        """
        Calculate synergy score for a card based on current deck.
        
        Args:
            card: Card to evaluate
            
        Returns:
            Dict with synergy info
        """
        synergy = {
            'score': 0,
            'reasons': [],
            'row_balance': 0,
            'has_copies': 0
        }
        
        # Check for Tactical Formation (tight bond) synergy
        if "Tactical Formation" in (card.ability or ""):
            copies_in_deck = sum(1 for c in self.drafted_cards if c.name == card.name)
            if copies_in_deck > 0:
                synergy['score'] += copies_in_deck * 3
                synergy['reasons'].append(f"+{copies_in_deck * 3} Tight Bond ({copies_in_deck} copies)")
                synergy['has_copies'] = copies_in_deck
        
        # Check for Gate Reinforcement (muster) synergy
        if "Gate Reinforcement" in (card.ability or ""):
            copies_in_deck = sum(1 for c in self.drafted_cards if c.name == card.name)
            if copies_in_deck > 0:
                synergy['score'] += copies_in_deck * 4
                synergy['reasons'].append(f"+{copies_in_deck * 4} Muster ({copies_in_deck} copies)")
                synergy['has_copies'] = copies_in_deck
        
        # Row balance scoring
        row_counts = {'close': 0, 'ranged': 0, 'siege': 0}
        for c in self.drafted_cards:
            if c.row in row_counts:
                row_counts[c.row] += 1
            elif c.row == 'agile':
                row_counts['close'] += 0.5
                row_counts['ranged'] += 0.5
        
        # Bonus for balancing rows
        if card.row in row_counts:
            min_row_count = min(row_counts.values())
            if row_counts[card.row] == min_row_count:
                synergy['score'] += 1
                synergy['row_balance'] = 1
                synergy['reasons'].append("+1 Row Balance")
        
        # Medic value increases with deck size
        if "Medical Evac" in (card.ability or ""):
            if len(self.drafted_cards) > 10:
                synergy['score'] += 2
                synergy['reasons'].append("+2 Medic Value")
        
        # Spy value early in draft (card advantage)
        if "Deep Cover Agent" in (card.ability or ""):
            if len(self.drafted_cards) < 15:
                synergy['score'] += 2
                synergy['reasons'].append("+2 Spy (Early Pick)")
        
        # Hero value
        if "Legendary Commander" in (card.ability or ""):
            hero_count = sum(1 for c in self.drafted_cards if "Legendary Commander" in (c.ability or ""))
            if hero_count < 2:
                synergy['score'] += 3
                synergy['reasons'].append("+3 Hero Value")
            elif hero_count >= 3:
                synergy['score'] -= 2
                synergy['reasons'].append("-2 Too Many Heroes")
        
        # Weather value
        if card.row == "weather":
            weather_count = sum(1 for c in self.drafted_cards if c.row == "weather")
            if weather_count == 0:
                synergy['score'] += 2
                synergy['reasons'].append("+2 First Weather")
            elif weather_count >= 2:
                synergy['score'] -= 2
                synergy['reasons'].append("-2 Too Much Weather")
        
        return synergy

    def get_deck_dict(self) -> Dict:
        """
        Get the drafted deck in standard deck format.

        Returns:
            Dict with 'leader' and 'cards' keys
        """
        return {
            'leader': self.drafted_leader,
            'cards': self.drafted_cards
        }

    def get_draft_stats(self) -> Dict:
        """
        Get statistics about the drafted deck.

        Returns:
            Dict with deck composition stats
        """
        stats = {
            'total_cards': len(self.drafted_cards),
            'total_power': sum(card.power for card in self.drafted_cards),
            'avg_power': sum(card.power for card in self.drafted_cards) / max(1, len(self.drafted_cards)),
            'faction_breakdown': {},
            'row_breakdown': {'close': 0, 'ranged': 0, 'siege': 0, 'agile': 0, 'weather': 0, 'special': 0},
            'ability_count': 0,
            'hero_count': 0,
            'spy_count': 0,
            'medic_count': 0
        }

        for card in self.drafted_cards:
            # Faction breakdown
            faction = card.faction
            stats['faction_breakdown'][faction] = stats['faction_breakdown'].get(faction, 0) + 1

            # Row breakdown
            row = card.row
            if row in stats['row_breakdown']:
                stats['row_breakdown'][row] += 1

            # Ability count
            if card.ability:
                stats['ability_count'] += 1
                if "Legendary Commander" in card.ability:
                    stats['hero_count'] += 1
                if "Deep Cover Agent" in card.ability:
                    stats['spy_count'] += 1
                if "Medical Evac" in card.ability:
                    stats['medic_count'] += 1

        return stats
        return previous_choices

    def is_draft_complete(self) -> bool:
        """Check if drafting is complete."""
        return len(self.drafted_cards) >= self.CARDS_TO_DRAFT
