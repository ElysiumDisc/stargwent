"""Upgrade, evolution, and enemy type definitions for the space shooter."""

# Upgrade definitions: name -> {display_name, description, max_stacks, icon, color, rarity}
# Rarity: "common" (white), "rare" (blue), "epic" (purple), "legendary" (gold)
UPGRADES = {
    # --- Original upgrades ---
    "naquadah_plating": {
        "name": "Naquadah Plating",
        "desc": "+20 max HP, heal 20",
        "max": 5, "icon": "+", "color": (200, 50, 50),
        "rarity": "common",
    },
    "weapons_power": {
        "name": "Weapons Power",
        "desc": "+15% projectile damage",
        "max": 5, "icon": "W", "color": (255, 100, 50),
        "rarity": "common",
    },
    "rapid_capacitors": {
        "name": "Rapid Capacitors",
        "desc": "-10% fire cooldown",
        "max": 5, "icon": ">>", "color": (255, 200, 50),
        "rarity": "common",
    },
    "sublight_engines": {
        "name": "Sublight Engines",
        "desc": "+1 ship speed",
        "max": 5, "icon": "^", "color": (50, 200, 255),
        "rarity": "common",
    },
    "multi_targeting": {
        "name": "Multi-Targeting",
        "desc": "+1 extra projectile",
        "max": 5, "icon": "|||", "color": (255, 150, 200),
        "rarity": "rare",
    },
    "shield_harmonics": {
        "name": "Shield Harmonics",
        "desc": "+20 max shields\n+0.1 shield regen",
        "max": 5, "icon": "O", "color": (100, 150, 255),
        "rarity": "common",
    },
    "tractor_beam": {
        "name": "Tractor Beam",
        "desc": "+50% XP orb range",
        "max": 5, "icon": "@", "color": (100, 255, 100),
        "rarity": "common",
    },
    "orbital_defense": {
        "name": "Orbital Defense",
        "desc": "+1 orbiting drone\n(max 3)",
        "max": 3, "icon": "D", "color": (150, 255, 150),
        "rarity": "rare",
    },
    "rear_turret": {
        "name": "Rear Turret",
        "desc": "Auto-fire backward",
        "max": 5, "icon": "<", "color": (255, 255, 100),
        "rarity": "rare",
    },
    "zpm_reserves": {
        "name": "ZPM Reserves",
        "desc": "Power-ups last\n50% longer",
        "max": 5, "icon": "Z", "color": (200, 100, 255),
        "rarity": "common",
    },
    "sarcophagus": {
        "name": "Sarcophagus",
        "desc": "Heal 5 HP/sec",
        "max": 5, "icon": "H", "color": (255, 100, 100),
        "rarity": "common",
    },
    "targeting_computer": {
        "name": "Targeting Computer",
        "desc": "Projectiles gain\nslight homing",
        "max": 5, "icon": "T", "color": (200, 200, 255),
        "rarity": "rare",
    },
    # --- Weapon upgrades ---
    "chain_lightning": {
        "name": "Chain Lightning",
        "desc": "Projectiles chain to\n+1 nearby enemy",
        "max": 3, "icon": "Z", "color": (100, 150, 255),
        "rarity": "epic",
    },
    "scatter_shot": {
        "name": "Scatter Shot",
        "desc": "+3 spread pellets\n(lower dmg)",
        "max": 3, "icon": "///", "color": (255, 180, 100),
        "rarity": "rare",
    },
    "gravity_well": {
        "name": "Gravity Well",
        "desc": "Auto-deploy well that\npulls enemies",
        "max": 3, "icon": "G", "color": (150, 80, 255),
        "rarity": "epic",
    },
    "shield_bash": {
        "name": "Shield Bash",
        "desc": "Dash damages\nenemies on contact",
        "max": 3, "icon": "!", "color": (255, 200, 50),
        "rarity": "rare",
    },
    # --- Passive upgrades ---
    "magnet_field": {
        "name": "Magnet Field",
        "desc": "+40 XP orb\ncollection range",
        "max": 5, "icon": "M", "color": (50, 255, 200),
        "rarity": "common",
    },
    "critical_strike": {
        "name": "Critical Strike",
        "desc": "+10% chance\ndouble damage",
        "max": 5, "icon": "!!", "color": (255, 50, 50),
        "rarity": "rare",
    },
    "evasion_matrix": {
        "name": "Evasion Matrix",
        "desc": "+8% dodge chance",
        "max": 5, "icon": "~", "color": (200, 200, 255),
        "rarity": "rare",
    },
    "berserker_protocol": {
        "name": "Berserker Protocol",
        "desc": "+5% dmg per stack\nwhen <50% HP",
        "max": 5, "icon": "B", "color": (255, 80, 80),
        "rarity": "epic",
    },
    "hyperspace_jump": {
        "name": "Hyperspace Jump",
        "desc": "-15% wormhole\ncooldown",
        "max": 3, "icon": "H", "color": (100, 180, 255),
        "rarity": "rare",
    },
    # --- NEW Phase 3 upgrades ---
    "orbital_laser": {
        "name": "Orbital Laser",
        "desc": "Periodic beam strike\non enemy clusters",
        "max": 3, "icon": "L", "color": (0, 200, 255),
        "rarity": "epic",
    },
    "nova_burst": {
        "name": "Nova Burst",
        "desc": "AoE damage pulse\nevery 8 seconds",
        "max": 3, "icon": "N", "color": (255, 100, 200),
        "rarity": "epic",
    },
    "naquadah_bomb": {
        "name": "Naquadah Bomb",
        "desc": "10% on-kill chance\nmassive explosion",
        "max": 3, "icon": "X", "color": (255, 150, 0),
        "rarity": "epic",
    },
    "temporal_field": {
        "name": "Temporal Field",
        "desc": "Slow nearby enemies\n15% per stack",
        "max": 3, "icon": "T", "color": (100, 200, 255),
        "rarity": "rare",
    },
    "ancient_knowledge": {
        "name": "Ancient Knowledge",
        "desc": "+30% XP gained\nper stack",
        "max": 5, "icon": "A", "color": (200, 200, 100),
        "rarity": "common",
    },
    "summon_ally": {
        "name": "Summon Ally",
        "desc": "Summon an ally ship\n+5s duration/stack",
        "max": 3, "icon": "F", "color": (100, 255, 100),
        "rarity": "epic",
    },
}

# Rarity colors for UI
RARITY_COLORS = {
    "common": (200, 200, 200),     # White/grey
    "rare": (80, 140, 255),        # Blue
    "epic": (180, 80, 255),        # Purple
    "legendary": (255, 165, 0),    # Gold
}

# Evolution system: combining two maxed upgrades creates a legendary evolution
EVOLUTIONS = {
    "thors_hammer": {
        "name": "Thor's Hammer",
        "desc": "Lightning arcs to\nALL nearby enemies",
        "prereqs": ["chain_lightning", "weapons_power"],
        "color": (100, 150, 255),
    },
    "bullet_hell": {
        "name": "Bullet Hell",
        "desc": "Fire projectiles in\nevery direction",
        "prereqs": ["multi_targeting", "rapid_capacitors"],
        "color": (255, 150, 200),
    },
    "black_hole": {
        "name": "Black Hole",
        "desc": "Massive pull +\ndamage field",
        "prereqs": ["gravity_well", "nova_burst"],
        "color": (150, 80, 255),
    },
    "ancient_outpost": {
        "name": "Ancient Outpost",
        "desc": "Drones become\nshielded turrets",
        "prereqs": ["orbital_defense", "shield_harmonics"],
        "color": (150, 255, 150),
    },
    "cluster_bomb": {
        "name": "Cluster Bomb",
        "desc": "Explosions scatter\ninto sub-munitions",
        "prereqs": ["naquadah_bomb", "scatter_shot"],
        "color": (255, 150, 0),
    },
}

# Level 20 Primary Fire Masteries — one unique upgrade per weapon type
PRIMARY_MASTERIES = {
    "beam": {
        "name": "Overcharged Beam",
        "desc": "Beam 50% wider + burn DoT",
        "color": (0, 255, 255),
    },
    "plasma_lance": {
        "name": "Plasma Detonation",
        "desc": "120px AoE explosion on impact",
        "color": (180, 60, 255),
    },
    "disruptor_pulse": {
        "name": "Cascade Disruption",
        "desc": "Fragments into 3 mini-pulses on hit",
        "color": (100, 200, 255),
    },
    "laser": {
        "name": "Focused Optics",
        "desc": "Shots pierce through all enemies",
        "color": (255, 180, 0),
    },
    "dual_staff": {
        "name": "Staff Barrage",
        "desc": "Fires 4 staffs instead of 2",
        "color": (255, 100, 50),
    },
    "missile": {
        "name": "MIRV Warhead",
        "desc": "Splits into 3 homing sub-missiles",
        "color": (0, 150, 255),
    },
    "drone_pulse": {
        "name": "Drone Swarm",
        "desc": "Each shot spawns 2 extra drones",
        "color": (255, 200, 50),
    },
    "staff": {
        "name": "Kree's Judgement",
        "desc": "Every 5th shot is supercharged (3x)",
        "color": (255, 120, 30),
    },
    "energy_ball": {
        "name": "Unstable Naquadah",
        "desc": "Energy balls deal trail damage",
        "color": (255, 100, 200),
    },
    "nanite_swarm": {
        "name": "Replicator Horde",
        "desc": "3 children per kill, cap raised to 30",
        "color": (180, 180, 200),
    },
    "wraith_culling": {
        "name": "Feeding Frenzy",
        "desc": "Life steal 40%, beam widens on kill",
        "color": (160, 40, 255),
    },
    "tunnel_crystal": {
        "name": "Crystal Labyrinth",
        "desc": "Max 4 vortices, duration doubled",
        "color": (150, 80, 255),
    },
}

# Enemy type modifiers: (speed_mult, hp_mult, scale, xp_value, tint, behavior)
ENEMY_TYPES = {
    # --- Original types ---
    "regular":  {"speed": 0.7, "hp": 1.0, "scale": 1.0, "xp": 30, "tint": None, "behavior": None},
    "fast":     {"speed": 1.0, "hp": 0.7, "scale": 0.9, "xp": 40, "tint": (100, 200, 255), "behavior": None},
    "tank":     {"speed": 0.4, "hp": 2.5, "scale": 1.3, "xp": 55, "tint": (150, 150, 150), "behavior": None},
    "elite":    {"speed": 0.8, "hp": 2.0, "scale": 1.1, "xp": 75, "tint": (255, 215, 0), "behavior": None},
    "kamikaze": {"speed": 1.2, "hp": 0.4, "scale": 0.8, "xp": 45, "tint": (255, 60, 60), "behavior": None},
    # --- Stargate-themed enemies ---
    "wraith_dart":    {"speed": 1.1, "hp": 0.6, "scale": 0.85, "xp": 50, "tint": (80, 0, 160), "behavior": "swarm_lifesteal"},
    "replicator":     {"speed": 0.9, "hp": 0.3, "scale": 0.6, "xp": 25, "tint": (180, 180, 200), "behavior": "split_on_death"},
    "ori_fighter":    {"speed": 0.7, "hp": 2.0, "scale": 1.15, "xp": 80, "tint": (255, 255, 200), "behavior": "shielded_charge"},
    "ancient_drone":  {"speed": 1.0, "hp": 0.8, "scale": 0.7, "xp": 60, "tint": (255, 200, 50), "behavior": "homing"},
    "death_glider":   {"speed": 0.8, "hp": 1.0, "scale": 1.0, "xp": 45, "tint": (200, 170, 0), "behavior": "paired"},
    "alkesh_bomber":  {"speed": 0.4, "hp": 3.0, "scale": 1.4, "xp": 70, "tint": (200, 100, 0), "behavior": "bomber"},
    "wraith_hive":    {"speed": 0.3, "hp": 5.0, "scale": 1.6, "xp": 150, "tint": (100, 0, 180), "behavior": "mini_boss_spawner"},
    "ori_mothership": {"speed": 0.3, "hp": 10.0, "scale": 2.5, "xp": 500, "tint": (255, 255, 180), "behavior": "ori_boss"},
    "wraith_supergate": {"speed": 0.25, "hp": 8.0, "scale": 2.0, "xp": 500, "tint": (80, 0, 160), "behavior": "wraith_boss"},
    "wraith_miniship": {"speed": 0.9, "hp": 1.5, "scale": 0.75, "xp": 65, "tint": (80, 0, 160), "behavior": "hostile_all"},
}

# Explosion color palettes per enemy behavior/type
ENEMY_EXPLOSION_PALETTES = {
    "wraith_dart": [(160, 0, 255), (100, 0, 180), (200, 100, 255)],
    "wraith_hive": [(160, 0, 255), (100, 0, 180), (200, 100, 255)],
    "replicator": [(200, 200, 220), (150, 150, 180), (255, 255, 255)],
    "ori_fighter": [(255, 255, 200), (255, 220, 100), (255, 255, 255)],
    "ancient_drone": [(255, 200, 50), (255, 180, 0), (255, 255, 150)],
    "ori_mothership": [(255, 255, 200), (255, 220, 100), (255, 200, 50), (255, 255, 255)],
    "wraith_supergate": [(160, 0, 255), (100, 0, 180), (200, 100, 255), (80, 0, 120)],
    "wraith_miniship": [(160, 0, 255), (100, 0, 180), (200, 100, 255)],
}
