"""
STARGWENT - GALACTIC CONQUEST - Stargate Network System

Connected player planets (BFS from homeworld through owned territory) determine
network tier. Rewards contiguous expansion along hyperspace lanes.
"""

from collections import deque


# Network tier definitions
NETWORK_TIERS = {
    1: {"name": "Outpost",   "min_planets": 1,  "naq_bonus": 0,  "counterattack_reduction": 0.0,
        "ability_level": 1, "card_choice_bonus": 0, "fortify_cost": 60, "two_hop_attacks": False},
    2: {"name": "Regional",  "min_planets": 4,  "naq_bonus": 5,  "counterattack_reduction": 0.0,
        "ability_level": 2, "card_choice_bonus": 0, "fortify_cost": 60, "two_hop_attacks": False},
    3: {"name": "Sector",    "min_planets": 7,  "naq_bonus": 10, "counterattack_reduction": 0.05,
        "ability_level": 3, "card_choice_bonus": 0, "fortify_cost": 60, "two_hop_attacks": True},
    4: {"name": "Quadrant",  "min_planets": 11, "naq_bonus": 15, "counterattack_reduction": 0.10,
        "ability_level": 4, "card_choice_bonus": 0, "fortify_cost": 40, "two_hop_attacks": True},
    5: {"name": "Galactic",  "min_planets": 15, "naq_bonus": 20, "counterattack_reduction": 0.10,
        "ability_level": 4, "card_choice_bonus": 1, "fortify_cost": 40, "two_hop_attacks": True},
}


def get_connected_planet_count(galaxy_map, player_faction, allied_factions=None):
    """BFS from player homeworld through player-owned planets.

    Allied faction planets act as bridges (traversable but not counted).

    Returns the number of player planets connected to the homeworld.
    Disconnected player planets don't count toward the network.
    """
    # Find player homeworld
    homeworld_id = None
    for pid, planet in galaxy_map.planets.items():
        if planet.faction == player_faction and planet.planet_type == "homeworld":
            if planet.owner == "player":
                homeworld_id = pid
            break

    if homeworld_id is None:
        return 0

    allied = set(allied_factions) if allied_factions else set()

    # BFS through player-owned and allied planets
    visited = set()
    queue = deque([homeworld_id])
    visited.add(homeworld_id)

    while queue:
        current = queue.popleft()
        for neighbor_id in galaxy_map.planets[current].connections:
            if neighbor_id in visited:
                continue
            neighbor = galaxy_map.planets.get(neighbor_id)
            if not neighbor:
                continue
            if neighbor.owner == "player" or neighbor.owner in allied:
                visited.add(neighbor_id)
                queue.append(neighbor_id)

    # Only count player-owned planets (allied are bridges only)
    return sum(1 for pid in visited
               if galaxy_map.planets[pid].owner == "player")


def get_disconnected_planets(galaxy_map, player_faction, allied_factions=None):
    """Return set of player-owned planet IDs NOT connected to homeworld.

    Allied faction planets act as bridges for connectivity.
    """
    homeworld_id = None
    for pid, planet in galaxy_map.planets.items():
        if planet.faction == player_faction and planet.planet_type == "homeworld":
            if planet.owner == "player":
                homeworld_id = pid
            break

    if homeworld_id is None:
        return set(pid for pid, p in galaxy_map.planets.items() if p.owner == "player")

    allied = set(allied_factions) if allied_factions else set()

    visited = set()
    queue = deque([homeworld_id])
    visited.add(homeworld_id)
    while queue:
        current = queue.popleft()
        for neighbor_id in galaxy_map.planets[current].connections:
            if neighbor_id in visited:
                continue
            neighbor = galaxy_map.planets.get(neighbor_id)
            if not neighbor:
                continue
            if neighbor.owner == "player" or neighbor.owner in allied:
                visited.add(neighbor_id)
                queue.append(neighbor_id)

    # Only player-owned planets count for disconnection check
    all_player = set(pid for pid, p in galaxy_map.planets.items() if p.owner == "player")
    connected_player = set(pid for pid in visited if galaxy_map.planets[pid].owner == "player")
    return all_player - connected_player


def calculate_network_tier(galaxy_map, player_faction, allied_factions=None):
    """Calculate the current Stargate Network tier based on connected planets.

    Returns:
        (tier_number, tier_data_dict)
    """
    connected = get_connected_planet_count(galaxy_map, player_faction, allied_factions)

    best_tier = 1
    for tier_num in sorted(NETWORK_TIERS.keys()):
        if connected >= NETWORK_TIERS[tier_num]["min_planets"]:
            best_tier = tier_num

    return best_tier, NETWORK_TIERS[best_tier]


def get_network_bonuses(galaxy_map, player_faction, allied_factions=None):
    """Get all active network bonuses.

    Returns:
        dict with keys: tier, name, naq_bonus, counterattack_reduction,
        ability_level, card_choice_bonus, fortify_cost, two_hop_attacks
    """
    tier, data = calculate_network_tier(galaxy_map, player_faction, allied_factions)
    return {
        "tier": tier,
        "name": data["name"],
        "naq_bonus": data["naq_bonus"],
        "counterattack_reduction": data["counterattack_reduction"],
        "ability_level": data["ability_level"],
        "card_choice_bonus": data["card_choice_bonus"],
        "fortify_cost": data["fortify_cost"],
        "two_hop_attacks": data["two_hop_attacks"],
    }
