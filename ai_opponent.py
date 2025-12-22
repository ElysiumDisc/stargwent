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
        """Analyze the current game state with comprehensive metrics."""
        # Calculate total board power for both players
        ai_board_power = sum(
            sum(c.displayed_power for c in row_cards)
            for row_cards in self.ai_player.board.values()
        )
        opp_board_power = sum(
            sum(c.displayed_power for c in row_cards)
            for row_cards in self.opponent.board.values()
        )
        
        # Calculate potential remaining hand power (estimate)
        ai_hand_power = sum(c.power for c in self.ai_player.hand)
        opp_hand_estimate = len(self.opponent.hand) * 5  # Estimate 5 avg power per card
        
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
            'ai_board_power': ai_board_power,
            'opp_board_power': opp_board_power,
            'ai_hand_power': ai_hand_power,
            'opp_hand_estimate': opp_hand_estimate,
            'card_advantage': len(self.ai_player.hand) - len(self.opponent.hand),
            'is_last_round': self.game.round_number == 3,
            'must_win_round': (self.game.round_number == 2 and self.ai_player.rounds_won == 0) or 
                              (self.game.round_number == 3 and self.ai_player.rounds_won < self.opponent.rounds_won),
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
        
        # Power Type Context
        power_name = getattr(self.ai_player.faction_power, 'name', '').lower()
        is_scorch = 'scorch' in power_name or 'destroy' in power_name
        is_revive = 'resurrect' in power_name or 'revive' in power_name

        # --- SCORCH SPECIFIC LOGIC ---
        if is_scorch:
            # Don't scorch if value is low (unless desperate)
            if power_value < 12 and context['score_diff'] > -20:
                return False
            # If opponent hasn't passed, waiting might yield a better target
            if not context['opponent_passed'] and power_value < 20:
                # But if we are losing badly, maybe use it
                if context['score_diff'] < -15:
                    pass # Consider using
                else:
                    return False # Wait for bigger targets

        # --- REVIVE SPECIFIC LOGIC ---
        if is_revive:
            # Don't revive weak stuff early
            if power_value < 10:
                return False
            # Save revive for R3 if possible
            if context['round_number'] < 3 and context['score_diff'] > -10:
                return False

        # If the power would provide huge value, use it
        if power_value >= 25:
            return True

        # Critical situations - we're losing badly
        if context['score_diff'] < -25:
            if power_value >= 10:
                return True

        # Round-specific strategy
        if context['round_number'] == 1:
            # Round 1: Only use if massive value (swing 20+ points)
            if power_value >= 20:
                return True
            # Or if it guarantees a pass-advantage (we catch up + get ahead)
            if context['score_diff'] < 0 and (context['score_diff'] + power_value) > 5:
                # But only if opponent passed, otherwise they can counter
                if context['opponent_passed']:
                    return True
        elif context['round_number'] == 2:
            # Round 2: Depends if we must win
            if context['ai_rounds_won'] == 0:  # Lost round 1, must win
                # Use if it swings the game
                if context['score_diff'] < 0 and (context['score_diff'] + power_value) > 0:
                    return True
            # If won round 1, SAVE power for round 3 mostly
            elif context['ai_rounds_won'] == 1:
                if power_value >= 30: # Only huge plays
                    return True
        elif context['round_number'] == 3:
            # Round 3: Use if it helps us win
            if power_value >= 8: # Lower threshold in final round
                return True
            # Or if losing and need every advantage
            if context['score_diff'] < 0:
                return True

        # Late in the round with few cards - use it or lose it
        if context['ai_cards_left'] == 0 and power_value >= 5:
            return True

        # Opponent passed and we're behind - last chance to catch up without spending cards
        if context['opponent_passed'] and context['score_diff'] < 0:
            if (context['score_diff'] + power_value) >= 0:
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
        card_advantage = context['ai_cards_left'] - context['opponent_cards_left']

        # If opponent passed
        if context['opponent_passed']:
            # If winning, pass immediately (Standard Gwent logic)
            if context['score_diff'] > 0:
                return True
            # If it's round 3 and must win, keep playing (obviously)
            if context['round_number'] == 3 and context['opponent_rounds_won'] >= 1:
                return False
            # If we lost R1, we MUST win R2. Never pass if losing R2.
            if context['round_number'] == 2 and context['ai_rounds_won'] == 0:
                return False
                
            # If losing by a lot and low on cards, pass to save cards for next round?
            # Only if we already WON a round (so this is R2/R3 context mismatch?)
            # If we won R1, and opponent passes R2 with huge lead... we might pass to save CA for R3.
            if context['ai_rounds_won'] == 1 and context['score_diff'] < -20:
                # Calculating if catching up is worth it happens in card selection, 
                # but sometimes cutting losses is better.
                return True

        # Strategic passing scenarios (Opponent still playing)

        # Round 1:
        if context['round_number'] == 1:
            # If winning comfortably (15+) and opponent has to play 2+ cards to catch up
            if context['score_diff'] > 15:
                # Pass if we have fewer cards (CA preservation)
                if card_advantage < 0:
                    return True
                # Or randomly if even cards, to force them down
                if card_advantage == 0 and self.rng.random() < 0.4:
                    return True

            # If we played many cards and winning big, pass to avoid overcommitting
            if context['score_diff'] > 25:
                return True

        # Round 2:
        elif context['round_number'] == 2:
            # If we won Round 1 (The "Bleed" Round)
            if context['ai_rounds_won'] == 1:
                # If we have card advantage, we can push or pass.
                # If we forced them down to equal cards or fewer, pass to take CA into R3.
                if context['ai_cards_left'] == context['opponent_cards_left']:
                    # We have last say in R3 if we pass now (they play 1 to win, go to R3 with -1 CA but we start? No winner starts next.)
                    # If we pass now, they MUST play. They go down to -1 card relative to us.
                    # This gives us Card Advantage in R3.
                    return True
                
                # If we are ahead on score in the bleed round, force them to play
                if context['score_diff'] > 0:
                    return True # They must play to catch up.
            
            # If we lost Round 1 (Must Win)
            elif context['ai_rounds_won'] == 0:
                # NEVER pass if losing or tied.
                if context['score_diff'] <= 0:
                    return False
                # If winning, only pass if we are sure they can't catch up easily? 
                # Risky. Usually better to stay ahead.
                if context['score_diff'] > 20 and context['opponent_cards_left'] < 2:
                    return True

        # Round 3:
        elif context['round_number'] == 3:
            # Never pass unless out of cards or guaranteed win (opp passed)
            # If we are winning by huge amount and have cards left, maybe BM pass? 
            # No, secure the win.
            pass

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
        
        # Base power value (raw points)
        score += card.power
        
        # --- AGILE CARD ROW OPTIMIZATION ---
        if card.row == "agile":
            # Smart row selection for agile cards
            close_weather = self.ai_player.weather_effects.get("close", False)
            ranged_weather = self.ai_player.weather_effects.get("ranged", False)
            close_horn = self.ai_player.horn_effects.get("close", False)
            ranged_horn = self.ai_player.horn_effects.get("ranged", False)
            
            # Prefer rows without weather
            if row == "close" and close_weather and not ranged_weather:
                score -= card.power * 0.7  # Significant penalty for weather row
            elif row == "ranged" and ranged_weather and not close_weather:
                score -= card.power * 0.7
            
            # Prefer rows with horn
            if row == "close" and close_horn and not ranged_horn:
                score += card.power * 0.5
            elif row == "ranged" and ranged_horn and not close_horn:
                score += card.power * 0.5
            
            # Consider synergy with existing cards (Tactical Formation)
            if "Tactical Formation" in (card.ability or ""):
                close_copies = sum(1 for c in self.ai_player.board.get("close", []) if c.name == card.name)
                ranged_copies = sum(1 for c in self.ai_player.board.get("ranged", []) if c.name == card.name)
                if row == "close" and close_copies > ranged_copies:
                    score += close_copies * card.power
                elif row == "ranged" and ranged_copies > close_copies:
                    score += ranged_copies * card.power
        
        # --- HERO LOGIC ---
        if "Legendary Commander" in (card.ability or ""):
            # Heroes are high value, save them!
            score += 10 # Intrinsic value
            
            # Penalize playing heroes early based on game state
            if context['round_number'] == 1:
                if context.get('must_win_round', False):
                    score -= 5  # Less penalty if we need this round
                else:
                    score -= 20  # Save for later
            elif context['round_number'] == 2:
                if context['ai_rounds_won'] == 1:
                    score -= 15 # Save for R3
                elif context['ai_rounds_won'] == 0:
                    score -= 5  # Must win, consider playing
            elif context['round_number'] == 3:
                score += 15 # Play them now!
            
            # Heroes immune to weather - HUGE value when weather is active
            if self.ai_player.weather_effects.get(row, False):
                score += 25
        
        # --- SPY LOGIC ---
        if "Deep Cover Agent" in (card.ability or ""):
            # Spies give points to enemy but draw cards
            # Play if we can afford the point loss, or desperate for cards
            card_diff = context['ai_cards_left'] - context['opponent_cards_left']
            
            if context['round_number'] == 2 and context['ai_rounds_won'] == 1:
                # Perfect time to bleed - play spy to gain CA
                score += 30
            elif context['score_diff'] > 15:
                # We are winning, can afford to play spy
                score += 20
            elif context['round_number'] == 1 and card_diff < 0:
                # Behind on cards, need to catch up
                score += 15
            else:
                score += 5 # Neutral
        
        # --- SYNERGY LOGIC ---
        # Tactical Formation evaluation (tight bond equivalent)
        if "Tactical Formation" in (card.ability or ""):
            # Check how many copies already on board
            copies_on_board = sum(
                1 for c in self.ai_player.board.get(row, []) 
                if c.name == card.name
            )
            if copies_on_board > 0:
                score += copies_on_board * card.power * 2.5  # Exponential bonus
            
            # Check hand for more copies (potential future value)
            copies_in_hand = sum(1 for c in self.ai_player.hand if c.name == card.name)
            if copies_in_hand > 1:
                score += 2 # Encourage starting the chain
        
        # Gate Reinforcement evaluation - auto-play all copies
        if "Gate Reinforcement" in (card.ability or ""):
            # Count copies in hand and deck
            copies = sum(
                1 for c in self.ai_player.hand + self.ai_player.deck 
                if c.name == card.name
            )
            # Massive tempo play
            score += copies * card.power * 1.5
            
            # If round 1/2 and losing, this swings tempo
            if context['score_diff'] < 0:
                score += 5
        
        # Medic evaluation
        if "Medical Evac" in (card.ability or ""):
            # Value based on best revival target
            best_revive = self.select_best_medic_target()
            if best_revive:
                revival_value = self.evaluate_medic_revival_value(best_revive, context)
                score += revival_value * 1.2
            else:
                score -= 10 # Don't play medic with no targets!
        
        # --- WEATHER / BOARD STATE ---
        # Weather considerations
        if self.ai_player.weather_effects.get(row, False):
            # Weather is active on this row
            if "Legendary Commander" not in (card.ability or ""):
                score -= card.power * 0.8 # Card effectively worth 1
        
        # Horn considerations
        if self.ai_player.horn_effects.get(row, False):
            if "Legendary Commander" not in (card.ability or ""):
                score += card.power * 1.2 # Bonus points
        
        # --- TEMPO / ROUND STRATEGY ---
        
        # If opponent passed and we're winning:
        if context['opponent_passed'] and context['score_diff'] > 0:
            # Why play? Pass instead. But if forced (logic in decide_action handles pass),
            # play absolute trash.
            score -= 100 
        
        # If opponent passed and we're losing:
        if context['opponent_passed'] and context['score_diff'] < 0:
            # We need to catch up. Calculate if this card is ENOUGH.
            needed = abs(context['score_diff'])
            if card.power >= needed:
                score += 50 # Winning play
            elif card.power + 5 >= needed: 
                score += 20 # Close
            else:
                score -= 5 # Doesn't help enough, maybe save it?
        
        # Bleeding Strategy (Round 2, we won R1)
        if context['round_number'] == 2 and context['ai_rounds_won'] == 1:
            # If we have card advantage, press it? Or play weak cards to force them?
            if card.power < 6:
                score += 5 # Play weak cards
            if "Deep Cover Agent" in (card.ability or ""):
                score += 50 # ALWAYS spy here
        
        return score
    
    def evaluate_weather_play(self, card, context: dict):
        """Evaluate playing a weather card. Returns list of (row, score)."""
        results = []
        ability = card.ability or ""
        
        if "Wormhole Stabilization" in ability:
            # Good if weather hurts us more than opponent, or to reset the board
            our_weather_damage = self.calculate_weather_damage(self.ai_player)
            opp_weather_damage = self.calculate_weather_damage(self.opponent)
            net_benefit = our_weather_damage - opp_weather_damage
            
            if net_benefit > 5:
                # Weather is hurting us significantly more
                score = net_benefit * 2.5
            elif our_weather_damage > 10:
                # We're taking significant weather damage
                score = our_weather_damage * 1.5
            elif any(self.game.weather_active.values()):
                # Weather is active but not hurting us much - low priority
                score = max(0, net_benefit)
            else:
                # No weather active - don't waste clear weather
                score = -15
            results.append(("close", score))
        else:
            # Offensive weather
            target_rows = self.get_weather_target_rows(ability)
            if not target_rows and "Electromagnetic Pulse" in ability:
                target_rows = ["close", "ranged", "siege"]
            
            for target_row in target_rows:
                # Calculate damage to opponent
                opp_power = self.count_non_hero_power(self.opponent, target_row)
                opp_card_count = sum(
                    1 for c in self.opponent.board.get(target_row, [])
                    if "Legendary Commander" not in (c.ability or "")
                )
                
                # Calculate self-damage (we also get affected)
                our_power = self.count_non_hero_power(self.ai_player, target_row)
                our_card_count = sum(
                    1 for c in self.ai_player.board.get(target_row, [])
                    if "Legendary Commander" not in (c.ability or "")
                )
                
                # Net damage = enemy damage - our damage
                enemy_damage = opp_power - opp_card_count  # Each card reduced to 1
                our_damage = our_power - our_card_count
                net_damage = enemy_damage - our_damage
                
                if net_damage > 8:
                    # Strong net advantage
                    score = net_damage * 2
                elif net_damage > 3:
                    # Moderate advantage
                    score = net_damage * 1.5
                elif net_damage > 0:
                    # Slight advantage - be cautious
                    score = net_damage - 2
                else:
                    # We'd hurt ourselves more - avoid
                    score = net_damage * 2  # Strong penalty
                
                # Weather already active on this row? Lower priority
                if self.game.weather_active.get(target_row, False):
                    score -= 10
                
                results.append((target_row, score))
        
        return results if results else [("close", -15.0)]
    
    def evaluate_special_play(self, card, context: dict) -> float:
        """Evaluate playing a special card with strategic timing."""
        score = 0.0
        ability = card.ability or ""
        
        if "Naquadah Overload" in ability:
            # Scorch: Destroy highest power non-hero cards
            opp_max = self.get_highest_non_hero_power(self.opponent)
            our_max = self.get_highest_non_hero_power(self.ai_player)
            
            # Count how many cards would be destroyed on each side
            opp_destroyed = sum(
                1 for row in self.opponent.board.values() for c in row
                if c.displayed_power == opp_max and "Legendary Commander" not in (c.ability or "")
            ) if opp_max > 0 else 0
            
            our_destroyed = sum(
                1 for row in self.ai_player.board.values() for c in row
                if c.displayed_power == opp_max and "Legendary Commander" not in (c.ability or "")
            ) if opp_max > 0 else 0
            
            # Calculate net value (enemy loss - our loss)
            net_destruction = (opp_destroyed * opp_max) - (our_destroyed * opp_max)
            
            if net_destruction > 15:
                # Massive swing - definitely play
                score = net_destruction * 1.5
            elif net_destruction > 8:
                # Good value
                score = net_destruction
            elif net_destruction > 0:
                # Slight advantage - consider timing
                if context['opponent_passed']:
                    score = net_destruction * 0.5  # Less urgent if they passed
                else:
                    score = net_destruction
            else:
                # We'd lose more or equal - avoid
                score = net_destruction * 2  # Strong penalty
            
            # Wait for higher targets if opponent hasn't passed
            if opp_max < 8 and not context['opponent_passed']:
                score -= 5  # Wait for bigger targets
        
        elif "Command Network" in ability:
            # Horn: Double non-hero power in a row
            best_row_score = 0
            best_row_potential = 0
            
            for row_name in ["close", "ranged", "siege"]:
                if not self.ai_player.horn_effects.get(row_name, False):
                    row_power = self.count_non_hero_power(self.ai_player, row_name)
                    card_count = sum(
                        1 for c in self.ai_player.board.get(row_name, [])
                        if "Legendary Commander" not in (c.ability or "")
                    )
                    
                    # Consider weather effects (if weather active, horn is less valuable)
                    if self.ai_player.weather_effects.get(row_name, False):
                        row_power = card_count  # All cards are 1 power
                    
                    if row_power > best_row_score:
                        best_row_score = row_power
                        best_row_potential = card_count
            
            score = best_row_score  # Will double this amount
            
            # Bonus if we have more cards coming to that row
            hand_cards_for_row = sum(
                1 for c in self.ai_player.hand 
                if c.row in ["close", "ranged", "siege", "agile"]
            )
            if hand_cards_for_row > 2:
                score += 3  # Room to grow
            
            # Timing: Wait if we don't have many cards on board yet
            if context['cards_on_board'] < 3 and context['ai_cards_left'] > 3:
                score -= 5  # Wait to build board first
        
        elif "Ring Transport" in ability:
            # Decoy: Return a unit to hand - good for reusing abilities
            best_target_value = 0
            for row_cards in self.ai_player.board.values():
                for c in row_cards:
                    if "Legendary Commander" not in (c.ability or ""):
                        target_value = c.power
                        # Bonus for cards with abilities
                        if "Medical Evac" in (c.ability or ""):
                            target_value += 8  # Reuse medic
                        if "Deep Cover Agent" in (c.ability or ""):
                            target_value += 10  # Reuse spy
                        if "Gate Reinforcement" in (c.ability or ""):
                            target_value += 6
                        if best_target_value < target_value:
                            best_target_value = target_value
            
            score = best_target_value * 0.8  # Slightly discount since we replay cost
        
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
