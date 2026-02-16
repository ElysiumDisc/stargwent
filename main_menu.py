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
import display_manager
from deck_persistence import get_persistence
from cards import ALL_CARDS, FACTION_TAURI, FACTION_GOAULD, FACTION_JAFFA, FACTION_LUCIAN, FACTION_ASGARD, FACTION_NEUTRAL, reload_card_images
from deck_builder import FACTION_LEADERS, MIN_DECK_SIZE, MAX_DECK_SIZE, validate_deck
from unlocks import CardUnlockSystem, UNLOCKABLE_CARDS
from rules_menu import run_rules_menu
from lan_menu import run_lan_menu
from stats_menu import run_stats_menu
from dhd_button import DHDButtonManager
import board_renderer
from save_paths import get_deck_save_path

# Save file for custom decks (using XDG Base Directory path)
CUSTOM_DECKS_FILE = get_deck_save_path()
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
            except (json.JSONDecodeError, OSError):
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
            is_fullscreen = display_manager.FULLSCREEN
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

            display_manager.gpu_flip()
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
                        result = self.run_options_menu(display_manager.screen)
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
                    else:
                        display_manager.toggle_fullscreen_mode()
                    screen = display_manager.screen
                    main_menu = MainMenu(screen.get_width(), screen.get_height(), unlock_system)
                    main_menu.screen_surface = screen
            
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
        display_manager.gpu_flip()
    
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
        display_manager.gpu_flip()
        clock.tick(60)
    
    return None


# ===== STARGATE OPENING ANIMATION (MERGED FROM stargate_opening.py) =====

class StargateOpeningAnimation:
    """Dramatic Stargate opening animation with movie-accurate effects."""

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

        # Inner ring rotation state
        self.inner_ring_angle = 0.0  # Current rotation in degrees
        self.target_symbol_angles = []  # Target angles for each chevron dial
        self.current_dialing_chevron = 0
        self.ring_state = 'idle'  # idle, rotating, paused, locked
        self.rotation_speed = 180  # degrees per second
        self.rotation_direction = 1  # 1 = clockwise, -1 = counter-clockwise
        self.pause_timer = 0  # Brief pause when symbol aligns
        self.last_lock_time = 0

        # Generate target angles for each chevron (randomized destinations)
        for i in range(9):
            # Alternate rotation direction for visual interest
            angle = random.randint(0, 35) * 10  # 36 symbols, 10° apart
            self.target_symbol_angles.append(angle)

        # Chevrons with enhanced states
        self.chevrons = []
        for i in range(9):
            angle = i * 40 - 90  # Start at top
            self.chevrons.append({
                'angle': angle,
                'locked': False,
                'lock_time': 500 + i * 800,  # Adjusted timing for rotation
                'glow': 0,
                'state': 'idle',  # idle, aligning, engaging, locked
                'engage_offset': 0,  # For top chevron movement animation
                'scale_bump': 1.0  # For "clunk" visual feedback
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

        # Enhanced kawoosh particles (directional cone)
        self.kawoosh_particles = []
        for _ in range(300):
            self.kawoosh_particles.append({
                'angle': random.gauss(0, 20),  # Clustered around forward direction (toward viewer)
                'distance': 0,
                'base_speed': random.uniform(25, 50),
                'speed': 0,
                'size': random.randint(4, 12),
                'alpha': 255,
                'lifetime': 1.0,
                'layer': random.randint(0, 3),  # For depth layering
                'offset_x': random.uniform(-0.3, 0.3),  # Horizontal spread
                'offset_y': random.uniform(-0.3, 0.3)   # Vertical spread
            })

        # Kawoosh state machine
        self.kawoosh_state = 'dormant'  # dormant, burst, extend, retract, stable
        self.kawoosh_progress = 0.0
        self.kawoosh_distance = 0
        self.kawoosh_max_distance = self.gate_radius * 2.0
        self.kawoosh_start_time = None

        # Event horizon depth effect
        self.horizon_depth_layers = 8
        self.horizon_depth_phase = 0.0
        self.horizon_ripples = []  # Ripples that propagate from center

        # Starfield backdrop and glyph engravings for extra fidelity
        self.starfield = [{
            'x': random.randint(0, screen_width),
            'y': random.randint(0, screen_height),
            'speed': random.uniform(0.01, 0.05),
            'phase': random.uniform(0, math.tau),
            'size': random.choice([1, 1, 2])
        } for _ in range(200)]

        # Gate glyphs on the inner ring (these rotate)
        self.gate_glyphs = [{
            'base_angle': i * 10,  # Base angle before rotation
            'width': random.randint(2, 3),
            'length': random.randint(16, 22),
            'glow': 0  # For highlighting when aligned
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

        # Update inner ring rotation
        self._update_ring_rotation(dt)

        # Update chevron states and engagement
        self._update_chevrons(dt)

        # Update glyph highlighting
        self._update_glyph_highlighting(dt)

        # Update event horizon particles (after chevrons start locking)
        if self.progress > 0.3:
            for particle in self.horizon_particles:
                particle['distance'] += particle['speed'] * (dt / 16.0)
                particle['alpha'] = min(255, particle['alpha'] + 5)

                # Reset if too far
                if particle['distance'] > self.inner_radius:
                    particle['distance'] = 0
                    particle['angle'] = random.uniform(0, 360)

        # Update event horizon depth animation
        if self.progress > 0.3:
            self.horizon_depth_phase = (self.horizon_depth_phase + dt * 0.002) % 1.0

            # Occasionally spawn ripples from center
            if random.random() < 0.02:
                self.horizon_ripples.append({
                    'radius': 0,
                    'max_radius': self.inner_radius,
                    'alpha': 200,
                    'speed': random.uniform(1.5, 3.0)
                })

            # Update existing ripples
            for ripple in self.horizon_ripples[:]:
                ripple['radius'] += ripple['speed'] * dt * 0.1
                ripple['alpha'] = int(200 * (1.0 - ripple['radius'] / ripple['max_radius']))
                if ripple['radius'] >= ripple['max_radius']:
                    self.horizon_ripples.remove(ripple)

        # Update kawoosh effect
        self._update_kawoosh(dt)

        return self.progress < 1.0

    def _update_ring_rotation(self, dt):
        """Handle inner ring dialing animation."""
        # Only rotate during dialing phase (before all chevrons locked)
        if self.current_dialing_chevron >= 9:
            return

        chevron = self.chevrons[self.current_dialing_chevron]
        target_angle = self.target_symbol_angles[self.current_dialing_chevron]

        # Check if it's time to start dialing this chevron
        dial_start_time = 300 + self.current_dialing_chevron * 800

        if self.elapsed < dial_start_time:
            self.ring_state = 'idle'
            return

        if self.ring_state == 'idle':
            # Start rotating toward target
            self.ring_state = 'rotating'
            # Alternate rotation direction
            self.rotation_direction = 1 if self.current_dialing_chevron % 2 == 0 else -1

        elif self.ring_state == 'rotating':
            # Calculate angle difference
            angle_diff = (target_angle - self.inner_ring_angle) % 360
            if angle_diff > 180:
                angle_diff -= 360

            # Check if close enough to lock
            if abs(angle_diff) < 5:
                self.inner_ring_angle = target_angle
                self.ring_state = 'paused'
                self.pause_timer = 200  # 200ms pause before lock
                chevron['state'] = 'aligning'
            else:
                # Rotate toward target
                rotation_amount = self.rotation_speed * dt / 1000.0
                self.inner_ring_angle += rotation_amount * self.rotation_direction
                self.inner_ring_angle = self.inner_ring_angle % 360

        elif self.ring_state == 'paused':
            self.pause_timer -= dt
            if self.pause_timer <= 0:
                # Lock the chevron
                chevron['state'] = 'engaging'
                chevron['locked'] = True
                chevron['glow'] = 255
                chevron['scale_bump'] = 1.3  # Visual "clunk"
                self.ring_state = 'locked'
                self.pause_timer = 300  # Hold before next dial

        elif self.ring_state == 'locked':
            self.pause_timer -= dt
            if self.pause_timer <= 0:
                chevron['state'] = 'locked'
                self.current_dialing_chevron += 1
                self.ring_state = 'idle'

    def _update_chevrons(self, dt):
        """Update chevron animations."""
        for i, chevron in enumerate(self.chevrons):
            # Fade glow (but pulse if locked)
            if chevron['locked']:
                # Pulsing glow for locked chevrons
                pulse = 50 + 30 * math.sin(self.elapsed * 0.005 + i * 0.5)
                target_glow = max(pulse, 50)
                if chevron['glow'] > target_glow + 10:
                    chevron['glow'] = max(target_glow, chevron['glow'] - dt * 0.4)
            else:
                if chevron['glow'] > 0:
                    chevron['glow'] = max(0, chevron['glow'] - dt * 0.3)

            # Animate scale bump back to normal
            if chevron['scale_bump'] > 1.0:
                chevron['scale_bump'] = max(1.0, chevron['scale_bump'] - dt * 0.002)

            # Top chevron (index 0) engagement animation
            if i == 0 and chevron['state'] == 'engaging':
                chevron['engage_offset'] = min(8, chevron['engage_offset'] + dt * 0.05)
            elif i == 0 and chevron['state'] == 'locked':
                chevron['engage_offset'] = max(0, chevron['engage_offset'] - dt * 0.02)

    def _update_glyph_highlighting(self, dt):
        """Update glyph highlighting based on ring position."""
        # Find which glyph is at the top (aligned with top chevron)
        aligned_index = self._get_aligned_glyph_index()

        for i, glyph in enumerate(self.gate_glyphs):
            if i == aligned_index and self.ring_state == 'rotating':
                # Highlight the aligned glyph
                glyph['glow'] = min(255, glyph['glow'] + dt * 0.8)
            else:
                # Fade out
                glyph['glow'] = max(0, glyph['glow'] - dt * 0.3)

    def _get_aligned_glyph_index(self):
        """Calculate which glyph is at top (angle -90° / 270°)."""
        # Top of gate is at -90 degrees
        # We need to find which glyph, when rotated, is at the top
        adjusted_angle = (270 - self.inner_ring_angle) % 360
        return int(adjusted_angle / 10) % 36

    def _update_kawoosh(self, dt):
        """Handle kawoosh burst/extend/retract phases."""
        kawoosh_trigger = 0.68  # Start kawoosh at 68%

        if self.progress < kawoosh_trigger:
            self.kawoosh_state = 'dormant'
            return

        if self.kawoosh_state == 'dormant':
            self.kawoosh_state = 'burst'
            self.kawoosh_progress = 0.0
            self.kawoosh_start_time = self.elapsed
            # Initialize particles for burst
            for particle in self.kawoosh_particles:
                particle['distance'] = 0
                particle['speed'] = particle['base_speed'] * random.uniform(0.8, 1.2)
                particle['alpha'] = 255
                particle['lifetime'] = 1.0

        # Calculate time since kawoosh started
        kawoosh_elapsed = (self.elapsed - self.kawoosh_start_time) / 1000.0  # in seconds

        if self.kawoosh_state == 'burst':
            # Burst phase: 0-0.3s - violent outward explosion
            if kawoosh_elapsed < 0.3:
                self.kawoosh_progress = kawoosh_elapsed / 0.3
                self.kawoosh_distance = self.kawoosh_max_distance * 0.4 * self.kawoosh_progress
                # Particles move fast outward
                for particle in self.kawoosh_particles:
                    particle['distance'] += particle['speed'] * dt / 16.0 * 2.0
                    particle['alpha'] = 255
            else:
                self.kawoosh_state = 'extend'

        elif self.kawoosh_state == 'extend':
            # Extension phase: 0.3-0.8s - vortex extends to max
            extend_time = kawoosh_elapsed - 0.3
            if extend_time < 0.5:
                self.kawoosh_progress = extend_time / 0.5
                self.kawoosh_distance = self.kawoosh_max_distance * (0.4 + 0.6 * self.kawoosh_progress)
                # Particles continue but slower
                for particle in self.kawoosh_particles:
                    particle['distance'] += particle['speed'] * dt / 16.0 * 0.5
            else:
                self.kawoosh_state = 'retract'

        elif self.kawoosh_state == 'retract':
            # Retraction phase: 0.8-1.5s - vortex pulls back
            retract_time = kawoosh_elapsed - 0.8
            if retract_time < 0.7:
                self.kawoosh_progress = 1.0 - (retract_time / 0.7)
                self.kawoosh_distance = self.kawoosh_max_distance * self.kawoosh_progress
                # Particles pull back toward gate
                for particle in self.kawoosh_particles:
                    particle['distance'] = max(0, particle['distance'] - particle['speed'] * dt / 16.0 * 1.5)
                    particle['alpha'] = int(255 * self.kawoosh_progress)
            else:
                self.kawoosh_state = 'stable'
                self.kawoosh_distance = 0

        elif self.kawoosh_state == 'stable':
            # Stable event horizon - particles reset for ambient effect
            for particle in self.kawoosh_particles:
                if particle['distance'] > 0:
                    particle['distance'] = max(0, particle['distance'] - dt * 0.5)
                particle['alpha'] = max(0, particle['alpha'] - int(dt * 0.2))
    
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

        # Draw gate body with rotation track
        self._draw_gate_body(surface)

        # Draw inner ring with rotating glyphs
        self._draw_inner_ring(surface)

        # Draw chevrons with engagement animation
        self._draw_chevrons(surface)

        # Event horizon with depth effect (after chevrons start locking)
        if self.progress > 0.3:
            self._draw_event_horizon_3d(surface)

        # Kawoosh effect
        if self.kawoosh_state != 'dormant':
            self._draw_kawoosh(surface)

        # Title text (fades in at end)
        if self.progress > 0.75:
            self._draw_title(surface)

        # White fade to next screen (98.75-100%) - starts at 15.8s
        if self.progress > 0.9875:
            fade_progress = (self.progress - 0.9875) / 0.0125
            fade_alpha = int(fade_progress * 255)
            fade_surface = pygame.Surface((self.screen_width, self.screen_height))
            fade_surface.fill((255, 255, 255))
            fade_surface.set_alpha(fade_alpha)
            surface.blit(fade_surface, (0, 0))

    def _draw_gate_body(self, surface):
        """Draw the gate body with metallic rings and rotation track."""
        gate_surface = pygame.Surface((self.gate_radius * 2 + 80, self.gate_radius * 2 + 80), pygame.SRCALPHA)
        gate_center = gate_surface.get_width() // 2

        # Outer beveled edge highlight
        for i in range(5):
            radius = self.gate_radius + 35 - i
            highlight = 80 - i * 10
            pygame.draw.circle(gate_surface, (highlight, highlight, highlight + 10, 200), (gate_center, gate_center), radius, 1)

        # Main metallic gradient rings
        for i in range(26):
            radius = self.gate_radius + 30 - i * 2
            shade = 40 + i * 3
            pygame.draw.circle(gate_surface, (shade, shade, shade + 20, 250), (gate_center, gate_center), radius, 2)

        # Inner track where ring rotates (darker groove)
        track_radius = self.inner_radius + 25
        pygame.draw.circle(gate_surface, (20, 20, 30, 255), (gate_center, gate_center), track_radius, 8)
        pygame.draw.circle(gate_surface, (15, 15, 25, 255), (gate_center, gate_center), track_radius - 2, 4)

        # Inner ring base
        pygame.draw.circle(gate_surface, (30, 30, 45, 255), (gate_center, gate_center), self.inner_radius + 18, 18)

        surface.blit(gate_surface, (self.center_x - gate_center, self.center_y - gate_center))

    def _draw_inner_ring(self, surface):
        """Draw the rotating inner ring with glyphs."""
        # Draw glyphs with rotation applied
        for i, glyph in enumerate(self.gate_glyphs):
            # Apply rotation to glyph angle
            rotated_angle = glyph['base_angle'] + self.inner_ring_angle
            angle_rad = math.radians(rotated_angle)

            glyph_radius = self.gate_radius - 8
            outer = (
                self.center_x + math.cos(angle_rad) * glyph_radius,
                self.center_y + math.sin(angle_rad) * glyph_radius
            )
            inner = (
                self.center_x + math.cos(angle_rad) * (glyph_radius - glyph['length']),
                self.center_y + math.sin(angle_rad) * (glyph_radius - glyph['length'])
            )

            # Base glyph color
            base_color = (110, 130, 170)

            # Highlight if glowing (aligned with top chevron)
            if glyph['glow'] > 0:
                glow_intensity = glyph['glow'] / 255.0
                # Glow effect around glyph
                glow_surf = pygame.Surface((40, 40), pygame.SRCALPHA)
                glow_color = (255, 200, 100, int(glyph['glow'] * 0.7))
                pygame.draw.circle(glow_surf, glow_color, (20, 20), 18)
                mid_x = (outer[0] + inner[0]) / 2
                mid_y = (outer[1] + inner[1]) / 2
                surface.blit(glow_surf, (int(mid_x - 20), int(mid_y - 20)), special_flags=pygame.BLEND_ADD)

                # Brighter glyph color when highlighted
                r = int(110 + 145 * glow_intensity)
                g = int(130 + 100 * glow_intensity)
                b = int(170 + 85 * glow_intensity)
                base_color = (min(255, r), min(255, g), min(255, b))

            pygame.draw.line(surface, base_color, inner, outer, glyph['width'])

        # Inner ring accent circle
        pygame.draw.circle(surface, (30, 40, 80), (self.center_x, self.center_y), self.inner_radius, 10)
        pygame.draw.circle(surface, (0, 0, 0), (self.center_x, self.center_y), self.inner_radius - 5, 0)

    def _draw_chevrons(self, surface):
        """Draw chevrons with engagement animation."""
        for i, chevron in enumerate(self.chevrons):
            angle_rad = math.radians(chevron['angle'])

            # Base position
            base_x = self.center_x + math.cos(angle_rad) * self.gate_radius
            base_y = self.center_y + math.sin(angle_rad) * self.gate_radius

            # Top chevron (i=0) has engagement offset
            if i == 0:
                # Move inward toward center when engaging
                offset = chevron['engage_offset']
                base_x -= math.cos(angle_rad) * offset
                base_y -= math.sin(angle_rad) * offset

            x, y = base_x, base_y

            # Chevron size with scale bump
            base_size = 20
            size = int(base_size * chevron['scale_bump'])

            # Calculate chevron points (pointing outward from center)
            # Rotate points based on chevron angle
            cos_a = math.cos(angle_rad + math.pi / 2)
            sin_a = math.sin(angle_rad + math.pi / 2)

            # Triangle pointing outward
            tip_offset = size
            base_offset = size // 2
            points = [
                (x + cos_a * tip_offset, y + sin_a * tip_offset),  # Tip
                (x - cos_a * base_offset - math.cos(angle_rad) * base_offset,
                 y - sin_a * base_offset - math.sin(angle_rad) * base_offset),
                (x - cos_a * base_offset + math.cos(angle_rad) * base_offset,
                 y - sin_a * base_offset + math.sin(angle_rad) * base_offset)
            ]

            if chevron['locked']:
                # Locked chevron - glowing orange with pulse
                glow = int(chevron['glow'])
                color = (255, min(255, 140 + glow // 2), 0)

                # Outer glow effect
                if chevron['glow'] > 30:
                    glow_size = int(size * 2 * chevron['scale_bump'])
                    glow_surf = pygame.Surface((glow_size * 2, glow_size * 2), pygame.SRCALPHA)
                    glow_alpha = int(min(180, chevron['glow'] * 0.7))
                    glow_color = (255, 180, 0, glow_alpha)
                    pygame.draw.circle(glow_surf, glow_color, (glow_size, glow_size), glow_size)
                    surface.blit(glow_surf, (int(x - glow_size), int(y - glow_size)), special_flags=pygame.BLEND_ADD)

                pygame.draw.polygon(surface, color, points)

                # Inner bright glow
                inner_glow = pygame.Surface((size * 3, size * 3), pygame.SRCALPHA)
                local_points = [(p[0] - x + size * 1.5, p[1] - y + size * 1.5) for p in points]
                pygame.draw.polygon(inner_glow, (255, 220, 120, 200), local_points)
                surface.blit(inner_glow, (int(x - size * 1.5), int(y - size * 1.5)), special_flags=pygame.BLEND_ADD)

            elif chevron['state'] == 'aligning':
                # Aligning state - dim orange glow
                pygame.draw.polygon(surface, (180, 120, 40), points)
            else:
                # Inactive chevron
                pygame.draw.polygon(surface, (60, 60, 70), points)

            # Chevron outline
            pygame.draw.polygon(surface, (200, 200, 200), points, 2)

    def _draw_event_horizon_3d(self, surface):
        """Draw event horizon with 3D depth tunnel effect."""
        horizon_alpha = int(min(255, (self.progress - 0.3) * 400))
        horizon_surf = pygame.Surface((self.inner_radius * 2, self.inner_radius * 2), pygame.SRCALPHA)
        center = (self.inner_radius, self.inner_radius)

        # 3D depth layers (concentric rings getting smaller toward center)
        for i in range(self.horizon_depth_layers):
            # Each layer smaller, creating perspective illusion
            scale = 1.0 - (i * 0.1)
            depth_offset = (self.horizon_depth_phase + i * 0.12) % 1.0

            # Layer radius with animated movement "into" screen
            base_radius = (self.inner_radius - 10) * scale
            animated_radius = base_radius * (0.95 + 0.05 * math.sin(depth_offset * math.tau))

            # Color gradient: lighter at edges, darker blue at center
            brightness = 255 - (i * 25)
            blue = min(255, 180 + i * 10)
            green = max(80, 150 - i * 15)
            layer_alpha = int(max(30, horizon_alpha - i * 20))

            color = (int(green * 0.3), green, blue, layer_alpha)
            pygame.draw.circle(horizon_surf, color, center, int(max(5, animated_radius)))

        # Watery ripple overlay
        for i in range(4):
            wave_offset = math.sin(self.ripple_phase * 2 + i * 0.8) * 6
            radius = self.inner_radius - 15 - i * 25 + wave_offset
            if radius > 10:
                alpha = int(max(20, 80 - i * 15))
                color = (100, 200, 255, alpha)
                pygame.draw.circle(horizon_surf, color, center, int(radius), 2)

        # Energy swirl accent
        swirl_surf = pygame.Surface((self.inner_radius * 2, self.inner_radius * 2), pygame.SRCALPHA)
        for i in range(6):
            angle = self.ripple_phase * 200 / math.pi + i * 60
            start_angle = math.radians(angle)
            end_angle = start_angle + math.radians(50)
            color = (120, 200, 255, 70)
            pygame.draw.arc(swirl_surf, color, swirl_surf.get_rect().inflate(-20, -20), start_angle, end_angle, 3)
        horizon_surf.blit(swirl_surf, (0, 0), special_flags=pygame.BLEND_ADD)

        # Draw propagating ripples from center
        for ripple in self.horizon_ripples:
            if ripple['alpha'] > 0:
                ripple_color = (150, 220, 255, ripple['alpha'])
                pygame.draw.circle(horizon_surf, ripple_color, center, int(ripple['radius']), 2)

        surface.blit(horizon_surf, (self.center_x - self.inner_radius, self.center_y - self.inner_radius))

        # Swirling particles
        for particle in self.horizon_particles:
            if particle['alpha'] > 0:
                angle_rad = math.radians(particle['angle'])
                px = self.center_x + math.cos(angle_rad) * particle['distance']
                py = self.center_y + math.sin(angle_rad) * particle['distance']

                particle_surf = pygame.Surface((particle['size'] * 2, particle['size'] * 2), pygame.SRCALPHA)
                color = (150, 200, 255, int(particle['alpha']))
                pygame.draw.circle(particle_surf, color, (particle['size'], particle['size']), particle['size'])
                surface.blit(particle_surf, (int(px - particle['size']), int(py - particle['size'])))

    def _draw_kawoosh(self, surface):
        """Draw the kawoosh effect with burst/extend/retract phases."""
        if self.kawoosh_state == 'stable':
            # Just draw a subtle lens flare for stable wormhole
            flare = pygame.Surface((self.gate_radius * 2, self.gate_radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(flare, (60, 140, 255, 40), (self.gate_radius, self.gate_radius), self.gate_radius)
            surface.blit(flare, (self.center_x - self.gate_radius, self.center_y - self.gate_radius), special_flags=pygame.BLEND_ADD)
            return

        # Cone-shaped vortex effect
        if self.kawoosh_distance > 0:
            # Draw the main vortex cone (narrower at gate, wider at tip)
            vortex_surf = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)

            # Multiple layers for depth
            for layer in range(4):
                layer_alpha = int(150 - layer * 30)
                layer_width = self.inner_radius * (0.8 - layer * 0.15)

                # Cone points
                cone_length = self.kawoosh_distance * (1.0 - layer * 0.1)
                tip_width = layer_width * (1.0 + cone_length / self.gate_radius * 0.5)

                # Color: bright white core, blue edges
                if layer == 0:
                    color = (255, 255, 255, layer_alpha)
                else:
                    blue_shift = layer * 40
                    color = (200 - blue_shift, 220 - blue_shift // 2, 255, layer_alpha)

                # Draw cone as a series of circles expanding outward
                steps = int(cone_length / 8) + 1
                for step in range(steps):
                    t = step / max(1, steps - 1)
                    step_dist = cone_length * t
                    step_radius = layer_width + (tip_width - layer_width) * t

                    # Wavy distortion
                    wave = math.sin(self.ripple_phase * 3 + step * 0.5) * 5 * t
                    cx = self.center_x + wave
                    cy = self.center_y - step_dist  # Toward viewer (up on screen)

                    step_alpha = int(layer_alpha * (1.0 - t * 0.5))
                    step_color = (color[0], color[1], color[2], step_alpha)
                    pygame.draw.circle(vortex_surf, step_color, (int(cx), int(cy)), int(max(3, step_radius)))

            surface.blit(vortex_surf, (0, 0), special_flags=pygame.BLEND_ADD)

        # Draw kawoosh particles
        for particle in self.kawoosh_particles:
            if particle['alpha'] > 10 and particle['distance'] > 0:
                # Particles spread in a cone toward viewer
                spread = particle['distance'] / self.kawoosh_max_distance
                px = self.center_x + particle['offset_x'] * particle['distance']
                py = self.center_y - particle['distance']  # Moving toward viewer (up)

                size = max(2, int(particle['size'] * (1.0 + spread * 0.5)))
                alpha = max(0, min(255, int(particle['alpha'])))

                if size > 0 and alpha > 0:
                    particle_surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
                    # Bright white/blue vortex particles
                    color = (220, 240, 255, alpha)
                    pygame.draw.circle(particle_surf, color, (size, size), size)
                    surface.blit(particle_surf, (int(px - size), int(py - size)), special_flags=pygame.BLEND_ADD)

        # Intense lens flare during burst/extend
        if self.kawoosh_state in ('burst', 'extend'):
            flare_intensity = 1.0 if self.kawoosh_state == 'burst' else 0.7
            flare = pygame.Surface((self.gate_radius * 3, self.gate_radius * 3), pygame.SRCALPHA)
            flare_alpha = int(120 * flare_intensity)
            pygame.draw.circle(flare, (100, 200, 255, flare_alpha), (self.gate_radius * 1.5, self.gate_radius * 1.5), int(self.gate_radius * 1.5))
            surface.blit(flare, (int(self.center_x - self.gate_radius * 1.5), int(self.center_y - self.gate_radius * 1.5)), special_flags=pygame.BLEND_ADD)

    def _draw_title(self, surface):
        """Draw the title text with glow effect."""
        title_alpha = int(min(255, (self.progress - 0.75) * 1000))
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
        display_manager.gpu_flip()
    
    return True
