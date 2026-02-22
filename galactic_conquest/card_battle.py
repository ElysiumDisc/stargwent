"""
STARGWENT - GALACTIC CONQUEST - Card Battle Wrapper

Runs a complete card battle (mulligan → play → game over) for conquest mode.
Reuses the existing main.py game loop by passing a pre-built Game object.
"""

import copy
import random

from cards import ALL_CARDS
from deck_builder import build_faction_deck, load_default_faction_deck, FACTION_LEADERS
from game import Game
from ai_opponent import AIController


def run_card_battle(screen, player_faction, player_leader, player_deck_ids,
                    ai_faction, ai_leader, exempt_penalties=True,
                    starting_weather=None, upgraded_cards=None):
    """
    Run a complete card battle for Galactic Conquest.

    Uses the existing main.py game loop by passing a pre-built Game via lan_game_data.

    Args:
        screen: Pygame display surface
        player_faction: Player's faction string
        player_leader: Player's leader dict
        player_deck_ids: List of card ID strings for player deck
        ai_faction: AI faction string
        ai_leader: AI leader dict (or None to pick random)
        exempt_penalties: True to exempt player from cross-faction penalties
        starting_weather: Optional weather preset dict (not yet wired)
        upgraded_cards: Optional dict of card_id → power bonus

    Returns:
        "player_win" | "player_loss" | "draw" | "quit"
    """
    # Build player deck from card IDs
    player_deck = []
    for cid in player_deck_ids:
        if cid in ALL_CARDS:
            card = copy.deepcopy(ALL_CARDS[cid])
            # Apply roguelite card upgrades
            if upgraded_cards and cid in upgraded_cards:
                bonus = upgraded_cards[cid]
                if hasattr(card, 'power') and card.power is not None:
                    card.power += bonus
            player_deck.append(card)
    random.shuffle(player_deck)

    # Pick AI leader if not provided
    if ai_leader is None:
        leaders = FACTION_LEADERS.get(ai_faction, [])
        if leaders:
            ai_leader = dict(random.choice(leaders))
            ai_leader.setdefault('faction', ai_faction)

    # Build AI deck
    ai_deck_ids = load_default_faction_deck(ai_faction)
    if not ai_deck_ids:
        ai_deck_ids = build_faction_deck(ai_faction, ai_leader)
    ai_deck = [copy.deepcopy(ALL_CARDS[cid]) for cid in ai_deck_ids if cid in ALL_CARDS]

    # Create Game object
    game = Game(
        player1_faction=player_faction,
        player1_deck=player_deck,
        player1_leader=player_leader,
        player2_faction=ai_faction,
        player2_deck=ai_deck,
        player2_leader=ai_leader,
        player2_is_ai=True,
        player1_exempt_penalties=exempt_penalties,
    )

    # Create AI controller
    ai_controller = AIController(game, game.player2, difficulty="hard")

    # Use main.py's game loop by passing the game object through lan_game_data
    # This reuses 100% of the existing battle code (mulligan, events, rendering, AI)
    import main as _main
    result = _main.main(lan_game_data={
        'game': game,
        'ai_controller': ai_controller,
    })

    # Determine outcome from the game object
    if game.game_state == "game_over":
        if game.winner == game.player1:
            return "player_win"
        elif game.winner == game.player2:
            return "player_loss"
        else:
            return "draw"

    # If main() returned "quit" or "restart", treat as quit from conquest perspective
    return "quit"
