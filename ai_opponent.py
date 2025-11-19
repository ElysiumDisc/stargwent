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
        self.difficulty = "medium"  # easy, medium, hard
        self.power_used = False  # Track if faction power has been used
    
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
    
    def should_use_power(self, context: dict) -> bool:
        """Simple heuristic: use power when behind or late in the game."""
        if self.power_used or not self.ai_player.faction_power:
            return False
        if not self.ai_player.faction_power.is_available():
            return False

        # If we're significantly behind, fire immediately
        if context['score_diff'] < -15:
            return True

        # Near the end of the round or running low on cards
        late_round = context['round_number'] >= 3 or context['ai_cards_left'] <= 3
        if late_round:
            return True

        return False

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

        # 1. If we're ahead by a small margin, protect the lead
        if 1 <= context['score_diff'] <= 15 and context['opponent_cards_left'] >= 1:
            # Higher chance to use when opponent has fewer cards (their plays are more valuable)
            if context['opponent_cards_left'] <= 3:
                return True

        # 2. In round 3 when it's close and we're ahead
        if context['round_number'] == 3 and 0 < context['score_diff'] <= 10:
            return True

        # 3. If opponent has many cards on board (likely has strong cards)
        if context['opponent_cards_on_board'] >= 5 and context['score_diff'] > 0:
            if random.random() < 0.3:  # 30% chance to activate
                return True

        # 4. Random chance when ahead to be unpredictable
        if context['score_diff'] > 5 and random.random() < 0.15:
            return True

        return False
    
    def should_pass(self, context: dict) -> bool:
        """Determine if AI should pass."""
        # Always pass if no cards
        if context['ai_cards_left'] == 0:
            return True
        
        # If opponent passed
        if context['opponent_passed']:
            # If winning, pass
            if context['score_diff'] > 0:
                return True
            # If it's round 3 and must win, keep playing
            if context['round_number'] == 3 and context['opponent_rounds_won'] >= 1:
                return False
            # If losing by a lot and low on cards, pass to save cards
            if context['score_diff'] < -15 and context['ai_cards_left'] <= 3:
                return True
        
        # Strategic passing scenarios
        
        # Round 1: If winning by 10+ and used 6+ cards, consider passing
        if context['round_number'] == 1:
            if context['score_diff'] > 10 and context['cards_on_board'] >= 6:
                return random.random() < 0.7  # 70% chance to pass
        
        # If winning significantly and opponent hasn't passed
        if context['score_diff'] > 20 and not context['opponent_passed']:
            return random.random() < 0.4  # 40% chance to pass
        
        # Card advantage: if we have many more cards, might pass to save them
        card_advantage = context['ai_cards_left'] - context['opponent_cards_left']
        if card_advantage > 3 and context['score_diff'] > 5:
            return random.random() < 0.3  # 30% chance
        
        # Don't pass by default
        return False

    def should_use_hathor_ability(self, context: dict) -> bool:
        """Determine if AI should use Hathor's ability."""
        # Check if the AI player has Hathor as leader
        if not self.ai_player.leader or "Hathor" not in self.ai_player.leader.get('name', ''):
            return False
        
        # Check if the ability is already in progress
        if hasattr(self.ai_player, 'hathor_ability_pending') and self.ai_player.hathor_ability_pending:
            return False
        
        # Find the lowest power card on opponent's board
        lowest_card = None
        lowest_power = float('inf')
        
        for row_name, row_cards in self.opponent.board.items():
            for card in row_cards:
                # Skip Legendary Commanders and special cards
                if "Legendary Commander" in (card.ability or "") or card.row in ["special", "weather"]:
                    continue
                
                if card.power < lowest_power:
                    lowest_power = card.power
                    lowest_card = card
        
        # Use the ability if there's a valuable card to steal (power >= 5)
        if lowest_card and lowest_card.power >= 5:
            return True
        
        return False
    
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
            if len(plays) > 1 and random.random() < 0.3:
                return (plays[1][0], plays[1][1])
        elif self.difficulty == "easy":
            # More randomness
            if len(plays) > 2:
                choice = random.choice(plays[:3])
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
            # Value based on discard pile
            revivable = [
                c for c in self.ai_player.discard_pile 
                if "Legendary Commander" not in (c.ability or "") and c.row in ["close", "ranged", "siege", "agile"]
            ]
            if revivable:
                best_revive = max(revivable, key=lambda c: c.power)
                score += best_revive.power * 1.5
        
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
    
    def __init__(self, game, ai_player, difficulty="medium"):
        self.game = game
        self.ai_player = ai_player
        self.strategy = AIStrategy(game, ai_player)
        self.strategy.difficulty = difficulty
    
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
