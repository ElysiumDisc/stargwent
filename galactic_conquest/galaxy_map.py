"""
STARGWENT - GALACTIC CONQUEST - Galaxy Map

Procedural galaxy generation with planet graph, adjacency, and territory management.
~20 planets: 5 homeworlds, 10 faction territories, 5 neutral — connected by hyperspace lanes.
"""

import random
import math
from dataclasses import dataclass, field


# Stargate-canon planet names by faction
FACTION_PLANETS = {
    "Tau'ri": {
        "homeworld": {"name": "Earth", "weather": None},
        "territory": [
            {"name": "Antarctica", "weather": {"row": "close", "type": "ice_planet_hazard"}},
            {"name": "Tollana", "weather": {"row": "ranged", "type": "nebula_interference"}},
        ],
    },
    "Goa'uld": {
        "homeworld": {"name": "Tartarus", "weather": {"row": "close", "type": "ice_planet_hazard"}},
        "territory": [
            {"name": "Netu", "weather": {"row": "close", "type": "ice_planet_hazard"}},
            {"name": "Hasara", "weather": None},
        ],
    },
    "Jaffa Rebellion": {
        "homeworld": {"name": "Chulak", "weather": None},
        "territory": [
            {"name": "Dakara", "weather": {"row": "siege", "type": "asteroid_storm"}},
            {"name": "Hak'tyl", "weather": None},
        ],
    },
    "Lucian Alliance": {
        "homeworld": {"name": "P4C-452", "weather": {"row": "ranged", "type": "nebula_interference"}},
        "territory": [
            {"name": "Lucia", "weather": None},
            {"name": "Langara", "weather": {"row": "siege", "type": "emp"}},
        ],
    },
    "Asgard": {
        "homeworld": {"name": "Othala", "weather": {"row": "siege", "type": "emp"}},
        "territory": [
            {"name": "Orilla", "weather": {"row": "ranged", "type": "nebula_interference"}},
            {"name": "Hala", "weather": {"row": "close", "type": "ice_planet_hazard"}},
        ],
    },
}

NEUTRAL_PLANETS = [
    {"name": "Abydos", "weather": {"row": "close", "type": "ice_planet_hazard"}},
    {"name": "Vis Uban", "weather": None},
    {"name": "Atlantis", "weather": {"row": "siege", "type": "emp"}},
    {"name": "Heliopolis", "weather": None},
    {"name": "Cimmeria", "weather": {"row": "ranged", "type": "nebula_interference"}},
    {"name": "Kheb", "weather": None},
    {"name": "Proclarush", "weather": {"row": "siege", "type": "asteroid_storm"}},
    {"name": "Vagonbrei", "weather": None},
    {"name": "P3X-888", "weather": None},
]

# Faction colors for rendering
FACTION_COLORS = {
    "Tau'ri": (50, 120, 200),
    "Goa'uld": (200, 50, 50),
    "Jaffa Rebellion": (200, 180, 50),
    "Lucian Alliance": (200, 80, 180),
    "Asgard": (100, 180, 220),
    "neutral": (150, 150, 150),
    "player": (80, 220, 120),
}

ALL_FACTIONS = ["Tau'ri", "Goa'uld", "Jaffa Rebellion", "Lucian Alliance", "Asgard"]


@dataclass
class Planet:
    """A planet on the galaxy map."""
    id: str
    name: str
    planet_type: str              # "homeworld" | "territory" | "neutral"
    faction: str                  # original owning faction (or "neutral")
    owner: str                    # current controller — changes during play
    position: tuple               # (x, y) normalized 0-1 for rendering
    connections: list = field(default_factory=list)  # adjacent planet IDs
    weather_preset: dict = None   # starting weather for card battles
    defender_leader: dict = None  # leader defending this planet (set during game)
    visited: bool = False         # for neutral planets — one-time events

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "planet_type": self.planet_type,
            "faction": self.faction,
            "owner": self.owner,
            "position": list(self.position),
            "connections": list(self.connections),
            "weather_preset": self.weather_preset,
            "defender_leader": self.defender_leader,
            "visited": self.visited,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Planet":
        return cls(
            id=data["id"],
            name=data["name"],
            planet_type=data["planet_type"],
            faction=data["faction"],
            owner=data["owner"],
            position=tuple(data["position"]),
            connections=data.get("connections", []),
            weather_preset=data.get("weather_preset"),
            defender_leader=data.get("defender_leader"),
            visited=data.get("visited", False),
        )


class GalaxyMap:
    """Procedural galaxy with planets connected by hyperspace lanes."""

    def __init__(self):
        self.planets: dict[str, Planet] = {}  # id → Planet

    def generate(self, seed: int, player_faction: str,
                 friendly_faction: str = None, neutral_count: int = 5,
                 enemy_leaders: dict = None):
        """Build the galaxy map from scratch.

        Args:
            seed: Random seed for reproducible generation
            player_faction: Player's faction name
            friendly_faction: Allied faction (their territory starts as player's)
            neutral_count: Number of neutral planets (3-9)
            enemy_leaders: Dict of faction→leader_name for homeworld defenders
        """
        rng = random.Random(seed)
        self.planets.clear()

        # Position factions around a circle (like a clock face)
        faction_order = list(ALL_FACTIONS)
        # Put player faction at the bottom
        faction_order.remove(player_faction)
        rng.shuffle(faction_order)
        faction_order.insert(0, player_faction)  # player at index 0 = bottom

        # Assign angular positions for each faction's sector
        angle_step = 2 * math.pi / 5
        faction_angles = {}
        for i, faction in enumerate(faction_order):
            # Start from bottom (270° = 3π/2), go clockwise
            faction_angles[faction] = (3 * math.pi / 2) + i * angle_step

        # Place homeworlds at ~0.35 radius from center
        # Place territory planets at ~0.25 radius (between homeworld and center)
        # Place neutral planets scattered between factions
        center = (0.5, 0.5)
        homeworld_radius = 0.32
        territory_radius_inner = 0.18
        territory_radius_outer = 0.28
        neutral_radius = 0.15

        # Create faction planets
        for faction in faction_order:
            angle = faction_angles[faction]
            faction_data = FACTION_PLANETS[faction]
            faction_id = faction.lower().replace("'", "").replace(" ", "_")

            # Homeworld
            hw_data = faction_data["homeworld"]
            hw_x = center[0] + math.cos(angle) * homeworld_radius
            hw_y = center[1] + math.sin(angle) * homeworld_radius
            hw_id = f"{faction_id}_homeworld"
            is_allied = (faction == player_faction or faction == friendly_faction)
            hw = Planet(
                id=hw_id,
                name=hw_data["name"],
                planet_type="homeworld",
                faction=faction,
                owner="player" if is_allied else faction,
                position=(hw_x, hw_y),
                weather_preset=hw_data["weather"],
            )
            self.planets[hw_id] = hw

            # Territory planets (flanking the homeworld)
            for j, t_data in enumerate(faction_data["territory"]):
                offset_angle = angle + ((-1) ** j) * 0.35
                t_radius = rng.uniform(territory_radius_inner, territory_radius_outer)
                t_x = center[0] + math.cos(offset_angle) * t_radius
                t_y = center[1] + math.sin(offset_angle) * t_radius
                # Add small random jitter
                t_x += rng.uniform(-0.03, 0.03)
                t_y += rng.uniform(-0.03, 0.03)
                t_x = max(0.05, min(0.95, t_x))
                t_y = max(0.05, min(0.95, t_y))

                t_id = f"{faction_id}_territory_{j}"
                t = Planet(
                    id=t_id,
                    name=t_data["name"],
                    planet_type="territory",
                    faction=faction,
                    owner="player" if is_allied else faction,
                    position=(t_x, t_y),
                    weather_preset=t_data["weather"],
                )
                self.planets[t_id] = t

        # Neutral planets — placed near the galactic center between faction sectors
        neutral_list = NEUTRAL_PLANETS[:max(0, min(neutral_count, len(NEUTRAL_PLANETS)))]
        for i, n_data in enumerate(neutral_list):
            n_angle = (i / len(NEUTRAL_PLANETS)) * 2 * math.pi + rng.uniform(-0.3, 0.3)
            n_r = rng.uniform(0.06, neutral_radius)
            n_x = center[0] + math.cos(n_angle) * n_r
            n_y = center[1] + math.sin(n_angle) * n_r
            n_x += rng.uniform(-0.04, 0.04)
            n_y += rng.uniform(-0.04, 0.04)
            n_x = max(0.08, min(0.92, n_x))
            n_y = max(0.08, min(0.92, n_y))

            n_id = f"neutral_{i}"
            n = Planet(
                id=n_id,
                name=n_data["name"],
                planet_type="neutral",
                faction="neutral",
                owner="neutral",
                position=(n_x, n_y),
                weather_preset=n_data["weather"],
            )
            self.planets[n_id] = n

        # Build adjacency graph — connect planets based on proximity
        self._build_connections(rng)

        # Assign defender leaders to enemy faction planets
        self._assign_defenders(rng, player_faction, enemy_leaders)

    def _build_connections(self, rng):
        """Connect planets via hyperspace lanes based on proximity + rules."""
        planet_ids = list(self.planets.keys())

        # Calculate all pairwise distances
        distances = {}
        for i, pid1 in enumerate(planet_ids):
            for pid2 in planet_ids[i + 1:]:
                p1 = self.planets[pid1]
                p2 = self.planets[pid2]
                dx = p1.position[0] - p2.position[0]
                dy = p1.position[1] - p2.position[1]
                dist = math.sqrt(dx * dx + dy * dy)
                distances[(pid1, pid2)] = dist

        # Sort pairs by distance
        sorted_pairs = sorted(distances.items(), key=lambda x: x[1])

        # Connect: each planet gets 2-4 connections
        # Homeworlds connect to their territory first
        for pid, planet in self.planets.items():
            if planet.planet_type == "homeworld":
                faction_id = pid.replace("_homeworld", "")
                for j in range(2):
                    t_id = f"{faction_id}_territory_{j}"
                    if t_id in self.planets:
                        self._add_connection(pid, t_id)

        # Connect territory planets to nearest other faction's territory/neutral
        for (pid1, pid2), dist in sorted_pairs:
            p1 = self.planets[pid1]
            p2 = self.planets[pid2]

            # Skip if already connected
            if pid2 in p1.connections:
                continue

            # Both planets need < 4 connections
            if len(p1.connections) >= 4 or len(p2.connections) >= 4:
                continue

            # Connect if close enough or if either has < 2 connections
            threshold = 0.25
            if dist < threshold or len(p1.connections) < 2 or len(p2.connections) < 2:
                self._add_connection(pid1, pid2)

        # Ensure every planet has at least 1 connection
        for pid in planet_ids:
            if not self.planets[pid].connections:
                # Connect to nearest planet
                nearest = None
                nearest_dist = float("inf")
                for pid2 in planet_ids:
                    if pid2 == pid:
                        continue
                    key = (min(pid, pid2), max(pid, pid2))
                    d = distances.get(key, float("inf"))
                    if d < nearest_dist:
                        nearest_dist = d
                        nearest = pid2
                if nearest:
                    self._add_connection(pid, nearest)

        # Ensure the graph is fully connected via BFS
        self._ensure_connected(rng, distances)

    def _ensure_connected(self, rng, distances):
        """Make sure all planets are reachable from any other planet."""
        planet_ids = list(self.planets.keys())
        if not planet_ids:
            return

        visited = set()
        queue = [planet_ids[0]]
        visited.add(planet_ids[0])
        while queue:
            current = queue.pop(0)
            for neighbor in self.planets[current].connections:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

        # Connect unvisited components
        unvisited = set(planet_ids) - visited
        while unvisited:
            # Find nearest pair between visited and unvisited
            best_pair = None
            best_dist = float("inf")
            for v in visited:
                for u in unvisited:
                    key = (min(v, u), max(v, u))
                    d = distances.get(key, float("inf"))
                    if d < best_dist:
                        best_dist = d
                        best_pair = (v, u)

            if best_pair:
                self._add_connection(best_pair[0], best_pair[1])
                # BFS from newly connected node
                queue = [best_pair[1]]
                visited.add(best_pair[1])
                unvisited.discard(best_pair[1])
                while queue:
                    current = queue.pop(0)
                    for neighbor in self.planets[current].connections:
                        if neighbor not in visited:
                            visited.add(neighbor)
                            unvisited.discard(neighbor)
                            queue.append(neighbor)
            else:
                break

    def _add_connection(self, pid1: str, pid2: str):
        """Add a bidirectional connection between two planets."""
        if pid2 not in self.planets[pid1].connections:
            self.planets[pid1].connections.append(pid2)
        if pid1 not in self.planets[pid2].connections:
            self.planets[pid2].connections.append(pid1)

    def _assign_defenders(self, rng, player_faction: str, enemy_leaders: dict = None):
        """Assign leaders to each enemy planet for card battles.

        Args:
            rng: Random instance
            player_faction: Player's faction
            enemy_leaders: Optional dict of faction→leader_name for homeworld defenders
        """
        from content_registry import get_all_leaders_for_faction
        if enemy_leaders is None:
            enemy_leaders = {}
        for planet in self.planets.values():
            if planet.owner == "player" or planet.owner == "neutral":
                continue
            faction = planet.faction
            leaders = get_all_leaders_for_faction(faction)
            if not leaders:
                continue
            # Homeworlds use player-chosen leader if set
            if planet.planet_type == "homeworld" and faction in enemy_leaders:
                chosen_name = enemy_leaders[faction]
                match = [l for l in leaders if l.get("name") == chosen_name]
                if match:
                    leader = dict(match[0])
                    leader.setdefault("faction", faction)
                    planet.defender_leader = leader
                    continue
            # Random leader for territory planets and fallback
            leader = dict(rng.choice(leaders))
            leader.setdefault("faction", faction)
            planet.defender_leader = leader

    def get_attackable_planets(self, ring_platform=False) -> list[str]:
        """Get planet IDs the player can attack (adjacent to player territory).

        Args:
            ring_platform: If True, include 2-hop neighbors (Ring Platform relic).
        """
        attackable = set()
        for pid, planet in self.planets.items():
            if planet.owner != "player":
                continue
            for neighbor_id in planet.connections:
                neighbor = self.planets[neighbor_id]
                if neighbor.owner != "player":
                    attackable.add(neighbor_id)
                # Ring Platform: also check 2-hop neighbors
                if ring_platform and neighbor.owner == "player":
                    for hop2_id in neighbor.connections:
                        hop2 = self.planets[hop2_id]
                        if hop2.owner != "player":
                            attackable.add(hop2_id)
        return list(attackable)

    def get_ai_attack_targets(self, ai_faction: str) -> list[str]:
        """Get player planets adjacent to a given AI faction's territory."""
        targets = set()
        for pid, planet in self.planets.items():
            if planet.owner != ai_faction:
                continue
            for neighbor_id in planet.connections:
                neighbor = self.planets[neighbor_id]
                if neighbor.owner == "player":
                    targets.add(neighbor_id)
        return list(targets)

    def get_ai_vs_ai_targets(self, attacking_faction):
        """Get planets attackable by one AI faction against another AI faction."""
        targets = []
        for pid, planet in self.planets.items():
            if planet.owner != attacking_faction:
                continue
            for neighbor_id in planet.connections:
                neighbor = self.planets[neighbor_id]
                if (neighbor.owner not in ("player", "neutral", attacking_faction)
                        and neighbor_id not in targets):
                    targets.append(neighbor_id)
        return targets

    def get_active_factions(self):
        """Get factions that still own at least 1 planet."""
        factions = set()
        for planet in self.planets.values():
            if planet.owner not in ("player", "neutral"):
                factions.add(planet.owner)
        return factions

    def transfer_ownership(self, planet_id: str, new_owner: str):
        """Transfer a planet to a new owner."""
        if planet_id in self.planets:
            self.planets[planet_id].owner = new_owner

    def check_homeworld_accessible(self, faction: str) -> bool:
        """Check if all planets adjacent to a faction's homeworld are owned by the player."""
        for pid, planet in self.planets.items():
            if planet.faction == faction and planet.planet_type == "homeworld":
                for neighbor_id in planet.connections:
                    if self.planets[neighbor_id].owner != "player":
                        return False
                return True
        return False

    def check_win(self) -> bool:
        """Check if the player has captured all enemy homeworlds."""
        for planet in self.planets.values():
            if planet.planet_type == "homeworld" and planet.faction != "neutral":
                if planet.owner != "player":
                    return False
        return True

    def check_loss(self, player_faction: str) -> bool:
        """Check if the player's homeworld has been captured."""
        for planet in self.planets.values():
            if planet.faction == player_faction and planet.planet_type == "homeworld":
                return planet.owner != "player"
        return False

    def get_player_planet_count(self) -> int:
        """Count planets owned by the player."""
        return sum(1 for p in self.planets.values() if p.owner == "player")

    def get_faction_planet_count(self, faction: str) -> int:
        """Count planets owned by a faction."""
        return sum(1 for p in self.planets.values() if p.owner == faction)

    def to_dict(self) -> dict:
        return {
            "planets": {pid: p.to_dict() for pid, p in self.planets.items()},
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GalaxyMap":
        gm = cls()
        for pid, pdata in data.get("planets", {}).items():
            gm.planets[pid] = Planet.from_dict(pdata)
        return gm
