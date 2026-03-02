"""
STARGWENT - GALACTIC CONQUEST MODE

Territory-conquest campaign with roguelite deck progression.
Win card battles to claim planets across the galaxy.

Entry point: run_galactic_conquest(screen, unlock_system)
"""

import asyncio
import random
import os
import pygame
import display_manager

from .conquest_menu import run_conquest_menu, run_customize_screen, run_unlocks_screen
from .campaign_state import CampaignState
from .campaign_persistence import (load_campaign, save_campaign, clear_campaign,
                                    load_conquest_settings)
from .galaxy_map import GalaxyMap
from .campaign_controller import CampaignController
from .faction_setup import run_faction_setup

# --- Conquest Music (loops during conquest menu & galaxy map) ---
CONQUEST_MUSIC_PATH = os.path.join("assets", "audio", "conquest.ogg")
_conquest_music_playing = False


def _ensure_mixer():
    """Initialize the mixer once before trying to play anything."""
    if pygame.mixer.get_init():
        return True
    try:
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
        return True
    except pygame.error as exc:
        print(f"[audio] Mixer init failed, conquest music disabled: {exc}")
        return False


def start_conquest_music():
    """Start the conquest background track (infinite loop)."""
    from game_settings import get_settings
    global _conquest_music_playing
    if _conquest_music_playing:
        return
    if not os.path.exists(CONQUEST_MUSIC_PATH):
        print("[audio] Conquest music file missing:", CONQUEST_MUSIC_PATH)
        return
    if not _ensure_mixer():
        return
    try:
        settings = get_settings()
        volume = settings.get_effective_music_volume()
        pygame.mixer.music.load(CONQUEST_MUSIC_PATH)
        pygame.mixer.music.set_volume(volume)
        pygame.mixer.music.play(-1)  # Loop infinitely
        _conquest_music_playing = True
        print(f"[audio] Conquest music playing at volume {volume:.2f}")
    except pygame.error as exc:
        print(f"[audio] Unable to start conquest music: {exc}")


def stop_conquest_music(fade_ms=600):
    """Stop the conquest track with optional fadeout."""
    global _conquest_music_playing
    if not _conquest_music_playing:
        return
    if not pygame.mixer.get_init():
        _conquest_music_playing = False
        return
    try:
        import sys
        if sys.platform == "emscripten":
            pygame.mixer.music.stop()
        else:
            pygame.mixer.music.fadeout(fade_ms)
    except pygame.error:
        pygame.mixer.music.stop()
    _conquest_music_playing = False


async def run_galactic_conquest(screen, unlock_system, toggle_fullscreen_callback=None):
    """
    Main entry point for Galactic Conquest mode.

    Called from main_menu.py when the player selects the mode.

    Args:
        screen: Pygame display surface
        unlock_system: CardUnlockSystem instance
        toggle_fullscreen_callback: Optional fullscreen toggle function

    Returns:
        None (returns to main menu)
    """
    start_conquest_music()

    while True:
        # Show conquest submenu
        action = await run_conquest_menu(screen, unlock_system, toggle_fullscreen_callback)
        # Refresh screen after potential fullscreen toggle
        screen = display_manager.screen

        if action is None or action == "back":
            stop_conquest_music()
            return

        result = None
        if action == "new_run":
            # Stop music during faction setup (different screen context)
            stop_conquest_music()
            result = await _start_new_campaign(screen, unlock_system, toggle_fullscreen_callback)
            # Restart when returning to submenu
            if result != "quit":
                start_conquest_music()
        elif action == "resume":
            result = await _resume_campaign(screen)
            # Restart when returning to submenu
            if result != "quit":
                start_conquest_music()
        elif action == "customize_run":
            await run_customize_screen(screen, toggle_fullscreen_callback)
            screen = display_manager.screen
            continue
        elif action == "unlocks":
            stop_conquest_music()
            await run_unlocks_screen(screen, toggle_fullscreen_callback)
            screen = display_manager.screen
            start_conquest_music()
            continue

        if result == "quit":
            stop_conquest_music()
            return
        # Otherwise loop back to submenu (after victory/defeat/save_quit)


async def _start_new_campaign(screen, unlock_system, toggle_fullscreen_callback=None):
    """Start a fresh campaign: faction select -> generate galaxy -> begin."""
    # Faction + leader + deck selection (supports custom decks)
    setup = await run_faction_setup(screen, unlock_system, toggle_fullscreen_callback)
    screen = display_manager.screen  # Refresh after potential fullscreen toggle

    if not setup:
        return "back"

    player_faction = setup["faction"]
    player_leader = setup["leader"]
    player_deck_ids = setup["deck_ids"]

    # Load customize run settings
    settings = load_conquest_settings()
    friendly_faction = settings.get("friendly_faction")
    neutral_count = settings.get("neutral_count", 5)
    enemy_leaders = settings.get("enemy_leaders", {})
    difficulty = settings.get("difficulty", "normal")

    # If friendly faction == player faction, treat as None
    if friendly_faction == player_faction:
        friendly_faction = None

    # Generate galaxy with settings
    seed = random.randint(0, 2**31)
    galaxy = GalaxyMap()
    galaxy.generate(seed, player_faction,
                    friendly_faction=friendly_faction,
                    neutral_count=neutral_count,
                    enemy_leaders=enemy_leaders)

    # Build initial planet ownership
    planet_ownership = {}
    for pid, planet in galaxy.planets.items():
        planet_ownership[pid] = planet.owner

    # Create campaign state with difficulty-scaled starting naquadah
    from .difficulty import get_start_naquadah
    start_naq = get_start_naquadah(difficulty)

    state = CampaignState(
        player_faction=player_faction,
        player_leader=player_leader,
        current_deck=player_deck_ids,
        naquadah=start_naq,
        turn_number=1,
        planet_ownership=planet_ownership,
        galaxy=galaxy.to_dict(),
        seed=seed,
        friendly_faction=friendly_faction,
        neutral_count=neutral_count,
        enemy_leaders=enemy_leaders,
        difficulty=difficulty,
    )

    # Apply meta-progression perks to the new campaign
    from .meta_progression import apply_meta_perks_to_campaign
    apply_meta_perks_to_campaign(state)

    # Track campaign start stats
    from deck_persistence import get_persistence
    p = get_persistence()
    cs = p.unlock_data.setdefault("conquest_stats", {})
    cs["campaigns_started"] = cs.get("campaigns_started", 0) + 1
    factions_used = cs.setdefault("conquest_factions_used", {})
    factions_used[player_faction] = factions_used.get(player_faction, 0) + 1
    leader_name = player_leader.get("name", "Unknown") if player_leader else "Unknown"
    leaders_used = cs.setdefault("conquest_leaders_used", {})
    leaders_used[leader_name] = leaders_used.get(leader_name, 0) + 1
    p.save_unlocks()

    # Handle relic choice perk (Repository of Knowledge)
    relic_options = state.conquest_ability_data.pop("relic_choice_options", None)
    if relic_options:
        from .relic_screen import show_relic_choice
        chosen = await show_relic_choice(screen, relic_options)
        screen = display_manager.screen
        if chosen:
            state.add_relic(chosen)

    # Clear any old save and save new campaign
    clear_campaign()
    save_campaign(state)

    # Run campaign
    controller = CampaignController(screen, state)
    return await controller.run()


async def _resume_campaign(screen):
    """Resume a saved campaign."""
    state = load_campaign()
    if not state:
        return "back"

    controller = CampaignController(screen, state)
    return await controller.run()
