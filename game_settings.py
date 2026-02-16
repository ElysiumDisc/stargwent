"""
Game Settings System for Stargwent
Handles persistent game settings like volume, controls, etc.
"""
import json
import os
import pygame
import board_renderer
from save_paths import get_settings_path, ensure_migration

# Ensure legacy saves are migrated to XDG directory on first access
ensure_migration()

# Settings file path (using XDG Base Directory path)
SETTINGS_FILE = get_settings_path()

class GameSettings:
    """Manages persistent game settings"""

    def __init__(self):
        self.settings = self.load_settings()

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
        """Save current settings to file"""
        try:
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(self.settings, f, indent=2)
            print(f"✓ Settings saved to {SETTINGS_FILE}")
        except Exception as e:
            print(f"Error saving settings: {e}")

    def _get_default_settings(self) -> dict:
        """Default settings"""
        return {
            "master_volume": 0.7,  # 0.0 to 1.0
            "music_volume": 0.7,
            "sfx_volume": 0.7,
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
        return self.settings.get("master_volume", 0.7)

    def set_master_volume(self, volume: float):
        """Set master volume (0.0 to 1.0) and apply immediately"""
        volume = max(0.0, min(1.0, volume))  # Clamp to 0-1
        self.settings["master_volume"] = volume
        self.apply_volume()
        self.save_settings()

    def get_music_volume(self) -> float:
        """Get music volume (0.0 to 1.0)"""
        return self.settings.get("music_volume", 0.7)

    def set_music_volume(self, volume: float):
        """Set music volume (0.0 to 1.0) and apply immediately"""
        volume = max(0.0, min(1.0, volume))
        self.settings["music_volume"] = volume
        self.apply_volume()
        self.save_settings()

    def get_sfx_volume(self) -> float:
        """Get SFX volume (0.0 to 1.0)"""
        return self.settings.get("sfx_volume", 0.7)

    def set_sfx_volume(self, volume: float):
        """Set SFX volume (0.0 to 1.0)"""
        volume = max(0.0, min(1.0, volume))
        self.settings["sfx_volume"] = volume
        # SFX volume will be applied when sounds play
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

    def get_show_fps(self) -> bool:
        """Get show FPS setting"""
        return self.settings.get("show_fps", False)

    def set_show_fps(self, show: bool):
        """Set show FPS setting"""
        self.settings["show_fps"] = bool(show)
        self.save_settings()

    def get_vsync_enabled(self) -> bool:
        """Get VSync enabled setting"""
        return self.settings.get("vsync", True)

    def set_vsync_enabled(self, enabled: bool):
        """Set VSync enabled setting"""
        self.settings["vsync"] = bool(enabled)
        self.save_settings()

    def get_competitive_mode(self) -> bool:
        """Get competitive mode setting (precise timing for LAN games)"""
        return self.settings.get("competitive_mode", False)

    def set_competitive_mode(self, enabled: bool):
        """Set competitive mode setting"""
        self.settings["competitive_mode"] = bool(enabled)
        self.save_settings()

    def get_gpu_enabled(self) -> bool:
        return self.settings.get("gpu_enabled", True)

    def set_gpu_enabled(self, enabled: bool):
        self.settings["gpu_enabled"] = bool(enabled)
        self.save_settings()

    def get_bloom_enabled(self) -> bool:
        return self.settings.get("bloom_enabled", True)

    def set_bloom_enabled(self, enabled: bool):
        self.settings["bloom_enabled"] = bool(enabled)
        self.save_settings()

    def get_bloom_intensity(self) -> float:
        return self.settings.get("bloom_intensity", 0.6)

    def set_bloom_intensity(self, value: float):
        self.settings["bloom_intensity"] = max(0.0, min(1.0, value))
        self.save_settings()

    def get_bloom_threshold(self) -> float:
        return self.settings.get("bloom_threshold", 0.65)

    def set_bloom_threshold(self, value: float):
        self.settings["bloom_threshold"] = max(0.0, min(1.0, value))
        self.save_settings()

    def get_vignette_enabled(self) -> bool:
        return self.settings.get("vignette_enabled", True)

    def set_vignette_enabled(self, enabled: bool):
        self.settings["vignette_enabled"] = bool(enabled)
        self.save_settings()

    def get_shader_quality(self) -> str:
        return self.settings.get("shader_quality", "medium")

    def set_shader_quality(self, quality: str):
        if quality in ("low", "medium", "high"):
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
                    running = False

                # Check sliders
                for name, slider_rect in slider_rects.items():
                    if slider_rect.collidepoint(event.pos):
                        dragging_slider = name
                        # Update value immediately
                        x_rel = (event.pos[0] - slider_rect.x) / slider_rect.width
                        x_rel = max(0.0, min(1.0, x_rel))
                        if name == "master":
                            settings.set_master_volume(x_rel)
                        elif name == "music":
                            settings.set_music_volume(x_rel)
                        elif name == "sfx":
                            settings.set_sfx_volume(x_rel)

            elif event.type == pygame.MOUSEBUTTONUP:
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
            ("sfx", "SFX Volume", settings.get_sfx_volume()),
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

        import display_manager
        display_manager.gpu_flip()
        clock.tick(60)

    return
