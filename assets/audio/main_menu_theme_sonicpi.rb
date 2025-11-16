# Stargwent Main Menu Theme (Sonic Pi arrangement)
# -----------------------------------------------
# Based on: "Stargate SG-1: Main Title" (1:03)
# Tempo: 120 BPM (126 beats ≈ 63s). Run once and record/export to WAV,
# then convert to OGG (e.g., `ffmpeg -i main_menu_theme.wav -c:a libvorbis main_menu_music.ogg`)
# and drop into assets/audio/main_menu_music.ogg for the game.

use_debug false
use_bpm 120
use_sched_ahead_time 2.0
set_volume! 2

INTRO_CHORDS = [
  [:d2, :a2, :d3, :f3],
  [:bb1, :f2, :bb2, :d3],
  [:c2, :g2, :c3, :e3],
  [:d2, :a2, :d3, :f3],
  [:g1, :d2, :g2, :bb2],
  [:d2, :a2, :d3, :f3]
]

THEME_PAD_CHORDS = [
  [:d3, :a3, :d4, :f4],
  [:bb2, :f3, :bb3, :d4],
  [:c3, :g3, :c4, :e4],
  [:d3, :a3, :d4, :f4],
  [:g2, :d3, :g3, :bb3],
  [:d3, :a3, :d4, :f4],
  [:f3, :c4, :f4, :a4],
  [:c3, :g3, :c4, :e4],
  [:bb2, :f3, :bb3, :d4],
  [:g2, :d3, :g3, :bb3],
  [:d3, :a3, :d4, :f4]
]

CODA_PAD_CHORDS = [
  [:d3, :a3, :d4, :f4],
  [:bb2, :f3, :bb3, :d4],
  [:c3, :g3, :c4, :e4],
  [:d3, :a3, :d4, :f4],
  [:g2, :d3, :g3, :bb3],
  [:f3, :c4, :f4, :a4],
  [:c3, :g3, :c4, :e4],
  [:bb2, :f3, :bb3, :d4],
  [:d3, :a3, :d4, :f4]
]

BUILD_LINE = [
  [:d2, 4], [:bb1, 4], [:c2, 4],
  [:d2, 4], [:g1, 4], [:d2, 2]
]

MAIN_THEME_LINE = [
  [:d4, 1], [:f4, 1], [:g4, 1], [:a4, 1],
  [:c5, 2], [:a4, 2],
  [:g4, 1], [:a4, 1], [:g4, 1], [:f4, 1],
  [:e4, 2], [:c4, 2],
  [:d4, 1], [:f4, 1], [:g4, 1], [:a4, 1],
  [:c5, 2], [:d5, 2],
  [:f5, 2], [:e5, 2], [:d5, 2], [:c5, 2],
  [:a4, 2], [:g4, 2],
  [:d5, 4], [:rest, 4]
]

CODA_LINE = [
  [:g4, 2], [:a4, 2],
  [:bb4, 4],
  [:a4, 2], [:g4, 2],
  [:f4, 2], [:g4, 2], [:a4, 2], [:d4, 2],
  [:a3, 2], [:d4, 2], [:f4, 2], [:g4, 2],
  [:a4, 4], [:d4, 4]
]

define :play_line do |line, opts|
  opts = {} if opts.nil?
  synth = opts.fetch(:synth, :prophet)
  amp = opts.fetch(:amp, 1.0)
  cutoff = opts.fetch(:cutoff, 100)
  use_synth synth
  line.each do |note, beats|
    if note == :rest
      sleep beats
    else
      play note,
           sustain: beats * 0.8,
           release: beats * 0.4,
           amp: amp,
           cutoff: cutoff
      sleep beats
    end
  end
end

define :pad_progression do |chords, opts|
  opts = {} if opts.nil?
  beats_per_chord = opts.fetch(:beats_per_chord, 4)
  amp = opts.fetch(:amp, 0.55)
  synth = opts.fetch(:synth, :hollow)
  use_synth synth
  chords.each do |ch|
    play_chord ch,
               sustain: beats_per_chord * 0.9,
               release: 1.2,
               amp: amp
    sleep beats_per_chord
  end
end

define :gate_percussion do |beats, opts|
  opts = {} if opts.nil?
  amp = opts.fetch(:amp, 0.6)
  beats.times do |i|
    sample :bd_zome, amp: amp if i.even?
    sample :elec_mid_snare, rate: 0.7, amp: amp * 0.45 if i % 4 == 2
    sleep 1
  end
end

define :string_ostinato do |beats, pattern|
  use_synth :blade
  beats.times do |i|
    note = pattern[i % pattern.length]
    play note,
         sustain: 0.4,
         release: 0.15,
         amp: 0.65,
         cutoff: 105
    sleep 1
  end
end

with_fx :reverb, room: 0.9, mix: 0.45 do
  # Section 1 - 24 beats (12s) - Ethereal gate reveal
  pad_progression(INTRO_CHORDS, beats_per_chord: 4, amp: 0.65, synth: :hollow)

  # Section 2 - 22 beats (11s) - Chevron locks + ostinato
  build_threads = []
  build_threads << in_thread { gate_percussion(22, amp: 0.6) }
  build_threads << in_thread { string_ostinato(22, [:d4, :a3, :d4, :f4]) }
  play_line(BUILD_LINE, synth: :fm, amp: 0.7, cutoff: 90)
  build_threads.each(&:join)

  # Section 3 - 44 beats (22s) - Main statement
  theme_threads = []
  theme_threads << in_thread { gate_percussion(44, amp: 0.8) }
  theme_threads << in_thread { pad_progression(THEME_PAD_CHORDS, beats_per_chord: 4, amp: 0.55, synth: :dark_ambience) }
  play_line(MAIN_THEME_LINE, synth: :prophet, amp: 1.15, cutoff: 120)
  theme_threads.each(&:join)

  # Section 4 - 36 beats (18s) - Heroic brass coda
  coda_threads = []
  coda_threads << in_thread { gate_percussion(36, amp: 0.7) }
  coda_threads << in_thread { pad_progression(CODA_PAD_CHORDS, beats_per_chord: 4, amp: 0.6, synth: :fm) }
  play_line(CODA_LINE, synth: :hoover, amp: 1.1, cutoff: 120)
  coda_threads.each(&:join)
end
