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


# Weather preset display names
_WEATHER_TYPE_MAP = {
    "ice_planet_hazard": "Ice Planet Hazard",
    "nebula_interference": "Nebula Interference",
    "asteroid_storm": "Asteroid Storm",
    "emp": "EMP Disruption",
}


def _apply_relic_combat_modifiers(relics, player_deck, ai_deck, player_faction):
    """Apply relic effects to decks before battle starts."""
    for card in player_deck:
        # Staff of Ra: +1 power to Goa'uld cards
        if "staff_of_ra" in relics and getattr(card, 'faction', None) == "Goa'uld":
            if hasattr(card, 'power') and card.power is not None:
                card.power += 1
        # Thor's Hammer: +2 to Hero cards
        if "thors_hammer" in relics and getattr(card, 'card_type', '') == "Hero":
            if hasattr(card, 'power') and card.power is not None:
                card.power += 2

    # Kull Armor: -1 to all enemy cards (min 1)
    if "kull_armor" in relics:
        for card in ai_deck:
            if hasattr(card, 'power') and card.power is not None and card.power > 1:
                card.power -= 1

    # Ori Prior Staff: flag for weather minimum 3 (applied in game.py calculate_score)
    # (Handled via game.conquest_relics check in Player.calculate_score)

    # Weaken enemy passive: handled in campaign_controller before calling run_card_battle


async def run_card_battle(screen, player_faction, player_leader, player_deck_ids,
                    ai_faction, ai_leader, exempt_penalties=True,
                    starting_weather=None, upgraded_cards=None,
                    ai_elite_bonus=0, ai_extra_cards=0, relics=None,
                    ai_weaken_amount=0, extra_player_cards=0,
                    fort_defense_bonus=0):
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
        starting_weather: Optional weather preset dict {row, type} to activate at battle start
        upgraded_cards: Optional dict of card_id → power bonus
        ai_elite_bonus: Power bonus applied to all AI cards (elite homeworld defenders)
        ai_extra_cards: Number of extra random faction cards added to AI deck
        relics: Optional list of relic ID strings for combat modifiers

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

    # Pick player leader if not provided (per-battle selection may have been skipped)
    if player_leader is None:
        leaders = FACTION_LEADERS.get(player_faction, [])
        if leaders:
            player_leader = dict(random.choice(leaders))
            player_leader.setdefault('faction', player_faction)

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

    # Elite homeworld defenders: add extra cards to AI deck
    if ai_extra_cards > 0:
        faction_pool = [cid for cid, c in ALL_CARDS.items()
                        if getattr(c, 'faction', None) == ai_faction
                        and getattr(c, 'card_type', '') != "Legendary Commander"
                        and getattr(c, 'row', '') != "weather"]
        if faction_pool:
            for _ in range(ai_extra_cards):
                cid = random.choice(faction_pool)
                ai_deck.append(copy.deepcopy(ALL_CARDS[cid]))

    # Elite homeworld defenders: boost all AI card power
    if ai_elite_bonus > 0:
        for card in ai_deck:
            if hasattr(card, 'power') and card.power is not None:
                card.power += ai_elite_bonus

    # Relic combat modifiers — apply to player/AI decks before game starts
    if relics:
        _apply_relic_combat_modifiers(relics, player_deck, ai_deck, player_faction)

    # Ancient ZPM: +1 starting card (add extra card to player deck before Game creation)
    if relics and "ancient_zpm" in relics:
        faction_pool = [cid for cid, c in ALL_CARDS.items()
                        if getattr(c, 'faction', None) == player_faction
                        and getattr(c, 'card_type', '') != "Legendary Commander"
                        and getattr(c, 'row', '') != "weather"]
        if faction_pool:
            extra_cid = random.choice(faction_pool)
            player_deck.append(copy.deepcopy(ALL_CARDS[extra_cid]))

    # Weaken enemy passive: remove cards from AI deck
    if ai_weaken_amount and ai_weaken_amount > 0 and len(ai_deck) > 10:
        for _ in range(min(ai_weaken_amount, len(ai_deck) - 10)):
            ai_deck.pop(random.randrange(len(ai_deck)))

    # Extra player cards for defense (extra_defense_card passive)
    if extra_player_cards and extra_player_cards > 0:
        faction_pool = [cid for cid, c in ALL_CARDS.items()
                        if getattr(c, 'faction', None) == player_faction
                        and getattr(c, 'card_type', '') != "Legendary Commander"
                        and getattr(c, 'row', '') != "weather"]
        if faction_pool:
            for _ in range(extra_player_cards):
                extra_cid = random.choice(faction_pool)
                player_deck.append(copy.deepcopy(ALL_CARDS[extra_cid]))

    # Fortification defense bonus: +1 power per fort level to all player cards
    if fort_defense_bonus and fort_defense_bonus > 0:
        for card in player_deck:
            if hasattr(card, 'power') and card.power is not None:
                card.power += fort_defense_bonus

    # Validate minimum deck sizes before creating game
    MIN_DECK_SIZE = 10
    if len(player_deck) < MIN_DECK_SIZE:
        print(f"[CardBattle] WARNING: Player deck too small ({len(player_deck)} cards), aborting battle")
        return "draw"
    if len(ai_deck) < MIN_DECK_SIZE:
        print(f"[CardBattle] WARNING: AI deck too small ({len(ai_deck)} cards), defaulting to player win")
        return "player_win"

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

    # Attach conquest relics to game for in-game effects (spy blocking, weather min, etc.)
    game.conquest_relics = list(relics) if relics else []

    # Wire starting weather into game state
    if starting_weather and isinstance(starting_weather, dict):
        row = starting_weather.get("row")
        weather_type = starting_weather.get("type")
        if row and weather_type and row in game.weather_active:
            game.weather_active[row] = True
            game.current_weather_types[row] = weather_type
            game.weather_row_targets[row] = "both"
            # Apply weather effects to both players
            game.player1.weather_effects[row] = True
            game.player2.weather_effects[row] = True

    # Create AI controller
    ai_controller = AIController(game, game.player2, difficulty="hard")

    # Use main.py's game loop by passing the game object through lan_game_data
    # This reuses 100% of the existing battle code (mulligan, events, rendering, AI)
    import main as _main
    result = await _main.main(lan_game_data={
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
