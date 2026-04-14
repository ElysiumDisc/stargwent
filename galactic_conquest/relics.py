"""
STARGWENT - GALACTIC CONQUEST - Relic / Artifact System

Stargate-themed relics with permanent passive effects for the campaign run.
Relics are acquired by conquering homeworlds, completing story arcs, or events.
"""

from dataclasses import dataclass


@dataclass
class Relic:
    """A collectible artifact with a passive campaign effect.

    v11.0 (G7): relics can optionally expose an ``active_ability`` for
    player-triggered effects. Only out-of-battle actives ship in 11.0 to
    keep the card-battle path completely untouched.

    active_ability: dict | None with keys:
        name: str                       — button label
        desc: str                       — tooltip
        charges: int                    — starting charge count (per campaign)
        effect_type: str                — "undo_last_planet_loss", "full_deck_heal"
    """
    id: str
    name: str
    description: str
    icon_char: str        # Unicode character for HUD display
    category: str         # "combat" | "economy" | "exploration"
    active_ability: dict = None


# All available relics
RELICS = {
    # === Combat Relics ===
    "staff_of_ra": Relic(
        id="staff_of_ra",
        name="Staff of Ra",
        description="+1 power to all Goa'uld cards in your deck",
        icon_char="\u2694",  # crossed swords
        category="combat",
        active_ability={
            "name": "Ra's Wrath",
            "desc": "Destroy a building on any enemy planet.",
            "charges": 2,
            "effect_type": "destroy_building",
            "target_kind": "enemy_planet",
        },
    ),
    "thors_hammer": Relic(
        id="thors_hammer",
        name="Thor's Hammer",
        description="+2 power to all Hero cards",
        icon_char="\u2692",  # hammer and pick
        category="combat",
        active_ability={
            "name": "Hammer of Judgment",
            "desc": "Cancel every counterattack this turn.",
            "charges": 1,
            "effect_type": "skip_all_counterattacks",
        },
    ),
    "kull_armor": Relic(
        id="kull_armor",
        name="Kull Armor",
        description="-1 power to all enemy cards (min 1)",
        icon_char="\u26E8",  # shield
        category="combat",
        active_ability={
            "name": "Impenetrable Guard",
            "desc": "+1 fortification on every owned planet.",
            "charges": 1,
            "effect_type": "fort_all_owned",
        },
    ),
    "iris_shield": Relic(
        id="iris_shield",
        name="Iris Shield",
        description="Block the first Spy card played against you",
        icon_char="\u25CE",  # bullseye
        category="combat",
        active_ability={
            "name": "Iris Lockdown",
            "desc": "Neutralise the next 2 sleeper-agent sabotages.",
            "charges": 2,
            "effect_type": "iris_lockdown",
        },
    ),
    "ancient_zpm": Relic(
        id="ancient_zpm",
        name="Ancient ZPM",
        description="+1 starting card in all battles",
        icon_char="\u26A1",  # lightning
        category="combat",
        active_ability={
            "name": "Power Surge",
            "desc": "Temporary +1 network tier for 3 turns.",
            "charges": 1,
            "effect_type": "network_surge",
        },
    ),
    "ori_prior_staff": Relic(
        id="ori_prior_staff",
        name="Ori Prior Staff",
        description="Weather effects deal minimum 3 power reduction (not 1)",
        icon_char="\u2721",  # star
        category="combat",
        active_ability={
            "name": "Prior's Judgment",
            "desc": "Clear the pending crisis and lock crises for 3 turns.",
            "charges": 1,
            "effect_type": "skip_crisis",
        },
    ),
    "sarcophagus": Relic(
        id="sarcophagus",
        name="Sarcophagus",
        description="Revive: +1 random card from your discard after each round",
        icon_char="\u2625",  # ankh
        category="combat",
        # v11.0 (G7): two-charge out-of-battle full-deck heal
        active_ability={
            "name": "Sarcophagus Chamber",
            "desc": "Restore all card upgrade penalties and reset cooldowns",
            "charges": 2,
            "effect_type": "full_deck_heal",
        },
    ),

    # === Economy Relics ===
    "asgard_core": Relic(
        id="asgard_core",
        name="Asgard Core",
        description="+20 bonus Naquadah per victory",
        icon_char="\u2B50",  # star
        category="economy",
        active_ability={
            "name": "Core Reroute",
            "desc": "Double your next 2 turns of passive naquadah income.",
            "charges": 1,
            "effect_type": "income_double",
        },
    ),
    "naquadah_reactor": Relic(
        id="naquadah_reactor",
        name="Naquadah Reactor",
        description="+10 Naquadah per turn (passive income)",
        icon_char="\u2622",  # radioactive
        category="economy",
        active_ability={
            "name": "Reactor Overload",
            "desc": "Overload for +150 naquadah now.",
            "charges": 2,
            "effect_type": "naq_burst",
            "naq_amount": 150,
        },
    ),

    # === Exploration Relics ===
    "ring_platform": Relic(
        id="ring_platform",
        name="Ring Platform",
        description="Attack planets 2 hops away (not just adjacent)",
        icon_char="\u25EF",  # large circle
        category="exploration",
        active_ability={
            "name": "Extended Ring",
            "desc": "Your next 2 attacks may reach distant planets.",
            "charges": 1,
            "effect_type": "two_hop_bank",
        },
    ),
    "replicator_nanites": Relic(
        id="replicator_nanites",
        name="Replicator Nanites",
        description="20% chance to duplicate chosen reward card",
        icon_char="\u2234",  # therefore (dots)
        category="exploration",
        active_ability={
            "name": "Nanite Storm",
            "desc": "Upgrade 3 random cards in your deck.",
            "charges": 1,
            "effect_type": "upgrade_random3",
        },
    ),
    "alteran_database": Relic(
        id="alteran_database",
        name="Alteran Database",
        description="+1 card choice on all reward screens",
        icon_char="\u2261",  # triple bar
        category="exploration",
        active_ability={
            "name": "Archive Query",
            "desc": "Reveal every faction's deck for your next 2 battles.",
            "charges": 1,
            "effect_type": "intel_bank",
        },
    ),
    "quantum_mirror": Relic(
        id="quantum_mirror",
        name="Quantum Mirror",
        description="See enemy hand size during battles",
        icon_char="\u2B2F",  # mirror
        category="exploration",
        active_ability={
            "name": "Strategic Glance",
            "desc": "Reveal all AI intel (naq, doctrines, buildings) for 3 turns.",
            "charges": 1,
            "effect_type": "reveal_ai_intel",
        },
    ),
    "teltak_transport": Relic(
        id="teltak_transport",
        name="Tel'tak Transport",
        description="See defender power total before attacking",
        icon_char="\u2708",  # airplane
        category="exploration",
        active_ability={
            "name": "Cloaked Run",
            "desc": "Recruit a free operative.",
            "charges": 2,
            "effect_type": "spawn_operative",
        },
    ),
    "jaffa_tretonin": Relic(
        id="jaffa_tretonin",
        name="Jaffa Tretonin",
        description="Weather can't reduce your cards below 3 power",
        icon_char="\u2695",  # caduceus
        category="combat",
        active_ability={
            "name": "Field Triage",
            "desc": "Upgrade your 2 strongest cards by +2.",
            "charges": 1,
            "effect_type": "upgrade_strongest2",
        },
    ),
    "ancient_repository": Relic(
        id="ancient_repository",
        name="Ancient Repository",
        description="+30 naq/turn if you control Atlantis",
        icon_char="\u2261",  # triple bar
        category="economy",
        active_ability={
            "name": "Knowledge Infusion",
            "desc": "Gain 40 Wisdom instantly.",
            "charges": 1,
            "effect_type": "wisdom_burst",
            "wisdom_amount": 40,
        },
    ),
    "asgard_time_machine": Relic(
        id="asgard_time_machine",
        name="Asgard Time Machine",
        description="Once per campaign: undo last planet loss",
        icon_char="\u231B",  # hourglass
        category="exploration",
        # v11.0 (G7): single-charge campaign rewind for the last planet loss
        active_ability={
            "name": "Temporal Rewind",
            "desc": "Restore your most recently lost planet (not homeworld)",
            "charges": 1,
            "effect_type": "undo_last_planet_loss",
        },
    ),
    "flames_of_celestis": Relic(
        id="flames_of_celestis",
        name="Flames of Celestis",
        description="+2 power to first card played each round",
        icon_char="\U0001F525",  # fire
        category="combat",
        active_ability={
            "name": "Pyre of the Ori",
            "desc": "Purge your weakest card for +120 naquadah.",
            "charges": 1,
            "effect_type": "purge_for_naq",
            "naq_amount": 120,
        },
    ),
}


# ===========================================================================
# Active relic dispatcher (12.0 — Pillar 4c expansion)
# ===========================================================================
#
# Relics with ``active_ability`` are player-triggered map actions.  The
# existing ``sarcophagus`` / ``asgard_time_machine`` both used bespoke
# code paths in the controller; 12.0 adds a unified dispatcher so the
# spellbook of actives stays in one place.
#
# Charges are tracked in ``state.relic_active_charges`` — a dict keyed
# by ``relic_id``.  A fresh run seeds the charge count on first use so
# we don't have to touch migration.

def get_active_charges_remaining(state, relic_id: str) -> int:
    """How many activations remain for *relic_id*.

    Uses the pre-12 "remaining" convention: ``state.relic_active_charges``
    stores the remaining count, seeded from ``active_ability['charges']``
    on first query.  Returns 0 if the relic is not owned, has no
    active, or is spent.
    """
    relic = RELICS.get(relic_id)
    if relic is None or not relic.active_ability:
        return 0
    if relic_id not in state.relics:
        return 0
    starting = int(relic.active_ability.get("charges", 1))
    return int(state.relic_active_charges.get(relic_id, starting))


def _apply_relic_effect(state, galaxy, relic, effect: str, target, rng) -> str:
    from cards import ALL_CARDS

    if effect == "destroy_building":
        if not target or target not in state.buildings:
            return f"{relic.name}: no building to destroy."
        name = state.buildings.pop(target)
        state.building_levels.pop(target, None)
        return f"{relic.name}: destroyed {name}."

    if effect == "skip_all_counterattacks":
        state.conquest_ability_data["skip_all_counterattacks"] = True
        return f"{relic.name}: counterattacks cancelled this turn."

    if effect == "fort_all_owned":
        count = 0
        for pid, owner in state.planet_ownership.items():
            if owner == "player":
                cur = state.fortification_levels.get(pid, 0)
                if cur < 3:
                    state.fortification_levels[pid] = cur + 1
                    count += 1
        return f"{relic.name}: +1 fort on {count} planet(s)."

    if effect == "iris_lockdown":
        state.conquest_ability_data["iris_lockdown_charges"] = \
            state.conquest_ability_data.get("iris_lockdown_charges", 0) + 2
        return f"{relic.name}: sleeper sabotages blocked (x2)."

    if effect == "network_surge":
        state.conquest_ability_data["network_surge_turns"] = 3
        return f"{relic.name}: +1 network tier for 3 turns."

    if effect == "skip_crisis":
        state.pending_crisis = {}
        state.crisis_cooldown = max(state.crisis_cooldown, 3)
        return f"{relic.name}: crises suppressed for 3 turns."

    if effect == "income_double":
        state.conquest_ability_data["income_double_turns"] = 2
        return f"{relic.name}: income doubled for 2 turns."

    if effect == "naq_burst":
        amt = int(relic.active_ability.get("naq_amount", 100))
        state.add_naquadah(amt)
        return f"{relic.name}: +{amt} naquadah."

    if effect == "two_hop_bank":
        state.conquest_ability_data["two_hop_attack_charges"] = \
            state.conquest_ability_data.get("two_hop_attack_charges", 0) + 2
        return f"{relic.name}: 2 extended-range attacks banked."

    if effect == "upgrade_random3":
        cards = [cid for cid in state.current_deck
                 if ALL_CARDS.get(cid) and getattr(ALL_CARDS[cid], 'power', None)]
        if not cards:
            return f"{relic.name}: no cards to upgrade."
        picks = rng.sample(cards, min(3, len(cards)))
        for cid in picks:
            state.upgrade_card(cid, 1)
        names = [getattr(ALL_CARDS[c], 'name', c) for c in picks]
        return f"{relic.name}: upgraded {', '.join(names)}."

    if effect == "intel_bank":
        state.conquest_ability_data["next_battle_intel_count"] = \
            state.conquest_ability_data.get("next_battle_intel_count", 0) + 2
        return f"{relic.name}: next 2 battles reveal enemy decks."

    if effect == "reveal_ai_intel":
        state.conquest_ability_data["ai_intel_turns"] = 3
        return f"{relic.name}: AI intel visible for 3 turns."

    if effect == "spawn_operative":
        op_id = state.operative_next_id
        state.operative_next_id += 1
        state.operatives.append({
            "id": op_id, "planet_id": None, "mission": None,
            "turns_remaining": 0, "status": "idle",
        })
        return f"{relic.name}: new operative recruited."

    if effect == "upgrade_strongest2":
        cards = [cid for cid in state.current_deck
                 if ALL_CARDS.get(cid) and getattr(ALL_CARDS[cid], 'power', None)]
        if not cards:
            return f"{relic.name}: no cards to upgrade."
        cards.sort(key=lambda c: getattr(ALL_CARDS[c], 'power', 0), reverse=True)
        for cid in cards[:2]:
            state.upgrade_card(cid, 2)
        names = [getattr(ALL_CARDS[c], 'name', c) for c in cards[:2]]
        return f"{relic.name}: +2 power to {', '.join(names)}."

    if effect == "wisdom_burst":
        amt = int(relic.active_ability.get("wisdom_amount", 30))
        state.wisdom = getattr(state, 'wisdom', 0) + amt
        return f"{relic.name}: +{amt} wisdom."

    if effect == "purge_for_naq":
        cards = [cid for cid in state.current_deck
                 if ALL_CARDS.get(cid) and getattr(ALL_CARDS[cid], 'power', None)]
        if not cards:
            return f"{relic.name}: no card to burn."
        cards.sort(key=lambda c: getattr(ALL_CARDS[c], 'power', 0))
        victim = cards[0]
        state.remove_card(victim)
        amt = int(relic.active_ability.get("naq_amount", 100))
        state.add_naquadah(amt)
        return f"{relic.name}: burned {getattr(ALL_CARDS[victim], 'name', victim)} for +{amt} naq."

    # Legacy effects kept for parity with pre-12 wiring (controller
    # already handles these through bespoke code, but we can fire them
    # from the panel too).
    if effect == "undo_last_planet_loss":
        last = state.conquest_ability_data.get("_last_planet_lost")
        if not last or not last.get("planet_id"):
            return f"{relic.name}: no recent loss."
        pid = last["planet_id"]
        galaxy.transfer_ownership(pid, "player")
        state.planet_ownership[pid] = "player"
        state.add_naquadah(30)
        state.conquest_ability_data["_last_planet_lost"] = None
        return f"{relic.name}: planet restored."

    if effect == "full_deck_heal":
        state.cooldowns.clear()
        return f"{relic.name}: all cooldowns cleared."

    return f"{relic.name}: activated."


# Guaranteed relic per conquered homeworld
HOMEWORLD_RELICS = {
    "Goa'uld": "sarcophagus",
    "Tau'ri": "iris_shield",
    "Jaffa Rebellion": "kull_armor",
    "Lucian Alliance": "naquadah_reactor",
    "Asgard": "asgard_core",
}


def get_relic(relic_id):
    """Get a Relic by ID, or None if not found."""
    return RELICS.get(relic_id)


def get_homeworld_relic(faction):
    """Get the relic ID awarded for conquering a faction's homeworld."""
    return HOMEWORLD_RELICS.get(faction)


# --- Relic Combos: specific pairs trigger bonus effects ---

RELIC_COMBOS = {
    "weapon_of_the_ancients": {
        "name": "Weapon of the Ancients",
        "relics": ("staff_of_ra", "thors_hammer"),
        "description": "Hero cards gain +1 power",
        "effect": {"hero_power_bonus": 1},
    },
    "unlimited_power": {
        "name": "Unlimited Power",
        "relics": ("ancient_zpm", "naquadah_reactor"),
        "description": "+2 starting cards in battles",
        "effect": {"extra_starting_cards": 2},
    },
    "self_replicating_network": {
        "name": "Self-Replicating Network",
        "relics": ("ring_platform", "replicator_nanites"),
        "description": "Fortify remote planets (2-hop range)",
        "effect": {"remote_fortify": True},
    },
    "impenetrable_defense": {
        "name": "Impenetrable Defense",
        "relics": ("iris_shield", "kull_armor"),
        "description": "-2 power to enemy cards (instead of -1)",
        "effect": {"enhanced_kull_armor": True},
    },
    "ascended_arsenal": {
        "name": "Ascended Arsenal",
        "relics": ("flames_of_celestis", "ori_prior_staff"),
        "description": "+15 naquadah per victory",
        "effect": {"victory_naq_bonus": 15},
    },
    "temporal_archives": {
        "name": "Temporal Archives",
        "relics": ("asgard_time_machine", "alteran_database"),
        "description": "+2 card choices on reward screens",
        "effect": {"extra_card_choices": 2},
    },
    # --- v11.0 three-relic trios (G7) ---
    "weapon_trinity": {
        "name": "Weapon Trinity",
        "relics": ("staff_of_ra", "thors_hammer", "ori_prior_staff"),
        "description": "Hero cards gain +2 power (trio bonus)",
        "effect": {"hero_power_bonus": 2},
    },
    "galactic_archive": {
        "name": "Galactic Archive",
        "relics": ("alteran_database", "asgard_core", "quantum_mirror"),
        "description": "+25 naquadah per victory and +1 card choice",
        "effect": {"victory_naq_bonus": 25, "extra_card_choices": 1},
    },
}


# --- Relic active ability activation ---
#
# 12.0 consolidation: a single ``activate_relic`` covers every active
# (legacy undo_last_planet_loss + full_deck_heal plus the 13 new
# effect_types added in Pillar 4c).  Charge bookkeeping keeps the
# pre-12 "remaining" convention so saves stay compatible.

def get_active_relics(state):
    """Return a list of ``(relic_id, active_ability_dict)`` for every
    owned relic whose active still has charges left.  (The relic
    ACTIVES panel consumes this shape.)"""
    result = []
    for relic_id in state.relics:
        relic = RELICS.get(relic_id)
        if relic is None or relic.active_ability is None:
            continue
        if get_active_charges_remaining(state, relic_id) <= 0:
            continue
        result.append((relic_id, relic.active_ability))
    return result


def activate_relic(state, galaxy, relic_id, target=None, rng=None):
    """Fire a relic active ability.  Returns message on success, ``None``
    if the relic isn't owned / has no active / is out of charges.

    Effect dispatch lives in ``_apply_relic_effect``; this wrapper
    handles ownership + charge bookkeeping so every code path sees
    the same deduction rules.
    """
    import random as _random
    relic = RELICS.get(relic_id)
    if relic is None or relic.active_ability is None:
        return None
    if not state.has_relic(relic_id):
        return None
    remaining = get_active_charges_remaining(state, relic_id)
    if remaining <= 0:
        return "No charges remaining."

    rng = rng or _random
    effect = relic.active_ability.get("effect_type", "")
    msg = _apply_relic_effect(state, galaxy, relic, effect, target, rng)
    state.relic_active_charges[relic_id] = remaining - 1
    return msg


def get_active_combos(state):
    """Return list of active relic combo dicts for the player's current relics.

    v11.0 (G7): combos can now list 2 *or* 3 relics. Matching is
    all-members-required so the generalization is a tuple membership check.
    """
    active = []
    for combo_id, combo in RELIC_COMBOS.items():
        relic_ids = combo["relics"]
        if all(state.has_relic(rid) for rid in relic_ids):
            active.append(combo)
    return active


def get_combo_effects(state):
    """Aggregate all active relic combo effects into a single dict."""
    effects = {}
    for combo in get_active_combos(state):
        for key, val in combo["effect"].items():
            if isinstance(val, bool):
                effects[key] = True
            elif isinstance(val, (int, float)):
                effects[key] = effects.get(key, 0) + val
            else:
                effects[key] = val
    return effects
