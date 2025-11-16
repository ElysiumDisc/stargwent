# Tau'ri Resolute March (Sonic Pi arrangement)
# -------------------------------------------
# Inspired by: "Stargate SG-1 OST - Tau'ri Theme" (https://www.youtube.com/watch?v=gTRIDgH12dE)
# Tempo: 110 BPM. Script ≈ 72 beats (~39s). Record once in Sonic Pi,
# export tauri_theme.wav, then convert with:
#   ffmpeg -i tauri_theme.wav -c:a libvorbis assets/audio/tauri_theme.ogg
# Drop the .ogg into assets/audio to loop it for Tau'ri battles.

use_debug false
use_bpm 110
use_sched_ahead_time 6
set_volume! 1.2

COURAGE_CHORDS = [
  [:d3, :a3, :d4, :f4],
  [:g3, :d4, :g4, :b4],
  [:c3, :g3, :c4, :e4],
  [:d3, :a3, :d4, :f4],
  [:f3, :c4, :f4, :a4],
  [:bb2, :f3, :bb3, :d4],
  [:c3, :g3, :c4, :e4],
  [:d3, :a3, :d4, :f4]
]

DEFENSE_BRASS = [
  [:d4, 1], [:f4, 1], [:a4, 1], [:d5, 1],
  [:c5, 2], [:a4, 2],
  [:g4, 1], [:a4, 1], [:g4, 1], [:f4, 1],
  [:e4, 2], [:d4, 2],
  [:c4, 1], [:d4, 1], [:f4, 1], [:g4, 1],
  [:a4, 2], [:f4, 2],
  [:g4, 2], [:e4, 2], [:d4, 2], [:c4, 2],
  [:bb3, 4], [:rest, 4]
]

HOPEFUL_LINE = [
  [:d5, 1], [:g5, 1], [:a5, 1], [:bb5, 1],
  [:c6, 2], [:a5, 2],
  [:g5, 1], [:a5, 1], [:g5, 1], [:f5, 1],
  [:e5, 2], [:d5, 2],
  [:c5, 1], [:d5, 1], [:f5, 1], [:g5, 1],
  [:a5, 2], [:f5, 2],
  [:g5, 2], [:e5, 2], [:d5, 2], [:c5, 2],
  [:bb4, 4], [:rest, 4]
]

define :play_line do |line, opts|
  opts ||= {}
  synth = opts.fetch(:synth, :prophet)
  amp = opts.fetch(:amp, 1.0)
  cutoff = opts.fetch(:cutoff, 110)
  use_synth synth
  line.each do |note, beats|
    if note == :rest
      sleep beats
    else
      play note,
           sustain: beats * 0.75,
           release: beats * 0.25,
           amp: amp,
           cutoff: cutoff
      sleep beats
    end
  end
end

define :pad_progression do |chords, opts|
  opts ||= {}
  beats = opts.fetch(:beats_per_chord, 4)
  amp = opts.fetch(:amp, 0.45)
  synth = opts.fetch(:synth, :hollow)
  use_synth synth
  chords.each do |ch|
    play_chord ch,
               sustain: beats * 0.95,
               release: 1.1,
               amp: amp
    sleep beats
  end
end

define :tau_percussion do |beats, opts|
  opts ||= {}
  amp = opts.fetch(:amp, 0.4)
  beats.times do |i|
    sample :bd_haus, amp: amp
    sample :elec_hi_snare, rate: 0.7, amp: amp * 0.45 if i.even?
    sleep 1
  end
end

with_fx :reverb, room: 0.8, mix: 0.3 do
  # Section 1 – 16 beats: resolute intro
  pad_progression(COURAGE_CHORDS[0..3], beats_per_chord: 4, amp: 0.5, synth: :dark_ambience)
  play_line(DEFENSE_BRASS, synth: :blade, amp: 0.95, cutoff: 115)
  
  # Section 2 – 16 beats: march forward
  perc_thread = in_thread { tau_percussion(16, amp: 0.35) }
  pad_progression(COURAGE_CHORDS[2..5], beats_per_chord: 4, amp: 0.45, synth: :prophet)
  perc_thread.join
  
  # Section 3 – 24 beats: hopeful swell
  perc_thread = in_thread { tau_percussion(24, amp: 0.4) }
  pad_thread = in_thread { pad_progression(COURAGE_CHORDS, beats_per_chord: 3, amp: 0.4, synth: :hollow) }
  play_line(HOPEFUL_LINE, synth: :dsaw, amp: 1.05, cutoff: 125)
  perc_thread.join
  pad_thread.join
  
  # Section 4 – 16 beats: fade to briefing room
  pad_progression(COURAGE_CHORDS[4..7], beats_per_chord: 4, amp: 0.4, synth: :dark_ambience)
end
