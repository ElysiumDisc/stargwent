"""
STARGWENT - GALACTIC CONQUEST - Diplomacy System

Faction relations: HOSTILE → NEUTRAL → TRADING → ALLIED
Trade, Alliance, and Betrayal mechanics.
"""

import random

# Relation levels (ordered by friendliness)
HOSTILE = "hostile"
NEUTRAL_REL = "neutral"
TRADING = "trading"
ALLIED = "allied"

RELATION_ORDER = [HOSTILE, NEUTRAL_REL, TRADING, ALLIED]

RELATION_DISPLAY = {
    HOSTILE: {"name": "Hostile", "color": (255, 80, 80)},
    NEUTRAL_REL: {"name": "Neutral", "color": (180, 180, 180)},
    TRADING: {"name": "Trading", "color": (100, 220, 255)},
    ALLIED: {"name": "Allied", "color": (80, 255, 140)},
}

# Costs
TRADE_COST = 50
ALLIANCE_COST = 100
BETRAY_REWARD = 80


def get_relation(state, faction):
    """Get current relation with a faction."""
    return state.faction_relations.get(faction, HOSTILE)


def set_relation(state, faction, relation):
    """Set relation with a faction."""
    state.faction_relations[faction] = relation


def init_relations(state, friendly_faction=None):
    """Initialize faction relations for a new campaign."""
    from .galaxy_map import ALL_FACTIONS
    for faction in ALL_FACTIONS:
        if faction == state.player_faction:
            continue
        if faction == friendly_faction:
            state.faction_relations[faction] = ALLIED
        else:
            state.faction_relations[faction] = HOSTILE


def can_trade(state, faction, galaxy):
    """Check if player can propose trade with a faction."""
    rel = get_relation(state, faction)
    if rel in (TRADING, ALLIED):
        return False  # Already friendly
    if rel == HOSTILE:
        # Can only trade if faction has adjacent player territory
        return _has_shared_border(state, faction, galaxy) and state.naquadah >= TRADE_COST
    return state.naquadah >= TRADE_COST


def can_ally(state, faction, galaxy):
    """Check if player can form alliance."""
    rel = get_relation(state, faction)
    if rel != TRADING:
        return False  # Must be trading first
    return state.naquadah >= ALLIANCE_COST


def can_betray(state, faction):
    """Check if player can betray an ally."""
    return get_relation(state, faction) == ALLIED


def propose_trade(state, faction, galaxy):
    """Propose trade agreement. Returns success message or None."""
    if not can_trade(state, faction, galaxy):
        return None
    state.add_naquadah(-TRADE_COST)
    set_relation(state, faction, TRADING)
    return f"Trade agreement with {faction}! They will not counterattack."


def form_alliance(state, faction, galaxy):
    """Form alliance. Returns success message or None."""
    if not can_ally(state, faction, galaxy):
        return None
    state.add_naquadah(-ALLIANCE_COST)
    set_relation(state, faction, ALLIED)
    return f"Alliance formed with {faction}! Their territory counts as yours for adjacency."


def betray_alliance(state, faction):
    """Break alliance for immediate reward. Returns message."""
    if not can_betray(state, faction):
        return None
    state.add_naquadah(BETRAY_REWARD)
    set_relation(state, faction, HOSTILE)
    # Permanent hostility boost
    state.conquest_ability_data[f"betrayed_{faction}"] = True
    return f"Betrayed {faction}! +{BETRAY_REWARD} naq. They are now permanently hostile (+15% counterattack)."


def get_betrayal_counter_bonus(state, faction):
    """Get extra counterattack chance from betrayal."""
    if state.conquest_ability_data.get(f"betrayed_{faction}"):
        return 0.15
    return 0.0


def check_ai_trade_proposals(state, galaxy, rng):
    """Check if weakened AI factions propose trades.

    Returns list of (faction, message) proposals.
    """
    proposals = []
    for faction in galaxy.get_active_factions():
        if faction == state.player_faction:
            continue
        rel = get_relation(state, faction)
        if rel != HOSTILE:
            continue
        planet_count = galaxy.get_faction_planet_count(faction)
        if planet_count <= 2 and rng.random() < 0.30:
            proposals.append((faction, f"{faction} offers a trade agreement (they're weakened)."))
    return proposals


def is_faction_friendly(state, faction):
    """Check if a faction is trading or allied (won't counterattack)."""
    rel = get_relation(state, faction)
    return rel in (TRADING, ALLIED)


def get_adjacency_bonus_factions(state):
    """Get factions whose territory counts as player's for adjacency (allied)."""
    return [f for f, rel in state.faction_relations.items() if rel == ALLIED]


def _has_shared_border(state, faction, galaxy):
    """Check if player and faction share a border."""
    for pid, planet in galaxy.planets.items():
        if planet.owner == "player":
            for neighbor_id in planet.connections:
                neighbor = galaxy.planets.get(neighbor_id)
                if neighbor and neighbor.owner == faction:
                    return True
    return False


def get_diplomacy_options(state, galaxy):
    """Get available diplomatic actions for each faction.

    Returns: list of (faction, available_actions) where actions is list of
    (action_name, cost_or_reward, enabled, description)
    """
    options = []
    from .galaxy_map import ALL_FACTIONS
    for faction in ALL_FACTIONS:
        if faction == state.player_faction:
            continue
        # Skip eliminated factions
        if galaxy.get_faction_planet_count(faction) == 0:
            continue
        rel = get_relation(state, faction)
        actions = []
        if rel == HOSTILE:
            actions.append(("trade", TRADE_COST, can_trade(state, faction, galaxy),
                            f"Propose trade (-{TRADE_COST} naq): stop counterattacks"))
        elif rel == TRADING:
            actions.append(("alliance", ALLIANCE_COST, can_ally(state, faction, galaxy),
                            f"Form alliance (-{ALLIANCE_COST} naq): shared adjacency"))
        elif rel == ALLIED:
            actions.append(("betray", -BETRAY_REWARD, True,
                            f"Betray (+{BETRAY_REWARD} naq): permanently hostile"))
        options.append((faction, rel, actions))
    return options
