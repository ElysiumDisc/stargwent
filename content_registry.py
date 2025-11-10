"""
Central registry for faction leaders, unlockable leaders, and related metadata.
Consolidates data that was previously duplicated across deck building, unlocks,
and asset placeholder generation to keep future content additions centralized.
"""
from cards import (
    FACTION_TAURI,
    FACTION_GOAULD,
    FACTION_JAFFA,
    FACTION_LUCIAN,
    FACTION_ASGARD,
)

# Base leaders available from the start for each faction.
BASE_FACTION_LEADERS = {
    FACTION_TAURI: [
        {"name": "Col. Jack O'Neill", "ability": "Draw 1 extra card at round start", "ability_desc": "Draw 1 extra card at the start of rounds 2 and 3", "card_id": "tauri_oneill"},
        {"name": "Gen. George Hammond", "ability": "Your first unit each round gets +3 power", "ability_desc": "Your first unit played each round gets +3 power", "card_id": "tauri_hammond"},
        {"name": "Dr. Samantha Carter", "ability": "+2 power to all Siege units", "ability_desc": "+2 power to all Siege units", "card_id": "tauri_carter"},
    ],
    FACTION_GOAULD: [
        {"name": "Apophis", "ability": "Seize a random enemy ship if they have 4+ in Siege", "ability_desc": "If the opponent has more than 3 siege ships, steal one at the start of your turn", "card_id": "goauld_apophis"},
        {"name": "Lord Yu", "ability": "See opponent's hand when you pass", "ability_desc": "Reveal opponent's hand for 3 seconds when you pass", "card_id": "goauld_yu"},
        {"name": "Sokar", "ability": "+1 power to all Close Combat units", "ability_desc": "+1 power to all Close Combat units", "card_id": "goauld_sokar"},
    ],
    FACTION_JAFFA: [
        {"name": "Teal'c", "ability": "Draw 1 card when winning a round", "ability_desc": "Draw 1 card when winning a round", "card_id": "jaffa_tealc"},
        {"name": "Bra'tac", "ability": "All Agile cards gain +1 power", "ability_desc": "All Agile cards gain +1 power", "card_id": "jaffa_bratac"},
        {"name": "Rak'nor", "ability": "Can play 2 cards on your first turn each round", "ability_desc": "Can play 2 cards on your first turn of each round", "card_id": "jaffa_raknor"},
    ],
    FACTION_LUCIAN: [
        {"name": "Vulkar", "ability": "Spy cards draw 3 instead of 2", "ability_desc": "Deep Cover Agents draw 3 cards instead of 2", "card_id": "lucian_vulkar"},
        {"name": "Sodan Master", "ability": "+3 power to highest unit in each row", "ability_desc": "+3 power to your highest unit in each row", "card_id": "lucian_sodan_master"},
        {"name": "Ba'al Clone", "ability": "+2 power to all Ranged units", "ability_desc": "+2 power to all Ranged units", "card_id": "lucian_baal_clone"},
    ],
    FACTION_ASGARD: [
        {"name": "Freyr", "ability": "Immune to weather effects", "ability_desc": "Immune to all space hazards (weather effects)", "card_id": "asgard_freyr"},
        {"name": "Loki", "ability": "Steal 1 power from opponent's strongest unit", "ability_desc": "Steal 1 power from opponent's strongest unit each turn", "card_id": "asgard_loki"},
        {"name": "Heimdall", "ability": "Your Legendary Commanders get +3 power", "ability_desc": "Your Legendary Commanders get +3 power", "card_id": "asgard_heimdall"},
    ],
}

# Leaders that can be unlocked through gameplay progression.
UNLOCKABLE_LEADERS = {
    FACTION_TAURI: [
        {"name": "Gen. Landry", "ability": "+1 power to all units each round they survive", "ability_desc": "+1 power to all units for each round they survive on the board", "card_id": "tauri_landry"},
        {"name": "Dr. McKay", "ability": "Draw 2 cards when you pass", "ability_desc": "Draw 2 cards when you pass your turn", "card_id": "tauri_mckay"},
        {"name": "Jonas Quinn", "ability": "Premonition: See opponent's next card", "ability_desc": "See the next card your opponent will play", "card_id": "tauri_quinn"},
        {"name": "Catherine Langford", "ability": "Archaeological Insight: All Neutral cards cost no resources", "ability_desc": "Play Neutral cards without restrictions", "card_id": "tauri_langford"},
    ],
    FACTION_GOAULD: [
        {"name": "Ba'al", "ability": "Clone technology: Copy highest power unit", "ability_desc": "At round start, copy your highest power unit", "card_id": "goauld_baal"},
        {"name": "Anubis", "ability": "Ascended power: Naquadah Overload every 2 rounds", "ability_desc": "Automatically trigger Naquadah Overload at start of rounds 2 and 3", "card_id": "goauld_anubis"},
        {"name": "Hathor", "ability": "Seduction: Steal opponent's lowest card to your hand", "ability_desc": "At round start, steal opponent's lowest power unit from their board", "card_id": "goauld_hathor_unlock"},
        {"name": "Cronus", "ability": "Ancient Goa'uld: All units gain +1 power per round number", "ability_desc": "Units get +1 in round 1, +2 in round 2, +3 in round 3", "card_id": "goauld_cronus"},
    ],
    FACTION_JAFFA: [
        {"name": "Master Bra'tac", "ability": "Final stand: Units get +3 power in final round", "ability_desc": "+3 power to all units in round 3", "card_id": "jaffa_master_bratac"},
        {"name": "Ka'lel", "ability": "Warrior training: First 3 units each round get +2 power", "ability_desc": "The first 3 units you play each round gain +2 power", "card_id": "jaffa_kalel"},
        {"name": "Gerak", "ability": "Free Jaffa: Draw 1 card for every 2 units played", "ability_desc": "Draw 1 card for every 2 units you play in a round", "card_id": "jaffa_gerak"},
        {"name": "Ishta", "ability": "Hak'tyl resistance: All Gate Reinforcement units gain +2 power", "ability_desc": "Units with Gate Reinforcement ability get +2 power", "card_id": "jaffa_ishta"},
    ],
    FACTION_LUCIAN: [
        {"name": "Netan", "ability": "Smuggling: Add random card from neutral pool each round", "ability_desc": "Gain 1 random Neutral card at start of each round", "card_id": "lucian_netan"},
        {"name": "Vala Mal Doran", "ability": "Treasure hunter: Reveal 3 cards, keep 1", "ability_desc": "Once per game, look at top 3 cards of deck and keep one", "card_id": "lucian_vala"},
        {"name": "Anateo", "ability": "Black market: Medical Evac ability every round", "ability_desc": "Can use Medical Evac ability once per round without card", "card_id": "lucian_anateo"},
        {"name": "Kiva", "ability": "Surprise attack: Play 2 cards on first turn", "ability_desc": "Can play 2 cards on your first turn of the game", "card_id": "lucian_kiva"},
    ],
    FACTION_ASGARD: [
        {"name": "Thor Supreme Commander", "ability": "Beam technology: Move any unit once per round", "ability_desc": "Once per round, move any unit to a different row", "card_id": "asgard_thor"},
        {"name": "Hermiod", "ability": "Shields up: Weather affects opponent only", "ability_desc": "Weather cards you play only affect your opponent", "card_id": "asgard_hermiod"},
        {"name": "Penegal", "ability": "Cloning bay: Revive one unit at start of each round", "ability_desc": "Revive 1 random unit from discard at start of rounds 2 and 3", "card_id": "asgard_penegal"},
        {"name": "Aegir", "ability": "High Council: +2 power to all Legendary Commanders", "ability_desc": "+2 power to all your Legendary Commander cards", "card_id": "asgard_aegir"},
    ],
}

# Leader-specific background colors used in the deck builder when an image is missing.
LEADER_COLOR_OVERRIDES = {
    # Tau'ri
    "tauri_oneill": (20, 30, 50),
    "tauri_hammond": (15, 35, 55),
    "tauri_carter": (10, 25, 50),
    "tauri_landry": (25, 35, 45),
    "tauri_mckay": (15, 30, 60),
    "tauri_quinn": (18, 28, 52),
    "tauri_langford": (12, 22, 48),
    # Goa'uld
    "goauld_apophis": (40, 15, 15),
    "goauld_yu": (45, 20, 10),
    "goauld_sokar": (35, 10, 10),
    "goauld_baal": (38, 12, 20),
    "goauld_anubis": (25, 10, 25),
    "goauld_hathor_unlock": (42, 15, 25),
    "goauld_cronus": (45, 18, 12),
    # Jaffa
    "jaffa_tealc": (35, 25, 15),
    "jaffa_bratac": (40, 30, 20),
    "jaffa_raknor": (30, 20, 10),
    "jaffa_master_bratac": (38, 28, 18),
    "jaffa_kalel": (32, 22, 12),
    "jaffa_gerak": (42, 32, 22),
    "jaffa_ishta": (28, 18, 8),
    # Lucian
    "lucian_vulkar": (35, 15, 35),
    "lucian_sodan_master": (40, 20, 40),
    "lucian_baal_clone": (30, 10, 30),
    "lucian_netan": (38, 18, 38),
    "lucian_vala": (42, 22, 42),
    "lucian_anateo": (32, 12, 32),
    "lucian_kiva": (36, 16, 36),
    # Asgard
    "asgard_freyr": (10, 35, 30),
    "asgard_loki": (15, 40, 35),
    "asgard_heimdall": (5, 30, 25),
    "asgard_thor": (12, 38, 32),
    "asgard_hermiod": (8, 32, 28),
    "asgard_penegal": (14, 42, 36),
    "asgard_aegir": (10, 35, 30),
}

# Optional shorter display names for leader backgrounds and matchup art.
LEADER_BANNER_NAMES = {
    "tauri_oneill": "Jack O'Neill",
    "tauri_hammond": "Gen. Hammond",
    "tauri_carter": "Samantha Carter",
    "tauri_landry": "Gen. Landry",
    "tauri_mckay": "Dr. McKay",
    "tauri_quinn": "Jonas Quinn",
    "tauri_langford": "Catherine Langford",
    "goauld_apophis": "Apophis",
    "goauld_yu": "Lord Yu",
    "goauld_sokar": "Sokar",
    "goauld_baal": "Ba'al",
    "goauld_anubis": "Anubis",
    "goauld_hathor_unlock": "Hathor",
    "goauld_cronus": "Cronus",
    "jaffa_tealc": "Teal'c",
    "jaffa_bratac": "Bra'tac",
    "jaffa_raknor": "Rak'nor",
    "jaffa_master_bratac": "Master Bra'tac",
    "jaffa_kalel": "Ka'lel",
    "jaffa_gerak": "Gerak",
    "jaffa_ishta": "Ishta",
    "lucian_vulkar": "Vulkar",
    "lucian_sodan_master": "Sodan Master",
    "lucian_baal_clone": "Ba'al Clone",
    "lucian_netan": "Netan",
    "lucian_vala": "Vala Mal Doran",
    "lucian_anateo": "Anateo",
    "lucian_kiva": "Kiva",
    "asgard_freyr": "Freyr",
    "asgard_loki": "Loki",
    "asgard_heimdall": "Heimdall",
    "asgard_thor": "Thor",
    "asgard_hermiod": "Hermiod",
    "asgard_penegal": "Penegal",
    "asgard_aegir": "Aegir",
}


def get_all_leaders_for_faction(faction):
    """Return the combined list of base and unlockable leader entries for a faction."""
    leaders = list(BASE_FACTION_LEADERS.get(faction, []))
    leaders.extend(UNLOCKABLE_LEADERS.get(faction, []))
    return leaders


LEADER_NAME_BY_ID = {}
ALL_LEADER_IDS_BY_FACTION = {}

for faction in {
    *BASE_FACTION_LEADERS.keys(),
    *UNLOCKABLE_LEADERS.keys(),
}:
    entries = get_all_leaders_for_faction(faction)
    ALL_LEADER_IDS_BY_FACTION[faction] = [leader["card_id"] for leader in entries]
    for leader in entries:
        LEADER_NAME_BY_ID[leader["card_id"]] = leader["name"]


def iter_unlockable_leader_ids():
    """Yield every unlockable leader card id."""
    for leaders in UNLOCKABLE_LEADERS.values():
        for leader in leaders:
            yield leader["card_id"]


def get_leader_banner_name(card_id):
    """Get a short display name for a leader (falls back to full name if needed)."""
    return LEADER_BANNER_NAMES.get(card_id, LEADER_NAME_BY_ID.get(card_id, card_id))
