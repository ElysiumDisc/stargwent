STARGWENT AUDIO FILES
=====================

Audio Format: OGG Vorbis (best for Pygame)
Fallback: MP3 or WAV

Required Audio Files:
---------------------

MENU MUSIC:
- main_menu_music.ogg - Looping menu theme (Stargate-inspired ambient)

GAME MUSIC:
- battle_round1.ogg - Round 1 battle music
- battle_round2.ogg - Round 2 music (more intense)
- battle_round3.ogg - Round 3 music (most intense)

SOUND EFFECTS:
- stargate_open.ogg - Stargate activation/kawoosh
- stargate_swoosh.ogg - Stargate vortex spiral
- card_play.ogg - Card placement sound
- card_draw.ogg - Drawing card sound
- power_activate.ogg - Generic power activation
- iris_close.ogg - Iris deployment (metal slamming)
- explosion.ogg - Explosion for Tau'ri power
- ring_transport.ogg - Ring transporter effect
- hyperspace_enter.ogg - Entering hyperspace
- hyperspace_exit.ogg - Exiting hyperspace  
- round_win.ogg - Win round sound
- round_lose.ogg - Lose round sound
- game_victory.ogg - Victory theme
- game_defeat.ogg - Defeat theme

FACTION POWER EFFECTS:
- power_tauri_destruction.ogg - Fire explosion
- power_goauld_revival.ogg - Golden energy
- power_lucian_naquadah.ogg - Green energy wave
- power_jaffa_aid.ogg - Stealth cloak whoosh
- power_asgard_swap.ogg - Blue transference

Note: All files should be normalized to similar volume levels.
Menu theme plays once per visit and will only restart every ~30 seconds. Battle themes play once, go silent for ~2 minutes, then restart if the match is still running. Drop any `.ogg` files listed below whenever you're ready for that faction's loop.

SONIC PI SOURCE:
- main_menu_theme_sonicpi.rb - 63-second Sonic Pi recreation of the Stargate SG-1 title cue.
  * Record once in Sonic Pi (`main_menu_theme.wav`) then convert with `ffmpeg -i main_menu_theme.wav -c:a libvorbis main_menu_music.ogg`.
  * Place the exported `.ogg` in this folder so `main_menu.py` can loop it automatically.
- goauld_theme_sonicpi.rb - 43-second Sonic Pi take matching the Goa'uld dark ascension cue (90 BPM).
  * Record to `goauld_theme.wav`, then `ffmpeg -i goauld_theme.wav -c:a libvorbis goauld_theme.ogg`.
  * Drop `goauld_theme.ogg` here so `main.py` can loop it whenever the player selects the Goa'uld faction.
- asgard_theme_sonicpi.rb - 45-second Sonic Pi arrangement matching the Asgard victory theme (96 BPM).
  * Record to `asgard_theme.wav`, then `ffmpeg -i asgard_theme.wav -c:a libvorbis asgard_theme.ogg`.
  * Place `asgard_theme.ogg` alongside the others so Asgard battles auto-loop it.
- goauld_theme_sonicpi.rb - 43-second Sonic Pi take matching the Goa'uld dark ascension cue (90 BPM).
  * Record to `goauld_theme.wav`, then `ffmpeg -i goauld_theme.wav -c:a libvorbis goauld_theme.ogg`.
  * Drop `goauld_theme.ogg` here so `main.py` can loop it whenever the player selects the Goa'uld faction.
- tauri_theme_sonicpi.rb - 39-second Sonic Pi recreation of the Tau'ri march (110 BPM).
  * Record to `tauri_theme.wav`, then `ffmpeg -i tauri_theme.wav -c:a libvorbis tauri_theme.ogg`.
  * Place `tauri_theme.ogg` here so Tau'ri battles can switch to it once playback hooks are added.
- jaffa_theme_sonicpi.rb - 39-second Sonic Pi chant for the Jaffa (92 BPM).
  * Record to `jaffa_theme.wav`, then `ffmpeg -i jaffa_theme.wav -c:a libvorbis jaffa_theme.ogg`.
  * Keep `jaffa_theme.ogg` here to plug it in when Jaffa battle music hooks arrive.
- lucian_theme_sonicpi.rb - 38-second Sonic Pi rogue pulse for the Lucian Alliance (102 BPM).
  * Record to `lucian_theme.wav`, then `ffmpeg -i lucian_theme.wav -c:a libvorbis lucian_theme.ogg`.
  * Store `lucian_theme.ogg` here for when Lucian battle music selection is implemented.
