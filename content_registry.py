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
    FACTION_ALTERAN,
)

# Base leaders available from the start for each faction.
BASE_FACTION_LEADERS = {
    FACTION_TAURI: [
        {"name": "Col. Jack O'Neill", "ability": "Clone gambit: Summon a temporary Jack clone each round. Draw +1 card at round start", "ability_desc": "At the start of every round summon a 6-power Jack clone that survives exactly 3 of your turns (removed when the 4th would begin)", "card_id": "tauri_oneill"},
        {"name": "Gen. George Hammond", "ability": "Your first unit each round gets +3 power", "ability_desc": "Your first unit played each round gets +3 power", "card_id": "tauri_hammond"},
        {"name": "Dr. Samantha Carter", "ability": "+2 power to all Siege units", "ability_desc": "+2 power to all Siege units", "card_id": "tauri_carter"},
    ],
    FACTION_GOAULD: [
        {"name": "Apophis", "ability": "Once per game, unleash a random weather storm", "ability_desc": "Activate a random battlefield weather that hits both sides once per game", "card_id": "goauld_apophis"},
        {"name": "Lord Yu", "ability": "See opponent's hand next round when you pass", "ability_desc": "When you pass, the opponent's entire next-round hand is revealed until the round ends", "card_id": "goauld_yu"},
        {"name": "Sokar", "ability": "+1 power to all Close Combat units", "ability_desc": "+1 power to all Close Combat units", "card_id": "goauld_sokar"},
    ],
    FACTION_JAFFA: [
        {"name": "Teal'c", "ability": "Draw 1 card when winning a round", "ability_desc": "Draw 1 card when winning a round", "card_id": "jaffa_tealc"},
        {"name": "Bra'tac", "ability": "All Agile cards gain +1 power", "ability_desc": "All Agile cards gain +1 power", "card_id": "jaffa_bratac"},
        {"name": "Rak'nor", "ability": "Can play 2 cards on your first turn each round", "ability_desc": "Can play 2 cards on your first turn of each round", "card_id": "jaffa_raknor"},
    ],
    FACTION_LUCIAN: [
        {"name": "Varro", "ability": "Spy cards draw 3 instead of 2", "ability_desc": "Deep Cover Agents draw 3 cards instead of 2", "card_id": "lucian_varro"},
        {"name": "Sodan Master", "ability": "+3 power to highest unit in each row", "ability_desc": "+3 power to your highest unit in each row", "card_id": "lucian_sodan_master"},
        {"name": "Ba'al Clone", "ability": "+2 power to all Ranged units", "ability_desc": "+2 power to all Ranged units", "card_id": "lucian_baal_clone"},
    ],
    FACTION_ASGARD: [
        {"name": "Freyr", "ability": "Block the first 2 weather effects per game", "ability_desc": "Freyr's shield absorbs the first 2 weather effects targeting you (per game)", "card_id": "asgard_freyr"},
        {"name": "Loki", "ability": "Steal 1 power from opponent's strongest unit", "ability_desc": "Steal 1 power from opponent's strongest unit each turn", "card_id": "asgard_loki"},
        {"name": "Heimdall", "ability": "Your Legendary Commanders get +3 power", "ability_desc": "Your Legendary Commanders get +3 power", "card_id": "asgard_heimdall"},
    ],
    FACTION_ALTERAN: [
        {"name": "Adria, The Orici", "ability": "Crusade: First 2 units each round gain +3 power", "ability_desc": "Your first 2 non-hero units played each round get +3 power from the Ori's blessing", "card_id": "alteran_adria"},
        {"name": "The Doci", "ability": "Voice of the Ori: Convert enemy spy into +5 unit for you", "ability_desc": "Once per game: When opponent plays a Spy on your side, it becomes a +5 unit for you instead", "card_id": "alteran_doci"},
        {"name": "Merlin (Moros)", "ability": "Sangraal Protocol: Destroy one enemy hero", "ability_desc": "Once per game: Target and destroy one Legendary Commander on the opponent's board", "card_id": "alteran_merlin"},
        {"name": "Morgan Le Fay", "ability": "Eternal Watch: Revive 1 unit at rounds 2 and 3", "ability_desc": "Automatically revive 1 random destroyed unit at the start of rounds 2 and 3", "card_id": "alteran_morgan"},
        {"name": "Oma Desala", "ability": "Path to Ascension: Sacrifice weakest for +3 all", "ability_desc": "Once per game: Sacrifice your weakest non-hero unit to give +3 power to all remaining units on your board", "card_id": "alteran_oma"},
    ],
}

# Leaders that can be unlocked through gameplay progression.
UNLOCKABLE_LEADERS = {
    FACTION_TAURI: [
        {"name": "Gen. Landry", "ability": "Homeworld Command: Units get +1 in row with most units", "ability_desc": "All units in your most populated row get +1 power", "card_id": "tauri_landry"},
        {"name": "Dr. McKay", "ability": "Draw 2 cards when you pass", "ability_desc": "Draw 2 cards when you pass your turn", "card_id": "tauri_mckay"},
        {"name": "Jonas Quinn", "ability": "Eidetic Memory: Copy a card opponent drew", "ability_desc": "Once per game: Look at cards opponent drew, copy one to your hand", "card_id": "tauri_quinn"},
        {"name": "Catherine Langford", "ability": "Ancient Knowledge: Look at top 3 cards of your deck, play one immediately", "ability_desc": "Once per game: Reveal top 3 cards, choose one to play, rest go to bottom of deck", "card_id": "tauri_langford"},
    ],
    FACTION_GOAULD: [
        {"name": "Ba'al", "ability": "System Lord's Cunning: Resurrect card from discard", "ability_desc": "Once per game: Return a destroyed unit from discard pile to your hand", "card_id": "goauld_baal"},
        {"name": "Anubis", "ability": "Ascended power: Naquadah Overload every 2 rounds", "ability_desc": "Automatically trigger Naquadah Overload at start of rounds 2 and 3", "card_id": "goauld_anubis"},
        {"name": "Hathor", "ability": "Seduction: Steal the lowest power enemy unit", "ability_desc": "Use her charm to take control of the enemy's weakest unit (manual activation)", "card_id": "goauld_hathor_unlock", "image_path": "assets/goauld_hathor_unlock_leader.png"},
        {"name": "Cronus", "ability": "Ancient Goa'uld: All units gain +1 power per round number", "ability_desc": "Units get +1 in round 1, +2 in round 2, +3 in round 3", "card_id": "goauld_cronus"},
    ],
    FACTION_JAFFA: [
        {"name": "Ka'lel", "ability": "Warrior training: First 3 units each round get +2 power", "ability_desc": "The first 3 units you play each round gain +2 power", "card_id": "jaffa_kalel"},
        {"name": "Gerak", "ability": "Free Jaffa: Draw 1 card for every 2 units played", "ability_desc": "Draw 1 card for every 2 units you play in a round", "card_id": "jaffa_gerak"},
        {"name": "Ishta", "ability": "Hak'tyl resistance: All Gate Reinforcement units gain +2 power", "ability_desc": "Units with Gate Reinforcement ability get +2 power", "card_id": "jaffa_ishta"},
        {"name": "Rya'c", "ability": "Hope for Tomorrow: Draw 2 extra cards at start of round 3", "ability_desc": "Automatically draw 2 extra cards when round 3 begins", "card_id": "jaffa_ryac"},
    ],
    FACTION_LUCIAN: [
        {"name": "Netan", "ability": "Smuggling: Draw +1 card each round", "ability_desc": "Draw 1 extra card at the start of each round", "card_id": "lucian_netan"},
        {"name": "Vala Mal Doran", "ability": "Thief's Luck: Steal card from opponent's hand", "ability_desc": "At start of round 2, steal 1 random card from opponent's hand", "card_id": "lucian_vala"},
        {"name": "Anateo", "ability": "Black market: Medical Evac ability every round", "ability_desc": "Free Medical Evac at start of rounds 2 and 3", "card_id": "lucian_anateo"},
        {"name": "Kiva", "ability": "Brutal Tactics: First unit each round gets +4 power", "ability_desc": "Your first unit each round gets +4 power", "card_id": "lucian_kiva"},
    ],
    FACTION_ASGARD: [
        {"name": "Thor Supreme Commander", "ability": "Fleet Command: Motherships get +3 power", "ability_desc": "All Mothership and O'Neill-Class ships get +3 power", "card_id": "asgard_thor"},
        {"name": "Hermiod", "ability": "Shields up: Weather affects opponent only", "ability_desc": "Weather cards you play only affect your opponent", "card_id": "asgard_hermiod"},
        {"name": "Penegal", "ability": "Cloning bay: Revive one unit at start of each round", "ability_desc": "Revive 1 random unit from discard at start of rounds 2 and 3", "card_id": "asgard_penegal"},
        {"name": "Aegir", "ability": "Asgard Archives: Draw 1 when playing Siege unit", "ability_desc": "Draw 1 card whenever you play a Siege unit", "card_id": "asgard_aegir"},
    ],
    FACTION_ALTERAN: [],  # All Alteran leaders are base (faction itself is the unlock gate)
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
    "jaffa_kalel": (32, 22, 12),
    "jaffa_gerak": (42, 32, 22),
    "jaffa_ishta": (28, 18, 8),
    "jaffa_ryac": (35, 25, 15),
    # Lucian
    "lucian_varro": (35, 15, 35),
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
    # Alteran
    "alteran_adria": (50, 25, 5),
    "alteran_doci": (45, 20, 0),
    "alteran_merlin": (30, 30, 40),
    "alteran_morgan": (25, 25, 45),
    "alteran_oma": (35, 30, 15),
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
    "jaffa_kalel": "Ka'lel",
    "jaffa_gerak": "Gerak",
    "jaffa_ishta": "Ishta",
    "jaffa_ryac": "Rya'c",
    "lucian_varro": "Varro",
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
    # Alteran
    "alteran_adria": "Adria",
    "alteran_doci": "The Doci",
    "alteran_merlin": "Merlin",
    "alteran_morgan": "Morgan Le Fay",
    "alteran_oma": "Oma Desala",
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


# Full registry of all leaders (base + unlockable) with faction info
LEADER_REGISTRY = []
for faction in {*BASE_FACTION_LEADERS.keys(), *UNLOCKABLE_LEADERS.keys()}:
    leaders = get_all_leaders_for_faction(faction)
    # Add faction field to each leader for easier lookup
    for leader in leaders:
        if 'faction' not in leader:
            leader['faction'] = faction
    LEADER_REGISTRY.extend(leaders)


# ============================================================================
# USER CONTENT LOADING
# ============================================================================

def load_user_leaders():
    """
    Load user-created leaders from user_content folder.

    This function is called at game startup to inject user leaders
    into the leader registries. User leaders use ONLY existing
    leader ability mechanics.
    """
    try:
        from user_content_loader import get_loader

        loader = get_loader()
        if not loader._loaded:
            loader.load_all()

        # Register user leaders
        for leader in loader.user_leaders:
            card_id = leader.get("card_id")
            faction = leader.get("faction")
            name = leader.get("name")
            is_base = leader.get("is_base", True)

            if not card_id or not faction:
                continue

            # Skip if already registered
            if card_id in LEADER_NAME_BY_ID:
                continue

            # Add to name mapping
            LEADER_NAME_BY_ID[card_id] = name

            # Add to faction leader IDs
            if faction not in ALL_LEADER_IDS_BY_FACTION:
                ALL_LEADER_IDS_BY_FACTION[faction] = []
            ALL_LEADER_IDS_BY_FACTION[faction].append(card_id)

            # Add to banner names
            banner_name = leader.get("banner_name", name)
            LEADER_BANNER_NAMES[card_id] = banner_name

            # Add to appropriate registry
            target_registry = BASE_FACTION_LEADERS if is_base else UNLOCKABLE_LEADERS
            if faction not in target_registry:
                target_registry[faction] = []

            leader_entry = {
                "name": name,
                "ability": leader.get("ability", ""),
                "ability_desc": leader.get("ability_desc", ""),
                "card_id": card_id,
                "faction": faction,
            }

            if leader.get("image_path"):
                leader_entry["image_path"] = leader["image_path"]

            target_registry[faction].append(leader_entry)
            LEADER_REGISTRY.append(leader_entry)

            print(f"[LEADERS] Registered user leader: {card_id}")

    except ImportError:
        pass
    except Exception as e:
        print(f"[LEADERS] Error loading user leaders: {e}")
