"""
STARGWENT - GALACTIC CONQUEST - Meta-Progression System

Persistent unlocks and high scores across campaign runs.
Earn Conquest Points (CP) from completing campaigns, conquering homeworlds,
and finishing story arcs. Spend CP to unlock permanent perks.
"""

import json
import os

from save_paths import get_data_dir, sync_saves

META_SAVE_FILENAME = "conquest_meta.json"
HIGH_SCORES_FILENAME = "conquest_high_scores.json"

# Conquest Point awards
CP_VICTORY = 50
CP_DEFEAT = 20
CP_PER_HOMEWORLD = 10
CP_PER_ARC = 5
CP_PER_RELIC = 3

# Difficulty multipliers for scoring
DIFFICULTY_MULTIPLIERS = {
    "easy": 0.5,
    "normal": 1.0,
    "hard": 1.5,
    "insane": 2.0,
}


# Unlockable perks
PERKS = {
    "extra_starting_card": {
        "name": "Extra Starting Card",
        "description": "+1 card in starting deck for all campaigns",
        "cost": 10,
        "icon": "\u2660",
    },
    "naquadah_boost": {
        "name": "Naquadah Boost",
        "description": "+20 starting naquadah for all campaigns",
        "cost": 10,
        "icon": "\u26A1",
    },
    "veteran_recruits": {
        "name": "Veteran Recruits",
        "description": "+1 power to all starting deck cards",
        "cost": 15,
        "icon": "\u2694",
    },
    "diplomatic_immunity": {
        "name": "Diplomatic Immunity",
        "description": "First counterattack each campaign automatically fails",
        "cost": 15,
        "icon": "\u2696",
    },
    "ancient_knowledge": {
        "name": "Ancient Knowledge",
        "description": "Start with a random relic on 3rd+ campaign",
        "cost": 20,
        "icon": "\u2261",
    },
}


def _get_meta_path():
    return os.path.join(get_data_dir(), META_SAVE_FILENAME)


def _get_high_scores_path():
    return os.path.join(get_data_dir(), HIGH_SCORES_FILENAME)


def load_meta() -> dict:
    """Load meta-progression data. Returns defaults if no file exists."""
    defaults = {
        "total_cp": 0,
        "unlocked_perks": [],
        "campaigns_played": 0,
        "campaigns_won": 0,
    }
    path = _get_meta_path()
    if not os.path.exists(path):
        return defaults
    try:
        with open(path, "r") as f:
            data = json.load(f)
        for k, v in defaults.items():
            data.setdefault(k, v)
        return data
    except (IOError, json.JSONDecodeError):
        return defaults


def save_meta(meta: dict) -> bool:
    """Save meta-progression data to disk."""
    path = _get_meta_path()
    try:
        with open(path, "w") as f:
            json.dump(meta, f, indent=2)
        sync_saves()
        return True
    except (IOError, OSError):
        return False


def load_high_scores() -> list:
    """Load high scores list. Returns empty list if no file."""
    path = _get_high_scores_path()
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (IOError, json.JSONDecodeError):
        return []


def save_high_scores(scores: list) -> bool:
    """Save high scores to disk. Keeps top 10."""
    scores = sorted(scores, key=lambda s: s.get("score", 0), reverse=True)[:10]
    path = _get_high_scores_path()
    try:
        with open(path, "w") as f:
            json.dump(scores, f, indent=2)
        sync_saves()
        return True
    except (IOError, OSError):
        return False


def calculate_run_score(campaign_state, galaxy, outcome):
    """Calculate the final score for a campaign run.

    Args:
        campaign_state: CampaignState at end of run
        galaxy: GalaxyMap at end of run
        outcome: "victory" or "defeat"

    Returns:
        dict with {score, breakdown, cp_earned}
    """
    breakdown = {}

    # Base score from outcome
    base = 500 if outcome == "victory" else 100
    breakdown["outcome"] = base

    # Planets controlled
    player_planets = sum(1 for p in galaxy.planets.values() if p.owner == "player")
    planet_score = player_planets * 20
    breakdown["planets"] = planet_score

    # Relics collected
    relic_score = len(campaign_state.relics) * 15
    breakdown["relics"] = relic_score

    # Arcs completed
    arcs_complete = 0
    for arc_id, progress in campaign_state.narrative_progress.items():
        from .narrative_arcs import NARRATIVE_ARCS
        arc = NARRATIVE_ARCS.get(arc_id)
        if arc and len(progress) >= len(arc.required_planets):
            arcs_complete += 1
    arc_score = arcs_complete * 30
    breakdown["arcs"] = arc_score

    # Turn penalty (fewer turns = better)
    turn_penalty = min(200, campaign_state.turn_number * 3)
    breakdown["turn_penalty"] = -turn_penalty

    # Naquadah bonus
    naq_bonus = campaign_state.naquadah // 10
    breakdown["naquadah"] = naq_bonus

    # Raw score
    raw = base + planet_score + relic_score + arc_score - turn_penalty + naq_bonus

    # Difficulty multiplier
    multiplier = DIFFICULTY_MULTIPLIERS.get(campaign_state.difficulty, 1.0)
    final_score = max(0, int(raw * multiplier))
    breakdown["multiplier"] = multiplier

    # CP earned
    cp = CP_VICTORY if outcome == "victory" else CP_DEFEAT
    # Homeworlds captured
    homeworlds = sum(1 for p in galaxy.planets.values()
                     if p.planet_type == "homeworld" and p.owner == "player"
                     and p.faction != campaign_state.player_faction)
    cp += homeworlds * CP_PER_HOMEWORLD
    cp += arcs_complete * CP_PER_ARC
    cp += len(campaign_state.relics) * CP_PER_RELIC

    return {
        "score": final_score,
        "breakdown": breakdown,
        "cp_earned": cp,
    }


def award_cp(cp_amount):
    """Award Conquest Points to the meta-progression pool."""
    meta = load_meta()
    meta["total_cp"] = meta.get("total_cp", 0) + cp_amount
    save_meta(meta)
    return meta["total_cp"]


def record_campaign_end(outcome):
    """Record that a campaign was played (and possibly won)."""
    meta = load_meta()
    meta["campaigns_played"] = meta.get("campaigns_played", 0) + 1
    if outcome == "victory":
        meta["campaigns_won"] = meta.get("campaigns_won", 0) + 1
    save_meta(meta)


def add_high_score(campaign_state, score_data):
    """Add a high score entry.

    Args:
        campaign_state: CampaignState
        score_data: dict from calculate_run_score()
    """
    scores = load_high_scores()
    leader_name = campaign_state.player_leader.get("name", "Unknown") if campaign_state.player_leader else "Unknown"
    entry = {
        "score": score_data["score"],
        "faction": campaign_state.player_faction,
        "leader": leader_name,
        "difficulty": campaign_state.difficulty,
        "turns": campaign_state.turn_number,
        "cp_earned": score_data["cp_earned"],
    }
    scores.append(entry)
    save_high_scores(scores)


def unlock_perk(perk_id):
    """Attempt to unlock a perk. Returns (success, message)."""
    if perk_id not in PERKS:
        return False, "Unknown perk."
    meta = load_meta()
    if perk_id in meta.get("unlocked_perks", []):
        return False, "Already unlocked."
    cost = PERKS[perk_id]["cost"]
    if meta.get("total_cp", 0) < cost:
        return False, f"Need {cost} CP (have {meta.get('total_cp', 0)})."
    meta["total_cp"] -= cost
    meta.setdefault("unlocked_perks", []).append(perk_id)
    save_meta(meta)
    return True, f"Unlocked: {PERKS[perk_id]['name']}!"


def has_perk(perk_id):
    """Check if a perk is unlocked."""
    meta = load_meta()
    return perk_id in meta.get("unlocked_perks", [])


def get_all_perks_display():
    """Get perk display data for the unlocks screen.

    Returns list of (perk_id, name, description, cost, icon, is_unlocked).
    """
    meta = load_meta()
    unlocked = meta.get("unlocked_perks", [])
    result = []
    for pid, perk in PERKS.items():
        result.append((
            pid,
            perk["name"],
            perk["description"],
            perk["cost"],
            perk["icon"],
            pid in unlocked,
        ))
    return result


def apply_meta_perks_to_campaign(campaign_state):
    """Apply unlocked meta-progression perks to a new campaign state.

    Call this during campaign startup after CampaignState is created.
    """
    meta = load_meta()
    unlocked = meta.get("unlocked_perks", [])

    if "naquadah_boost" in unlocked:
        campaign_state.add_naquadah(20)

    if "extra_starting_card" in unlocked:
        # Add an extra random card from player faction
        from cards import ALL_CARDS
        faction_pool = [cid for cid, c in ALL_CARDS.items()
                        if getattr(c, 'faction', None) == campaign_state.player_faction
                        and getattr(c, 'card_type', '') != "Legendary Commander"
                        and getattr(c, 'row', '') != "weather"]
        if faction_pool:
            import random
            campaign_state.add_card(random.choice(faction_pool))

    if "veteran_recruits" in unlocked:
        # +1 power to all starting cards
        seen = set()
        for cid in campaign_state.current_deck:
            if cid not in seen:
                campaign_state.upgrade_card(cid, 1)
                seen.add(cid)

    if "ancient_knowledge" in unlocked:
        # Start with a random relic on 3rd+ campaign
        if meta.get("campaigns_played", 0) >= 2:
            from .relics import RELICS
            import random
            available = [rid for rid in RELICS if rid not in campaign_state.relics]
            if available:
                campaign_state.add_relic(random.choice(available))

    # diplomatic_immunity is checked at counterattack time in campaign_controller
