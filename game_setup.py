import pygame
import sys
import random
import os
import copy
from game import Game
from deck_builder import run_deck_builder, build_faction_deck, FACTION_LEADERS
from main_menu import run_main_menu, DeckManager, show_stargate_opening
from ai_opponent import AIController
from lan_opponent import NetworkController, NetworkPlayerProxy
from cards import ALL_CARDS, FACTION_TAURI, FACTION_GOAULD, FACTION_JAFFA, FACTION_LUCIAN, FACTION_ASGARD
from draft_mode import DraftRun
from game_config import FACTION_GLOW_COLORS

def initialize_game(screen, unlock_system, lan_mode=False, lan_context=None,
                   toggle_fullscreen_callback=None, lan_game_data=None):
    """
    Handles game initialization flow: menu, deck selection, game creation.
    Returns:
        (game, ai_controller, network_proxy, menu_action) or None if quitting.
    """

    # Initialize unlock system if not provided
    if unlock_system is None:
        from unlocks import CardUnlockSystem
        unlock_system = CardUnlockSystem()

    # Main Menu Loop
    menu_action = None
    lan_data = None
    
    # If pre-configured LAN game data provided (e.g. from recursion/rematch), use it directly
    if lan_game_data:
        # We assume lan_game_data contains { 'game': ..., 'player_faction': ..., etc }
        if 'game' in lan_game_data:
             # Just return the game object directly
             return lan_game_data['game'], None, None, 'lan_game'

        # Rematch: If we have faction info but no game object, set up for rematch
        if 'player_faction' in lan_game_data:
            # Show Stargate opening animation for rematch
            if not os.environ.get('STARGWENT_SKIP_INTRO'):
                if not show_stargate_opening(screen):
                    return None
                os.environ['STARGWENT_SKIP_INTRO'] = '1'

            player_faction = lan_game_data.get('player_faction')
            player_leader = lan_game_data.get('player_leader')
            ai_faction = lan_game_data.get('ai_faction')
            ai_leader = lan_game_data.get('ai_leader')

            # Build decks for both players
            deck_manager = DeckManager(unlock_system)
            deck_manager.load_decks()

            # Player deck - check for custom deck
            custom_deck_data = deck_manager.get_deck(player_faction)
            if custom_deck_data and custom_deck_data.get("cards"):
                player_deck_ids = custom_deck_data["cards"]
                player_deck = [copy.deepcopy(ALL_CARDS[id]) for id in player_deck_ids if id != 'leader' and id in ALL_CARDS]
            else:
                player_deck_ids = build_faction_deck(player_faction, player_leader)
                player_deck = [copy.deepcopy(ALL_CARDS[id]) for id in player_deck_ids]
            random.shuffle(player_deck)

            # AI deck
            ai_deck_ids = build_faction_deck(ai_faction, ai_leader)
            ai_deck = [copy.deepcopy(ALL_CARDS[id]) for id in ai_deck_ids]

            # Create game
            game = Game(
                player1_faction=player_faction,
                player1_deck=player_deck,
                player1_leader=player_leader,
                player2_faction=ai_faction,
                player2_deck=ai_deck,
                player2_leader=ai_leader
            )

            # Create AI controller
            ai_controller = AIController(game, game.player2, difficulty="hard")

            return game, ai_controller, None, 'rematch'

    # If LAN context provided, skip menu
    if lan_mode and lan_context:
        menu_action = "lan_game"
        lan_data = {"context": lan_context}
    elif not lan_game_data:
        # Run main menu
        result = run_main_menu(screen, unlock_system, toggle_fullscreen_callback)
        if not result:
            return None
        
        if isinstance(result, dict): # LAN game data
            menu_action = "lan_game"
            lan_data = result
        else:
            menu_action = result
    
    # ... Rest of function ...

    # Handle different game modes
    player_deck = []
    player_faction = FACTION_TAURI
    player_leader = None
    
    ai_faction = FACTION_GOAULD
    ai_deck = []
    ai_leader = None
    
    game_seed = None
    
    # Draft Mode
    if menu_action == 'draft_mode':
        from draft_controller import launch_draft_mode
        # Run draft menu to start a run
        draft_result = launch_draft_mode(screen, unlock_system)
        if not draft_result:
            return initialize_game(screen, unlock_system, toggle_fullscreen_callback=toggle_fullscreen_callback)

        # If draft result is a deck, we are ready to play
        if isinstance(draft_result, dict) and 'cards' in draft_result:
            # Show Stargate opening animation before starting draft game
            if not os.environ.get('STARGWENT_SKIP_INTRO'):
                if not show_stargate_opening(screen):
                    return None
                # Set flag to skip on retry/back
                os.environ['STARGWENT_SKIP_INTRO'] = '1'

            player_leader = draft_result['leader']
            player_deck = draft_result['cards']
            player_faction = player_leader.get('faction', 'Neutral')

            # Create game with this deck against random opponent
            # AI setup similar to new_game
            factions = [FACTION_TAURI, FACTION_GOAULD, FACTION_JAFFA, FACTION_LUCIAN, FACTION_ASGARD]
            ai_faction = random.choice([f for f in factions if f != player_faction])
            ai_leader = dict(random.choice(FACTION_LEADERS[ai_faction]))
            ai_leader.setdefault('faction', ai_faction)
            ai_deck_ids = build_faction_deck(ai_faction, ai_leader)
            ai_deck = [copy.deepcopy(ALL_CARDS[id]) for id in ai_deck_ids]

            # Store draft run object in game for progression
            # We need to pass this to the Game object somehow or handle post-game
            # For now, we'll let the Game object know it's a draft game
            pass
            
    # New Game (Standard)
    elif menu_action == 'new_game':
        # Show Stargate opening animation before starting new game
        if not os.environ.get('STARGWENT_SKIP_INTRO'):
            if not show_stargate_opening(screen):
                return None
            # Set flag to skip on retry/back
            os.environ['STARGWENT_SKIP_INTRO'] = '1'

        # Deck Builder / Selection
        deck_result = run_deck_builder(
            screen,
            for_new_game=True,
            unlock_override=unlock_system.is_unlock_override_enabled(),
            unlock_system=unlock_system,
            toggle_fullscreen_callback=toggle_fullscreen_callback
        )
        
        if not deck_result:
            return initialize_game(screen, unlock_system, toggle_fullscreen_callback=toggle_fullscreen_callback)

        player_faction = deck_result['faction']
        player_leader = dict(deck_result['leader'])
        player_leader.setdefault('faction', player_faction)
        player_deck_ids = deck_result['deck_ids']

        # Check if player has a custom deck for this faction
        deck_manager = DeckManager(unlock_system)
        deck_manager.load_decks()
        custom_deck_data = deck_manager.get_deck(player_faction)
        if custom_deck_data and custom_deck_data.get("cards"):
            # Use custom deck
            custom_card_ids = custom_deck_data["cards"]
            # Filter out 'leader' key and invalid cards - deep copy to prevent shared state
            player_deck = [copy.deepcopy(ALL_CARDS[id]) for id in custom_card_ids if id != 'leader' and id in ALL_CARDS]
            # Shuffle custom deck
            random.shuffle(player_deck)
        else:
            # Use default faction deck - deep copy to prevent shared state
            player_deck = [copy.deepcopy(ALL_CARDS[id]) for id in player_deck_ids]

        # Setup AI
        factions = [FACTION_TAURI, FACTION_GOAULD, FACTION_JAFFA, FACTION_LUCIAN, FACTION_ASGARD]
        ai_faction = random.choice([f for f in factions if f != player_faction])
        ai_leader = dict(random.choice(FACTION_LEADERS[ai_faction]))
        ai_leader.setdefault('faction', ai_faction)
        ai_deck_ids = build_faction_deck(ai_faction, ai_leader)
        ai_deck = [copy.deepcopy(ALL_CARDS[id]) for id in ai_deck_ids]
        
    # LAN Game
    elif menu_action == 'lan_game' and lan_data:
        # LAN Setup is complex, handled by lan_game.py logic usually
        # But here we integrate it
        context = lan_data.get("context")
        if context:
            # Setup from context
            # Helper to find leader
            from content_registry import UNLOCKABLE_LEADERS

            def find_leader(faction, leader_id):
                # Check base leaders
                for leader in FACTION_LEADERS.get(faction, []):
                    if leader.get("card_id") == leader_id:
                        return leader
                # Check unlockable leaders
                if faction in UNLOCKABLE_LEADERS:
                    for leader in UNLOCKABLE_LEADERS[faction]:
                        if leader.get("card_id") == leader_id:
                            return leader
                # Fallback
                return FACTION_LEADERS.get(faction, [{}])[0]

            player_faction = context.local.faction
            player_deck = [copy.deepcopy(ALL_CARDS[cid]) for cid in context.local.deck_ids if cid in ALL_CARDS]
            player_leader = find_leader(player_faction, context.local.leader_id)

            ai_faction = context.remote.faction
            ai_deck = [copy.deepcopy(ALL_CARDS[cid]) for cid in context.remote.deck_ids if cid in ALL_CARDS]
            ai_leader = find_leader(ai_faction, context.remote.leader_id)
            
            game_seed = context.seed
            
    # Initialize Game Object
    game = Game(
        player1_faction=player_faction,
        player1_deck=player_deck,
        player1_leader=player_leader,
        player2_faction=ai_faction,
        player2_deck=ai_deck,
        player2_leader=ai_leader,
        seed=game_seed
    )
    
    # Flag draft mode if applicable
    if menu_action == 'draft_mode':
        game.is_draft_match = True
        # Attach draft run if available (hacky but works)
        # In a real refactor, Game would take game_mode as param
    
    # Initialize Controller
    ai_controller = None
    network_proxy = None
    
    if menu_action == 'lan_game' and lan_data and lan_data.get("context"):
        context = lan_data["context"]
        ai_controller = NetworkController(game, game.player2, context.session, context.role)
        network_proxy = NetworkPlayerProxy(context.session, context.role, game)
        # Set global LAN context for main loop (still needed for chat/polling)
        # This is a side effect, but necessary until full refactor
        # We return it so main can set it
    else:
        ai_controller = AIController(game, game.player2, difficulty="hard")
        
    return game, ai_controller, network_proxy, menu_action

def create_game_from_saved_settings(previous_game):
    """Create a new game using the same settings as a previous game."""
    from game import Game
    from persistence import get_persistence

    persistence = get_persistence()

    # Get deck and leader info from persistence
    player1_deck_data = persistence.get_deck(previous_game.player1_faction)
    player2_deck_data = persistence.get_deck(previous_game.player2_faction)

    player1_deck = player1_deck_data.get("cards", [])
    player1_leader = player1_deck_data.get("leader", None)

    player2_deck = player2_deck_data.get("cards", [])
    player2_leader = player2_deck_data.get("leader", None)

    # Create new game with same settings
    new_game = Game(
        player1_faction=previous_game.player1_faction,
        player1_deck=player1_deck,
        player1_leader=player1_leader,
        player2_faction=previous_game.player2_faction,
        player2_deck=player2_deck,
        player2_leader=player2_leader
    )

    return new_game
