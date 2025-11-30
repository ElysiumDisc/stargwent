"""
STARGWENT - DRAFT MODE CONTROLLER

Main controller for Draft Mode that ties together the logic and UI.
"""

import pygame
from typing import Optional
from draft_mode import DraftPool, DraftRun, calculate_draft_rewards
from draft_mode_ui import DraftModeUI
from unlocks import CardUnlockSystem
from cards import ALL_CARDS
from deck_persistence import get_persistence


class DraftModeController:
    """Controls the flow of Draft Mode."""

    def __init__(self, screen_width: int, screen_height: int, unlock_manager: CardUnlockSystem):
        """
        Initialize Draft Mode Controller.

        Args:
            screen_width: Screen width in pixels
            screen_height: Screen height in pixels
            unlock_manager: CardUnlockSystem instance for checking unlocks
        """
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.unlock_manager = unlock_manager

        # Initialize UI
        self.ui = DraftModeUI(screen_width, screen_height)

        # Get unlocked content
        unlocked_cards = list(unlock_manager.unlocked_cards)
        unlocked_leaders = list(unlock_manager.unlocked_leaders)

        # Ensure all default content is available even if not unlocked
        # (for testing and to ensure draft pool is large enough)
        if len(unlocked_cards) < 50:
            unlocked_cards = list(ALL_CARDS.keys())

        # Create draft pool
        self.pool = DraftPool(unlocked_cards, unlocked_leaders)

        # Current draft run
        self.current_run: Optional[DraftRun] = None

        # Leader choices (shown at start)
        self.leader_choices = []

        # Current card choices
        self.current_choices = []

        # UI state
        self.clickable_rects = []

        # Clock for animations
        self.clock = pygame.time.Clock()

    def start_new_run(self):
        """Start a new draft run."""
        self.current_run = DraftRun(self.pool)
        self.leader_choices = self.pool.get_leader_choices(3)
        self.current_choices = []
        self.ui.hovered_index = None
        self.ui.selected_index = None

        # Track draft start
        get_persistence().record_draft_start()

    def render(self, surface: pygame.Surface):
        """
        Render the current draft state.

        Args:
            surface: Pygame surface to draw on
        """
        if not self.current_run:
            self.start_new_run()

        if self.current_run.phase == "leader_select":
            self.clickable_rects = self.ui.draw_leader_selection(surface, self.leader_choices)

        elif self.current_run.phase == "draft":
            # Get new choices if needed
            if not self.current_choices:
                self.current_choices = self.current_run.get_current_choices()

            self.clickable_rects = self.ui.draw_draft_phase(
                surface,
                self.current_choices,
                self.current_run.current_pick,
                DraftRun.CARDS_TO_DRAFT,
                self.current_run.drafted_cards
            )

        elif self.current_run.phase == "review":
            stats = self.current_run.get_draft_stats()
            battle_rect, redraft_rect = self.ui.draw_review_phase(
                surface,
                self.current_run.drafted_leader,
                self.current_run.drafted_cards,
                stats
            )
            self.clickable_rects = [battle_rect, redraft_rect]

    def handle_event(self, event: pygame.event.Event) -> Optional[str]:
        """
        Handle pygame events.

        Args:
            event: Pygame event

        Returns:
            Action string: "start_battle", "exit", or None
        """
        if not self.current_run:
            return None

        if event.type == pygame.MOUSEMOTION:
            self.ui.handle_mouse_motion(event.pos, self.clickable_rects)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            clicked_index = self.ui.handle_click(event.pos, self.clickable_rects)

            if clicked_index is not None:
                if self.current_run.phase == "leader_select":
                    # Leader selected
                    selected_leader = self.leader_choices[clicked_index]
                    self.current_run.select_leader(selected_leader)
                    self.current_choices = []  # Reset for draft phase

                elif self.current_run.phase == "draft":
                    # Card selected
                    selected_card = self.current_choices[clicked_index]
                    self.current_run.pick_card(selected_card)
                    self.current_choices = []  # Get new choices next render
                    self.ui.selected_index = None

                elif self.current_run.phase == "review":
                    if clicked_index == 0:
                        # Start Battle button
                        return "start_battle"
                    elif clicked_index == 1:
                        # Redraft button
                        self.start_new_run()

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return "exit"

        return None

    def get_drafted_deck(self) -> Optional[dict]:
        """
        Get the completed drafted deck.

        Returns:
            Deck dictionary, or None if draft not complete
        """
        if not self.current_run or self.current_run.phase != "review":
            return None

        return self.current_run.get_deck_dict()

    def run_draft_loop(self, screen: pygame.Surface) -> Optional[dict]:
        """
        Run the draft mode main loop.

        Args:
            screen: Pygame screen surface

        Returns:
            Drafted deck dictionary if completed, None if exited
        """
        self.start_new_run()
        running = True

        while running:
            self.clock.tick(60)  # 60 FPS

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return None

                action = self.handle_event(event)

                if action == "start_battle":
                    # Draft complete, return deck
                    return self.get_drafted_deck()
                elif action == "exit":
                    return None

            # Render
            self.render(screen)
            pygame.display.flip()

        return None


def launch_draft_mode(screen: pygame.Surface, unlock_manager: CardUnlockSystem) -> Optional[dict]:
    """
    Launch Draft Mode and return the drafted deck.

    Args:
        screen: Pygame screen surface
        unlock_manager: CardUnlockSystem instance

    Returns:
        Drafted deck dictionary if completed, None if exited
    """
    screen_width, screen_height = screen.get_size()
    controller = DraftModeController(screen_width, screen_height, unlock_manager)
    return controller.run_draft_loop(screen)
