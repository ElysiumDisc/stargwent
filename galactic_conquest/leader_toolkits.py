"""
STARGWENT - GALACTIC CONQUEST - Leader Toolkits (12.0 Pillar 1)

The core thesis of 12.0: every leader gets 2-3 *active* abilities they
can employ on the galactic map — not just passive triggers that fire on
battle hooks.  Playing O'Neill should feel tactically different from
playing Apophis even before the cards hit the table.

This module is the data layer and dispatcher.  UI (the "Leader
Command" panel on the map HUD) lives in ``map_renderer.py``.

### Shape

- ``LeaderAction``  — one button on the Command panel.
- ``ACTION_TEMPLATES`` section  — small reusable handler factories.
  Each factory returns a closure suitable for the ``handler`` field.
- ``LEADER_ACTIONS``  — ``card_id → list[LeaderAction]`` registry,
  covering all 40 leaders with 2-3 actions each, 100+ buttons total.

### Handler side effects

Handlers mutate ``state`` directly.  For effects that are *scheduled*
rather than immediate (e.g. "next battle, reveal opponent's top 3
cards"), we write a sentinel key into
``state.conquest_ability_data``.  Downstream systems (battle setup,
counterattack phase, reward screen) check for the key and apply the
effect.  Keeping the sentinels in one dict avoids sprawling new
fields across the controller.

### Runtime flow

1. UI queries ``list_actions(state)`` to render the panel.
2. User clicks a button.  UI calls ``can_use(state, galaxy, action_id)``
   to validate (naq cost, cooldown, charges, predicate).
3. If valid, UI resolves the ``target_kind`` (own/enemy planet,
   faction) and calls ``execute(state, galaxy, action_id, target, rng)``.
4. Dispatcher debits cost, trips cooldown, consumes a charge, invokes
   the handler, and appends an ``activity_log`` entry.
5. ``tick_cooldowns(state)`` runs once per turn end (wired in
   ``campaign_controller``).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional
import random

from . import activity_log


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class LeaderAction:
    """A single player-initiated map action available to one leader."""
    id: str
    name: str
    description: str
    cost_naq: int = 0
    cooldown_turns: int = 0
    charges: Optional[int] = None
    target_kind: str = "none"        # none / own_planet / enemy_planet / any_planet / faction
    predicate: Optional[Callable] = None
    handler: Optional[Callable] = None


# ---------------------------------------------------------------------------
# Per-action runtime state
# ---------------------------------------------------------------------------

def _get_action_state(state, action_id: str) -> dict:
    store = state.leader_action_state
    if action_id not in store:
        store[action_id] = {"cooldown": 0, "charges_used": 0}
    return store[action_id]


def _charges_remaining(action: LeaderAction, astate: dict) -> Optional[int]:
    if action.charges is None:
        return None
    return max(0, action.charges - astate.get("charges_used", 0))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def list_actions(state) -> list:
    """Return the ``LeaderAction`` list for the player's current leader.

    Empty list if the leader has no registered toolkit.
    """
    leader = getattr(state, "player_leader", None) or {}
    card_id = leader.get("card_id", "")
    return list(LEADER_ACTIONS.get(card_id, ()))


def get_action(state, action_id: str) -> Optional[LeaderAction]:
    for a in list_actions(state):
        if a.id == action_id:
            return a
    return None


def can_use(state, galaxy, action_id: str) -> tuple[bool, str]:
    """Check whether an action is usable right now.

    Returns ``(ok, reason)``.  ``reason`` is a short player-facing
    explanation when ``ok`` is False.
    """
    action = get_action(state, action_id)
    if action is None:
        return False, "Unknown action"

    astate = _get_action_state(state, action_id)
    if astate.get("cooldown", 0) > 0:
        return False, f"Cooldown: {astate['cooldown']} turn(s)"

    remaining = _charges_remaining(action, astate)
    if remaining is not None and remaining <= 0:
        return False, "No charges remaining"

    if action.cost_naq and state.naquadah < action.cost_naq:
        return False, f"Need {action.cost_naq - state.naquadah} more naquadah"

    if action.predicate and not action.predicate(state, galaxy):
        return False, "Not available right now"

    return True, ""


def execute(state, galaxy, action_id: str, target=None, rng=None) -> Optional[str]:
    """Run a leader action.  Returns activity-log text or ``None``."""
    action = get_action(state, action_id)
    if action is None or action.handler is None:
        return None

    if action.cost_naq:
        state.add_naquadah(-action.cost_naq)

    astate = _get_action_state(state, action_id)
    if action.cooldown_turns:
        astate["cooldown"] = action.cooldown_turns
    if action.charges is not None:
        astate["charges_used"] = astate.get("charges_used", 0) + 1

    rng = rng or random
    text = action.handler(state, galaxy, target, rng)

    leader_name = (getattr(state, "player_leader", None) or {}).get("name", "Leader")
    activity_log.log(
        state,
        activity_log.CAT_LEADER_ACTION,
        text or f"{leader_name} used {action.name}",
        icon="action",
        faction=getattr(state, "player_faction", ""),
    )
    return text


def tick_cooldowns(state) -> None:
    """Decrement every leader action's cooldown by 1.  Call on turn end."""
    for astate in state.leader_action_state.values():
        if astate.get("cooldown", 0) > 0:
            astate["cooldown"] -= 1


# ===========================================================================
# Shared helpers
# ===========================================================================

def _card_name(cid):
    from cards import ALL_CARDS
    c = ALL_CARDS.get(cid)
    return c.name if c else cid


def _upgradeable_cards(state):
    from cards import ALL_CARDS
    return [cid for cid in state.current_deck
            if ALL_CARDS.get(cid) and getattr(ALL_CARDS[cid], 'power', None)]


def _planet_name(galaxy, pid):
    return galaxy.planets[pid].name if pid in galaxy.planets else str(pid)


def _any_owned_planet(state):
    return [pid for pid, owner in state.planet_ownership.items() if owner == "player"]


def _any_non_player_planet(galaxy):
    return [pid for pid, p in galaxy.planets.items() if p.owner not in ("player", "neutral")]


def _any_enemy_faction(state, galaxy):
    factions = set()
    for p in galaxy.planets.values():
        if p.owner not in ("player", "neutral", state.friendly_faction):
            factions.add(p.owner)
    return sorted(factions)


def _set_flag(state, key, value=True):
    """Write a sentinel into conquest_ability_data so other systems honour it."""
    state.conquest_ability_data[key] = value


def _incr_flag(state, key, amount=1):
    state.conquest_ability_data[key] = state.conquest_ability_data.get(key, 0) + amount


# ===========================================================================
# Action template factories
# ===========================================================================
# Each factory returns a handler closure with signature
#   (state, galaxy, target, rng) -> str | None

def T_naq_grant(amount: int, flavor: str):
    def _h(state, galaxy, target, rng):
        state.add_naquadah(amount)
        return f"{flavor}: +{amount} naquadah."
    return _h


def T_wisdom_grant(amount: int, flavor: str):
    def _h(state, galaxy, target, rng):
        state.wisdom += amount
        return f"{flavor}: +{amount} wisdom."
    return _h


def T_clear_longest_cooldown(flavor: str):
    def _h(state, galaxy, target, rng):
        if not state.cooldowns:
            return f"{flavor}: nothing to fix."
        pid = max(state.cooldowns, key=lambda k: state.cooldowns[k])
        name = _planet_name(galaxy, pid)
        del state.cooldowns[pid]
        return f"{flavor}: cooldown at {name} lifted."
    return _h


def T_clear_all_cooldowns(flavor: str):
    def _h(state, galaxy, target, rng):
        count = len(state.cooldowns)
        state.cooldowns.clear()
        return f"{flavor}: cleared {count} cooldowns."
    return _h


def T_cancel_next_counterattack(flavor: str):
    """Target = faction name.  Honoured by controller counterattack loop."""
    def _h(state, galaxy, target, rng):
        if not target:
            return f"{flavor}: no target."
        blocks = state.conquest_ability_data.setdefault("sg1_strike_block", {})
        blocks[target] = blocks.get(target, 0) + 1
        return f"{flavor}: {target}'s next counterattack neutralised."
    return _h


def T_fort_free(flavor: str, cap: int = 3):
    """Target = owned planet.  Instantly +1 fort (capped)."""
    def _h(state, galaxy, target, rng):
        if not target:
            return f"{flavor}: no target."
        cur = state.fortification_levels.get(target, 0)
        if cur >= cap:
            return f"{flavor}: {_planet_name(galaxy, target)} already fortified to {cap}."
        state.fortification_levels[target] = cur + 1
        return f"{flavor}: +1 fortification at {_planet_name(galaxy, target)}."
    return _h


def T_abandon_refund(flavor: str):
    """Target = owned planet.  Transfer to neutral; refund 20 naq per fort."""
    def _h(state, galaxy, target, rng):
        if not target or state.planet_ownership.get(target) != "player":
            return f"{flavor}: no target."
        fort = state.fortification_levels.pop(target, 0)
        refund = 20 + fort * 20
        state.add_naquadah(refund)
        galaxy.transfer_ownership(target, "neutral")
        state.planet_ownership[target] = "neutral"
        return f"{flavor}: {_planet_name(galaxy, target)} evacuated (+{refund} naq)."
    return _h


def T_upgrade_random(count: int, flavor: str):
    def _h(state, galaxy, target, rng):
        cards = _upgradeable_cards(state)
        if not cards:
            return f"{flavor}: no upgradeable cards."
        picks = rng.sample(cards, min(count, len(cards)))
        for cid in picks:
            state.upgrade_card(cid, 1)
        return f"{flavor}: upgraded " + ", ".join(_card_name(c) for c in picks) + "."
    return _h


def T_upgrade_strongest(count: int, flavor: str, bonus: int = 1):
    def _h(state, galaxy, target, rng):
        from cards import ALL_CARDS
        cards = _upgradeable_cards(state)
        if not cards:
            return f"{flavor}: no upgradeable cards."
        cards.sort(key=lambda c: getattr(ALL_CARDS[c], 'power', 0), reverse=True)
        picks = cards[:count]
        for cid in picks:
            state.upgrade_card(cid, bonus)
        return f"{flavor}: +{bonus} to " + ", ".join(_card_name(c) for c in picks) + "."
    return _h


def T_remove_weakest(flavor: str):
    def _h(state, galaxy, target, rng):
        from cards import ALL_CARDS
        cards = _upgradeable_cards(state)
        if not cards:
            return f"{flavor}: no removable cards."
        cards.sort(key=lambda c: getattr(ALL_CARDS[c], 'power', 0))
        victim = cards[0]
        state.remove_card(victim)
        return f"{flavor}: purged {_card_name(victim)}."
    return _h


def T_favor_shift(delta: int, flavor: str):
    """Target = faction name.  Shift diplomatic favor."""
    def _h(state, galaxy, target, rng):
        if not target:
            return f"{flavor}: no target."
        cur = state.diplomatic_favor.get(target, 0)
        state.diplomatic_favor[target] = max(-100, min(100, cur + delta))
        sign = "+" if delta >= 0 else ""
        return f"{flavor}: {sign}{delta} favor with {target}."
    return _h


def T_reveal_enemy_hand(flavor: str):
    """Target = faction.  Next battle vs faction shows opponent intel."""
    def _h(state, galaxy, target, rng):
        if not target:
            return f"{flavor}: no target."
        state.conquest_ability_data.setdefault("enemy_intel_factions", {})[target] = 1
        # Also bumps generic pre-battle intel for the next battle.
        _incr_flag(state, "next_battle_intel_count", 3)
        return f"{flavor}: {target}'s next deck will be revealed."
    return _h


def T_skip_crisis(flavor: str):
    def _h(state, galaxy, target, rng):
        state.crisis_cooldown = max(state.crisis_cooldown, 3)
        state.pending_crisis = {}
        return f"{flavor}: crisis suppressed for 3 turns."
    return _h


def T_fake_identity(turns: int, flavor: str):
    """Makes AI treat player as neutral for N turns (reduces counterattacks)."""
    def _h(state, galaxy, target, rng):
        _incr_flag(state, "fake_identity_turns", turns)
        return f"{flavor}: masquerade active for {turns} turns."
    return _h


def T_spawn_operative(flavor: str):
    def _h(state, galaxy, target, rng):
        op_id = state.operative_next_id
        state.operative_next_id += 1
        state.operatives.append({
            "id": op_id,
            "planet_id": None,
            "mission": None,
            "turns_remaining": 0,
            "status": "idle",
        })
        return f"{flavor}: new operative recruited."
    return _h


def T_grant_relic(relic_id: str, flavor: str):
    def _h(state, galaxy, target, rng):
        if state.has_relic(relic_id):
            # Refund the charge expenditure implicitly by leaving flavor.
            return f"{flavor}: relic already owned."
        state.add_relic(relic_id)
        return f"{flavor}: relic {relic_id} acquired."
    return _h


def T_sabotage_building(flavor: str):
    """Target = enemy planet with a building."""
    def _h(state, galaxy, target, rng):
        if not target or target not in state.buildings:
            return f"{flavor}: no building to sabotage."
        b_type = state.buildings.pop(target)
        state.building_levels.pop(target, None)
        return f"{flavor}: destroyed {b_type} at {_planet_name(galaxy, target)}."
    return _h


def T_enable_two_hop(flavor: str):
    """Next attack may target a 2-hop planet."""
    def _h(state, galaxy, target, rng):
        _incr_flag(state, "two_hop_attack_charges", 1)
        return f"{flavor}: your next attack may reach a distant planet."
    return _h


def T_force_nap(turns: int, flavor: str):
    """Target = faction.  Force a one-sided NAP treaty."""
    def _h(state, galaxy, target, rng):
        if not target:
            return f"{flavor}: no target."
        state.treaties.append({
            "type": "nap",
            "faction": target,
            "turns_remaining": turns,
            "signed_on_turn": state.turn_number,
            "penalty_if_broken": 30,
        })
        return f"{flavor}: NAP with {target} for {turns} turns."
    return _h


def T_undo_last_loss(flavor: str):
    """Restore the most recent lost planet."""
    def _h(state, galaxy, target, rng):
        last = state.conquest_ability_data.get("_last_planet_lost")
        if not last:
            return f"{flavor}: no recent loss to undo."
        pid = last.get("planet_id")
        if not pid:
            return f"{flavor}: no recent loss to undo."
        galaxy.transfer_ownership(pid, "player")
        state.planet_ownership[pid] = "player"
        state.conquest_ability_data["_last_planet_lost"] = None
        return f"{flavor}: {_planet_name(galaxy, pid)} restored."
    return _h


def T_dispel_coalition(flavor: str):
    def _h(state, galaxy, target, rng):
        if not state.coalition.get("active"):
            return f"{flavor}: no coalition active."
        state.coalition["active"] = False
        state.coalition["members"] = []
        state.coalition["turns_remaining"] = 0
        return f"{flavor}: coalition against you has fractured."
    return _h


def T_reveal_operatives(flavor: str):
    def _h(state, galaxy, target, rng):
        _set_flag(state, "operatives_visible_turns", 3)
        return f"{flavor}: all operative activity revealed for 3 turns."
    return _h


def T_income_boost_all(turns: int, flavor: str, amount: int = 10):
    def _h(state, galaxy, target, rng):
        state.conquest_ability_data.setdefault("income_boost", {})
        state.conquest_ability_data["income_boost"] = {
            "turns": turns,
            "amount": amount,
        }
        return f"{flavor}: +{amount} naq/turn for {turns} turns."
    return _h


def T_draw_faction_card(flavor: str):
    """Target = faction.  Add a random card from that faction's pool."""
    def _h(state, galaxy, target, rng):
        if not target:
            return f"{flavor}: no target."
        from cards import ALL_CARDS
        pool = [cid for cid, c in ALL_CARDS.items()
                if getattr(c, 'faction', None) == target and getattr(c, 'power', None)]
        if not pool:
            return f"{flavor}: no cards available."
        cid = rng.choice(pool)
        state.add_card(cid)
        return f"{flavor}: {_card_name(cid)} recruited."
    return _h


def T_trade_income_boost(flavor: str, bonus: int = 30):
    """One-turn naq injection from trade partners."""
    def _h(state, galaxy, target, rng):
        trading = [f for f, r in state.faction_relations.items() if r == "trading"]
        total = bonus * max(1, len(trading))
        state.add_naquadah(total)
        return f"{flavor}: +{total} naq from trade network."
    return _h


def T_convert_minor_world(flavor: str):
    """Target = planet_id of a minor world.  Instantly set to Ally tier."""
    def _h(state, galaxy, target, rng):
        if not target or target not in state.minor_world_states:
            return f"{flavor}: no minor world targeted."
        mw = state.minor_world_states[target]
        if isinstance(mw, dict):
            mw["influence"] = 100
            mw["tier"] = "ally"
        return f"{flavor}: {_planet_name(galaxy, target)} pledged as ally."
    return _h


def T_skip_counterattack_all(flavor: str):
    """One turn of no AI counterattacks from any faction."""
    def _h(state, galaxy, target, rng):
        _set_flag(state, "skip_all_counterattacks", True)
        return f"{flavor}: all counterattacks suppressed this turn."
    return _h


# ---------------------------------------------------------------------------
# Predicates
# ---------------------------------------------------------------------------

def _pred_has_owned_planet(state, galaxy):
    return any(o == "player" for o in state.planet_ownership.values())


def _pred_has_cooldown(state, galaxy):
    return bool(state.cooldowns)


def _pred_has_enemy_faction(state, galaxy):
    return bool(_any_enemy_faction(state, galaxy))


def _pred_has_enemy_building(state, galaxy):
    for pid, _b in state.buildings.items():
        p = galaxy.planets.get(pid)
        if p and p.owner not in ("player", "neutral"):
            return True
    return False


def _pred_has_minor_world(state, galaxy):
    return bool(state.minor_world_states)


def _pred_has_last_loss(state, galaxy):
    last = state.conquest_ability_data.get("_last_planet_lost")
    return bool(last and last.get("planet_id"))


def _pred_coalition_active(state, galaxy):
    return bool(state.coalition.get("active"))


# ===========================================================================
# Per-leader registry (40 leaders × 2-3 actions each)
# ===========================================================================
# Faction flavour motifs:
#   Tau'ri    — tactical & flexible
#   Goa'uld   — coercive & tyrannical
#   Jaffa     — honourable & rebellious
#   Lucian    — opportunistic & economic
#   Asgard    — surgical & technological
#   Alteran   — escalating & metaphysical

LEADER_ACTIONS: dict[str, list] = {

    # ============================= TAU'RI ==================================

    "tauri_oneill": [
        LeaderAction(
            id="tauri_oneill_macgyver", name="MacGyver Protocol",
            description="Instantly clear the longest cooldown on any planet.",
            cost_naq=20, cooldown_turns=4, target_kind="none",
            predicate=_pred_has_cooldown,
            handler=T_clear_longest_cooldown("MacGyver"),
        ),
        LeaderAction(
            id="tauri_oneill_sg1_strike", name="SG-1 Strike",
            description="Cancel the target faction's next counterattack.",
            cost_naq=40, cooldown_turns=5, target_kind="faction",
            predicate=_pred_has_enemy_faction,
            handler=T_cancel_next_counterattack("SG-1 Strike"),
        ),
        LeaderAction(
            id="tauri_oneill_dhd", name="Dial Home Device",
            description="Evacuate an owned planet; refund its fortification.",
            charges=1, target_kind="own_planet",
            predicate=_pred_has_owned_planet,
            handler=T_abandon_refund("DHD"),
        ),
    ],

    "tauri_hammond": [
        LeaderAction(
            id="tauri_hammond_homeworld_defense", name="Homeworld Command",
            description="Grant +1 fortification on any owned planet.",
            cost_naq=30, cooldown_turns=3, target_kind="own_planet",
            predicate=_pred_has_owned_planet,
            handler=T_fort_free("Homeworld Command"),
        ),
        LeaderAction(
            id="tauri_hammond_sgc_briefing", name="SGC Briefing",
            description="Reveal one faction's deck at the next battle.",
            cost_naq=20, cooldown_turns=4, target_kind="faction",
            predicate=_pred_has_enemy_faction,
            handler=T_reveal_enemy_hand("SGC Briefing"),
        ),
    ],

    "tauri_carter": [
        LeaderAction(
            id="tauri_carter_reactor", name="Naquadah Reactor",
            description="Overload a reactor for a surge of naquadah.",
            cooldown_turns=5, target_kind="none",
            handler=T_naq_grant(120, "Naquadah Reactor"),
        ),
        LeaderAction(
            id="tauri_carter_wormhole", name="Wormhole Redirect",
            description="Your next attack may reach a 2-hop planet.",
            cost_naq=30, cooldown_turns=6, target_kind="none",
            handler=T_enable_two_hop("Wormhole Redirect"),
        ),
        LeaderAction(
            id="tauri_carter_diagnostic", name="Gate Diagnostic",
            description="Instantly clear every cooldown.",
            charges=1, target_kind="none",
            predicate=_pred_has_cooldown,
            handler=T_clear_all_cooldowns("Gate Diagnostic"),
        ),
    ],

    "tauri_landry": [
        LeaderAction(
            id="tauri_landry_logistics", name="SGC Logistics",
            description="Lift the longest cooldown in the galaxy.",
            cost_naq=15, cooldown_turns=3, target_kind="none",
            predicate=_pred_has_cooldown,
            handler=T_clear_longest_cooldown("SGC Logistics"),
        ),
        LeaderAction(
            id="tauri_landry_alliance_push", name="Alliance Push",
            description="Improve favor with a faction by +15.",
            cost_naq=40, cooldown_turns=4, target_kind="faction",
            predicate=_pred_has_enemy_faction,
            handler=T_favor_shift(15, "Alliance Push"),
        ),
    ],

    "tauri_mckay": [
        LeaderAction(
            id="tauri_mckay_improvisation", name="Brilliant Improvisation",
            description="Upgrade 2 random cards in your deck.",
            cost_naq=30, cooldown_turns=4, target_kind="none",
            handler=T_upgrade_random(2, "Improvisation"),
        ),
        LeaderAction(
            id="tauri_mckay_purge_weak", name="Purge Inefficient",
            description="Remove your weakest card from the deck.",
            cooldown_turns=5, target_kind="none",
            handler=T_remove_weakest("McKay's Purge"),
        ),
        LeaderAction(
            id="tauri_mckay_zpm", name="ZPM Redirect",
            description="Gain an instant +80 naquadah surge.",
            cooldown_turns=6, target_kind="none",
            handler=T_naq_grant(80, "ZPM Redirect"),
        ),
    ],

    "tauri_quinn": [
        LeaderAction(
            id="tauri_quinn_eidetic", name="Eidetic Memory",
            description="Reveal every card in one faction's deck next battle.",
            cost_naq=20, cooldown_turns=4, target_kind="faction",
            predicate=_pred_has_enemy_faction,
            handler=T_reveal_enemy_hand("Eidetic Memory"),
        ),
        LeaderAction(
            id="tauri_quinn_kelownan_intel", name="Kelownan Intel",
            description="+10 favor with every trading faction via shared intel.",
            cost_naq=30, cooldown_turns=5, target_kind="none",
            handler=lambda s, g, t, r: _trade_favor_boost(s, 10),
        ),
    ],

    "tauri_langford": [
        LeaderAction(
            id="tauri_langford_archaeology", name="Archaeological Find",
            description="Uncover a random relic from the Ancient archives.",
            charges=1, target_kind="none",
            handler=T_grant_relic("ancient_zpm", "Archaeological Find"),
        ),
        LeaderAction(
            id="tauri_langford_repository", name="Ancient Repository",
            description="Upgrade your strongest 2 cards by +2.",
            cost_naq=60, cooldown_turns=6, target_kind="none",
            handler=T_upgrade_strongest(2, "Ancient Repository", bonus=2),
        ),
    ],

    # ============================= GOA'ULD ================================

    "goauld_apophis": [
        LeaderAction(
            id="goauld_apophis_decree", name="System Lord Decree",
            description="Enforce a 3-turn NAP on a rival faction.",
            cost_naq=80, cooldown_turns=6, target_kind="faction",
            predicate=_pred_has_enemy_faction,
            handler=T_force_nap(3, "System Lord Decree"),
        ),
        LeaderAction(
            id="goauld_apophis_hatak", name="Ha'tak Fleet",
            description="Your next attack may strike a 2-hop planet.",
            cost_naq=50, cooldown_turns=5, target_kind="none",
            handler=T_enable_two_hop("Ha'tak Fleet"),
        ),
        LeaderAction(
            id="goauld_apophis_sarcophagus", name="Sarcophagus",
            description="Once per run: undo your most recent planet loss.",
            charges=1, target_kind="none",
            predicate=_pred_has_last_loss,
            handler=T_undo_last_loss("Sarcophagus"),
        ),
    ],

    "goauld_yu": [
        LeaderAction(
            id="goauld_yu_ancient_wisdom", name="Ancient Wisdom",
            description="Divine an enemy faction's next deck.",
            cost_naq=15, cooldown_turns=3, target_kind="faction",
            predicate=_pred_has_enemy_faction,
            handler=T_reveal_enemy_hand("Ancient Wisdom"),
        ),
        LeaderAction(
            id="goauld_yu_tribute", name="Imperial Tribute",
            description="Extract 80 naq from your System Lord coffers.",
            cooldown_turns=5, target_kind="none",
            handler=T_naq_grant(80, "Imperial Tribute"),
        ),
    ],

    "goauld_sokar": [
        LeaderAction(
            id="goauld_sokar_netu", name="Netu's Torment",
            description="All rivals lose 10 favor; the galaxy dreads you.",
            cost_naq=40, cooldown_turns=5, target_kind="none",
            handler=lambda s, g, t, r: _broadcast_favor(s, g, -10,
                                                        "Netu's Torment"),
        ),
        LeaderAction(
            id="goauld_sokar_infernal_fort", name="Infernal Fortress",
            description="+1 fortification at an owned planet, free.",
            cooldown_turns=3, target_kind="own_planet",
            predicate=_pred_has_owned_planet,
            handler=T_fort_free("Infernal Fortress"),
        ),
    ],

    "goauld_baal": [
        LeaderAction(
            id="goauld_baal_clone_gambit", name="Clone Gambit",
            description="Recruit a free operative from your clone network.",
            cost_naq=40, cooldown_turns=5, target_kind="none",
            handler=T_spawn_operative("Clone Gambit"),
        ),
        LeaderAction(
            id="goauld_baal_stock_market", name="Black Market Play",
            description="Purge your weakest card for +80 naquadah.",
            cooldown_turns=4, target_kind="none",
            handler=lambda s, g, t, r: (_strip_weakest_for_naq(s, 80,
                                                              "Black Market")),
        ),
        LeaderAction(
            id="goauld_baal_shadow_network", name="Shadow Network",
            description="Reveal all operative movement for 3 turns.",
            cost_naq=30, cooldown_turns=6, target_kind="none",
            handler=T_reveal_operatives("Shadow Network"),
        ),
    ],

    "goauld_anubis": [
        LeaderAction(
            id="goauld_anubis_ascended_wrath", name="Ascended Wrath",
            description="Devastate a rival's building; +1 favor penalty.",
            cost_naq=50, cooldown_turns=5, target_kind="enemy_planet",
            predicate=_pred_has_enemy_building,
            handler=T_sabotage_building("Ascended Wrath"),
        ),
        LeaderAction(
            id="goauld_anubis_dark_pact", name="Dark Pact",
            description="Force a 2-turn NAP on a faction (they resent you).",
            cost_naq=40, cooldown_turns=5, target_kind="faction",
            predicate=_pred_has_enemy_faction,
            handler=lambda s, g, t, r: _force_nap_with_favor_cost(s, t, 2, 10),
        ),
    ],

    "goauld_hathor_unlock": [
        LeaderAction(
            id="goauld_hathor_seduction", name="Seduction",
            description="+20 favor with a target faction (for now).",
            cost_naq=50, cooldown_turns=5, target_kind="faction",
            predicate=_pred_has_enemy_faction,
            handler=T_favor_shift(20, "Seduction"),
        ),
        LeaderAction(
            id="goauld_hathor_bloodline", name="Bloodline Decree",
            description="Convert a minor world into an instant ally.",
            cost_naq=120, charges=1, target_kind="any_planet",
            predicate=_pred_has_minor_world,
            handler=T_convert_minor_world("Bloodline Decree"),
        ),
    ],

    "goauld_cronus": [
        LeaderAction(
            id="goauld_cronus_imperial_expansion", name="Imperial Expansion",
            description="+10 naq per planet you own this turn.",
            cooldown_turns=5, target_kind="none",
            handler=lambda s, g, t, r: _per_planet_naq(s, 10,
                                                        "Imperial Expansion"),
        ),
        LeaderAction(
            id="goauld_cronus_time_dilation", name="Time Dilation",
            description="Skip the next counterattack phase entirely.",
            cost_naq=80, cooldown_turns=8, target_kind="none",
            handler=T_skip_counterattack_all("Time Dilation"),
        ),
    ],

    # ============================= JAFFA ==================================

    "jaffa_tealc": [
        LeaderAction(
            id="jaffa_tealc_uprising", name="Shol'va Uprising",
            description="+10 favor with a Jaffa-adjacent faction via rebellion.",
            cost_naq=40, cooldown_turns=5, target_kind="faction",
            predicate=_pred_has_enemy_faction,
            handler=T_favor_shift(10, "Shol'va Uprising"),
        ),
        LeaderAction(
            id="jaffa_tealc_honor", name="Warrior's Honor",
            description="Decline all counterattacks this turn.",
            cost_naq=60, cooldown_turns=6, target_kind="none",
            handler=T_skip_counterattack_all("Warrior's Honor"),
        ),
        LeaderAction(
            id="jaffa_tealc_rite", name="Rite of M'al Sharran",
            description="Upgrade your strongest card +2.",
            cost_naq=30, cooldown_turns=4, target_kind="none",
            handler=T_upgrade_strongest(1, "Rite of M'al Sharran", bonus=2),
        ),
    ],

    "jaffa_bratac": [
        LeaderAction(
            id="jaffa_bratac_elder_council", name="Elder Council",
            description="Recruit a Jaffa card into your deck.",
            cost_naq=40, cooldown_turns=5, target_kind="none",
            handler=lambda s, g, t, r: _recruit_random_faction_card(
                s, "Jaffa Rebellion", "Elder Council"),
        ),
        LeaderAction(
            id="jaffa_bratac_chulak_exile", name="Chulak Exile",
            description="Purge your weakest card (banished from memory).",
            cooldown_turns=4, target_kind="none",
            handler=T_remove_weakest("Chulak Exile"),
        ),
    ],

    "jaffa_raknor": [
        LeaderAction(
            id="jaffa_raknor_rebel_tactics", name="Rebel Tactics",
            description="Lift every cooldown across the galaxy.",
            cost_naq=40, charges=1, target_kind="none",
            predicate=_pred_has_cooldown,
            handler=T_clear_all_cooldowns("Rebel Tactics"),
        ),
        LeaderAction(
            id="jaffa_raknor_strike_team", name="Strike Team",
            description="Your next attack may strike a 2-hop planet.",
            cost_naq=40, cooldown_turns=5, target_kind="none",
            handler=T_enable_two_hop("Strike Team"),
        ),
    ],

    "jaffa_kalel": [
        LeaderAction(
            id="jaffa_kalel_warrior_training", name="Warrior Training",
            description="Upgrade your 3 strongest cards by +1.",
            cost_naq=50, cooldown_turns=5, target_kind="none",
            handler=T_upgrade_strongest(3, "Warrior Training"),
        ),
        LeaderAction(
            id="jaffa_kalel_council_rally", name="Council Rally",
            description="+15 favor with every trading faction.",
            cost_naq=30, cooldown_turns=4, target_kind="none",
            handler=lambda s, g, t, r: _trade_favor_boost(s, 15),
        ),
    ],

    "jaffa_gerak": [
        LeaderAction(
            id="jaffa_gerak_rite_of_kinship", name="Rite of Kinship",
            description="Draw a random Jaffa card into your deck.",
            cost_naq=30, cooldown_turns=4, target_kind="none",
            handler=lambda s, g, t, r: _recruit_random_faction_card(
                s, "Jaffa Rebellion", "Rite of Kinship"),
        ),
        LeaderAction(
            id="jaffa_gerak_vision", name="Ori Vision",
            description="Reveal a rival faction's deck next battle.",
            cost_naq=25, cooldown_turns=5, target_kind="faction",
            predicate=_pred_has_enemy_faction,
            handler=T_reveal_enemy_hand("Ori Vision"),
        ),
    ],

    "jaffa_ishta": [
        LeaderAction(
            id="jaffa_ishta_haktyl", name="Hak'tyl Resistance",
            description="Recruit a stealth operative.",
            cost_naq=40, cooldown_turns=5, target_kind="none",
            handler=T_spawn_operative("Hak'tyl Resistance"),
        ),
        LeaderAction(
            id="jaffa_ishta_bloodletting", name="Bloodletting",
            description="+1 fortification on any owned planet.",
            cost_naq=30, cooldown_turns=3, target_kind="own_planet",
            predicate=_pred_has_owned_planet,
            handler=T_fort_free("Bloodletting"),
        ),
    ],

    "jaffa_ryac": [
        LeaderAction(
            id="jaffa_ryac_hope", name="Hope for Tomorrow",
            description="Draw 2 upgrade tokens (upgrade random 2 cards).",
            cost_naq=40, cooldown_turns=5, target_kind="none",
            handler=T_upgrade_random(2, "Hope for Tomorrow"),
        ),
        LeaderAction(
            id="jaffa_ryac_young_leader", name="Young Leader",
            description="+10 wisdom from youthful inspiration.",
            cooldown_turns=6, target_kind="none",
            handler=T_wisdom_grant(10, "Young Leader"),
        ),
    ],

    # ============================= LUCIAN =================================

    "lucian_varro": [
        LeaderAction(
            id="lucian_varro_spy_mastery", name="Spy Mastery",
            description="Recruit a new operative instantly.",
            cost_naq=30, cooldown_turns=4, target_kind="none",
            handler=T_spawn_operative("Spy Mastery"),
        ),
        LeaderAction(
            id="lucian_varro_intel_leak", name="Intel Leak",
            description="Reveal a faction's deck next battle.",
            cost_naq=20, cooldown_turns=4, target_kind="faction",
            predicate=_pred_has_enemy_faction,
            handler=T_reveal_enemy_hand("Intel Leak"),
        ),
    ],

    "lucian_sodan_master": [
        LeaderAction(
            id="lucian_sodan_elite_training", name="Elite Training",
            description="Upgrade your 3 strongest cards by +1.",
            cost_naq=50, cooldown_turns=5, target_kind="none",
            handler=T_upgrade_strongest(3, "Elite Training"),
        ),
        LeaderAction(
            id="lucian_sodan_ritual_purge", name="Ritual Purge",
            description="Remove your weakest card from the deck.",
            cooldown_turns=4, target_kind="none",
            handler=T_remove_weakest("Ritual Purge"),
        ),
    ],

    "lucian_baal_clone": [
        LeaderAction(
            id="lucian_baal_clone_network", name="Clone Network",
            description="Spawn a free operative from a stored clone.",
            cost_naq=40, cooldown_turns=5, target_kind="none",
            handler=T_spawn_operative("Clone Network"),
        ),
        LeaderAction(
            id="lucian_baal_clone_market", name="Market Play",
            description="Shed a weak card for +100 naq on the black market.",
            cooldown_turns=5, target_kind="none",
            handler=lambda s, g, t, r: _strip_weakest_for_naq(s, 100,
                                                              "Market Play"),
        ),
    ],

    "lucian_netan": [
        LeaderAction(
            id="lucian_netan_smuggling", name="Smuggling Run",
            description="Instant +100 naquadah from contraband.",
            cooldown_turns=5, target_kind="none",
            handler=T_naq_grant(100, "Smuggling Run"),
        ),
        LeaderAction(
            id="lucian_netan_mercenary_contract", name="Mercenary Contract",
            description="Force a 2-turn NAP on a faction for 120 naq.",
            cost_naq=120, cooldown_turns=6, target_kind="faction",
            predicate=_pred_has_enemy_faction,
            handler=T_force_nap(2, "Mercenary Contract"),
        ),
        LeaderAction(
            id="lucian_netan_protection_racket", name="Protection Racket",
            description="Extort +60 naq from your current trade partners.",
            cost_naq=0, cooldown_turns=5, target_kind="none",
            handler=T_trade_income_boost("Protection Racket", bonus=60),
        ),
    ],

    "lucian_vala": [
        LeaderAction(
            id="lucian_vala_grand_theft", name="Grand Theft",
            description="Steal a random relic from a rival faction.",
            cost_naq=60, charges=1, target_kind="faction",
            predicate=_pred_has_enemy_faction,
            handler=lambda s, g, t, r: _steal_relic_from_pool(s, t),
        ),
        LeaderAction(
            id="lucian_vala_fake_identity", name="Fake Identity",
            description="For 2 turns AI treats you as neutral.",
            cost_naq=60, cooldown_turns=8, target_kind="none",
            handler=T_fake_identity(2, "Fake Identity"),
        ),
        LeaderAction(
            id="lucian_vala_smugglers_luck", name="Smuggler's Luck",
            description="+120 naq from a lucky haul.",
            cooldown_turns=6, target_kind="none",
            handler=T_naq_grant(120, "Smuggler's Luck"),
        ),
    ],

    "lucian_anateo": [
        LeaderAction(
            id="lucian_anateo_black_market", name="Black Market",
            description="Instant +80 naq from the underworld.",
            cooldown_turns=4, target_kind="none",
            handler=T_naq_grant(80, "Black Market"),
        ),
        LeaderAction(
            id="lucian_anateo_sabotage", name="Sabotage Run",
            description="Destroy a building on an enemy planet.",
            cost_naq=40, cooldown_turns=5, target_kind="enemy_planet",
            predicate=_pred_has_enemy_building,
            handler=T_sabotage_building("Sabotage Run"),
        ),
    ],

    "lucian_kiva": [
        LeaderAction(
            id="lucian_kiva_brutal_tactics", name="Brutal Tactics",
            description="Upgrade your 2 strongest cards by +2.",
            cost_naq=50, cooldown_turns=5, target_kind="none",
            handler=T_upgrade_strongest(2, "Brutal Tactics", bonus=2),
        ),
        LeaderAction(
            id="lucian_kiva_reign_of_fear", name="Reign of Fear",
            description="-15 favor with every faction (your name becomes dread).",
            cost_naq=20, cooldown_turns=6, target_kind="none",
            handler=lambda s, g, t, r: _broadcast_favor(s, g, -15,
                                                        "Reign of Fear"),
        ),
    ],

    # ============================= ASGARD =================================

    "asgard_freyr": [
        LeaderAction(
            id="asgard_freyr_shield", name="Asgard Shield",
            description="+1 fortification on any owned planet.",
            cost_naq=30, cooldown_turns=3, target_kind="own_planet",
            predicate=_pred_has_owned_planet,
            handler=T_fort_free("Asgard Shield"),
        ),
        LeaderAction(
            id="asgard_freyr_protectors", name="Protector's Vow",
            description="Skip all counterattacks for one turn.",
            cost_naq=80, cooldown_turns=8, target_kind="none",
            handler=T_skip_counterattack_all("Protector's Vow"),
        ),
    ],

    "asgard_loki": [
        LeaderAction(
            id="asgard_loki_experiment", name="Genetic Experiment",
            description="Upgrade a random card +2.",
            cost_naq=40, cooldown_turns=5, target_kind="none",
            handler=T_upgrade_random(1, "Genetic Experiment"),
        ),
        LeaderAction(
            id="asgard_loki_clone_swap", name="Clone Swap",
            description="Reveal an enemy faction's deck next battle.",
            cost_naq=20, cooldown_turns=4, target_kind="faction",
            predicate=_pred_has_enemy_faction,
            handler=T_reveal_enemy_hand("Clone Swap"),
        ),
        LeaderAction(
            id="asgard_loki_forbidden_research", name="Forbidden Research",
            description="+15 wisdom, -10 favor with all factions.",
            cost_naq=0, cooldown_turns=6, target_kind="none",
            handler=lambda s, g, t, r: _forbidden_research(s, g),
        ),
    ],

    "asgard_heimdall": [
        LeaderAction(
            id="asgard_heimdall_archive", name="Archive Protocol",
            description="Upgrade your strongest 2 cards by +2.",
            cost_naq=50, cooldown_turns=5, target_kind="none",
            handler=T_upgrade_strongest(2, "Archive Protocol", bonus=2),
        ),
        LeaderAction(
            id="asgard_heimdall_bifrost", name="Bifrost Redirect",
            description="Lift every cooldown in the galaxy.",
            cost_naq=60, cooldown_turns=6, target_kind="none",
            predicate=_pred_has_cooldown,
            handler=T_clear_all_cooldowns("Bifrost Redirect"),
        ),
    ],

    "asgard_thor": [
        LeaderAction(
            id="asgard_thor_asgard_beam", name="Asgard Beam",
            description="Destroy a building on an enemy planet instantly.",
            cost_naq=50, cooldown_turns=4, target_kind="enemy_planet",
            predicate=_pred_has_enemy_building,
            handler=T_sabotage_building("Asgard Beam"),
        ),
        LeaderAction(
            id="asgard_thor_fleet_command", name="Fleet Command",
            description="Skip every counterattack this turn.",
            cost_naq=100, cooldown_turns=8, target_kind="none",
            handler=T_skip_counterattack_all("Fleet Command"),
        ),
        LeaderAction(
            id="asgard_thor_oneill_class", name="O'Neill-Class Deployment",
            description="Your next attack may strike a 2-hop planet.",
            cost_naq=50, cooldown_turns=5, target_kind="none",
            handler=T_enable_two_hop("O'Neill-Class"),
        ),
    ],

    "asgard_hermiod": [
        LeaderAction(
            id="asgard_hermiod_shields_up", name="Shields Up",
            description="+1 fort on any owned planet.",
            cost_naq=30, cooldown_turns=3, target_kind="own_planet",
            predicate=_pred_has_owned_planet,
            handler=T_fort_free("Shields Up"),
        ),
        LeaderAction(
            id="asgard_hermiod_reroute", name="Power Reroute",
            description="Instant +80 naquadah from reactor efficiency.",
            cooldown_turns=5, target_kind="none",
            handler=T_naq_grant(80, "Power Reroute"),
        ),
    ],

    "asgard_penegal": [
        LeaderAction(
            id="asgard_penegal_cloning_bay", name="Cloning Bay",
            description="Spawn a fresh operative from your cloning tanks.",
            cost_naq=40, cooldown_turns=5, target_kind="none",
            handler=T_spawn_operative("Cloning Bay"),
        ),
        LeaderAction(
            id="asgard_penegal_archive", name="Archive Retrieval",
            description="Upgrade a random card by +1.",
            cost_naq=25, cooldown_turns=4, target_kind="none",
            handler=T_upgrade_random(1, "Archive Retrieval"),
        ),
    ],

    "asgard_aegir": [
        LeaderAction(
            id="asgard_aegir_archives", name="Asgard Archives",
            description="Draw a random Asgard card.",
            cost_naq=40, cooldown_turns=5, target_kind="none",
            handler=lambda s, g, t, r: _recruit_random_faction_card(
                s, "Asgard", "Asgard Archives"),
        ),
        LeaderAction(
            id="asgard_aegir_deep_surge", name="Deep Surge",
            description="+80 naq from Asgard industry.",
            cooldown_turns=5, target_kind="none",
            handler=T_naq_grant(80, "Deep Surge"),
        ),
    ],

    # ============================= ALTERAN ================================

    "alteran_adria": [
        LeaderAction(
            id="alteran_adria_crusade", name="Crusade",
            description="+1 fortification on every owned planet.",
            cost_naq=100, cooldown_turns=6, target_kind="none",
            predicate=_pred_has_owned_planet,
            handler=lambda s, g, t, r: _crusade_fortify_all(s, g),
        ),
        LeaderAction(
            id="alteran_adria_book_of_origin", name="Book of Origin",
            description="Convert a minor world to Ally instantly.",
            cost_naq=150, charges=1, target_kind="any_planet",
            predicate=_pred_has_minor_world,
            handler=T_convert_minor_world("Book of Origin"),
        ),
        LeaderAction(
            id="alteran_adria_orici_will", name="Orici's Will",
            description="Clear the pending crisis and shield for 3 turns.",
            cost_naq=80, cooldown_turns=8, target_kind="none",
            handler=T_skip_crisis("Orici's Will"),
        ),
    ],

    "alteran_doci": [
        LeaderAction(
            id="alteran_doci_voice_of_origin", name="Voice of Origin",
            description="+20 favor with a target faction.",
            cost_naq=60, cooldown_turns=5, target_kind="faction",
            predicate=_pred_has_enemy_faction,
            handler=T_favor_shift(20, "Voice of Origin"),
        ),
        LeaderAction(
            id="alteran_doci_convert", name="Convert the Unworthy",
            description="Purge your weakest card (ritual offering).",
            cooldown_turns=4, target_kind="none",
            handler=T_remove_weakest("Convert the Unworthy"),
        ),
    ],

    "alteran_merlin": [
        LeaderAction(
            id="alteran_merlin_sangraal", name="Sangraal Protocol",
            description="Shatter the coalition against you.",
            charges=1, target_kind="none",
            predicate=_pred_coalition_active,
            handler=T_dispel_coalition("Sangraal Protocol"),
        ),
        LeaderAction(
            id="alteran_merlin_ancient_repository", name="Ancient Repository",
            description="Upgrade your strongest card +3.",
            cost_naq=60, cooldown_turns=6, target_kind="none",
            handler=T_upgrade_strongest(1, "Ancient Repository", bonus=3),
        ),
        LeaderAction(
            id="alteran_merlin_time_dilation", name="Time Dilation",
            description="Collect 2 turns of baseline naquadah income now.",
            cost_naq=60, cooldown_turns=8, target_kind="none",
            handler=lambda s, g, t, r: _time_dilation_income(s, g),
        ),
    ],

    "alteran_morgan": [
        LeaderAction(
            id="alteran_morgan_eternal_watch", name="Eternal Watch",
            description="Undo your most recent planet loss.",
            charges=1, target_kind="none",
            predicate=_pred_has_last_loss,
            handler=T_undo_last_loss("Eternal Watch"),
        ),
        LeaderAction(
            id="alteran_morgan_ascended_guidance", name="Ascended Guidance",
            description="Upgrade 2 random cards.",
            cost_naq=40, cooldown_turns=5, target_kind="none",
            handler=T_upgrade_random(2, "Ascended Guidance"),
        ),
    ],

    "alteran_oma": [
        LeaderAction(
            id="alteran_oma_path", name="Path to Ascension",
            description="Purge weakest, upgrade strongest +3.",
            cost_naq=40, cooldown_turns=5, target_kind="none",
            handler=lambda s, g, t, r: _oma_ascension(s),
        ),
        LeaderAction(
            id="alteran_oma_serenity", name="Serenity",
            description="Shield the galaxy from crisis for 3 turns.",
            cost_naq=60, cooldown_turns=7, target_kind="none",
            handler=T_skip_crisis("Serenity"),
        ),
    ],
}


# ===========================================================================
# Inline handlers referenced by lambdas above
# ===========================================================================

def _trade_favor_boost(state, amount: int) -> str:
    trading = [f for f, r in state.faction_relations.items() if r == "trading"]
    for f in trading:
        cur = state.diplomatic_favor.get(f, 0)
        state.diplomatic_favor[f] = max(-100, min(100, cur + amount))
    n = len(trading)
    return f"+{amount} favor with {n} trade partner(s)."


def _broadcast_favor(state, galaxy, delta: int, flavor: str) -> str:
    factions = _any_enemy_faction(state, galaxy)
    for f in factions:
        cur = state.diplomatic_favor.get(f, 0)
        state.diplomatic_favor[f] = max(-100, min(100, cur + delta))
    sign = "+" if delta >= 0 else ""
    return f"{flavor}: {sign}{delta} favor with all {len(factions)} rival(s)."


def _force_nap_with_favor_cost(state, faction: str, turns: int, favor_cost: int) -> str:
    if not faction:
        return "Dark Pact: no target."
    state.treaties.append({
        "type": "nap",
        "faction": faction,
        "turns_remaining": turns,
        "signed_on_turn": state.turn_number,
        "penalty_if_broken": 30,
    })
    cur = state.diplomatic_favor.get(faction, 0)
    state.diplomatic_favor[faction] = max(-100, cur - favor_cost)
    return f"Dark Pact: forced NAP with {faction} ({turns} turns, -{favor_cost} favor)."


def _per_planet_naq(state, per_planet: int, flavor: str) -> str:
    owned = sum(1 for o in state.planet_ownership.values() if o == "player")
    total = owned * per_planet
    state.add_naquadah(total)
    return f"{flavor}: +{total} naq ({owned} planets × {per_planet})."


def _strip_weakest_for_naq(state, amount: int, flavor: str) -> str:
    from cards import ALL_CARDS
    cards = [cid for cid in state.current_deck
             if ALL_CARDS.get(cid) and getattr(ALL_CARDS[cid], 'power', None)]
    if not cards:
        return f"{flavor}: no card to trade."
    cards.sort(key=lambda c: getattr(ALL_CARDS[c], 'power', 0))
    victim = cards[0]
    state.remove_card(victim)
    state.add_naquadah(amount)
    return f"{flavor}: sold {_card_name(victim)} for {amount} naq."


def _recruit_random_faction_card(state, faction: str, flavor: str) -> str:
    from cards import ALL_CARDS
    pool = [cid for cid, c in ALL_CARDS.items()
            if getattr(c, 'faction', None) == faction and getattr(c, 'power', None)]
    if not pool:
        return f"{flavor}: no card available."
    cid = random.choice(pool)
    state.add_card(cid)
    return f"{flavor}: {_card_name(cid)} joins your deck."


def _forbidden_research(state, galaxy) -> str:
    state.wisdom += 15
    for f in _any_enemy_faction(state, galaxy):
        cur = state.diplomatic_favor.get(f, 0)
        state.diplomatic_favor[f] = max(-100, cur - 10)
    return "Forbidden Research: +15 wisdom, -10 favor with all rivals."


def _steal_relic_from_pool(state, faction: str) -> str:
    """Grant a relic from a hardcoded pool tied to the faction.  Crude but
    keeps the action feeling factional until Sprint 5's relic overhaul."""
    pool = {
        "Tau'ri": "alteran_database",
        "Goa'uld": "staff_of_ra",
        "Jaffa Rebellion": "kara_kesh",
        "Lucian Alliance": "kull_armor",
        "Asgard": "thors_hammer",
        "Alteran": "ancient_zpm",
    }
    relic_id = pool.get(faction, "staff_of_ra")
    if state.has_relic(relic_id):
        # Fall back to naq compensation.
        state.add_naquadah(60)
        return f"Grand Theft: already own relic — took 60 naq instead."
    state.add_relic(relic_id)
    return f"Grand Theft: stole relic {relic_id} from {faction}."


def _crusade_fortify_all(state, galaxy) -> str:
    owned = _any_owned_planet(state)
    for pid in owned:
        cur = state.fortification_levels.get(pid, 0)
        state.fortification_levels[pid] = min(3, cur + 1)
    return f"Crusade: +1 fortification on {len(owned)} planet(s)."


def _time_dilation_income(state, galaxy) -> str:
    from .planet_passives import get_naquadah_per_turn
    from .diplomacy import get_adjacency_bonus_factions
    allied = get_adjacency_bonus_factions(state)
    per_turn = max(20, get_naquadah_per_turn(galaxy, allied))
    gain = per_turn * 2
    state.add_naquadah(gain)
    return f"Time Dilation: +{gain} naq (two turns of income)."


def _oma_ascension(state) -> str:
    from cards import ALL_CARDS
    cards = [cid for cid in state.current_deck
             if ALL_CARDS.get(cid) and getattr(ALL_CARDS[cid], 'power', None)]
    if len(cards) < 2:
        return "Path to Ascension: not enough cards."
    cards.sort(key=lambda c: getattr(ALL_CARDS[c], 'power', 0))
    state.remove_card(cards[0])
    state.upgrade_card(cards[-1], 3)
    return (f"Path to Ascension: purged {_card_name(cards[0])}, "
            f"{_card_name(cards[-1])} +3.")
