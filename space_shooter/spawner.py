"""Continuous enemy spawner for infinite survival mode.

Replaces the wave system with time-based difficulty scaling.
Starts very easy and slowly ramps up, giving the player time to
become powerful through upgrades before things get intense.
"""

import random
import math

from .ship import Ship
from .upgrades import ENEMY_TYPES


# Difficulty schedule: (time_seconds, label, spawn_interval_frames, max_alive,
#                       enemy_types, hp_mult, speed_mult, elite_chance, boss_interval_s)
# Designed so the first few minutes are relaxed — player can farm XP and upgrades.
DIFFICULTY_TIERS = [
    # time_s  label              interval  max   types                              hp    spd   elite  boss_interval
    (0,       "Calm",            240,      6,    ["regular"],                        0.7,  0.6,  0.00,  None),
    (30,      "Warming Up",      180,      8,    ["regular"],                        0.8,  0.65, 0.00,  None),
    (60,      "Skirmish",        140,      10,   ["regular", "fast"],                0.9,  0.7,  0.00,  None),
    (120,     "Engaged",         110,      14,   ["regular", "fast", "kamikaze"],    1.0,  0.8,  0.00,  600),
    (180,     "Contested",       90,       18,   ["regular", "fast", "kamikaze"],    1.1,  0.85, 0.05,  600),
    (300,     "Intense",         70,       24,   ["regular", "fast", "kamikaze", "tank"], 1.2, 0.9, 0.10, 480),
    (420,     "Dangerous",       55,       30,   ["regular", "fast", "kamikaze", "tank", "elite"], 1.4, 0.95, 0.15, 420),
    (600,     "Overwhelming",    45,       40,   ["regular", "fast", "kamikaze", "tank", "elite"], 1.7, 1.0, 0.20, 360),
    (900,     "Apocalypse",      35,       50,   ["regular", "fast", "kamikaze", "tank", "elite"], 2.0, 1.1, 0.25, 300),
    (1200,    "Beyond",          28,       60,   ["regular", "fast", "kamikaze", "tank", "elite"], 2.5, 1.2, 0.30, 240),
]


class ContinuousSpawner:
    """Spawns enemies continuously based on elapsed survival time.

    Difficulty scales smoothly between tiers. The player starts
    facing only a handful of weak regulars and gradually encounters
    faster, tougher, and more numerous enemies.
    """

    def __init__(self, camera, player_faction, all_factions):
        self.camera = camera
        self.player_faction = player_faction
        self.all_factions = all_factions

        # Timing
        self.elapsed_frames = 0
        self.spawn_timer = 0

        # Boss tracking
        self.last_boss_time = -999  # seconds
        self.bosses_spawned = 0

        # Current tier cache
        self._tier_index = 0

    @property
    def elapsed_seconds(self):
        return self.elapsed_frames / 60.0

    def get_current_tier(self):
        """Return the current difficulty tier dict based on elapsed time."""
        t = self.elapsed_seconds
        tier_idx = 0
        for i, tier in enumerate(DIFFICULTY_TIERS):
            if t >= tier[0]:
                tier_idx = i
        self._tier_index = tier_idx
        tier = DIFFICULTY_TIERS[tier_idx]
        return {
            "time": tier[0],
            "label": tier[1],
            "interval": tier[2],
            "max_alive": tier[3],
            "types": tier[4],
            "hp_mult": tier[5],
            "speed_mult": tier[6],
            "elite_chance": tier[7],
            "boss_interval": tier[8],
        }

    def get_difficulty_label(self):
        """Return the current difficulty tier label for UI display."""
        tier = self.get_current_tier()
        return tier["label"]

    def _interpolate_tier(self):
        """Smoothly interpolate between current and next tier."""
        t = self.elapsed_seconds
        tier = DIFFICULTY_TIERS[self._tier_index]
        # If we're at the last tier, no interpolation needed
        if self._tier_index >= len(DIFFICULTY_TIERS) - 1:
            return self.get_current_tier()

        next_tier = DIFFICULTY_TIERS[self._tier_index + 1]
        # How far between this tier and next (0.0 to 1.0)
        span = next_tier[0] - tier[0]
        if span <= 0:
            progress = 1.0
        else:
            progress = min(1.0, (t - tier[0]) / span)

        base = self.get_current_tier()
        # Interpolate numeric values
        base["interval"] = int(tier[2] + (next_tier[2] - tier[2]) * progress)
        base["max_alive"] = int(tier[3] + (next_tier[3] - tier[3]) * progress)
        base["hp_mult"] = tier[5] + (next_tier[5] - tier[5]) * progress
        base["speed_mult"] = tier[6] + (next_tier[6] - tier[6]) * progress
        base["elite_chance"] = tier[7] + (next_tier[7] - tier[7]) * progress
        return base

    def update(self, ai_ships, screen_width, screen_height):
        """Called every frame. Returns list of newly spawned Ship objects."""
        self.elapsed_frames += 1
        self.spawn_timer += 1
        new_ships = []

        tier = self._interpolate_tier()

        # Regular spawn
        if self.spawn_timer >= tier["interval"] and len(ai_ships) < tier["max_alive"]:
            self.spawn_timer = 0
            ship = self._spawn_enemy(tier, screen_width, screen_height)
            if ship:
                new_ships.append(ship)

        # Boss spawn check
        if tier["boss_interval"] is not None:
            time_since_boss = self.elapsed_seconds - self.last_boss_time
            if time_since_boss >= tier["boss_interval"]:
                boss = self._spawn_boss(tier, screen_width, screen_height)
                if boss:
                    new_ships.append(boss)
                    self.last_boss_time = self.elapsed_seconds
                    self.bosses_spawned += 1

        return new_ships

    def _spawn_enemy(self, tier, screen_width, screen_height):
        """Spawn a single enemy at the viewport edge ring."""
        import pygame  # deferred import

        enemy_faction = random.choice([f for f in self.all_factions if f != self.player_faction])
        wx, wy = self.camera.get_spawn_ring(300, 500)

        # Pick enemy type
        enemy_type = random.choice(tier["types"])
        # Elite chance override
        if random.random() < tier["elite_chance"] and "elite" in ENEMY_TYPES:
            enemy_type = "elite"

        mods = ENEMY_TYPES[enemy_type]

        ship = Ship(wx, wy, enemy_faction, is_player=False,
                    screen_width=screen_width, screen_height=screen_height)

        # Apply tier scaling
        ship.max_health = int(ship.max_health * tier["hp_mult"] * mods["hp"])
        ship.health = ship.max_health
        ship.speed = max(1, int(ship.speed * tier["speed_mult"] * mods["speed"]))
        ship.fire_rate = max(5, ship.fire_rate)

        # Scale ship visual
        if mods["scale"] != 1.0 and ship.image:
            new_w = int(ship.width * mods["scale"])
            new_h = int(ship.height * mods["scale"])
            ship.image = pygame.transform.smoothscale(ship.image, (new_w, new_h))
            ship.width = new_w
            ship.height = new_h

        # Apply tint
        if mods["tint"] and ship.image:
            tint_surf = pygame.Surface(ship.image.get_size(), pygame.SRCALPHA)
            tint_surf.fill((*mods["tint"], 60))
            ship.image.blit(tint_surf, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

        # Re-cache directional images
        if ship.image:
            ship.image_right = ship.image.copy()
            ship.image_left = pygame.transform.flip(ship.image, True, False)
            ship.image_up = pygame.transform.rotate(ship.image_right, 90)
            ship.image_down = pygame.transform.rotate(ship.image_right, -90)

        ship.xp_value = mods["xp"]
        ship.enemy_type = enemy_type
        ship.ai_fire_timer = random.randint(0, 60)
        return ship

    def _spawn_boss(self, tier, screen_width, screen_height):
        """Spawn a boss enemy with escorts."""
        import pygame

        boss_faction = random.choice([f for f in self.all_factions if f != self.player_faction])
        wx, wy = self.camera.get_spawn_ring(500, 700)

        boss = Ship(wx, wy, boss_faction, is_player=False,
                    screen_width=screen_width, screen_height=screen_height)

        # Boss HP scales with time survived
        boss_num = self.bosses_spawned + 1
        hp_scale = 2.0 + boss_num * 1.5
        boss.max_health = int(100 * hp_scale)
        boss.health = boss.max_health
        boss.max_shields = int(100 * hp_scale * 0.5)
        boss.shields = boss.max_shields

        # Visual scale
        scale = 1.3 + min(boss_num * 0.1, 0.5)
        if boss.image:
            new_w = int(boss.width * scale)
            new_h = int(boss.height * scale)
            boss.image = pygame.transform.smoothscale(boss.image, (new_w, new_h))
            boss.width = new_w
            boss.height = new_h

        # Red tint
        if boss.image:
            tint = pygame.Surface(boss.image.get_size(), pygame.SRCALPHA)
            tint.fill((255, 50, 50, 40))
            boss.image.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

        # Re-cache directional images
        if boss.image:
            boss.image_right = boss.image.copy()
            boss.image_left = pygame.transform.flip(boss.image, True, False)
            boss.image_up = pygame.transform.rotate(boss.image_right, 90)
            boss.image_down = pygame.transform.rotate(boss.image_right, -90)

        boss.fire_rate = max(10, boss.fire_rate // 2)
        boss.xp_value = 200 + boss_num * 50
        boss.enemy_type = "boss"
        boss.is_boss = True
        boss.ai_fire_timer = 0
        return boss
