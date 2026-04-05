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
    ),
    "thors_hammer": Relic(
        id="thors_hammer",
        name="Thor's Hammer",
        description="+2 power to all Hero cards",
        icon_char="\u2692",  # hammer and pick
        category="combat",
    ),
    "kull_armor": Relic(
        id="kull_armor",
        name="Kull Armor",
        description="-1 power to all enemy cards (min 1)",
        icon_char="\u26E8",  # shield
        category="combat",
    ),
    "iris_shield": Relic(
        id="iris_shield",
        name="Iris Shield",
        description="Block the first Spy card played against you",
        icon_char="\u25CE",  # bullseye
        category="combat",
    ),
    "ancient_zpm": Relic(
        id="ancient_zpm",
        name="Ancient ZPM",
        description="+1 starting card in all battles",
        icon_char="\u26A1",  # lightning
        category="combat",
    ),
    "ori_prior_staff": Relic(
        id="ori_prior_staff",
        name="Ori Prior Staff",
        description="Weather effects deal minimum 3 power reduction (not 1)",
        icon_char="\u2721",  # star
        category="combat",
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
    ),
    "naquadah_reactor": Relic(
        id="naquadah_reactor",
        name="Naquadah Reactor",
        description="+10 Naquadah per turn (passive income)",
        icon_char="\u2622",  # radioactive
        category="economy",
    ),

    # === Exploration Relics ===
    "ring_platform": Relic(
        id="ring_platform",
        name="Ring Platform",
        description="Attack planets 2 hops away (not just adjacent)",
        icon_char="\u25EF",  # large circle
        category="exploration",
    ),
    "replicator_nanites": Relic(
        id="replicator_nanites",
        name="Replicator Nanites",
        description="20% chance to duplicate chosen reward card",
        icon_char="\u2234",  # therefore (dots)
        category="exploration",
    ),
    "alteran_database": Relic(
        id="alteran_database",
        name="Alteran Database",
        description="+1 card choice on all reward screens",
        icon_char="\u2261",  # triple bar
        category="exploration",
    ),
    "quantum_mirror": Relic(
        id="quantum_mirror",
        name="Quantum Mirror",
        description="See enemy hand size during battles",
        icon_char="\u2B2F",  # mirror
        category="exploration",
    ),
    "teltak_transport": Relic(
        id="teltak_transport",
        name="Tel'tak Transport",
        description="See defender power total before attacking",
        icon_char="\u2708",  # airplane
        category="exploration",
    ),
    "jaffa_tretonin": Relic(
        id="jaffa_tretonin",
        name="Jaffa Tretonin",
        description="Weather can't reduce your cards below 3 power",
        icon_char="\u2695",  # caduceus
        category="combat",
    ),
    "ancient_repository": Relic(
        id="ancient_repository",
        name="Ancient Repository",
        description="+30 naq/turn if you control Atlantis",
        icon_char="\u2261",  # triple bar
        category="economy",
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
    ),
}


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

def get_active_relics(state):
    """Return a list of (relic, charges_remaining) for every owned relic
    that exposes an active ability with remaining charges."""
    result = []
    for relic_id in state.relics:
        relic = RELICS.get(relic_id)
        if relic is None or relic.active_ability is None:
            continue
        starting = relic.active_ability.get("charges", 1)
        remaining = state.relic_active_charges.get(
            relic_id,
            starting,
        )
        result.append((relic, remaining))
    return result


def activate_relic(state, galaxy, relic_id):
    """Fire a relic active ability. Returns message on success, None on failure.

    This function handles ONLY out-of-battle actives — `undo_last_planet_loss`
    and `full_deck_heal`. Charge bookkeeping lives on
    state.relic_active_charges (migrated save field) so activations persist
    across save/load.
    """
    relic = RELICS.get(relic_id)
    if relic is None or relic.active_ability is None:
        return None
    if not state.has_relic(relic_id):
        return None
    starting = relic.active_ability.get("charges", 1)
    remaining = state.relic_active_charges.get(relic_id, starting)
    if remaining <= 0:
        return "No charges remaining."

    effect_type = relic.active_ability.get("effect_type")

    if effect_type == "undo_last_planet_loss":
        last_lost = state.conquest_ability_data.get("_last_planet_lost")
        if not last_lost:
            return "No recent planet loss to undo."
        pid = last_lost.get("planet_id")
        planet = galaxy.planets.get(pid) if pid else None
        if not planet:
            return "Lost planet data unavailable."
        # Restore ownership
        galaxy.transfer_ownership(pid, "player")
        state.planet_ownership[pid] = "player"
        del state.conquest_ability_data["_last_planet_lost"]
        state.relic_active_charges[relic_id] = remaining - 1
        return f"Temporal Rewind restored {planet.name}! ({remaining - 1} charges left)"

    if effect_type == "full_deck_heal":
        # Remove all card-upgrade penalties from prior crises/plagues and
        # reset cooldowns — a clean slate between battles.
        healed_count = 0
        for cid, val in list(state.upgraded_cards.items()):
            if val < 0:
                state.upgraded_cards[cid] = 0
                healed_count += 1
        state.cooldowns.clear()
        state.relic_active_charges[relic_id] = remaining - 1
        return (f"Sarcophagus Chamber: cooldowns reset, {healed_count} cards "
                f"restored. ({remaining - 1} charges left)")

    return None


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
