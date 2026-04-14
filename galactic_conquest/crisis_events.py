"""
STARGWENT - GALACTIC CONQUEST - Crisis Events

Galaxy-wide crisis events that trigger randomly after turn 5.
10% chance per turn (respects crisis_cooldown on CampaignState).
Each crisis affects ALL factions and creates dramatic turning points.
"""

import asyncio
import random
import pygame
import display_manager


# Crisis definitions: each has a title, description, and an apply function name
CRISIS_EVENTS = [
    {
        "id": "replicator_outbreak",
        "title": "Replicator Outbreak",
        "text": "Self-replicating machines swarm across the galaxy!\n"
                "All factions lose their weakest unit card.",
        "effect": "replicator_outbreak",
        "color": (180, 180, 200),
    },
    {
        "id": "ori_crusade",
        "title": "Ori Crusade",
        "text": "The Ori launch a devastating crusade across the galaxy!\n"
                "All players suffer -40 naquadah. AI factions lose a random planet.",
        "effect": "ori_crusade",
        "color": (255, 200, 100),
    },
    {
        "id": "galactic_plague",
        "title": "Galactic Plague",
        "text": "A virulent plague spreads through the Stargate network!\n"
                "All card upgrades are reduced by 1 (min 0). -20 naquadah.",
        "effect": "galactic_plague",
        "color": (100, 200, 80),
    },
    {
        "id": "ascension_wave",
        "title": "Ascension Wave",
        "text": "A wave of ascension energy sweeps the galaxy!\n"
                "Your 2 strongest cards gain +2 power. Cooldowns reset.",
        "effect": "ascension_wave",
        "color": (200, 220, 255),
    },
    {
        "id": "wraith_invasion",
        "title": "Wraith Invasion",
        "text": "The Wraith have come from the Pegasus galaxy!\n"
                "A random neutral planet becomes hostile. -30 naquadah.",
        "effect": "wraith_invasion",
        "color": (140, 80, 160),
    },
    # --- 5 new events (G4, v11.0) ---
    {
        "id": "stargate_virus",
        "title": "Stargate Virus",
        "text": "A self-replicating virus has compromised the gate network!\n"
                "Network bonuses are disabled and building repairs cost extra.",
        "effect": "stargate_virus",
        "color": (140, 255, 140),
    },
    {
        "id": "black_hole_proximity",
        "title": "Black Hole Proximity",
        "text": "Gravitational shear ripples through the sector!\n"
                "A random building suffers catastrophic damage.",
        "effect": "black_hole_proximity",
        "color": (60, 60, 100),
    },
    {
        "id": "naquadria_meltdown",
        "title": "Naquadria Reactor Meltdown",
        "text": "An experimental reactor has gone critical!\n"
                "You must choose: bleed naquadah or sacrifice a card.",
        "effect": "naquadria_meltdown",
        "color": (255, 140, 40),
    },
    {
        "id": "first_contact",
        "title": "First Contact",
        "text": "An unknown civilization opens communication!\n"
                "Their gifts could reshape your campaign.",
        "effect": "first_contact",
        "color": (180, 220, 255),
    },
    {
        "id": "dakara_signal",
        "title": "Dakara Signal",
        "text": "Ancient harmonic waves wash across the galaxy!\n"
                "Temporary diplomatic thaw between all factions.",
        "effect": "dakara_signal",
        "color": (255, 220, 180),
    },
]

CRISIS_CHOICES = {
    "replicator_outbreak": {
        "a": {"label": "Sacrifice weakest card", "desc": "Lose your weakest card. Outbreak contained."},
        "b": {"label": "Risk containment", "desc": "40% chance enemy loses 2 cards. 60% you lose 2 cards."},
        "c": {"label": "Isolate & study", "desc": "Gain Replicator Nanites relic, no cards lost.",
               "requires": "sensor_array_2"},
    },
    "ori_crusade": {
        "a": {"label": "Pay for shields (-60 naq)", "desc": "Heavy cost but no other damage."},
        "b": {"label": "Endure the crusade", "desc": "-40 naq, but an AI faction loses a planet."},
        "c": {"label": "Allied defense", "desc": "Split cost with ally. Only -30 naq.",
               "requires": "has_ally"},
    },
    "galactic_plague": {
        "a": {"label": "Quarantine (-30 naq)", "desc": "Pay more but keep all card upgrades intact."},
        "b": {"label": "Endure the plague", "desc": "-20 naq, all card upgrades reduced by 1."},
        "c": {"label": "Ancient cure", "desc": "No losses. Upgrades intact. Free.",
               "requires": "ascension_complete"},
    },
    "ascension_wave": {
        "a": {"label": "Channel into power", "desc": "+2 power to 2 strongest cards. Reset cooldowns."},
        "b": {"label": "Store as wisdom", "desc": "+20 wisdom. Reset cooldowns."},
        "c": {"label": "Harmonic resonance", "desc": "+1 power to ALL cards. Reset cooldowns.",
               "requires": "3_ancient_planets"},
    },
    "wraith_invasion": {
        "a": {"label": "Stand and fight", "desc": "Keep the planet but lose 50 naquadah."},
        "b": {"label": "Evacuate", "desc": "Lose the planet but only -20 naquadah."},
        "c": {"label": "Covert counterattack", "desc": "60% keep planet. Only -10 naq.",
               "requires": "3_operatives"},
    },
    # --- v11.0 additions (G4) ---
    "stargate_virus": {
        "a": {"label": "Purge the network (-50 naq)", "desc": "Full clean. Network bonuses restored next turn."},
        "b": {"label": "Endure the outage", "desc": "Network bonuses disabled for 3 turns."},
        "c": {"label": "Asgard debug tools", "desc": "Instant fix, no cost.",
               "requires": "asgard_relic"},
    },
    "black_hole_proximity": {
        "a": {"label": "Reinforce structures (-40 naq)", "desc": "Buildings survive. No damage."},
        "b": {"label": "Ride it out", "desc": "A random building loses 1 upgrade level."},
        "c": {"label": "Orbital stabilizers", "desc": "No damage, free.",
               "requires": "shipyard_2"},
    },
    "naquadria_meltdown": {
        "a": {"label": "Flood coolant (-60 naq)", "desc": "Contained. Deck untouched."},
        "b": {"label": "Vent the core", "desc": "Lose your weakest card, keep the naq."},
        "c": {"label": "Ancient containment", "desc": "No losses at all.",
               "requires": "ascension_complete"},
    },
    "first_contact": {
        "a": {"label": "Accept relic", "desc": "Gain Replicator Nanites relic. No other effect."},
        "b": {"label": "Trade for wisdom", "desc": "+20 Wisdom. No relic."},
        "c": {"label": "Deep exchange", "desc": "Gain relic AND +10 Wisdom.",
               "requires": "sensor_array_2"},
    },
    "dakara_signal": {
        "a": {"label": "Embrace the harmony", "desc": "+10 favor with all factions for 3 turns."},
        "b": {"label": "Ignore the signal", "desc": "-5 Wisdom, no effect on relations."},
        "c": {"label": "Amplify the wave", "desc": "+20 favor with all factions, +5 Wisdom.",
               "requires": "3_ancient_planets"},
    },
}


def check_crisis_option_c(campaign_state, galaxy, crisis_effect):
    """Check if the conditional 3rd crisis option is available.

    Returns True if the player meets the requirements for option C.
    """
    choices = CRISIS_CHOICES.get(crisis_effect, {})
    option_c = choices.get("c")
    if not option_c:
        return False

    req = option_c.get("requires", "")

    if req == "sensor_array_2":
        # Need 2+ Sensor Arrays on player planets
        count = sum(1 for pid, bid in campaign_state.buildings.items()
                    if bid == "sensor_array"
                    and galaxy.planets.get(pid)
                    and galaxy.planets[pid].owner == "player")
        return count >= 2

    elif req == "has_ally":
        return any(rel == "allied" for rel in campaign_state.faction_relations.values())

    elif req == "ascension_complete":
        return "ascension" in campaign_state.completed_doctrines

    elif req == "3_ancient_planets":
        from .doctrines import ANCIENT_PLANETS
        count = sum(1 for pid, p in galaxy.planets.items()
                    if p.name in ANCIENT_PLANETS and p.owner == "player")
        return count >= 3

    elif req == "3_operatives":
        active_ops = sum(1 for op in campaign_state.operatives
                         if op.get("status") in ("active", "idle", "moving", "establishing"))
        return active_ops >= 3

    # --- v11.0 crisis requirements (G4) ---
    elif req == "asgard_relic":
        return any(r in campaign_state.relics for r in ("asgard_core", "thors_hammer"))

    elif req == "shipyard_2":
        count = sum(1 for pid, bid in campaign_state.buildings.items()
                    if bid == "shipyard"
                    and galaxy.planets.get(pid)
                    and galaxy.planets[pid].owner == "player"
                    and campaign_state.building_levels.get(pid, 1) >= 2)
        return count >= 1

    return False


# --- v11.0: 3-act escalation (G4) ---

ACT_1_END_TURN = 10
ACT_2_END_TURN = 20


def get_current_act(turn_number):
    """Return the current campaign act (1, 2, or 3) for a given turn.

    Act 1 (Expansion): turns 1-10.
    Act 2 (Tension):   turns 11-20.
    Act 3 (Endgame):   turns 21+.
    """
    if turn_number <= ACT_1_END_TURN:
        return 1
    if turn_number <= ACT_2_END_TURN:
        return 2
    return 3


_ACT_CRISIS_CHANCE = {
    1: 0.05,  # Quiet opening
    2: 0.10,  # Standard mid game
    3: 0.15,  # Chaotic endgame
}


def should_trigger_crisis(campaign_state):
    """Check if a crisis should trigger this turn.

    v11.0 (G4): chance scales with current act — calmer early game, more
    chaotic endgame. Ori Shield Matrix perk still halves the final chance.
    Cooldown + turn floor are unchanged.
    """
    if campaign_state.turn_number < 5:
        return False
    if campaign_state.crisis_cooldown > 0:
        return False
    act = get_current_act(campaign_state.turn_number)
    chance = _ACT_CRISIS_CHANCE.get(act, 0.10)
    from .meta_progression import has_perk
    if has_perk("crisis_resistance"):
        chance *= 0.5
    return random.random() < chance


def pick_crisis(campaign_state, galaxy=None):
    """Pick a crisis event. Scripted faction crises are preferred when
    their trigger predicate fires; otherwise a random generic one is
    returned.

    12.0: adds the scripted-crisis tier so big faction-state milestones
    (Goa'uld dominance, Asgard network apex, Alteran doctrine mastery,
    etc.) land as bespoke events instead of generic RNG.
    """
    if galaxy is not None:
        eligible = _scripted_eligible(campaign_state, galaxy)
        if eligible:
            chosen = random.choice(eligible)
            # Record the fire so it doesn't immediately re-trigger.
            fired = campaign_state.conquest_ability_data.setdefault(
                "scripted_crisis_fired", [])
            if chosen["id"] not in fired:
                fired.append(chosen["id"])
            return chosen
    if not CRISIS_EVENTS:
        return None
    return random.choice(CRISIS_EVENTS)


# --- 12.0 scripted crises ------------------------------------------------
# Each entry is a standard crisis dict PLUS a ``predicate`` callable
# ``(state, galaxy) -> bool``.  Predicates may read any state; they
# should be cheap — they run once per trigger check.  Scripted crises
# also respect a one-shot ``scripted_crisis_fired`` list so they don't
# re-fire back-to-back.

def _pred_goauld_dominance(state, galaxy):
    count = sum(1 for p in galaxy.planets.values() if p.owner == "Goa'uld")
    return count >= 5


def _pred_asgard_network_apex(state, galaxy):
    return getattr(state, "network_tier", 1) >= 4 and \
        any(p.owner == "Asgard" for p in galaxy.planets.values())


def _pred_alteran_doctrine_mastery(state, galaxy):
    return len(getattr(state, "completed_doctrines", []) or []) >= 2


def _pred_jaffa_ascendant(state, galaxy):
    count = sum(1 for p in galaxy.planets.values()
                if p.owner == "Jaffa Rebellion")
    return count >= 4


def _pred_lucian_cartel(state, galaxy):
    trading = [f for f, r in (state.faction_relations or {}).items()
               if r == "trading"]
    leader_id = (state.player_leader or {}).get("card_id", "")
    lucian_leader = leader_id in ("lucian_vala", "lucian_netan",
                                   "lucian_varro", "lucian_anateo",
                                   "lucian_kiva", "lucian_sodan_master",
                                   "lucian_baal_clone")
    return len(trading) >= 3 and lucian_leader


def _pred_stargate_lockdown(state, galaxy):
    return getattr(state, "network_tier", 1) >= 5 and \
        state.supergate_progress.get("built")


def _pred_ancient_awakening(state, galaxy):
    ancient_names = {"Atlantis", "Heliopolis", "Vis Uban",
                     "Kheb", "Proclarush"}
    count = sum(1 for p in galaxy.planets.values()
                if p.owner == "player" and p.name in ancient_names)
    return count >= 3


SCRIPTED_CRISIS_EVENTS = [
    {
        "id": "apophis_declaration",
        "title": "Apophis's Declaration",
        "text": "The System Lord Apophis demands tribute from all the galaxy.\n"
                "Pay 100 naq to avoid a cascade of Goa'uld raids.",
        "effect": "apophis_declaration",
        "color": (240, 80, 80),
        "predicate": _pred_goauld_dominance,
    },
    {
        "id": "replicator_signal",
        "title": "Replicator Signal",
        "text": "The Asgard network detects Replicator pings from deep space.\n"
                "Asgard-owned worlds face an incursion — share intel or leave them to it.",
        "effect": "replicator_signal",
        "color": (180, 200, 230),
        "predicate": _pred_asgard_network_apex,
    },
    {
        "id": "ori_crusade_scripted",
        "title": "Ori Crusade",
        "text": "The Ori turn their gaze toward the galaxy.\n"
                "Mass conversion events sweep every world you do not hold.",
        "effect": "ori_crusade",  # reuse existing effect
        "color": (255, 180, 80),
        "predicate": _pred_alteran_doctrine_mastery,
    },
    {
        "id": "jaffa_rebellion_rising",
        "title": "Jaffa Rebellion Rising",
        "text": "Free Jaffa armies mobilise under a unified banner.\n"
                "The Tok'ra offer you a free operative in solidarity.",
        "effect": "jaffa_rebellion_rising",
        "color": (240, 210, 120),
        "predicate": _pred_jaffa_ascendant,
    },
    {
        "id": "lucian_cartel_open",
        "title": "Lucian Cartel Opens",
        "text": "The black market floods the galaxy with naquadah at fire-sale prices.\n"
                "+120 naq, and every trade partner gains +10 favor.",
        "effect": "lucian_cartel_open",
        "color": (220, 130, 220),
        "predicate": _pred_lucian_cartel,
    },
    {
        "id": "stargate_lockdown",
        "title": "Stargate Lockdown",
        "text": "Your Supergate has drawn the attention of every surviving power.\n"
                "All rivals gain +20% counterattack chance for 3 turns.",
        "effect": "stargate_lockdown",
        "color": (140, 180, 255),
        "predicate": _pred_stargate_lockdown,
    },
    {
        "id": "ancient_awakening",
        "title": "Ancient Awakening",
        "text": "Atlantis resurfaces. Ancient machinery hums to life across your empire.\n"
                "Gain an Ancient ZPM relic and +60 wisdom.",
        "effect": "ancient_awakening",
        "color": (200, 230, 255),
        "predicate": _pred_ancient_awakening,
    },
]


def _scripted_eligible(state, galaxy):
    fired = state.conquest_ability_data.get("scripted_crisis_fired", []) or []
    out = []
    for crisis in SCRIPTED_CRISIS_EVENTS:
        if crisis["id"] in fired:
            continue
        try:
            if crisis["predicate"](state, galaxy):
                out.append(crisis)
        except Exception:
            continue
    return out


def apply_crisis(campaign_state, galaxy, crisis, rng=None, choice="b"):
    """Apply a crisis event's effects.

    Args:
        campaign_state: CampaignState instance
        galaxy: GalaxyMap instance
        crisis: Crisis event dict
        rng: Optional Random instance
        choice: "a" (safe/costly), "b" (risky/cheap), or "c" (conditional)

    Returns:
        Result message string.
    """
    if rng is None:
        rng = random.Random()

    effect = crisis["effect"]

    if effect == "replicator_outbreak":
        from cards import ALL_CARDS
        if choice == "c":
            # Conditional: Sensor Arrays isolate and study — gain relic, no losses
            campaign_state.add_relic("replicator_nanites")
            return "Sensor Arrays isolated the Replicators! Gained Replicator Nanites relic."
        elif choice == "a":
            # Safe: remove weakest card (original behavior)
            deck_power = [(cid, getattr(ALL_CARDS.get(cid), 'power', 0) or 0)
                          for cid in campaign_state.current_deck]
            deck_power.sort(key=lambda x: x[1])
            removed_name = "none"
            if deck_power and len(campaign_state.current_deck) > 10:
                removed_cid = deck_power[0][0]
                campaign_state.remove_card(removed_cid)
                removed_name = getattr(ALL_CARDS.get(removed_cid), 'name', removed_cid)
            return f"Replicators consumed your weakest card: {removed_name}. Outbreak contained."
        else:
            # Risky: 40% reward, 60% lose 2 cards
            if rng.random() < 0.40:
                campaign_state.add_naquadah(10)
                return "Containment gamble paid off! Replicators destroyed. +10 naq."
            else:
                deck_power = [(cid, getattr(ALL_CARDS.get(cid), 'power', 0) or 0)
                              for cid in campaign_state.current_deck]
                deck_power.sort(key=lambda x: x[1])
                removed = []
                for cid, _pw in deck_power:
                    if len(campaign_state.current_deck) > 10 and len(removed) < 2:
                        campaign_state.remove_card(cid)
                        removed.append(getattr(ALL_CARDS.get(cid), 'name', cid))
                names = ", ".join(removed) if removed else "none"
                return f"Containment failed! Replicators consumed 2 cards: {names}."

    elif effect == "ori_crusade":
        if choice == "c":
            # Conditional: Allied defense — split cost
            campaign_state.add_naquadah(-30)
            return "-30 Naquadah. Allied forces shared the burden — shields held!"
        elif choice == "a":
            # Safe: pay 60 naq, no planet damage
            campaign_state.add_naquadah(-60)
            return "-60 Naquadah. Shields held — no planetary damage."
        else:
            # Risky: original behavior
            campaign_state.add_naquadah(-40)
            ai_planets = [(pid, p) for pid, p in galaxy.planets.items()
                          if p.owner not in ("player", "neutral")]
            flipped_name = "none"
            if ai_planets:
                pid, planet = rng.choice(ai_planets)
                flipped_name = planet.name
                galaxy.transfer_ownership(pid, "neutral")
                campaign_state.planet_ownership[pid] = "neutral"
            return f"-40 Naquadah. Ori crusade destabilized {flipped_name}."

    elif effect == "galactic_plague":
        if choice == "c":
            # Conditional: Ancient cure — no losses at all
            return "Ancient knowledge neutralized the plague. No losses!"
        elif choice == "a":
            # Safe: pay 30 naq, keep upgrades
            campaign_state.add_naquadah(-30)
            return "-30 Naquadah. Quarantine successful — card upgrades intact."
        else:
            # Risky: original behavior
            campaign_state.add_naquadah(-20)
            downgraded = 0
            for cid in list(campaign_state.upgraded_cards):
                if campaign_state.upgraded_cards[cid] > 0:
                    campaign_state.upgraded_cards[cid] -= 1
                    downgraded += 1
                if campaign_state.upgraded_cards[cid] <= 0:
                    del campaign_state.upgraded_cards[cid]
            return f"-20 Naquadah. Plague weakened {downgraded} card upgrade(s)."

    elif effect == "ascension_wave":
        from cards import ALL_CARDS
        if choice == "c":
            # Conditional: Harmonic resonance — +1 power to ALL cards
            upgraded_count = 0
            for cid in campaign_state.current_deck:
                card = ALL_CARDS.get(cid)
                if card and getattr(card, 'power', 0) and getattr(card, 'power', 0) > 0:
                    campaign_state.upgrade_card(cid, 1)
                    upgraded_count += 1
            campaign_state.cooldowns.clear()
            return f"Harmonic resonance! {upgraded_count} cards gained +1 power. Cooldowns reset!"
        elif choice == "a":
            # Channel into power: +2 to 2 strongest + reset cooldowns (original)
            deck_power = [(cid, getattr(ALL_CARDS.get(cid), 'power', 0) or 0)
                          for cid in campaign_state.current_deck]
            deck_power.sort(key=lambda x: -x[1])
            upgraded = []
            seen = set()
            for cid, pw in deck_power:
                if cid in seen or pw <= 0:
                    continue
                campaign_state.upgrade_card(cid, 2)
                upgraded.append(getattr(ALL_CARDS.get(cid), 'name', cid))
                seen.add(cid)
                if len(upgraded) >= 2:
                    break
            campaign_state.cooldowns.clear()
            parts = []
            if upgraded:
                parts.append(f"Ascended: {', '.join(upgraded)} (+2)")
            parts.append("All cooldowns reset!")
            return " | ".join(parts)
        else:
            # Store as wisdom: +20 wisdom + reset cooldowns
            campaign_state.wisdom = getattr(campaign_state, 'wisdom', 0) + 20
            campaign_state.cooldowns.clear()
            return "+20 Wisdom. All cooldowns reset!"

    # --- v11.0 crisis effects (G4) ---

    elif effect == "stargate_virus":
        if choice == "c":
            return "Asgard debug tools wiped the virus clean — network intact!"
        elif choice == "a":
            campaign_state.add_naquadah(-50)
            return "-50 Naquadah. Virus purged, network restored."
        else:
            campaign_state.conquest_ability_data["_stargate_virus_turns"] = 3
            return "Gate network disabled for 3 turns — no network bonuses."

    elif effect == "black_hole_proximity":
        if choice == "c":
            return "Orbital stabilizers held. No structural damage."
        elif choice == "a":
            campaign_state.add_naquadah(-40)
            return "-40 Naquadah. Reinforcements held — buildings safe."
        else:
            # Downgrade a random player building
            candidates = [
                pid for pid, bid in campaign_state.buildings.items()
                if galaxy.planets.get(pid)
                and galaxy.planets[pid].owner == "player"
                and campaign_state.building_levels.get(pid, 1) > 1
            ]
            if candidates:
                pid = rng.choice(candidates)
                level = campaign_state.building_levels.get(pid, 1)
                campaign_state.building_levels[pid] = level - 1
                name = galaxy.planets[pid].name
                return f"Gravitational shear damaged a building on {name}. Level {level} → {level - 1}."
            return "The black hole rumbled past — no buildings at risk."

    elif effect == "naquadria_meltdown":
        from cards import ALL_CARDS
        if choice == "c":
            return "Ancient containment protocols neutralized the reactor. No losses."
        elif choice == "a":
            campaign_state.add_naquadah(-60)
            return "-60 Naquadah. Reactor contained — deck intact."
        else:
            deck_power = [(cid, getattr(ALL_CARDS.get(cid), 'power', 0) or 0)
                          for cid in campaign_state.current_deck]
            deck_power.sort(key=lambda x: x[1])
            if deck_power and len(campaign_state.current_deck) > 10:
                removed_cid = deck_power[0][0]
                campaign_state.remove_card(removed_cid)
                name = getattr(ALL_CARDS.get(removed_cid), 'name', removed_cid)
                return f"Reactor vented — lost weakest card: {name}. Naquadah preserved."
            return "Reactor vented. Deck already at minimum — no card lost."

    elif effect == "first_contact":
        if choice == "c":
            campaign_state.add_relic("replicator_nanites")
            campaign_state.wisdom = getattr(campaign_state, 'wisdom', 0) + 10
            return "Deep exchange! Replicator Nanites relic + 10 Wisdom."
        elif choice == "a":
            campaign_state.add_relic("replicator_nanites")
            return "Accepted the relic — Replicator Nanites added to your collection."
        else:
            campaign_state.wisdom = getattr(campaign_state, 'wisdom', 0) + 20
            return "+20 Wisdom. The visitors shared their research data."

    elif effect == "dakara_signal":
        from .diplomacy import adjust_favor_all  # local import to avoid cycles
        if choice == "c":
            adjust_favor_all(campaign_state, 20)
            campaign_state.wisdom = getattr(campaign_state, 'wisdom', 0) + 5
            return "+20 favor with all factions. +5 Wisdom. The harmony holds."
        elif choice == "a":
            adjust_favor_all(campaign_state, 10)
            return "+10 favor with all factions — a wave of diplomatic thaw."
        else:
            campaign_state.wisdom = max(0, getattr(campaign_state, 'wisdom', 0) - 5)
            return "-5 Wisdom. The signal passed you by."

    elif effect == "wraith_invasion":
        if choice == "c":
            # Conditional: Covert counterattack — 60% keep planet, only -10 naq
            campaign_state.add_naquadah(-10)
            if rng.random() < 0.60:
                return "-10 Naquadah. Operatives repelled the Wraith! All planets secure."
            else:
                player_non_hw = [(pid, p) for pid, p in galaxy.planets.items()
                                 if p.owner == "player" and p.planet_type != "homeworld"]
                lost_name = "none"
                if player_non_hw:
                    pid, planet = rng.choice(player_non_hw)
                    lost_name = planet.name
                    ai_factions = list(set(p.owner for p in galaxy.planets.values()
                                           if p.owner not in ("player", "neutral")))
                    new_owner = rng.choice(ai_factions) if ai_factions else "neutral"
                    galaxy.transfer_ownership(pid, new_owner)
                    campaign_state.planet_ownership[pid] = new_owner
                return f"-10 Naquadah. Counterattack failed — Wraith took {lost_name}."
        elif choice == "a":
            # Stand and fight: pay 50 naq, keep planet
            campaign_state.add_naquadah(-50)
            return "-50 Naquadah. Wraith repelled — all planets secure!"
        else:
            # Evacuate: lose planet but only -20 naq
            campaign_state.add_naquadah(-20)
            player_non_hw = [(pid, p) for pid, p in galaxy.planets.items()
                             if p.owner == "player" and p.planet_type != "homeworld"]
            lost_name = "none"
            if player_non_hw:
                pid, planet = rng.choice(player_non_hw)
                lost_name = planet.name
                ai_factions = list(set(p.owner for p in galaxy.planets.values()
                                       if p.owner not in ("player", "neutral")))
                new_owner = rng.choice(ai_factions) if ai_factions else "neutral"
                galaxy.transfer_ownership(pid, new_owner)
                campaign_state.planet_ownership[pid] = new_owner
            return f"-20 Naquadah. Evacuated {lost_name} — Wraith took control."

    # --- 12.0 scripted crises ----------------------------------------

    elif effect == "apophis_declaration":
        if choice == "a":
            campaign_state.add_naquadah(-100)
            return "-100 naq. Tribute paid — the raids subside."
        # Refuse: Goa'uld counterattacks spike for 3 turns
        campaign_state.conquest_ability_data["apophis_declaration_turns"] = 3
        return "Defiance. Goa'uld raids intensify for 3 turns."

    elif effect == "replicator_signal":
        if choice == "a":
            campaign_state.add_naquadah(-30)
            # +10 favor with Asgard
            cur = campaign_state.diplomatic_favor.get("Asgard", 0)
            campaign_state.diplomatic_favor["Asgard"] = min(100, cur + 15)
            return "-30 naq, +15 favor with Asgard. They remember."
        # Stand aside: Asgard loses a random planet to neutral
        asgard_planets = [pid for pid, p in galaxy.planets.items()
                          if p.owner == "Asgard" and p.planet_type != "homeworld"]
        if asgard_planets:
            pid = rng.choice(asgard_planets)
            galaxy.transfer_ownership(pid, "neutral")
            campaign_state.planet_ownership[pid] = "neutral"
            return f"The Asgard take the hit alone — {galaxy.planets[pid].name} falls."
        return "The Replicator probe fizzles in empty space."

    elif effect == "jaffa_rebellion_rising":
        # Grant a free operative (reuse the espionage operative dict shape)
        op_id = campaign_state.operative_next_id
        campaign_state.operative_next_id += 1
        campaign_state.operatives.append({
            "id": op_id,
            "planet_id": None,
            "mission": None,
            "turns_remaining": 0,
            "status": "idle",
        })
        cur = campaign_state.diplomatic_favor.get("Jaffa Rebellion", 0)
        campaign_state.diplomatic_favor["Jaffa Rebellion"] = min(100, cur + 10)
        return "A Tok'ra agent joins your service. +10 favor with Jaffa."

    elif effect == "lucian_cartel_open":
        campaign_state.add_naquadah(120)
        trading = [f for f, r in (campaign_state.faction_relations or {}).items()
                   if r == "trading"]
        for f in trading:
            cur = campaign_state.diplomatic_favor.get(f, 0)
            campaign_state.diplomatic_favor[f] = min(100, cur + 10)
        return f"+120 naq, +10 favor with {len(trading)} trade partner(s)."

    elif effect == "stargate_lockdown":
        campaign_state.conquest_ability_data["stargate_lockdown_turns"] = 3
        return "Stargate Lockdown: all rivals +20% counterattack for 3 turns."

    elif effect == "ancient_awakening":
        if not campaign_state.has_relic("ancient_zpm"):
            campaign_state.add_relic("ancient_zpm")
        campaign_state.wisdom = getattr(campaign_state, 'wisdom', 0) + 60
        return "Ancient ZPM acquired. +60 Wisdom."

    return "The crisis passes without incident."


async def show_crisis_screen(screen, crisis, choices=None, has_option_c=False):
    """Show a dramatic crisis event screen with choice buttons.

    Args:
        screen: Pygame display surface
        crisis: Crisis event dict
        choices: Optional dict with "a" and "b" keys (and optionally "c"),
                 each having "label" and "desc".  If None, falls back to legacy
                 "press any key" behavior and returns "b".
        has_option_c: If True and choices has "c", show the third button.

    Returns:
        "a", "b", or "c" depending on which button the player clicks.
    """
    sw, sh = screen.get_width(), screen.get_height()
    clock = pygame.time.Clock()

    title_font = pygame.font.SysFont("Impact, Arial", max(48, sh // 18), bold=True)
    text_font = pygame.font.SysFont("Arial", max(22, sh // 40))
    btn_font = pygame.font.SysFont("Arial", max(18, sh // 50), bold=True)
    desc_font = pygame.font.SysFont("Arial", max(14, sh // 65))
    hint_font = pygame.font.SysFont("Arial", max(16, sh // 60))

    crisis_color = tuple(crisis.get("color", (255, 200, 100)))

    # Button layout — adapts to 2 or 3 buttons
    show_c = has_option_c and choices and "c" in choices
    if show_c:
        btn_w = int(sw * 0.26)
        btn_h = int(sh * 0.10)
        gap = int(sw * 0.02)
        total_w = btn_w * 3 + gap * 2
        btn_y = int(sh * 0.65)
        start_x = sw // 2 - total_w // 2
        btn_a_rect = pygame.Rect(start_x, btn_y, btn_w, btn_h)
        btn_b_rect = pygame.Rect(start_x + btn_w + gap, btn_y, btn_w, btn_h)
        btn_c_rect = pygame.Rect(start_x + 2 * (btn_w + gap), btn_y, btn_w, btn_h)
    else:
        btn_w = int(sw * 0.30)
        btn_h = int(sh * 0.10)
        gap = int(sw * 0.04)
        btn_y = int(sh * 0.68)
        btn_a_rect = pygame.Rect(sw // 2 - btn_w - gap // 2, btn_y, btn_w, btn_h)
        btn_b_rect = pygame.Rect(sw // 2 + gap // 2, btn_y, btn_w, btn_h)
        btn_c_rect = None

    frame = 0
    while True:
        clock.tick(60)
        await asyncio.sleep(0)
        frame += 1

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return "b"
            if choices is None:
                # Legacy: press any key to dismiss
                if (ev.type == pygame.KEYDOWN or ev.type == pygame.MOUSEBUTTONDOWN) and frame > 30:
                    return "b"
            else:
                if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and frame > 30:
                    if btn_a_rect.collidepoint(ev.pos):
                        return "a"
                    if btn_b_rect.collidepoint(ev.pos):
                        return "b"
                    if btn_c_rect and btn_c_rect.collidepoint(ev.pos):
                        return "c"

        # Dark background with crisis-colored vignette
        screen.fill((10, 10, 15))
        overlay = pygame.Surface((sw, sh))
        overlay.fill(crisis_color)
        overlay.set_alpha(30)
        screen.blit(overlay, (0, 0))

        # Warning flash effect (first second)
        if frame < 60 and frame % 20 < 10:
            flash = pygame.Surface((sw, sh))
            flash.fill(crisis_color)
            flash.set_alpha(40)
            screen.blit(flash, (0, 0))

        # Crisis warning header
        import math
        pulse = 0.7 + 0.3 * math.sin(frame * 0.05)
        warn_color = tuple(int(c * pulse) for c in (255, 80, 80))
        warn_text = title_font.render("CRISIS EVENT", True, warn_color)
        screen.blit(warn_text, (sw // 2 - warn_text.get_width() // 2, int(sh * 0.12)))

        # Crisis title
        title_surf = title_font.render(crisis["title"], True, crisis_color)
        screen.blit(title_surf, (sw // 2 - title_surf.get_width() // 2, int(sh * 0.25)))

        # Crisis text (multi-line)
        lines = crisis["text"].split("\n")
        for i, line in enumerate(lines):
            line_surf = text_font.render(line.strip(), True, (220, 220, 220))
            screen.blit(line_surf, (sw // 2 - line_surf.get_width() // 2,
                                    int(sh * 0.42) + i * int(sh * 0.05)))

        if choices is not None and frame > 30:
            # Draw choice buttons
            mx, my = pygame.mouse.get_pos()
            buttons = [
                (btn_a_rect, "a", (40, 100, 60)),
                (btn_b_rect, "b", (100, 60, 40)),
            ]
            if show_c:
                buttons.append((btn_c_rect, "c", (60, 60, 120)))
            for rect, key, base_color in buttons:
                choice_data = choices[key]
                hovered = rect.collidepoint(mx, my)
                color = tuple(min(255, c + 40) for c in base_color) if hovered else base_color
                pygame.draw.rect(screen, color, rect)
                border_color = (255, 220, 100) if key == "c" else ((200, 200, 200) if hovered else (120, 120, 120))
                pygame.draw.rect(screen, border_color, rect, 2)
                # Label
                lbl = btn_font.render(choice_data["label"], True, (255, 255, 255))
                screen.blit(lbl, (rect.centerx - lbl.get_width() // 2,
                                  rect.y + int(btn_h * 0.20)))
                # Description
                dsc = desc_font.render(choice_data["desc"], True, (200, 200, 200))
                screen.blit(dsc, (rect.centerx - dsc.get_width() // 2,
                                  rect.y + int(btn_h * 0.60)))
        elif choices is None and frame > 30:
            # Legacy hint
            hint = hint_font.render("Press any key to continue", True, (150, 150, 150))
            screen.blit(hint, (sw // 2 - hint.get_width() // 2, int(sh * 0.82)))

        display_manager.gpu_flip()
