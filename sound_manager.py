"""
Sound effect manager for card-specific audio snippets.
Handles loading, caching, and playing commander audio clips.
"""

import pygame
import os


class SoundEffectManager:
    """Manages card-specific sound effects, particularly legendary commander snippets."""

    COMMANDER_SNIPPETS_PATH = os.path.join("assets", "audio", "commander_snippets")
    ROW_SOUNDS_PATH = os.path.join("assets", "audio")

    def __init__(self):
        self._ensure_mixer_ready()
        self.loaded_sounds = {}

    def _ensure_mixer_ready(self):
        """Initialize pygame mixer if not already done."""
        if pygame.mixer.get_init():
            return True
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
            return True
        except pygame.error as exc:
            print(f"[audio] Unable to init mixer for sound effects: {exc}")
            return False

    def get_commander_sound(self, card_id):
        """
        Get or load a commander snippet by card ID.

        Args:
            card_id: The card's ID (e.g., 'tauri_oneill')

        Returns:
            pygame.mixer.Sound object or None if not found/loadable
        """
        if card_id in self.loaded_sounds:
            return self.loaded_sounds[card_id]

        sound_path = os.path.join(
            self.COMMANDER_SNIPPETS_PATH,
            f"{card_id}.ogg"
        )

        if not os.path.exists(sound_path):
            # Silent fail - audio file not yet created
            return None

        try:
            sound = pygame.mixer.Sound(sound_path)
            self.loaded_sounds[card_id] = sound
            return sound
        except pygame.error as exc:
            print(f"[audio] Failed to load {card_id} snippet: {exc}")
            return None

    def play_commander_snippet(self, card_id, volume=1.0):
        """
        Play a commander snippet when card is played.

        Args:
            card_id: The card's ID (e.g., 'tauri_oneill')
            volume: Volume level from 0.0 to 1.0

        Returns:
            True if sound was played, False otherwise
        """
        sound = self.get_commander_sound(card_id)
        if sound:
            try:
                sound.set_volume(volume)
                sound.play()
                return True
            except pygame.error as exc:
                print(f"[audio] Failed to play {card_id} snippet: {exc}")
        return False

    def get_row_sound(self, row_type):
        """
        Get or load a row type sound (close, ranged, siege).

        Args:
            row_type: The row type ('close', 'ranged', 'siege')

        Returns:
            pygame.mixer.Sound object or None if not found/loadable
        """
        cache_key = f"row_{row_type}"
        if cache_key in self.loaded_sounds:
            return self.loaded_sounds[cache_key]

        sound_path = os.path.join(
            self.ROW_SOUNDS_PATH,
            f"{row_type}.ogg"
        )

        if not os.path.exists(sound_path):
            return None

        try:
            sound = pygame.mixer.Sound(sound_path)
            self.loaded_sounds[cache_key] = sound
            return sound
        except pygame.error as exc:
            print(f"[audio] Failed to load {row_type} sound: {exc}")
            return None

    def play_row_sound(self, row_type, volume=1.0):
        """
        Play a row type sound when a unit card is played.

        Args:
            row_type: The row type ('close', 'ranged', 'siege')
            volume: Volume level from 0.0 to 1.0

        Returns:
            True if sound was played, False otherwise
        """
        # Normalize row type (agile cards go to close or ranged)
        if row_type not in ('close', 'ranged', 'siege'):
            return False

        sound = self.get_row_sound(row_type)
        if sound:
            try:
                sound.set_volume(volume)
                sound.play()
                return True
            except pygame.error as exc:
                print(f"[audio] Failed to play {row_type} sound: {exc}")
        return False

    def play_ring_transport_sound(self, volume=1.0):
        """
        Play ring transport sound when a Ring Transport card is used.
        Always plays (not throttled).

        Args:
            volume: Volume level from 0.0 to 1.0

        Returns:
            True if sound was played, False otherwise
        """
        cache_key = "ring_transport"
        if cache_key not in self.loaded_sounds:
            sound_path = os.path.join(self.ROW_SOUNDS_PATH, "ring.ogg")
            if not os.path.exists(sound_path):
                return False
            try:
                self.loaded_sounds[cache_key] = pygame.mixer.Sound(sound_path)
            except pygame.error as exc:
                print(f"[audio] Failed to load ring transport sound: {exc}")
                return False

        sound = self.loaded_sounds[cache_key]
        try:
            sound.set_volume(volume)
            sound.play()
            return True
        except pygame.error as exc:
            print(f"[audio] Failed to play ring transport sound: {exc}")
        return False

    def play_iris_sound(self, volume=1.0):
        """
        Play iris sound when Tau'ri faction power is used.
        Always plays (not throttled).

        Args:
            volume: Volume level from 0.0 to 1.0

        Returns:
            True if sound was played, False otherwise
        """
        cache_key = "iris"
        if cache_key not in self.loaded_sounds:
            sound_path = os.path.join(self.ROW_SOUNDS_PATH, "iris.ogg")
            if not os.path.exists(sound_path):
                return False
            try:
                self.loaded_sounds[cache_key] = pygame.mixer.Sound(sound_path)
            except pygame.error as exc:
                print(f"[audio] Failed to load iris sound: {exc}")
                return False

        sound = self.loaded_sounds[cache_key]
        try:
            sound.set_volume(volume)
            sound.play()
            return True
        except pygame.error as exc:
            print(f"[audio] Failed to play iris sound: {exc}")
        return False

    def preload_all_commander_sounds(self):
        """
        Preload all commander snippets to avoid lag during gameplay.
        Call this during game initialization.
        """
        if not os.path.exists(self.COMMANDER_SNIPPETS_PATH):
            return

        for filename in os.listdir(self.COMMANDER_SNIPPETS_PATH):
            if filename.endswith('.ogg'):
                card_id = filename[:-4]  # Remove .ogg extension
                self.get_commander_sound(card_id)

    def stop_all_effects(self):
        """Stop all currently playing sound effects."""
        try:
            pygame.mixer.stop()
        except pygame.error:
            pass

    def clear_cache(self):
        """Clear all cached sounds to free memory."""
        self.loaded_sounds.clear()


# Global instance for easy access
_sound_manager = None


def get_sound_manager():
    """Get the global SoundEffectManager instance."""
    global _sound_manager
    if _sound_manager is None:
        _sound_manager = SoundEffectManager()
    return _sound_manager
