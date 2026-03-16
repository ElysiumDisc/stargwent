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


def _get_effective_trade_cost(state):
    """Get trade cost after doctrine/minor world discounts."""
    cost = TRADE_COST
    # Doctrine: Free Trade Zone (-20 naq)
    from .doctrines import get_active_effects
    effects = get_active_effects(state)
    cost -= effects.get("trade_cost_discount", 0)
    # Minor world: diplomatic friend/ally (-15 naq)
    from .minor_worlds import get_minor_world_bonuses
    mw_bonuses = get_minor_world_bonuses(state, None)  # galaxy not needed for trade discount
    cost -= mw_bonuses.get("trade_cost_discount", 0)
    return max(10, cost)


def can_trade(state, faction, galaxy):
    """Check if player can propose trade with a faction."""
    rel = get_relation(state, faction)
    if rel in (TRADING, ALLIED):
        return False  # Already friendly
    cost = _get_effective_trade_cost(state)
    if rel == HOSTILE:
        return _has_shared_border(state, faction, galaxy) and state.naquadah >= cost
    return state.naquadah >= cost


def can_ally(state, faction, galaxy):
    """Check if player can form alliance."""
    rel = get_relation(state, faction)
    if rel != TRADING:
        return False  # Must be trading first
    return state.naquadah >= ALLIANCE_COST


def can_betray(state, faction):
    """Check if player can betray an ally."""
    return get_relation(state, faction) == ALLIED


def _track_conquest_stat(key, increment=1):
    """Increment a conquest stat counter."""
    from deck_persistence import get_persistence
    p = get_persistence()
    cs = p.unlock_data.setdefault("conquest_stats", {})
    cs[key] = cs.get(key, 0) + increment
    p.save_unlocks()


def propose_trade(state, faction, galaxy):
    """Propose trade agreement. Returns success message or None."""
    if not can_trade(state, faction, galaxy):
        return None
    cost = _get_effective_trade_cost(state)
    state.add_naquadah(-cost)
    set_relation(state, faction, TRADING)
    _track_conquest_stat("trades_made")
    # Minor world quest: trade event
    from .minor_worlds import notify_quest_event
    notify_quest_event(state, "trade")
    return f"Trade agreement with {faction}! They will not counterattack."


def form_alliance(state, faction, galaxy):
    """Form alliance. Returns success message or None."""
    if not can_ally(state, faction, galaxy):
        return None
    state.add_naquadah(-ALLIANCE_COST)
    set_relation(state, faction, ALLIED)
    _track_conquest_stat("alliances_forged")
    return f"Alliance formed with {faction}! Their territory counts as yours for adjacency."


def betray_alliance(state, faction, rng=None):
    """Break alliance for immediate reward. Returns message.

    Ripple effect: 40% chance each TRADING partner also turns HOSTILE.
    """
    if not can_betray(state, faction):
        return None
    state.add_naquadah(BETRAY_REWARD)
    set_relation(state, faction, HOSTILE)
    # Permanent hostility boost
    state.conquest_ability_data[f"betrayed_{faction}"] = True
    _track_conquest_stat("betrayals")
    msg = f"Betrayed {faction}! +{BETRAY_REWARD} naq. Permanently hostile (+15% counterattack)."

    # Ripple effect: other trading partners may turn hostile
    if rng is None:
        rng = random.Random()
    for other, rel in list(state.faction_relations.items()):
        if other == faction:
            continue
        if rel == TRADING and rng.random() < 0.40:
            set_relation(state, other, HOSTILE)
            msg += f" {other} lost trust — now Hostile!"
    return msg


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


def generate_ai_proposals(state, galaxy, rng):
    """Generate AI diplomatic proposals at turn start.

    Returns list of proposal dicts:
    {type, faction, description, accept_label, reject_label, accept_fn_key, reject_fn_key}
    """
    proposals = []
    for faction in galaxy.get_active_factions():
        if faction == state.player_faction:
            continue
        rel = get_relation(state, faction)
        planet_count = galaxy.get_faction_planet_count(faction)

        if rel == HOSTILE:
            # Trade offer from weakened faction
            if planet_count <= 3 and rng.random() < 0.25:
                proposals.append({
                    "type": "trade_offer",
                    "faction": faction,
                    "description": f"{faction} offers a trade agreement and a 20 naquadah signing bonus.",
                    "accept_label": "Accept Trade",
                    "reject_label": "Decline",
                })
            # Ceasefire from very weak faction
            elif planet_count <= 2 and rng.random() < 0.20:
                proposals.append({
                    "type": "ceasefire",
                    "faction": faction,
                    "description": f"{faction} requests a ceasefire. They will stop counterattacking.",
                    "accept_label": "Accept Ceasefire",
                    "reject_label": "Refuse",
                })
            # Tribute demand from strong faction
            elif planet_count >= 6 and rng.random() < 0.15:
                proposals.append({
                    "type": "tribute_demand",
                    "faction": faction,
                    "description": f"{faction} demands 40 naquadah tribute — or face increased aggression.",
                    "accept_label": "Pay Tribute (-40 naq)",
                    "reject_label": "Refuse",
                })

        elif rel == TRADING:
            # Joint attack proposal
            # Find mutual enemy (hostile to player AND borders this trading partner)
            mutual_enemies = []
            for other_faction in galaxy.get_active_factions():
                if other_faction == state.player_faction or other_faction == faction:
                    continue
                if get_relation(state, other_faction) == HOSTILE:
                    if _has_shared_border(state, other_faction, galaxy):
                        mutual_enemies.append(other_faction)
            if mutual_enemies and rng.random() < 0.15:
                target = rng.choice(mutual_enemies)
                proposals.append({
                    "type": "joint_attack",
                    "faction": faction,
                    "target": target,
                    "description": f"{faction} proposes a joint offensive against {target}. Accept for -1 attack cooldown vs {target}.",
                    "accept_label": "Coordinate Attack",
                    "reject_label": "Decline",
                })

    return proposals


def apply_proposal(state, proposal, accepted, galaxy, rng):
    """Apply the result of an AI diplomatic proposal.

    Returns result message string.
    """
    p_type = proposal["type"]
    faction = proposal["faction"]

    if p_type == "trade_offer":
        if accepted:
            set_relation(state, faction, TRADING)
            state.add_naquadah(20)
            _track_conquest_stat("ai_trades_accepted")
            return f"Trade with {faction}! +20 naq signing bonus."
        return f"Declined {faction}'s trade offer."

    elif p_type == "ceasefire":
        if accepted:
            set_relation(state, faction, NEUTRAL_REL)
            _track_conquest_stat("ceasefires_accepted")
            return f"Ceasefire with {faction}. They won't counterattack."
        return f"Refused {faction}'s ceasefire."

    elif p_type == "tribute_demand":
        if accepted:
            state.add_naquadah(-40)
            return f"Paid 40 naquadah tribute to {faction}."
        else:
            # Store rejection: +10% counterattack for 3 turns
            key = f"tribute_rejected_{faction}"
            state.conquest_ability_data[key] = 3
            return f"Refused {faction}'s demand! They're +10% more aggressive for 3 turns."

    elif p_type == "joint_attack":
        if accepted:
            target = proposal.get("target", "unknown")
            key = f"joint_attack_cooldown_{target}"
            state.conquest_ability_data[key] = 1  # -1 cooldown on next attack
            return f"Joint offensive with {faction} against {target}! -1 cooldown on next attack."
        else:
            # Small chance of relation downgrade
            if rng.random() < 0.10:
                set_relation(state, faction, HOSTILE)
                return f"Declined {faction}'s joint attack. They feel slighted — now Hostile!"
            return f"Declined {faction}'s joint attack proposal."

    return ""


def get_tribute_reject_bonus(state, faction):
    """Get extra counterattack chance from tribute rejection (0.10 if active, else 0.0)."""
    key = f"tribute_rejected_{faction}"
    if state.conquest_ability_data.get(key, 0) > 0:
        return 0.10
    return 0.0


def tick_tribute_rejections(state):
    """Decrement tribute rejection timers each turn."""
    keys_to_remove = []
    for key in list(state.conquest_ability_data):
        if key.startswith("tribute_rejected_"):
            state.conquest_ability_data[key] -= 1
            if state.conquest_ability_data[key] <= 0:
                keys_to_remove.append(key)
    for key in keys_to_remove:
        del state.conquest_ability_data[key]


def check_potential_strain(state, planet_id, galaxy):
    """Check if attacking a planet might strain an alliance.

    Returns warning string or None.
    """
    planet = galaxy.planets.get(planet_id)
    if not planet:
        return None
    allied_factions = get_adjacency_bonus_factions(state)
    if not allied_factions:
        return None
    for neighbor_id in planet.connections:
        neighbor = galaxy.planets.get(neighbor_id)
        if neighbor and neighbor.owner in allied_factions:
            return (f"Attacking {planet.name} may strain your alliance "
                    f"with {neighbor.owner} (30% chance of downgrade).")
    return None


def is_faction_friendly(state, faction):
    """Check if a faction is trading or allied (won't counterattack)."""
    rel = get_relation(state, faction)
    return rel in (TRADING, ALLIED)


def get_adjacency_bonus_factions(state):
    """Get factions whose territory counts as player's for adjacency (allied)."""
    return [f for f, rel in state.faction_relations.items() if rel == ALLIED]


def get_trade_income(state):
    """Get naquadah income per turn from trading partners (+5 per partner)."""
    count = sum(1 for rel in state.faction_relations.values() if rel == TRADING)
    return 5 * count


def get_alliance_upkeep(state):
    """Get naquadah upkeep per turn from alliances (-10 per ally)."""
    count = sum(1 for rel in state.faction_relations.values() if rel == ALLIED)
    return 10 * count


def check_conquest_strain(state, conquered_planet, galaxy, rng):
    """Check if conquering near an ally causes diplomatic strain.

    30% chance to downgrade alliance to trading if conquered planet
    is adjacent to allied faction territory.

    Returns: warning message string if strain occurred, else None.
    """
    allied_factions = get_adjacency_bonus_factions(state)
    if not allied_factions:
        return None

    for neighbor_id in conquered_planet.connections:
        neighbor = galaxy.planets.get(neighbor_id)
        if not neighbor:
            continue
        if neighbor.owner in allied_factions:
            strained_faction = neighbor.owner
            if rng.random() < 0.30:
                set_relation(state, strained_faction, TRADING)
                _track_conquest_stat("alliances_strained")
                return (f"{strained_faction} feels threatened by your expansion! "
                        f"Alliance downgraded to Trading.")
    return None


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
            eff_cost = _get_effective_trade_cost(state)
            actions.append(("trade", eff_cost, can_trade(state, faction, galaxy),
                            f"Propose trade (-{eff_cost} naq): +5 naq/turn, card pool access"))
        elif rel == TRADING:
            actions.append(("alliance", ALLIANCE_COST, can_ally(state, faction, galaxy),
                            f"Form alliance (-{ALLIANCE_COST} naq): network bridge, 50% passives, -10 upkeep"))
        elif rel == ALLIED:
            actions.append(("betray", -BETRAY_REWARD, True,
                            f"Betray (+{BETRAY_REWARD} naq): permanently hostile, trust ripple"))
        options.append((faction, rel, actions))
    return options
