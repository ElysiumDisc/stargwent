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
                         get_attack_extra_cards, construct_building, BUILDINGS, can_build)
from .crisis_events import should_trigger_crisis, pick_crisis, apply_crisis, show_crisis_screen
from .diplomacy import (check_ai_trade_proposals, get_adjacency_bonus_factions,
                         get_trade_income, get_alliance_upkeep, set_relation,
                         TRADING, check_conquest_strain)
from .minor_worlds import (init_minor_worlds, ensure_minor_world,
                            decay_minor_world_influence, ai_court_minor_worlds,
                            apply_minor_world_income, notify_quest_event,
                            get_minor_world_bonuses)
from .doctrines import (get_active_effects, apply_wisdom_income, get_wisdom_per_turn)
from .espionage import (tick_operatives, check_earn_operative, get_sabotage_effect,
                         get_operative_summary)
from .victory_conditions import (check_any_victory, tick_supergate, VICTORY_INFO,
                                   VICTORY_SCORE_MULTIPLIERS)


# AI counterattack chance per faction with adjacent border (now overridden by difficulty)
AI_COUNTERATTACK_CHANCE = 0.30
# Cooldown turns after failed attack
ATTACK_COOLDOWN = 3

# Faction-specific bonuses when conquering a faction's planet
FACTION_CONQUEST_BONUSES = {
    "Tau'ri": {"type": "extra_card", "desc": "Intel: +1 random card"},
    "Goa'uld": {"type": "upgrade_card", "desc": "Domination: +2 power to a random card"},
    "Jaffa Rebellion": {"type": "remove_weak", "desc": "Training: removed weakest card"},
    "Lucian Alliance": {"type": "naquadah", "value": 50, "desc": "Trade: +50 naquadah"},
    "Asgard": {"type": "upgrade_multi", "desc": "Tech: +1 power to 2 random cards"},
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
            elif action and action.startswith("build_"):
                building_id = action[6:]  # strip "build_" prefix
                planet_id = self.map_screen.selected_planet
                if planet_id and can_build(self.state, planet_id, building_id, self.galaxy):
                    msg = construct_building(self.state, planet_id, building_id)
                    if msg:
                        self.message = msg
                        # Minor world quest: build event
                        for _qpid, _qmsg in notify_quest_event(self.state, "build"):
                            self._flash_message(_qmsg, 1200)
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
            elif action == "attack":
                planet_id = self.map_screen.selected_planet
                if planet_id:
                    result = await self._attack_planet(planet_id)
                    if result == "quit":
                        return "quit"
            elif action == "end_turn":
                # AI counterattack phase
                ai_result = self._ai_counterattack_phase()
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
                # Apply cooldown reduction passive
                cd_reduce = get_cooldown_reduction(self.galaxy)
                if cd_reduce > 0:
                    for pid in list(self.state.cooldowns):
                        self.state.cooldowns[pid] = max(0, self.state.cooldowns[pid] - cd_reduce)
                    # Clean up expired
                    self.state.cooldowns = {k: v for k, v in self.state.cooldowns.items() if v > 0}
                self.rng = random.Random(self.state.seed + self.state.turn_number)

                # Turn summary display — brief animated income breakdown
                await self._show_turn_summary()

                # Planet passive income + relic income + network bonus + building income
                allied = get_adjacency_bonus_factions(self.state)
                naq_income = get_naquadah_per_turn(self.galaxy, allied)
                if self.state.has_relic("naquadah_reactor"):
                    naq_income += 10
                network = self._get_network_cached(allied)
                naq_income += network["naq_bonus"]
                naq_income += get_building_naq_income(self.state, self.galaxy)
                # Diplomacy: trade income and alliance upkeep
                trade_income = get_trade_income(self.state)
                alliance_upkeep = get_alliance_upkeep(self.state)
                naq_income += trade_income
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
                # Tick crisis cooldown
                if self.state.crisis_cooldown > 0:
                    self.state.crisis_cooldown -= 1

                # Minor worlds: decay influence, AI courting, income
                init_minor_worlds(self.state, self.galaxy)
                decay_minor_world_influence(self.state)
                ai_court_minor_worlds(self.state, self.galaxy, self.rng)
                mw_naq = apply_minor_world_income(self.state, self.galaxy)
                if mw_naq > 0:
                    self.state.add_naquadah(mw_naq)

                # Wisdom income from doctrines + ancient planets + minor worlds
                wisdom_gained = apply_wisdom_income(self.state, self.galaxy)

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

                # AI trade proposals (weakened factions offer deals)
                proposals = check_ai_trade_proposals(self.state, self.galaxy, self.rng)
                for prop_faction, prop_msg in proposals:
                    accepted = await self._show_trade_proposal(prop_faction, prop_msg)
                    if accepted:
                        set_relation(self.state, prop_faction, TRADING)
                        from .diplomacy import _track_conquest_stat
                        _track_conquest_stat("ai_trades_accepted")
                        turn_msg += f" | {prop_faction} trade accepted!"
                    else:
                        turn_msg += f" | {prop_faction} trade declined."

                # Ancient Repository relic: +30 naq/turn if player controls Atlantis
                if self.state.has_relic("ancient_repository"):
                    atlantis_controlled = any(
                        p.name == "Atlantis" and p.owner == "player"
                        for p in self.galaxy.planets.values())
                    if atlantis_controlled:
                        self.state.add_naquadah(30)
                        turn_msg += " | Ancient Repository: +30 naq"

                # Crisis events: 10% chance after turn 5
                if should_trigger_crisis(self.state):
                    crisis = pick_crisis(self.state)
                    if crisis:
                        crisis_result = apply_crisis(self.state, self.galaxy, crisis, self.rng)
                        await show_crisis_screen(self.screen, crisis, crisis_result)
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

                # Espionage: tick operatives + check earn
                esp_messages = tick_operatives(self.state, self.galaxy, self.rng)
                for esp_msg in esp_messages:
                    turn_msg += f" | {esp_msg}"
                earn_msg = check_earn_operative(self.state, self.rng)
                if earn_msg:
                    turn_msg += f" | {earn_msg}"

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

                action = self.map_screen.handle_event(
                    event, self.galaxy, self.state, attackable)
                if action:
                    return action

            self.map_screen.draw(
                self.screen, self.galaxy, self.state, attackable, self.message)
            display_manager.gpu_flip()

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

        card_result = self._run_card_battle(planet, ai_elite_bonus=ai_elite_bonus,
                                             ai_extra_cards=ai_extra_cards)
        self._refresh_after_battle()
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
            self.galaxy.transfer_ownership(planet_id, "player")
            self.state.planet_ownership[planet_id] = "player"
            self.message = f"Conquered {planet.name}!"
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

            # Reward screen — quality scales with planets controlled
            extra_choices = get_card_choice_bonus(self.galaxy)
            # Relic: Alteran Database gives +1 card choice
            if hasattr(self.state, 'relics') and "alteran_database" in self.state.relics:
                extra_choices += 1
            # Meta perk: Tok'ra Intelligence gives +1 card choice
            from .meta_progression import has_perk
            if has_perk("expanded_rewards"):
                extra_choices += 1
            # Trading partners: include their faction cards in reward pool
            trading_factions = [f for f, rel in self.state.faction_relations.items()
                                if rel == "trading"]
            reward_result = await run_reward_screen(
                self.screen, self.state, planet.faction,
                planet_type=planet.planet_type,
                galaxy_map=self.galaxy,
                bonus_message=bonus_msg,
                extra_card_choices=extra_choices,
                trading_factions=trading_factions)
            self._refresh_after_battle()
            if reward_result == "quit":
                return "quit"

            # Relic: Asgard Core bonus naquadah on victory
            if self.state.has_relic("asgard_core"):
                self.state.add_naquadah(20)

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

            # Conquest near allies causes diplomatic strain
            strain_msg = check_conquest_strain(self.state, planet, self.galaxy, self.rng)
            if strain_msg:
                self._flash_message(strain_msg, 2000)

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

            # Check narrative arc progress
            await self._check_narrative_arcs(planet.name)
        else:
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

    def _run_card_battle(self, planet, ai_elite_bonus=0, ai_extra_cards=0):
        """Run a card battle against a planet's defender. Returns battle outcome."""
        ai_faction = planet.faction
        ai_leader = planet.defender_leader
        # Weaken enemy passive: remove cards from AI deck
        weaken_amount = int(get_total_passive(self.galaxy, "weaken_enemy"))
        # Espionage sabotage: additional card removal from operative missions
        sabotage_cards = get_sabotage_effect(self.state, planet.id)
        weaken_amount += sabotage_cards

        result = run_card_battle(
            self.screen,
            player_faction=self.state.player_faction,
            player_leader=self.state.player_leader,
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
        )
        return result

    def _refresh_after_battle(self):
        """Refresh screen and clear events after returning from a battle/event screen."""
        self.screen = display_manager.screen
        self.map_screen = MapScreen(self.screen.get_width(), self.screen.get_height())
        pygame.event.clear()
        self._music_start()

    def _ai_counterattack_phase(self):
        """Process AI counterattacks. Returns 'done', 'defeat', or 'quit'."""
        # Meta perk: Diplomatic Immunity — first counterattack auto-fails
        from .meta_progression import has_perk
        diplomatic_immunity = (has_perk("diplomatic_immunity")
                               and not self.state.conquest_ability_data.get("diplomatic_immunity_used"))

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

            # Base chance from difficulty, reduced by passives + network tier
            base_chance = get_counterattack_chance(self.state.difficulty)
            network = self._get_network_cached(allied)
            betrayal_bonus = get_betrayal_counter_bonus(self.state, faction)
            effective_chance = (base_chance + betrayal_bonus
                                - get_counterattack_reduction(self.galaxy, allied)
                                - network["counterattack_reduction"])

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

            self._music_stop()
            # Defense battles use the target planet's weather
            fort_level = getattr(self.state, 'fortification_levels', {}).get(target_id, 0)
            # Extra defense cards passive
            extra_defense = int(get_total_passive(self.galaxy, "extra_defense_card"))
            # Building: Training Ground defense bonus
            building_defense = get_defense_bonus(self.state, target_id)
            fort_level += building_defense
            # Conquest leader ability: on_defense (pre-battle bonuses)
            defense_bonus_power = 0
            defense_result = trigger_ability(
                self.state, self.galaxy, "on_defense",
                {"rng": self.rng, "planet_id": target_id})
            if isinstance(defense_result, dict):
                defense_bonus_power = defense_result.get("defense_power_bonus", 0)
                extra_defense += defense_result.get("defense_extra_cards", 0)
            result = run_card_battle(
                self.screen,
                player_faction=self.state.player_faction,
                player_leader=self.state.player_leader,
                player_deck_ids=list(self.state.current_deck),
                ai_faction=faction,
                ai_leader=ai_leader,
                exempt_penalties=True,
                starting_weather=target.weather_preset,
                upgraded_cards=self.state.upgraded_cards,
                relics=getattr(self.state, 'relics', []),
                extra_player_cards=extra_defense,
                fort_defense_bonus=fort_level + defense_bonus_power,
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

        for faction in war_factions:
            targets = self.galaxy.get_ai_vs_ai_targets(faction)
            if not targets:
                continue

            # Attack chance scales with planet count
            planet_count = self.galaxy.get_faction_planet_count(faction)
            attack_chance = min(0.40, 0.15 + 0.05 * planet_count)
            if self.rng.random() > attack_chance:
                continue

            target_id = self.rng.choice(targets)
            target = self.galaxy.planets[target_id]
            defender_faction = target.owner

            # Success weighted by relative strength
            attacker_strength = self.galaxy.get_faction_planet_count(faction)
            defender_strength = self.galaxy.get_faction_planet_count(defender_faction)
            total = attacker_strength + defender_strength
            if total == 0:
                continue
            success_chance = 0.25 + 0.30 * (attacker_strength / total)
            success_chance = max(0.25, min(0.55, success_chance))

            if self.rng.random() < success_chance:
                # Capture!
                self.galaxy.transfer_ownership(target_id, faction)
                self.state.planet_ownership[target_id] = faction
                self._flash_message(f"{faction} captured {target.name} from {defender_faction}!", 1500)

                # Check if a faction was eliminated
                if self.galaxy.get_faction_planet_count(defender_faction) == 0:
                    self._flash_message(f"{defender_faction} has been ELIMINATED!", 2000)

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
            leader_name = self.state.player_leader.get("name", "Unknown") if self.state.player_leader else "Unknown"
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
        player_leader = self.state.player_leader.get("name", "?") if self.state.player_leader else "?"
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
        """Show a message overlay for a brief duration."""
        sw, sh = self.screen.get_width(), self.screen.get_height()
        font = pygame.font.SysFont("Impact, Arial", max(36, sh // 25), bold=True)
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))
        msg_surf = font.render(text, True, (255, 200, 100))
        self.screen.blit(msg_surf, (sw // 2 - msg_surf.get_width() // 2,
                                     sh // 2 - msg_surf.get_height() // 2))
        display_manager.gpu_flip()
        pygame.time.wait(duration_ms)

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

    async def _show_trade_proposal(self, faction, message):
        """Show an AI trade proposal with ACCEPT/DECLINE buttons.

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
                (accept_rect, "ACCEPT", (40, 100, 40)),
                (decline_rect, "DECLINE", (100, 40, 40)),
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
