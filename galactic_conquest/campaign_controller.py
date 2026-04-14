"""
STARGWENT - GALACTIC CONQUEST - Campaign Controller

Main orchestrator: turn loop, planet attacks, card battles,
AI counterattacks, and campaign flow.
"""

import asyncio
import pygame
import random
import os
import display_manager

from .campaign_state import CampaignState
from .campaign_persistence import save_campaign, load_campaign
from .galaxy_map import GalaxyMap, ALL_FACTIONS
from .map_renderer import MapScreen
from .card_battle import run_card_battle
from .reward_screen import run_reward_screen
from .neutral_events import run_neutral_event
from .planet_passives import (get_naquadah_per_turn, get_counterattack_reduction,
                               get_card_choice_bonus, get_cooldown_reduction,
                               get_total_passive)
from .relics import get_relic, get_homeworld_relic
from .relic_screen import show_relic_acquired
from .narrative_arcs import check_arc_progress, apply_arc_rewards
from .stargate_network import get_network_bonuses, get_disconnected_planets
from .difficulty import get_counterattack_chance, get_ai_power_bonus, get_loss_penalty
from .conquest_abilities import trigger_ability, get_ability_display
from .buildings import (get_building_naq_income, get_defense_bonus,
                         get_attack_extra_cards, construct_building, BUILDINGS, can_build,
                         get_building_level, can_upgrade as can_upgrade_building,
                         upgrade_building, get_upgrade_cost)
from .crisis_events import (should_trigger_crisis, pick_crisis, apply_crisis,
                             show_crisis_screen, CRISIS_CHOICES,
                             check_crisis_option_c, get_current_act)
from .diplomacy import (get_adjacency_bonus_factions,
                         get_trade_income, get_alliance_upkeep, set_relation,
                         get_neutral_income, get_lucian_sabotage_penalty,
                         get_favor_counter_bonus, get_demand_retaliation_bonus,
                         get_ultimatum_aggro, tick_favor_decay, tick_trading_favor,
                         tick_nap_timers, tick_diplomacy_cooldowns, tick_special_effects,
                         check_nap_break, break_nap, on_faction_eliminated,
                         get_mutual_defense_bonus, get_asgard_tech_bonus,
                         consume_asgard_tech_draw,
                         TRADING, check_conquest_strain,
                         update_coalition_trust, check_coalition_formation,
                         check_coalition_break, get_coalition_counterattack_mult)
from .minor_worlds import (init_minor_worlds, ensure_minor_world,
                            decay_minor_world_influence, ai_court_minor_worlds,
                            apply_minor_world_income, notify_quest_event,
                            get_minor_world_bonuses,
                            update_rival_courtship, tick_rival_lockouts)
from .doctrines import (get_active_effects, apply_wisdom_income, get_wisdom_per_turn)
from .espionage import (tick_operatives, check_earn_operative, get_sabotage_effect,
                         get_operative_summary, generate_ai_espionage_events,
                         resolve_ai_espionage, generate_incident_choices,
                         resolve_incident_choice)
from .relics import get_combo_effects
from .buildings import get_synergy_effects
from .planet_passives import tick_turns_held, get_development_counterattack_mod
from .victory_conditions import (check_any_victory, tick_supergate, VICTORY_INFO,
                                   VICTORY_SCORE_MULTIPLIERS,
                                   _player_income_per_turn,
                                   ECONOMIC_TERRITORY_FRACTION,
                                   ECONOMIC_INCOME_PER_TURN)
from . import activity_log, leader_toolkits, rival_arcs


# AI counterattack chance per faction with adjacent border (now overridden by difficulty)
AI_COUNTERATTACK_CHANCE = 0.30
# Cooldown turns after failed attack
ATTACK_COOLDOWN = 3

# AI Faction Personalities — shape counterattack, expansion, and diplomacy behavior
FACTION_PERSONALITIES = {
    "Goa'uld": {
        "name": "Aggressive",
        "counterattack_mult": 1.5,    # 50% more likely to counterattack
        "expansion_mult": 1.4,        # more likely to attack in faction wars
        "success_bonus": 0.05,        # slightly better at conquering
        "desc": "Relentless conquerors — high counterattack, aggressive expansion",
        # Diplomacy personality
        "gift_favor_mult": 0.5,       # gifts are half as effective
        "nap_acceptance": 0.30,       # rarely accept NAPs
        "demand_refusal_rate": 0.80,  # almost always refuse tribute demands
        "trade_propose_mult": 0.5,    # rarely propose trades
        "unique_proposal": "subjugation",
        # G2a: which doctrine tree this AI prefers when adopting
        "preferred_tree": "conquest",
    },
    "Asgard": {
        "name": "Diplomatic",
        "counterattack_mult": 0.5,    # much less likely to counterattack
        "expansion_mult": 0.6,        # rarely attacks others
        "success_bonus": 0.0,
        "desc": "Prefer trade and protection — low aggression",
        # Diplomacy personality
        "gift_favor_mult": 1.5,       # appreciate gifts more
        "nap_acceptance": 0.95,       # almost always accept NAPs
        "demand_refusal_rate": 0.20,  # usually comply with demands
        "trade_propose_mult": 1.5,    # frequently propose trades
        "unique_proposal": "tech_exchange",
        "preferred_tree": "alliance",
    },
    "Jaffa Rebellion": {
        "name": "Vengeful",
        "counterattack_mult": 1.0,    # normal base, but see below
        "expansion_mult": 1.0,
        "success_bonus": 0.0,
        "vengeful": True,             # 2x counterattack if lost planet last turn
        "desc": "Strike back hard when wronged — vengeful counterattacks",
        # Diplomacy personality
        "gift_favor_mult": 1.0,
        "nap_acceptance": 0.50,
        "demand_refusal_rate": 0.50,
        "trade_propose_mult": 1.0,
        "unique_proposal": "revenge_pact",
        "preferred_tree": "shadow",
    },
    "Lucian Alliance": {
        "name": "Opportunistic",
        "counterattack_mult": 1.0,
        "expansion_mult": 1.2,
        "success_bonus": 0.10,        # better at winning battles
        "target_weakest": True,       # targets faction with fewest planets
        "desc": "Strike the weak, exploit the strong",
        # Diplomacy personality
        "gift_favor_mult": 0.8,       # greedy, gifts less effective
        "nap_acceptance": 0.40,       # suspicious of NAPs
        "demand_refusal_rate": 0.60,  # usually refuse demands
        "trade_propose_mult": 1.3,    # love trade (profit motive)
        "unique_proposal": "protection_racket",
        "preferred_tree": "shadow",
    },
    "Alteran": {
        "name": "Ascendant",
        "counterattack_mult": 0.4,    # passive early
        "expansion_mult": 0.5,
        "success_bonus": 0.0,
        "late_game_mult": 2.5,        # multiplier after turn 15
        "desc": "Passive early, overwhelming after turn 15",
        # Diplomacy personality
        "gift_favor_mult": 1.2,       # receptive to gifts
        "nap_acceptance": 0.70,       # generally peaceful
        "demand_refusal_rate": 0.30,
        "trade_propose_mult": 0.5,    # aloof early, but unique proposals late
        "unique_proposal": "knowledge_sharing",
        "preferred_tree": "ascension",
    },
    "Tau'ri": {
        "name": "Balanced",
        "counterattack_mult": 1.0,
        "expansion_mult": 1.0,
        "success_bonus": 0.0,
        "desc": "Standard behavior — no special modifiers",
        # Diplomacy personality
        "gift_favor_mult": 1.0,
        "nap_acceptance": 0.60,
        "demand_refusal_rate": 0.40,
        "trade_propose_mult": 1.0,
        "unique_proposal": "mutual_defense",
        "preferred_tree": "innovation",
    },
}


def _get_personality(faction):
    """Get faction personality, defaulting to Balanced."""
    return FACTION_PERSONALITIES.get(faction, FACTION_PERSONALITIES["Tau'ri"])


# Faction-specific bonuses when conquering a faction's planet
FACTION_CONQUEST_BONUSES = {
    "Tau'ri": {"type": "extra_card", "desc": "Intel: +1 random card"},
    "Goa'uld": {"type": "upgrade_card", "desc": "Domination: +2 power to a random card"},
    "Jaffa Rebellion": {"type": "remove_weak", "desc": "Training: removed weakest card"},
    "Lucian Alliance": {"type": "naquadah", "value": 50, "desc": "Trade: +50 naquadah"},
    "Asgard": {"type": "upgrade_multi", "desc": "Tech: +1 power to 2 random cards"},
    "Alteran": {"type": "upgrade_multi", "desc": "Ascension: +1 power to 2 random cards"},
}


class CampaignController:
    """Orchestrates the Galactic Conquest campaign turn loop."""

    def __init__(self, screen, campaign_state: CampaignState):
        self.screen = screen
        self.state = campaign_state
        self.galaxy = GalaxyMap.from_dict(campaign_state.galaxy)
        self.map_screen = MapScreen(screen.get_width(), screen.get_height())
        self.message = None
        self.rng = random.Random(campaign_state.seed + campaign_state.turn_number)
        # Defense alert sound
        self._defend_sound = None
        try:
            path = os.path.join("assets", "audio", "conquest_defend.ogg")
            if os.path.exists(path):
                self._defend_sound = pygame.mixer.Sound(path)
        except Exception:
            pass
        self._debug_force_crisis = False

    def _get_network_cached(self, allied=None):
        """Return network bonuses, cached per turn (invalidated after ownership changes)."""
        if allied is None:
            allied = get_adjacency_bonus_factions(self.state)
        cache_key = (self.state.turn_number, frozenset(self.state.planet_ownership.items()))
        if not hasattr(self, '_network_cache_key') or self._network_cache_key != cache_key:
            self._network_cache = get_network_bonuses(self.galaxy, self.state.player_faction, allied)
            self._network_cache_key = cache_key
        return self._network_cache

    @staticmethod
    def _music_start():
        from . import start_conquest_music
        start_conquest_music()

    @staticmethod
    def _music_stop():
        from . import stop_conquest_music
        stop_conquest_music()

    async def run(self):
        """Main campaign loop. Returns 'victory', 'defeat', 'quit', or 'save_quit'."""
        clock = pygame.time.Clock()
        self._music_start()

        while True:
            await asyncio.sleep(0)
            # Refresh screen reference (may have changed after card battle)
            self.screen = display_manager.screen

            # Sync planet ownership from state to galaxy
            for pid, owner in self.state.planet_ownership.items():
                if pid in self.galaxy.planets:
                    self.galaxy.planets[pid].owner = owner

            # Check win/loss
            victory = check_any_victory(self.state, self.galaxy)
            if victory:
                v_type, v_name = victory
                self._music_stop()
                self._finalize_run("victory", victory_type=v_type)
                v_info = VICTORY_INFO.get(v_type, {})
                await self._show_end_screen(
                    f"VICTORY — {v_name}",
                    v_info.get("desc", "You have won the campaign!"))
                return "victory"
            if self.galaxy.check_loss(self.state.player_faction):
                self._music_stop()
                self._finalize_run("defeat")
                await self._show_end_screen("DEFEAT", "Your homeworld has fallen!")
                return "defeat"

            has_ring = self.state.has_relic("ring_platform")
            allied = get_adjacency_bonus_factions(self.state)
            network = self._get_network_cached(allied)
            has_two_hop = has_ring or network["two_hop_attacks"]
            attackable = self.galaxy.get_attackable_planets(ring_platform=has_two_hop)
            # Remove cooldown planets
            attackable = [p for p in attackable if p not in self.state.cooldowns]

            # Map screen loop (player turn)
            action = await self._run_map_screen(clock, attackable)

            if action == "save_quit":
                self._save()
                self._music_stop()
                return "save_quit"
            elif action == "quit":
                self._music_stop()
                return "quit"
            elif action == "view_deck":
                await self._show_deck_viewer()
            elif action == "run_info":
                await self._show_run_info()
            elif action == "diplomacy":
                await self._show_diplomacy()
            elif action == "minor_world":
                await self._show_minor_world()
            elif action == "doctrines":
                await self._show_doctrines()
            elif action == "operatives":
                await self._show_operatives()
            elif action == "spy_report":
                from .spy_report import show_spy_report
                await show_spy_report(self.screen, self.state, self.galaxy)
                self._refresh_after_battle()
            elif action and action.startswith("build_"):
                building_id = action[6:]  # strip "build_" prefix
                planet_id = self.map_screen.selected_planet
                if planet_id and can_build(self.state, planet_id, building_id, self.galaxy):
                    msg = construct_building(self.state, planet_id, building_id, self.galaxy)
                    if msg:
                        self.message = msg
                        # Minor world quest: build event
                        for _qpid, _qmsg in notify_quest_event(self.state, "build"):
                            self._flash_message(_qmsg, 1200)
            elif action and action.startswith("upgrade_"):
                planet_id = action[8:]
                if planet_id and can_upgrade_building(self.state, planet_id, self.galaxy):
                    msg = upgrade_building(self.state, planet_id)
                    if msg:
                        self.message = msg
            elif action == "fortify":
                planet_id = self.map_screen.selected_planet
                if planet_id and planet_id in self.galaxy.planets:
                    planet = self.galaxy.planets[planet_id]
                    cur_level = self.state.fortification_levels.get(planet_id, 0)
                    network = self._get_network_cached(allied)
                    fort_cost = network["fortify_cost"]
                    if planet.owner == "player" and cur_level < 3 and self.state.naquadah >= fort_cost:
                        self.state.add_naquadah(-fort_cost)
                        self.state.fortification_levels[planet_id] = cur_level + 1
                        self.message = f"Fortified {planet.name}! (Level {cur_level + 1}/3) -{fort_cost} naq"
            elif action and action.startswith("wisdom_"):
                action_id = action[7:]
                from .wisdom_actions import use_wisdom_action
                msg = use_wisdom_action(self.state, action_id, self.galaxy, self.rng)
                if msg:
                    self.message = msg
            elif action and action.startswith("leader_action:"):
                leader_action_id = action[len("leader_action:"):]
                msg = await self._handle_leader_action(leader_action_id)
                if msg:
                    self.message = msg
                    self._flash_message(msg, 1500)
            elif action and action.startswith("relic_active:"):
                relic_id = action[len("relic_active:"):]
                msg = await self._handle_relic_active(relic_id)
                if msg:
                    self.message = msg
                    self._flash_message(msg, 1500)
            elif action == "attack":
                planet_id = self.map_screen.selected_planet
                if planet_id:
                    # Check conquest strain warning
                    from .diplomacy import check_potential_strain
                    strain_msg = check_potential_strain(self.state, planet_id, self.galaxy)
                    if strain_msg:
                        proceed = await self._show_trade_proposal(
                            "Warning", strain_msg,
                            accept_label="Attack Anyway", reject_label="Cancel")
                        if not proceed:
                            continue
                    result = await self._attack_planet(planet_id)
                    if result == "quit":
                        return "quit"
            elif action == "end_turn":
                # AI counterattack phase
                ai_result = await self._ai_counterattack_phase()
                if ai_result == "quit":
                    self._music_stop()
                    return "quit"
                if ai_result == "defeat":
                    self._music_stop()
                    self._finalize_run("defeat")
                    await self._show_end_screen("DEFEAT", "Your homeworld has fallen!")
                    return "defeat"

                # AI faction wars phase
                self._ai_faction_wars_phase()

                # Advance turn
                self.state.turn_number += 1
                self.state.tick_cooldowns()
                # 12.0: tick leader action cooldowns
                leader_toolkits.tick_cooldowns(self.state)
                # 12.0: tick turn-counted flags (relic actives / scripted
                # crises).  Each flag decrements until 0 and is then
                # removed; consumers just read the value.
                for _flag in (
                        "ai_intel_turns",
                        "network_surge_turns",
                        "income_double_turns",
                        "apophis_declaration_turns",
                        "stargate_lockdown_turns",
                        "fake_identity_turns",
                        "operatives_visible_turns",
                ):
                    if self.state.conquest_ability_data.get(_flag, 0) > 0:
                        self.state.conquest_ability_data[_flag] -= 1
                        if self.state.conquest_ability_data[_flag] <= 0:
                            del self.state.conquest_ability_data[_flag]
                # Clear one-shot "this turn only" flags
                self.state.conquest_ability_data.pop(
                    "skip_all_counterattacks", None)
                # Apply cooldown reduction passive
                cd_reduce = get_cooldown_reduction(self.galaxy)
                if cd_reduce > 0:
                    for pid in list(self.state.cooldowns):
                        self.state.cooldowns[pid] = max(0, self.state.cooldowns[pid] - cd_reduce)
                    # Clean up expired
                    self.state.cooldowns = {k: v for k, v in self.state.cooldowns.items() if v > 0}
                self.rng = random.Random(self.state.seed + self.state.turn_number)

                # 12.0: advance rival leader arcs (exile → guerrilla → resurgence → showdown)
                for _arc_msg in rival_arcs.advance_all(self.state, self.galaxy, self.rng):
                    self._flash_message(_arc_msg, 1800)
                # 12.0: any rival that just hit SHOWDOWN gets a confrontation prompt
                for arc in rival_arcs.pending_showdowns(self.state):
                    showdown_result = await self._run_rival_showdown(arc)
                    if showdown_result == "quit":
                        return "quit"

                # Turn summary display — brief animated income breakdown
                await self._show_turn_summary()

                # Planet passive income + relic income + network bonus + building income
                allied = get_adjacency_bonus_factions(self.state)
                naq_income = get_naquadah_per_turn(self.galaxy, allied)
                if self.state.has_relic("naquadah_reactor"):
                    naq_income += 10
                network = self._get_network_cached(allied)
                naq_income += network["naq_bonus"]
                building_income = get_building_naq_income(self.state, self.galaxy)
                # Building synergy: Naquadria Cascade (+50% refinery income)
                syn_effects = get_synergy_effects(self.state, self.galaxy)
                refinery_bonus = syn_effects.get("refinery_income_bonus", 0)
                if refinery_bonus > 0:
                    building_income = int(building_income * (1.0 + refinery_bonus))
                naq_income += building_income
                # Relic combo: victory_naq_bonus handled in attack flow
                # Relic combo: extra naq from combos (passive income handled elsewhere)
                # Diplomacy: trade income and alliance upkeep
                trade_income = get_trade_income(self.state)
                alliance_upkeep = get_alliance_upkeep(self.state)
                # Doctrine penalty: trade_income_penalty
                doctrine_effects_income = get_active_effects(self.state)
                trade_penalty = doctrine_effects_income.get("trade_income_penalty", 0)
                naq_income += max(0, trade_income - trade_penalty)
                # Doctrine penalty: naquadah_per_turn_penalty
                naq_penalty = doctrine_effects_income.get("naquadah_per_turn_penalty", 0)
                naq_income -= naq_penalty
                # Doctrine penalty: alliance_upkeep_increase
                alliance_upkeep += doctrine_effects_income.get("alliance_upkeep_increase", 0)
                # Meta perk: Naquadria Synthesis gives +15% income
                from .meta_progression import has_perk
                if has_perk("naquadah_income_bonus") and naq_income > 0:
                    naq_income += max(1, (naq_income * 15 + 99) // 100)
                # Apply upkeep after income bonuses
                naq_income -= alliance_upkeep
                # If can't afford alliance upkeep, degrade alliances to trading
                if self.state.naquadah + naq_income < 0:
                    for faction, rel in list(self.state.faction_relations.items()):
                        if rel == "allied":
                            set_relation(self.state, faction, TRADING)
                            self._flash_message(
                                f"Cannot afford alliance upkeep! {faction} downgraded to Trading.", 2000)
                    # Recalculate without upkeep
                    alliance_upkeep = 0
                    naq_income += get_alliance_upkeep(self.state)  # will be 0 now
                self.state.network_tier = network["tier"]
                if naq_income != 0:
                    self.state.add_naquadah(naq_income)
                # Reset attacks counter for new turn
                self.state.attacks_this_turn = 0
                self.state.wisdom_actions_this_turn = 0
                # Tick crisis cooldown
                if self.state.crisis_cooldown > 0:
                    self.state.crisis_cooldown -= 1

                # Minor worlds: decay influence, AI courting, income
                init_minor_worlds(self.state, self.galaxy)
                decay_minor_world_influence(self.state)
                ai_court_minor_worlds(self.state, self.galaxy, self.rng)
                # G6: rival courtship — pick a suitor for each minor world,
                # tick their influence, fire lockouts if they beat the player.
                rival_events = update_rival_courtship(self.state, self.galaxy, self.rng)
                for _pid, rival_msg in rival_events:
                    turn_msg += f" | {rival_msg}"
                tick_rival_lockouts(self.state)
                mw_naq = apply_minor_world_income(self.state, self.galaxy)
                if mw_naq > 0:
                    self.state.add_naquadah(mw_naq)

                # Planet development track — tick turns held
                tick_turns_held(self.state, self.galaxy)

                # Wisdom income from doctrines + ancient planets + minor worlds
                wisdom_gained = apply_wisdom_income(self.state, self.galaxy)
                # Doctrine penalty: wisdom_per_turn_penalty
                wisdom_penalty = get_active_effects(self.state).get("wisdom_per_turn_penalty", 0)
                if wisdom_penalty > 0:
                    self.state.wisdom = max(0, self.state.wisdom - wisdom_penalty)

                # Doctrine: alliance influence per turn (+5 from Diplomatic Mastery)
                doctrine_effects = get_active_effects(self.state)
                mw_inf_bonus = doctrine_effects.get("minor_world_influence_per_turn", 0)
                if mw_inf_bonus > 0:
                    from .minor_worlds import MinorWorldState, INFLUENCE_MAX
                    for _pid, _data in list(self.state.minor_world_states.items()):
                        _mw = MinorWorldState.from_dict(_data)
                        _mw.influence = min(INFLUENCE_MAX, _mw.influence + mw_inf_bonus)
                        self.state.minor_world_states[_pid] = _mw.to_dict()

                # Conquest leader ability: on_turn_end
                turn_ability_result = trigger_ability(
                    self.state, self.galaxy, "on_turn_end",
                    {"rng": self.rng})
                turn_msg = f"Turn {self.state.turn_number}"
                if naq_income > 0:
                    turn_msg += f" | +{naq_income} Naquadah"
                elif naq_income < 0:
                    turn_msg += f" | {naq_income} Naquadah"
                if trade_income > 0:
                    turn_msg += f" | Trade: +{trade_income}"
                if alliance_upkeep > 0:
                    turn_msg += f" | Upkeep: -{alliance_upkeep}"
                if isinstance(turn_ability_result, str) and turn_ability_result:
                    turn_msg += f" | {turn_ability_result}"

                # AI diplomatic proposals
                from .diplomacy import generate_ai_proposals, apply_proposal, tick_tribute_rejections
                ai_proposals = generate_ai_proposals(self.state, self.galaxy, self.rng)
                for proposal in ai_proposals:
                    accepted = await self._show_trade_proposal(
                        proposal["faction"], proposal["description"],
                        accept_label=proposal.get("accept_label", "Accept"),
                        reject_label=proposal.get("reject_label", "Decline"))
                    result_msg = apply_proposal(self.state, proposal, accepted, self.galaxy, self.rng)
                    if result_msg:
                        turn_msg += f" | {result_msg}"
                tick_tribute_rejections(self.state)

                # Diplomacy: tick favor decay, NAP timers, trading favor, cooldowns, special effects
                tick_favor_decay(self.state)
                tick_nap_timers(self.state)
                tick_trading_favor(self.state)
                tick_diplomacy_cooldowns(self.state)
                tick_special_effects(self.state)

                # G2a: AI doctrine adoption (every 8 turns)
                ai_doctrine_msg = self._ai_adopt_doctrines()
                if ai_doctrine_msg:
                    turn_msg += f" | {ai_doctrine_msg}"

                # G2b: Tick down espionage doctrine block
                blocked = self.state.espionage_blocks.get("doctrine_blocked_turns", 0)
                if blocked > 0:
                    self.state.espionage_blocks["doctrine_blocked_turns"] = blocked - 1

                # G5: Economic Hegemony streak counter — tick when both
                # territory and income thresholds are met this turn, reset
                # otherwise. check_economic reads the counter.
                total_planets = len(self.galaxy.planets)
                if total_planets > 0:
                    fraction = self.galaxy.get_player_planet_count() / total_planets
                    income = _player_income_per_turn(self.state, self.galaxy)
                    if (fraction >= ECONOMIC_TERRITORY_FRACTION
                            and income >= ECONOMIC_INCOME_PER_TURN):
                        self.state.consecutive_high_income_turns += 1
                    else:
                        self.state.consecutive_high_income_turns = 0

                # G4: keep state.act in sync with turn_number. Acts are
                # purely informational for now — chance scaling in
                # should_trigger_crisis reads directly from turn_number.
                prev_act = self.state.act
                self.state.act = get_current_act(self.state.turn_number)
                if self.state.act != prev_act:
                    act_names = {1: "Act I: Expansion", 2: "Act II: Tension", 3: "Act III: Endgame"}
                    new_act_msg = act_names.get(self.state.act, f"Act {self.state.act}")
                    turn_msg += f" | {new_act_msg}"
                    self._flash_message(new_act_msg, 2500)

                # G3: Coalition against player — trust update, form, break
                update_coalition_trust(self.state, self.galaxy)
                # 12.0: emergency coalition if player is 1 step from victory
                from .victory_conditions import is_player_near_victory
                near, victory_path = is_player_near_victory(self.state, self.galaxy)
                if near and not self.state.coalition.get("active"):
                    from .diplomacy import (COALITION_DURATION,
                                              COALITION_FORM_THRESHOLD)
                    survivors = [f for f in self.galaxy.get_active_factions()
                                 if f != self.state.player_faction
                                 and self.galaxy.get_faction_planet_count(f) > 0]
                    trust = self.state.coalition.setdefault("trust", {})
                    for f in survivors:
                        trust[f] = COALITION_FORM_THRESHOLD
                    self._flash_message(
                        f"The galaxy rallies to stop your {victory_path.upper()} victory!",
                        2500)
                    activity_log.log(
                        self.state, activity_log.CAT_DIPLOMACY,
                        f"Emergency coalition forming against "
                        f"your {victory_path} ambitions.",
                        icon="coalition",
                    )
                coalition_form_msg = check_coalition_formation(self.state, self.galaxy)
                if coalition_form_msg:
                    turn_msg += f" | {coalition_form_msg}"
                    self._flash_message(coalition_form_msg, 3000)
                coalition_break_msg = check_coalition_break(self.state, self.galaxy)
                if coalition_break_msg:
                    turn_msg += f" | {coalition_break_msg}"
                # Clear planet loss counters (used for peace offering proposals, one-shot per turn)
                for _pk in list(self.state.conquest_ability_data):
                    if _pk.startswith("_faction_planets_lost_"):
                        del self.state.conquest_ability_data[_pk]

                # Neutral income (+2/turn per neutral partner)
                neutral_inc = get_neutral_income(self.state)
                if neutral_inc > 0:
                    self.state.add_naquadah(neutral_inc)

                # Lucian sabotage penalty
                sab_penalty = get_lucian_sabotage_penalty(self.state)
                if sab_penalty > 0:
                    self.state.add_naquadah(-sab_penalty)

                # Ancient Repository relic: +30 naq/turn if player controls Atlantis
                if self.state.has_relic("ancient_repository"):
                    atlantis_controlled = any(
                        p.name == "Atlantis" and p.owner == "player"
                        for p in self.galaxy.planets.values())
                    if atlantis_controlled:
                        self.state.add_naquadah(30)
                        turn_msg += " | Ancient Repository: +30 naq"

                # Crisis events: 10% chance after turn 5 (or forced via dev shim F6)
                if self._debug_force_crisis or should_trigger_crisis(self.state):
                    self._debug_force_crisis = False
                    crisis = pick_crisis(self.state, self.galaxy)
                    if crisis:
                        choices = CRISIS_CHOICES.get(crisis["effect"])
                        has_c = check_crisis_option_c(self.state, self.galaxy, crisis["effect"])
                        player_choice = await show_crisis_screen(
                            self.screen, crisis, choices, has_option_c=has_c)
                        crisis_result = apply_crisis(
                            self.state, self.galaxy, crisis, self.rng, choice=player_choice)
                        self._flash_message(crisis_result, 2000)
                        self._refresh_after_battle()
                        self.state.crisis_cooldown = 3  # 3-turn cooldown between crises
                        turn_msg += f" | CRISIS: {crisis['title']}"
                        # Track crisis stats
                        from deck_persistence import get_persistence
                        _p = get_persistence()
                        _cs = _p.unlock_data.setdefault("conquest_stats", {})
                        _cs["crises_encountered"] = _cs.get("crises_encountered", 0) + 1
                        _cs["crises_survived"] = _cs.get("crises_survived", 0) + 1
                        unique_crises = _cs.setdefault("unique_crises_seen", [])
                        if crisis["title"] not in unique_crises:
                            unique_crises.append(crisis["title"])
                        _p.save_unlocks()

                # AI espionage events
                ai_esp_events = generate_ai_espionage_events(self.state, self.galaxy, self.rng)
                for esp_event in ai_esp_events:
                    if esp_event["has_counter_intel"]:
                        result = resolve_ai_espionage(
                            self.state, self.galaxy, esp_event, "counter", self.rng)
                        turn_msg += f" | {result}"
                    else:
                        choice = await self._show_espionage_alert(esp_event)
                        result = resolve_ai_espionage(
                            self.state, self.galaxy, esp_event, choice, self.rng)
                        turn_msg += f" | {result}"

                # Espionage: tick operatives + check earn
                esp_messages = tick_operatives(self.state, self.galaxy, self.rng)
                for esp_msg in esp_messages:
                    turn_msg += f" | {esp_msg}"
                earn_msg = check_earn_operative(self.state, self.rng)
                if earn_msg:
                    turn_msg += f" | {earn_msg}"

                # Diplomatic incident choices
                incidents = generate_incident_choices(self.state, self.galaxy, self.rng)
                for incident in incidents:
                    choice = await self._show_incident_choice(incident)
                    result = resolve_incident_choice(self.state, incident, choice, self.rng)
                    turn_msg += f" | {result}"

                # Supergate victory: tick progress
                sg_msg = tick_supergate(self.state, self.galaxy)
                if sg_msg:
                    turn_msg += f" | {sg_msg}"

                self.message = turn_msg

                # Auto-save
                self._save()

    async def _run_map_screen(self, clock, attackable):
        """Run the galaxy map until player takes an action."""
        while True:
            clock.tick(60)
            await asyncio.sleep(0)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return "quit"

                # G7: active relic ability hotkeys (v11.0)
                if self._handle_relic_active_key(event):
                    continue

                action = self.map_screen.handle_event(
                    event, self.galaxy, self.state, attackable)
                if action:
                    return action

            self.map_screen.draw(
                self.screen, self.galaxy, self.state, attackable, self.message)
            display_manager.gpu_flip()

    def _handle_relic_active_key(self, event):
        """Handle G7 active-ability hotkeys on the galaxy map.

        Shift+T fires the Asgard Time Machine's manual rewind (separate
        from the automatic counterattack-loss fallback at line ~1240).
        Shift+S fires the Sarcophagus Chamber (full deck heal).

        Returns True if the event was consumed.
        """
        if event.type != pygame.KEYDOWN:
            return False
        shift_held = bool(event.mod & pygame.KMOD_SHIFT)
        if not shift_held:
            return False
        from .relics import activate_relic
        if event.key == pygame.K_t:
            msg = activate_relic(self.state, self.galaxy, "asgard_time_machine")
            if msg:
                self.message = msg
                self._flash_message(msg, 2500)
            return True
        if event.key == pygame.K_s:
            msg = activate_relic(self.state, self.galaxy, "sarcophagus")
            if msg:
                self.message = msg
                self._flash_message(msg, 2500)
            return True
        return False

    async def _attack_planet(self, planet_id):
        """Execute an attack on a planet. Returns 'done' or 'quit'."""
        planet = self.galaxy.planets[planet_id]

        # Neutral planet — text event, no combat
        if planet.owner == "neutral":
            self._music_stop()
            result = await run_neutral_event(self.screen, self.state)
            self._refresh_after_battle()
            if result == "quit":
                return "quit"
            planet.visited = True
            self.galaxy.transfer_ownership(planet_id, "player")
            self.state.planet_ownership[planet_id] = "player"
            # Initialize minor world state for this neutral planet
            ensure_minor_world(self.state, planet_id, self.galaxy)
            self.message = f"Claimed {planet.name}!"
            # +3 Wisdom for neutral event completion
            self.state.wisdom += 3
            # Check narrative arc progress (neutral planets like Atlantis are in arcs)
            await self._check_narrative_arcs(planet.name)
            return "done"

        # Enemy faction planet — card battle
        self._music_stop()
        # Homeworld attacks: elite defenders with bonus power + extra cards
        # Difficulty bonus applies to all AI cards
        ai_elite_bonus = get_ai_power_bonus(self.state.difficulty)
        ai_extra_cards = 0
        if planet.planet_type == "homeworld":
            ai_elite_bonus += 2
            ai_extra_cards = 2

        # Pre-battle preview screen with ENGAGE / RETREAT
        preview_result = await self._show_pre_battle_preview(
            planet, ai_elite_bonus, ai_extra_cards)
        if preview_result == "retreat":
            self._refresh_after_battle()
            self.message = f"Retreated from {planet.name}."
            return "done"
        if preview_result == "quit":
            return "quit"

        # Leader selection for this battle
        from .leader_select import run_leader_select
        battle_leader = await run_leader_select(
            self.screen, self.state.player_faction, self.state.player_leader)
        if battle_leader is None:
            # Player backed out
            self._refresh_after_battle()
            self.message = f"Retreated from {planet.name}."
            return "done"

        # 12.0: brief hyperspace warp into battle
        self._map_to_battle_transition("out", 550)

        card_result = await self._run_card_battle(planet, ai_elite_bonus=ai_elite_bonus,
                                                   ai_extra_cards=ai_extra_cards,
                                                   override_leader=battle_leader)
        self._refresh_after_battle()
        # 12.0: and drop back out on the way home
        self._map_to_battle_transition("in", 450)
        if card_result == "quit":
            return "quit"

        if card_result == "player_win":
            # Track battle win
            from deck_persistence import get_persistence
            _p = get_persistence()
            _cs = _p.unlock_data.setdefault("conquest_stats", {})
            _cs["battles_won"] = _cs.get("battles_won", 0) + 1
            _cs["planets_conquered"] = _cs.get("planets_conquered", 0) + 1
            if planet.planet_type == "homeworld":
                _cs["homeworlds_captured"] = _cs.get("homeworlds_captured", 0) + 1
            _p.save_unlocks()

            # Victory! Claim planet
            defeated_faction_name = planet.owner  # Capture before transfer
            self.galaxy.transfer_ownership(planet_id, "player")
            self.state.planet_ownership[planet_id] = "player"
            self.message = f"Conquered {planet.name}!"
            # Track planet loss for AI peace offering proposals
            loss_key = f"_faction_planets_lost_{defeated_faction_name}"
            self.state.conquest_ability_data[loss_key] = \
                self.state.conquest_ability_data.get(loss_key, 0) + 1
            # +5 Wisdom for card battle victory
            self.state.wisdom += 5
            # Minor world quest: conquer event
            for _qpid, _qmsg in notify_quest_event(self.state, "conquer"):
                self._flash_message(_qmsg, 1200)

            # Apply faction-specific conquest bonus
            bonus_msg = self._apply_faction_bonus(planet.faction)

            # Apply upgrade_on_victory passive
            upgrade_chance = get_total_passive(self.galaxy, "upgrade_on_victory")
            if upgrade_chance > 0 and self.rng.random() < upgrade_chance:
                from cards import ALL_CARDS
                upgradeable = [cid for cid in self.state.current_deck
                               if ALL_CARDS.get(cid) and getattr(ALL_CARDS[cid], 'power', 0)]
                if upgradeable:
                    target = self.rng.choice(upgradeable)
                    self.state.upgrade_card(target, 1)
                    name = getattr(ALL_CARDS[target], 'name', target)
                    bonus_msg += f" | Passive: {name} +1"

            # Doctrine penalty: conquest_naq_penalty
            c_effects = get_active_effects(self.state)
            conquest_penalty = c_effects.get("conquest_naq_penalty", 0)
            if conquest_penalty > 0:
                self.state.add_naquadah(-conquest_penalty)
                bonus_msg += f" | Doctrine penalty: -{conquest_penalty} naq"

            # Reward screen — quality scales with planets controlled
            extra_choices = get_card_choice_bonus(self.galaxy)
            # Relic: Alteran Database gives +1 card choice
            if hasattr(self.state, 'relics') and "alteran_database" in self.state.relics:
                extra_choices += 1
            # Relic combo: Temporal Archives gives +2 card choices
            combo_effects = get_combo_effects(self.state)
            extra_choices += combo_effects.get("extra_card_choices", 0)
            # Meta perk: Tok'ra Intelligence gives +1 card choice
            from .meta_progression import has_perk
            if has_perk("expanded_rewards"):
                extra_choices += 1
            # Trading partners: include their faction cards in reward pool
            trading_factions = [f for f, rel in self.state.faction_relations.items()
                                if rel == "trading"]
            # Conquest streak: count consecutive attacks this turn
            streak = self.state.attacks_this_turn
            # Narrative context: check if planet is part of a story arc
            narr_faction = None
            from .narrative_arcs import get_arc_for_planet
            arc_info = get_arc_for_planet(planet.name)
            if arc_info:
                narr_faction = arc_info.get("reward_faction", planet.faction)
            reward_result = await run_reward_screen(
                self.screen, self.state, planet.faction,
                planet_type=planet.planet_type,
                galaxy_map=self.galaxy,
                bonus_message=bonus_msg,
                extra_card_choices=extra_choices,
                trading_factions=trading_factions,
                conquest_streak=streak,
                narrative_faction=narr_faction)
            self._refresh_after_battle()
            if reward_result == "quit":
                return "quit"

            # Relic: Asgard Core bonus naquadah on victory
            if self.state.has_relic("asgard_core"):
                self.state.add_naquadah(20)

            # Relic combo: Ascended Arsenal (+15 naq per victory)
            victory_combo_naq = combo_effects.get("victory_naq_bonus", 0)
            if victory_combo_naq > 0:
                self.state.add_naquadah(victory_combo_naq)

            # Conquest leader ability: on_victory
            ability_result = trigger_ability(
                self.state, self.galaxy, "on_victory",
                {"rng": self.rng, "planet_id": planet_id, "planet": planet,
                 "defeated_faction": planet.faction})
            if ability_result:
                if isinstance(ability_result, str):
                    self._flash_message(ability_result, 1500)
                elif isinstance(ability_result, dict):
                    msg = ability_result.get("message", "")
                    if msg:
                        self._flash_message(msg, 1500)

            self.state.attacks_this_turn += 1

            # Break NAP if attacking a NAP faction
            nap_faction = check_nap_break(self.state, planet_id, self.galaxy)
            if nap_faction:
                break_nap(self.state, nap_faction)
                self._flash_message(f"NAP with {nap_faction} broken! Severe diplomatic penalty.", 2000)

            # Conquest near allies causes diplomatic strain
            strain_msg = check_conquest_strain(self.state, planet, self.galaxy, self.rng)
            if strain_msg:
                self._flash_message(strain_msg, 2000)

            # Check if conquered faction was eliminated
            defeated_faction = planet.faction
            if (defeated_faction != "neutral"
                    and self.galaxy.get_faction_planet_count(defeated_faction) == 0):
                on_faction_eliminated(self.state, defeated_faction)
                self._flash_message(
                    f"The galaxy trembles -- {defeated_faction} has been destroyed!", 2500)

            # Consume Asgard tech draw if active
            consume_asgard_tech_draw(self.state)

            # Homeworld conquest: award faction-specific relic
            if planet.planet_type == "homeworld":
                relic_id = get_homeworld_relic(planet.faction)
                if relic_id and not self.state.has_relic(relic_id):
                    relic = get_relic(relic_id)
                    if relic:
                        self.state.add_relic(relic_id)
                        await show_relic_acquired(self.screen, relic,
                                            source_text=f"Conquered {planet.faction} Homeworld")
                        self._refresh_after_battle()

                # 12.0: spawn a rival leader arc for the defeated commander
                rival_arcs.spawn_on_homeworld_capture(
                    self.state, self.galaxy, defeated_faction_name,
                    planet.defender_leader)

            # 12.0: log the victory
            activity_log.log(
                self.state, activity_log.CAT_BATTLE,
                f"Conquered {planet.name} from {defeated_faction_name}.",
                icon="victory", faction=defeated_faction_name, planet=planet_id,
            )

            # Check narrative arc progress
            await self._check_narrative_arcs(planet.name)
        elif card_result == "draw":
            # Draw — no penalty, no reward, no cooldown
            self.message = f"Draw at {planet.name}! No penalty."
            self._flash_message(f"Draw at {planet.name}!", 1500)
            self.state.attacks_this_turn += 1
        elif card_result == "player_loss":
            # Track battle loss
            from deck_persistence import get_persistence
            _p = get_persistence()
            _cs = _p.unlock_data.setdefault("conquest_stats", {})
            _cs["battles_lost"] = _cs.get("battles_lost", 0) + 1
            _p.save_unlocks()

            # Lost card battle — cooldown
            loss_penalty = get_loss_penalty(self.state.difficulty)

            # Conquest leader ability: on_defeat
            defeat_result = trigger_ability(
                self.state, self.galaxy, "on_defeat",
                {"rng": self.rng, "planet_id": planet_id})
            negate_cooldown = False
            halve_penalty = False
            if isinstance(defeat_result, dict):
                negate_cooldown = defeat_result.get("negate_cooldown", False)
                halve_penalty = defeat_result.get("halve_loss_penalty", False)
                msg = defeat_result.get("message", "")
                if msg:
                    self._flash_message(msg, 1500)
            elif isinstance(defeat_result, str) and defeat_result:
                self._flash_message(defeat_result, 1500)

            if not negate_cooldown:
                self.state.cooldowns[planet_id] = ATTACK_COOLDOWN
            if halve_penalty:
                loss_penalty = loss_penalty // 2
            self.state.add_naquadah(-loss_penalty)
            cd_text = f"Cooldown: {ATTACK_COOLDOWN} turns" if not negate_cooldown else "No cooldown!"
            self.message = f"Card battle lost at {planet.name}! -{loss_penalty} naq, {cd_text}"
            self.state.attacks_this_turn += 1

        return "done"

    def _map_to_battle_transition(self, direction: str = "out",
                                    duration_ms: int = 700) -> None:
        """Short hyperspace warp transition from the map into a battle.

        Uses the existing ``hyperspace`` shader so we don't ship new
        GPU assets.  The map frame is frozen, the warp uniform ramps
        from 0 → 1 over *duration_ms* (or 1 → 0 on the way back if
        ``direction == 'in'``).  Non-async to stay simple; blocking for
        ~0.7s is fine at battle boundaries.
        """
        try:
            from transitions import _get_gpu, _enable_effect, _set_effect_uniform
        except Exception:
            return
        gpu = _get_gpu()
        if not gpu:
            return

        _enable_effect(gpu, "hyperspace")
        _set_effect_uniform(gpu, "hyperspace", "center", (0.5, 0.5))
        _set_effect_uniform(gpu, "hyperspace", "direction",
                              1.0 if direction == "out" else -1.0)

        start = pygame.time.get_ticks()
        while True:
            now = pygame.time.get_ticks()
            elapsed = now - start
            if elapsed >= duration_ms:
                break
            # Drain events so the window stays responsive
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    break
            p = elapsed / duration_ms
            warp = p if direction == "out" else (1.0 - p)
            _set_effect_uniform(gpu, "hyperspace", "warp_factor", max(0.0, min(1.0, warp)))
            _set_effect_uniform(gpu, "hyperspace", "time", gpu.time)
            # Leave the frame as-is — the shader post-processes it
            display_manager.gpu_flip()
            pygame.time.wait(16)

        # Leave hyperspace off after transition.
        _set_effect_uniform(gpu, "hyperspace", "warp_factor", 0.0)
        try:
            gpu.set_effect_enabled("hyperspace", False)
        except Exception:
            pass

    async def _run_rival_showdown(self, arc: dict):
        """Climactic card battle against a rival leader in SHOWDOWN phase.

        Flow:
          1. Prompt player: ENGAGE or DEFER (staying in SHOWDOWN).
          2. On engage: build a card battle with the rival's faction +
             leader, scaled harder by ``arc['difficulty_tier']``.
          3. Win → ``rival_arcs.resolve`` + trophy (relic + naq).
             Loss → ``rival_arcs.rearm_after_loss`` (bumps difficulty).

        Returns ``"quit"`` if the battle window is closed, else
        ``"done"``.
        """
        rival_name = arc.get("rival_name", "Rival")
        faction = arc.get("rival_faction", "")

        # Build the rival's leader entry for the AI side.  Reuse
        # content_registry to pull the card_id's canonical dict.
        from content_registry import get_all_leaders_for_faction
        rival_leader = None
        for entry in get_all_leaders_for_faction(faction) or []:
            if entry.get("card_id") == arc.get("rival_card_id"):
                rival_leader = dict(entry)
                rival_leader.setdefault("faction", faction)
                break
        if rival_leader is None:
            rival_leader = {
                "name": rival_name,
                "card_id": arc.get("rival_card_id", ""),
                "faction": faction,
            }

        tagline = ""
        scripted = rival_arcs.SCRIPTED_ARCS.get(
            (self.state.player_leader.get("card_id", ""), rival_leader.get("card_id", "")))
        if scripted:
            tagline = scripted.get("tagline", "")

        prompt = (f"{rival_name} has emerged. "
                  f"{tagline or 'This ends now.'}").strip()
        proceed = await self._show_trade_proposal(
            faction, prompt, accept_label="Engage", reject_label="Defer")
        if proceed is None:  # window closed
            return "quit"
        if not proceed:
            activity_log.log(
                self.state, activity_log.CAT_RIVAL_ARC,
                f"You deferred {rival_name}'s challenge.",
                icon="rival", faction=faction,
            )
            return "done"

        # Buff the rival by difficulty tier + homeworld-equivalent bias.
        tier = int(arc.get("difficulty_tier", 0))
        ai_elite_bonus = 2 + tier
        ai_extra_cards = 1 + tier

        self._music_stop()
        result = await run_card_battle(
            self.screen,
            player_faction=self.state.player_faction,
            player_leader=self.state.player_leader,
            player_deck_ids=list(self.state.current_deck),
            ai_faction=faction,
            ai_leader=rival_leader,
            exempt_penalties=True,
            starting_weather=None,
            upgraded_cards=self.state.upgraded_cards,
            ai_elite_bonus=ai_elite_bonus,
            ai_extra_cards=ai_extra_cards,
            relics=getattr(self.state, "relics", []),
        )
        self._refresh_after_battle()
        if result == "quit":
            return "quit"

        if result == "player_win":
            rival_arcs.resolve(self.state, arc, player_won=True)
            # Trophy: faction-themed relic + naq bounty scaling with tier
            trophy = self._rival_showdown_trophy(faction, tier)
            if trophy and not self.state.has_relic(trophy):
                self.state.add_relic(trophy)
            self.state.add_naquadah(80 + 40 * tier)
            self._flash_message(
                f"{rival_name} defeated! Trophy relic + {80 + 40 * tier} naq.",
                2200)
        else:
            rival_arcs.rearm_after_loss(self.state, self.galaxy, arc, self.rng)
            self.state.add_naquadah(-40)
            self._flash_message(
                f"{rival_name} escapes, stronger for having lived. -40 naq.",
                2200)
        return "done"

    @staticmethod
    def _rival_showdown_trophy(faction: str, tier: int) -> str | None:
        """Pick a trophy relic appropriate to the defeated rival's faction.

        Falls back through a fixed table — relic IDs are validated at
        ``add_relic`` time so an unknown ID is silently skipped.
        """
        table = {
            "Tau'ri": "alteran_database",
            "Goa'uld": "staff_of_ra",
            "Jaffa Rebellion": "kara_kesh",
            "Lucian Alliance": "kull_armor",
            "Asgard": "thors_hammer",
            "Alteran": "ancient_zpm",
        }
        return table.get(faction)

    async def _run_card_battle(self, planet, ai_elite_bonus=0, ai_extra_cards=0,
                               override_leader=None):
        """Run a card battle against a planet's defender. Returns battle outcome."""
        ai_faction = planet.faction
        ai_leader = planet.defender_leader
        # Weaken enemy passive: remove cards from AI deck
        weaken_amount = int(get_total_passive(self.galaxy, "weaken_enemy"))
        # Espionage sabotage: additional card removal from operative missions
        sabotage_cards = get_sabotage_effect(self.state, planet.id)
        weaken_amount += sabotage_cards

        # Asgard tech exchange: +1 extra card draw for player
        asgard_extra = get_asgard_tech_bonus(self.state)

        result = await run_card_battle(
            self.screen,
            player_faction=self.state.player_faction,
            player_leader=override_leader or self.state.player_leader,
            player_deck_ids=list(self.state.current_deck),
            ai_faction=ai_faction,
            ai_leader=ai_leader,
            exempt_penalties=True,
            starting_weather=planet.weather_preset,
            upgraded_cards=self.state.upgraded_cards,
            ai_elite_bonus=ai_elite_bonus,
            ai_extra_cards=ai_extra_cards,
            relics=getattr(self.state, 'relics', []),
            ai_weaken_amount=weaken_amount,
            extra_player_cards=asgard_extra,
        )
        return result

    def _refresh_after_battle(self):
        """Refresh screen and clear events after returning from a battle/event screen."""
        self.screen = display_manager.screen
        # Preserve panel toggle state across refresh
        panel_visible = getattr(self.map_screen, 'panel_visible', True)
        self.map_screen = MapScreen(self.screen.get_width(), self.screen.get_height(),
                                     panel_visible=panel_visible)
        pygame.event.clear()
        self._music_start()

    # ──────────────────────────────────────────────────────────────
    # G2a — AI Doctrine Adoption
    # ──────────────────────────────────────────────────────────────
    # Every 8 turns, pick one random active AI faction and advance it
    # one policy down its personality-preferred doctrine tree. Capped
    # at tier-2 in 11.0 so we can tune balance before letting AI take
    # tier-3 branches and capstones.
    AI_DOCTRINE_INTERVAL = 8
    AI_DOCTRINE_TIER_CAP = 2  # 11.0 safety cap

    def _ai_adopt_doctrines(self):
        """Roll AI doctrine adoption for this turn. No-op off-interval."""
        if self.state.turn_number < self.AI_DOCTRINE_INTERVAL:
            return None
        if self.state.turn_number % self.AI_DOCTRINE_INTERVAL != 0:
            return None

        # Pick an active (non-eliminated) AI faction with a preferred tree.
        candidates = []
        for faction in ALL_FACTIONS:
            if faction == self.state.player_faction:
                continue
            if self.galaxy.get_faction_planet_count(faction) == 0:
                continue
            personality = _get_personality(faction)
            tree_id = personality.get("preferred_tree")
            if not tree_id:
                continue
            candidates.append((faction, tree_id))
        if not candidates:
            return None

        faction, tree_id = self.rng.choice(candidates)
        from .doctrines import DOCTRINE_TREES
        tree = DOCTRINE_TREES.get(tree_id)
        if not tree:
            return None

        # Find the next policy down the spine up to the tier cap.
        adopted = self.state.ai_doctrines.setdefault(faction, [])
        for policy in tree["policies"]:
            if policy.get("tier", 1) > self.AI_DOCTRINE_TIER_CAP:
                break
            if policy["id"] in adopted:
                continue
            # Spine-only for AI in 11.0 (skip branches — IDs ending in 'a'/'b')
            pid = policy["id"]
            if pid.endswith("a") or pid.endswith("b"):
                continue
            adopted.append(pid)
            return f"{faction} adopted {policy['name']}"
        return None

    async def _ai_counterattack_phase(self):
        """Process AI counterattacks. Returns 'done', 'defeat', or 'quit'."""
        # Meta perk: Diplomatic Immunity — first counterattack auto-fails
        from .meta_progression import has_perk
        diplomatic_immunity = (has_perk("diplomatic_immunity")
                               and not self.state.conquest_ability_data.get("diplomatic_immunity_used"))

        # 12.0: relic / leader action one-turn block on all counterattacks
        if self.state.conquest_ability_data.get("skip_all_counterattacks"):
            self._flash_message("All counterattacks suppressed this turn.",
                                  1500)
            activity_log.log(
                self.state, activity_log.CAT_COUNTERATTACK,
                "All counterattacks suppressed.",
            )
            return "done"

        allied = get_adjacency_bonus_factions(self.state)

        enemy_factions = set()
        for planet in self.galaxy.planets.values():
            if planet.owner not in ("player", "neutral"):
                enemy_factions.add(planet.owner)

        for faction in enemy_factions:
            # Skip friendly/trading/allied factions — they don't counterattack
            from .diplomacy import is_faction_friendly, get_betrayal_counter_bonus
            if faction == self.state.friendly_faction or is_faction_friendly(self.state, faction):
                continue
            targets = self.galaxy.get_ai_attack_targets(faction)
            if not targets:
                continue

            # 12.0 leader action: SG-1 Strike cancels next counterattack from this faction
            sg1_blocks = self.state.conquest_ability_data.get("sg1_strike_block", {})
            if sg1_blocks.get(faction, 0) > 0:
                sg1_blocks[faction] -= 1
                if sg1_blocks[faction] <= 0:
                    del sg1_blocks[faction]
                self._flash_message(f"SG-1 Strike neutralised {faction}'s counterattack!", 1800)
                activity_log.log(
                    self.state, activity_log.CAT_LEADER_ACTION,
                    f"SG-1 Strike cancelled {faction}'s counterattack.",
                    faction=faction,
                )
                continue

            # Base chance from difficulty, reduced by passives + network tier
            base_chance = get_counterattack_chance(self.state.difficulty)
            network = self._get_network_cached(allied)
            betrayal_bonus = get_betrayal_counter_bonus(self.state, faction)
            favor_bonus = get_favor_counter_bonus(self.state, faction)
            demand_bonus = get_demand_retaliation_bonus(self.state, faction)
            ultimatum_override = get_ultimatum_aggro(self.state, faction)
            if ultimatum_override > 0:
                effective_chance = 1.0  # 100% counterattack from ultimatum
            else:
                effective_chance = (base_chance + betrayal_bonus + favor_bonus + demand_bonus
                                    - get_counterattack_reduction(self.galaxy, allied)
                                    - network["counterattack_reduction"])

            # AI Personality modifier
            personality = _get_personality(faction)
            ca_mult = personality["counterattack_mult"]
            # Alteran: late-game escalation after turn 15
            if personality.get("late_game_mult") and self.state.turn_number >= 15:
                ca_mult = personality["late_game_mult"]
            # Jaffa Rebellion: vengeful — 2x if lost a planet last turn
            if personality.get("vengeful"):
                lost_last_turn = self.state.conquest_ability_data.get("_ai_lost_planet_last_turn", {})
                if lost_last_turn.get(faction):
                    ca_mult *= 2.0
            # G2a: AI doctrine bonuses
            ai_policies = self.state.ai_doctrines.get(faction, [])
            if "con_1" in ai_policies:
                # Conquest tier-1: slight aggression bump
                ca_mult *= 1.10
            if "con_2" in ai_policies:
                # Conquest tier-2: meaningful aggression bump
                ca_mult *= 1.15
            if "all_1" in ai_policies or "all_2" in ai_policies:
                # Alliance policies: calmer counterattack
                ca_mult *= 0.90
            # G3: Coalition against player bonus
            ca_mult *= get_coalition_counterattack_mult(self.state, faction)
            effective_chance *= ca_mult

            # Doctrine penalty: counterattack_chance_increase
            doctrine_effects = get_active_effects(self.state)
            effective_chance += doctrine_effects.get("counterattack_chance_increase", 0)

            # Planet development track modifier
            effective_chance += get_development_counterattack_mod(self.state, self.galaxy)

            # Sleeper agent: enemy attacks from this planet start -1 card
            # (applied later during battle setup)

            # Conquest leader ability: on_counterattack (reduce chance or skip)
            counter_result = trigger_ability(
                self.state, self.galaxy, "on_counterattack",
                {"rng": self.rng, "faction": faction, "target_id": self.rng.choice(targets)})
            if isinstance(counter_result, dict):
                if counter_result.get("skip_counterattack"):
                    msg = counter_result.get("message", "")
                    if msg:
                        self._flash_message(msg, 1500)
                    continue
                # Hathor's cede_territory: enemy cedes a planet to player
                if counter_result.get("cede_territory"):
                    ceded = self._handle_cede_territory(faction)
                    msg = counter_result.get("message", "")
                    if ceded:
                        msg += f" Gained {ceded}!"
                    if msg:
                        self._flash_message(msg, 2000)
                    continue
                effective_chance -= counter_result.get("counterattack_reduction", 0)

            if self.rng.random() > max(0.05, effective_chance):
                continue

            # Diplomatic Immunity perk: auto-block first counterattack
            if diplomatic_immunity:
                self.state.conquest_ability_data["diplomatic_immunity_used"] = True
                diplomatic_immunity = False
                self._flash_message(f"{faction} counterattack blocked by Diplomatic Immunity!", 1500)
                continue

            # AI attacks a random player planet
            target_id = self.rng.choice(targets)
            target = self.galaxy.planets[target_id]

            self.message = f"{faction} attacks {target.name}!"
            # Play defense alert sound
            if self._defend_sound:
                try:
                    self._defend_sound.play()
                except Exception:
                    pass
            # Brief message display
            self._flash_message(f"{faction} is attacking {target.name}!", 2000)

            # Card battle defense
            # Pick a random leader from the attacking faction
            from content_registry import get_all_leaders_for_faction
            leaders = get_all_leaders_for_faction(faction)
            ai_leader = dict(self.rng.choice(leaders)) if leaders else None
            if ai_leader:
                ai_leader.setdefault("faction", faction)

            # Leader selection for defense battle
            from .leader_select import run_leader_select
            defense_leader = await run_leader_select(
                self.screen, self.state.player_faction, self.state.player_leader)
            if defense_leader is None:
                # Can't back out of defense — auto-pick first available leader
                defense_leader = dict(leaders[0]) if leaders else None
                if defense_leader:
                    defense_leader.setdefault("faction", self.state.player_faction)

            self._music_stop()
            # Defense battles use the target planet's weather
            fort_level = getattr(self.state, 'fortification_levels', {}).get(target_id, 0)
            # Extra defense cards passive
            extra_defense = int(get_total_passive(self.galaxy, "extra_defense_card"))
            # Building: Training Ground defense bonus
            building_defense = get_defense_bonus(self.state, target_id)
            fort_level += building_defense
            # Doctrine penalty: defense_power_penalty
            doctrine_defense_penalty = doctrine_effects.get("defense_power_penalty", 0)

            # Building synergy: Integrated Defense Grid (+1 fort)
            synergy_effects = get_synergy_effects(self.state, self.galaxy)
            fort_level += synergy_effects.get("fortify_bonus", 0)

            # Conquest leader ability: on_defense (pre-battle bonuses)
            defense_bonus_power = 0 - doctrine_defense_penalty
            defense_result = trigger_ability(
                self.state, self.galaxy, "on_defense",
                {"rng": self.rng, "planet_id": target_id})
            if isinstance(defense_result, dict):
                defense_bonus_power = defense_result.get("defense_power_bonus", 0) - doctrine_defense_penalty
                extra_defense += defense_result.get("defense_extra_cards", 0)

            # Sleeper agent: find if enemy has a planet adjacent to target with sleeper
            sleeper_reduction = 0
            for neighbor_id in target.connections:
                neighbor = self.galaxy.planets.get(neighbor_id)
                if neighbor and neighbor.owner == faction:
                    if self.state.conquest_ability_data.get(f"sleeper_{neighbor_id}"):
                        sleeper_reduction = 1
                        break

            # Mutual defense treaty bonus (+1 defense power)
            mutual_def = get_mutual_defense_bonus(self.state)

            result = await run_card_battle(
                self.screen,
                player_faction=self.state.player_faction,
                player_leader=defense_leader,
                player_deck_ids=list(self.state.current_deck),
                ai_faction=faction,
                ai_leader=ai_leader,
                exempt_penalties=True,
                starting_weather=target.weather_preset,
                upgraded_cards=self.state.upgraded_cards,
                relics=getattr(self.state, 'relics', []),
                extra_player_cards=extra_defense,
                fort_defense_bonus=fort_level + defense_bonus_power + mutual_def,
                ai_weaken_amount=sleeper_reduction,
            )
            self._refresh_after_battle()

            if result == "quit":
                return "quit"

            if result == "player_win":
                # Track defense win
                from deck_persistence import get_persistence
                _p = get_persistence()
                _cs = _p.unlock_data.setdefault("conquest_stats", {})
                _cs["defenses_won"] = _cs.get("defenses_won", 0) + 1
                _p.save_unlocks()

                self.state.add_naquadah(40)
                # +5 Wisdom for card battle victory (defense)
                self.state.wisdom += 5
                # Defense bonus: random card from attacking faction
                defense_bonus = self._apply_defense_bonus(faction)
                # Minor world quest: defend event
                for _qpid, _qmsg in notify_quest_event(self.state, "defend"):
                    self._flash_message(_qmsg, 1200)
                self.message = f"Defended {target.name}! +40 Naquadah{defense_bonus}"
                activity_log.log(
                    self.state, activity_log.CAT_COUNTERATTACK,
                    f"Defended {target.name} against {faction}.",
                    icon="shield", faction=faction, planet=target_id,
                )
            else:
                # Track defense loss
                from deck_persistence import get_persistence
                _p = get_persistence()
                _cs = _p.unlock_data.setdefault("conquest_stats", {})
                _cs["defenses_lost"] = _cs.get("defenses_lost", 0) + 1
                _p.save_unlocks()

                # Lost defense — enemy takes the planet
                self.galaxy.transfer_ownership(target_id, faction)
                self.state.planet_ownership[target_id] = faction
                self.state.add_naquadah(-30)
                self.message = f"{target.name} lost to {faction}!"
                activity_log.log(
                    self.state, activity_log.CAT_COUNTERATTACK,
                    f"{target.name} lost to {faction}.",
                    icon="breach", faction=faction, planet=target_id,
                )
                # G7: record for Asgard Time Machine manual activation path.
                self.state.conquest_ability_data["_last_planet_lost"] = {
                    "planet_id": target_id,
                    "turn": self.state.turn_number,
                }

                # Asgard Time Machine relic: once per campaign, undo last planet loss
                if (self.state.has_relic("asgard_time_machine")
                        and not self.state.conquest_ability_data.get("time_machine_used")):
                    self._flash_message("Asgard Time Machine activating...", 1500)
                    # Undo the loss
                    self.galaxy.transfer_ownership(target_id, "player")
                    self.state.planet_ownership[target_id] = "player"
                    self.state.add_naquadah(30)  # Refund the penalty
                    self.state.conquest_ability_data["time_machine_used"] = True
                    self.message = f"Time Machine! {target.name} restored! (One-time use)"
                    continue  # Skip homeworld loss check since planet was restored

                # Check if homeworld was lost
                if self.galaxy.check_loss(self.state.player_faction):
                    return "defeat"

        return "done"

    def _ai_faction_wars_phase(self):
        """Process AI-vs-AI faction attacks. Factions fight each other for territory."""
        active_factions = self.galaxy.get_active_factions()
        # Remove friendly faction and player
        war_factions = [f for f in active_factions
                        if f != self.state.friendly_faction]

        # Track planet losses for Jaffa Rebellion vengeful personality
        lost_planets = {}

        for faction in war_factions:
            personality = _get_personality(faction)
            targets = self.galaxy.get_ai_vs_ai_targets(faction)
            if not targets:
                continue

            # Lucian: target the weakest faction's planets
            if personality.get("target_weakest") and targets:
                # Group targets by defender faction, pick weakest
                defender_counts = {}
                for tid in targets:
                    df = self.galaxy.planets[tid].owner
                    defender_counts.setdefault(df, []).append(tid)
                weakest_faction = min(defender_counts.keys(),
                                      key=lambda f: self.galaxy.get_faction_planet_count(f))
                targets = defender_counts[weakest_faction]

            # Attack chance scales with planet count + personality
            planet_count = self.galaxy.get_faction_planet_count(faction)
            attack_chance = min(0.40, 0.15 + 0.05 * planet_count)
            attack_chance *= personality["expansion_mult"]
            # Alteran: late-game escalation
            if personality.get("late_game_mult") and self.state.turn_number >= 15:
                attack_chance *= personality["late_game_mult"]
            if self.rng.random() > attack_chance:
                continue

            target_id = self.rng.choice(targets)
            target = self.galaxy.planets[target_id]
            defender_faction = target.owner

            # Success weighted by relative strength + personality bonus
            attacker_strength = self.galaxy.get_faction_planet_count(faction)
            defender_strength = self.galaxy.get_faction_planet_count(defender_faction)
            total = attacker_strength + defender_strength
            if total == 0:
                continue
            success_chance = 0.25 + 0.30 * (attacker_strength / total)
            success_chance += personality.get("success_bonus", 0)
            success_chance = max(0.25, min(0.60, success_chance))

            if self.rng.random() < success_chance:
                # Capture!
                self._animate_ai_war_arc(faction, target_id, success=True)
                self.galaxy.transfer_ownership(target_id, faction)
                self.state.planet_ownership[target_id] = faction
                self._flash_message(f"{faction} captured {target.name} from {defender_faction}!", 1500)
                activity_log.log(
                    self.state, activity_log.CAT_AI_WAR,
                    f"{faction} captured {target.name} from {defender_faction}.",
                    icon="war", faction=faction, planet=target_id,
                )
                lost_planets.setdefault(defender_faction, True)
            else:
                # War happened but defender held — visual only, no capture.
                self._animate_ai_war_arc(faction, target_id, success=False)

                # Check if a faction was eliminated
                if self.galaxy.get_faction_planet_count(defender_faction) == 0:
                    on_faction_eliminated(self.state, defender_faction)
                    self._flash_message(
                        f"The galaxy trembles -- {defender_faction} has been destroyed!", 2500)

                # Track planet losses for AI proposals (peace offering trigger)
                key = f"_faction_planets_lost_{defender_faction}"
                self.state.conquest_ability_data[key] = \
                    self.state.conquest_ability_data.get(key, 0) + 1

        # Reset planet loss counters at end of wars phase (they track "this turn")
        for key in list(self.state.conquest_ability_data):
            if key.startswith("_faction_planets_lost_"):
                pass  # Keep for AI proposals next turn, cleared on turn after

        # Store lost-planet info for Jaffa vengeful personality next turn
        self.state.conquest_ability_data["_ai_lost_planet_last_turn"] = lost_planets

    async def _check_narrative_arcs(self, planet_name):
        """Check narrative arc progress after conquering a planet."""
        results = check_arc_progress(self.state, planet_name)
        for arc, step, total, is_complete in results:
            if is_complete:
                apply_arc_rewards(self.state, arc)
                self._flash_message(f"ARC COMPLETE: {arc.name}!", 2500)
                # Show relic if arc awards one
                if arc.rewards["type"] == "relic":
                    relic = get_relic(arc.rewards["value"])
                    if relic and self.state.has_relic(relic.id):
                        await show_relic_acquired(self.screen, relic,
                                            source_text=f"Story Arc: {arc.name}")
                        self._refresh_after_battle()
                elif arc.rewards["type"] == "relic_and_naquadah":
                    relic = get_relic(arc.rewards["value"]["relic"])
                    if relic and self.state.has_relic(relic.id):
                        await show_relic_acquired(self.screen, relic,
                                            source_text=f"Story Arc: {arc.name}")
                        self._refresh_after_battle()
            else:
                self._flash_message(f"{arc.name}: {step}/{total}", 1500)

    async def _show_diplomacy(self):
        """Show diplomacy screen for managing faction relations."""
        from .diplomacy_screen import run_diplomacy_screen
        self._music_stop()
        await run_diplomacy_screen(self.screen, self.state, self.galaxy)
        self._refresh_after_battle()

    async def _show_minor_world(self):
        """Show minor world interaction screen for selected neutral planet."""
        planet_id = self.map_screen.selected_planet
        if not planet_id:
            return
        from .minor_world_screen import run_minor_world_screen
        self._music_stop()
        await run_minor_world_screen(self.screen, self.state, self.galaxy, planet_id)
        self._refresh_after_battle()

    async def _show_doctrines(self):
        """Show doctrine trees screen for Wisdom spending."""
        from .doctrine_screen import run_doctrine_screen
        self._music_stop()
        await run_doctrine_screen(self.screen, self.state, self.galaxy)
        self._refresh_after_battle()

    async def _show_operatives(self):
        """Show espionage screen for managing Tok'ra operatives."""
        from .espionage_screen import run_espionage_screen
        self._music_stop()
        await run_espionage_screen(self.screen, self.state, self.galaxy)
        self._refresh_after_battle()

    async def _show_deck_viewer(self):
        """Show the player's current conquest deck using the full deck builder UI."""
        from deck_builder import run_deck_builder

        def _conquest_save(card_ids):
            """Callback: save deck changes back to campaign state."""
            self.state.current_deck = list(card_ids)
            from .campaign_persistence import save_campaign
            self.state.galaxy = self.galaxy.to_dict()
            for pid, planet in self.galaxy.planets.items():
                self.state.planet_ownership[pid] = planet.owner
            save_campaign(self.state)

        self._music_stop()
        await run_deck_builder(
            self.screen,
            for_new_game=False,
            conquest_save_callback=_conquest_save,
            preset_faction=self.state.player_faction,
            preset_leader=self.state.player_leader,
            preset_deck_ids=list(self.state.current_deck),
        )
        self._refresh_after_battle()

    async def _show_run_info(self):
        """Show a summary of the current campaign run with CRT terminal aesthetic."""
        import math
        from .conquest_menu import (_get_scanline_overlay, CRT_AMBER, CRT_CYAN,
                                    CRT_GREEN, CRT_BORDER, CRT_TEXT, CRT_TEXT_DIM,
                                    CRT_BTN_BG, CRT_BTN_BORDER, FACTION_DISPLAY_COLORS)

        sw, sh = self.screen.get_width(), self.screen.get_height()
        clock = pygame.time.Clock()

        title_font = pygame.font.SysFont("Impact, Arial", max(40, sh // 22), bold=True)
        section_font = pygame.font.SysFont("Impact, Arial", max(22, sh // 42), bold=True)
        info_font = pygame.font.SysFont("Arial", max(17, sh // 55))

        # Load background (same as conquest menu)
        background = None
        bg_path = os.path.join("assets", "conquest_menu_bg.png")
        if not os.path.exists(bg_path):
            bg_path = os.path.join("assets", "conquest.png")
        try:
            raw = pygame.image.load(bg_path).convert()
            background = pygame.transform.smoothscale(raw, (sw, sh))
        except (pygame.error, FileNotFoundError):
            background = pygame.Surface((sw, sh))
            background.fill((8, 12, 10))

        scroll_offset = 0
        frame_count = 0
        running = True

        while running:
            clock.tick(60)
            await asyncio.sleep(0)
            frame_count += 1
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_ESCAPE, pygame.K_i, pygame.K_RETURN):
                        running = False
                    elif event.key == pygame.K_UP:
                        scroll_offset = max(0, scroll_offset - 40)
                    elif event.key == pygame.K_DOWN:
                        scroll_offset += 40
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        running = False
                    elif event.button == 4:
                        scroll_offset = max(0, scroll_offset - 40)
                    elif event.button == 5:
                        scroll_offset += 40

            # Background + dark overlay
            self.screen.blit(background, (0, 0))
            overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 170))
            self.screen.blit(overlay, (0, 0))

            # Panel with CRT border
            panel_w = int(sw * 0.6)
            panel_h = int(sh * 0.8)
            panel_x = sw // 2 - panel_w // 2
            panel_y = int(sh * 0.1)
            panel_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
            panel_surf.fill((*CRT_BTN_BG, 230))
            pygame.draw.rect(panel_surf, CRT_BORDER, panel_surf.get_rect(), 2)

            # Content lines
            content_lines = []

            # Title (pulsing amber)
            content_lines.append(("title", "RUN INFORMATION"))
            content_lines.append(("spacer", ""))

            # General stats
            content_lines.append(("section", "Campaign Status"))
            faction_color = FACTION_DISPLAY_COLORS.get(self.state.player_faction, CRT_TEXT)
            content_lines.append(("info", f"Faction: {self.state.player_faction}", faction_color))
            leader_name = self.state.player_leader.get("name", "Unknown") if self.state.player_leader else "Chosen per battle"
            content_lines.append(("info", f"Leader: {leader_name}", CRT_TEXT))
            content_lines.append(("info", f"Turn: {self.state.turn_number}", CRT_AMBER))
            content_lines.append(("info", f"Naquadah: {self.state.naquadah}", CRT_CYAN))
            content_lines.append(("info", f"Deck Size: {len(self.state.current_deck)} cards", CRT_AMBER))
            content_lines.append(("info", f"Difficulty: {self.state.difficulty.title()}", CRT_TEXT))

            # Network tier
            from .stargate_network import get_network_bonuses
            network = get_network_bonuses(self.galaxy, self.state.player_faction,
                                          get_adjacency_bonus_factions(self.state))
            tier_color = {1: CRT_TEXT, 2: CRT_CYAN, 3: CRT_AMBER, 4: (255, 140, 60), 5: (200, 100, 255)}.get(network["tier"], CRT_TEXT)
            content_lines.append(("info", f"Stargate Network: Tier {network['tier']} — {network['name']}", tier_color))

            # Conquest ability
            ability_info = get_ability_display(self.state)
            if ability_info:
                aname, alevel, adesc = ability_info
                content_lines.append(("info", f"Conquest Ability: {aname} (L{alevel})", (255, 220, 100)))
                content_lines.append(("info", f"  {adesc}", CRT_TEXT))
            content_lines.append(("spacer", ""))

            # Territory
            content_lines.append(("section", "Territory"))
            player_planets = []
            enemy_planets = []
            neutral_planets = []
            for pid, planet in self.galaxy.planets.items():
                if planet.owner == "player":
                    player_planets.append(planet)
                elif planet.owner == "neutral":
                    neutral_planets.append(planet)
                else:
                    enemy_planets.append(planet)
            total = len(self.galaxy.planets)
            content_lines.append(("info", f"Controlled: {len(player_planets)}/{total} planets", CRT_GREEN))
            content_lines.append(("info", f"Enemy: {len(enemy_planets)} | Neutral: {len(neutral_planets)}", CRT_TEXT))

            # Reward tier
            player_count = len(player_planets)
            if player_count >= 10:
                tier_text = "Supreme (5 card choices, +50% naquadah)"
                tier_color = CRT_AMBER
            elif player_count >= 6:
                tier_text = "Enhanced (4 card choices, +25% naquadah)"
                tier_color = CRT_CYAN
            else:
                tier_text = "Standard (3 card choices)"
                tier_color = CRT_TEXT
            content_lines.append(("info", f"Reward Tier: {tier_text}", tier_color))
            content_lines.append(("spacer", ""))

            # Your planets
            if player_planets:
                content_lines.append(("section", "Your Planets"))
                for p in player_planets:
                    tag = " (Homeworld)" if p.planet_type == "homeworld" else ""
                    content_lines.append(("info", f"  {p.name}{tag}", CRT_GREEN))

            # Cooldowns
            if self.state.cooldowns:
                content_lines.append(("spacer", ""))
                content_lines.append(("section", "Active Cooldowns"))
                for pid, turns in self.state.cooldowns.items():
                    pname = self.galaxy.planets[pid].name if pid in self.galaxy.planets else pid
                    content_lines.append(("info", f"  {pname}: {turns} turn(s) remaining", (255, 100, 100)))

            # Upgraded cards
            if self.state.upgraded_cards:
                content_lines.append(("spacer", ""))
                content_lines.append(("section", "Upgraded Cards"))
                from cards import ALL_CARDS
                for cid, bonus in sorted(self.state.upgraded_cards.items()):
                    if bonus <= 0:
                        continue
                    card = ALL_CARDS.get(cid)
                    cname = card.name if card else cid
                    content_lines.append(("info", f"  {cname}: +{bonus} power", CRT_GREEN))
            content_lines.append(("spacer", ""))

            # Enemy homeworld status
            content_lines.append(("section", "Enemy Homeworlds"))
            for pid, planet in self.galaxy.planets.items():
                if planet.planet_type == "homeworld" and planet.owner != "player":
                    hw_color = FACTION_DISPLAY_COLORS.get(planet.owner, (255, 100, 100))
                    content_lines.append(("info", f"  {planet.name} ({planet.owner})", hw_color))
            for pid, planet in self.galaxy.planets.items():
                if planet.planet_type == "homeworld" and planet.owner == "player" and planet.faction != self.state.player_faction:
                    content_lines.append(("info", f"  {planet.name} (CAPTURED)", CRT_GREEN))

            # Relics
            if self.state.relics:
                content_lines.append(("spacer", ""))
                content_lines.append(("section", "Relics"))
                from .relics import RELICS as ALL_RELICS
                for rid in self.state.relics:
                    relic = ALL_RELICS.get(rid)
                    if relic:
                        content_lines.append(("info", f"  {relic.icon_char} {relic.name}: {relic.description}",
                                              (255, 176, 0)))

            # Planet Passives
            from .planet_passives import get_active_passives
            active_passives = get_active_passives(self.galaxy)
            if active_passives:
                content_lines.append(("spacer", ""))
                content_lines.append(("section", "Planet Passives"))
                for pname, passive in active_passives:
                    content_lines.append(("info", f"  {pname}: {passive['desc']}", CRT_CYAN))

            # Fortifications
            forts = {pid: lvl for pid, lvl in self.state.fortification_levels.items() if lvl > 0}
            if forts:
                content_lines.append(("spacer", ""))
                content_lines.append(("section", "Fortifications"))
                for pid, level in forts.items():
                    pname = self.galaxy.planets[pid].name if pid in self.galaxy.planets else pid
                    content_lines.append(("info", f"  {pname}: Level {level}/3", (100, 200, 255)))

            # Story Arcs
            from .narrative_arcs import get_arc_progress_display
            arc_display = get_arc_progress_display(self.state)
            if arc_display:
                content_lines.append(("spacer", ""))
                content_lines.append(("section", "Story Arcs"))
                for arc_name, progress_str, is_complete in arc_display:
                    color = CRT_GREEN if is_complete else CRT_TEXT
                    prefix = "[COMPLETE] " if is_complete else ""
                    content_lines.append(("info", f"  {prefix}{arc_name}: {progress_str}", color))

            content_lines.append(("spacer", ""))
            content_lines.append(("info", "Press ESC / I / Click to close", CRT_TEXT_DIM))

            # Render content
            pulse = 0.85 + 0.15 * math.sin(frame_count * 0.03)
            y = 20 - scroll_offset
            for kind, text, *extra in content_lines:
                if kind == "title":
                    title_color = tuple(int(c * pulse) for c in CRT_AMBER)
                    surf = title_font.render(text, True, title_color)
                    panel_surf.blit(surf, (panel_w // 2 - surf.get_width() // 2, y))
                    y += surf.get_height() + 4
                    # Decorative line under title
                    line_w = int(panel_w * 0.6)
                    line_color = tuple(int(c * pulse) for c in CRT_BORDER)
                    pygame.draw.line(panel_surf, line_color,
                                     (panel_w // 2 - line_w // 2, y),
                                     (panel_w // 2 + line_w // 2, y), 2)
                    y += 8
                elif kind == "section":
                    surf = section_font.render(text, True, CRT_AMBER)
                    panel_surf.blit(surf, (30, y))
                    y += surf.get_height() + 6
                elif kind == "info":
                    color = extra[0] if extra else CRT_TEXT
                    surf = info_font.render(text, True, color)
                    panel_surf.blit(surf, (40, y))
                    y += surf.get_height() + 3
                elif kind == "spacer":
                    y += 12

            self.screen.blit(panel_surf, (panel_x, panel_y))

            # CRT scanlines over entire screen
            scanlines = _get_scanline_overlay(sw, sh, alpha=25)
            self.screen.blit(scanlines, (0, 0))

            # Bottom bar
            bar_h = int(sh * 0.035)
            bar_rect = pygame.Rect(0, sh - bar_h, sw, bar_h)
            bar_surf = pygame.Surface((bar_rect.width, bar_rect.height), pygame.SRCALPHA)
            bar_surf.fill((0, 0, 0, 180))
            self.screen.blit(bar_surf, bar_rect.topleft)
            hint = info_font.render("ESC / I / Click to close", True, CRT_TEXT_DIM)
            self.screen.blit(hint, (int(sw * 0.04), bar_rect.centery - hint.get_height() // 2))

            display_manager.gpu_flip()

    def _apply_faction_bonus(self, faction):
        """Apply faction-specific bonus after conquering a planet. Returns bonus message."""
        bonus = FACTION_CONQUEST_BONUSES.get(faction)
        if not bonus:
            return ""
        from cards import ALL_CARDS
        btype = bonus["type"]

        if btype == "extra_card":
            all_ids = [cid for cid, c in ALL_CARDS.items()
                       if getattr(c, 'card_type', '') != "Legendary Commander"
                       and getattr(c, 'row', '') != "weather"]
            if all_ids:
                cid = self.rng.choice(all_ids)
                self.state.add_card(cid)
                name = getattr(ALL_CARDS[cid], 'name', cid)
                return f" | {bonus['desc']}: {name}"

        elif btype == "upgrade_card":
            upgradeable = [cid for cid in self.state.current_deck
                           if ALL_CARDS.get(cid) and getattr(ALL_CARDS[cid], 'power', 0)]
            if upgradeable:
                target = self.rng.choice(upgradeable)
                self.state.upgrade_card(target, 2)
                name = getattr(ALL_CARDS[target], 'name', target)
                return f" | {bonus['desc']}: {name}"

        elif btype == "remove_weak":
            deck_with_power = [(cid, getattr(ALL_CARDS.get(cid), 'power', 0) or 0)
                               for cid in self.state.current_deck]
            deck_with_power.sort(key=lambda x: x[1])
            if len(deck_with_power) > 15:  # don't remove if deck too small
                removed_cid = deck_with_power[0][0]
                self.state.remove_card(removed_cid)
                name = getattr(ALL_CARDS.get(removed_cid), 'name', removed_cid)
                return f" | {bonus['desc']}: {name}"

        elif btype == "naquadah":
            amount = bonus.get("value", 50)
            self.state.add_naquadah(amount)
            return f" | {bonus['desc']}"

        elif btype == "upgrade_multi":
            upgradeable = list(set(cid for cid in self.state.current_deck
                                   if ALL_CARDS.get(cid) and getattr(ALL_CARDS[cid], 'power', 0)))
            if upgradeable:
                targets = self.rng.sample(upgradeable, min(2, len(upgradeable)))
                names = []
                for cid in targets:
                    self.state.upgrade_card(cid, 1)
                    names.append(getattr(ALL_CARDS[cid], 'name', cid))
                return f" | {bonus['desc']}: {', '.join(names)}"

        return ""

    def _apply_defense_bonus(self, attacking_faction):
        """Apply bonus for successfully defending a counterattack. Returns bonus string."""
        from cards import ALL_CARDS
        # Award a random card from attacking faction
        faction_cards = [cid for cid, c in ALL_CARDS.items()
                         if getattr(c, 'faction', None) == attacking_faction
                         and getattr(c, 'card_type', '') != "Legendary Commander"
                         and getattr(c, 'row', '') != "weather"]
        bonus_parts = []
        if faction_cards:
            cid = self.rng.choice(faction_cards)
            self.state.add_card(cid)
            name = getattr(ALL_CARDS[cid], 'name', cid)
            bonus_parts.append(f"+1 {attacking_faction} card: {name}")

        # 30% chance to upgrade a random card
        if self.rng.random() < 0.30:
            upgradeable = [cid for cid in self.state.current_deck
                           if ALL_CARDS.get(cid) and getattr(ALL_CARDS[cid], 'power', 0)]
            if upgradeable:
                target = self.rng.choice(upgradeable)
                self.state.upgrade_card(target, 1)
                name = getattr(ALL_CARDS[target], 'name', target)
                bonus_parts.append(f"Upgrade: {name} +1")

        if bonus_parts:
            return " | " + " | ".join(bonus_parts)
        return ""

    async def _show_pre_battle_preview(self, planet, ai_elite_bonus, ai_extra_cards):
        """Show pre-battle preview with matchup info. Returns 'engage', 'retreat', or 'quit'."""
        from .map_renderer import FACTION_COLORS
        from .stargate_network import get_network_bonuses
        from .conquest_abilities import get_ability_display

        sw, sh = self.screen.get_width(), self.screen.get_height()
        clock = pygame.time.Clock()

        title_font = pygame.font.SysFont("Impact, Arial", max(40, sh // 22), bold=True)
        section_font = pygame.font.SysFont("Impact, Arial", max(24, sh // 36), bold=True)
        info_font = pygame.font.SysFont("Arial", max(17, sh // 50))
        btn_font = pygame.font.SysFont("Impact, Arial", max(26, sh // 34), bold=True)

        faction_color = FACTION_COLORS.get(planet.faction, (255, 100, 100))
        player_color = FACTION_COLORS.get("player", (80, 220, 120))

        # Buttons
        btn_w = int(sw * 0.15)
        btn_h = int(sh * 0.06)
        engage_rect = pygame.Rect(sw // 2 - btn_w - 20, int(sh * 0.82), btn_w, btn_h)
        retreat_rect = pygame.Rect(sw // 2 + 20, int(sh * 0.82), btn_w, btn_h)

        # Compute intel
        leader_name = planet.defender_leader.get("name", "?") if planet.defender_leader else "Unknown"
        player_leader = self.state.player_leader.get("name", "?") if self.state.player_leader else "Selected per battle"
        weather_name = "None"
        if planet.weather_preset:
            weather_name = planet.weather_preset.get('type', 'none').replace('_', ' ').title()

        # Tel'tak Transport: estimate enemy power
        show_power = self.state.has_relic("teltak_transport")
        estimated_power = 0
        enemy_card_count = 0
        if show_power:
            from deck_builder import load_default_faction_deck, build_faction_deck
            from cards import ALL_CARDS
            ai_deck_ids = load_default_faction_deck(planet.faction)
            if not ai_deck_ids:
                ai_deck_ids = build_faction_deck(planet.faction, planet.defender_leader)
            for cid in ai_deck_ids:
                card = ALL_CARDS.get(cid)
                if card:
                    estimated_power += (getattr(card, 'power', 0) or 0) + ai_elite_bonus
            enemy_card_count = len(ai_deck_ids) + ai_extra_cards
            estimated_power += ai_extra_cards * 4

        # Modifiers info
        modifiers = []
        if ai_elite_bonus > 0:
            modifiers.append(f"AI Power Bonus: +{ai_elite_bonus}")
        if ai_extra_cards > 0:
            modifiers.append(f"AI Extra Cards: +{ai_extra_cards}")
        if self.state.relics:
            active_relics = []
            from .relics import RELICS
            for rid in self.state.relics:
                r = RELICS.get(rid)
                if r and r.category == "combat":
                    active_relics.append(r.name)
            if active_relics:
                modifiers.append(f"Combat Relics: {', '.join(active_relics)}")
        ability_info = get_ability_display(self.state)
        if ability_info:
            modifiers.append(f"Ability: {ability_info[0]} (L{ability_info[1]})")
        if planet.planet_type == "homeworld":
            modifiers.append("ELITE HOMEWORLD DEFENDER")

        hovered = None
        frame = 0

        while True:
            clock.tick(60)
            await asyncio.sleep(0)
            frame += 1

            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    return "quit"
                elif ev.type == pygame.MOUSEMOTION:
                    mx, my = ev.pos
                    hovered = None
                    if engage_rect.collidepoint(mx, my):
                        hovered = "engage"
                    elif retreat_rect.collidepoint(mx, my):
                        hovered = "retreat"
                elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    mx, my = ev.pos
                    if engage_rect.collidepoint(mx, my):
                        return "engage"
                    elif retreat_rect.collidepoint(mx, my):
                        return "retreat"
                elif ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_RETURN or ev.key == pygame.K_SPACE:
                        return "engage"
                    elif ev.key == pygame.K_ESCAPE:
                        return "retreat"

            # Draw
            self.screen.fill((10, 12, 20))
            overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 60))
            self.screen.blit(overlay, (0, 0))

            # Title
            import math
            pulse = 0.85 + 0.15 * math.sin(frame * 0.04)
            t_color = tuple(int(c * pulse) for c in (255, 200, 100))
            title = title_font.render("BATTLE PREVIEW", True, t_color)
            self.screen.blit(title, (sw // 2 - title.get_width() // 2, int(sh * 0.04)))

            # Separator
            sep_w = int(sw * 0.5)
            pygame.draw.line(self.screen, (80, 100, 120),
                             (sw // 2 - sep_w // 2, int(sh * 0.11)),
                             (sw // 2 + sep_w // 2, int(sh * 0.11)), 2)

            # Left side: Player info
            left_x = int(sw * 0.08)
            y = int(sh * 0.15)
            ps = section_font.render("YOUR FORCES", True, player_color)
            self.screen.blit(ps, (left_x, y))
            y += ps.get_height() + 8

            player_lines = [
                f"Leader: {player_leader}",
                f"Faction: {self.state.player_faction}",
                f"Deck: {len(self.state.current_deck)} cards",
                f"Upgrades: {sum(1 for v in self.state.upgraded_cards.values() if v > 0)}",
            ]
            for line in player_lines:
                s = info_font.render(line, True, (200, 220, 200))
                self.screen.blit(s, (left_x + 10, y))
                y += info_font.get_height() + 3

            # Right side: Enemy info
            right_x = int(sw * 0.55)
            y = int(sh * 0.15)
            es = section_font.render("ENEMY FORCES", True, faction_color)
            self.screen.blit(es, (right_x, y))
            y += es.get_height() + 8

            enemy_lines = [
                f"Defender: {leader_name}",
                f"Faction: {planet.faction}",
                f"Planet: {planet.name} ({planet.planet_type.title()})",
            ]
            if show_power:
                enemy_lines.append(f"Est. Cards: ~{enemy_card_count}")
                enemy_lines.append(f"Est. Power: ~{estimated_power}")
            for line in enemy_lines:
                s = info_font.render(line, True, (220, 200, 200))
                self.screen.blit(s, (right_x + 10, y))
                y += info_font.get_height() + 3

            # Center: VS + Weather
            vs_font = pygame.font.SysFont("Impact, Arial", max(48, sh // 16), bold=True)
            vs = vs_font.render("VS", True, (255, 80, 80))
            self.screen.blit(vs, (sw // 2 - vs.get_width() // 2, int(sh * 0.20)))

            weather_text = info_font.render(f"Weather: {weather_name}", True, (180, 180, 220))
            self.screen.blit(weather_text, (sw // 2 - weather_text.get_width() // 2, int(sh * 0.34)))

            # Modifiers section
            mod_y = int(sh * 0.42)
            if modifiers:
                mod_title = section_font.render("MODIFIERS", True, (255, 220, 100))
                self.screen.blit(mod_title, (sw // 2 - mod_title.get_width() // 2, mod_y))
                mod_y += mod_title.get_height() + 6
                for mod in modifiers:
                    is_elite = "ELITE" in mod
                    color = (255, 100, 80) if is_elite else (200, 200, 220)
                    ms = info_font.render(f"  {mod}", True, color)
                    self.screen.blit(ms, (sw // 2 - ms.get_width() // 2, mod_y))
                    mod_y += info_font.get_height() + 2

            # Buttons
            for rect, label, key, base_color in [
                (engage_rect, "ENGAGE", "engage", (40, 140, 60)),
                (retreat_rect, "RETREAT", "retreat", (140, 60, 60)),
            ]:
                is_hover = (hovered == key)
                color = tuple(min(255, c + 40) for c in base_color) if is_hover else base_color
                btn_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
                btn_surf.fill((*color, 230))
                self.screen.blit(btn_surf, rect.topleft)
                pygame.draw.rect(self.screen, (200, 200, 200) if is_hover else (150, 150, 150), rect, 2)
                lbl = btn_font.render(label, True, (255, 255, 255))
                self.screen.blit(lbl, (rect.centerx - lbl.get_width() // 2,
                                       rect.centery - lbl.get_height() // 2))

            # Hint
            hint = info_font.render("ENTER = Engage  |  ESC = Retreat", True, (120, 120, 140))
            self.screen.blit(hint, (sw // 2 - hint.get_width() // 2, int(sh * 0.93)))

            display_manager.gpu_flip()

    async def _show_turn_summary(self):
        """Show a brief animated turn transition with income breakdown."""
        sw, sh = self.screen.get_width(), self.screen.get_height()

        title_font = pygame.font.SysFont("Impact, Arial", max(36, sh // 25), bold=True)
        info_font = pygame.font.SysFont("Arial", max(17, sh // 50))

        # Calculate income breakdown
        allied = get_adjacency_bonus_factions(self.state)
        passive_income = get_naquadah_per_turn(self.galaxy, allied)
        reactor_income = 10 if self.state.has_relic("naquadah_reactor") else 0
        network = get_network_bonuses(self.galaxy, self.state.player_faction, allied)
        net_income = network["naq_bonus"]
        building_income = get_building_naq_income(self.state, self.galaxy)
        trade_income = get_trade_income(self.state)
        alliance_upkeep = get_alliance_upkeep(self.state)
        total = (passive_income + reactor_income + net_income + building_income
                 + trade_income - alliance_upkeep)

        lines = [
            (f"Turn {self.state.turn_number} → Turn {self.state.turn_number + 1}", (255, 220, 100)),
        ]
        if passive_income > 0:
            lines.append((f"  Planet Passives: +{passive_income} naq", (100, 200, 255)))
        if reactor_income > 0:
            lines.append((f"  Naquadah Reactor: +{reactor_income} naq", (100, 200, 255)))
        if net_income > 0:
            lines.append((f"  Stargate Network T{network['tier']}: +{net_income} naq", (200, 100, 255)))
        if building_income > 0:
            lines.append((f"  Buildings: +{building_income} naq", (200, 180, 100)))
        if trade_income > 0:
            lines.append((f"  Trade Agreements: +{trade_income} naq", (100, 220, 255)))
        if alliance_upkeep > 0:
            lines.append((f"  Alliance Upkeep: -{alliance_upkeep} naq", (255, 180, 80)))
        if total > 0:
            lines.append((f"  Total Income: +{total} naq", (100, 255, 200)))
        elif total < 0:
            lines.append((f"  Total Income: {total} naq", (255, 100, 100)))
        else:
            lines.append(("  No income this turn", (150, 150, 150)))

        # Brief display with fade-in
        for frame in range(60):  # ~1 second at 60fps
            alpha = min(255, frame * 8)
            overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, min(160, alpha)))
            self.screen.blit(overlay, (0, 0))

            y = int(sh * 0.35)
            for text, color in lines:
                fade_color = tuple(int(c * alpha / 255) for c in color)
                s = title_font.render(text, True, fade_color) if text.startswith("Turn") else info_font.render(text, True, fade_color)
                self.screen.blit(s, (sw // 2 - s.get_width() // 2, y))
                y += s.get_height() + 6

            display_manager.gpu_flip()
            pygame.time.Clock().tick(60)
            await asyncio.sleep(0)

            # Allow skip
            for ev in pygame.event.get():
                if ev.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                    return
                if ev.type == pygame.QUIT:
                    return

    def _flash_message(self, text, duration_ms=2000):
        """Show a message overlay; interruptible by Space/Enter/Esc/LMB.

        12.0: replaces the old blocking ``pygame.time.wait`` with an
        event-pumping loop so players can blast through stacks of
        messages with Space or a click.  The visual is identical to
        keep the rest of the controller code unchanged.
        """
        sw, sh = self.screen.get_width(), self.screen.get_height()
        font = pygame.font.SysFont("Impact, Arial", max(36, sh // 25), bold=True)
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))
        msg_surf = font.render(text, True, (255, 200, 100))
        self.screen.blit(msg_surf, (sw // 2 - msg_surf.get_width() // 2,
                                     sh // 2 - msg_surf.get_height() // 2))
        # Skip hint in smaller font, bottom centre
        hint_font = pygame.font.SysFont("Arial", max(14, sh // 60))
        hint = hint_font.render("Space / click to skip", True, (180, 180, 200))
        self.screen.blit(hint, (sw // 2 - hint.get_width() // 2,
                                 sh - hint.get_height() - 16))
        display_manager.gpu_flip()

        skip_keys = {pygame.K_SPACE, pygame.K_RETURN, pygame.K_ESCAPE}
        end_at = pygame.time.get_ticks() + duration_ms
        while pygame.time.get_ticks() < end_at:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                if event.type == pygame.KEYDOWN and event.key in skip_keys:
                    return
                if event.type == pygame.MOUSEBUTTONDOWN:
                    return
            pygame.time.wait(16)

    def _animate_ai_war_arc(self, attacker_faction: str, target_id,
                             *, success: bool, duration_ms: int = 500):
        """Brief visual beat for an AI-vs-AI war.

        Draws a faction-coloured travelling pulse from one of the
        attacker's planets to the target.  Blocking, but short — about
        half a second per resolved war.  The map is redrawn every frame
        so icons, borders, and the activity sidebar stay coherent.
        """
        if target_id not in self.galaxy.planets:
            return
        # Pick a source planet owned by the attacker (closest to target for flavor)
        target = self.galaxy.planets[target_id]
        sources = [pid for pid, p in self.galaxy.planets.items()
                   if p.owner == attacker_faction]
        if not sources:
            return
        from .map_renderer import FACTION_COLORS
        color = FACTION_COLORS.get(attacker_faction, (200, 200, 200))

        # Pick the attacker planet with shortest distance to target.
        def _dist(pid):
            p = self.galaxy.planets[pid]
            return (p.position[0] - target.position[0]) ** 2 + \
                   (p.position[1] - target.position[1]) ** 2
        src_id = min(sources, key=_dist)
        src = self.galaxy.planets[src_id]

        sx, sy = self.map_screen._world_to_screen(src.position)
        tx, ty = self.map_screen._world_to_screen(target.position)

        start = pygame.time.get_ticks()
        attackable = []  # no selection concerns during animation
        while True:
            now = pygame.time.get_ticks()
            elapsed = now - start
            if elapsed >= duration_ms:
                break
            # Pump events so the window stays responsive / skippable
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                    return

            progress = elapsed / duration_ms
            # Redraw map under the animation so icons stay live.
            self.map_screen.draw(self.screen, self.galaxy, self.state,
                                  attackable, message=None)

            # Streak line
            pygame.draw.line(self.screen, color, (sx, sy), (tx, ty), 2)
            # Travelling pulse
            px = int(sx + (tx - sx) * progress)
            py = int(sy + (ty - sy) * progress)
            pygame.draw.circle(self.screen, color, (px, py), 7)
            pygame.draw.circle(self.screen, (255, 255, 255), (px, py), 3)

            # Impact flash on the last 20% of the animation
            if progress > 0.8:
                flash_alpha = int(200 * (progress - 0.8) / 0.2)
                flash_color = color if success else (120, 120, 140)
                flash_surf = pygame.Surface((64, 64), pygame.SRCALPHA)
                pygame.draw.circle(flash_surf,
                                    (*flash_color, flash_alpha),
                                    (32, 32), 32)
                self.screen.blit(flash_surf, (tx - 32, ty - 32))

            display_manager.gpu_flip()
            pygame.time.wait(16)

    def _handle_cede_territory(self, faction):
        """Handle Hathor's cede_territory ability: pick a random planet from
        the faction adjacent to player territory and transfer it.

        Returns the planet name if successful, else None.
        """
        candidates = []
        for pid, planet in self.galaxy.planets.items():
            if planet.owner != faction:
                continue
            # Check if adjacent to any player planet
            for neighbor_id in planet.connections:
                neighbor = self.galaxy.planets.get(neighbor_id)
                if neighbor and neighbor.owner == "player":
                    candidates.append(pid)
                    break
        if not candidates:
            return None
        target_id = self.rng.choice(candidates)
        target = self.galaxy.planets[target_id]
        self.galaxy.transfer_ownership(target_id, "player")
        self.state.planet_ownership[target_id] = "player"
        return target.name

    async def _handle_relic_active(self, relic_id: str) -> str | None:
        """Fire a relic active ability.  Resolves ``target_kind`` the
        same way ``_handle_leader_action`` does so target-needing
        relics (e.g. Staff of Ra → enemy planet) play nicely with the
        selected-planet flow.
        """
        from .relics import get_relic, activate_relic, get_active_charges_remaining
        relic = get_relic(relic_id)
        if relic is None or not relic.active_ability:
            return None
        if get_active_charges_remaining(self.state, relic_id) <= 0:
            return "No charges remaining."

        ability = relic.active_ability
        target_kind = ability.get("target_kind", "none")

        target = None
        if target_kind == "faction":
            target = await self._pick_faction_for_action(ability.get("name", relic.name))
            if target is None:
                return None
        elif target_kind in ("own_planet", "enemy_planet", "any_planet"):
            pid = self.map_screen.selected_planet
            if not pid or pid not in self.galaxy.planets:
                return f"Select a {self._target_kind_hint(target_kind)} first."
            planet = self.galaxy.planets[pid]
            if target_kind == "own_planet" and planet.owner != "player":
                return "Select one of your planets first."
            if target_kind == "enemy_planet" and planet.owner in ("player", "neutral"):
                return "Select an enemy planet first."
            target = pid

        msg = activate_relic(self.state, self.galaxy, relic_id, target=target, rng=self.rng)
        if msg:
            activity_log.log(
                self.state, activity_log.CAT_LEADER_ACTION,
                msg, icon="relic",
                faction=getattr(self.state, "player_faction", ""),
            )
        return msg

    async def _handle_leader_action(self, action_id: str) -> str | None:
        """Execute a leader toolkit action, resolving its target.

        Returns a short message to flash, or ``None``.
        """
        action = leader_toolkits.get_action(self.state, action_id)
        if action is None:
            return None

        ok, reason = leader_toolkits.can_use(self.state, self.galaxy, action_id)
        if not ok:
            return reason or "Action unavailable"

        target = None
        if action.target_kind == "faction":
            target = await self._pick_faction_for_action(action.name)
            if target is None:
                return None  # player cancelled
        elif action.target_kind in ("own_planet", "enemy_planet", "any_planet"):
            pid = self.map_screen.selected_planet
            if not pid or pid not in self.galaxy.planets:
                return f"Select a {self._target_kind_hint(action.target_kind)} first."
            planet = self.galaxy.planets[pid]
            if action.target_kind == "own_planet" and planet.owner != "player":
                return "Select one of your planets first."
            if action.target_kind == "enemy_planet" and planet.owner in ("player", "neutral"):
                return "Select an enemy planet first."
            target = pid

        return leader_toolkits.execute(self.state, self.galaxy, action_id,
                                       target=target, rng=self.rng)

    @staticmethod
    def _target_kind_hint(kind: str) -> str:
        return {"own_planet": "planet of yours",
                "enemy_planet": "enemy planet",
                "any_planet": "planet"}.get(kind, "target")

    async def _pick_faction_for_action(self, action_name: str):
        """Pop a small modal asking which faction to target.

        Returns the faction name or ``None`` if cancelled.  Lists every
        faction that still holds at least one planet and is not the
        player's own or friendly faction.
        """
        factions = sorted({p.owner for p in self.galaxy.planets.values()
                           if p.owner not in ("player", "neutral",
                                               self.state.friendly_faction)})
        if not factions:
            return None

        sw, sh = self.screen.get_width(), self.screen.get_height()
        font_title = pygame.font.SysFont("Impact, Arial", max(26, sh // 36), bold=True)
        font_btn = pygame.font.SysFont("Arial", max(18, sh // 50), bold=True)
        btn_w = int(sw * 0.28)
        btn_h = int(sh * 0.06)
        gap = int(sh * 0.015)
        total_h = btn_h * len(factions) + gap * (len(factions) - 1)
        top = (sh - total_h) // 2 + int(sh * 0.04)

        rects = []
        for i, f in enumerate(factions):
            rects.append((pygame.Rect((sw - btn_w) // 2,
                                       top + i * (btn_h + gap),
                                       btn_w, btn_h), f))
        cancel_rect = pygame.Rect((sw - btn_w) // 2,
                                   top + len(factions) * (btn_h + gap),
                                   btn_w, btn_h)

        while True:
            await asyncio.sleep(0)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return None
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    return None
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for rect, f in rects:
                        if rect.collidepoint(event.pos):
                            return f
                    if cancel_rect.collidepoint(event.pos):
                        return None

            overlay = pygame.Surface((sw, sh))
            overlay.fill((0, 0, 0))
            overlay.set_alpha(200)
            self.screen.blit(overlay, (0, 0))
            title = font_title.render(f"{action_name} — Choose a faction",
                                       True, (255, 210, 130))
            self.screen.blit(title, ((sw - title.get_width()) // 2,
                                     top - title.get_height() - int(sh * 0.02)))
            mx, my = pygame.mouse.get_pos()
            for rect, f in rects:
                hovered = rect.collidepoint(mx, my)
                pygame.draw.rect(self.screen,
                                 (40, 60, 100) if not hovered else (70, 110, 170),
                                 rect)
                pygame.draw.rect(self.screen, (150, 180, 220), rect, 2)
                lbl = font_btn.render(f, True, (235, 235, 245))
                self.screen.blit(lbl, (rect.centerx - lbl.get_width() // 2,
                                        rect.centery - lbl.get_height() // 2))
            hovered = cancel_rect.collidepoint(mx, my)
            pygame.draw.rect(self.screen,
                             (80, 40, 40) if not hovered else (120, 60, 60),
                             cancel_rect)
            pygame.draw.rect(self.screen, (180, 120, 120), cancel_rect, 2)
            lbl = font_btn.render("Cancel", True, (235, 235, 245))
            self.screen.blit(lbl, (cancel_rect.centerx - lbl.get_width() // 2,
                                    cancel_rect.centery - lbl.get_height() // 2))
            display_manager.gpu_flip()

    async def _show_trade_proposal(self, faction, message,
                                     accept_label="Accept", reject_label="Decline"):
        """Show an AI trade/diplomatic proposal with customizable buttons.

        Returns True if accepted, False if declined.
        """
        sw, sh = self.screen.get_width(), self.screen.get_height()
        font = pygame.font.SysFont("Impact, Arial", max(30, sh // 30), bold=True)
        info_font = pygame.font.SysFont("Arial", max(18, sh // 50))
        btn_font = pygame.font.SysFont("Arial", max(16, sh // 55), bold=True)

        btn_w = int(sw * 0.12)
        btn_h = int(sh * 0.05)
        gap = int(sw * 0.04)
        accept_rect = pygame.Rect(sw // 2 - btn_w - gap // 2, int(sh * 0.58), btn_w, btn_h)
        decline_rect = pygame.Rect(sw // 2 + gap // 2, int(sh * 0.58), btn_w, btn_h)

        while True:
            await asyncio.sleep(0)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return False
                    elif event.key == pygame.K_RETURN:
                        return True
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if accept_rect.collidepoint(event.pos):
                        return True
                    if decline_rect.collidepoint(event.pos):
                        return False

            # Draw overlay
            overlay = pygame.Surface((sw, sh))
            overlay.fill((0, 0, 0))
            overlay.set_alpha(180)
            self.screen.blit(overlay, (0, 0))

            # Message
            msg_surf = font.render("DIPLOMATIC PROPOSAL", True, (255, 200, 100))
            self.screen.blit(msg_surf, (sw // 2 - msg_surf.get_width() // 2, int(sh * 0.38)))

            detail = info_font.render(message, True, (200, 220, 255))
            self.screen.blit(detail, (sw // 2 - detail.get_width() // 2, int(sh * 0.46)))

            benefit = info_font.render("Free trade: +5 naq/turn, card pool access", True, (100, 220, 255))
            self.screen.blit(benefit, (sw // 2 - benefit.get_width() // 2, int(sh * 0.51)))

            # Buttons
            mx, my = pygame.mouse.get_pos()
            for rect, label, base_color in [
                (accept_rect, accept_label.upper(), (40, 100, 40)),
                (decline_rect, reject_label.upper(), (100, 40, 40)),
            ]:
                hovered = rect.collidepoint(mx, my)
                color = tuple(min(255, c + 40) for c in base_color) if hovered else base_color
                pygame.draw.rect(self.screen, color, rect)
                pygame.draw.rect(self.screen, (200, 200, 200) if hovered else (120, 120, 120), rect, 2)
                lbl = btn_font.render(label, True, (255, 255, 255))
                self.screen.blit(lbl, (rect.centerx - lbl.get_width() // 2,
                                       rect.centery - lbl.get_height() // 2))

            display_manager.gpu_flip()
            pygame.time.Clock().tick(60)

    async def _show_espionage_alert(self, event):
        """Show an AI espionage alert with IGNORE/CAPTURE buttons.

        Returns "ignore" or "capture".
        """
        sw, sh = self.screen.get_width(), self.screen.get_height()
        font = pygame.font.SysFont("Impact, Arial", max(30, sh // 30), bold=True)
        info_font = pygame.font.SysFont("Arial", max(18, sh // 50))
        btn_font = pygame.font.SysFont("Arial", max(16, sh // 55), bold=True)
        desc_font = pygame.font.SysFont("Arial", max(14, sh // 65))

        btn_w = int(sw * 0.14)
        btn_h = int(sh * 0.06)
        gap = int(sw * 0.03)
        btn_y = int(sh * 0.62)
        ignore_rect = pygame.Rect(sw // 2 - btn_w - gap // 2, btn_y, btn_w, btn_h)
        capture_rect = pygame.Rect(sw // 2 + gap // 2, btn_y, btn_w, btn_h)

        while True:
            await asyncio.sleep(0)
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    return "ignore"
                elif ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_ESCAPE:
                        return "ignore"
                elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    if ignore_rect.collidepoint(ev.pos):
                        return "ignore"
                    if capture_rect.collidepoint(ev.pos):
                        return "capture"

            # Draw overlay
            overlay = pygame.Surface((sw, sh))
            overlay.fill((0, 0, 0))
            overlay.set_alpha(180)
            self.screen.blit(overlay, (0, 0))

            # Title
            title_surf = font.render("ESPIONAGE DETECTED!", True, (255, 80, 80))
            self.screen.blit(title_surf, (sw // 2 - title_surf.get_width() // 2, int(sh * 0.32)))

            # Details
            detail = info_font.render(
                f"{event['faction']} operative spotted on {event['planet_name']}!",
                True, (200, 220, 255))
            self.screen.blit(detail, (sw // 2 - detail.get_width() // 2, int(sh * 0.42)))

            mission = info_font.render(
                f"Mission: {event['mission_name']} — {event['mission_desc']}",
                True, (255, 200, 100))
            self.screen.blit(mission, (sw // 2 - mission.get_width() // 2, int(sh * 0.48)))

            chance = info_font.render(
                f"Success chance if ignored: {int(event['success_chance'] * 100)}%",
                True, (200, 200, 200))
            self.screen.blit(chance, (sw // 2 - chance.get_width() // 2, int(sh * 0.54)))

            # Buttons
            mx, my = pygame.mouse.get_pos()
            for rect, label, sub, base_color in [
                (ignore_rect, "IGNORE", "Free — hope it fails", (80, 80, 80)),
                (capture_rect, "CAPTURE", "-20 naq, 60% success", (100, 40, 40)),
            ]:
                hovered = rect.collidepoint(mx, my)
                color = tuple(min(255, c + 40) for c in base_color) if hovered else base_color
                pygame.draw.rect(self.screen, color, rect)
                pygame.draw.rect(self.screen, (200, 200, 200) if hovered else (120, 120, 120), rect, 2)
                lbl = btn_font.render(label, True, (255, 255, 255))
                self.screen.blit(lbl, (rect.centerx - lbl.get_width() // 2,
                                       rect.y + int(btn_h * 0.18)))
                sub_surf = desc_font.render(sub, True, (180, 180, 180))
                self.screen.blit(sub_surf, (rect.centerx - sub_surf.get_width() // 2,
                                             rect.y + int(btn_h * 0.58)))

            display_manager.gpu_flip()
            pygame.time.Clock().tick(60)

    async def _show_incident_choice(self, incident):
        """Show a diplomatic incident choice with DENY/RECALL/DOUBLE DOWN buttons.

        Returns "deny", "recall", or "double_down".
        """
        sw, sh = self.screen.get_width(), self.screen.get_height()
        font = pygame.font.SysFont("Impact, Arial", max(30, sh // 30), bold=True)
        info_font = pygame.font.SysFont("Arial", max(18, sh // 50))
        btn_font = pygame.font.SysFont("Arial", max(16, sh // 55), bold=True)
        desc_font = pygame.font.SysFont("Arial", max(14, sh // 65))

        btn_w = int(sw * 0.16)
        btn_h = int(sh * 0.07)
        gap = int(sw * 0.02)
        total_w = btn_w * 3 + gap * 2
        start_x = sw // 2 - total_w // 2
        btn_y = int(sh * 0.62)
        deny_rect = pygame.Rect(start_x, btn_y, btn_w, btn_h)
        recall_rect = pygame.Rect(start_x + btn_w + gap, btn_y, btn_w, btn_h)
        double_rect = pygame.Rect(start_x + 2 * (btn_w + gap), btn_y, btn_w, btn_h)

        while True:
            await asyncio.sleep(0)
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    return "deny"
                elif ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_ESCAPE:
                        return "deny"
                elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    if deny_rect.collidepoint(ev.pos):
                        return "deny"
                    if recall_rect.collidepoint(ev.pos):
                        return "recall"
                    if double_rect.collidepoint(ev.pos):
                        return "double_down"

            # Draw overlay
            overlay = pygame.Surface((sw, sh))
            overlay.fill((0, 0, 0))
            overlay.set_alpha(180)
            self.screen.blit(overlay, (0, 0))

            # Title
            title_surf = font.render("OPERATIVE DISCOVERED!", True, (255, 180, 60))
            self.screen.blit(title_surf, (sw // 2 - title_surf.get_width() // 2, int(sh * 0.32)))

            # Details
            detail = info_font.render(
                f"{incident['operative_name']} was spotted on {incident['planet_name']}!",
                True, (200, 220, 255))
            self.screen.blit(detail, (sw // 2 - detail.get_width() // 2, int(sh * 0.42)))

            faction_info = info_font.render(
                f"{incident['faction']} demands an explanation.",
                True, (255, 200, 100))
            self.screen.blit(faction_info, (sw // 2 - faction_info.get_width() // 2, int(sh * 0.48)))

            # Buttons
            mx, my = pygame.mouse.get_pos()
            for rect, label, sub, base_color in [
                (deny_rect, "DENY", "50/50 cover holds", (60, 60, 100)),
                (recall_rect, "RECALL", "Safe — no damage", (40, 100, 40)),
                (double_rect, "DOUBLE DOWN", "+20% mission, relations hit", (100, 40, 40)),
            ]:
                hovered = rect.collidepoint(mx, my)
                color = tuple(min(255, c + 40) for c in base_color) if hovered else base_color
                pygame.draw.rect(self.screen, color, rect)
                pygame.draw.rect(self.screen, (200, 200, 200) if hovered else (120, 120, 120), rect, 2)
                lbl = btn_font.render(label, True, (255, 255, 255))
                self.screen.blit(lbl, (rect.centerx - lbl.get_width() // 2,
                                       rect.y + int(btn_h * 0.20)))
                sub_surf = desc_font.render(sub, True, (180, 180, 180))
                self.screen.blit(sub_surf, (rect.centerx - sub_surf.get_width() // 2,
                                             rect.y + int(btn_h * 0.60)))

            display_manager.gpu_flip()
            pygame.time.Clock().tick(60)

    def _show_elite_defender_screen(self, leader_name, faction):
        """Show a dramatic overlay before homeworld battles."""
        sw, sh = self.screen.get_width(), self.screen.get_height()
        from .map_renderer import FACTION_COLORS
        faction_color = FACTION_COLORS.get(faction, (255, 200, 100))

        title_font = pygame.font.SysFont("Impact, Arial", max(48, sh // 18), bold=True)
        sub_font = pygame.font.SysFont("Impact, Arial", max(28, sh // 30), bold=True)
        info_font = pygame.font.SysFont("Arial", max(18, sh // 50))

        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.screen.blit(overlay, (0, 0))

        # Pulsing faction-colored title
        title_surf = title_font.render("ELITE DEFENDER", True, faction_color)
        self.screen.blit(title_surf, (sw // 2 - title_surf.get_width() // 2, int(sh * 0.30)))

        name_surf = sub_font.render(leader_name, True, (255, 255, 255))
        self.screen.blit(name_surf, (sw // 2 - name_surf.get_width() // 2, int(sh * 0.42)))

        warn_surf = info_font.render("All enemy cards have +2 power  |  +2 extra cards in enemy deck",
                                     True, (255, 180, 100))
        self.screen.blit(warn_surf, (sw // 2 - warn_surf.get_width() // 2, int(sh * 0.55)))

        hint_surf = info_font.render("Prepare for battle...", True, (150, 150, 150))
        self.screen.blit(hint_surf, (sw // 2 - hint_surf.get_width() // 2, int(sh * 0.65)))

        display_manager.gpu_flip()
        pygame.time.wait(2500)

    async def _show_end_screen(self, title, subtitle):
        """Show a victory/defeat screen."""
        self.screen = display_manager.screen
        sw, sh = self.screen.get_width(), self.screen.get_height()
        clock = pygame.time.Clock()

        title_font = pygame.font.SysFont("Impact, Arial", max(72, sh // 12), bold=True)
        sub_font = pygame.font.SysFont("Arial", max(28, sh // 30))
        info_font = pygame.font.SysFont("Arial", max(20, sh // 45))

        title_color = (255, 220, 100) if title == "VICTORY" else (255, 80, 80)

        running = True
        while running:
            clock.tick(60)
            await asyncio.sleep(0)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                elif event.type == pygame.KEYDOWN:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    running = False

            self.screen.fill((10, 15, 25))
            t_surf = title_font.render(title, True, title_color)
            self.screen.blit(t_surf, (sw // 2 - t_surf.get_width() // 2, int(sh * 0.25)))
            s_surf = sub_font.render(subtitle, True, (220, 220, 220))
            self.screen.blit(s_surf, (sw // 2 - s_surf.get_width() // 2, int(sh * 0.42)))

            # Stats
            stats_y = int(sh * 0.50)
            stats = [
                f"Turns: {self.state.turn_number}",
                f"Planets: {self.galaxy.get_player_planet_count()}/{len(self.galaxy.planets)}",
                f"Naquadah: {self.state.naquadah}",
                f"Deck size: {len(self.state.current_deck)}",
                f"Relics: {len(self.state.relics)}",
            ]
            # Score and CP from meta-progression
            score_data = getattr(self, '_run_score', None)
            if score_data:
                stats.append(f"SCORE: {score_data['score']}  (x{score_data['breakdown'].get('multiplier', 1.0)} {self.state.difficulty})")
                stats.append(f"Conquest Points earned: +{score_data['cp_earned']}")
            for stat in stats:
                color = (255, 220, 100) if "SCORE:" in stat else (180, 180, 200)
                if "Conquest Points" in stat:
                    color = (100, 255, 200)
                stat_surf = info_font.render(stat, True, color)
                self.screen.blit(stat_surf, (sw // 2 - stat_surf.get_width() // 2, stats_y))
                stats_y += int(sh * 0.035)

            cont = info_font.render("Press any key to continue", True, (150, 150, 150))
            self.screen.blit(cont, (sw // 2 - cont.get_width() // 2, int(sh * 0.85)))
            display_manager.gpu_flip()

    def _finalize_run(self, outcome, victory_type=None):
        """Finalize a campaign run: calculate score, award CP, record stats."""
        from .meta_progression import (calculate_run_score, award_cp,
                                        record_campaign_end, add_high_score)
        score_data = calculate_run_score(self.state, self.galaxy, outcome)
        # Apply victory type score multiplier
        if victory_type and victory_type in VICTORY_SCORE_MULTIPLIERS:
            v_mult = VICTORY_SCORE_MULTIPLIERS[victory_type]
            score_data["score"] = int(score_data["score"] * v_mult)
            score_data["breakdown"]["victory_type"] = victory_type
            score_data["breakdown"]["victory_multiplier"] = v_mult
        award_cp(score_data["cp_earned"])
        record_campaign_end(outcome)
        add_high_score(self.state, score_data)
        # Store for end screen display
        self._run_score = score_data

        # Record conquest stats to persistence
        from deck_persistence import get_persistence
        p = get_persistence()
        cs = p.unlock_data.setdefault("conquest_stats", {})
        if outcome == "victory":
            cs["campaigns_won"] = cs.get("campaigns_won", 0) + 1
            diff_wins = cs.setdefault("difficulty_wins",
                                      {"easy": 0, "normal": 0, "hard": 0, "insane": 0})
            diff_wins[self.state.difficulty] = diff_wins.get(self.state.difficulty, 0) + 1
            best = cs.get("best_victory_turn")
            if best is None or self.state.turn_number < best:
                cs["best_victory_turn"] = self.state.turn_number
        else:
            cs["campaigns_lost"] = cs.get("campaigns_lost", 0) + 1
        cs["total_turns_played"] = cs.get("total_turns_played", 0) + self.state.turn_number
        cs["naquadah_earned"] = cs.get("naquadah_earned", 0) + self.state.naquadah
        # Network tier
        if self.state.network_tier > cs.get("best_network_tier", 0):
            cs["best_network_tier"] = self.state.network_tier
        # Relics
        cs["relics_collected"] = cs.get("relics_collected", 0) + len(self.state.relics)
        unique_relics = cs.setdefault("unique_relics_seen", [])
        for r in self.state.relics:
            if r not in unique_relics:
                unique_relics.append(r)
        # Arcs completed
        from .narrative_arcs import NARRATIVE_ARCS
        arcs_done = 0
        unique_arcs = cs.setdefault("unique_arcs_completed", [])
        for arc_id, progress in self.state.narrative_progress.items():
            arc = NARRATIVE_ARCS.get(arc_id)
            if arc and len(progress) >= len(arc.required_planets):
                arcs_done += 1
                if arc_id not in unique_arcs:
                    unique_arcs.append(arc_id)
        cs["arcs_completed"] = cs.get("arcs_completed", 0) + arcs_done
        p.save_unlocks()

    def _save(self):
        """Save current campaign state."""
        # Sync galaxy data back to state
        self.state.galaxy = self.galaxy.to_dict()
        # Sync ownership
        for pid, planet in self.galaxy.planets.items():
            self.state.planet_ownership[pid] = planet.owner
        save_campaign(self.state)
