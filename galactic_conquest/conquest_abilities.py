"""
STARGWENT - GALACTIC CONQUEST - Conquest Leader Abilities

Each leader gets a unique conquest-map ability that scales L1-L4 with Stargate
Network tier.  Abilities trigger at specific campaign hook points (on_victory,
on_defeat, on_defense, pre_battle, on_turn_end, on_counterattack, on_neutral_event,
on_fortify).

The registry maps leader card_id → ability definition.
"""

import random

from cards import ALL_CARDS


# ---------------------------------------------------------------------------
# Helper: pick upgradeable cards from deck
# ---------------------------------------------------------------------------
def _upgradeable(state):
    return [cid for cid in state.current_deck
            if ALL_CARDS.get(cid) and getattr(ALL_CARDS[cid], 'power', None)]


def _card_name(cid):
    c = ALL_CARDS.get(cid)
    return c.name if c else cid


# ---------------------------------------------------------------------------
# Ability definitions — each is a dict:
#   name, description (list of 4 level strings), triggers (list), handler func
# The handler receives (state, galaxy, level, context) where context varies.
# ---------------------------------------------------------------------------

# ============================= TAU'RI ======================================

def _oneill_handler(state, galaxy, level, context):
    """MacGyver Protocol: if losing after R1, +power to random unit in R2."""
    trigger = context.get("trigger")
    if trigger == "pre_battle":
        # Store ability data for the battle to read
        bonus = min(1 + level, 4)  # +1/+2/+3/+3
        state.conquest_ability_data["oneill_comeback_bonus"] = bonus
        state.conquest_ability_data["oneill_draw_card"] = level >= 4
        return None
    return None


def _hammond_handler(state, galaxy, level, context):
    """Homeworld Command: defense battles boost cards."""
    trigger = context.get("trigger")
    if trigger == "on_defense":
        bonus = 1 if level <= 2 else 2
        extra_cards = 1 if level >= 4 else 0
        return {"defense_power_bonus": bonus, "defense_extra_cards": extra_cards,
                "scope": "any" if level >= 2 else "homeworld"}
    return None


def _carter_handler(state, galaxy, level, context):
    """Naquadah Generator: bonus naq per victory."""
    trigger = context.get("trigger")
    if trigger == "on_victory":
        bonus_naq = {1: 15, 2: 25, 3: 35, 4: 50}.get(level, 15)
        state.add_naquadah(bonus_naq)
        msg = f"Naquadah Generator: +{bonus_naq} naq"
        if level >= 3:
            # Reduce fortify cost tracked in ability data
            state.conquest_ability_data["carter_fortify_discount"] = 10 if level == 3 else 15
        return msg
    return None


def _landry_handler(state, galaxy, level, context):
    """SGC Logistics: reduce attack cooldowns."""
    trigger = context.get("trigger")
    if trigger == "on_turn_end":
        reduction = 1 if level <= 2 else 2
        rng = context.get("rng", random)
        skip_chance = 0.20 if level >= 2 else 0
        for pid in list(state.cooldowns):
            if skip_chance > 0 and rng.random() < skip_chance:
                state.cooldowns[pid] = 0
            else:
                state.cooldowns[pid] = max(0, state.cooldowns[pid] - reduction)
        state.cooldowns = {k: v for k, v in state.cooldowns.items() if v > 0}
        return f"SGC Logistics: cooldowns reduced by {reduction}"
    return None


def _mckay_handler(state, galaxy, level, context):
    """Brilliant Improvisation: chance to auto-upgrade after victory."""
    trigger = context.get("trigger")
    if trigger == "on_victory":
        rng = context.get("rng", random)
        chance = {1: 0.30, 2: 0.45, 3: 0.60, 4: 0.75}.get(level, 0.30)
        upgradeable = _upgradeable(state)
        msgs = []
        if upgradeable and rng.random() < chance:
            target = rng.choice(upgradeable)
            state.upgrade_card(target, 1)
            msgs.append(f"Improvisation: upgraded {_card_name(target)}")
        if level >= 3 and rng.random() < 0.25:
            msgs.append("Improvisation: bonus reward card duplicated")
            return {"message": " | ".join(msgs), "duplicate_reward": True}
        return " | ".join(msgs) if msgs else None
    return None


def _quinn_handler(state, galaxy, level, context):
    """Kelownan Intelligence: pre-battle intel."""
    trigger = context.get("trigger")
    if trigger == "pre_battle":
        reveal_count = {1: 0, 2: 1, 3: 3, 4: 99}.get(level, 0)
        return {"intel_reveal_count": reveal_count,
                "show_ability": level >= 1,
                "show_deck_top": reveal_count}
    return None


def _langford_handler(state, galaxy, level, context):
    """Archaeological Discovery: neutral event bonuses."""
    trigger = context.get("trigger")
    if trigger == "on_neutral_event":
        extra_choices = 1  # Always +1 choice at L1+
        bonus_naq = 20 if level >= 2 else 0
        rng = context.get("rng", random)
        relic_chance = {3: 0.15, 4: 0.25}.get(level, 0)
        got_relic = relic_chance > 0 and rng.random() < relic_chance
        state.add_naquadah(bonus_naq)
        return {"extra_choices": extra_choices, "bonus_naq": bonus_naq,
                "relic_chance_triggered": got_relic}
    return None


# ============================= GOA'ULD =====================================

def _apophis_handler(state, galaxy, level, context):
    """System Lord's Dominion: conquest grants permanent power boosts."""
    trigger = context.get("trigger")
    if trigger == "on_victory":
        rng = context.get("rng", random)
        bonus = 1 if level <= 2 else 2
        num_cards = 1 if level <= 3 else 2
        upgradeable = _upgradeable(state)
        msgs = []
        if upgradeable:
            targets = rng.sample(upgradeable, min(num_cards, len(upgradeable)))
            for cid in targets:
                state.upgrade_card(cid, bonus)
                msgs.append(f"{_card_name(cid)} +{bonus}")
        return f"Dominion: {', '.join(msgs)}" if msgs else None
    return None


def _yu_handler(state, galaxy, level, context):
    """Ancient Wisdom: pre-battle reveal enemy cards."""
    trigger = context.get("trigger")
    if trigger == "pre_battle":
        reveal = {1: 1, 2: 2, 3: 3, 4: 99}.get(level, 1)
        return {"intel_reveal_count": reveal,
                "show_hand_round1": level >= 4}
    return None


def _sokar_handler(state, galaxy, level, context):
    """Netu's Torment: reduce counterattack chance."""
    trigger = context.get("trigger")
    if trigger == "on_counterattack":
        reduction = {1: 0.05, 2: 0.10, 3: 0.15, 4: 0.20}.get(level, 0.05)
        return {"counterattack_reduction": reduction}
    if trigger == "on_defense" and context.get("result") == "player_win" and level >= 3:
        bonus_naq = 15 if level == 3 else 25
        state.add_naquadah(bonus_naq)
        return f"Netu's Torment: +{bonus_naq} naq for defense win"
    return None


def _baal_handler(state, galaxy, level, context):
    """Clone Network: chance to negate cooldown on loss."""
    trigger = context.get("trigger")
    if trigger == "on_defeat":
        rng = context.get("rng", random)
        chance = {1: 0.25, 2: 0.35, 3: 0.50, 4: 0.60}.get(level, 0.25)
        if rng.random() < chance:
            msgs = ["Clone Network: cooldown negated!"]
            if level >= 3:
                refund = 15 if level == 3 else 25
                state.add_naquadah(refund)
                msgs.append(f"+{refund} naq refund")
            return {"negate_cooldown": True, "message": " | ".join(msgs)}
    return None


def _anubis_handler(state, galaxy, level, context):
    """Ascended Wrath: reduce/negate elite defender bonuses."""
    trigger = context.get("trigger")
    if trigger == "pre_battle":
        planet = context.get("planet")
        if planet and planet.planet_type == "homeworld":
            elite_reduction = {1: 1, 2: 1, 3: 2, 4: 2}.get(level, 1)
            negate_extra = level >= 3
            player_bonus = 1 if level >= 4 else 0
            return {"elite_power_reduction": elite_reduction,
                    "negate_extra_cards": negate_extra,
                    "player_power_bonus": player_bonus}
    return None


def _hathor_handler(state, galaxy, level, context):
    """Seductive Diplomacy: chance enemy skips counterattack."""
    trigger = context.get("trigger")
    if trigger == "on_counterattack":
        rng = context.get("rng", random)
        skip_chance = {1: 0.15, 2: 0.20, 3: 0.25, 4: 0.35}.get(level, 0.15)
        if rng.random() < skip_chance:
            return {"skip_counterattack": True, "message": "Seductive Diplomacy: enemy retreats!"}
        if level >= 3:
            cede_chance = 0.10 if level == 3 else 0.15
            if rng.random() < cede_chance:
                return {"cede_territory": True, "message": "Seductive Diplomacy: enemy cedes territory!"}
    return None


def _cronus_handler(state, galaxy, level, context):
    """Imperial Expansion: bonus naq per planet beyond 3."""
    trigger = context.get("trigger")
    if trigger == "on_turn_end":
        planet_count = galaxy.get_player_planet_count()
        extra = max(0, planet_count - 3)
        per_planet = {1: 2, 2: 3, 3: 4, 4: 5}.get(level, 2)
        bonus = extra * per_planet
        if bonus > 0:
            state.add_naquadah(bonus)
        # L3: free relic at 10th planet, L4: also at 15th
        rng = context.get("rng", random)
        if level >= 3 and planet_count == 10:
            if not state.conquest_ability_data.get("cronus_10th_relic"):
                state.conquest_ability_data["cronus_10th_relic"] = True
                return {"grant_relic": True, "message": f"Imperial Expansion: +{bonus} naq + relic at 10 planets!"}
        if level >= 4 and planet_count == 15:
            if not state.conquest_ability_data.get("cronus_15th_relic"):
                state.conquest_ability_data["cronus_15th_relic"] = True
                return {"grant_relic": True, "message": f"Imperial Expansion: +{bonus} naq + relic at 15 planets!"}
        return f"Imperial Expansion: +{bonus} naq ({extra} planets beyond 3)" if bonus > 0 else None
    return None


# ============================= JAFFA =======================================

def _tealc_handler(state, galaxy, level, context):
    """Shol'va's Resolve: defense battle bonuses."""
    trigger = context.get("trigger")
    if trigger == "on_defense":
        bonus = 1 if level <= 2 else 2
        extra_card = 1 if level >= 2 else 0
        return {"defense_power_bonus": bonus, "defense_extra_cards": extra_card}
    if trigger == "on_defense" and context.get("result") == "player_win" and level >= 4:
        upgradeable = _upgradeable(state)
        if upgradeable:
            rng = context.get("rng", random)
            target = rng.choice(upgradeable)
            state.upgrade_card(target, 1)
            return f"Shol'va's Resolve: upgraded {_card_name(target)} on defense win"
    return None


def _bratac_handler(state, galaxy, level, context):
    """Warrior's Training: periodic card upgrades."""
    trigger = context.get("trigger")
    if trigger == "on_victory":
        data = state.conquest_ability_data
        data["bratac_wins"] = data.get("bratac_wins", 0) + 1
        threshold = {1: 3, 2: 2, 3: 2, 4: 1}.get(level, 3)
        if data["bratac_wins"] >= threshold:
            data["bratac_wins"] = 0
            rng = context.get("rng", random)
            upgradeable = _upgradeable(state)
            num_upgrades = 2 if level >= 3 else 1
            if upgradeable:
                targets = rng.sample(upgradeable, min(num_upgrades, len(upgradeable)))
                for cid in targets:
                    state.upgrade_card(cid, 2)
                names = [_card_name(c) for c in targets]
                return f"Warrior's Training: {', '.join(names)} +2"
    return None


def _raknor_handler(state, galaxy, level, context):
    """Rebel Recruitment: free cards from defeated faction."""
    trigger = context.get("trigger")
    if trigger == "on_victory":
        defeated_faction = context.get("defeated_faction")
        if not defeated_faction:
            return None
        rng = context.get("rng", random)
        num_cards = 1 if level <= 2 else 2
        pool = [cid for cid, c in ALL_CARDS.items()
                if getattr(c, 'faction', None) == defeated_faction
                and getattr(c, 'card_type', '') != "Legendary Commander"
                and getattr(c, 'row', '') != "weather"]
        msgs = []
        if pool:
            picks = rng.sample(pool, min(num_cards, len(pool)))
            for cid in picks:
                state.add_card(cid)
                if level >= 3:
                    state.upgrade_card(cid, 1)
                msgs.append(_card_name(cid))
        pre = "pre-upgraded " if level >= 3 else ""
        return f"Rebel Recruitment: +{pre}{', '.join(msgs)}" if msgs else None
    return None


def _kalel_handler(state, galaxy, level, context):
    """Hak'tyl Warriors: cheaper fortify + fort power bonus."""
    trigger = context.get("trigger")
    if trigger == "on_fortify":
        discount = {1: 0.20, 2: 0.30, 3: 0.40, 4: 0.50}.get(level, 0.20)
        return {"fortify_discount": discount}
    if trigger == "on_defense":
        if level >= 3:
            planet_id = context.get("planet_id")
            fort_level = state.fortification_levels.get(planet_id, 0) if planet_id else 0
            if fort_level > 0:
                return {"defense_power_bonus": fort_level}
    return None


def _gerak_handler(state, galaxy, level, context):
    """Political Maneuvering: starting naq + event bonuses."""
    # Starting naq handled at campaign creation via conquest_ability_data
    trigger = context.get("trigger")
    if trigger == "on_neutral_event" and level >= 2:
        bonus = {2: 15, 3: 25, 4: 40}.get(level, 15)
        state.add_naquadah(bonus)
        return f"Political Maneuvering: +{bonus} naq from event"
    return None


def _ishta_handler(state, galaxy, level, context):
    """Guerrilla Resistance: can attack extra planets per turn."""
    trigger = context.get("trigger")
    if trigger == "pre_attack":
        max_attacks = {1: 2, 2: 2, 3: 3, 4: 3}.get(level, 2)
        return {"max_attacks_per_turn": max_attacks}
    return None


def _ryac_handler(state, galaxy, level, context):
    """Next Generation: card upgrades get extra power."""
    trigger = context.get("trigger")
    if trigger == "on_victory":
        extra_power = {1: 1, 2: 1, 3: 2, 4: 2}.get(level, 1)
        rng = context.get("rng", random)
        # Apply to any upgrade that just happened
        return {"upgrade_bonus": extra_power,
                "extra_choice_chance": 0.30 if level >= 2 else 0}
    return None


# ============================= LUCIAN ALLIANCE ==============================

def _varro_handler(state, galaxy, level, context):
    """Black Market Contacts: naq after every battle."""
    trigger = context.get("trigger")
    if trigger in ("on_victory", "on_defeat"):
        bonus = {1: 10, 2: 15, 3: 20, 4: 25}.get(level, 10)
        state.add_naquadah(bonus)
        msgs = [f"Black Market: +{bonus} naq"]
        if trigger == "on_defeat" and level >= 4:
            return {"message": " | ".join(msgs), "halve_loss_penalty": True}
        if level >= 3:
            rng = context.get("rng", random)
            if rng.random() < 0.20:
                pool = [cid for cid, c in ALL_CARDS.items()
                        if getattr(c, 'faction', None) == state.player_faction
                        and getattr(c, 'card_type', '') != "Legendary Commander"
                        and getattr(c, 'row', '') != "weather"]
                if pool:
                    free_card = rng.choice(pool)
                    state.add_card(free_card)
                    msgs.append(f"Free card: {_card_name(free_card)}")
        return " | ".join(msgs)
    return None


def _sodan_handler(state, galaxy, level, context):
    """Sodan Cloak: chance AI can't counterattack."""
    trigger = context.get("trigger")
    if trigger == "on_counterattack":
        rng = context.get("rng", random)
        chance = {1: 0.20, 2: 0.30, 3: 0.40, 4: 0.50}.get(level, 0.20)
        if rng.random() < chance:
            return {"skip_counterattack": True, "message": "Sodan Cloak: attack evaded!"}
    if trigger == "pre_battle" and level >= 3:
        return {"ignore_weather": level >= 3, "power_bonus": 1 if level >= 4 else 0}
    return None


def _baal_clone_handler(state, galaxy, level, context):
    """Infiltration: chance to flip adjacent planet on conquest."""
    trigger = context.get("trigger")
    if trigger == "on_victory":
        rng = context.get("rng", random)
        chance = {1: 0.20, 2: 0.25, 3: 0.30, 4: 0.40}.get(level, 0.20)
        planet_id = context.get("planet_id")
        if planet_id and rng.random() < chance:
            # Find adjacent non-player planet
            planet = galaxy.planets.get(planet_id)
            if planet:
                adjacent = [cid for cid in planet.connections
                            if galaxy.planets.get(cid) and galaxy.planets[cid].owner != "player"]
                if adjacent:
                    flip_id = rng.choice(adjacent)
                    flip_name = galaxy.planets[flip_id].name
                    galaxy.transfer_ownership(flip_id, "player")
                    state.planet_ownership[flip_id] = "player"
                    bonus_naq = 15 if level >= 3 else 0
                    if bonus_naq:
                        state.add_naquadah(bonus_naq)
                    msg = f"Infiltration: also captured {flip_name}!"
                    if bonus_naq:
                        msg += f" +{bonus_naq} naq"
                    # L4: chance for second flip
                    if level >= 4 and len(adjacent) > 1:
                        remaining = [a for a in adjacent if a != flip_id
                                     and galaxy.planets.get(a) and galaxy.planets[a].owner != "player"]
                        if remaining and rng.random() < 0.25:
                            flip2 = rng.choice(remaining)
                            galaxy.transfer_ownership(flip2, "player")
                            state.planet_ownership[flip2] = "player"
                            msg += f" + {galaxy.planets[flip2].name}!"
                    return msg
    return None


def _netan_handler(state, galaxy, level, context):
    """Smuggler's Network: bonus naq from neutral events."""
    trigger = context.get("trigger")
    if trigger == "on_neutral_event":
        bonus = {1: 30, 2: 40, 3: 50, 4: 60}.get(level, 30)
        state.add_naquadah(bonus)
        return f"Smuggler's Network: +{bonus} naq"
    return None


def _vala_handler(state, galaxy, level, context):
    """Treasure Hunter: extra relic chances."""
    trigger = context.get("trigger")
    if trigger == "on_victory":
        planet = context.get("planet")
        rng = context.get("rng", random)
        if planet and planet.planet_type == "homeworld":
            chance = {1: 0.15, 2: 0.25, 3: 0.30, 4: 0.40}.get(level, 0.15)
            if rng.random() < chance:
                return {"grant_relic": True, "message": "Treasure Hunter: found a relic!"}
    return None


def _anateo_handler(state, galaxy, level, context):
    """Hostage Tactics: chance to keep planet after defense loss."""
    trigger = context.get("trigger")
    if trigger == "on_defense" and context.get("result") == "player_loss":
        rng = context.get("rng", random)
        chance = {1: 0.30, 2: 0.40, 3: 0.50, 4: 0.60}.get(level, 0.30)
        if rng.random() < chance:
            msgs = ["Hostage Tactics: planet retained!"]
            if level >= 3:
                state.add_naquadah(20)
                msgs.append("+20 naq")
            if level >= 4:
                planet_id = context.get("planet_id")
                if planet_id:
                    cur = state.fortification_levels.get(planet_id, 0)
                    if cur < 3:
                        state.fortification_levels[planet_id] = cur + 1
                        msgs.append("free fort level")
            return {"keep_planet": True, "message": " | ".join(msgs)}
    return None


def _kiva_handler(state, galaxy, level, context):
    """Shock Assault: first attack each turn gets power bonus."""
    trigger = context.get("trigger")
    if trigger == "pre_battle":
        if state.attacks_this_turn == 0:
            bonus = {1: 1, 2: 2, 3: 2, 4: 3}.get(level, 1)
            return {"player_power_bonus": bonus,
                    "message": f"Shock Assault: all cards +{bonus} power!"}
    return None


# ============================= ASGARD ======================================

def _freyr_handler(state, galaxy, level, context):
    """Protected Planets Treaty: reduce counterattacks."""
    trigger = context.get("trigger")
    if trigger == "on_counterattack":
        reduction = {1: 0.05, 2: 0.10, 3: 0.15, 4: 0.20}.get(level, 0.05)
        result = {"counterattack_reduction": reduction}
        # L3: AI can't attack homeworld directly
        if level >= 3:
            target_id = context.get("target_id")
            if target_id:
                planet = galaxy.planets.get(target_id)
                if planet and planet.planet_type == "homeworld" and planet.faction == state.player_faction:
                    return {"skip_counterattack": True,
                            "message": "Protected Planets Treaty: homeworld shielded!"}
        # L4: protect fortified planets
        if level >= 4:
            target_id = context.get("target_id")
            if target_id and state.fortification_levels.get(target_id, 0) >= 2:
                return {"skip_counterattack": True,
                        "message": "Protected Planets Treaty: fortified planet shielded!"}
        return result
    return None


def _loki_handler(state, galaxy, level, context):
    """Genetic Manipulation: steal enemy faction card on victory."""
    trigger = context.get("trigger")
    if trigger == "on_victory":
        rng = context.get("rng", random)
        chance = {1: 0.25, 2: 0.35, 3: 0.40, 4: 0.50}.get(level, 0.25)
        defeated_faction = context.get("defeated_faction")
        if defeated_faction and rng.random() < chance:
            pool = [cid for cid, c in ALL_CARDS.items()
                    if getattr(c, 'faction', None) == defeated_faction
                    and getattr(c, 'card_type', '') != "Legendary Commander"
                    and getattr(c, 'row', '') != "weather"]
            if pool:
                stolen = rng.choice(pool)
                state.add_card(stolen)
                if level >= 3:
                    state.upgrade_card(stolen, 1)
                    return f"Genetic Manipulation: stole & upgraded {_card_name(stolen)}"
                return f"Genetic Manipulation: stole {_card_name(stolen)}"
    return None


def _heimdall_handler(state, galaxy, level, context):
    """Research Archives: extra reward choices."""
    trigger = context.get("trigger")
    if trigger == "on_victory":
        extra = {1: 1, 2: 1, 3: 2, 4: 3}.get(level, 1)
        result = {"extra_card_choices": extra}
        if level >= 3:
            result["guarantee_hero"] = True
        if level >= 4:
            result["guarantee_strong"] = True
        return result
    return None


def _thor_handler(state, galaxy, level, context):
    """Asgard Fleet: ship/mothership cards get power bonus."""
    trigger = context.get("trigger")
    if trigger == "pre_battle":
        bonus = {1: 1, 2: 2, 3: 2, 4: 3}.get(level, 1)
        extra_start = 1 if level >= 3 else 0
        return {"ship_power_bonus": bonus, "extra_start_cards": extra_start}
    return None


def _hermiod_handler(state, galaxy, level, context):
    """Beaming Technology: extended attack range."""
    trigger = context.get("trigger")
    if trigger == "pre_attack":
        hop_range = {1: 2, 2: 2, 3: 3, 4: 3}.get(level, 2)
        no_penalty = level >= 2
        flip_chance = 0.15 if level >= 4 else 0
        return {"attack_range": hop_range, "no_range_penalty": no_penalty,
                "flip_at_range_chance": flip_chance}
    return None


def _penegal_handler(state, galaxy, level, context):
    """Asgard Preservation: chance to keep cards when forced to lose them."""
    trigger = context.get("trigger")
    if trigger == "on_defeat":
        rng = context.get("rng", random)
        chance = {1: 0.25, 2: 0.35, 3: 0.40, 4: 0.50}.get(level, 0.25)
        preserved = rng.random() < chance
        # L3-4: auto-add cards if deck too small
        min_deck = 18 if level >= 4 else (15 if level >= 3 else 0)
        cards_added = 0
        if min_deck > 0 and len(state.current_deck) < min_deck:
            pool = [cid for cid, c in ALL_CARDS.items()
                    if getattr(c, 'faction', None) == state.player_faction
                    and getattr(c, 'card_type', '') != "Legendary Commander"
                    and getattr(c, 'row', '') != "weather"]
            while len(state.current_deck) < min_deck and pool:
                state.add_card(rng.choice(pool))
                cards_added += 1
        msg_parts = []
        if preserved:
            msg_parts.append("Asgard Preservation: cards preserved!")
        if cards_added:
            msg_parts.append(f"+{cards_added} cards to maintain deck")
        return " | ".join(msg_parts) if msg_parts else None
    return None


def _aegir_handler(state, galaxy, level, context):
    """Asgard Science Council: free card upgrade every N turns."""
    trigger = context.get("trigger")
    if trigger == "on_turn_end":
        interval = {1: 3, 2: 2, 3: 2, 4: 1}.get(level, 3)
        data = state.conquest_ability_data
        data["aegir_turns"] = data.get("aegir_turns", 0) + 1
        if data["aegir_turns"] >= interval:
            data["aegir_turns"] = 0
            rng = context.get("rng", random)
            upgradeable = _upgradeable(state)
            if upgradeable:
                target = rng.choice(upgradeable)
                state.upgrade_card(target, 1)
                return f"Asgard Science Council: upgraded {_card_name(target)}"
    return None


# ===========================================================================
# REGISTRY — maps leader card_id to ability definition
# ===========================================================================

CONQUEST_ABILITIES = {
    # --- Tau'ri ---
    "tauri_oneill": {
        "name": "MacGyver Protocol",
        "descriptions": [
            "If losing after R1, +1 power to random unit in R2",
            "If losing after R1, +2 power to random unit in R2",
            "Also triggers after R2. +3 power bonus",
            "+3 power bonus + draw 1 card on comeback",
        ],
        "triggers": ["pre_battle"],
        "handler": _oneill_handler,
    },
    "tauri_hammond": {
        "name": "Homeworld Command",
        "descriptions": [
            "Homeworld defense: all cards +1 power",
            "Any defense battle: all cards +1 power",
            "Any defense: all cards +2 power",
            "Any defense: all cards +2 power, +1 card drawn",
        ],
        "triggers": ["on_defense"],
        "handler": _hammond_handler,
    },
    "tauri_carter": {
        "name": "Naquadah Generator",
        "descriptions": [
            "+15 bonus naquadah per victory",
            "+25 bonus naquadah per victory",
            "+35 naq/victory, fortify cost -10",
            "+50 naq/victory, fortify cost -15",
        ],
        "triggers": ["on_victory"],
        "handler": _carter_handler,
    },
    "tauri_landry": {
        "name": "SGC Logistics",
        "descriptions": [
            "Attack cooldowns reduced by 1 turn",
            "-1 cooldown + 20% chance to skip cooldown",
            "Cooldowns reduced by 2 turns",
            "-2 cooldown + 20% skip chance",
        ],
        "triggers": ["on_turn_end"],
        "handler": _landry_handler,
    },
    "tauri_mckay": {
        "name": "Brilliant Improvisation",
        "descriptions": [
            "30% chance to auto-upgrade card after victory",
            "45% upgrade chance after victory",
            "60% upgrade + chance to duplicate reward card",
            "75% upgrade + duplicate chance",
        ],
        "triggers": ["on_victory"],
        "handler": _mckay_handler,
    },
    "tauri_quinn": {
        "name": "Kelownan Intelligence",
        "descriptions": [
            "Pre-battle: see enemy leader ability",
            "See enemy leader + 1 deck card",
            "See enemy leader + top 3 deck cards",
            "See entire enemy deck before battle",
        ],
        "triggers": ["pre_battle"],
        "handler": _quinn_handler,
    },
    "tauri_langford": {
        "name": "Archaeological Discovery",
        "descriptions": [
            "Neutral events: +1 choice",
            "+1 choice, +20 naq from events",
            "+1 choice, +20 naq, 15% relic chance",
            "+1 choice, +20 naq, 25% relic chance",
        ],
        "triggers": ["on_neutral_event"],
        "handler": _langford_handler,
    },

    # --- Goa'uld ---
    "goauld_apophis": {
        "name": "System Lord's Dominion",
        "descriptions": [
            "Conquest: +1 power to 1 random card (permanent)",
            "Conquest: +1 power to 1 random card",
            "Conquest: +2 power to 1 random card",
            "Conquest: +2 power to 2 random cards",
        ],
        "triggers": ["on_victory"],
        "handler": _apophis_handler,
    },
    "goauld_yu": {
        "name": "Ancient Wisdom",
        "descriptions": [
            "Pre-battle: reveal 1 enemy card",
            "Reveal 2 enemy cards",
            "Reveal 3 enemy cards",
            "See entire enemy hand in Round 1",
        ],
        "triggers": ["pre_battle"],
        "handler": _yu_handler,
    },
    "goauld_sokar": {
        "name": "Netu's Torment",
        "descriptions": [
            "AI counterattacks -5% chance",
            "-10% counterattack chance",
            "-15% counter + bonus naq on defense win",
            "-20% counter + 25 naq on defense win",
        ],
        "triggers": ["on_counterattack", "on_defense"],
        "handler": _sokar_handler,
    },
    "goauld_baal": {
        "name": "Clone Network",
        "descriptions": [
            "25% chance to negate cooldown on loss",
            "35% negate cooldown on loss",
            "50% negate + 15 naq refund",
            "60% negate + 25 naq refund",
        ],
        "triggers": ["on_defeat"],
        "handler": _baal_handler,
    },
    "goauld_anubis": {
        "name": "Ascended Wrath",
        "descriptions": [
            "Reduce elite defender bonus by 1",
            "Reduce elite bonus by 1",
            "Reduce by 2, negate extra cards",
            "Reduce by 2, negate extras, YOUR cards +1 vs homeworlds",
        ],
        "triggers": ["pre_battle"],
        "handler": _anubis_handler,
    },
    "goauld_hathor_unlock": {
        "name": "Seductive Diplomacy",
        "descriptions": [
            "15% chance enemy faction skips counterattack",
            "20% skip chance",
            "25% skip + 10% cede territory",
            "35% skip + 15% cede territory",
        ],
        "triggers": ["on_counterattack"],
        "handler": _hathor_handler,
    },
    "goauld_cronus": {
        "name": "Imperial Expansion",
        "descriptions": [
            "+2 naq/turn per planet beyond 3",
            "+3 naq/turn per planet beyond 3",
            "+4 naq/turn per planet beyond 3, relic at 10 planets",
            "+5 naq/turn, relic at 10 + 15 planets",
        ],
        "triggers": ["on_turn_end"],
        "handler": _cronus_handler,
    },

    # --- Jaffa ---
    "jaffa_tealc": {
        "name": "Shol'va's Resolve",
        "descriptions": [
            "Defense: all cards +1 power",
            "Defense: +1 power, +1 card",
            "Defense: +2 power, +1 card",
            "Defense: +2 power, +1 card, upgrade on defense win",
        ],
        "triggers": ["on_defense"],
        "handler": _tealc_handler,
    },
    "jaffa_bratac": {
        "name": "Warrior's Training",
        "descriptions": [
            "Every 3 victories: upgrade weakest card +2",
            "Every 2 victories: upgrade +2",
            "Every 2 victories: upgrade 2 cards +2",
            "Every victory: upgrade card +2",
        ],
        "triggers": ["on_victory"],
        "handler": _bratac_handler,
    },
    "jaffa_raknor": {
        "name": "Rebel Recruitment",
        "descriptions": [
            "Conquest: +1 free card from defeated faction",
            "Conquest: +1 card from defeated faction",
            "+2 pre-upgraded cards from defeated faction",
            "+2 pre-upgraded cards",
        ],
        "triggers": ["on_victory"],
        "handler": _raknor_handler,
    },
    "jaffa_kalel": {
        "name": "Hak'tyl Warriors",
        "descriptions": [
            "Fortify 20% cheaper",
            "Fortify 30% cheaper",
            "40% cheaper + fort adds power in defense",
            "50% cheaper + fort adds power in defense",
        ],
        "triggers": ["on_fortify", "on_defense"],
        "handler": _kalel_handler,
    },
    "jaffa_gerak": {
        "name": "Political Maneuvering",
        "descriptions": [
            "+30 starting naquadah",
            "+50 naq start + event naq bonus",
            "+75 naq start + event bonus",
            "+100 naq start + event bonus + start with relic",
        ],
        "triggers": ["on_neutral_event"],
        "handler": _gerak_handler,
    },
    "jaffa_ishta": {
        "name": "Guerrilla Resistance",
        "descriptions": [
            "Can attack 2 planets per turn",
            "Attack 2 per turn",
            "Attack 3 per turn",
            "Attack 3 per turn",
        ],
        "triggers": ["pre_attack"],
        "handler": _ishta_handler,
    },
    "jaffa_ryac": {
        "name": "Next Generation",
        "descriptions": [
            "All card upgrades get +1 extra power",
            "+1 extra + 30% chance for extra upgrade choice",
            "All upgrades get +2 extra power",
            "+2 extra + extra choice chance",
        ],
        "triggers": ["on_victory"],
        "handler": _ryac_handler,
    },

    # --- Lucian Alliance ---
    "lucian_varro": {
        "name": "Black Market Contacts",
        "descriptions": [
            "+10 naq after every battle (win or lose)",
            "+15 naq every battle",
            "+20 naq + chance for free card",
            "+25 naq + free card chance + halved loss penalty",
        ],
        "triggers": ["on_victory", "on_defeat"],
        "handler": _varro_handler,
    },
    "lucian_sodan_master": {
        "name": "Sodan Cloak",
        "descriptions": [
            "20% chance AI can't counterattack",
            "30% cloak chance",
            "40% cloak + attacks ignore weather",
            "50% cloak + ignore weather + +1 power",
        ],
        "triggers": ["on_counterattack", "pre_battle"],
        "handler": _sodan_handler,
    },
    "lucian_baal_clone": {
        "name": "Infiltration",
        "descriptions": [
            "20% chance conquest flips adjacent planet",
            "25% flip chance",
            "30% flip + 15 naq bonus",
            "40% flip + 15 naq + can flip 2 adjacent",
        ],
        "triggers": ["on_victory"],
        "handler": _baal_clone_handler,
    },
    "lucian_netan": {
        "name": "Smuggler's Network",
        "descriptions": [
            "Neutral events: +30 bonus naquadah",
            "+40 naq from events",
            "+50 naq from events",
            "+60 naq from events",
        ],
        "triggers": ["on_neutral_event"],
        "handler": _netan_handler,
    },
    "lucian_vala": {
        "name": "Treasure Hunter",
        "descriptions": [
            "15% extra relic on homeworld conquest",
            "25% extra relic on homeworld",
            "30% relic + Furling events always give relic",
            "40% relic on homeworld + start with relic",
        ],
        "triggers": ["on_victory"],
        "handler": _vala_handler,
    },
    "lucian_anateo": {
        "name": "Hostage Tactics",
        "descriptions": [
            "30% chance to keep planet after defense loss",
            "40% keep planet",
            "50% keep + 20 naq bonus",
            "60% keep + 20 naq + free fort level",
        ],
        "triggers": ["on_defense"],
        "handler": _anateo_handler,
    },
    "lucian_kiva": {
        "name": "Shock Assault",
        "descriptions": [
            "First attack each turn: all cards +1 power",
            "First attack: +2 power",
            "First attack: +2 power",
            "First attack: +3 power",
        ],
        "triggers": ["pre_battle"],
        "handler": _kiva_handler,
    },

    # --- Asgard ---
    "asgard_freyr": {
        "name": "Protected Planets Treaty",
        "descriptions": [
            "AI counterattack -5%",
            "-10% counterattack chance",
            "-15% + AI can't attack homeworld",
            "-20% + protects fortified (2+) planets",
        ],
        "triggers": ["on_counterattack"],
        "handler": _freyr_handler,
    },
    "asgard_loki": {
        "name": "Genetic Manipulation",
        "descriptions": [
            "25% chance to steal enemy card on victory",
            "35% steal chance",
            "40% steal + stolen cards pre-upgraded",
            "50% steal + pre-upgraded",
        ],
        "triggers": ["on_victory"],
        "handler": _loki_handler,
    },
    "asgard_heimdall": {
        "name": "Research Archives",
        "descriptions": [
            "Reward screens: +1 card choice",
            "+1 card choice",
            "+2 choices + guarantee hero card",
            "+3 choices + guarantee 6+ power card",
        ],
        "triggers": ["on_victory"],
        "handler": _heimdall_handler,
    },
    "asgard_thor": {
        "name": "Asgard Fleet",
        "descriptions": [
            "Ship/mothership cards +1 power in battle",
            "+2 power to ships",
            "+2 power + extra starting card if 3+ ships",
            "+3 power + extra starting cards",
        ],
        "triggers": ["pre_battle"],
        "handler": _thor_handler,
    },
    "asgard_hermiod": {
        "name": "Beaming Technology",
        "descriptions": [
            "Attack 2 hops away (built-in Ring Platform)",
            "2 hops + no extra loss penalty at range",
            "Attack 3 hops away",
            "3 hops + chance to flip planet at range",
        ],
        "triggers": ["pre_attack"],
        "handler": _hermiod_handler,
    },
    "asgard_penegal": {
        "name": "Asgard Preservation",
        "descriptions": [
            "25% chance to preserve cards on loss",
            "35% preservation chance",
            "40% + auto-add cards if deck < 15",
            "50% + auto-add if deck < 18",
        ],
        "triggers": ["on_defeat"],
        "handler": _penegal_handler,
    },
    "asgard_aegir": {
        "name": "Asgard Science Council",
        "descriptions": [
            "Free card upgrade every 3 turns",
            "Free upgrade every 2 turns",
            "Every 2 turns + upgrade protection",
            "Every turn + upgrade protection",
        ],
        "triggers": ["on_turn_end"],
        "handler": _aegir_handler,
    },
}


# ===========================================================================
# Public API
# ===========================================================================

def get_conquest_ability(leader):
    """Get conquest ability definition for a leader.

    Args:
        leader: Leader dict with 'card_id' key

    Returns:
        Ability dict or None
    """
    if not leader:
        return None
    card_id = leader.get("card_id", "")
    return CONQUEST_ABILITIES.get(card_id)


def get_ability_level(state):
    """Get the current ability level from the network tier stored in state."""
    from .stargate_network import NETWORK_TIERS
    tier = getattr(state, 'network_tier', 1)
    tier_data = NETWORK_TIERS.get(tier, NETWORK_TIERS[1])
    return tier_data["ability_level"]


def trigger_ability(state, galaxy, trigger_name, context=None):
    """Fire a conquest ability if the leader has one for this trigger.

    Args:
        state: CampaignState
        galaxy: GalaxyMap
        trigger_name: e.g. "on_victory", "pre_battle", etc.
        context: dict of trigger-specific data

    Returns:
        Handler result (varies by ability) or None
    """
    ability = get_conquest_ability(state.player_leader)
    if not ability:
        return None

    if trigger_name not in ability.get("triggers", []):
        return None

    level = get_ability_level(state)
    ctx = dict(context or {})
    ctx["trigger"] = trigger_name

    return ability["handler"](state, galaxy, level, ctx)


def get_ability_display(state):
    """Get display info for the current conquest ability.

    Returns:
        (name, level, description) or None
    """
    ability = get_conquest_ability(state.player_leader)
    if not ability:
        return None

    level = get_ability_level(state)
    desc_idx = min(level - 1, len(ability["descriptions"]) - 1)
    return (ability["name"], level, ability["descriptions"][desc_idx])
