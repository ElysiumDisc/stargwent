"""
Advanced AI opponent for Stargwent.
Implements strategic decision-making for competitive gameplay.
"""
import random
from typing import List, Tuple, Optional

class AIStrategy:
    """Strategic AI for playing Gwent."""
    
    def __init__(self, game, ai_player):
        self.game = game
        self.ai_player = ai_player
        self.opponent = game.player1  # Assume AI is always player2
        self.difficulty = "hard"  # single top difficulty
        self.power_used = False  # Track if faction power has been used
        self.rng = getattr(game, "rng", random)
    
    def decide_action(self) -> Tuple[str, Optional[object], Optional[str]]:
        """
        Decide what action to take.
        Returns: (action_type, card, row) where action_type is 'play', 'pass', or 'power'
        """
        # Calculate round context
        round_context = self.analyze_round_state()
        
        # Check if it's time to use Hathor's ability
        if self.should_use_hathor_ability(round_context):
            return ('hathor_ability', None, None)
        
        # Decide if it's time to use faction power
        if self.should_use_power(round_context):
            return ('power', None, None)
        
        # Decide whether to pass
        if self.should_pass(round_context):
            return ('pass', None, None)
        
        # Choose best card to play
        card, row = self.choose_best_card(round_context)
        
        if card:
            return ('play', card, row)
        else:
            return ('pass', None, None)
    
    def analyze_round_state(self) -> dict:
        """Analyze the current game state."""
        return {
            'round_number': self.game.round_number,
            'score_diff': self.ai_player.score - self.opponent.score,
            'ai_cards_left': len(self.ai_player.hand),
            'opponent_cards_left': len(self.opponent.hand),
            'opponent_passed': self.opponent.has_passed,
            'ai_rounds_won': self.ai_player.rounds_won,
            'opponent_rounds_won': self.opponent.rounds_won,
            'cards_on_board': sum(len(row) for row in self.ai_player.board.values()),
            'opponent_cards_on_board': sum(len(row) for row in self.opponent.board.values()),
        }

    def evaluate_hand_quality(self) -> float:
        """Evaluate the quality of cards remaining in hand. Returns average card value."""
        if not self.ai_player.hand:
            return 0.0

        total_value = 0.0
        for card in self.ai_player.hand:
            value = card.power

            # Heroes are premium
            if "Legendary Commander" in (card.ability or ""):
                value += 5

            # Spies are valuable (card advantage)
            if "Deep Cover Agent" in (card.ability or ""):
                value += 3

            # Synergy cards
            if "Tactical Formation" in (card.ability or ""):
                value += 2
            if "Gate Reinforcement" in (card.ability or ""):
                value += 3

            # Medics are valuable if discard pile has targets
            if "Medical Evac" in (card.ability or ""):
                if any(c.row in ["close", "ranged", "siege", "agile"] for c in self.ai_player.discard_pile):
                    value += 2

            # Special cards
            if card.row in ["special", "weather"]:
                value += 1

            total_value += value

        return total_value / len(self.ai_player.hand)

    def decide_mulligan(self) -> List[object]:
        """
        Decide which cards to mulligan at the start of the game.
        Returns list of cards to redraw (2-5 cards as per game rules).
        """
        if not self.ai_player.hand:
            return []

        # Evaluate each card for mulligan
        card_scores = []
        for card in self.ai_player.hand:
            score = self.evaluate_card_for_mulligan(card)
            card_scores.append((card, score))

        # Sort by score (lowest = worst cards = should mulligan)
        card_scores.sort(key=lambda x: x[1])

        # Analyze hand composition
        hand_analysis = self.analyze_hand_composition()

        # Determine how many cards to mulligan based on hand quality
        avg_score = sum(s for _, s in card_scores) / len(card_scores)

        # Decide mulligan count based on hand quality
        if avg_score < 4:
            # Terrible hand - mulligan 4-5 cards
            mulligan_count = self.rng.randint(4, 5)
        elif avg_score < 5:
            # Bad hand - mulligan 3-4 cards
            mulligan_count = self.rng.randint(3, 4)
        elif avg_score < 6:
            # Mediocre hand - mulligan 2-3 cards
            mulligan_count = self.rng.randint(2, 3)
        else:
            # Good hand - mulligan 2 cards (minimum)
            mulligan_count = 2

        # Adjust based on hand composition issues
        if hand_analysis['too_many_heroes'] > 3:
            mulligan_count = max(mulligan_count, 3)  # Too many heroes, mulligan more
        if hand_analysis['no_units']:
            mulligan_count = max(mulligan_count, 4)  # No units at all, mulligan heavily
        if hand_analysis['all_weak']:
            mulligan_count = max(mulligan_count, 4)  # All weak cards

        # Ensure within valid range (2-5 cards)
        mulligan_count = max(2, min(5, mulligan_count))

        # Select worst cards to mulligan
        cards_to_mulligan = [card for card, _ in card_scores[:mulligan_count]]

        return cards_to_mulligan

    def evaluate_card_for_mulligan(self, card) -> float:
        """
        Evaluate a card for mulligan decision.
        Lower score = worse card = should mulligan.
        Higher score = better card = should keep.
        """
        score = card.power

        # Heroes: Keep 1-2, mulligan extras
        if "Legendary Commander" in (card.ability or ""):
            hero_count = sum(1 for c in self.ai_player.hand
                           if "Legendary Commander" in (c.ability or ""))
            if hero_count <= 2:
                score += 8  # Keep first 2 heroes
            else:
                score -= 5  # Mulligan 3rd+ hero

        # Spies: Always keep (card advantage is critical)
        if "Deep Cover Agent" in (card.ability or ""):
            score += 10

        # Gate Reinforcement: Very strong, always keep
        if "Gate Reinforcement" in (card.ability or ""):
            score += 8

        # Tactical Formation: Keep if we have copies
        if "Tactical Formation" in (card.ability or ""):
            copies = sum(1 for c in self.ai_player.hand if c.name == card.name)
            if copies >= 2:
                score += 6  # Keep, we have synergy
            else:
                score += 2  # Less valuable alone

        # Medics: Not useful early, can mulligan
        if "Medical Evac" in (card.ability or ""):
            score -= 2  # Slight penalty, not useful in Round 1

        # Weather cards: Keep 1, mulligan extras
        if card.row == "weather":
            weather_count = sum(1 for c in self.ai_player.hand if c.row == "weather")
            if weather_count <= 1:
                score += 3
            else:
                score -= 3  # Don't need multiple weather cards

        # Special cards: Keep 1-2
        if card.row == "special":
            special_count = sum(1 for c in self.ai_player.hand if c.row == "special")
            if special_count <= 2:
                score += 2
            else:
                score -= 2

        # Very weak cards (power 1-2): Consider mulliganing
        if card.power <= 2 and not card.ability:
            score -= 4

        # Strong cards (power 7+): Keep
        if card.power >= 7:
            score += 3

        return score

    def analyze_hand_composition(self) -> dict:
        """Analyze hand composition for mulligan decisions."""
        hero_count = 0
        unit_count = 0
        special_count = 0
        weather_count = 0
        total_power = 0
        has_synergy = False

        for card in self.ai_player.hand:
            total_power += card.power

            if "Legendary Commander" in (card.ability or ""):
                hero_count += 1
            elif card.row in ["close", "ranged", "siege", "agile"]:
                unit_count += 1
            elif card.row == "special":
                special_count += 1
            elif card.row == "weather":
                weather_count += 1

            # Check for synergies
            if "Tactical Formation" in (card.ability or "") or "Gate Reinforcement" in (card.ability or ""):
                copies = sum(1 for c in self.ai_player.hand if c.name == card.name)
                if copies >= 2:
                    has_synergy = True

        avg_power = total_power / len(self.ai_player.hand) if self.ai_player.hand else 0

        return {
            'too_many_heroes': hero_count > 3,
            'no_units': unit_count == 0,
            'all_weak': avg_power < 3,
            'has_synergy': has_synergy,
            'weather_count': weather_count,
            'special_count': special_count
        }
    
    def should_use_power(self, context: dict) -> bool:
        """Strategically decide when to use faction power."""
        if self.power_used or not self.ai_player.faction_power:
            return False
        if not self.ai_player.faction_power.is_available():
            return False

        # Estimate the value we'd get from using the power
        power_value = self.estimate_faction_power_value()

        # If the power would provide huge value, use it
        if power_value >= 15:
            return True

        # Critical situations - we're losing badly
        if context['score_diff'] < -20:
            # Use if power provides meaningful value
            if power_value >= 8:
                return True

        # Mid-range behind - use if it can swing the game
        if -20 <= context['score_diff'] < -10:
            if power_value >= 10:
                return True

        # Round-specific strategy
        if context['round_number'] == 1:
            # Round 1: Only use if massive value and we're behind
            if context['score_diff'] < -15 and power_value >= 12:
                return True
        elif context['round_number'] == 2:
            # Round 2: More willing to use, especially if must win
            if context['ai_rounds_won'] == 0:  # Lost round 1, must win this
                if context['score_diff'] < 0 and power_value >= 8:
                    return True
            # If won round 1, save power for round 3 unless great value
            elif context['ai_rounds_won'] == 1:
                if power_value >= 15:
                    return True
        elif context['round_number'] == 3:
            # Round 3: Use if it helps us win
            if context['score_diff'] < 5 and power_value >= 6:
                return True
            # Or if losing and need every advantage
            if context['score_diff'] < 0:
                return True

        # Late in the round with few cards - use it or lose it
        if context['ai_cards_left'] <= 2 and power_value >= 5:
            return True

        # Opponent passed and we're behind - last chance
        if context['opponent_passed'] and context['score_diff'] < 0:
            if power_value >= 5:
                return True

        return False

    def estimate_faction_power_value(self) -> float:
        """Estimate how much value faction power would provide. Override for specific factions."""
        # Generic estimation - subclass can override for specific powers
        # Most faction powers are worth roughly 10-15 points
        base_value = 10.0

        # Check the power name if available
        if hasattr(self.ai_player.faction_power, 'name'):
            power_name = self.ai_player.faction_power.name.lower()

            # Powers that draw cards or revive are more valuable with good discard pile
            if 'resurrect' in power_name or 'revive' in power_name:
                revivable = [c for c in self.ai_player.discard_pile
                           if c.row in ["close", "ranged", "siege", "agile"]]
                if revivable:
                    best = max(revivable, key=lambda c: c.power)
                    base_value = best.power + 5
                else:
                    base_value = 2

            # Powers that damage enemy cards are valuable if enemy has high power
            elif 'scorch' in power_name or 'destroy' in power_name:
                opp_max = self.get_highest_non_hero_power(self.opponent)
                base_value = max(opp_max, 8)

            # Powers that boost own units
            elif 'boost' in power_name or 'strengthen' in power_name:
                cards_on_board = sum(len(row) for row in self.ai_player.board.values())
                base_value = cards_on_board * 2

        return base_value

    def should_use_iris_defense(self) -> bool:
        """Decide if AI should activate Iris Defense to block next opponent card."""
        # Check if AI has iris defense available
        if not hasattr(self.ai_player, 'iris_defense'):
            return False
        if not self.ai_player.iris_defense.is_available():
            return False
        if self.ai_player.iris_defense.is_active():
            return False

        # Don't use if opponent has already passed
        if self.opponent.has_passed:
            return False

        # Don't use if opponent has no cards
        if len(self.opponent.hand) == 0:
            return False

        context = self.analyze_round_state()

        # Use iris defense strategically:

        # 1. Critical round 3 protection when we're barely ahead
        if context['round_number'] == 3:
            if 0 < context['score_diff'] <= 12:
                # Very likely to use in close round 3
                return self.rng.random() < 0.8
            elif context['score_diff'] <= 0 and context['opponent_cards_left'] >= 2:
                # Even when tied or slightly behind, might block a strong play
                return self.rng.random() < 0.4

        # 2. Protect narrow leads when opponent has few cards left (high value plays expected)
        if 1 <= context['score_diff'] <= 15 and context['opponent_cards_left'] <= 3:
            # More likely when opponent has fewer, stronger cards
            use_chance = 0.5 + (0.15 * (3 - context['opponent_cards_left']))
            return self.rng.random() < use_chance

        # 3. In round 2, protect a good lead to secure the round
        if context['round_number'] == 2:
            # If we lost round 1, this round is critical
            if context['ai_rounds_won'] == 0 and 1 <= context['score_diff'] <= 20:
                return self.rng.random() < 0.6
            # If we won round 1, can be more conservative
            elif context['ai_rounds_won'] == 1 and 1 <= context['score_diff'] <= 10:
                return self.rng.random() < 0.3

        # 4. If opponent has lots of cards on board, they likely have strong cards in hand
        if context['opponent_cards_on_board'] >= 6 and 0 < context['score_diff'] <= 20:
            return self.rng.random() < 0.35

        # 5. Card advantage play - if we're ahead with more cards, preserve both advantages
        card_advantage = context['ai_cards_left'] - context['opponent_cards_left']
        if card_advantage >= 2 and 3 <= context['score_diff'] <= 15:
            return self.rng.random() < 0.25

        # 6. Unpredictable use when ahead (mind games)
        if context['score_diff'] > 8 and self.rng.random() < 0.1:
            return True

        return False
    
    def should_pass(self, context: dict) -> bool:
        """Determine if AI should pass with advanced strategy."""
        # Always pass if no cards
        if context['ai_cards_left'] == 0:
            return True

        # Evaluate hand quality for decision making
        hand_quality = self.evaluate_hand_quality()
        card_advantage = context['ai_cards_left'] - context['opponent_cards_left']

        # If opponent passed
        if context['opponent_passed']:
            # If winning, pass immediately
            if context['score_diff'] > 0:
                return True
            # If it's round 3 and must win, keep playing
            if context['round_number'] == 3 and context['opponent_rounds_won'] >= 1:
                return False
            # If losing by a lot and low on cards, pass to save cards for next round
            if context['score_diff'] < -15 and context['ai_cards_left'] <= 3:
                return True

        # Strategic passing scenarios

        # Round 1: Conservative play - save cards for later rounds
        if context['round_number'] == 1:
            # If winning comfortably with decent cards played, pass to save hand
            if context['score_diff'] > 10 and context['cards_on_board'] >= 5:
                # More likely to pass if we have card advantage
                pass_chance = 0.6 if card_advantage >= 0 else 0.4
                return self.rng.random() < pass_chance

            # If winning big with many cards played, definitely consider passing
            if context['score_diff'] > 20 and context['cards_on_board'] >= 6:
                return self.rng.random() < 0.8

            # If we used too many cards (7+) and barely winning, pass to cut losses
            if context['cards_on_board'] >= 7 and context['score_diff'] > 0:
                return self.rng.random() < 0.5

        # Round 2: Depends on Round 1 outcome
        elif context['round_number'] == 2:
            # If we won round 1, can afford to pass early if ahead
            if context['ai_rounds_won'] == 1:
                if context['score_diff'] > 15 and context['cards_on_board'] >= 4:
                    return self.rng.random() < 0.5
            # If we lost round 1, must win this round - be more aggressive
            elif context['ai_rounds_won'] == 0:
                # Only pass if winning significantly
                if context['score_diff'] > 25 and context['cards_on_board'] >= 6:
                    return self.rng.random() < 0.3

        # Round 3: All or nothing, but still strategic
        elif context['round_number'] == 3:
            # If winning by a lot and opponent hasn't passed, might bluff pass
            if context['score_diff'] > 30 and not context['opponent_passed']:
                return self.rng.random() < 0.2

        # General: If winning significantly and opponent hasn't passed
        if context['score_diff'] > 20 and not context['opponent_passed']:
            # Consider hand quality - pass more if we have weak cards remaining
            pass_chance = 0.3 if hand_quality > 5 else 0.5
            return self.rng.random() < pass_chance

        # Card advantage strategy: if we have more cards and winning, preserve advantage
        if card_advantage >= 3 and context['score_diff'] > 5:
            # Higher chance to pass if winning comfortably with big card advantage
            pass_chance = min(0.5, card_advantage * 0.1)
            return self.rng.random() < pass_chance

        # Don't pass by default
        return False

    def should_use_hathor_ability(self, context: dict) -> bool:
        """Determine if AI should use Hathor's ability with smart target selection."""
        # Check if the AI player has Hathor as leader
        if not self.ai_player.leader or "Hathor" not in self.ai_player.leader.get('name', ''):
            return False

        # Check if the ability is already in progress
        if hasattr(self.ai_player, 'hathor_ability_pending') and self.ai_player.hathor_ability_pending:
            return False

        # Find the best target to steal
        best_target = self.select_hathor_target()

        if not best_target:
            return False

        # Calculate the value of stealing this card
        steal_value = self.evaluate_hathor_steal_value(best_target, context)

        # Use ability if value is good enough
        if steal_value >= 8:
            return True

        # In critical situations, lower threshold
        if context['score_diff'] < -10 and steal_value >= 5:
            return True

        # Round 3 - more aggressive
        if context['round_number'] == 3 and context['score_diff'] < 5 and steal_value >= 6:
            return True

        return False

    def select_hathor_target(self) -> Optional[object]:
        """Select the best card to steal with Hathor's ability."""
        candidates = []

        for row_name, row_cards in self.opponent.board.items():
            for card in row_cards:
                # Skip Legendary Commanders and special cards
                if "Legendary Commander" in (card.ability or "") or card.row in ["special", "weather"]:
                    continue
                candidates.append(card)

        if not candidates:
            return None

        # Score each candidate
        best_card = None
        best_score = -1

        for card in candidates:
            score = card.power

            # Valuable abilities make cards better targets
            if card.ability:
                if "Tactical Formation" in card.ability:
                    # Check how many copies opponent has
                    copies = sum(1 for c in candidates if c.name == card.name)
                    if copies > 1:
                        score += copies * 3  # Breaking synergy is valuable

                if "Gate Reinforcement" in card.ability:
                    score += 5  # Very valuable ability

                if "Medical Evac" in card.ability:
                    score += 3

                if "Deep Cover Agent" in card.ability:
                    score += 2  # Spy already used, but still decent

            # Consider row synergy - steal from rows opponent is strong in
            row_power = sum(c.power for c in self.opponent.board.get(card.row, []))
            if row_power >= 20:
                score += 2  # Weakening their strong row

            # Horn/Weather considerations
            if self.opponent.horn_effects.get(card.row, False):
                score += card.power  # Card is doubled, stealing removes more value

            if score > best_score:
                best_score = score
                best_card = card

        return best_card

    def evaluate_hathor_steal_value(self, card, context: dict) -> float:
        """Evaluate how valuable it is to steal a specific card."""
        # Base value: we gain the card's power, opponent loses it
        value = card.power * 2

        # Synergy bonus
        if "Tactical Formation" in (card.ability or ""):
            # We might be able to use it with our own copies
            our_copies = sum(1 for c in self.ai_player.board.get(card.row, []) if c.name == card.name)
            value += our_copies * 3

        # Breaking opponent's synergy
        if "Tactical Formation" in (card.ability or ""):
            opp_copies = sum(1 for c in self.opponent.board.get(card.row, []) if c.name == card.name)
            if opp_copies > 1:
                value += opp_copies * 2

        # Horn row consideration
        if self.opponent.horn_effects.get(card.row, False):
            value += card.power  # Actually worth double on their side

        if self.ai_player.horn_effects.get(card.row, False):
            value += card.power  # Will be worth double on our side

        return value

    def select_best_medic_target(self) -> Optional[object]:
        """Select the best card to revive from discard pile."""
        revivable = [
            c for c in self.ai_player.discard_pile
            if "Legendary Commander" not in (c.ability or "") and c.row in ["close", "ranged", "siege", "agile"]
        ]

        if not revivable:
            return None

        # Score each candidate
        best_card = None
        best_score = -1

        for card in revivable:
            score = card.power * 1.5  # Base power value

            # Prioritize cards with valuable abilities
            if card.ability:
                if "Tactical Formation" in card.ability:
                    # Check if we have copies on board to synergize with
                    copies_on_board = sum(
                        1 for c in self.ai_player.board.get(card.row, [])
                        if c.name == card.name
                    )
                    score += copies_on_board * 5  # Great synergy

                if "Gate Reinforcement" in card.ability:
                    score += 8  # Will pull more cards

                if "Medical Evac" in card.ability:
                    # Another medic is valuable if we have more cards to revive
                    if len(revivable) > 3:
                        score += 5

                if "Deep Cover Agent" in card.ability:
                    # Already used as spy, less valuable now
                    score += 1

            # Consider horn effects on target row
            if self.ai_player.horn_effects.get(card.row, False):
                score += card.power  # Will be doubled

            # Weather penalties
            if self.ai_player.weather_effects.get(card.row, False):
                if "Legendary Commander" not in (card.ability or ""):
                    score -= card.power * 0.5  # Will be reduced to 1

            if score > best_score:
                best_score = score
                best_card = card

        return best_card

    def evaluate_medic_revival_value(self, card, context: dict) -> float:
        """Evaluate how valuable it is to revive a specific card."""
        value = card.power * 1.5

        # Synergy bonuses
        if "Tactical Formation" in (card.ability or ""):
            copies_on_board = sum(
                1 for c in self.ai_player.board.get(card.row, [])
                if c.name == card.name
            )
            value += copies_on_board * card.power  # Multiplicative synergy

        if "Gate Reinforcement" in (card.ability or ""):
            # Check deck for more copies
            copies_in_deck = sum(1 for c in self.ai_player.deck if c.name == card.name)
            value += copies_in_deck * card.power

        # Horn bonus
        if self.ai_player.horn_effects.get(card.row, False):
            value += card.power

        # Weather penalty
        if self.ai_player.weather_effects.get(card.row, False):
            if "Legendary Commander" not in (card.ability or ""):
                value *= 0.3  # Heavy penalty

        return value

    def choose_best_card(self, context: dict) -> Tuple[Optional[object], Optional[str]]:
        """Choose the best card to play based on strategy."""
        if not self.ai_player.hand:
            return (None, None)
        
        # Evaluate all possible plays
        plays = []
        for card in self.ai_player.hand:
            # Get valid rows for this card
            if card.row == "weather":
                weather_options = self.evaluate_weather_play(card, context)
                for row_option, row_score in weather_options:
                    plays.append((card, row_option, row_score))
            elif card.row == "special":
                plays.append((card, "close", self.evaluate_special_play(card, context)))
            else:
                valid_rows = self.get_valid_rows(card)
                for row in valid_rows:
                    score = self.evaluate_card_play(card, row, context)
                    plays.append((card, row, score))
        
        if not plays:
            return (None, None)
        
        # Sort by score (highest first)
        plays.sort(key=lambda x: x[2], reverse=True)
        
        # Add some randomness for medium difficulty
        if self.difficulty == "medium":
            # 70% best play, 30% second best
            if len(plays) > 1 and self.rng.random() < 0.3:
                return (plays[1][0], plays[1][1])
        elif self.difficulty == "easy":
            # More randomness
            if len(plays) > 2:
                choice = self.rng.choice(plays[:3])
                return (choice[0], choice[1])
        
        return (plays[0][0], plays[0][1])
    
    def evaluate_card_play(self, card, row: str, context: dict) -> float:
        """Evaluate how good it is to play this card in this row."""
        score = 0.0
        
        # Base power value
        score += card.power * 2
        
        # Hero cards are valuable
        if "Legendary Commander" in (card.ability or ""):
            score += 15
            # Save heroes if weather is active
            if self.ai_player.weather_effects.get(row, False):
                score += 20  # Heroes immune to weather
        
        # Spy cards - great for card advantage
        if "Deep Cover Agent" in (card.ability or ""):
            # Very valuable early game or when behind on cards
            card_diff = context['ai_cards_left'] - context['opponent_cards_left']
            if card_diff <= 0:
                score += 25
            else:
                score += 15
            # Less valuable if already winning big
            if context['score_diff'] > 20:
                score -= 10
        
        # Tactical Formation evaluation (tight bond equivalent)
        if "Tactical Formation" in (card.ability or ""):
            # Check how many copies already on board
            copies_on_board = sum(
                1 for c in self.ai_player.board.get(row, []) 
                if c.name == card.name
            )
            if copies_on_board > 0:
                score += copies_on_board * card.power * 2  # Multiply bonus
        
        # Gate Reinforcement evaluation - auto-play all copies
        if "Gate Reinforcement" in (card.ability or ""):
            # Count copies in hand and deck
            copies = sum(
                1 for c in self.ai_player.hand + self.ai_player.deck 
                if c.name == card.name
            )
            score += copies * card.power  # Massive value
        
        # Medic evaluation
        if "Medical Evac" in (card.ability or ""):
            # Value based on best revival target
            best_revive = self.select_best_medic_target()
            if best_revive:
                revival_value = self.evaluate_medic_revival_value(best_revive, context)
                score += revival_value
        
        # Weather considerations
        if self.ai_player.weather_effects.get(row, False):
            # Weather is active on this row
            if "Legendary Commander" not in (card.ability or ""):
                score -= card.power  # Card will be reduced to 1
        
        # Horn considerations
        if self.ai_player.horn_effects.get(row, False):
            if "Legendary Commander" not in (card.ability or ""):
                score += card.power  # Will be doubled
        
        # Round strategy
        if context['round_number'] == 1:
            # Round 1: Play medium cards, save strong cards
            if card.power > 8 and "Legendary Commander" not in (card.ability or ""):
                score -= 10  # Penalty for playing strong cards early
        elif context['round_number'] == 2:
            # Round 2: Play strong cards if necessary
            if context['ai_rounds_won'] == 0:  # Must win
                score += 10
        elif context['round_number'] == 3:
            # Round 3: All or nothing
            score += card.power  # Play everything
        
        # If opponent passed and we're winning, prefer low-value cards
        if context['opponent_passed'] and context['score_diff'] > 0:
            score -= card.power * 0.5  # Prefer cheap cards
        
        return score
    
    def evaluate_weather_play(self, card, context: dict):
        """Evaluate playing a weather card. Returns list of (row, score)."""
        results = []
        ability = card.ability or ""
        
        if "Wormhole Stabilization" in ability:
            # Good if weather hurts us more than opponent
            our_weather_damage = self.calculate_weather_damage(self.ai_player)
            opp_weather_damage = self.calculate_weather_damage(self.opponent)
            if our_weather_damage > opp_weather_damage:
                score = (our_weather_damage - opp_weather_damage) * 2
            else:
                score = -2  # Mild penalty if not needed
            results.append(("close", score))
        else:
            # Offensive weather
            target_rows = self.get_weather_target_rows(ability)
            if not target_rows and "Electromagnetic Pulse" in ability:
                target_rows = ["close", "ranged", "siege"]
            for target_row in target_rows:
                opp_power = self.count_non_hero_power(self.opponent, target_row)
                
                damage_diff = opp_power
                if damage_diff > 5:  # Only if it hurts opponent meaningfully
                    score = damage_diff * 1.5
                else:
                    score = damage_diff - 5  # Slight penalty to discourage poor plays
                results.append((target_row, score))
        
        return results if results else [("close", -5.0)]
    
    def evaluate_special_play(self, card, context: dict) -> float:
        """Evaluate playing a special card."""
        score = 0.0
        ability = card.ability or ""
        
        if "Naquadah Overload" in ability:
            # Good if opponent has high power units
            opp_max = self.get_highest_non_hero_power(self.opponent)
            our_max = self.get_highest_non_hero_power(self.ai_player)
            
            if opp_max > our_max:
                score += (opp_max - our_max) * 2
            elif opp_max > 8:  # High value target
                score += opp_max
        
        elif "Command Network" in ability:
            # Evaluate best row to apply horn
            best_row_score = 0
            for row_name in ["close", "ranged", "siege"]:
                if not self.ai_player.horn_effects.get(row_name, False):
                    row_power = self.count_non_hero_power(self.ai_player, row_name)
                    if row_power > best_row_score:
                        best_row_score = row_power
            score += best_row_score  # Will double this row
        
        return score
    
    def get_valid_rows(self, card) -> List[str]:
        """Get valid rows for a card."""
        if card.row == "agile":
            return ["close", "ranged"]
        elif card.row in ["close", "ranged", "siege"]:
            return [card.row]
        return []
    
    def get_weather_target_rows(self, ability: str) -> List[str]:
        """Get which rows a weather card affects."""
        if "Ice Planet Hazard" in ability:
            return ["close"]
        elif "Nebula Interference" in ability:
            return ["ranged"]
        elif "Asteroid Storm" in ability:
            return ["siege"]
        return []
    
    def calculate_weather_damage(self, player) -> int:
        """Calculate how much weather is hurting a player."""
        damage = 0
        for row_name, is_weathered in player.weather_effects.items():
            if is_weathered:
                for card in player.board.get(row_name, []):
                    if "Legendary Commander" not in (card.ability or ""):
                        damage += max(0, card.power - 1)
        return damage
    
    def count_non_hero_power(self, player, row: str) -> int:
        """Count non-hero power in a row."""
        return sum(
            card.power for card in player.board.get(row, [])
            if "Legendary Commander" not in (card.ability or "")
        )
    
    def get_highest_non_hero_power(self, player) -> int:
        """Get the highest power non-hero unit."""
        max_power = 0
        for row in player.board.values():
            for card in row:
                if "Legendary Commander" not in (card.ability or "") and card.displayed_power > max_power:
                    max_power = card.displayed_power
        return max_power


class AIController:
    """Controls the AI player's actions."""
    
    def __init__(self, game, ai_player, difficulty="hard"):
        self.game = game
        self.ai_player = ai_player
        self.strategy = AIStrategy(game, ai_player)
        self.strategy.difficulty = "hard"
    
    def choose_move(self):
        """Choose a move without executing it. Returns (card, row) tuple."""
        if self.ai_player.has_passed:
            return (None, None)
        
        action_type, card, row = self.strategy.decide_action()
        
        if action_type == 'play' and card:
            return (card, row)
        elif action_type == 'pass':
            self.game.pass_turn()
            return (None, None)
        elif action_type == 'power':
            # Use faction power
            if not self.ai_player.power_used:
                self.ai_player.power_used = True
                self.strategy.power_used = True
                if self.ai_player.faction_power:
                    if self.ai_player.faction_power.activate(self.game, self.ai_player):
                        self.game.add_history_event(
                            "faction_power",
                            f"{self.ai_player.name} used {self.ai_player.faction_power.name}",
                            "ai"
                        )
            return (None, None)
        
        return (None, None)
    
    def take_turn(self):
        """Execute the AI's turn."""
        if self.ai_player.has_passed:
            return
        
        action_type, card, row = self.strategy.decide_action()
        
        if action_type == 'hathor_ability':
            if self.game.trigger_hathor_ability(self.ai_player):
                self.game.switch_turn()
                return 'hathor_ability'
        elif action_type == 'power':
            # Use faction power
            if not self.ai_player.power_used:
                self.ai_player.power_used = True
                self.strategy.power_used = True
                return 'power'  # Signal to main game to trigger power animation
        elif action_type == 'pass':
            self.game.pass_turn()
        elif action_type == 'play' and card:
            self.game.play_card(card, row)
        
        return action_type
