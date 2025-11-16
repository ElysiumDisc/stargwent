# Asgard Victory March (Sonic Pi arrangement)
# -------------------------------------------
# Inspired by: "Stargate - Asgard Theme" (https://www.youtube.com/watch?v=6gB3QZR3iWk)
# Tempo: 96 BPM. Script length ≈ 72 beats (45s). Record once in Sonic Pi
# as asgard_theme.wav then convert with:
#   ffmpeg -i asgard_theme.wav -c:a libvorbis assets/audio/asgard_theme.ogg
# Drop the .ogg into assets/audio so the Asgard faction loop finds it.

use_debug false
use_bpm 96
use_sched_ahead_time 6
set_volume! 1.2

VALHALLA_PADS = [
  [:g3, :d4, :g4, :b4],
  [:c3, :g3, :c4, :e4],
  [:bb2, :f3, :bb3, :d4],
  [:g3, :d4, :g4, :b4],
  [:d3, :a3, :d4, :f4],
  [:c3, :g3, :c4, :e4],
  [:bb2, :f3, :bb3, :d4],
  [:g3, :d4, :g4, :b4]
]

CRYSTAL_ARP = [
  [:g5, 1], [:b5, 1], [:d6, 1], [:g5, 1],
  [:f5, 1], [:a5, 1], [:c6, 1], [:f5, 1],
  [:e5, 1], [:g5, 1], [:c6, 1], [:e5, 1],
  [:d5, 1], [:f5, 1], [:bb5, 1], [:d5, 1]
]

GLIDER_MELODY = [
  [:g4, 1], [:b4, 1], [:d5, 1], [:g5, 1],
  [:f5, 2], [:d5, 2],
  [:c5, 1], [:d5, 1], [:c5, 1], [:b4, 1],
  [:a4, 2], [:g4, 2],
  [:bb4, 1], [:c5, 1], [:d5, 1], [:f5, 1],
  [:e5, 2], [:c5, 2],
  [:d5, 2], [:bb4, 2], [:a4, 2], [:g4, 2],
  [:f4, 4], [:rest, 4]
]

HEIMDALL_LINE = [
  [:g4, 2], [:b4, 2], [:d5, 2], [:g5, 2],
  [:f5, 4], [:rest, 4],
  [:e5, 2], [:d5, 2], [:c5, 2], [:a4, 2],
  [:g4, 4], [:rest, 4]
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
  amp = opts.fetch(:amp, 0.4)
  synth = opts.fetch(:synth, :hollow)
  use_synth synth
  chords.each do |ch|
    play_chord ch,
               sustain: beats * 0.9,
               release: 0.8,
               amp: amp
    sleep beats
  end
end

define :asgard_percussion do |beats, opts|
  opts ||= {}
  amp = opts.fetch(:amp, 0.35)
  beats.times do |i|
    sample :bd_zum, amp: amp
    sample :drum_cymbal_pedal, amp: amp * 0.3 if i % 4 == 2
    sleep 1
  end
end

with_fx :reverb, room: 0.85, mix: 0.35 do
  # Section 1 – 16 beats: crystalline intro
  pad_progression(VALHALLA_PADS[0..3], beats_per_chord: 4, amp: 0.45, synth: :dark_ambience)
  play_line(CRYSTAL_ARP, synth: :pretty_bell, amp: 0.5, cutoff: 125)
  
  # Section 2 – 16 beats: honor march
  perc_thread = in_thread { asgard_percussion(16, amp: 0.35) }
  pad_thread = in_thread { pad_progression(VALHALLA_PADS[2..5], beats_per_chord: 4, amp: 0.4, synth: :hollow) }
  play_line(GLIDER_MELODY, synth: :blade, amp: 0.9, cutoff: 120)
  perc_thread.join
  pad_thread.join
  
  # Section 3 – 24 beats: triumphant swell
  perc_thread = in_thread { asgard_percussion(24, amp: 0.4) }
  pad_thread = in_thread { pad_progression(VALHALLA_PADS, beats_per_chord: 3, amp: 0.45, synth: :prophet) }
  play_line(HEIMDALL_LINE, synth: :dsaw, amp: 1.0, cutoff: 125)
  perc_thread.join
  pad_thread.join
  
  # Section 4 – 16 beats: fade into hyperspace
  pad_progression(VALHALLA_PADS[4..7], beats_per_chord: 4, amp: 0.35, synth: :dark_ambience)
end
