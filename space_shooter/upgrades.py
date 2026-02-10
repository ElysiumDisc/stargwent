"""Upgrade and enemy type definitions for the space shooter."""

# Upgrade definitions: name -> {display_name, description, max_stacks, icon, color, rarity}
# Rarity: "common" (white), "rare" (blue), "epic" (purple)
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
    # --- New weapon upgrades ---
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
    # --- New passive upgrades ---
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
}

# Rarity colors for UI
RARITY_COLORS = {
    "common": (200, 200, 200),  # White/grey
    "rare": (80, 140, 255),     # Blue
    "epic": (180, 80, 255),     # Purple
}

# Enemy type modifiers: (speed_mult, hp_mult, scale, xp_value, tint)
ENEMY_TYPES = {
    "regular":  {"speed": 0.7, "hp": 1.0, "scale": 1.0, "xp": 30, "tint": None},
    "fast":     {"speed": 1.0, "hp": 0.7, "scale": 0.9, "xp": 40, "tint": (100, 200, 255)},
    "tank":     {"speed": 0.4, "hp": 2.5, "scale": 1.3, "xp": 55, "tint": (150, 150, 150)},
    "elite":    {"speed": 0.8, "hp": 2.0, "scale": 1.1, "xp": 75, "tint": (255, 215, 0)},
    "kamikaze": {"speed": 1.2, "hp": 0.4, "scale": 0.8, "xp": 45, "tint": (255, 60, 60)},
}
