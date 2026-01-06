"""
Sound effect manager for card-specific audio snippets.
Handles loading, caching, and playing commander audio clips.
"""

import pygame
import os

from game_settings import get_settings


class SoundEffectManager:
    """Manages card-specific sound effects, particularly legendary commander snippets."""

    COMMANDER_SNIPPETS_PATH = os.path.join("assets", "audio", "commander_snippets")
    ROW_SOUNDS_PATH = os.path.join("assets", "audio")

    def __init__(self):
        self._ensure_mixer_ready()
        self.loaded_sounds = {}
        self.settings = get_settings()

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

    def _get_effective_sfx_volume(self, requested_volume: float) -> float:
        """Scale requested volume by the user's settings."""
        base_volume = 1.0
        if self.settings:
            try:
                base_volume = self.settings.get_effective_sfx_volume()
            except AttributeError:
                base_volume = self.settings.get_master_volume()
        final_volume = max(0.0, min(1.0, requested_volume * base_volume))
        return final_volume

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
                sound.set_volume(self._get_effective_sfx_volume(volume))
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
                sound.set_volume(self._get_effective_sfx_volume(volume))
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
            sound.set_volume(self._get_effective_sfx_volume(volume))
            sound.play()
            return True
        except pygame.error as exc:
            print(f"[audio] Failed to play ring transport sound: {exc}")
        return False

    def _load_generic_sound(self, cache_key, filename):
        """Helper to load a one-off sound with caching (no fallbacks)."""
        if cache_key in self.loaded_sounds:
            return self.loaded_sounds[cache_key]
        sound_path = os.path.join(self.ROW_SOUNDS_PATH, filename)
        if not os.path.exists(sound_path):
            return None
        try:
            self.loaded_sounds[cache_key] = pygame.mixer.Sound(sound_path)
            return self.loaded_sounds[cache_key]
        except pygame.error as exc:
            print(f"[audio] Failed to load {filename}: {exc}")
            return None

    def play_weather_sound(self, weather_key="generic", volume=1.0):
        """
        Play a weather-related sound. Looks for assets/audio/weather_<key>.ogg.
        No fallback; silent if missing.
        """
        key = weather_key.lower().replace(" ", "_")
        cache_key = f"weather_{key}"
        sound = self._load_generic_sound(cache_key, f"weather_{key}.ogg")
        if not sound:
            return False
        try:
            sound.set_volume(self._get_effective_sfx_volume(volume))
            sound.play()
            return True
        except pygame.error as exc:
            print(f"[audio] Failed to play weather sound {key}: {exc}")
            return False

    def play_horn_sound(self, volume=1.0):
        """
        Play Commander Horn sound from assets/audio/horn.ogg.
        No fallback; silent if missing.
        """
        sound = self._load_generic_sound("horn", "horn.ogg")
        if not sound:
            return False
        try:
            sound.set_volume(self._get_effective_sfx_volume(volume))
            sound.play()
            return True
        except pygame.error as exc:
            print(f"[audio] Failed to play horn sound: {exc}")
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
            sound.set_volume(self._get_effective_sfx_volume(volume))
            sound.play()
            return True
        except pygame.error as exc:
            print(f"[audio] Failed to play iris sound: {exc}")
        return False

    def get_leader_voice_sound(self, leader_id):
        """
        Get or load a leader voice snippet by leader card ID.
        Looks for assets/audio/leader_voices/<leader_id>.ogg

        Args:
            leader_id: The leader's card ID (e.g., 'tauri_oneill', 'jaffa_tealc')

        Returns:
            pygame.mixer.Sound object or None if not found/loadable
        """
        cache_key = f"leader_voice_{leader_id}"
        if cache_key in self.loaded_sounds:
            return self.loaded_sounds[cache_key]

        # Try leader_voices subfolder first, then commander_snippets as fallback
        voice_paths = [
            os.path.join(self.ROW_SOUNDS_PATH, "leader_voices", f"{leader_id}.ogg"),
            os.path.join(self.COMMANDER_SNIPPETS_PATH, f"{leader_id}.ogg"),
        ]

        for sound_path in voice_paths:
            if os.path.exists(sound_path):
                try:
                    sound = pygame.mixer.Sound(sound_path)
                    self.loaded_sounds[cache_key] = sound
                    return sound
                except pygame.error as exc:
                    print(f"[audio] Failed to load leader voice {leader_id}: {exc}")
                    return None

        # Silent fail - voice file not yet created
        return None

    def play_leader_voice(self, leader_id, volume=0.8):
        """
        Play a leader voice snippet when hovering/selecting in draft mode.

        Args:
            leader_id: The leader's card ID (e.g., 'tauri_oneill')
            volume: Volume level from 0.0 to 1.0

        Returns:
            True if sound was played, False otherwise
        """
        sound = self.get_leader_voice_sound(leader_id)
        if sound:
            try:
                # Stop any currently playing leader voice to avoid overlap
                sound.stop()
                sound.set_volume(self._get_effective_sfx_volume(volume))
                sound.play()
                return True
            except pygame.error as exc:
                print(f"[audio] Failed to play leader voice {leader_id}: {exc}")
        return False

    def stop_leader_voice(self, leader_id=None):
        """
        Stop a specific leader voice or all leader voices.

        Args:
            leader_id: Specific leader to stop, or None to stop all
        """
        if leader_id:
            cache_key = f"leader_voice_{leader_id}"
            if cache_key in self.loaded_sounds:
                try:
                    self.loaded_sounds[cache_key].stop()
                except pygame.error:
                    pass
        else:
            # Stop all leader voices
            for key, sound in self.loaded_sounds.items():
                if key.startswith("leader_voice_"):
                    try:
                        sound.stop()
                    except pygame.error:
                        pass

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
