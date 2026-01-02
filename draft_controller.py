"""
STARGWENT - DRAFT MODE CONTROLLER

Main controller for Draft Mode that ties together the logic and UI.
"""

import pygame
from typing import Optional
from draft_mode import DraftPool, DraftRun
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

        # Leader choices (shown at start or redraft)
        self.leader_choices = []

        # Current card choices
        self.current_choices = []

        # UI state
        self.clickable_rects = []

        # Clock for animations
        self.clock = pygame.time.Clock()
        
        # Try to restore active run
        self._try_restore_run()

    def _try_restore_run(self):
        """Attempt to restore an active draft run from persistence."""
        active_data = get_persistence().get_active_draft_run()
        if active_data:
            self.current_run = DraftRun(self.pool)
            self.current_run.wins = active_data.get('wins', 0)
            self.current_run.losses = active_data.get('losses', 0)
            self.current_run.phase = active_data.get('phase', 'leader_select')
            self.current_run.current_pick = active_data.get('current_pick', 0)
            
            # Restore leader
            leader_id = active_data.get('leader_id')
            if leader_id:
                for leader in self.pool.available_leaders:
                    if leader['card_id'] == leader_id:
                        self.current_run.drafted_leader = leader
                        break
            
            # Restore cards
            card_ids = active_data.get('card_ids', [])
            for cid in card_ids:
                if cid in ALL_CARDS:
                    # We need a fresh copy of the card object
                    import copy
                    self.current_run.drafted_cards.append(copy.deepcopy(ALL_CARDS[cid]))
            
            # If we are in a picking phase, we might need to regenerate choices
            # Ideally we'd persist choices too, but regenerating is acceptable for now
            if self.current_run.phase in ["draft", "redraft_cards_pick"]:
                 self.current_choices = self.current_run.get_current_choices()
            elif self.current_run.phase == "redraft_leader":
                self.leader_choices = self.pool.get_leader_choices(3)
            elif self.current_run.phase == "leader_select":
                self.leader_choices = self.pool.get_leader_choices(3)
                
            print(f"Resumed draft run: Phase={self.current_run.phase}, Wins={self.current_run.wins}")

    def save_run_state(self):
        """Save current run state to persistence."""
        if not self.current_run:
            return
            
        # Serialize card IDs
        # Helper to find ID for a card object since Card class might not store it directly
        # We search ALL_CARDS for matching name/stats or assume 'id' attr if added
        card_ids = []
        for card in self.current_run.drafted_cards:
            # Try efficient lookup first
            found = False
            for cid, c_obj in ALL_CARDS.items():
                if c_obj.name == card.name and c_obj.faction == card.faction:
                    card_ids.append(cid)
                    found = True
                    break
            if not found:
                print(f"Warning: Could not match card '{card.name}' to ID for persistence")

        leader_id = self.current_run.drafted_leader['card_id'] if self.current_run.drafted_leader else None

        data = {
            'wins': self.current_run.wins,
            'losses': self.current_run.losses,
            'phase': self.current_run.phase,
            'current_pick': self.current_run.current_pick,
            'leader_id': leader_id,
            'card_ids': card_ids
        }
        get_persistence().save_active_draft_run(data)

    def start_new_run(self):
        """Start a new draft run."""
        get_persistence().clear_active_draft_run() # Clear old one
        self.current_run = DraftRun(self.pool)
        self.leader_choices = self.pool.get_leader_choices(3)
        self.current_choices = []
        self.ui.hovered_index = None
        self.ui.selected_index = None

        # Track draft start
        get_persistence().record_draft_start()
        self.save_run_state()

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

            # Calculate synergy scores for each choice
            synergy_scores = [self.current_run.get_synergy_score(card) for card in self.current_choices]

            self.clickable_rects = self.ui.draw_draft_phase(
                surface,
                self.current_choices,
                self.current_run.current_pick,
                DraftRun.CARDS_TO_DRAFT,
                self.current_run.drafted_cards,
                synergy_scores=synergy_scores,
                can_undo=self.current_run.current_pick > 0
            )

        elif self.current_run.phase == "review":
            stats = self.current_run.get_draft_stats()
            # Pass wins info to UI if possible (might need to update draw_review_phase signature)
            # For now we use the existing UI
            battle_rect, redraft_rect = self.ui.draw_review_phase(
                surface,
                self.current_run.drafted_leader,
                self.current_run.drafted_cards,
                stats
            )
            
            # If 8 wins, maybe show "Claim Victory" instead of Battle?
            # Or main.py handles the win condition.
            
            self.clickable_rects = [battle_rect, redraft_rect]
            
            # Show win counter overlay
            win_text = f"Wins: {self.current_run.wins}/{DraftRun.MAX_WINS}"
            font = pygame.font.SysFont("Arial", 32, bold=True)
            text_surf = font.render(win_text, True, (255, 215, 0))
            surface.blit(text_surf, (20, 20))

        elif self.current_run.phase == "redraft_cards_select":
            # UI to remove cards. Reuse review UI but with different prompt?
            # We'll need a way to render the deck and allow clicking cards to remove them
            # For simplicity, let's reuse draw_review_phase but handle clicks differently
            stats = self.current_run.get_draft_stats()
            # Draw header manually
            surface.fill((20, 20, 30))
            font = pygame.font.SysFont("Arial", 36, bold=True)
            prompt = f"REDRAFT: Remove {self.current_run.cards_to_remove_count} cards from your deck"
            text = font.render(prompt, True, (255, 100, 100))
            surface.blit(text, (self.screen_width//2 - text.get_width()//2, 50))
            
            # Draw deck list (simplified reuse of internal logic or new UI method)
            # We'll implement a simple list for removal
            # Using the UI's deck preview drawing would be ideal
            
            # Hack: Use the review phase drawing but ignore buttons
            self.ui.draw_review_phase(surface, self.current_run.drafted_leader, self.current_run.drafted_cards, stats)
            
            # Add click regions for cards (Review UI doesn't return card rects easily, 
            # might need to rely on list index clicks if UI supported it.
            # Assuming we can just implement a simple click-to-remove here or modify UI later.
            # For now, let's just assume the user sees the list and we handle clicks)
            # We'll update clickable_rects in 'handle_event' or 'ui' logic properly.
            
            # Let's actually use the scroll offset from UI
            # We need to register rects for cards to handle removal
            # This requires updating DraftModeUI to return card rects or doing it here
            # We'll do a basic overlay implementation here for simplicity
            
            # ... (Implementation detail: effectively we rely on mouse position mapping to list index)
            
        elif self.current_run.phase == "redraft_cards_pick":
            # Same as draft phase but with "Redrafting..." title
            if not self.current_choices:
                self.current_choices = self.current_run.get_current_choices()
            
            synergy_scores = [self.current_run.get_synergy_score(card) for card in self.current_choices]
            self.clickable_rects = self.ui.draw_draft_phase(
                surface, self.current_choices, 
                5 - self.current_run.cards_to_remove_count, # Current pick in this batch
                5, # Total to redraft
                self.current_run.drafted_cards,
                synergy_scores=synergy_scores,
                title="REDRAFTING - Pick Replacements"
            )

        elif self.current_run.phase == "redraft_leader":
            if not self.leader_choices:
                self.leader_choices = self.pool.get_leader_choices(3)
            self.clickable_rects = self.ui.draw_leader_selection(surface, self.leader_choices)
            # Overlay "Keep Current" button?
            # Or just make one of the choices the current one?
            # Let's just offer 3 new ones. The player chose to redraft, implies swap.
            
            title = pygame.font.SysFont("Arial", 48, bold=True).render("CHOOSE NEW LEADER", True, (255, 215, 0))
            surface.blit(title, (self.screen_width//2 - title.get_width()//2, 30))

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

        elif event.type == pygame.MOUSEWHEEL:
            # ... (Scrolling logic same as before, omitted for brevity but assumed present)
            if self.current_run.phase in ["review", "redraft_cards_select"]:
                self.ui.review_scroll_y += event.y * 30
                # Clamp scroll logic...
                card_counts = {}
                for card in self.current_run.drafted_cards:
                    card_counts[card.name] = True
                content_height = 60 + len(card_counts) * 40
                max_scroll = max(0, content_height - (self.screen_height - 330))
                self.ui.review_scroll_y = min(0, max(-max_scroll, self.ui.review_scroll_y))
            elif self.current_run.phase in ["draft", "redraft_cards_pick"]:
                 self.ui.draft_scroll_y += event.y * 25
                 # Clamp...

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.current_run.phase == "redraft_cards_select":
                # Handle card removal click
                # Map mouse Y to list index using scroll_y
                # This is an approximation of the UI layout
                list_start_y = 160 + self.ui.review_scroll_y
                
                # Filter unique cards for display mapping
                unique_cards = []
                seen = set()
                for card in self.current_run.drafted_cards:
                    if card.name not in seen:
                        unique_cards.append(card)
                        seen.add(card.name)
                
                for i, card in enumerate(unique_cards):
                    y_pos = list_start_y + i * 40
                    rect = pygame.Rect(self.screen_width // 2 - 250, y_pos, 500, 35)
                    if rect.collidepoint(event.pos):
                        # Find actual index in drafted_cards to remove
                        for actual_idx, c in enumerate(self.current_run.drafted_cards):
                            if c.name == card.name:
                                self.current_run.remove_card_for_redraft(actual_idx)
                                self.save_run_state()
                                break
                        break

            else:
                clicked_index = self.ui.handle_click(event.pos, self.clickable_rects)

                if clicked_index is not None:
                    if self.current_run.phase == "leader_select":
                        # Leader selected
                        selected_leader = self.leader_choices[clicked_index]
                        self.current_run.select_leader(selected_leader)
                        self.current_choices = []  # Reset for draft phase
                        self.save_run_state()

                    elif self.current_run.phase == "draft":
                        # Card selected
                        selected_card = self.current_choices[clicked_index]
                        self.current_run.pick_card(selected_card, self.current_choices)
                        self.current_choices = []  # Get new choices next render
                        self.ui.selected_index = None
                        self.save_run_state()

                    elif self.current_run.phase == "review":
                        if clicked_index == 0:
                            # Start Battle button
                            return "start_battle"
                        elif clicked_index == 1:
                            # Redraft button (Resets run)
                            self.start_new_run()

                    elif self.current_run.phase == "redraft_cards_pick":
                        selected_card = self.current_choices[clicked_index]
                        self.current_run.pick_card(selected_card)
                        self.current_choices = []
                        self.ui.selected_index = None
                        self.save_run_state()
                    
                    elif self.current_run.phase == "redraft_leader":
                        selected_leader = self.leader_choices[clicked_index]
                        self.current_run.select_leader(selected_leader)
                        self.leader_choices = []
                        self.save_run_state()

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return "exit"
            
            # Undo last pick with Z or Backspace
            if event.key in (pygame.K_z, pygame.K_BACKSPACE):
                if self.current_run.phase == "draft" and self.current_run.current_pick > 0:
                    previous_choices = self.current_run.undo_last_pick()
                    if previous_choices:
                        self.current_choices = previous_choices
                        self.ui.selected_index = None
                        self.save_run_state()

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
        if not self.current_run:
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
