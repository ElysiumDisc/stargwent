"""
STARGWENT - GALACTIC CONQUEST - Rival Leader Arcs (12.0 Pillar 2)

When a player defeats a rival leader in their homeworld battle, they
don't just disappear — they become a persistent antagonist haunting
the rest of the run.

### Phases

1. ``EXILE``      — 1-3 turns.  Rival flees.  Ghost icon on a random
                    neutral/friendly planet.  No direct effect yet.
2. ``GUERRILLA``  — 3-5 turns.  Rival raids your planets with
                    weakened faction-themed decks.  Declining a raid
                    costs -1 fort on a random owned planet.
3. ``RESURGENCE`` — fires when the arc has run 8+ turns total.  Rival
                    reclaims a neutral planet as a new capital and
                    becomes a minor power on the map.
4. ``SHOWDOWN``   — scripted climactic battle with custom deck.
                    Player victory = unique trophy; loss = arc
                    reopens at EXILE with +1 difficulty.
5. ``RESOLVED``   — arc over, rival permanently defeated OR won.

### Scripted pairs (Sprint 4, shipped in 12.0)

- O'Neill vs Apophis
- Teal'c vs Ba'al
- Catherine Langford vs Anubis
- Merlin vs Adria

Other pairs fall back to ``GENERIC_ARC`` with procedural flavor keyed
on faction pair.  All four scripted pairs reuse ``LEADER_MATCHUPS``
entries in ``leader_matchup.py`` for dialogue — this module only
stores arc *state*, not script content.

### Sprint 1 scope

Dataclass, phase constants, spawn hook, turn-tick advancer, and a
stubbed generic arc.  Scripted scripts + UI + actual raid battles
arrive in Sprint 4.
"""

from __future__ import annotations

import random

from . import activity_log


# --- Phase constants ------------------------------------------------------

PHASE_EXILE = "exile"
PHASE_GUERRILLA = "guerrilla"
PHASE_RESURGENCE = "resurgence"
PHASE_SHOWDOWN = "showdown"
PHASE_RESOLVED = "resolved"


# Minimum turns to spend in each phase before advancement is checked.
# Keeps arcs from blasting through stages in a single AI counterattack
# burst.  Tunable per scripted pair later.
PHASE_DURATIONS = {
    PHASE_EXILE: 2,
    PHASE_GUERRILLA: 4,
    PHASE_RESURGENCE: 3,
}


# --- Scripted pair registry ----------------------------------------------
# Keys are ``(player_card_id, rival_card_id)`` tuples.  When a scripted
# pair fires, its dict overrides the generic arc in the places listed.
# Sprint 4 will flesh these out; Sprint 1 just records the slots.

SCRIPTED_ARCS: dict[tuple[str, str], dict] = {
    ("tauri_oneill", "goauld_apophis"): {
        "name": "Jack vs Apophis",
        "tagline": "You're not getting rid of me that easily, O'Neill.",
    },
    ("jaffa_tealc", "goauld_baal"): {
        "name": "Shol'va's Hunt",
        "tagline": "Every clone I destroy, another takes its place.",
    },
    ("tauri_langford", "goauld_anubis"): {
        "name": "Light and Shadow",
        "tagline": "The Ancients' light cannot banish what they themselves became.",
    },
    ("alteran_merlin", "alteran_adria"): {
        "name": "Sangraal",
        "tagline": "The Ori cannot be reasoned with. Only unmade.",
    },
}


# --- Spawn & advance ------------------------------------------------------

def _scripted_key(state, rival_card_id: str) -> tuple[str, str]:
    player_card_id = (state.player_leader or {}).get("card_id", "")
    return (player_card_id, rival_card_id)


def _pick_hideout(state, galaxy, rng) -> str | None:
    """Choose a neutral or friendly-faction planet for the rival to flee to.

    Preference order:
      1. Neutral planets (most lore-flavored — rebel cell in a frontier
         outpost);
      2. Player-controlled planets *without* fortification (they slip
         through a lightly defended outpost);
      3. Any remaining planet except homeworlds.

    Returns a ``planet_id`` or ``None`` if nothing fits.
    """
    neutral = [pid for pid, p in galaxy.planets.items()
               if p.owner == "neutral" and p.planet_type != "homeworld"]
    if neutral:
        return rng.choice(neutral)
    unfortified = [pid for pid, p in galaxy.planets.items()
                   if p.owner == "player"
                   and p.planet_type != "homeworld"
                   and state.fortification_levels.get(pid, 0) == 0]
    if unfortified:
        return rng.choice(unfortified)
    fallback = [pid for pid, p in galaxy.planets.items()
                if p.planet_type != "homeworld"]
    return rng.choice(fallback) if fallback else None


def spawn_on_homeworld_capture(state, galaxy, defeated_faction: str,
                                rival_leader: dict) -> None:
    """Create a new rival arc after the player captures a homeworld.

    Skips if:
      - ``rival_leader`` has no ``card_id`` (fallback/AI random)
      - the player already has an active arc against this rival
        (covers weird re-capture edge cases)
    """
    if not rival_leader:
        return
    rival_card_id = rival_leader.get("card_id", "")
    if not rival_card_id:
        return

    # One arc per rival at a time.
    for arc in state.rival_arcs:
        if arc.get("rival_card_id") == rival_card_id and arc.get("phase") != PHASE_RESOLVED:
            return

    scripted = SCRIPTED_ARCS.get(_scripted_key(state, rival_card_id))
    # Seed a fresh RNG from the turn + rival id so hideout choice is
    # deterministic (useful for testing and replays).
    rng = random.Random(
        hash((state.turn_number, rival_card_id)) & 0xFFFFFFFF)
    hideout = _pick_hideout(state, galaxy, rng)
    arc = {
        "rival_card_id": rival_card_id,
        "rival_name": rival_leader.get("name", "Rival"),
        "rival_faction": defeated_faction,
        "phase": PHASE_EXILE,
        "turn_started": getattr(state, "turn_number", 0),
        "phase_turn": 0,                 # turns spent in current phase
        "hideout_planet_id": hideout,
        "raid_count": 0,                 # guerrilla raids launched
        "scripted": bool(scripted),
        "script_name": scripted["name"] if scripted else None,
        "difficulty_tier": 0,            # +1 each time a showdown is lost
    }
    state.rival_arcs.append(arc)

    tagline = (scripted or {}).get("tagline", "")
    hideout_name = (galaxy.planets[hideout].name
                    if hideout and hideout in galaxy.planets else "parts unknown")
    activity_log.log(
        state,
        activity_log.CAT_RIVAL_ARC,
        f"{arc['rival_name']} has fled to {hideout_name}. {tagline}".strip(),
        icon="rival",
        faction=defeated_faction,
        planet=hideout or "",
    )


def advance_all(state, galaxy, rng) -> list[str]:
    """Tick every active rival arc one turn.  Returns flash messages.

    Called from ``campaign_controller`` during the end-of-turn phase.
    Each arc may transition phases or trigger a side effect (fort loss
    from declined raid, capital seizure, etc.).

    For Sprint 1 this only advances phase counters; raid battles,
    resurgence-planet seizure, and the final showdown are wired in
    Sprint 4.
    """
    messages = []
    for arc in state.rival_arcs:
        if arc.get("phase") == PHASE_RESOLVED:
            continue
        arc["phase_turn"] = arc.get("phase_turn", 0) + 1
        msg = _maybe_advance_phase(arc, state, galaxy, rng)
        if msg:
            messages.append(msg)
    return messages


def _maybe_advance_phase(arc: dict, state, galaxy, rng) -> str | None:
    """Move an arc to its next phase if dwell time is met.

    Returns a short player-facing message when a transition fires.
    """
    phase = arc.get("phase")
    dwell = PHASE_DURATIONS.get(phase, 0)
    if arc["phase_turn"] < dwell:
        return None

    if phase == PHASE_EXILE:
        arc["phase"] = PHASE_GUERRILLA
        arc["phase_turn"] = 0
        text = f"{arc['rival_name']} is staging guerrilla raids."
        activity_log.log(state, activity_log.CAT_RIVAL_ARC, text,
                         icon="rival", faction=arc["rival_faction"])
        return text

    if phase == PHASE_GUERRILLA:
        arc["phase"] = PHASE_RESURGENCE
        arc["phase_turn"] = 0
        text = f"{arc['rival_name']} has reclaimed a foothold in the galaxy."
        activity_log.log(state, activity_log.CAT_RIVAL_ARC, text,
                         icon="rival", faction=arc["rival_faction"])
        return text

    if phase == PHASE_RESURGENCE:
        arc["phase"] = PHASE_SHOWDOWN
        arc["phase_turn"] = 0
        text = f"{arc['rival_name']} challenges you to a final reckoning."
        activity_log.log(state, activity_log.CAT_RIVAL_ARC, text,
                         icon="rival", faction=arc["rival_faction"])
        return text

    # SHOWDOWN resolution is a Sprint 4 concern — player must accept
    # and fight a scripted battle.  Nothing auto-advances here.
    return None


def get_active_arcs(state) -> list[dict]:
    """Return arcs that are not yet resolved.  Used by UI & map icons."""
    return [a for a in getattr(state, "rival_arcs", [])
            if a.get("phase") != PHASE_RESOLVED]


def pending_showdowns(state) -> list[dict]:
    """Every SHOWDOWN-phase arc the player hasn't yet engaged.

    Called after ``advance_all`` on end-of-turn.  Returns any
    unresolved SHOWDOWN arcs — a player who ``Defer``'d last turn will
    be prompted again, because a rival who has emerged keeps demanding
    a reckoning until it's dealt with one way or the other.
    """
    return [a for a in getattr(state, "rival_arcs", [])
            if a.get("phase") == PHASE_SHOWDOWN]


def resolve(state, arc: dict, *, player_won: bool) -> None:
    """Mark an arc resolved after a showdown battle."""
    arc["phase"] = PHASE_RESOLVED
    arc["resolved_on_turn"] = getattr(state, "turn_number", 0)
    arc["player_won"] = bool(player_won)
    outcome = "destroyed" if player_won else "triumphed"
    activity_log.log(
        state,
        activity_log.CAT_RIVAL_ARC,
        f"{arc['rival_name']} was {outcome} in the final showdown.",
        icon="rival",
        faction=arc.get("rival_faction", ""),
    )


def rearm_after_loss(state, galaxy, arc: dict, rng) -> None:
    """Reset a losing arc to EXILE with a tougher tier.

    If the player loses a showdown, the rival slips away with
    renewed resolve: ``difficulty_tier`` increments (so the next
    showdown's card battle gets +1/+2/+3 power buff stacked) and the
    arc re-rolls a hideout.
    """
    arc["phase"] = PHASE_EXILE
    arc["phase_turn"] = 0
    arc["difficulty_tier"] = min(3, arc.get("difficulty_tier", 0) + 1)
    arc["hideout_planet_id"] = _pick_hideout(state, galaxy, rng)
    hideout_name = "parts unknown"
    if arc["hideout_planet_id"] in galaxy.planets:
        hideout_name = galaxy.planets[arc["hideout_planet_id"]].name
    activity_log.log(
        state,
        activity_log.CAT_RIVAL_ARC,
        f"{arc['rival_name']} escapes to {hideout_name}, hatred fermenting.",
        icon="rival",
        faction=arc.get("rival_faction", ""),
        planet=arc.get("hideout_planet_id", ""),
    )
