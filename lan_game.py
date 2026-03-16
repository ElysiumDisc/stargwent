import random
import asyncio
import pygame
import display_manager
from typing import Optional
from deck_builder import run_deck_builder, FACTION_LEADERS, build_faction_deck
from leader_matchup import LeaderMatchupAnimation
from lan_session import LanSession
from lan_context import LanContext, LanDeckSelection
from lan_protocol import (
    build_deck_message,
    build_seed_message,
    build_chat_message,
    LanMessageType,
    parse_message,
)
from lan_chat import LanChatPanel

CHAT_FONT = None


def get_chat_font(size=24):
    global CHAT_FONT
    if CHAT_FONT is None:
        CHAT_FONT = pygame.font.SysFont("Consolas", size)
    return CHAT_FONT


def find_leader(faction, leader_id):
    for leader in FACTION_LEADERS.get(faction, []):
        if leader.get("id") == leader_id:
            data = dict(leader)
            data.setdefault("faction", faction)
            return data
    return {"id": leader_id, "name": leader_id, "faction": faction}


async def wait_for_message(session, expected_type):
    while True:
        await asyncio.sleep(0)
        msg = session.receive()
        if msg:
            parsed = parse_message(msg)
            if parsed.get("type") == expected_type:
                return msg.get("payload")
            elif msg.get("type") == "disconnect":
                return None
        pygame.time.wait(50)


async def run_lan_setup(screen, unlock_system, session: LanSession, role: str, toggle_fullscreen_callback=None) -> Optional[LanContext]:
    from lan_lobby import run_lan_lobby

    # Show waiting lobby with chat until both players are ready
    ready = await run_lan_lobby(screen, session, role)
    if not ready:
        session.close()
        return None

    clock = pygame.time.Clock()
    selection = await run_deck_builder(
        screen,
        unlock_override=True,  # In LAN, always give full pool to both players
        unlock_system=unlock_system,
        toggle_fullscreen_callback=toggle_fullscreen_callback,
        exclude_user_content=True  # CRITICAL: No user content in multiplayer!
    )
    if selection is None:
        session.close()
        return None

    # CRITICAL: Validate deck contains NO user content before sending
    try:
        from user_content_loader import validate_deck_for_multiplayer, filter_out_user_cards
        deck_ids = selection["deck_ids"]
        leader_id = selection["leader"]["id"]
        faction = selection["faction"]

        is_valid, error_msg = validate_deck_for_multiplayer(deck_ids, leader_id, faction)
        if not is_valid:
            print(f"[LAN] ERROR: Deck validation failed!\n{error_msg}")
            # Filter out any user content that slipped through
            deck_ids = filter_out_user_cards(deck_ids)
            selection["deck_ids"] = deck_ids
            print(f"[LAN] Filtered deck to {len(deck_ids)} base game cards")
    except ImportError:
        print("[LAN] Warning: user_content_loader not available, skipping deck validation")

    local_payload = {
        "faction": selection["faction"],
        "leader_id": selection["leader"]["id"],
        "deck_ids": selection["deck_ids"],
    }
    session.send(LanMessageType.DECK_SELECTION.value, local_payload)
    remote_payload = await wait_for_message(session, LanMessageType.DECK_SELECTION.value)
    if not remote_payload:
        session.close()
        return

    # Validate remote deck has no obviously invalid data
    if remote_payload:
        remote_deck_ids = remote_payload.get("deck_ids", [])
        if not remote_deck_ids or not isinstance(remote_deck_ids, list):
            print("[LAN] Warning: Remote player sent invalid deck data")
        elif len(remote_deck_ids) < 10:
            print(f"[LAN] Warning: Remote deck suspiciously small ({len(remote_deck_ids)} cards)")

    if role == "host":
        seed = random.randint(0, 2**32 - 1)
        session.send(LanMessageType.SEED.value, {"seed": seed})
    else:
        payload = await wait_for_message(session, LanMessageType.SEED.value)
        seed = payload.get("seed", 0)
    local_leader = find_leader(local_payload["faction"], local_payload["leader_id"])
    remote_leader = find_leader(remote_payload["faction"], remote_payload["leader_id"])
    
    await show_leader_matchup(screen, local_leader, remote_leader)
    context = LanContext(
        session=session,
        role=role,
        local=LanDeckSelection(local_payload["faction"], local_payload["leader_id"], local_payload["deck_ids"]),
        remote=LanDeckSelection(remote_payload["faction"], remote_payload["leader_id"], remote_payload["deck_ids"]),
        seed=seed,
    )

    return context


async def show_leader_matchup(screen, local_leader, remote_leader):
    animation = LeaderMatchupAnimation(local_leader, remote_leader, screen.get_width(), screen.get_height())
    clock = pygame.time.Clock()
    while not animation.finished:
        dt = clock.tick(60)
        await asyncio.sleep(0)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                animation.finished = True
            elif event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_SPACE):
                animation.finished = True
        animation.update(dt)
        animation.draw(screen)
        display_manager.gpu_flip()


async def run_lan_match(screen, context: LanContext):
    """
    Run a LAN multiplayer match.

    This imports the main game loop and runs it with NetworkController
    instead of AIController, enabling networked multiplayer.
    """
    # Import main game module - we'll call into it with LAN mode enabled
    import main as game_main
    from lan_opponent import NetworkController, NetworkPlayerProxy

    # Set LAN mode flag and context on main module
    game_main.LAN_MODE = True
    game_main.LAN_CONTEXT = context

    # Run the main game (it will detect LAN_MODE and use NetworkController)
    try:
        await game_main.run_game_with_context(screen, context)
    finally:
        # Clean up
        game_main.LAN_MODE = False
        game_main.LAN_CONTEXT = None
        context.session.close()


async def run_lan_chat_scene(screen, session: LanSession, role: str):
    clock = pygame.time.Clock()
    running = True
    info_font = pygame.font.SysFont("Arial", 28)
    title = f"LAN Chat ({'Host' if role == 'host' else 'Client'})"
    panel_rect = pygame.Rect(40, 100, screen.get_width() - 80, screen.get_height() - 200)
    chat_panel = LanChatPanel(session, role, max_lines=18)
    chat_panel.add_message("System", "Type a message and press Enter. ESC to return.")
    
    while running:
        screen.fill((15, 20, 35))
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
            chat_panel.handle_event(event)
        
        chat_panel.poll_session()
        title_surf = info_font.render(title, True, (200, 200, 200))
        screen.blit(title_surf, (40, 40))
        chat_panel.draw(screen, panel_rect, title=None)
        
        display_manager.gpu_flip()
        clock.tick(60)
        await asyncio.sleep(0)

    session.close()
