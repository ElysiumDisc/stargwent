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


def get_building(building_id):
    """Get a Building by ID."""
    return BUILDINGS.get(building_id)


def _get_building_cost(building, state=None):
    """Get effective building cost, applying Asgard Engineering perk + doctrine discount."""
    from .meta_progression import has_perk
    cost = building.cost
    if has_perk("building_discount"):
        cost = max(10, cost - 20)
    # Doctrine: Advanced Engineering (-25 naq)
    if state is not None:
        from .doctrines import get_active_effects
        effects = get_active_effects(state)
        cost -= effects.get("building_cost_reduction", 0)
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
    return state.naquadah >= _get_building_cost(building, state)


def construct_building(state, planet_id, building_id):
    """Build a building on a planet. Returns message or None."""
    building = BUILDINGS.get(building_id)
    if not building:
        return None
    cost = _get_building_cost(building, state)
    state.add_naquadah(-cost)
    state.buildings[planet_id] = building_id
    # Track building construction stat
    from deck_persistence import get_persistence
    p = get_persistence()
    cs = p.unlock_data.setdefault("conquest_stats", {})
    cs["buildings_constructed"] = cs.get("buildings_constructed", 0) + 1
    p.save_unlocks()
    return f"Built {building.name}! (-{cost} naq)"


def get_building_naq_income(state, galaxy):
    """Total naquadah income from Naquadah Refineries on player planets."""
    total = 0
    for pid, bid in state.buildings.items():
        if bid == "naquadah_refinery":
            planet = galaxy.planets.get(pid)
            if planet and planet.owner == "player":
                total += 10
    return total


def get_defense_bonus(state, planet_id):
    """Get defense power bonus from Training Ground on this planet."""
    if state.buildings.get(planet_id) == "training_ground":
        return 1
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
                    extra += 1
    return extra


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
    return (building.name, building.icon_char, building.description)
