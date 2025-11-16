# Jaffa Unbroken Chant (Sonic Pi arrangement)
# -------------------------------------------
# Inspired by: "Stargate - Jaffa Theme" (https://www.youtube.com/watch?v=tpHw0mLA1Vo)
# Tempo: 92 BPM. Script ≈ 60 beats (~39s). Record once in Sonic Pi,
# export jaffa_theme.wav, then convert with:
#   ffmpeg -i jaffa_theme.wav -c:a libvorbis assets/audio/jaffa_theme.ogg
# Drop the .ogg into assets/audio to loop it for future Jaffa battle playback.

use_debug false
use_bpm 92
use_sched_ahead_time 6
set_volume! 1.1

SPEAR_CHORDS = [
  [:d2, :a2, :d3, :f3],
  [:c2, :g2, :c3, :e3],
  [:bb1, :f2, :bb2, :d3],
  [:d2, :a2, :d3, :f3],
  [:f2, :c3, :f3, :a3],
  [:g2, :d3, :g3, :bb3],
  [:c2, :g2, :c3, :e3],
  [:d2, :a2, :d3, :f3]
]

CHANT_LINE = [
  [:d4, 2], [:f4, 2], [:g4, 2], [:a4, 2],
  [:bb4, 2], [:a4, 2], [:g4, 2], [:f4, 2],
  [:e4, 2], [:g4, 2], [:a4, 2], [:bb4, 2],
  [:a4, 4], [:rest, 4]
]

HONOR_FANFARE = [
  [:d5, 1], [:f5, 1], [:a5, 1], [:bb5, 1],
  [:c6, 2], [:a5, 2],
  [:g5, 1], [:a5, 1], [:g5, 1], [:f5, 1],
  [:e5, 2], [:d5, 2],
  [:c5, 1], [:d5, 1], [:f5, 1], [:g5, 1],
  [:bb5, 2], [:a5, 2],
  [:g5, 2], [:f5, 2], [:d5, 2], [:c5, 2],
  [:bb4, 4], [:rest, 4]
]

define :play_line do |line, opts|
  opts ||= {}
  synth = opts.fetch(:synth, :prophet)
  amp = opts.fetch(:amp, 1.0)
  cutoff = opts.fetch(:cutoff, 105)
  use_synth synth
  line.each do |note, beats|
    if note == :rest
      sleep beats
    else
      play note,
           sustain: beats * 0.75,
           release: beats * 0.3,
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
  synth = opts.fetch(:synth, :dark_ambience)
  use_synth synth
  chords.each do |ch|
    play_chord ch,
               sustain: beats * 0.9,
               release: 0.9,
               amp: amp
    sleep beats
  end
end

define :jaffa_drums do |beats, opts|
  opts ||= {}
  amp = opts.fetch(:amp, 0.45)
  beats.times do |i|
    sample :bd_zome, amp: amp
    sample :drum_bass_soft, amp: amp * 0.35 if i % 2 == 1
    sleep 1
  end
end

with_fx :reverb, room: 0.85, mix: 0.35 do
  # Section 1 – 16 beats: solemn chant
  pad_progression(SPEAR_CHORDS[0..3], beats_per_chord: 4, amp: 0.45, synth: :hollow)
  play_line(CHANT_LINE, synth: :blade, amp: 0.85, cutoff: 110)
  
  # Section 2 – 16 beats: march of honor
  drum_thread = in_thread { jaffa_drums(16, amp: 0.4) }
  pad_progression(SPEAR_CHORDS[2..5], beats_per_chord: 4, amp: 0.4, synth: :prophet)
  drum_thread.join
  
  # Section 3 – 16 beats: fanfare rise
  drum_thread = in_thread { jaffa_drums(16, amp: 0.45) }
  pad_thread = in_thread { pad_progression(SPEAR_CHORDS, beats_per_chord: 4, amp: 0.4, synth: :dark_ambience) }
  play_line(HONOR_FANFARE, synth: :dsaw, amp: 1.0, cutoff: 115)
  drum_thread.join
  pad_thread.join
  
  # Section 4 – 12 beats: fade to silence
  pad_progression(SPEAR_CHORDS[4..7], beats_per_chord: 3, amp: 0.35, synth: :hollow)
end
