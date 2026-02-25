"""
STARGWENT - GALACTIC CONQUEST - Difficulty System

Four difficulty levels affecting counterattack rates, starting naquadah,
AI power bonuses, and loss penalties.
"""


DIFFICULTIES = {
    "easy": {
        "name": "Easy",
        "description": "Relaxed — fewer counterattacks, more starting resources",
        "counterattack_chance": 0.15,
        "start_naquadah": 150,
        "ai_power_bonus": 0,
        "loss_naquadah_penalty": 20,
        "color": (80, 255, 140),
    },
    "normal": {
        "name": "Normal",
        "description": "Standard challenge — balanced risk and reward",
        "counterattack_chance": 0.30,
        "start_naquadah": 100,
        "ai_power_bonus": 0,
        "loss_naquadah_penalty": 30,
        "color": (255, 200, 80),
    },
    "hard": {
        "name": "Hard",
        "description": "Brutal — aggressive AI, fewer resources",
        "counterattack_chance": 0.40,
        "start_naquadah": 80,
        "ai_power_bonus": 1,
        "loss_naquadah_penalty": 40,
        "color": (255, 100, 80),
    },
    "insane": {
        "name": "Insane",
        "description": "Nightmare — relentless AI, minimal resources",
        "counterattack_chance": 0.50,
        "start_naquadah": 60,
        "ai_power_bonus": 2,
        "loss_naquadah_penalty": 50,
        "color": (200, 50, 255),
    },
}

DIFFICULTY_ORDER = ["easy", "normal", "hard", "insane"]


def get_difficulty(key):
    """Get difficulty config dict by key."""
    return DIFFICULTIES.get(key, DIFFICULTIES["normal"])


def get_start_naquadah(difficulty_key):
    """Get starting naquadah for a difficulty."""
    return get_difficulty(difficulty_key)["start_naquadah"]


def get_counterattack_chance(difficulty_key):
    """Get base counterattack chance for a difficulty."""
    return get_difficulty(difficulty_key)["counterattack_chance"]


def get_ai_power_bonus(difficulty_key):
    """Get AI card power bonus for a difficulty."""
    return get_difficulty(difficulty_key)["ai_power_bonus"]


def get_loss_penalty(difficulty_key):
    """Get naquadah loss penalty for a difficulty."""
    return get_difficulty(difficulty_key)["loss_naquadah_penalty"]
