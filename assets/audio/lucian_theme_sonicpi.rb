# Lucian Rogue Pulse (Sonic Pi arrangement)
# ----------------------------------------
# Inspired by: "SGU - Lucian Alliance Theme" (https://www.youtube.com/watch?v=bn5s-VTxHNI&list=PLDBI5FsuFMFXOfzb-k7nXwUvkWy07jN5M&index=31)
# Tempo: 102 BPM. Script ≈ 64 beats (~38s). Record once in Sonic Pi,
# export lucian_theme.wav, then convert with:
#   ffmpeg -i lucian_theme.wav -c:a libvorbis assets/audio/lucian_theme.ogg
# Drop the .ogg into assets/audio for future Lucian battle playback.

use_debug false
use_bpm 102
use_sched_ahead_time 6
set_volume! 1.1

NEBULA_CHORDS = [
  [:e2, :b2, :e3, :g3],
  [:d2, :a2, :d3, :f3],
  [:c2, :g2, :c3, :e3],
  [:e2, :b2, :e3, :g3],
  [:g2, :d3, :g3, :bb3],
  [:a2, :e3, :a3, :c4],
  [:c2, :g2, :c3, :e3],
  [:e2, :b2, :e3, :g3]
]

PULSE_LINE = [
  [:e4, 2], [:g4, 2], [:a4, 2], [:c5, 2],
  [:b4, 2], [:a4, 2], [:g4, 2], [:f4, 2],
  [:e4, 2], [:g4, 2], [:a4, 2], [:c5, 2],
  [:b4, 4], [:rest, 4]
]

SMUGGLER_HOOK = [
  [:e5, 1], [:g5, 1], [:b5, 1], [:c6, 1],
  [:d6, 2], [:b5, 2],
  [:a5, 1], [:c6, 1], [:a5, 1], [:g5, 1],
  [:f5, 2], [:e5, 2],
  [:d5, 1], [:e5, 1], [:g5, 1], [:a5, 1],
  [:c6, 2], [:b5, 2],
  [:a5, 2], [:g5, 2], [:e5, 2], [:d5, 2],
  [:c5, 4], [:rest, 4]
]

define :play_line do |line, opts|
  opts ||= {}
  synth = opts.fetch(:synth, :prophet)
  amp = opts.fetch(:amp, 1.0)
  cutoff = opts.fetch(:cutoff, 120)
  use_synth synth
  line.each do |note, beats|
    if note == :rest
      sleep beats
    else
      play note,
           sustain: beats * 0.7,
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

define :lucian_groove do |beats, opts|
  opts ||= {}
  amp = opts.fetch(:amp, 0.45)
  beats.times do |i|
    sample :bd_808, amp: amp
    sample :elec_soft_kick, amp: amp * 0.35 if i % 2 == 1
    sleep 0.5
    sample :elec_cymbal, rate: 1.2, amp: amp * 0.2 if i % 2 == 0
    sleep 0.5
  end
end

with_fx :echo, phase: 0.375, mix: 0.25 do
  # Section 1 – 16 beats: stealth buildup
  pad_progression(NEBULA_CHORDS[0..3], beats_per_chord: 4, amp: 0.45, synth: :dark_ambience)
  play_line(PULSE_LINE, synth: :blade, amp: 0.8, cutoff: 120)
  
  # Section 2 – 16 beats: rogue pulse
  groove_thread = in_thread { lucian_groove(16, amp: 0.4) }
  pad_progression(NEBULA_CHORDS[2..5], beats_per_chord: 4, amp: 0.4, synth: :prophet)
  groove_thread.join
  
  # Section 3 – 20 beats: smuggler hook
  groove_thread = in_thread { lucian_groove(20, amp: 0.45) }
  pad_thread = in_thread { pad_progression(NEBULA_CHORDS, beats_per_chord: 5, amp: 0.35, synth: :dark_ambience) }
  play_line(SMUGGLER_HOOK, synth: :dsaw, amp: 1.0, cutoff: 125)
  groove_thread.join
  pad_thread.join
  
  # Section 4 – 12 beats: fade into hyperspace
  pad_progression(NEBULA_CHORDS[4..7], beats_per_chord: 3, amp: 0.35, synth: :hollow)
end
