"""
STARGWENT - GALACTIC CONQUEST - Victory Conditions

Six victory paths (v11.0):
  1. Domination — capture all enemy homeworlds
  2. Ascension — complete the Ascension doctrine tree + control 3 Ancient planets
  3. Galactic Alliance — achieve ALLIED status with all surviving factions
  4. Stargate Supremacy — build and hold a Supergate for 5 turns
  5. Economic (NEW) — 40%+ planets + 500 naq/turn income for 3 consecutive turns
  6. Cultural (NEW) — 4+ Ally minor worlds + 2+ relics owned

Also: Score Fallback — if no victory by turn 30, highest score wins.
"""

from .galaxy_map import ALL_FACTIONS

# Ancient planets needed for Ascension victory
ANCIENT_PLANETS = ["Atlantis", "Heliopolis", "Vis Uban", "Kheb", "Proclarush"]
ASCENSION_ANCIENT_NEEDED = 3

# Supergate turns to hold
SUPERGATE_HOLD_TURNS = 5

# Score fallback turn
SCORE_FALLBACK_TURN = 30

# Economic victory thresholds (v11.0, G5)
ECONOMIC_TERRITORY_FRACTION = 0.40
ECONOMIC_INCOME_PER_TURN = 500
ECONOMIC_CONSECUTIVE_TURNS = 3

# Cultural victory thresholds (v11.0, G5)
CULTURAL_ALLY_MINOR_WORLDS = 4
CULTURAL_RELICS_REQUIRED = 2

# Victory type display names and colors
VICTORY_INFO = {
    "domination": {
        "name": "Domination",
        "color": (255, 100, 80),
        "desc": "Capture all enemy homeworlds",
        "icon": "\u2694",
    },
    "ascension": {
        "name": "Ascension",
        "color": (200, 150, 255),
        "desc": f"Complete Ascension tree + control {ASCENSION_ANCIENT_NEEDED} Ancient planets",
        "icon": "\u2261",
    },
    "alliance": {
        "name": "Galactic Alliance",
        "color": (80, 255, 140),
        "desc": "Allied with all surviving factions",
        "icon": "\u2696",
    },
    "supremacy": {
        "name": "Stargate Supremacy",
        "color": (100, 200, 255),
        "desc": f"Build Supergate + hold {SUPERGATE_HOLD_TURNS} turns",
        "icon": "\u25CE",
    },
    "economic": {
        "name": "Economic Hegemony",
        "color": (255, 200, 80),
        "desc": f"Hold {int(ECONOMIC_TERRITORY_FRACTION*100)}%+ planets and "
                f"earn {ECONOMIC_INCOME_PER_TURN}+ naq/turn for "
                f"{ECONOMIC_CONSECUTIVE_TURNS} consecutive turns",
        "icon": "\u25C9",
    },
    "cultural": {
        "name": "Cultural Ascendancy",
        "color": (200, 140, 255),
        "desc": f"Ally with {CULTURAL_ALLY_MINOR_WORLDS}+ minor worlds and "
                f"own {CULTURAL_RELICS_REQUIRED}+ relics",
        "icon": "\u2740",
    },
    "score": {
        "name": "Score Victory",
        "color": (255, 220, 100),
        "desc": f"Highest score at turn {SCORE_FALLBACK_TURN}",
        "icon": "\u2605",
    },
}

# Score multipliers per victory type
VICTORY_SCORE_MULTIPLIERS = {
    "domination": 1.5,
    "ascension": 1.4,
    "alliance": 1.3,
    "supremacy": 1.3,
    "economic": 1.25,
    "cultural": 1.25,
    "score": 1.0,
}


def check_domination(state, galaxy):
    """Check if player captured all enemy homeworlds."""
    return galaxy.check_win()


def check_ascension(state, galaxy):
    """Check Ascension victory: completed Ascension doctrine tree + 3 Ancient planets owned."""
    if "ascension" not in getattr(state, 'completed_doctrines', []):
        return False
    ancient_owned = sum(
        1 for p in galaxy.planets.values()
        if p.name in ANCIENT_PLANETS and p.owner == "player"
    )
    return ancient_owned >= ASCENSION_ANCIENT_NEEDED


def check_alliance(state, galaxy):
    """Check Galactic Alliance: ALLIED with all surviving (non-eliminated) factions."""
    for faction in ALL_FACTIONS:
        if faction == state.player_faction:
            continue
        # Skip eliminated factions
        if galaxy.get_faction_planet_count(faction) == 0:
            continue
        rel = state.faction_relations.get(faction, "hostile")
        if rel != "allied":
            return False
    # Must have at least one surviving faction to ally with
    surviving = sum(1 for f in ALL_FACTIONS
                    if f != state.player_faction and galaxy.get_faction_planet_count(f) > 0)
    return surviving > 0


def check_supremacy(state, galaxy):
    """Check Stargate Supremacy: Supergate built + held for 5 turns."""
    sg = state.supergate_progress
    return sg.get("built", False) and sg.get("turns_held", 0) >= SUPERGATE_HOLD_TURNS


def _player_income_per_turn(state, galaxy):
    """Estimate the player's total per-turn income in naquadah.

    Sums the main income sources we already compute for other purposes:
    planet passives, buildings, neutral trade, and trade agreements. We
    intentionally skip one-shot sources (conquest bonuses, gift gains).
    """
    total = 0
    # Planet base income
    try:
        from .planet_passives import get_naquadah_per_turn
        total += get_naquadah_per_turn(state, galaxy)
    except Exception:
        pass
    # Buildings
    try:
        from .buildings import get_building_naq_income
        total += get_building_naq_income(state, galaxy)
    except Exception:
        pass
    # Trade / neutral diplomacy income
    try:
        from .diplomacy import get_trade_income, get_neutral_income, get_alliance_upkeep
        total += get_trade_income(state)
        total += get_neutral_income(state)
        total -= get_alliance_upkeep(state)
    except Exception:
        pass
    return max(0, total)


def check_economic(state, galaxy):
    """Check Economic Hegemony: sustained income dominance.

    Requires:
      - Player owns >= ECONOMIC_TERRITORY_FRACTION of all planets.
      - Player earns >= ECONOMIC_INCOME_PER_TURN per turn.
      - Both conditions held for ECONOMIC_CONSECUTIVE_TURNS turns in a row.

    The "consecutive" counter (`state.consecutive_high_income_turns`) is
    ticked by the campaign controller — see G5 end-of-turn block.
    """
    total = len(galaxy.planets)
    if total == 0:
        return False
    fraction = galaxy.get_player_planet_count() / total
    if fraction < ECONOMIC_TERRITORY_FRACTION:
        return False
    if _player_income_per_turn(state, galaxy) < ECONOMIC_INCOME_PER_TURN:
        return False
    return state.consecutive_high_income_turns >= ECONOMIC_CONSECUTIVE_TURNS


def check_cultural(state, galaxy):
    """Check Cultural Ascendancy: deep minor-world network + relic collection."""
    try:
        from .minor_worlds import MinorWorldState, INFLUENCE_TIERS
    except ImportError:
        return False
    ally_count = 0
    for pid, mw_data in state.minor_world_states.items():
        try:
            mw = MinorWorldState.from_dict(mw_data)
        except Exception:
            continue
        influence = getattr(mw, "influence", 0)
        # Ally tier threshold (60 in the current minor_worlds balance)
        if influence >= 60:
            ally_count += 1
    if ally_count < CULTURAL_ALLY_MINOR_WORLDS:
        return False
    return len(state.relics) >= CULTURAL_RELICS_REQUIRED


def check_score_fallback(state):
    """Check if score fallback triggers (turn 30+)."""
    return state.turn_number >= SCORE_FALLBACK_TURN


def tick_supergate(state, galaxy):
    """Tick supergate progress at end of turn.

    Supergate requires: 'enable_supergate' from Innovation doctrine tree completion
    + player must control 75%+ of all planets.

    Returns: message string if progress changed, else None.
    """
    sg = state.supergate_progress
    if not sg.get("built", False):
        # Check if supergate can be built
        from .doctrines import get_active_effects
        effects = get_active_effects(state)
        if effects.get("enable_supergate"):
            total = len(galaxy.planets)
            player_owned = galaxy.get_player_planet_count()
            if player_owned >= total * 0.75:
                sg["built"] = True
                sg["turns_held"] = 1
                state.supergate_progress = sg
                return "Supergate constructed! Hold for 5 turns to achieve Supremacy."
        return None

    # Already built — tick hold timer (requires maintaining 50%+ planets)
    total = len(galaxy.planets)
    player_owned = galaxy.get_player_planet_count()
    if player_owned < total * 0.50:
        sg["built"] = False
        sg["turns_held"] = 0
        state.supergate_progress = sg
        return "Supergate lost — territory dropped below 50%!"

    sg["turns_held"] = sg.get("turns_held", 0) + 1
    state.supergate_progress = sg
    remaining = SUPERGATE_HOLD_TURNS - sg["turns_held"]
    if remaining > 0:
        return f"Supergate held: {sg['turns_held']}/{SUPERGATE_HOLD_TURNS} turns."
    return None


def check_any_victory(state, galaxy):
    """Check all victory conditions.

    Returns: (victory_type, victory_name) or None.
    """
    if check_domination(state, galaxy):
        return ("domination", "Domination")
    if check_ascension(state, galaxy):
        return ("ascension", "Ascension")
    if check_alliance(state, galaxy):
        return ("alliance", "Galactic Alliance")
    if check_supremacy(state, galaxy):
        return ("supremacy", "Stargate Supremacy")
    if check_economic(state, galaxy):
        return ("economic", "Economic Hegemony")
    if check_cultural(state, galaxy):
        return ("cultural", "Cultural Ascendancy")
    if check_score_fallback(state):
        return ("score", "Score Victory")
    return None


def get_victory_progress(state, galaxy):
    """Get progress toward each victory condition.

    Returns: list of (victory_type, name, progress_str, fraction)
    """
    progress = []

    # Domination: count homeworlds captured
    total_hw = sum(1 for p in galaxy.planets.values()
                   if p.planet_type == "homeworld" and p.faction != "neutral"
                   and p.faction != state.player_faction)
    captured_hw = sum(1 for p in galaxy.planets.values()
                      if p.planet_type == "homeworld" and p.faction != "neutral"
                      and p.faction != state.player_faction and p.owner == "player")
    if total_hw > 0:
        progress.append(("domination", "Domination",
                          f"Homeworlds: {captured_hw}/{total_hw}",
                          captured_hw / total_hw))
    else:
        progress.append(("domination", "Domination", "All captured", 1.0))

    # Ascension: doctrine + ancient planets
    asc_tree = 1 if "ascension" in getattr(state, 'completed_doctrines', []) else 0
    ancient_owned = sum(1 for p in galaxy.planets.values()
                        if p.name in ANCIENT_PLANETS and p.owner == "player")
    asc_parts = asc_tree + min(ASCENSION_ANCIENT_NEEDED, ancient_owned)
    asc_total = 1 + ASCENSION_ANCIENT_NEEDED
    tree_str = "Tree: Done" if asc_tree else "Tree: No"
    progress.append(("ascension", "Ascension",
                      f"{tree_str} | Ancient: {ancient_owned}/{ASCENSION_ANCIENT_NEEDED}",
                      asc_parts / asc_total))

    # Alliance: count allied surviving factions
    surviving = []
    for f in ALL_FACTIONS:
        if f == state.player_faction:
            continue
        if galaxy.get_faction_planet_count(f) > 0:
            surviving.append(f)
    allied_count = sum(1 for f in surviving
                       if state.faction_relations.get(f) == "allied")
    total_surviving = max(1, len(surviving))
    progress.append(("alliance", "Galactic Alliance",
                      f"Allied: {allied_count}/{len(surviving)} factions",
                      allied_count / total_surviving))

    # Economic Hegemony (v11.0)
    total = len(galaxy.planets)
    if total > 0:
        fraction = galaxy.get_player_planet_count() / total
        income = _player_income_per_turn(state, galaxy)
        streak = state.consecutive_high_income_turns
        parts_done = 0
        parts_total = 3
        if fraction >= ECONOMIC_TERRITORY_FRACTION:
            parts_done += 1
        if income >= ECONOMIC_INCOME_PER_TURN:
            parts_done += 1
        if streak >= ECONOMIC_CONSECUTIVE_TURNS:
            parts_done += 1
        progress.append((
            "economic", "Economic Hegemony",
            f"Territory {int(fraction*100)}%/{int(ECONOMIC_TERRITORY_FRACTION*100)}% | "
            f"Income {income}/{ECONOMIC_INCOME_PER_TURN} | Streak {streak}/{ECONOMIC_CONSECUTIVE_TURNS}",
            parts_done / parts_total,
        ))

    # Cultural Ascendancy (v11.0)
    try:
        from .minor_worlds import MinorWorldState
        ally_count = 0
        for _pid, _mw_data in state.minor_world_states.items():
            try:
                _mw = MinorWorldState.from_dict(_mw_data)
                if getattr(_mw, "influence", 0) >= 60:
                    ally_count += 1
            except Exception:
                continue
        relic_count = len(state.relics)
        parts_done = 0
        if ally_count >= CULTURAL_ALLY_MINOR_WORLDS:
            parts_done += 1
        if relic_count >= CULTURAL_RELICS_REQUIRED:
            parts_done += 1
        progress.append((
            "cultural", "Cultural Ascendancy",
            f"Ally MW {ally_count}/{CULTURAL_ALLY_MINOR_WORLDS} | "
            f"Relics {relic_count}/{CULTURAL_RELICS_REQUIRED}",
            parts_done / 2,
        ))
    except ImportError:
        pass

    # Supremacy: supergate built + turns held
    sg = state.supergate_progress
    if sg.get("built"):
        held = sg.get("turns_held", 0)
        progress.append(("supremacy", "Stargate Supremacy",
                          f"Supergate: {held}/{SUPERGATE_HOLD_TURNS} turns",
                          min(1.0, held / SUPERGATE_HOLD_TURNS)))
    else:
        from .doctrines import get_active_effects
        effects = get_active_effects(state)
        if effects.get("enable_supergate"):
            total = len(galaxy.planets)
            player_owned = galaxy.get_player_planet_count()
            pct = int(player_owned / total * 100) if total > 0 else 0
            progress.append(("supremacy", "Stargate Supremacy",
                              f"Territory: {pct}%/75% (building)",
                              min(0.5, (player_owned / total) / 0.75 * 0.5) if total > 0 else 0))
        else:
            progress.append(("supremacy", "Stargate Supremacy",
                              "Need: Innovation tree complete",
                              0.0))

    return progress
