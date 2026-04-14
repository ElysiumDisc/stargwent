"""
STARGWENT - GALACTIC CONQUEST - Activity Log (12.0 Pillar 3e)

A structured, persistent log of notable events that happen during a
campaign run: your attacks, AI counterattacks, faction-vs-faction wars,
diplomatic shifts, crisis outcomes, leader action uses, rival arc
advances.

The current 11.0 flash-message system is ephemeral and blocks the event
loop with ``pygame.time.wait()``. Activity log is the durable
replacement: entries are appended non-blockingly, persisted in
``CampaignState.activity_log``, and rendered in a right-edge slide-out
sidebar (UI sidebar lives in ``map_renderer.py`` — this module is just
the data layer).

Entry schema::

    {
        "turn":     int,               # turn the event occurred
        "category": str,               # see CATEGORIES below
        "text":     str,               # short human-readable line
        "icon":     str | None,        # optional glyph key for sidebar
        "faction":  str | None,        # faction most associated, for color
        "planet":   str | None,        # planet_id for click-to-focus
    }

Categories are soft (just strings) but this module exposes constants
for the known ones so callers don't typo.  The UI uses the category to
pick a color and icon.
"""

from dataclasses import dataclass


# --- Category constants ---------------------------------------------------
# Using strings (not Enum) to keep saves plain-JSON-serializable.
CAT_BATTLE = "battle"
CAT_COUNTERATTACK = "counterattack"
CAT_AI_WAR = "ai_war"
CAT_DIPLOMACY = "diplomacy"
CAT_CRISIS = "crisis"
CAT_LEADER_ACTION = "leader_action"
CAT_RIVAL_ARC = "rival_arc"
CAT_ECONOMY = "economy"
CAT_DISCOVERY = "discovery"
CAT_SYSTEM = "system"


# Cap to keep saves bounded. A 50-turn run typically produces ~100-200
# entries; 400 gives headroom for long campaigns without save bloat.
MAX_LOG_ENTRIES = 400


@dataclass
class LogEntry:
    """Typed view on a log entry. Stored as a dict in state for JSON ease."""
    turn: int
    category: str
    text: str
    icon: str = ""
    faction: str = ""
    planet: str = ""

    def to_dict(self) -> dict:
        return {
            "turn": self.turn,
            "category": self.category,
            "text": self.text,
            "icon": self.icon,
            "faction": self.faction,
            "planet": self.planet,
        }


def log(state, category: str, text: str, *,
        icon: str = "", faction: str = "", planet: str = "") -> None:
    """Append an entry to the campaign activity log.

    Always safe to call. If *state* has no ``activity_log`` attribute
    (pre-12 state somehow leaked through), silently no-ops.
    """
    if not hasattr(state, "activity_log"):
        return
    entry = LogEntry(
        turn=getattr(state, "turn_number", 0),
        category=category,
        text=text,
        icon=icon,
        faction=faction,
        planet=planet,
    ).to_dict()
    state.activity_log.append(entry)
    # Drop oldest entries once past cap. Using slice assignment keeps
    # the list identity stable in case something else holds a reference.
    excess = len(state.activity_log) - MAX_LOG_ENTRIES
    if excess > 0:
        del state.activity_log[:excess]


def recent(state, count: int = 10) -> list:
    """Return the most recent *count* entries (newest last)."""
    if not hasattr(state, "activity_log"):
        return []
    return state.activity_log[-count:]


def entries_for_turn(state, turn: int) -> list:
    """Return all entries logged during a specific turn."""
    if not hasattr(state, "activity_log"):
        return []
    return [e for e in state.activity_log if e.get("turn") == turn]


def entries_by_category(state, category: str, count: int | None = None) -> list:
    """Return entries filtered by category (newest last)."""
    if not hasattr(state, "activity_log"):
        return []
    matches = [e for e in state.activity_log if e.get("category") == category]
    if count is not None:
        matches = matches[-count:]
    return matches


def clear(state) -> None:
    """Wipe the activity log. Used when starting a fresh campaign."""
    if hasattr(state, "activity_log"):
        state.activity_log.clear()
