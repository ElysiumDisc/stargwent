"""
STARGWENT - GALACTIC CONQUEST - Planet Passives

Each owned planet grants a passive bonus to the player's campaign.
Passives are checked by the campaign controller at relevant trigger points.
"""

# Passive types:
#   naquadah_per_turn    — gain naquadah each turn
#   card_choice_bonus    — extra card choices on reward screens
#   reduce_counterattack — reduce AI counterattack chance (percentage points)
#   upgrade_on_victory   — chance to auto-upgrade a card after winning
#   extra_defense_card   — extra cards drawn when defending
#   cooldown_reduction   — reduce attack cooldown by N turns
#   weaken_enemy         — enemy starts with fewer cards in battle

PLANET_PASSIVES = {
    # Tau'ri planets
    "Earth": {
        "type": "naquadah_per_turn",
        "value": 15,
        "desc": "+15 Naquadah/turn",
    },
    "Antarctica": {
        "type": "reduce_counterattack",
        "value": 0.08,
        "desc": "-8% counterattack chance",
    },
    "Tollana": {
        "type": "card_choice_bonus",
        "value": 1,
        "desc": "+1 card choice on rewards",
    },

    # Goa'uld planets
    "Tartarus": {
        "type": "weaken_enemy",
        "value": 1,
        "desc": "Enemies start -1 card",
    },
    "Netu": {
        "type": "upgrade_on_victory",
        "value": 0.40,
        "desc": "40% chance to auto-upgrade after victory",
    },
    "Hasara": {
        "type": "cooldown_reduction",
        "value": 1,
        "desc": "-1 turn attack cooldown",
    },

    # Jaffa planets
    "Chulak": {
        "type": "naquadah_per_turn",
        "value": 10,
        "desc": "+10 Naquadah/turn",
    },
    "Dakara": {
        "type": "naquadah_per_turn",
        "value": 10,
        "desc": "+10 Naquadah/turn",
    },
    "Hak'tyl": {
        "type": "extra_defense_card",
        "value": 1,
        "desc": "+1 card when defending",
    },

    # Lucian Alliance planets
    "P4C-452": {
        "type": "naquadah_per_turn",
        "value": 20,
        "desc": "+20 Naquadah/turn",
    },
    "Lucia": {
        "type": "reduce_counterattack",
        "value": 0.05,
        "desc": "-5% counterattack chance",
    },
    "Langara": {
        "type": "card_choice_bonus",
        "value": 1,
        "desc": "+1 card choice on rewards",
    },

    # Asgard planets
    "Othala": {
        "type": "card_choice_bonus",
        "value": 1,
        "desc": "+1 card choice on rewards",
    },
    "Orilla": {
        "type": "upgrade_on_victory",
        "value": 0.35,
        "desc": "35% chance to auto-upgrade after victory",
    },
    "Hala": {
        "type": "reduce_counterattack",
        "value": 0.07,
        "desc": "-7% counterattack chance",
    },

    # Neutral planets (only active once claimed)
    "Atlantis": {
        "type": "card_choice_bonus",
        "value": 1,
        "desc": "+1 card choice on rewards",
    },
    "Abydos": {
        "type": "naquadah_per_turn",
        "value": 5,
        "desc": "+5 Naquadah/turn",
    },
    "Heliopolis": {
        "type": "upgrade_on_victory",
        "value": 0.25,
        "desc": "25% chance to auto-upgrade after victory",
    },
}


def get_planet_passive(planet_id, galaxy_map):
    """Get the passive for a specific planet, or None.

    Args:
        planet_id: Planet ID string
        galaxy_map: GalaxyMap instance

    Returns:
        Passive dict or None.
    """
    planet = galaxy_map.planets.get(planet_id)
    if planet and planet.name in PLANET_PASSIVES:
        return PLANET_PASSIVES[planet.name]
    return None


def get_active_passives(galaxy_map, allied_factions=None):
    """Get list of active passives from player-owned planets.

    If allied_factions is provided, also includes passives from allied planets
    at 50% value (only naquadah_per_turn and reduce_counterattack).

    Returns:
        List of (planet_name, passive_dict) tuples for player-owned planets,
        plus allied passives with halved values.
    """
    active = []
    for planet in galaxy_map.planets.values():
        if planet.owner == "player" and planet.name in PLANET_PASSIVES:
            active.append((planet.name, PLANET_PASSIVES[planet.name]))

    # Allied passive sharing at 50%
    if allied_factions:
        allied_set = set(allied_factions)
        shareable_types = {"naquadah_per_turn", "reduce_counterattack"}
        for planet in galaxy_map.planets.values():
            if planet.owner in allied_set and planet.name in PLANET_PASSIVES:
                passive = PLANET_PASSIVES[planet.name]
                if passive["type"] in shareable_types:
                    halved = dict(passive)
                    halved["value"] = passive["value"] * 0.5
                    active.append((planet.name, halved))
    return active


def get_total_passive(galaxy_map, passive_type, allied_factions=None):
    """Sum a specific passive type across all player-owned planets.

    Args:
        galaxy_map: GalaxyMap instance
        passive_type: One of the passive type strings
        allied_factions: Optional list of allied faction names for passive sharing

    Returns:
        Total value (int or float depending on type).
    """
    total = 0
    for _name, passive in get_active_passives(galaxy_map, allied_factions):
        if passive["type"] == passive_type:
            total += passive["value"]
    return total


def get_counterattack_reduction(galaxy_map, allied_factions=None):
    """Get total counterattack chance reduction from passives."""
    return get_total_passive(galaxy_map, "reduce_counterattack", allied_factions)


def get_naquadah_per_turn(galaxy_map, allied_factions=None):
    """Get total naquadah income per turn from passives."""
    return int(get_total_passive(galaxy_map, "naquadah_per_turn", allied_factions))


def get_card_choice_bonus(galaxy_map):
    """Get total extra card choices from passives."""
    return int(get_total_passive(galaxy_map, "card_choice_bonus"))


def get_cooldown_reduction(galaxy_map):
    """Get total cooldown reduction from passives."""
    return int(get_total_passive(galaxy_map, "cooldown_reduction"))
