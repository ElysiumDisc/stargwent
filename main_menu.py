"""
Main Menu System for Stargwent
Includes main menu, deck customization, and deck management.
Also includes Stargate opening animation (merged from stargate_opening.py).
"""
import pygame
import json
import os
import math
import random
from deck_persistence import get_persistence
from cards import ALL_CARDS, FACTION_TAURI, FACTION_GOAULD, FACTION_JAFFA, FACTION_LUCIAN, FACTION_ASGARD, FACTION_NEUTRAL, reload_card_images
from deck_builder import FACTION_LEADERS, MIN_DECK_SIZE, MAX_DECK_SIZE, validate_deck
from unlocks import CardUnlockSystem, UNLOCKABLE_CARDS
from rules_menu import run_rules_menu
from lan_menu import run_lan_menu
from stats_menu import run_stats_menu
from dhd_button import DHDButtonManager
import board_renderer

# Save file for custom decks
CUSTOM_DECKS_FILE = "player_decks.json"
MENU_MUSIC_PATH = os.path.join("assets", "audio", "main_menu_music.ogg")
STARGATE_SEQUENCE_PATH = os.path.join("assets", "audio", "stargate_sequence.ogg")
STARGATE_SEQUENCE_DURATION_MS = 16000  # Match the 16s audio clip
_menu_music_playing = False
_menu_music_next_allowed = 0
_MENU_LOOP_DELAY_MS = 0  # No delay - restart immediately
_stargate_sequence_sound = None
_stargate_sequence_sound_loaded = False
_STARGATE_SEQUENCE_VOLUME = 0.85


def _ensure_mixer():
    """Initialize the mixer once before trying to play anything."""
    if pygame.mixer.get_init():
        return True
    try:
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
        return True
    except pygame.error as exc:
        print(f"[audio] Mixer init failed, menu music disabled: {exc}")
        return False


def start_menu_music(immediate=False):
    """Kick off the main menu track if allowed."""
    from game_settings import get_settings
    global _menu_music_playing, _menu_music_next_allowed
    if _menu_music_playing:
        return
    if not os.path.exists(MENU_MUSIC_PATH):
        print("[audio] Menu music file missing:", MENU_MUSIC_PATH)
        return
    now = pygame.time.get_ticks()
    if not immediate and now < _menu_music_next_allowed:
        return
    if not _ensure_mixer():
        return
    try:
        settings = get_settings()
        volume = settings.get_effective_music_volume()
        pygame.mixer.music.load(MENU_MUSIC_PATH)
        pygame.mixer.music.set_volume(volume)
        pygame.mixer.music.play(-1)  # Loop infinitely
        _menu_music_playing = True
        print(f"[audio] Main menu music playing from {MENU_MUSIC_PATH} at volume {volume:.2f}")
    except pygame.error as exc:
        print(f"[audio] Unable to start menu music: {exc}")


def update_menu_music():
    """Restart menu track every 30s after it finishes."""
    global _menu_music_playing, _menu_music_next_allowed
    if not os.path.exists(MENU_MUSIC_PATH):
        return
    if not pygame.mixer.get_init():
        return
    if _menu_music_playing and not pygame.mixer.music.get_busy():
        _menu_music_playing = False
        _menu_music_next_allowed = pygame.time.get_ticks() + _MENU_LOOP_DELAY_MS
    if not _menu_music_playing:
        start_menu_music()


def stop_menu_music(fade_ms=600):
    """Stop the menu track."""
    global _menu_music_playing, _menu_music_next_allowed
    if not _menu_music_playing:
        return
    if not pygame.mixer.get_init():
        _menu_music_playing = False
        _menu_music_next_allowed = 0
        return
    try:
        pygame.mixer.music.fadeout(fade_ms)
    except pygame.error:
        pygame.mixer.music.stop()
    _menu_music_playing = False
    _menu_music_next_allowed = 0


def _get_stargate_sequence_sound():
    """Load and cache the Stargate sequence clip."""
    global _stargate_sequence_sound, _stargate_sequence_sound_loaded
    if _stargate_sequence_sound_loaded:
        return _stargate_sequence_sound
    _stargate_sequence_sound_loaded = True
    if not os.path.exists(STARGATE_SEQUENCE_PATH):
        print("[audio] Missing Stargate sequence clip:", STARGATE_SEQUENCE_PATH)
        return None
    if not _ensure_mixer():
        return None
    try:
        sound = pygame.mixer.Sound(STARGATE_SEQUENCE_PATH)
        _stargate_sequence_sound = sound
        print(f"[audio] Stargate sequence loaded from {STARGATE_SEQUENCE_PATH}")
    except pygame.error as exc:
        print(f"[audio] Unable to load Stargate sequence audio: {exc}")
        _stargate_sequence_sound = None
    return _stargate_sequence_sound


class DeckManager:
    """Manages custom deck configurations for each faction."""
    
    def __init__(self, unlock_system):
        self.unlock_system = unlock_system
        self.custom_decks = {}
        self.load_decks()
    
    def load_decks(self):
        """Load saved custom decks from file."""
        if os.path.exists(CUSTOM_DECKS_FILE):
            try:
                with open(CUSTOM_DECKS_FILE, 'r') as f:
                    self.custom_decks = json.load(f)
            except:
                self.custom_decks = {}
        else:
            self.custom_decks = {}
    
    def save_decks(self):
        """Save custom decks to file."""
        with open(CUSTOM_DECKS_FILE, 'w') as f:
            json.dump(self.custom_decks, f, indent=2)
    
    def get_deck(self, faction):
        """Get custom deck for faction, or None if using default."""
        return self.custom_decks.get(faction, None)
    
    def set_deck(self, faction, card_ids):
        """Set custom deck for faction."""
        if card_ids is None:
            if faction in self.custom_decks:
                self.custom_decks.pop(faction, None)
            print(f"✗ Custom deck cleared for {faction}, reverting to defaults")
        else:
            self.custom_decks[faction] = card_ids
            print(f"✓ Custom deck saved for {faction}: {len(card_ids)} cards")
        self.save_decks()
    
    def get_available_cards_for_faction(self, faction):
        """Get all cards available for a faction (base + unlocked + neutral)."""
        available = []
        
        # Faction cards
        for card_id, card in ALL_CARDS.items():
            if card.faction == faction:
                available.append({'id': card_id, 'card': card, 'source': 'faction'})
        
        # Neutral cards
        for card_id, card in ALL_CARDS.items():
            if card.faction == FACTION_NEUTRAL:
                available.append({'id': card_id, 'card': card, 'source': 'neutral'})
        
        # Unlocked cards (that match faction or are neutral)
        if hasattr(self.unlock_system, "is_unlock_override_enabled") and self.unlock_system.is_unlock_override_enabled():
            unlocked_ids = UNLOCKABLE_CARDS.keys()
        else:
            unlocked_ids = self.unlock_system.unlocked_cards
        for card_id in unlocked_ids:
            card_data = UNLOCKABLE_CARDS.get(card_id)
            if not card_data:
                continue
            if card_data['faction'] == faction or card_data['faction'] == 'Neutral':
                available.append({'id': card_id, 'card': None, 'data': card_data, 'source': 'unlocked'})
        
        return available


class MainMenu:

    screen_surface = None
    """Main menu screen."""
    
    def __init__(self, screen_width, screen_height, unlock_system):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.selected_option = 0
        self.unlock_system = unlock_system
        self.unlock_option_index = -1
        
        # Load background
        self.background = None
        self.load_background()
        
        # Calculate scaling factor based on screen size (baseline: 1080p)
        self.scale_factor = min(screen_height / 1080.0, screen_width / 1920.0)
        
        # Fonts - Scale based on screen size
        title_size = max(60, int(140 * self.scale_factor))
        subtitle_size = max(20, int(32 * self.scale_factor))
        button_size = max(18, int(36 * self.scale_factor))
        
        try:
            self.title_font = pygame.font.Font(None, title_size)
        except:
            self.title_font = pygame.font.SysFont("Impact, Arial Black, Arial", title_size, bold=True)
        
        try:
            self.subtitle_font = pygame.font.SysFont("Courier New, Consolas, Monospace", subtitle_size)
        except:
            self.subtitle_font = pygame.font.SysFont("Arial", subtitle_size)
        
        try:
            self.button_font = pygame.font.SysFont("Impact, Arial Black, Arial", button_size, bold=True)
        except:
            self.button_font = pygame.font.SysFont("Arial", button_size, bold=True)
        
        # Colors
        self.bg_color = (10, 15, 30)
        self.button_color = (40, 60, 100)
        self.button_hover_color = (60, 90, 150)
        self.button_selected_color = (80, 120, 180)
        self.text_color = (255, 255, 255)
        self.highlight_color = (100, 200, 255)  # Stargate blue
        
        # Menu options
        self.options = [
            {'text': 'NEW GAME', 'action': 'new_game'},
            {'text': 'DRAFT MODE', 'action': 'draft_mode'},
            {'text': 'DECK BUILDING', 'action': 'deck_building'},
            {'text': 'MULTIPLAYER', 'action': 'lan_menu'},
            {'text': 'RULE MENU', 'action': 'rules_menu'},
            {'text': 'STATS', 'action': 'stats_menu'},
            {'text': 'OPTIONS', 'action': 'options_menu'},
            {'text': 'QUIT', 'action': 'quit'}
        ]
        self.unlock_option_index = -1
        
        # Initialize DHD button system
        self.dhd_manager = DHDButtonManager()
        
        self.setup_buttons()

    def _unlock_override_state(self) -> bool:
        if self.unlock_system and hasattr(self.unlock_system, "is_unlock_override_enabled"):
            return self.unlock_system.is_unlock_override_enabled()
        return False

    def _update_unlock_option_label(self):
        if self.unlock_option_index < 0:
            return
        state = "ON" if self._unlock_override_state() else "OFF"
        self.options[self.unlock_option_index]['text'] = f"UNLOCK ALL (SP): {state}"

    def toggle_unlock_override(self):
        if not self.unlock_system:
            return
        if hasattr(self.unlock_system, "toggle_unlock_override"):
            self.unlock_system.toggle_unlock_override()
        elif hasattr(self.unlock_system, "set_unlock_override"):
            self.unlock_system.set_unlock_override(not self._unlock_override_state())
        self._update_unlock_option_label()
    
    def run_options_menu(self, surface):
        from game_settings import get_settings
        import os

        # Try to load options menu background
        options_bg = None
        options_bg_path = os.path.join("assets", "options_menu_bg.png")
        if os.path.exists(options_bg_path):
            try:
                options_bg = pygame.image.load(options_bg_path).convert()
                options_bg = pygame.transform.scale(options_bg, (self.screen_width, self.screen_height))
            except Exception as e:
                print(f"Warning: Could not load options background: {e}")
                options_bg = None

        overlay = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        clock = pygame.time.Clock()
        running = True
        center_x = self.screen_width // 2
        center_y = self.screen_height // 2
        
        # Scale factor for responsive layout
        scale = min(self.screen_height / 1080.0, self.screen_width / 1920.0)

        settings = get_settings()

        # Slider state
        dragging_slider = False

        # Panel geometry - responsive sizing
        panel_width = int(800 * scale)
        panel_height = int(750 * scale)
        panel_top = center_y - panel_height // 2

        # Fonts - scaled
        title_font = pygame.font.SysFont("Arial", max(36, int(52 * scale)), bold=True)
        label_font = pygame.font.SysFont("Arial", max(22, int(30 * scale)), bold=True)
        status_font = pygame.font.SysFont("Arial", max(18, int(24 * scale)), bold=True)
        instruction_font = pygame.font.SysFont("Arial", max(16, int(22 * scale)))

        # Back button - top left of panel
        back_rect = pygame.Rect(
            center_x - panel_width // 2 + int(20 * scale),
            panel_top + int(15 * scale),
            int(140 * scale),
            int(45 * scale)
        )

        # Volume slider
        slider_y = panel_top + int(140 * scale)
        slider_width = int(500 * scale)
        slider_height = int(50 * scale)
        slider_rect = pygame.Rect(center_x - slider_width // 2, slider_y, slider_width, slider_height)
        slider_track_height = int(10 * scale)
        slider_handle_radius = int(18 * scale)

        # Stargate toggle geometry
        gate_radius = int(60 * scale)
        gate_rect = pygame.Rect(0, 0, gate_radius * 2, gate_radius * 2)

        # Fullscreen toggle
        fullscreen_y = slider_y + int(200 * scale)
        gate_rect.center = (center_x, fullscreen_y)

        # Unlock toggle
        unlock_gate_radius = int(60 * scale)
        unlock_gate_rect = pygame.Rect(0, 0, unlock_gate_radius * 2, unlock_gate_radius * 2)
        unlock_y = fullscreen_y + int(220 * scale)
        unlock_gate_rect.center = (center_x, unlock_y)

        # FPS toggle
        fps_gate_radius = int(60 * scale)
        fps_gate_rect = pygame.Rect(0, 0, fps_gate_radius * 2, fps_gate_radius * 2)
        # Position FPS toggle to the right of Unlock toggle
        fps_y = unlock_y
        fps_x = center_x + int(250 * scale)
        # Shift Unlock toggle to the left
        unlock_gate_rect.center = (center_x - int(250 * scale), unlock_y)
        fps_gate_rect.center = (fps_x, fps_y)

        def draw_stargate_toggle(active, rect, pulse_phase=0):
            """Draw a Stargate-style toggle with animation."""
            gate_surf = pygame.Surface(rect.size, pygame.SRCALPHA)
            radius = rect.width // 2
            center = (radius, radius)
            
            # Outer ring with gradient effect
            pygame.draw.circle(gate_surf, (70, 75, 90), center, radius)
            pygame.draw.circle(gate_surf, (50, 55, 65), center, radius - 4)
            pygame.draw.circle(gate_surf, (90, 100, 120), center, radius, 3)
            
            # Chevrons (9) with glow when active
            for i in range(9):
                angle = (i / 9) * 2 * math.pi - math.pi / 2
                cx = radius + int(math.cos(angle) * (radius - 8))
                cy = radius + int(math.sin(angle) * (radius - 8))
                
                if active:
                    # Glowing orange chevron
                    glow_intensity = 0.7 + 0.3 * math.sin(pulse_phase + i * 0.5)
                    glow_color = (int(255 * glow_intensity), int(120 * glow_intensity), 0)
                    pygame.draw.circle(gate_surf, glow_color, (cx, cy), 7)
                    pygame.draw.circle(gate_surf, (255, 180, 50), (cx, cy), 4)
                else:
                    # Dim chevron
                    pygame.draw.circle(gate_surf, (80, 50, 50), (cx, cy), 6)
                    pygame.draw.circle(gate_surf, (50, 35, 35), (cx, cy), 4)
            
            # Event horizon
            if active:
                # Animated watery blue effect
                pulse = 0.8 + 0.2 * math.sin(pulse_phase * 2)
                pygame.draw.circle(gate_surf, (0, int(80 * pulse), int(180 * pulse)), center, radius - 14)
                pygame.draw.circle(gate_surf, (int(80 * pulse), int(180 * pulse), 255), center, radius - 22)
                # Ripple rings
                for r_offset in range(3):
                    ring_r = radius - 30 - r_offset * 12
                    if ring_r > 5:
                        alpha = int(100 - r_offset * 30)
                        ring_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
                        pygame.draw.circle(ring_surf, (150, 220, 255, alpha), center, ring_r, 2)
                        gate_surf.blit(ring_surf, (0, 0))
            else:
                # Closed iris
                pygame.draw.circle(gate_surf, (20, 25, 35), center, radius - 14)
                # Iris pattern (X)
                iris_size = radius - 20
                pygame.draw.line(gate_surf, (50, 55, 70), 
                               (center[0] - iris_size // 2, center[1] - iris_size // 2),
                               (center[0] + iris_size // 2, center[1] + iris_size // 2), 3)
                pygame.draw.line(gate_surf, (50, 55, 70), 
                               (center[0] + iris_size // 2, center[1] - iris_size // 2),
                               (center[0] - iris_size // 2, center[1] + iris_size // 2), 3)
                # Iris border
                pygame.draw.circle(gate_surf, (60, 65, 80), center, radius - 14, 2)
                
            return gate_surf

        def get_slider_handle_pos():
            volume = settings.get_master_volume()
            return slider_rect.x + int(volume * slider_width)

        def set_volume_from_pos(x):
            rel_x = x - slider_rect.x
            volume = max(0.0, min(1.0, rel_x / slider_width))
            settings.set_master_volume(volume)

        pulse_phase = 0
        
        while running:
            dt = clock.tick(60)
            pulse_phase += dt * 0.005  # Animate toggles
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return 'quit'
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_ESCAPE, pygame.K_RETURN):
                        running = False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if back_rect.collidepoint(event.pos):
                        running = False
                        continue

                    handle_x = get_slider_handle_pos()
                    handle_rect = pygame.Rect(
                        handle_x - slider_handle_radius,
                        slider_rect.centery - slider_handle_radius,
                        slider_handle_radius * 2,
                        slider_handle_radius * 2
                    )
                    if handle_rect.collidepoint(event.pos) or slider_rect.collidepoint(event.pos):
                        dragging_slider = True
                        set_volume_from_pos(event.pos[0])
                    elif unlock_gate_rect.collidepoint(event.pos):
                        self.toggle_unlock_override()
                    elif fps_gate_rect.collidepoint(event.pos):
                        settings.set_show_fps(not settings.get_show_fps())
                    elif gate_rect.collidepoint(event.pos):
                        import display_manager
                        display_manager.toggle_fullscreen_mode()
                        # Update surface reference after toggle
                        surface = display_manager.screen
                        
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    dragging_slider = False
                elif event.type == pygame.MOUSEMOTION:
                    if dragging_slider:
                        set_volume_from_pos(event.pos[0])

            # Draw background
            if options_bg:
                surface.blit(options_bg, (0, 0))
            else:
                surface.fill((15, 20, 35))
            
            # Semi-transparent overlay for readability
            surface.blit(overlay, (0, 0))

            # Draw main panel with nice styling
            panel_rect = pygame.Rect(
                center_x - panel_width // 2,
                panel_top,
                panel_width,
                panel_height
            )
            
            # Panel background with gradient effect
            panel_surf = pygame.Surface((panel_rect.width, panel_rect.height), pygame.SRCALPHA)
            for y in range(panel_rect.height):
                progress = y / panel_rect.height
                alpha = int(200 - progress * 30)
                r = int(25 + progress * 10)
                g = int(35 + progress * 15)
                b = int(55 + progress * 20)
                pygame.draw.line(panel_surf, (r, g, b, alpha), (0, y), (panel_rect.width, y))
            
            surface.blit(panel_surf, panel_rect.topleft)
            
            # Panel border with glow
            pygame.draw.rect(surface, (60, 140, 220), panel_rect, width=3, border_radius=16)
            # Inner glow line
            inner_rect = panel_rect.inflate(-6, -6)
            pygame.draw.rect(surface, (40, 100, 180, 100), inner_rect, width=1, border_radius=14)

            # Title
            title_surface = title_font.render("OPTIONS", True, (100, 200, 255))
            title_rect = title_surface.get_rect(center=(center_x, panel_top + int(60 * scale)))
            # Title glow
            glow_surf = title_font.render("OPTIONS", True, (50, 150, 255))
            surface.blit(glow_surf, (title_rect.x + 2, title_rect.y + 2))
            surface.blit(title_surface, title_rect)

            # Back button (DHD style - top left)
            back_rect = board_renderer.draw_dhd_back_button(surface, 20, 20, 80)

            # === VOLUME SECTION ===
            volume_label = label_font.render("Master Volume", True, (220, 230, 255))
            volume_label_rect = volume_label.get_rect(center=(center_x, slider_y - int(35 * scale)))
            surface.blit(volume_label, volume_label_rect)

            # Slider track background
            track_rect = pygame.Rect(
                slider_rect.x,
                slider_rect.centery - slider_track_height // 2,
                slider_width,
                slider_track_height
            )
            pygame.draw.rect(surface, (50, 60, 80), track_rect, border_radius=5)

            # Slider filled portion with gradient
            volume = settings.get_master_volume()
            filled_width = int(volume * slider_width)
            if filled_width > 0:
                filled_rect = pygame.Rect(
                    slider_rect.x,
                    slider_rect.centery - slider_track_height // 2,
                    filled_width,
                    slider_track_height
                )
                # Gradient fill
                for x in range(filled_width):
                    progress = x / max(1, slider_width)
                    color = (int(60 + progress * 40), int(140 + progress * 60), int(200 + progress * 55))
                    pygame.draw.line(surface, color, 
                                   (slider_rect.x + x, filled_rect.y),
                                   (slider_rect.x + x, filled_rect.y + slider_track_height))

            # Slider handle
            handle_x = get_slider_handle_pos()
            handle_center = (handle_x, slider_rect.centery)
            pygame.draw.circle(surface, (255, 255, 255), handle_center, slider_handle_radius)
            pygame.draw.circle(surface, (80, 180, 255), handle_center, slider_handle_radius - 4)
            pygame.draw.circle(surface, (150, 220, 255), handle_center, slider_handle_radius - 8)

            # Volume percentage
            volume_pct = int(volume * 100)
            volume_text = status_font.render(f"{volume_pct}%", True, (180, 200, 220))
            volume_text_rect = volume_text.get_rect(center=(center_x, slider_y + int(45 * scale)))
            surface.blit(volume_text, volume_text_rect)

            # === FULLSCREEN SECTION ===
            fs_label = label_font.render("Fullscreen Mode", True, (220, 230, 255))
            fs_label_rect = fs_label.get_rect(center=(center_x, fullscreen_y - gate_radius - int(30 * scale)))
            surface.blit(fs_label, fs_label_rect)

            # Fullscreen Stargate Toggle
            is_fullscreen = (surface.get_flags() & pygame.FULLSCREEN) != 0
            gate_surface = draw_stargate_toggle(is_fullscreen, gate_rect, pulse_phase)
            surface.blit(gate_surface, gate_rect.topleft)

            # Fullscreen status
            fs_state_text = "ACTIVE" if is_fullscreen else "WINDOWED"
            fs_state_color = (100, 255, 120) if is_fullscreen else (180, 180, 190)
            fs_status = status_font.render(fs_state_text, True, fs_state_color)
            fs_status_rect = fs_status.get_rect(center=(center_x, fullscreen_y + gate_radius + int(25 * scale)))
            surface.blit(fs_status, fs_status_rect)

            # === UNLOCK SECTION ===
            unlock_label = label_font.render("Unlock All Content", True, (220, 230, 255))
            unlock_label_rect = unlock_label.get_rect(center=(unlock_gate_rect.centerx, unlock_y - unlock_gate_radius - int(30 * scale)))
            surface.blit(unlock_label, unlock_label_rect)

            # Unlock Stargate toggle
            unlock_surface = draw_stargate_toggle(self._unlock_override_state(), unlock_gate_rect, pulse_phase)
            surface.blit(unlock_surface, unlock_gate_rect.topleft)

            # Unlock status
            state_text = "UNLOCKED" if self._unlock_override_state() else "PROGRESSION"
            state_color = (100, 255, 120) if self._unlock_override_state() else (180, 180, 190)
            status_surface = status_font.render(state_text, True, state_color)
            status_rect = status_surface.get_rect(center=(unlock_gate_rect.centerx, unlock_gate_rect.bottom + int(25 * scale)))
            surface.blit(status_surface, status_rect)

            # === FPS SECTION ===
            fps_label = label_font.render("Show FPS", True, (220, 230, 255))
            fps_label_rect = fps_label.get_rect(center=(fps_gate_rect.centerx, fps_y - fps_gate_radius - int(30 * scale)))
            surface.blit(fps_label, fps_label_rect)

            # FPS Stargate toggle
            fps_surface = draw_stargate_toggle(settings.get_show_fps(), fps_gate_rect, pulse_phase)
            surface.blit(fps_surface, fps_gate_rect.topleft)

            # FPS status
            fps_state_text = "VISIBLE" if settings.get_show_fps() else "HIDDEN"
            fps_state_color = (100, 255, 120) if settings.get_show_fps() else (180, 180, 190)
            fps_status_surface = status_font.render(fps_state_text, True, fps_state_color)
            fps_status_rect = fps_status_surface.get_rect(center=(fps_gate_rect.centerx, fps_gate_rect.bottom + int(25 * scale)))
            surface.blit(fps_status_surface, fps_status_rect)

            # Instructions at bottom
            hint_text = "Click Stargates to toggle  |  Drag slider to adjust volume"
            hint_surface = instruction_font.render(hint_text, True, (140, 160, 180))
            hint_rect = hint_surface.get_rect(center=(center_x, panel_top + panel_height - int(50 * scale)))
            surface.blit(hint_surface, hint_rect)
            
            esc_text = "Press ESC or ENTER to return"
            esc_surface = instruction_font.render(esc_text, True, (120, 140, 160))
            esc_rect = esc_surface.get_rect(center=(center_x, panel_top + panel_height - int(25 * scale)))
            surface.blit(esc_surface, esc_rect)

            pygame.display.flip()
        return None
    def load_background(self):
        """Load menu background image."""
        try:
            self.background = pygame.image.load("assets/menu_background.png").convert()
            # Scale to screen size if needed
            if self.background.get_size() != (self.screen_width, self.screen_height):
                self.background = pygame.transform.scale(self.background, (self.screen_width, self.screen_height))
        except:
            self.background = None
    
    def setup_buttons(self):
        """Setup menu button positions with proper scaling for all resolutions."""
        num_options = len(self.options)
        
        # Scale button dimensions based on screen size (use height as reference)
        # Design baseline: 1080p (1920x1080)
        scale_factor = min(self.screen_height / 1080.0, self.screen_width / 1920.0)
        
        button_width = int(400 * scale_factor)
        button_height = int(70 * scale_factor)
        spacing = int(15 * scale_factor)
        
        # Calculate total menu height
        total_menu_height = num_options * button_height + (num_options - 1) * spacing
        
        # Ensure buttons fit in available space (leave room for title and bottom margin)
        title_space = int(self.screen_height * 0.25)  # Reserve 25% for title area
        bottom_margin = int(self.screen_height * 0.05)  # 5% bottom margin
        available_height = self.screen_height - title_space - bottom_margin
        
        # If buttons don't fit, shrink them
        if total_menu_height > available_height:
            # Calculate maximum button height that fits
            max_button_height = (available_height - (num_options - 1) * spacing) // num_options
            button_height = max(30, min(button_height, max_button_height))
            spacing = max(5, int(spacing * 0.6))  # Reduce spacing proportionally
            total_menu_height = num_options * button_height + (num_options - 1) * spacing
        
        # Center buttons horizontally
        start_x = (self.screen_width - button_width) // 2
        
        # Start buttons below title area, centered in remaining space
        start_y = title_space + (available_height - total_menu_height) // 2
        
        # Clear existing DHD buttons
        self.dhd_manager.buttons.clear()
        
        for i, option in enumerate(self.options):
            y = start_y + i * (button_height + spacing)
            option['rect'] = pygame.Rect(start_x, y, button_width, button_height)
            option['hovered'] = False
            
            # Add DHD button
            self.dhd_manager.add_button(i, option['rect'], option['text'], self.button_font)
    
    def handle_event(self, event):
        """Handle input events."""
        if event.type == pygame.MOUSEMOTION:
            mouse_pos = event.pos
            for i, option in enumerate(self.options):
                option['hovered'] = option['rect'].collidepoint(mouse_pos)
                if option['hovered']:
                    self.selected_option = i
        
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = event.pos
            for i, option in enumerate(self.options):
                if option['rect'].collidepoint(mouse_pos):
                    # Trigger DHD activation effect
                    self.dhd_manager.activate_button(i)
                    
                    if option['action'] == 'options_menu':
                        screen_surface = pygame.display.get_surface()
                        result = self.run_options_menu(screen_surface)
                        if isinstance(result, str):
                            return result
                    else:
                        return option['action']
        
        elif event.type == pygame.KEYDOWN:
            if event.key in [pygame.K_UP, pygame.K_w]:
                self.selected_option = (self.selected_option - 1) % len(self.options)
            elif event.key in [pygame.K_DOWN, pygame.K_s]:
                self.selected_option = (self.selected_option + 1) % len(self.options)
            elif event.key == pygame.K_RETURN:
                # Trigger DHD activation effect
                self.dhd_manager.activate_button(self.selected_option)
                
                action = self.options[self.selected_option]['action']
                if action == 'options_menu':
                    result = self.run_options_menu(surface)
                    if isinstance(result, str):
                        return result
                else:
                    return action
            elif event.key == pygame.K_ESCAPE:
                return 'quit'
        
        return None
    
    def draw(self, surface):
        """Draw the main menu."""
        # Apply screen shake offset if active
        shake_offset = self.dhd_manager.get_shake_offset()
        
        # Create a temporary surface if shake is active
        if shake_offset != (0, 0):
            temp_surface = pygame.Surface((self.screen_width, self.screen_height))
            draw_target = temp_surface
        else:
            draw_target = surface
        
        # Draw background
        if self.background:
            draw_target.blit(self.background, (0, 0))
        else:
            draw_target.fill(self.bg_color)
        
        # IMPRESSIVE TITLE with multiple effects - scale position based on screen
        title_y = int(self.screen_height * 0.12)  # 12% from top
        
        # Create gradient effect - draw multiple layers
        title_text = "STARGWENT"
        
        # Shadow layers (black, offset) - scale shadow offset
        shadow_scale = max(1, int(4 * self.scale_factor))
        for offset in range(shadow_scale * 2, 0, -shadow_scale // 2 or 1):
            shadow = self.title_font.render(title_text, True, (0, 0, 0))
            shadow_rect = shadow.get_rect(center=(self.screen_width // 2 + offset, title_y + offset))
            draw_target.blit(shadow, shadow_rect)
        
        # Outer glow (blue/cyan)
        glow_height = int(200 * self.scale_factor)
        glow_surf = pygame.Surface((self.screen_width, glow_height), pygame.SRCALPHA)
        for i in range(6, 0, -1):
            glow_color = (*self.highlight_color, 30)
            glow_text = self.title_font.render(title_text, True, glow_color)
            glow_rect = glow_text.get_rect(center=(self.screen_width // 2 + i, glow_height // 2 + i))
            glow_surf.blit(glow_text, glow_rect)
        draw_target.blit(glow_surf, (0, title_y - glow_height // 2))
        
        # Inner glow (brighter)
        inner_glow_color = (255, 255, 200, 80)
        inner_glow = self.title_font.render(title_text, True, inner_glow_color)
        inner_rect = inner_glow.get_rect(center=(self.screen_width // 2, title_y))
        draw_target.blit(inner_glow, inner_rect)
        
        # Main title (gold/yellow)
        main_title = self.title_font.render(title_text, True, self.highlight_color)
        main_rect = main_title.get_rect(center=(self.screen_width // 2, title_y))
        draw_target.blit(main_title, main_rect)
        
        # Highlight edge (white)
        highlight = self.title_font.render(title_text, True, (255, 255, 255))
        highlight_rect = highlight.get_rect(center=(self.screen_width // 2 - 2, title_y - 2))
        highlight.set_alpha(150)
        draw_target.blit(highlight, highlight_rect)
        
        # Draw DHD buttons with enhanced effects
        self.dhd_manager.draw(draw_target, self.selected_option)
        
        # Blit temp surface with shake offset if active
        if shake_offset != (0, 0):
            surface.blit(temp_surface, shake_offset)


class DeckCustomizationUI:
    """UI for customizing decks for each faction."""
    
    def __init__(self, screen_width, screen_height, deck_manager):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.deck_manager = deck_manager
        self.selected_faction = FACTION_TAURI
        self.current_deck = []
        self.available_cards = []
        self.scroll_offset = 0
        self.deck_scroll_offset = 0
        self.selected_card = None
        
        # Load deck building background
        self.deck_building_bg = None
        self.load_deck_building_bg()
        
        # Fonts
        self.title_font = pygame.font.SysFont("Arial", 48, bold=True)
        self.subtitle_font = pygame.font.SysFont("Arial", 28)
        self.small_font = pygame.font.SysFont("Arial", 20)
        
        # Colors
        self.bg_color = (15, 15, 25)
        self.text_color = (255, 255, 255)
        self.highlight_color = (255, 215, 0)
        
        # Faction tabs
        self.faction_tabs = [
            FACTION_TAURI, FACTION_GOAULD, FACTION_JAFFA, 
            FACTION_LUCIAN, FACTION_ASGARD
        ]
        
        self.setup_ui()
        self.load_faction_deck(self.selected_faction)
    
    def load_deck_building_bg(self):
        """Load deck building background image."""
        import os
        bg_path = os.path.join("assets", "deck_building_bg.png")
        
        if os.path.exists(bg_path):
            try:
                bg_image = pygame.image.load(bg_path).convert()
                self.deck_building_bg = pygame.transform.scale(bg_image, (self.screen_width, self.screen_height))
                print("✓ Loaded deck_building_bg.png for deck customization")
            except Exception as e:
                print(f"Warning: Could not load {bg_path}: {e}")
                self.deck_building_bg = None
        else:
            self.deck_building_bg = None
    
    def setup_ui(self):
        """Setup UI elements."""
        # Faction tabs at top
        self.tab_rects = []
        tab_width = 250
        tab_height = 50
        spacing = 10
        total_width = len(self.faction_tabs) * tab_width + (len(self.faction_tabs) - 1) * spacing
        start_x = (self.screen_width - total_width) // 2
        
        for i, faction in enumerate(self.faction_tabs):
            x = start_x + i * (tab_width + spacing)
            rect = pygame.Rect(x, 10, tab_width, tab_height)
            self.tab_rects.append({'faction': faction, 'rect': rect})
        
        # Back button (DHD style - top left)
        self.back_button = pygame.Rect(20, 20, 80, 104)
        
        # Save button
        self.save_button = pygame.Rect(self.screen_width - 170, self.screen_height - 70, 150, 50)
        
        # Reset to default button
        self.reset_button = pygame.Rect(self.screen_width - 350, self.screen_height - 70, 170, 50)
    
    def load_faction_deck(self, faction):
        """Load deck for selected faction."""
        self.selected_faction = faction
        
        # Load custom deck or create default
        saved_deck = self.deck_manager.get_deck(faction)
        if saved_deck:
            # Load saved deck
            self.current_deck = saved_deck[:]
        else:
            # Create default deck from faction cards (limited to 40 max)
            import random
            self.current_deck = []
            faction_card_ids = [card_id for card_id, card in ALL_CARDS.items() if card.faction == faction]
            
            # If faction has more than 35 cards, randomly select 35 to leave room for neutrals
            if len(faction_card_ids) > 35:
                faction_card_ids = random.sample(faction_card_ids, 35)
            
            self.current_deck.extend(faction_card_ids)
            
            # Add some neutrals (up to 5, but respect 40 card limit)
            neutral_card_ids = [card_id for card_id, card in ALL_CARDS.items() if card.faction == FACTION_NEUTRAL]
            neutral_count = min(5, 40 - len(self.current_deck))
            if neutral_card_ids and neutral_count > 0:
                selected_neutrals = random.sample(neutral_card_ids, min(neutral_count, len(neutral_card_ids)))
                self.current_deck.extend(selected_neutrals)
            
            # Ensure we don't exceed 40 cards
            if len(self.current_deck) > 40:
                self.current_deck = self.current_deck[:40]
        
        # Load available cards
        self.available_cards = self.deck_manager.get_available_cards_for_faction(faction)
        self.scroll_offset = 0
        self.deck_scroll_offset = 0
    
    def handle_event(self, event):
        """Handle input events."""
        if event.type == pygame.MOUSEMOTION:
            # Update hover states if needed
            pass
        
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button in [4, 5]:  # Mouse wheel
                # Scroll available cards area
                if event.button == 4:
                    self.scroll_offset = max(0, self.scroll_offset - 50)
                else:
                    self.scroll_offset += 50
                return None
            
            mouse_pos = event.pos
            
            # Check faction tabs
            for tab in self.tab_rects:
                if tab['rect'].collidepoint(mouse_pos):
                    self.load_faction_deck(tab['faction'])
                    return None
            
            # Check back button
            if self.back_button.collidepoint(mouse_pos):
                return 'back'
            
            # Check save button
            if self.save_button.collidepoint(mouse_pos):
                is_valid, message = validate_deck(self.get_deck_cards())
                if is_valid:
                    self.deck_manager.set_deck(self.selected_faction, self.current_deck)
                    return 'back'
                else:
                    print(f"Cannot save: {message}")
                return None
            
            # Check reset button
            if self.reset_button.collidepoint(mouse_pos):
                self.current_deck = []
                self.deck_manager.set_deck(self.selected_faction, None)
                self.load_faction_deck(self.selected_faction)
                return None
            
            # Check card clicks (add/remove from deck)
            # Available cards area (left side)
            card_area_rect = pygame.Rect(20, 120, self.screen_width // 2 - 40, self.screen_height - 220)
            if card_area_rect.collidepoint(mouse_pos):
                self.handle_available_card_click(mouse_pos)
            
            # Current deck area (right side)
            deck_area_rect = pygame.Rect(self.screen_width // 2 + 20, 120, self.screen_width // 2 - 40, self.screen_height - 220)
            if deck_area_rect.collidepoint(mouse_pos):
                self.handle_deck_card_click(mouse_pos)
        
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return 'back'
        
        return None
    
    def handle_available_card_click(self, mouse_pos):
        """Handle click on available cards."""
        card_width = 100
        card_height = 150
        cards_per_row = 4
        spacing = 15
        start_x = 30
        start_y = 150 - self.scroll_offset
        
        for i, card_info in enumerate(self.available_cards):
            row = i // cards_per_row
            col = i % cards_per_row
            x = start_x + col * (card_width + spacing)
            y = start_y + row * (card_height + spacing)
            card_rect = pygame.Rect(x, y, card_width, card_height)
            
            if card_rect.collidepoint(mouse_pos):
                # Add card to deck if not at max
                if len(self.current_deck) < MAX_DECK_SIZE:
                    self.current_deck.append(card_info['id'])
                break
    
    def handle_deck_card_click(self, mouse_pos):
        """Handle click on deck cards (remove)."""
        card_width = 100
        card_height = 150
        cards_per_row = 4
        spacing = 15
        start_x = self.screen_width // 2 + 30
        start_y = 150 - self.deck_scroll_offset
        
        for i, card_id in enumerate(self.current_deck):
            row = i // cards_per_row
            col = i % cards_per_row
            x = start_x + col * (card_width + spacing)
            y = start_y + row * (card_height + spacing)
            card_rect = pygame.Rect(x, y, card_width, card_height)
            
            if card_rect.collidepoint(mouse_pos):
                # Remove card from deck
                self.current_deck.pop(i)
                break
    
    def get_deck_cards(self):
        """Convert deck IDs to Card objects for validation."""
        deck_cards = []
        for card_id in self.current_deck:
            if card_id in ALL_CARDS:
                deck_cards.append(ALL_CARDS[card_id])
        return deck_cards
    
    def draw(self, surface):
        """Draw the deck customization UI."""
        # Use deck building background if available
        if self.deck_building_bg:
            surface.blit(self.deck_building_bg, (0, 0))
        else:
            surface.fill(self.bg_color)
        
        # Title
        title = self.title_font.render("DECK CUSTOMIZATION", True, self.highlight_color)
        surface.blit(title, (self.screen_width // 2 - title.get_width() // 2, 70))
        
        # Faction tabs
        for tab in self.tab_rects:
            is_selected = (tab['faction'] == self.selected_faction)
            color = (80, 120, 180) if is_selected else (40, 60, 100)
            pygame.draw.rect(surface, color, tab['rect'], border_radius=5)
            if is_selected:
                pygame.draw.rect(surface, self.highlight_color, tab['rect'], width=3, border_radius=5)
            
            text = self.subtitle_font.render(tab['faction'], True, self.text_color)
            text_rect = text.get_rect(center=tab['rect'].center)
            surface.blit(text, text_rect)
        
        # Draw available cards (left) and current deck (right)
        self.draw_available_cards(surface)
        self.draw_current_deck(surface)
        
        # Buttons - DHD back button
        self.back_button = board_renderer.draw_dhd_back_button(surface, 20, 20, 80)
        
        pygame.draw.rect(surface, (50, 150, 50), self.save_button, border_radius=5)
        save_text = self.subtitle_font.render("SAVE", True, self.text_color)
        surface.blit(save_text, (self.save_button.centerx - save_text.get_width() // 2, self.save_button.centery - save_text.get_height() // 2))
        
        pygame.draw.rect(surface, (150, 50, 50), self.reset_button, border_radius=5)
        reset_text = self.small_font.render("RESET DEFAULT", True, self.text_color)
        surface.blit(reset_text, (self.reset_button.centerx - reset_text.get_width() // 2, self.reset_button.centery - reset_text.get_height() // 2))
    
    def draw_available_cards(self, surface):
        """Draw available cards pool."""
        header = self.subtitle_font.render("Available Cards (Click to Add)", True, self.text_color)
        surface.blit(header, (30, 125))
        
        # Draw card grid (simplified - showing card names)
        card_width = 100
        card_height = 150
        cards_per_row = 4
        spacing = 15
        start_x = 30
        start_y = 150 - self.scroll_offset
        
        for i, card_info in enumerate(self.available_cards):
            row = i // cards_per_row
            col = i % cards_per_row
            x = start_x + col * (card_width + spacing)
            y = start_y + row * (card_height + spacing)
            
            # Only draw if visible
            if y + card_height < 120 or y > self.screen_height - 100:
                continue
            
            # Draw card placeholder
            pygame.draw.rect(surface, (60, 60, 80), (x, y, card_width, card_height), border_radius=5)
            pygame.draw.rect(surface, (100, 100, 120), (x, y, card_width, card_height), width=2, border_radius=5)
            
            # Draw card name (truncated)
            if card_info['card']:
                name = card_info['card'].name[:12]
            else:
                name = card_info['data']['name'][:12]
            
            name_text = self.small_font.render(name, True, self.text_color)
            surface.blit(name_text, (x + 5, y + 5))
    
    def draw_current_deck(self, surface):
        """Draw current deck."""
        deck_cards = self.get_deck_cards()
        is_valid, message = validate_deck(deck_cards)
        
        color = (100, 255, 100) if is_valid else (255, 100, 100)
        header = self.subtitle_font.render(f"Current Deck: {len(self.current_deck)}/{MIN_DECK_SIZE}-{MAX_DECK_SIZE}", True, color)
        surface.blit(header, (self.screen_width // 2 + 30, 125))
        
        if not is_valid:
            error_text = self.small_font.render(message, True, (255, 100, 100))
            surface.blit(error_text, (self.screen_width // 2 + 30, 155))
        
        # Draw deck grid
        card_width = 100
        card_height = 150
        cards_per_row = 4
        spacing = 15
        start_x = self.screen_width // 2 + 30
        start_y = 180 - self.deck_scroll_offset
        
        for i, card_id in enumerate(self.current_deck):
            row = i // cards_per_row
            col = i % cards_per_row
            x = start_x + col * (card_width + spacing)
            y = start_y + row * (card_height + spacing)
            
            # Only draw if visible
            if y + card_height < 120 or y > self.screen_height - 100:
                continue
            
            # Draw card placeholder
            pygame.draw.rect(surface, (80, 80, 100), (x, y, card_width, card_height), border_radius=5)
            pygame.draw.rect(surface, (150, 150, 170), (x, y, card_width, card_height), width=2, border_radius=5)
            
            # Draw card name
            if card_id in ALL_CARDS:
                name = ALL_CARDS[card_id].name[:12]
            else:
                name = "Unknown"
            
            name_text = self.small_font.render(name, True, self.text_color)
            surface.blit(name_text, (x + 5, y + 5))


def run_main_menu(screen, unlock_system, toggle_fullscreen_callback=None):
    """Run the main menu loop."""
    # CRITICAL: Reload card images at menu start to ensure proper loading
    print("Main Menu: Reloading card images for current screen size...")
    reload_card_images()
    print("Main Menu: Card images loaded!")
    
    deck_manager = DeckManager(unlock_system)
    main_menu = MainMenu(screen.get_width(), screen.get_height(), unlock_system)
    clock = pygame.time.Clock()
    start_menu_music(immediate=True)
    
    running = True
    while running:
        dt = clock.tick(60)
        
        # Update DHD button animations
        mouse_pos = pygame.mouse.get_pos()
        main_menu.dhd_manager.update(dt, mouse_pos, main_menu.selected_option)
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                stop_menu_music()
                return None
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:
                    # Toggle fullscreen using shared callback if available
                    if toggle_fullscreen_callback:
                        toggle_fullscreen_callback()
                        screen = pygame.display.get_surface()
                        main_menu = MainMenu(screen.get_width(), screen.get_height(), unlock_system)
                        main_menu.screen_surface = screen
                    else:
                        import display_manager; display_manager.toggle_fullscreen_mode(); screen = display_manager.screen; main_menu = MainMenu(screen.get_width(), screen.get_height(), unlock_system); main_menu.screen_surface = screen
            
            action = main_menu.handle_event(event)
            if action == 'new_game':
                stop_menu_music()
                return 'new_game'
            elif action == 'draft_mode':
                stop_menu_music()
                return 'draft_mode'
            elif action == 'deck_building':
                # Use the GOOD deck builder from deck_builder.py
                from deck_builder import run_deck_builder
                result = run_deck_builder(
                    screen,
                    for_new_game=False,
                    unlock_override=unlock_system.is_unlock_override_enabled(),
                    unlock_system=unlock_system,
                    toggle_fullscreen_callback=toggle_fullscreen_callback
                )
                deck_manager.load_decks()
                # If result is None, user clicked MAIN MENU or ESC - just continue showing main menu
                # (Don't return None here, that would quit the game!)
            elif action == 'rules_menu':
                run_rules_menu(screen, toggle_fullscreen_callback)
            elif action == 'lan_menu':
                lan_data = run_lan_menu(screen)
                if isinstance(lan_data, dict):
                    stop_menu_music()
                    return lan_data
            elif action == 'stats_menu':
                run_stats_menu(screen)
            elif action == 'toggle_unlock_override':
                main_menu.toggle_unlock_override()
            elif action == 'quit':
                stop_menu_music()
                return None
        
        update_menu_music()
        main_menu.draw(screen)
        pygame.display.flip()
    
    stop_menu_music()
    return None


def run_deck_customization(screen, deck_manager):
    """Run the deck customization UI."""
    deck_ui = DeckCustomizationUI(screen.get_width(), screen.get_height(), deck_manager)
    clock = pygame.time.Clock()
    
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            
            result = deck_ui.handle_event(event)
            if result == 'back':
                return 'back'
        
        deck_ui.draw(screen)
        pygame.display.flip()
        clock.tick(60)
    
    return None


# ===== STARGATE OPENING ANIMATION (MERGED FROM stargate_opening.py) =====

class StargateOpeningAnimation:
    """Dramatic Stargate opening animation."""
    
    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.center_x = screen_width // 2
        self.center_y = screen_height // 2
        self.progress = 0.0
        self.duration = STARGATE_SEQUENCE_DURATION_MS  # 16 seconds to match audio cue
        self.elapsed = 0
        
        # Gate properties
        self.gate_radius = min(screen_width, screen_height) // 3
        self.inner_radius = self.gate_radius - 40
        
        # Chevrons
        self.chevrons = []
        for i in range(9):
            angle = i * 40 - 90  # Start at top
            self.chevrons.append({
                'angle': angle,
                'locked': False,
                'lock_time': 500 + i * 400,  # Stagger locks
                'glow': 0
            })
        
        # Event horizon particles
        self.horizon_particles = []
        for _ in range(100):
            self.horizon_particles.append({
                'angle': random.uniform(0, 360),
                'distance': 0,
                'speed': random.uniform(2, 5),
                'size': random.randint(2, 4),
                'alpha': 0
            })
        
        # Outward vortex particles (KAWOOSH!)
        self.vortex_particles = []
        for _ in range(200):
            self.vortex_particles.append({
                'angle': random.uniform(0, 360),
                'distance': 0,
                'speed': random.uniform(15, 30),  # Fast outward burst
                'size': random.randint(3, 8),
                'alpha': 255,
                'lifetime': random.uniform(0.5, 1.5)  # How long it lives
            })
        
        # Starfield backdrop and glyph engravings for extra fidelity
        self.starfield = [{
            'x': random.randint(0, screen_width),
            'y': random.randint(0, screen_height),
            'speed': random.uniform(0.01, 0.05),
            'phase': random.uniform(0, math.tau),
            'size': random.choice([1, 1, 2])
        } for _ in range(200)]
        self.gate_glyphs = [{
            'angle': i * 10 + random.uniform(-2, 2),
            'width': random.randint(2, 3),
            'length': random.randint(16, 22)
        } for i in range(36)]
        
        self.ripple_phase = 0.0
        self.title_pulse = 0.0
    
    def update(self, dt):
        """Update animation."""
        self.elapsed += dt
        self.progress = min(1.0, self.elapsed / self.duration)
        self.ripple_phase = (self.ripple_phase + dt * 0.003) % (math.tau)
        self.title_pulse = (self.title_pulse + dt * 0.005) % (math.tau)
        
        # Parallax starfield (slow drift + twinkle)
        for star in self.starfield:
            star['phase'] = (star['phase'] + dt * 0.002) % (math.tau)
            star['y'] += star['speed'] * dt * 0.05
            if star['y'] > self.screen_height:
                star['y'] = 0
                star['x'] = random.randint(0, self.screen_width)
    
        # Lock chevrons progressively
        for chevron in self.chevrons:
            if self.elapsed >= chevron['lock_time'] and not chevron['locked']:
                chevron['locked'] = True
                chevron['glow'] = 255
            
            # Fade glow
            if chevron['glow'] > 50:
                chevron['glow'] = max(50, chevron['glow'] - dt * 0.3)
        
        # Update event horizon particles (after chevrons lock)
        if self.progress > 0.5:
            for particle in self.horizon_particles:
                particle['distance'] += particle['speed'] * (dt / 16.0)
                particle['alpha'] = min(255, particle['alpha'] + 5)
                
                # Reset if too far
                if particle['distance'] > self.inner_radius:
                    particle['distance'] = 0
                    particle['angle'] = random.uniform(0, 360)
        
        # Update VORTEX particles (KAWOOSH at 70% progress, lasts longer)
        if self.progress > 0.7:
            for particle in self.vortex_particles:
                particle['distance'] += particle['speed'] * (dt / 16.0)
                particle['lifetime'] -= dt / 1000.0
                particle['alpha'] = max(0, int(255 * particle['lifetime']))
                
                # Reset when dead
                if particle['lifetime'] <= 0:
                    particle['distance'] = 0
                    particle['angle'] = random.uniform(0, 360)
                    particle['lifetime'] = random.uniform(0.5, 1.5)
                    particle['alpha'] = 255
        
        return self.progress < 1.0
    
    def draw(self, surface):
        """Draw the Stargate opening animation."""
        # Deep-space background with subtle nebula
        surface.fill((4, 6, 16))
        nebula = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        pygame.draw.circle(nebula, (20, 60, 140, 90), (self.center_x - 200, self.center_y - 150), self.gate_radius * 2)
        pygame.draw.circle(nebula, (10, 30, 80, 70), (self.center_x + 260, self.center_y + 80), self.gate_radius * 2)
        surface.blit(nebula, (0, 0), special_flags=pygame.BLEND_ADD)
        
        for star in self.starfield:
            brightness = 150 + int(100 * (math.sin(star['phase']) * 0.5 + 0.5))
            color = (brightness, brightness, min(255, brightness + 80))
            pygame.draw.circle(surface, color, (int(star['x']), int(star['y'])), star['size'])
        
        # Gate body (layered metallic gradient)
        gate_surface = pygame.Surface((self.gate_radius * 2 + 80, self.gate_radius * 2 + 80), pygame.SRCALPHA)
        gate_center = gate_surface.get_width() // 2
        for i in range(26):
            radius = self.gate_radius + 30 - i * 2
            shade = 40 + i * 3
            pygame.draw.circle(gate_surface, (shade, shade, shade + 20, 250), (gate_center, gate_center), radius, 2)
        pygame.draw.circle(gate_surface, (30, 30, 45, 255), (gate_center, gate_center), self.inner_radius + 22, 22)
        surface.blit(gate_surface, (self.center_x - gate_center, self.center_y - gate_center))
        
        # Glyph engravings around the ring
        for glyph in self.gate_glyphs:
            angle_rad = math.radians(glyph['angle'])
            outer = (
                self.center_x + math.cos(angle_rad) * (self.gate_radius - 5),
                self.center_y + math.sin(angle_rad) * (self.gate_radius - 5)
            )
            inner = (
                self.center_x + math.cos(angle_rad) * (self.gate_radius - glyph['length']),
                self.center_y + math.sin(angle_rad) * (self.gate_radius - glyph['length'])
            )
            pygame.draw.line(surface, (110, 130, 170), inner, outer, glyph['width'])
        
        # Inner ring accent
        pygame.draw.circle(surface, (30, 40, 80), (self.center_x, self.center_y), self.inner_radius, 10)
        pygame.draw.circle(surface, (0, 0, 0), (self.center_x, self.center_y), self.inner_radius - 5, 0)
        
        # Draw chevrons
        for chevron in self.chevrons:
            angle_rad = math.radians(chevron['angle'])
            x = self.center_x + math.cos(angle_rad) * self.gate_radius
            y = self.center_y + math.sin(angle_rad) * self.gate_radius
            
            # Chevron symbol (triangle)
            size = 20
            points = [
                (x, y - size),
                (x - size // 2, y + size // 2),
                (x + size // 2, y + size // 2)
            ]
            
            if chevron['locked']:
                # Locked chevron - glowing orange
                glow = int(chevron['glow'])
                color = (255, min(255, 140 + glow // 2), 0)
                
                # Glow effect
                if chevron['glow'] > 100:
                    glow_surf = pygame.Surface((size * 4, size * 4), pygame.SRCALPHA)
                    glow_color = (255, 180, 0, int(chevron['glow'] * 0.6))
                    pygame.draw.circle(glow_surf, glow_color, (size * 2, size * 2), size * 2)
                    surface.blit(glow_surf, (int(x - size * 2), int(y - size * 2)))
                
                pygame.draw.polygon(surface, color, points)
                inner_glow = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
                pygame.draw.polygon(inner_glow, (255, 220, 120, 200), [(p[0] - x + size, p[1] - y + size) for p in points])
                inner_glow = pygame.transform.smoothscale(inner_glow, (size * 3, size * 3))
                surface.blit(inner_glow, (int(x - 1.5 * size), int(y - 1.5 * size)), special_flags=pygame.BLEND_ADD)
            else:
                # Inactive chevron
                pygame.draw.polygon(surface, (60, 60, 70), points)
            
            pygame.draw.polygon(surface, (200, 200, 200), points, 2)
        
        # Event horizon (after chevrons start locking)
        if self.progress > 0.3:
            # Base event horizon glow
            horizon_alpha = int(min(255, (self.progress - 0.3) * 400))
            horizon_surf = pygame.Surface((self.inner_radius * 2, self.inner_radius * 2), pygame.SRCALPHA)
            center = (self.inner_radius, self.inner_radius)
            
            # Pulsing watery ripples
            ripple_layers = 6
            for i in range(ripple_layers):
                wave_offset = math.sin(self.ripple_phase + i * 0.6) * 8
                radius = self.inner_radius - i * 18 + wave_offset
                alpha = max(10, horizon_alpha - i * 25)
                blue_component = min(255, 120 + i * 30)
                alpha_int = int(max(0, min(255, alpha)))
                color = (40, blue_component, 255, alpha_int)
                pygame.draw.circle(horizon_surf, color, center, int(max(10, radius)))
            
            # Energy swirl accent
            swirl_surf = pygame.Surface((self.inner_radius * 2, self.inner_radius * 2), pygame.SRCALPHA)
            for i in range(8):
                angle = self.ripple_phase * 180 / math.pi + i * 45
                start_angle = math.radians(angle)
                end_angle = start_angle + math.radians(40)
                color = (120, 200, 255, 90)
                pygame.draw.arc(swirl_surf, color, swirl_surf.get_rect(), start_angle, end_angle, 3)
            horizon_surf.blit(swirl_surf, (0, 0), special_flags=pygame.BLEND_ADD)
            
            surface.blit(horizon_surf, (self.center_x - self.inner_radius, self.center_y - self.inner_radius))
            
            # Swirling particles
            for particle in self.horizon_particles:
                if particle['alpha'] > 0:
                    angle_rad = math.radians(particle['angle'])
                    x = self.center_x + math.cos(angle_rad) * particle['distance']
                    y = self.center_y + math.sin(angle_rad) * particle['distance']
                    
                    particle_surf = pygame.Surface((particle['size'] * 2, particle['size'] * 2), pygame.SRCALPHA)
                    color = (150, 200, 255, int(particle['alpha']))
                    pygame.draw.circle(particle_surf, color, (particle['size'], particle['size']), particle['size'])
                    surface.blit(particle_surf, (int(x - particle['size']), int(y - particle['size'])))
        
        # OUTWARD VORTEX (KAWOOSH!) at 70%
        if self.progress > 0.7:
            for particle in self.vortex_particles:
                if particle['alpha'] > 0 and particle['distance'] < self.gate_radius * 2 and particle['size'] > 0:
                    angle_rad = math.radians(particle['angle'])
                    x = self.center_x + math.cos(angle_rad) * particle['distance']
                    y = self.center_y + math.sin(angle_rad) * particle['distance']
                    
                    size = max(1, int(particle['size']))  # Ensure size is at least 1
                    alpha = max(0, min(255, int(particle['alpha'])))  # Clamp alpha
                    
                    particle_surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
                    # Bright white/blue vortex particles
                    color = (200, 230, 255, alpha)
                    pygame.draw.circle(particle_surf, color, (size, size), size)
                    surface.blit(particle_surf, (int(x - size), int(y - size)))
            
            # Lens flare burst
            flare = pygame.Surface((self.gate_radius * 2, self.gate_radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(flare, (80, 180, 255, 70), (self.gate_radius, self.gate_radius), self.gate_radius)
            surface.blit(flare, (self.center_x - self.gate_radius, self.center_y - self.gate_radius), special_flags=pygame.BLEND_ADD)
        
        # Title text (fades in at end)
        if self.progress > 0.7:
            title_alpha = int(min(255, (self.progress - 0.7) * 850))
            pulse_scale = 1.0 + 0.03 * math.sin(self.title_pulse * 2)
            title_font = pygame.font.SysFont("Eurostile", 80, bold=True)
            title_text = title_font.render("STARGWENT", True, (230, 240, 255))
            title_text = pygame.transform.rotozoom(title_text, 0, pulse_scale)
            title_rect = title_text.get_rect(center=(self.center_x, self.screen_height - 140))
            
            # Stargate-style glow layers
            glow_surface = pygame.Surface((title_rect.width + 120, title_rect.height + 80), pygame.SRCALPHA)
            pygame.draw.ellipse(glow_surface, (40, 120, 255, min(180, title_alpha)), glow_surface.get_rect())
            surface.blit(glow_surface, (title_rect.x - 60, title_rect.y - 40), special_flags=pygame.BLEND_ADD)
            
            title_text.set_alpha(title_alpha)
            surface.blit(title_text, title_rect)
        
        # White fade to next screen (98.75-100%) - starts at 15.8s
        if self.progress > 0.9875:
            # Smooth fade out to white
            fade_progress = (self.progress - 0.9875) / 0.0125  # 0 to 1 over last 1.25% (0.2s)
            fade_alpha = int(fade_progress * 255)
            
            fade_surface = pygame.Surface((self.screen_width, self.screen_height))
            fade_surface.fill((255, 255, 255))
            fade_surface.set_alpha(fade_alpha)
            surface.blit(fade_surface, (0, 0))



def show_stargate_opening(screen):
    """Show the Stargate opening animation."""
    from game_settings import get_settings
    animation = StargateOpeningAnimation(screen.get_width(), screen.get_height())
    clock = pygame.time.Clock()
    sound_channel = None
    stargate_sound = _get_stargate_sequence_sound()
    if stargate_sound:
        try:
            settings = get_settings()
            stargate_sound.set_volume(settings.get_effective_sfx_volume() * _STARGATE_SEQUENCE_VOLUME)
            sound_channel = stargate_sound.play()
        except pygame.error as exc:
            print(f"[audio] Unable to play Stargate sequence audio: {exc}")
            sound_channel = None
    
    running = True
    while running:
        dt = clock.tick(60)
        
        # Handle events (allow skip)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                if sound_channel:
                    sound_channel.stop()
                return False
            elif event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
                if sound_channel:
                    try:
                        sound_channel.fadeout(600)
                    except pygame.error:
                        sound_channel.stop()
                return True  # Skip animation
        
        # Update and draw
        if not animation.update(dt):
            running = False
        
        animation.draw(screen)
        pygame.display.flip()
    
    return True
