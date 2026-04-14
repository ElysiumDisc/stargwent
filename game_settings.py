"""
Game Settings System for Stargwent
Handles persistent game settings like volume, controls, etc.
"""
import json
import os
import pygame
import board_renderer
from save_paths import atomic_write_json, get_settings_path, ensure_migration, sync_saves
from game_config import GAME_VERSION, GAME_LICENSE

# Ensure legacy saves are migrated to XDG directory on first access
ensure_migration()

# Settings file path (using XDG Base Directory path)
SETTINGS_FILE = get_settings_path()

class GameSettings:
    """Manages persistent game settings"""

    def __init__(self):
        self.settings = self.load_settings()
        self._dirty = False
        self._batch_mode = False  # When True, defer saves until batch ends

    def load_settings(self) -> dict:
        """Load saved settings from file"""
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r') as f:
                    loaded = json.load(f)
                    # Merge with defaults to ensure all keys exist
                    defaults = self._get_default_settings()
                    defaults.update(loaded)
                    return defaults
            except Exception as e:
                print(f"Error loading settings: {e}")
                return self._get_default_settings()
        return self._get_default_settings()

    def save_settings(self):
        """Save current settings to file (respects batch mode)."""
        if self._batch_mode:
            self._dirty = True
            return
        self._force_save()

    def _force_save(self):
        """Unconditionally write settings to disk (atomic)."""
        if atomic_write_json(SETTINGS_FILE, self.settings):
            self._dirty = False
            print(f"✓ Settings saved to {SETTINGS_FILE}")
        else:
            print(f"Error saving settings to {SETTINGS_FILE}")

    def begin_batch(self):
        """Start a batch of changes — saves are deferred until end_batch()."""
        self._batch_mode = True

    def end_batch(self):
        """End a batch of changes and save if anything was modified."""
        self._batch_mode = False
        if self._dirty:
            self._force_save()

    def _get_default_settings(self) -> dict:
        """Default settings"""
        return {
            "master_volume": 1.0,  # 0.0 to 1.0
            "music_volume": 0.5,
            "sfx_volume": 0.4,
            "voice_volume": 0.6,
            "show_fps": False,
            "vsync": True,  # VSync enabled by default for tear-free rendering
            "competitive_mode": False,  # Precise timing for LAN games
            "gpu_enabled": True,
            "bloom_enabled": True,
            "bloom_intensity": 0.6,
            "bloom_threshold": 0.65,
            "vignette_enabled": True,
            "shader_quality": "medium",  # "low" | "medium" | "high"
        }

    def get_master_volume(self) -> float:
        """Get master volume (0.0 to 1.0)"""
        return self.settings.get("master_volume", 1.0)

    def set_master_volume(self, volume: float):
        """Set master volume (0.0 to 1.0) and apply immediately"""
        volume = max(0.0, min(1.0, volume))  # Clamp to 0-1
        if self.settings.get("master_volume") == volume:
            return
        self.settings["master_volume"] = volume
        self.apply_volume()
        self.save_settings()

    def get_music_volume(self) -> float:
        """Get music volume (0.0 to 1.0)"""
        return self.settings.get("music_volume", 0.5)

    def set_music_volume(self, volume: float):
        """Set music volume (0.0 to 1.0) and apply immediately"""
        volume = max(0.0, min(1.0, volume))
        if self.settings.get("music_volume") == volume:
            return
        self.settings["music_volume"] = volume
        self.apply_volume()
        self.save_settings()

    def get_sfx_volume(self) -> float:
        """Get SFX volume (0.0 to 1.0)"""
        return self.settings.get("sfx_volume", 0.4)

    def set_sfx_volume(self, volume: float):
        """Set SFX volume (0.0 to 1.0)"""
        volume = max(0.0, min(1.0, volume))
        if self.settings.get("sfx_volume") == volume:
            return
        self.settings["sfx_volume"] = volume
        # SFX volume will be applied when sounds play
        self.save_settings()

    def get_voice_volume(self) -> float:
        """Get voice volume (0.0 to 1.0)"""
        return self.settings.get("voice_volume", 0.6)

    def set_voice_volume(self, volume: float):
        """Set voice volume (0.0 to 1.0)"""
        volume = max(0.0, min(1.0, volume))
        if self.settings.get("voice_volume") == volume:
            return
        self.settings["voice_volume"] = volume
        self.save_settings()

    def apply_volume(self):
        """Apply current volume settings to pygame mixer"""
        if not pygame.mixer.get_init():
            return

        master = self.get_master_volume()
        music = self.get_music_volume()

        # Apply to music (master * music volume)
        final_music_vol = master * music
        pygame.mixer.music.set_volume(final_music_vol)

    def get_effective_music_volume(self) -> float:
        """Get effective music volume (master * music)"""
        return self.get_master_volume() * self.get_music_volume()

    def get_effective_sfx_volume(self) -> float:
        """Get effective SFX volume (master * sfx)"""
        return self.get_master_volume() * self.get_sfx_volume()

    def get_effective_voice_volume(self) -> float:
        """Get effective voice volume (master * voice)"""
        return self.get_master_volume() * self.get_voice_volume()

    def get_show_fps(self) -> bool:
        """Get show FPS setting"""
        return self.settings.get("show_fps", False)

    def set_show_fps(self, show: bool):
        """Set show FPS setting"""
        show = bool(show)
        if self.settings.get("show_fps") == show:
            return
        self.settings["show_fps"] = show
        self.save_settings()

    def get_vsync_enabled(self) -> bool:
        """Get VSync enabled setting"""
        return self.settings.get("vsync", True)

    def set_vsync_enabled(self, enabled: bool):
        """Set VSync enabled setting"""
        enabled = bool(enabled)
        if self.settings.get("vsync") == enabled:
            return
        self.settings["vsync"] = enabled
        self.save_settings()

    def get_competitive_mode(self) -> bool:
        """Get competitive mode setting (precise timing for LAN games)"""
        return self.settings.get("competitive_mode", False)

    def set_competitive_mode(self, enabled: bool):
        """Set competitive mode setting"""
        enabled = bool(enabled)
        if self.settings.get("competitive_mode") == enabled:
            return
        self.settings["competitive_mode"] = enabled
        self.save_settings()

    def get_gpu_enabled(self) -> bool:
        return self.settings.get("gpu_enabled", True)

    def set_gpu_enabled(self, enabled: bool):
        enabled = bool(enabled)
        if self.settings.get("gpu_enabled") == enabled:
            return
        self.settings["gpu_enabled"] = enabled
        self.save_settings()

    def get_bloom_enabled(self) -> bool:
        return self.settings.get("bloom_enabled", True)

    def set_bloom_enabled(self, enabled: bool):
        enabled = bool(enabled)
        if self.settings.get("bloom_enabled") == enabled:
            return
        self.settings["bloom_enabled"] = enabled
        self.save_settings()

    def get_bloom_intensity(self) -> float:
        return self.settings.get("bloom_intensity", 0.6)

    def set_bloom_intensity(self, value: float):
        value = max(0.0, min(1.0, value))
        if self.settings.get("bloom_intensity") == value:
            return
        self.settings["bloom_intensity"] = value
        self.save_settings()

    def get_bloom_threshold(self) -> float:
        return self.settings.get("bloom_threshold", 0.65)

    def set_bloom_threshold(self, value: float):
        value = max(0.0, min(1.0, value))
        if self.settings.get("bloom_threshold") == value:
            return
        self.settings["bloom_threshold"] = value
        self.save_settings()

    def get_vignette_enabled(self) -> bool:
        return self.settings.get("vignette_enabled", True)

    def set_vignette_enabled(self, enabled: bool):
        enabled = bool(enabled)
        if self.settings.get("vignette_enabled") == enabled:
            return
        self.settings["vignette_enabled"] = enabled
        self.save_settings()

    def get_shader_quality(self) -> str:
        return self.settings.get("shader_quality", "medium")

    def set_shader_quality(self, quality: str):
        if quality in ("low", "medium", "high"):
            if self.settings.get("shader_quality") == quality:
                return
            self.settings["shader_quality"] = quality
            self.save_settings()


# Global settings instance
_settings_instance = None

def get_settings() -> GameSettings:
    """Get the global settings instance"""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = GameSettings()
    return _settings_instance


def draw_back_button(surface, font=None):
    """Draw a DHD-style back button in top-left corner. Returns the button rect."""
    return board_renderer.draw_dhd_back_button(surface, 20, 20, 80)


def run_settings_menu(screen):
    """Run the settings menu."""
    settings = get_settings()
    clock = pygame.time.Clock()
    running = True

    screen_width, screen_height = screen.get_size()

    # Slider tracking
    dragging_slider = None

    while running:
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                import sys
                sys.exit()

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Check back button
                if back_rect.collidepoint(event.pos):
                    try:
                        import os
                        _sel_path = os.path.join("assets", "audio", "menu_select.ogg")
                        if os.path.exists(_sel_path):
                            _sel_snd = pygame.mixer.Sound(_sel_path)
                            _sel_snd.set_volume(settings.get_effective_sfx_volume())
                            _sel_snd.play()
                    except (pygame.error, Exception):
                        pass
                    running = False

                # Check sliders
                for name, slider_rect in slider_rects.items():
                    if slider_rect.collidepoint(event.pos):
                        dragging_slider = name
                        settings.begin_batch()
                        # Update value immediately
                        x_rel = (event.pos[0] - slider_rect.x) / slider_rect.width
                        x_rel = max(0.0, min(1.0, x_rel))
                        if name == "master":
                            settings.set_master_volume(x_rel)
                        elif name == "music":
                            settings.set_music_volume(x_rel)
                        elif name == "sfx":
                            settings.set_sfx_volume(x_rel)
                        elif name == "voice":
                            settings.set_voice_volume(x_rel)

            elif event.type == pygame.MOUSEBUTTONUP:
                if dragging_slider:
                    settings.end_batch()
                dragging_slider = None

            elif event.type == pygame.MOUSEMOTION and dragging_slider:
                slider_rect = slider_rects.get(dragging_slider)
                if slider_rect:
                    x_rel = (event.pos[0] - slider_rect.x) / slider_rect.width
                    x_rel = max(0.0, min(1.0, x_rel))
                    if dragging_slider == "master":
                        settings.set_master_volume(x_rel)
                    elif dragging_slider == "music":
                        settings.set_music_volume(x_rel)
                    elif dragging_slider == "sfx":
                        settings.set_sfx_volume(x_rel)
                    elif dragging_slider == "voice":
                        settings.set_voice_volume(x_rel)

        # Draw
        screen.fill((20, 25, 35))

        # Back button
        back_rect = draw_back_button(screen)

        # Title
        title_font = pygame.font.SysFont("Arial", 48, bold=True)
        title = title_font.render("SETTINGS", True, (200, 220, 255))
        screen.blit(title, (screen_width // 2 - title.get_width() // 2, 80))

        # Sliders
        slider_font = pygame.font.SysFont("Arial", 28, bold=True)
        slider_rects = {}
        slider_y = 180
        slider_width = 400
        slider_height = 30
        slider_x = screen_width // 2 - slider_width // 2

        volumes = [
            ("master", "Master Volume", settings.get_master_volume()),
            ("music", "Music Volume", settings.get_music_volume()),
            ("voice", "Voice Volume", settings.get_voice_volume()),
            ("sfx", "Effects Volume", settings.get_sfx_volume()),
        ]

        for name, label, value in volumes:
            # Label
            label_surf = slider_font.render(label, True, (180, 200, 220))
            screen.blit(label_surf, (slider_x, slider_y))
            slider_y += 35

            # Slider background
            slider_rect = pygame.Rect(slider_x, slider_y, slider_width, slider_height)
            slider_rects[name] = slider_rect
            pygame.draw.rect(screen, (40, 50, 70), slider_rect, border_radius=5)
            pygame.draw.rect(screen, (70, 100, 140), slider_rect, width=2, border_radius=5)

            # Slider fill
            fill_width = int(slider_width * value)
            if fill_width > 0:
                fill_rect = pygame.Rect(slider_x, slider_y, fill_width, slider_height)
                pygame.draw.rect(screen, (80, 140, 200), fill_rect, border_radius=5)

            # Slider handle
            handle_x = slider_x + int(slider_width * value)
            handle_rect = pygame.Rect(handle_x - 8, slider_y - 4, 16, slider_height + 8)
            pygame.draw.rect(screen, (150, 200, 255), handle_rect, border_radius=4)

            # Value text
            value_text = slider_font.render(f"{int(value * 100)}%", True, (255, 255, 255))
            screen.blit(value_text, (slider_x + slider_width + 20, slider_y))

            slider_y += 60

        # Hint text
        hint_font = pygame.font.SysFont("Arial", 20)
        hint = hint_font.render("Press ESC or click BACK to return", True, (120, 140, 160))
        screen.blit(hint, (screen_width // 2 - hint.get_width() // 2, screen_height - 60))

        # Version & license
        version_font = pygame.font.SysFont("Arial", 16)
        version_text = f"v{GAME_VERSION}  \u2022  {GAME_LICENSE}"
        version_surf = version_font.render(version_text, True, (90, 105, 125))
        screen.blit(version_surf, (screen_width // 2 - version_surf.get_width() // 2, screen_height - 30))

        import display_manager
        display_manager.gpu_flip()
        clock.tick(60)

    # Flush any pending batch save (e.g., if menu closed while dragging a slider)
    if dragging_slider:
        settings.end_batch()
    return
