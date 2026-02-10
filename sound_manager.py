"""
Sound effect manager for card-specific audio snippets.
Handles loading, caching, and playing commander audio clips.
"""

import pygame
import os

from game_settings import get_settings


class SoundEffectManager:
    """Manages card-specific sound effects, particularly legendary commander snippets.

    Features:
    - Channel management with reserved channels for critical sounds
    - Audio fadeout for smooth transitions
    - Sound caching for performance
    - Volume control integration with game settings
    """

    COMMANDER_SNIPPETS_PATH = os.path.join("assets", "audio", "commander_snippets")
    ROW_SOUNDS_PATH = os.path.join("assets", "audio")

    # Channel configuration
    NUM_CHANNELS = 16  # Increased from default 8 for complex audio scenarios
    NUM_RESERVED_CHANNELS = 2  # Channels 0-1 reserved for critical sounds (victory/defeat)

    # Default fadeout durations (milliseconds)
    FADE_QUICK = 300
    FADE_NORMAL = 500
    FADE_SLOW = 800

    def __init__(self):
        self._ensure_mixer_ready()
        self.loaded_sounds = {}
        self.settings = get_settings()
        self._reserved_channels = []
        self._setup_channels()

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

    def _setup_channels(self):
        """Configure audio channels with reserved channels for critical sounds."""
        if not pygame.mixer.get_init():
            return

        try:
            # Increase total channels
            pygame.mixer.set_num_channels(self.NUM_CHANNELS)

            # Reserve channels for critical sounds (victory, defeat, important UI)
            pygame.mixer.set_reserved(self.NUM_RESERVED_CHANNELS)

            # Cache reserved channel references
            self._reserved_channels = [
                pygame.mixer.Channel(i)
                for i in range(self.NUM_RESERVED_CHANNELS)
            ]

            print(f"[audio] Configured {self.NUM_CHANNELS} channels, "
                  f"{self.NUM_RESERVED_CHANNELS} reserved for critical sounds")
        except pygame.error as exc:
            print(f"[audio] Channel setup failed: {exc}")

    def get_critical_channel(self, index=0):
        """Get a reserved channel for critical sounds.

        Args:
            index: Which reserved channel (0 or 1)

        Returns:
            pygame.mixer.Channel or None
        """
        if 0 <= index < len(self._reserved_channels):
            return self._reserved_channels[index]
        return None

    def play_critical_sound(self, sound, volume=1.0):
        """Play a sound on a reserved channel (won't be interrupted).

        Args:
            sound: pygame.mixer.Sound object
            volume: Volume level 0.0 to 1.0

        Returns:
            pygame.mixer.Channel or None
        """
        channel = self.get_critical_channel(0)
        if channel and sound:
            try:
                sound.set_volume(self._get_effective_sfx_volume(volume))
                channel.play(sound)
                return channel
            except pygame.error:
                pass
        return None

    def fadeout_all(self, fade_ms=None):
        """Fade out all sound effects.

        Args:
            fade_ms: Fadeout duration in milliseconds (default: FADE_NORMAL)
        """
        if fade_ms is None:
            fade_ms = self.FADE_NORMAL

        if pygame.mixer.get_init():
            try:
                # Fadeout all channels (not music)
                for i in range(pygame.mixer.get_num_channels()):
                    channel = pygame.mixer.Channel(i)
                    if channel.get_busy():
                        channel.fadeout(fade_ms)
            except pygame.error:
                # Fallback to immediate stop
                pygame.mixer.stop()

    def fadeout_sound(self, cache_key, fade_ms=None):
        """Fade out a specific cached sound.

        Args:
            cache_key: Key in loaded_sounds cache
            fade_ms: Fadeout duration in milliseconds
        """
        if fade_ms is None:
            fade_ms = self.FADE_NORMAL

        sound = self.loaded_sounds.get(cache_key)
        if sound:
            try:
                sound.fadeout(fade_ms)
            except pygame.error:
                sound.stop()

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

    def play_symbiote_sound(self, volume=0.8):
        """
        Play Goa'uld symbiote seeking host sound.
        Looks for assets/audio/symbiote.ogg

        Args:
            volume: Volume level from 0.0 to 1.0

        Returns:
            True if sound was played, False otherwise
        """
        sound = self._load_generic_sound("symbiote", "symbiote.ogg")
        if not sound:
            return False
        try:
            sound.set_volume(self._get_effective_sfx_volume(volume))
            sound.play()
            return True
        except pygame.error as exc:
            print(f"[audio] Failed to play symbiote sound: {exc}")
            return False

    def play_asgard_beam_sound(self, volume=0.7):
        """
        Play Asgard transporter beam sound effect.
        Looks for assets/audio/asgard_beamup.ogg

        Args:
            volume: Volume level from 0.0 to 1.0

        Returns:
            True if sound was played, False otherwise
        """
        sound = self._load_generic_sound("asgard_beam", "asgard_beamup.ogg")
        if not sound:
            return False
        try:
            sound.set_volume(self._get_effective_sfx_volume(volume))
            sound.play()
            return True
        except pygame.error as exc:
            print(f"[audio] Failed to play asgard beam sound: {exc}")
            return False

    def play_chat_notification(self, msg_type="peer", volume=0.5):
        """
        Play chat notification sound.
        Looks for assets/audio/chat_notification.ogg.
        Silent fallback if file doesn't exist.

        Args:
            msg_type: "peer" for opponent messages, "system" for system messages
            volume: Volume level from 0.0 to 1.0

        Returns:
            True if sound was played, False otherwise
        """
        cache_key = "chat_notification"
        sound = self._load_generic_sound(cache_key, "chat_notification.ogg")

        # Silent fallback if no sound file exists
        if not sound:
            return False

        try:
            sound.set_volume(self._get_effective_sfx_volume(volume))
            sound.play()
            return True
        except pygame.error as exc:
            print(f"[audio] Failed to play chat notification: {exc}")
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
