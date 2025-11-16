"""
Game Settings System for Stargwent
Handles persistent game settings like volume, controls, etc.
"""
import json
import os
import pygame

SETTINGS_FILE = "game_settings.json"

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


# Global settings instance
_settings_instance = None

def get_settings() -> GameSettings:
    """Get the global settings instance"""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = GameSettings()
    return _settings_instance
