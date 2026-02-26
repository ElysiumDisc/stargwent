import pygame
import os
import sys
from game_settings import get_settings

# Round-based battle music (increases intensity each round)
ROUND_BATTLE_MUSIC = {
    1: os.path.join("assets", "audio", "battle_round1.ogg"),
    2: os.path.join("assets", "audio", "battle_round2.ogg"),
    3: os.path.join("assets", "audio", "battle_round3.ogg"),
}
_current_battle_music = None
_current_music_round = None
_next_music_allowed_at = 0
_battle_music_cooldown_ms = 120000


def _ensure_mixer_ready():
    if pygame.mixer.get_init():
        return True
    try:
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
        return True
    except pygame.error as exc:
        print(f"[audio] Unable to init mixer: {exc}")
        return False


def _play_battle_theme(round_number, *, force=False):
    """Internal helper that plays the round track once if cooldown allows."""
    global _current_battle_music, _next_music_allowed_at
    if round_number is None:
        return False
    music_path = ROUND_BATTLE_MUSIC.get(round_number)
    if not music_path:
        return False
    if not os.path.exists(music_path):
        print(f"[audio] Battle music missing for round {round_number}: {music_path}")
        return False
    now = pygame.time.get_ticks()
    if not force and now < _next_music_allowed_at:
        return False
    if not _ensure_mixer_ready():
        return False
    try:
        pygame.mixer.music.load(music_path)
        # Get volume from settings
        settings = get_settings()
        volume = settings.get_effective_music_volume()
        pygame.mixer.music.set_volume(volume)
        pygame.mixer.music.play(-1)  # Loop the battle music
        _current_battle_music = music_path
        _next_music_allowed_at = now + _battle_music_cooldown_ms
        print(f"[audio] Battle music playing for round {round_number}: {music_path} at volume {volume:.2f}")
        return True
    except (pygame.error, Exception) as exc:
        print(f"[audio] Unable to play battle music ({music_path}): {exc}")
        return False


def set_battle_music_round(round_number, *, immediate=False):
    """Select which round music should be considered for playback."""
    global _current_music_round, _next_music_allowed_at
    if round_number == _current_music_round:
        if immediate:
            _play_battle_theme(round_number, force=True)
        return
    # On web, fadeout() immediately followed by load() on a new track can crash
    # the Emscripten audio backend.  Just stop instantly (no fade) then let
    # update_battle_music() pick it up on the next frame.
    if sys.platform == "emscripten":
        if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass
        _current_battle_music = None
        _current_music_round = round_number
        _next_music_allowed_at = 0
        return
    stop_battle_music()
    _current_music_round = round_number
    _next_music_allowed_at = 0
    if round_number:
        _play_battle_theme(round_number, force=True)


def update_battle_music():
    """Call regularly to restart music respecting the cooldown."""
    global _current_music_round
    if not _current_music_round:
        return
    if not pygame.mixer.get_init():
        return
    if pygame.mixer.music.get_busy():
        return
    _play_battle_theme(_current_music_round)


def stop_battle_music(fade_ms=800):
    """Stop any playing battle theme and clear the round."""
    global _current_battle_music, _current_music_round
    if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
        try:
            if sys.platform == "emscripten":
                pygame.mixer.music.stop()
            else:
                pygame.mixer.music.fadeout(fade_ms)
        except (pygame.error, Exception):
            pygame.mixer.music.stop()
    if _current_battle_music:
        print(f"[audio] Battle music stopped ({_current_battle_music})")
    _current_battle_music = None
    _current_music_round = None
