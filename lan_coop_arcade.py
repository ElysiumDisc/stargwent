"""
LAN Co-op Arcade Flow

Top-level orchestration for LAN co-op space shooter:
  1. Each player picks their ship faction locally
  2. Exchange faction choices via ss_ready messages
  3. Host creates CoopSpaceShooterGame, client creates CoopSpaceShooterClient
  4. Game loop → Game over → combined stats → return
"""

import pygame
import display_manager

from space_shooter import run_coop_space_shooter
from space_shooter.ship_select import ShipSelectScreen
from space_shooter.coop_protocol import CoopMsg, build_ready


def run_lan_coop_arcade(screen, session, role):
    """
    Run the LAN co-op arcade flow.

    Args:
        screen: Pygame display surface
        session: Active LanSession connection
        role: "host" or "client"

    Returns:
        None
    """
    clock = pygame.time.Clock()
    screen_width = screen.get_width()
    screen_height = screen.get_height()

    # --- Phase 1: Ship Selection ---
    local_faction = _select_faction(screen, clock, screen_width, screen_height)
    if local_faction is None:
        return None  # User pressed ESC

    # --- Phase 2: Exchange faction choices ---
    session.send(CoopMsg.READY, {"faction": local_faction})

    # Wait for partner's faction choice
    remote_faction = None
    font = pygame.font.SysFont("Arial", 36, bold=True)
    small_font = pygame.font.SysFont("Arial", 24)
    waiting = True

    while waiting:
        clock.tick(60)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return None

        # Poll for partner's ready message
        msg = session.receive()
        while msg:
            if msg.get("type") == CoopMsg.READY:
                remote_faction = msg["payload"]["faction"]
                waiting = False
                break
            msg = session.receive()

        if not session.is_connected():
            return None

        # Draw waiting screen
        screen.fill((10, 10, 25))
        title = font.render("CO-OP ARCADE", True, (100, 255, 100))
        screen.blit(title, title.get_rect(center=(screen_width // 2, screen_height // 2 - 80)))

        your_text = small_font.render(f"Your ship: {local_faction}", True, (200, 200, 200))
        screen.blit(your_text, your_text.get_rect(center=(screen_width // 2, screen_height // 2 - 20)))

        if remote_faction:
            partner_text = small_font.render(f"Partner: {remote_faction}", True, (200, 200, 200))
        else:
            dots = "." * (int(pygame.time.get_ticks() / 500) % 4)
            partner_text = small_font.render(f"Waiting for partner{dots}", True, (150, 150, 200))
        screen.blit(partner_text, partner_text.get_rect(center=(screen_width // 2, screen_height // 2 + 20)))

        display_manager.gpu_flip()

    # Brief "LAUNCHING" screen
    screen.fill((10, 10, 25))
    launch = font.render("LAUNCHING CO-OP ARCADE!", True, (255, 215, 0))
    screen.blit(launch, launch.get_rect(center=(screen_width // 2, screen_height // 2)))
    info = small_font.render(f"{local_faction}  +  {remote_faction}", True, (200, 200, 200))
    screen.blit(info, info.get_rect(center=(screen_width // 2, screen_height // 2 + 50)))
    display_manager.gpu_flip()
    pygame.time.wait(1000)

    # --- Phase 3: Start game ---
    if role == "host":
        # Host is P1, client is P2
        return run_coop_space_shooter(screen, session, role,
                                       p1_faction=local_faction,
                                       p2_faction=remote_faction)
    else:
        # Client is P2, host is P1
        return run_coop_space_shooter(screen, session, role,
                                       p1_faction=remote_faction,
                                       p2_faction=local_faction)


def _select_faction(screen, clock, screen_width, screen_height):
    """Show ship selection screen and return chosen faction or None."""
    select_screen = ShipSelectScreen(screen_width, screen_height)

    while True:
        clock.tick(60)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            result = select_screen.handle_event(event)
            if result == "exit":
                return None
            elif result:
                return result

        select_screen.draw(screen)
        display_manager.gpu_flip()
