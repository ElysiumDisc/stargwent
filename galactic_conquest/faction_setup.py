"""
STARGWENT - GALACTIC CONQUEST - Faction Setup

Faction and deck selection for starting a new campaign.
Leaders are chosen per-battle, not at campaign start.
"""

import pygame
import os
import display_manager
from deck_builder import run_deck_builder, build_faction_deck, load_default_faction_deck, FACTION_LEADERS
from main_menu import DeckManager
from cards import ALL_CARDS, FACTION_TAURI, FACTION_GOAULD, FACTION_JAFFA, FACTION_LUCIAN, FACTION_ASGARD, FACTION_ALTERAN


ALL_FACTIONS = [FACTION_TAURI, FACTION_GOAULD, FACTION_JAFFA, FACTION_LUCIAN, FACTION_ASGARD, FACTION_ALTERAN]

FACTION_COLORS = {
    FACTION_TAURI: (50, 120, 200),
    FACTION_GOAULD: (200, 50, 50),
    FACTION_JAFFA: (200, 180, 50),
    FACTION_LUCIAN: (200, 80, 180),
    FACTION_ASGARD: (100, 180, 220),
    FACTION_ALTERAN: (100, 200, 170),
}


async def run_faction_setup(screen, unlock_system, toggle_fullscreen_callback=None):
    """
    Run faction + deck selection for a new campaign.
    Uses the existing deck builder UI for faction and deck selection.
    Leaders are NOT chosen here — they are selected per-battle.

    Returns:
        dict with {faction, leader (None), deck_ids} or None if cancelled.
    """
    # Use the existing deck builder in "for_new_game" mode
    # Player picks faction and optionally customizes their deck
    # The leader selected in deck builder is ignored — leaders are chosen per-battle
    deck_result = await run_deck_builder(
        screen,
        for_new_game=True,
        unlock_override=unlock_system.is_unlock_override_enabled(),
        unlock_system=unlock_system,
        toggle_fullscreen_callback=toggle_fullscreen_callback
    )

    if not deck_result:
        return None

    player_faction = deck_result['faction']
    # Leader is NOT locked at campaign start — chosen per-battle instead
    player_deck_ids = list(deck_result['deck_ids'])

    # Check if player has a custom deck for this faction
    deck_manager = DeckManager(unlock_system)
    deck_manager.load_decks()
    custom_deck_data = deck_manager.get_deck(player_faction)
    if custom_deck_data and custom_deck_data.get("cards"):
        # Use custom deck
        player_deck_ids = [cid for cid in custom_deck_data["cards"]
                          if cid != 'leader' and cid in ALL_CARDS]

    return {
        "faction": player_faction,
        "leader": None,
        "deck_ids": player_deck_ids,
    }
