"""
STARGWENT - SPACE SHOOTER EASTER EGG
A Vampire Survivors-inspired arcade mini-game.
Unlocked after achieving 8 wins in Draft Mode.

Controls:
- WASD or Arrow keys: Move ship (all directions, auto-fire)
- Q: Wormhole escape
- ESC: Exit to main menu

Scoring:
- Enemy destroyed: 100 pts
- Boss defeated: 1000 pts (Wave 5 final enemy)
- Wave clear bonus: 500 pts
- No damage bonus: 200 pts (per wave, if took no damage)
- Asteroid destroyed: 50 pts
"""

import pygame
import random

from .game import SpaceShooterGame
from .ship_select import ShipSelectScreen


def run_space_shooter(screen, player_faction=None, ai_faction=None):
    """
    Run the space shooter mini-game.

    Args:
        screen: Pygame display surface
        player_faction: Player's faction name (if None, show selection screen)
        ai_faction: AI's faction name (if None, pick random)

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
            pygame.display.flip()

    # Pick random AI faction (different from player)
    if ai_faction is None:
        factions = ["Tau'ri", "Goa'uld", "Asgard", "Jaffa Rebellion", "Lucian Alliance"]
        ai_faction = random.choice([f for f in factions if f != player_faction])

    session_scores = []
    game = SpaceShooterGame(screen_width, screen_height, player_faction, ai_faction,
                            session_scores=session_scores)

    while game.running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                game.exit_to_menu = True
                game.running = False
            else:
                game.handle_event(event)

        game.update()
        game.draw(screen)

        pygame.display.flip()
        clock.tick(60)

    if game.exit_to_menu:
        return None

    return game.winner == "player"
