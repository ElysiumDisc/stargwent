# Goa'uld Dark Ascension (Sonic Pi arrangement)
# ----------------------------------------------
# Inspired by: "Stargate SG-1 - Goa'uld Theme" (https://www.youtube.com/watch?v=E4FXbPEkGpM&t=91s)
# Tempo: 90 BPM. Script length ≈ 64 beats (~43s). Record once in Sonic Pi,
# export goauld_theme.wav, then run:
#   ffmpeg -i goauld_theme.wav -c:a libvorbis assets/audio/goauld_theme.ogg
# Drop the OGG into assets/audio so the Goa'uld faction battle loop can play it.

use_debug false
use_bpm 90
use_sched_ahead_time 6
set_volume! 1.2

OBELISK_CHORDS = [
  [:d2, :a2, :d3, :f3],
  [:c2, :g2, :c3, :e3],
  [:bb1, :f2, :bb2, :d3],
  [:d2, :a2, :d3, :f3],
  [:g1, :d2, :g2, :bb2],
  [:c2, :g2, :c3, :e3],
  [:bb1, :f2, :bb2, :d3],
  [:d2, :a2, :d3, :f3]
]

SERPENT_HUM = [
  [:d4, 2], [:f4, 2], [:g4, 2], [:a4, 2],
  [:bb4, 2], [:a4, 2], [:g4, 2], [:f4, 2],
  [:e4, 2], [:f4, 2], [:g4, 2], [:bb4, 2],
  [:a4, 4], [:rest, 4]
]

SARCOPHAGUS_LINE = [
  [:d5, 1], [:f5, 1], [:a5, 1], [:bb5, 1],
  [:c6, 2], [:a5, 2],
  [:g5, 1], [:bb5, 1], [:g5, 1], [:f5, 1],
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
  cutoff = opts.fetch(:cutoff, 110)
  use_synth synth
  line.each do |note, beats|
    if note == :rest
      sleep beats
    else
      play note,
           sustain: beats * 0.8,
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
  amp = opts.fetch(:amp, 0.45)
  synth = opts.fetch(:synth, :dark_ambience)
  use_synth synth
  chords.each do |ch|
    play_chord ch,
               sustain: beats * 0.95,
               release: 1.0,
               amp: amp
    sleep beats
  end
end

define :goauld_percussion do |beats, opts|
  opts ||= {}
  amp = opts.fetch(:amp, 0.4)
  beats.times do |i|
    sample :bd_haus, amp: amp
    sleep 0.5
    sample :elec_mid_snare, rate: 0.65, amp: amp * 0.5 if i % 2 == 0
    sleep 0.5
  end
end

with_fx :gverb, room: 70, mix: 0.35 do
  # Section 1 – 16 beats: deep chant
  pad_progression(OBELISK_CHORDS[0..3], beats_per_chord: 4, amp: 0.5, synth: :hollow)
  play_line(SERPENT_HUM, synth: :blade, amp: 0.9, cutoff: 105)
  
  # Section 2 – 16 beats: march of the Jaffa
  perc_thread = in_thread { goauld_percussion(16, amp: 0.35) }
  pad_progression(OBELISK_CHORDS[2..5], beats_per_chord: 4, amp: 0.45, synth: :dark_ambience)
  perc_thread.join
  
  # Section 3 – 16 beats: sarcophagus melody
  perc_thread = in_thread { goauld_percussion(16, amp: 0.4) }
  pad_thread = in_thread { pad_progression(OBELISK_CHORDS, beats_per_chord: 4, amp: 0.4, synth: :prophet) }
  play_line(SARCOPHAGUS_LINE, synth: :dsaw, amp: 1.05, cutoff: 120)
  perc_thread.join
  pad_thread.join
  
  # Section 4 – 16 beats: eerie fade
  pad_progression(OBELISK_CHORDS[4..7], beats_per_chord: 4, amp: 0.4, synth: :hollow)
end
