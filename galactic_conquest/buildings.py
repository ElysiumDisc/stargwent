"""
STARGWENT - GALACTIC CONQUEST - Planet Buildings

Each planet can have 1 building (plus fortification).
Buildings provide local bonuses when owned.
"""

from dataclasses import dataclass


@dataclass
class Building:
    """A constructible improvement on a planet."""
    id: str
    name: str
    description: str
    cost: int
    icon_char: str


BUILDINGS = {
    "naquadah_refinery": Building(
        id="naquadah_refinery",
        name="Naquadah Refinery",
        description="+10 naquadah per turn from this planet",
        cost=80,
        icon_char="\u2622",  # radioactive
    ),
    "training_ground": Building(
        id="training_ground",
        name="Training Ground",
        description="+1 power to all cards when defending this planet",
        cost=60,
        icon_char="\u2694",  # swords
    ),
    "shipyard": Building(
        id="shipyard",
        name="Shipyard",
        description="+1 card when attacking FROM this planet's neighbors",
        cost=100,
        icon_char="\u2693",  # anchor
    ),
    "sensor_array": Building(
        id="sensor_array",
        name="Sensor Array",
        description="Reveal enemy deck size when attacking neighbors",
        cost=40,
        icon_char="\u25CE",  # bullseye
    ),
    "shield_generator": Building(
        id="shield_generator",
        name="Shield Generator",
        description="Fortify cost -20 for this planet",
        cost=50,
        icon_char="\u26E8",  # shield
    ),
}

# Level-scaled effects per building type
BUILDING_LEVEL_EFFECTS = {
    "naquadah_refinery": {1: 10, 2: 18, 3: 25},    # naq/turn
    "training_ground":   {1: 1,  2: 2,  3: 3},      # defense power bonus
    "shipyard":          {1: 1,  2: 1,  3: 2},      # extra cards when attacking from neighbors
    "sensor_array":      {1: 1,  2: 2,  3: 3},      # info tiers
    "shield_generator":  {1: 20, 2: 30, 3: 40},     # fortify cost discount
}

UPGRADE_COST_MULTIPLIERS = {2: 1.5, 3: 2.0}


def get_building(building_id):
    """Get a Building by ID."""
    return BUILDINGS.get(building_id)


def _get_building_cost(building, state=None, planet_id=None, galaxy=None):
    """Get effective building cost, applying Asgard Engineering perk + doctrine + trading discount."""
    from .meta_progression import has_perk
    cost = building.cost
    if has_perk("building_discount"):
        cost = max(10, cost - 20)
    # Doctrine: Advanced Engineering (-25 naq)
    if state is not None:
        from .doctrines import get_active_effects
        effects = get_active_effects(state)
        cost -= effects.get("building_cost_reduction", 0)
    # Trading partner adjacency discount (-10 naq)
    if state is not None and planet_id is not None and galaxy is not None:
        from .diplomacy import get_trading_building_discount
        cost -= get_trading_building_discount(state, planet_id, galaxy)
    return max(10, cost)


def can_build(state, planet_id, building_id, galaxy):
    """Check if player can construct a building on a planet."""
    planet = galaxy.planets.get(planet_id)
    if not planet or planet.owner != "player":
        return False
    # Already has a building
    if state.buildings.get(planet_id):
        return False
    building = BUILDINGS.get(building_id)
    if not building:
        return False
    return state.naquadah >= _get_building_cost(building, state, planet_id, galaxy)


def construct_building(state, planet_id, building_id, galaxy=None):
    """Build a building on a planet. Returns message or None.

    Defensive: re-checks funds and existing building even though callers
    should call can_build() first. Prevents silent state corruption if a
    caller skips the check (e.g. from a stale UI state).
    """
    building = BUILDINGS.get(building_id)
    if not building:
        return None
    if state.buildings.get(planet_id):
        return None
    cost = _get_building_cost(building, state, planet_id, galaxy)
    if state.naquadah < cost:
        return None
    state.add_naquadah(-cost)
    state.buildings[planet_id] = building_id
    # Track building construction stat
    from deck_persistence import get_persistence
    p = get_persistence()
    cs = p.unlock_data.setdefault("conquest_stats", {})
    cs["buildings_constructed"] = cs.get("buildings_constructed", 0) + 1
    p.save_unlocks()
    return f"Built {building.name}! (-{cost} naq)"


def get_building_level(state, planet_id):
    """Get current building level (1-3). Defaults to 1 for existing buildings."""
    return max(1, min(3, state.building_levels.get(planet_id, 1)))


def get_upgrade_cost(state, planet_id):
    """Get cost to upgrade building to next level. Returns None if maxed or no building."""
    bid = state.buildings.get(planet_id)
    if not bid:
        return None
    building = BUILDINGS.get(bid)
    if not building:
        return None
    level = get_building_level(state, planet_id)
    if level >= 3:
        return None
    next_level = level + 1
    base_cost = _get_building_cost(building, state)
    return max(10, int(base_cost * UPGRADE_COST_MULTIPLIERS[next_level]))


def can_upgrade(state, planet_id, galaxy):
    """Check if player can upgrade the building on a planet."""
    planet = galaxy.planets.get(planet_id)
    if not planet or planet.owner != "player":
        return False
    cost = get_upgrade_cost(state, planet_id)
    if cost is None:
        return False
    return state.naquadah >= cost


def upgrade_building(state, planet_id):
    """Upgrade building to next level. Returns message or None."""
    cost = get_upgrade_cost(state, planet_id)
    if cost is None:
        return None
    bid = state.buildings.get(planet_id)
    building = BUILDINGS.get(bid)
    if not building:
        return None
    state.add_naquadah(-cost)
    new_level = get_building_level(state, planet_id) + 1
    state.building_levels[planet_id] = new_level
    from deck_persistence import get_persistence
    p = get_persistence()
    cs = p.unlock_data.setdefault("conquest_stats", {})
    cs["buildings_upgraded"] = cs.get("buildings_upgraded", 0) + 1
    p.save_unlocks()
    return f"Upgraded {building.name} to Lv{new_level}! (-{cost} naq)"


def get_building_naq_income(state, galaxy):
    """Total naquadah income from Naquadah Refineries on player planets."""
    total = 0
    for pid, bid in state.buildings.items():
        if bid == "naquadah_refinery":
            planet = galaxy.planets.get(pid)
            if planet and planet.owner == "player":
                total += BUILDING_LEVEL_EFFECTS["naquadah_refinery"][get_building_level(state, pid)]
    return total


def get_defense_bonus(state, planet_id):
    """Get defense power bonus from Training Ground on this planet."""
    if state.buildings.get(planet_id) == "training_ground":
        return BUILDING_LEVEL_EFFECTS["training_ground"][get_building_level(state, planet_id)]
    return 0


def get_attack_extra_cards(state, planet_id, galaxy):
    """Get extra cards when attacking, based on Shipyard on adjacent player planets."""
    extra = 0
    planet = galaxy.planets.get(planet_id)
    if planet:
        for neighbor_id in planet.connections:
            neighbor = galaxy.planets.get(neighbor_id)
            if neighbor and neighbor.owner == "player":
                if state.buildings.get(neighbor_id) == "shipyard":
                    extra += BUILDING_LEVEL_EFFECTS["shipyard"][get_building_level(state, neighbor_id)]
    return extra


# --- Building Synergies: connected planet combos grant bonuses ---

BUILDING_SYNERGIES = {
    "prometheus_protocol": {
        "name": "Prometheus Protocol",
        "buildings": ("shipyard", "training_ground"),
        "description": "+1 attack power from connected Shipyard + Training Ground",
        "effect": {"attack_power_bonus": 1},
    },
    "deep_space_telemetry": {
        "name": "Deep Space Telemetry",
        "buildings": ("sensor_array", "sensor_array"),
        "description": "Two Sensor Arrays reveal full enemy deck",
        "effect": {"full_deck_reveal": True},
    },
    "naquadria_cascade": {
        "name": "Naquadria Cascade",
        "buildings": ("naquadah_refinery", "shield_generator"),
        "description": "Connected Refinery + Shield boosts refinery income +50%",
        "effect": {"refinery_income_bonus": 0.50},
    },
    "integrated_defense_grid": {
        "name": "Integrated Defense Grid",
        "buildings": ("shield_generator", "training_ground"),
        "description": "Connected shields + training grants +1 fortification",
        "effect": {"fortify_bonus": 1},
    },
}


def get_active_synergies(state, galaxy):
    """Check which building synergies are active across the player's network.

    Returns list of active synergy dicts.
    """
    active = []
    player_buildings = {}
    for pid, bid in state.buildings.items():
        planet = galaxy.planets.get(pid)
        if planet and planet.owner == "player":
            player_buildings[pid] = bid

    for syn_id, synergy in BUILDING_SYNERGIES.items():
        b1, b2 = synergy["buildings"]
        if b1 == b2:
            # Same building type: need 2+ on connected planets
            pids_with = [pid for pid, bid in player_buildings.items() if bid == b1]
            if len(pids_with) >= 2:
                # Check if any pair is connected
                for i, p1 in enumerate(pids_with):
                    for p2 in pids_with[i + 1:]:
                        planet1 = galaxy.planets.get(p1)
                        if planet1 and p2 in planet1.connections:
                            active.append(synergy)
                            break
                    else:
                        continue
                    break
        else:
            # Different buildings: need them on connected planets
            pids_b1 = [pid for pid, bid in player_buildings.items() if bid == b1]
            pids_b2 = [pid for pid, bid in player_buildings.items() if bid == b2]
            found = False
            for p1 in pids_b1:
                planet1 = galaxy.planets.get(p1)
                if planet1:
                    for p2 in pids_b2:
                        if p2 in planet1.connections:
                            found = True
                            break
                if found:
                    break
            if found:
                active.append(synergy)
    return active


def get_synergy_effects(state, galaxy):
    """Aggregate all active building synergy effects into a single dict."""
    effects = {}
    for synergy in get_active_synergies(state, galaxy):
        for key, val in synergy["effect"].items():
            if isinstance(val, bool):
                effects[key] = True
            elif isinstance(val, (int, float)):
                effects[key] = effects.get(key, 0) + val
            else:
                effects[key] = val
    return effects


def get_planet_building_display(state, planet_id):
    """Get display info for a planet's building.

    Returns (name, icon_char, description) or None.
    """
    bid = state.buildings.get(planet_id)
    if not bid:
        return None
    building = BUILDINGS.get(bid)
    if not building:
        return None
    level = get_building_level(state, planet_id)
    name = f"{building.name} Lv{level}"
    effects = BUILDING_LEVEL_EFFECTS.get(bid)
    if effects:
        val = effects[level]
        descs = {
            "naquadah_refinery": f"+{val} naquadah per turn from this planet",
            "training_ground": f"+{val} power to all cards when defending this planet",
            "shipyard": f"+{val} card{'s' if val > 1 else ''} when attacking FROM this planet's neighbors",
            "sensor_array": f"Reveal enemy info (tier {val}) when attacking neighbors",
            "shield_generator": f"Fortify cost -{val} for this planet",
        }
        desc = descs.get(bid, building.description)
    else:
        desc = building.description
    return (name, building.icon_char, desc)
