"""
STARGWENT - SPACE SHOOTER EASTER EGG
A Vampire Survivors-inspired infinite survival mini-game.
Unlocked after achieving 8 wins in Draft Mode.

Controls:
- WASD or Arrow keys: Move ship (all directions, auto-fire)
- Q: Wormhole escape
- ESC: Exit to main menu

Scoring:
- Enemy destroyed: 100 pts
- Boss defeated: 1000 pts
- Asteroid destroyed: 50 pts
- Kill streak bonus: streak * 25 pts
- Survival time: 10 pts per second
"""

import pygame
import random
import os
import display_manager

from .game import SpaceShooterGame
from .ship_select import ShipSelectScreen

_MUSIC_PATH = os.path.join("assets", "audio", "space_shooter", "space_shooter.ogg")


def _start_space_music():
    """Start the space shooter background music loop."""
    if not os.path.exists(_MUSIC_PATH):
        print("[audio] Space shooter music file missing:", _MUSIC_PATH)
        return
    if not pygame.mixer.get_init():
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
        except pygame.error as exc:
            print(f"[audio] Mixer init failed: {exc}")
            return
    try:
        from game_settings import get_settings
        volume = get_settings().get_effective_music_volume()
        pygame.mixer.music.load(_MUSIC_PATH)
        pygame.mixer.music.set_volume(volume)
        pygame.mixer.music.play(-1)
        print(f"[audio] Space shooter music playing at volume {volume:.2f}")
    except Exception as exc:
        print(f"[audio] Unable to start space shooter music: {exc}")


def _stop_space_music(fade_ms=800):
    """Fade out and stop space shooter music."""
    if not pygame.mixer.get_init():
        return
    try:
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.fadeout(fade_ms)
    except pygame.error:
        try:
            pygame.mixer.music.stop()
        except pygame.error:
            pass


def run_space_shooter(screen, player_faction=None, ai_faction=None,
                      mission_type=None, mission_target=None, starting_upgrades=None):
    """
    Run the space shooter mini-game.

    Args:
        screen: Pygame display surface
        player_faction: Player's faction name (if None, show selection screen)
        ai_faction: AI's faction name (if None, pick random)
        mission_type: Optional "eliminate" for kill-count missions (None = infinite survival)
        mission_target: Kill count to win (e.g. 4 for planet defense)
        starting_upgrades: Optional dict of upgrade_name → stacks (roguelite carry-over)

    Returns:
        True if player won, False if AI won, None if exited early
    """
    clock = pygame.time.Clock()
    screen_width = screen.get_width()
    screen_height = screen.get_height()

    # Show ship selection if no faction provided
    if player_faction is None:
        select_screen = ShipSelectScreen(screen_width, screen_height)
        selecting = True

        while selecting:
            clock.tick(60)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return None

                result = select_screen.handle_event(event)
                if result == "exit":
                    return None
                elif result:
                    player_faction = result
                    selecting = False

            select_screen.draw(screen)
            display_manager.gpu_flip()

    # Pick random AI faction (different from player)
    if ai_faction is None:
        factions = ["Tau'ri", "Goa'uld", "Asgard", "Jaffa Rebellion", "Lucian Alliance"]
        ai_faction = random.choice([f for f in factions if f != player_faction])

    # Stop any existing music (e.g. main menu) and start space shooter music
    try:
        if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
            pygame.mixer.music.fadeout(400)
            pygame.time.wait(400)
    except pygame.error:
        pass
    _start_space_music()

    session_scores = []
    game = SpaceShooterGame(screen_width, screen_height, player_faction, ai_faction,
                            session_scores=session_scores,
                            mission_type=mission_type, mission_target=mission_target,
                            starting_upgrades=starting_upgrades)

    while game.running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                game.exit_to_menu = True
                game.running = False
            else:
                game.handle_event(event)

        game.update()
        game.draw(screen)

        display_manager.gpu_flip()
        clock.tick(60)

    # Stop space shooter music when leaving
    _stop_space_music()

    if game.exit_to_menu:
        return None

    # Mission mode — return based on objective completion
    if mission_type == "eliminate" and getattr(game, 'mission_complete', False):
        return True

    # Survival mode — always ends in death, but return based on performance
    return game.survival_seconds > 120  # "Won" if survived >2 minutes


def run_coop_space_shooter(screen, session, role, p1_faction=None, p2_faction=None):
    """
    Run co-op space shooter over LAN.

    Args:
        screen: Pygame display surface
        session: Active LanSession connection
        role: "host" or "client"
        p1_faction: Host player's faction
        p2_faction: Client player's faction

    Returns:
        True if survived >2 minutes, None if exited early
    """
    from .coop_protocol import CoopMsg, build_input, build_state
    from .coop_game import CoopSpaceShooterGame
    from .coop_client import CoopSpaceShooterClient

    clock = pygame.time.Clock()
    screen_width = screen.get_width()
    screen_height = screen.get_height()

    # Stop existing music and start space shooter music
    try:
        if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
            pygame.mixer.music.fadeout(400)
            pygame.time.wait(400)
    except pygame.error:
        pass
    _start_space_music()

    if role == "host":
        # Host runs full simulation
        game = CoopSpaceShooterGame(screen_width, screen_height,
                                     p1_faction, p2_faction)
        snapshot_counter = 0

        while game.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    game.exit_to_menu = True
                    game.running = False
                else:
                    game.handle_event(event)

            # Poll network for client input
            msg = session.receive()
            while msg:
                mtype = msg.get("type")
                if mtype == CoopMsg.INPUT:
                    game.apply_partner_input(msg.get("payload", {}))
                elif mtype == CoopMsg.ACTION:
                    payload = msg.get("payload", {})
                    action = payload.get("action")
                    if action == "secondary":
                        game.fire_partner_secondary()
                elif mtype == CoopMsg.DISCONNECT:
                    # Client disconnected gracefully — continue as solo
                    game.p2_alive = False
                    game.p2_ghost = False
                msg = session.receive()

            # Check for partner disconnect (no input for 5 seconds)
            if hasattr(session, 'is_connected') and not session.is_connected():
                if game.p2_alive:
                    game.p2_alive = False
                    game.p2_ghost = False

            game.update()
            game.draw(screen)

            # Send state snapshot every 3 frames (20 Hz)
            snapshot_counter += 1
            if snapshot_counter >= 3:
                snapshot_counter = 0
                snapshot = game.get_state_snapshot()
                session.send(CoopMsg.STATE, snapshot)

            display_manager.gpu_flip()
            clock.tick(60)

        # Send game over to client
        session.send(CoopMsg.GAME_OVER, {
            'score': game.score,
            'survival_frames': game.survival_frames,
            'enemies_defeated': game.enemies_defeated,
        })

        _stop_space_music()
        return None if game.exit_to_menu else game.survival_seconds > 120

    else:
        # Client — render only
        client = CoopSpaceShooterClient(screen_width, screen_height,
                                         session, p2_faction, p1_faction)

        while client.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    client.exit_to_menu = True
                    client.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        client.exit_to_menu = True
                        client.running = False

            # Send input to host every frame
            input_state = client.get_input_state()
            try:
                session.send(CoopMsg.INPUT, input_state)
            except Exception:
                client.host_disconnected = True

            # Send secondary fire action on E press
            keys = pygame.key.get_pressed()
            if keys[pygame.K_e] and not getattr(client, '_e_was_pressed', False):
                try:
                    from .coop_protocol import build_action
                    session.send(CoopMsg.ACTION, {"action": "secondary", "data": {}})
                except Exception:
                    pass
            client._e_was_pressed = keys[pygame.K_e]

            # Receive state snapshots
            msg = session.receive()
            while msg:
                mtype = msg.get("type")
                if mtype == CoopMsg.STATE:
                    client.apply_state(msg.get("payload", {}))
                elif mtype == CoopMsg.GAME_OVER:
                    client.game_over = True
                    client.apply_state(msg.get("payload", {}))
                elif mtype == CoopMsg.DISCONNECT:
                    client.host_disconnected = True
                msg = session.receive()

            # Check connection health
            if hasattr(session, 'is_connected') and not session.is_connected():
                client.host_disconnected = True

            client.update()
            client.draw(screen)

            # Host disconnected — show message and wait for ESC
            if client.host_disconnected:
                pass  # draw() handles the disconnect overlay

            if client.game_over:
                pass  # Stay on game over screen until ESC

            display_manager.gpu_flip()
            clock.tick(60)

        # Send disconnect notification to host
        try:
            from .coop_protocol import build_disconnect
            session.send(CoopMsg.DISCONNECT, {"reason": "client_exit"})
        except Exception:
            pass

        _stop_space_music()
        return None
