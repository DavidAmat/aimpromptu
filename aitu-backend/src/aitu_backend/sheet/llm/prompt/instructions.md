# Task

You turn a piano matrix notation into a classical piano sheet. The matrix comes from a transcription of audio (or
of a MIDI file): it only says which key starts at which frame (one frame = 40 ms). It has no bars, no beats, no
figures, and often no hands. You write the same notes as a sheet in the text format **F1 bars**: bars and beats,
hand of each note (left hand = lower staff, right hand = upper staff), figure, beam groups, triplets, the `#` or `b`
name of each note, and clef changes. The goal is the sheet a classical engraver (Chopin, Beethoven, Mozart, Schubert
editions) would print for these notes.

You work window by window (8 bars of music at a time). Each window prompt gives you the **target** (the notes to
write), a **look-ahead** (the next notes, only to see what comes; do not write them) and, from the second window
on, the **decided context** (the last bars you wrote before).

In this run the matrix is a **pop song** played on the piano (a cover recorded from YouTube and transcribed by a machine), not a classical score; write it as a classical engraver would print it. The windows of a song follow each other: the last bar you write in a window is not kept (the target may end inside it); the next window starts at that bar and writes it again with what follows. The first window holds about 8 bars of a first tempo estimate, which is often wrong by a factor of 2: the length of a window says nothing about the beat.

# Input format: F1 frames

Format F1, frame lines without bars. The time is counted in frames, the columns of the piano matrix: one frame is 40 ms. There are no bars and no beats. Each line is one frame where at least one note starts. Only note starts are written: there are no rests and no ties, and a note sounds until the pianist releases it (pedal).

- `F1 frames frameMs=40` is the first line. The second line gives the key signature (`key=3#` three sharps, `key=2b` two flats, `key=0` none) and the clef of each staff at the start (`clefs: R=treble L=bass`).
- A note line starts with its frame: `f57` is frame 57 from the start of the passage. A line `[]x10` means that 10 frames without any note start come before the next line (it is the gap; the frame numbers are always written too).
- `f57 key=2b` alone on a line changes the key signature at that frame.
- After the frame come the hands that start notes there: `L:` left hand (lower staff), then `R:` right hand (upper staff). A hand that starts nothing is not written.
- A note is `pitch:figure`. The pitch is the scientific pitch name with the accidental as it is spelled (C4 is middle C; `C#4`, `Bb2`, `F##5`). The figure is the note value printed on the sheet: 1 whole, 2 half, 4 quarter, 8 eighth, 16 sixteenth, 32 thirty-second; a dot after it makes it dotted (`8.`). Without bars the figure does not give the time: the frames do. Notes of one hand that share the figure and all tags are written as one chord: `A2,C#3,E3:8`. Notes are ordered from low to high. A note without `:figure` is a note of a matrix whose figure is not decided yet; `?:` instead of `L:`/`R:` is a note without a hand.
- Tags after a note describe it:
  - `b3`: the note belongs to beam group 3. Every note joined by one beam carries the same number, on different lines and also across the two staves. Notes without a `b` tag have a flag or no beam.
  - `t3`: a triplet note (3 in the time of 2); `t5:4`: 5 in the time of 4. `(t3` marks the first note of each tuplet group (as `(3` in ABC).
  - `grace`: a grace note (`grace/` slashed).
  - `arp` rolled chord, `tr` trill, `ferm` fermata, `mord` mordent, `turn` turn, `trem` tremolo.
  - `8va`: the note is printed an octave lower under an 8va line (the pitch written here is the sounding pitch); `8vb` the opposite.
- `clef=treble` or `clef=bass` right after `L:` or `R:` changes the clef of that staff at that frame.

# Output format: F1 bars with frame anchors

Format F1, frame lines with bars. Each line is one moment of the music: the time at which at least one note starts. Only note starts are written: there are no rests and no ties, and a note sounds until the pianist releases it (pedal).

- `F1 bars` is the first line. `clefs: R=treble L=bass` gives the clef of each staff at the start.
- `bar 12 meter=3/4 key=2b` starts bar 12. The meter and the key are written in the first bar and when they change; the key is the number of sharps (`3#`) or flats (`2b`) of the key signature, `0` for none. `len=1` gives the length in quarters of a bar that is shorter than its meter (a pickup).
- A note line starts with its position in the bar, counted in beats from 1: `1`, `2`, `2+1/2` (half a beat after beat 2), `1+1/3`, `3+3/4`. The beat is the quarter note in 2/4, 3/4 and 4/4, the half note in 2/2, and the dotted quarter in 6/8, 9/8 and 12/8.
- After the position come the hands that start notes at that moment: `L:` left hand (lower staff), then `R:` right hand (upper staff). A hand that starts nothing is not written.
- A note is `pitch:figure`. The pitch is the scientific pitch name with the accidental as it is spelled (C4 is middle C; `C#4`, `Bb2`, `F##5`, `Ebb3`). The figure is 1 whole, 2 half, 4 quarter, 8 eighth, 16 sixteenth, 32 thirty-second, 64; a dot after it makes it dotted (`8.`). Notes of one hand that share the figure and all tags are written as one chord: `A2,C#3,E3:8`. Notes are ordered from low to high.
- Tags after a note describe it:
  - `b3`: the note belongs to beam group 3. Every note joined by one beam carries the same number, on different lines and also across the two staves. Notes without a `b` tag have a flag or no beam.
  - `t3`: a triplet note (3 in the time of 2); `t5:4`: 5 in the time of 4. `(t3` marks the first note of each tuplet group (as `(3` in ABC).
  - `grace`: a grace note, written before the main note of the same moment; `grace/` is a slashed grace note (acciaccatura).
  - `arp` rolled chord, `tr` trill, `ferm` fermata, `mord` mordent, `turn` turn, `trem` tremolo.
  - `8va`: the note is printed an octave lower under an 8va line (the pitch written here is the sounding pitch); `8vb` the opposite.
- `clef=treble` or `clef=bass` right after `L:` or `R:` changes the clef of that staff at that moment.

**Frame anchors.** In your answer every note line starts with its position in the bar and then the frame of its
notes in the input: `2+1/2 f57  L: C3:8 b4  R: E5:8 b5`. The frame must be copied exactly from the input line of
those notes. Notes that the input gives in one frame are written on one line (one position). A grace note that
the input gives one or two frames before its main note keeps its own frame: write it on its own line with the
same position as its main note (`3 f28  R: F#5:16 grace/` then `3 f30  R: E5:4`).

**Every onset exactly once.** Write every note of the target exactly once, with its frame and its pitch (you may
change the spelling, e.g. `A#3` -> `Bb3`, but not the key). Do not add notes, do not drop notes, and do not write
the look-ahead.

# What you decide

1. **Beat, meter and bar lines.** Find the beat from the frames: the gap (in frames) that repeats between the
   strong onsets (bass notes, chords). One quarter note usually lasts 10 to 20 frames (400–800 ms); the most
   common gap is often an eighth or a sixteenth, not the quarter. Choose the meter (3/4 if strong bass onsets come
   every 3 beats, 6/8 if the beat divides in three, ...) and put bar 1 on a strong onset; a first bar shorter than
   the meter is a pickup (`bar 0 ... len=1`). Then every frame gets a position: frame -> beat with the same
   tempo for the whole window (in this run the matrix is a real performance: the pianist moves the tempo, so the quarter can be a few
   frames longer or shorter from bar to bar, and chords are not perfectly together; follow the music, not a
   fixed grid). Write one comment line before the bars: `# quarter=15 frames meter=3/4` (lines that start
   with `#` are ignored by the reader).
2. **Hands**: who plays each note.
3. **Figures**: each onset gets the time until the next onset of the same hand, as a written value
   (sustains are not important; notes are pedaled), but cut at the barline. Triplets get `t3` and `(t3` on the
   first note of each group.
4. **Beams**, **spelling** and **clefs** following the rules below.

# Rules of classical engraving (measured on Chopin, Beethoven, Mozart and Schubert scores)

Hands
- hand.1 Keep a note in the hand of its figure: when the right hand holds a note and a new note starts below it
  inside a left-hand figure (the notes before and after are left hand), it is left hand, also above C4 (99 %).
- hand.2 Do not decide the hand by middle C: 23–42 % of left-hand notes are at or above C4 (Alberti bass).
- hand.3 In one slice all left-hand notes are below all right-hand notes (98.5 %).
- hand.4 One hand starts at most an octave at once (rolled tenths are marked `arp`).
- hand.5 A run of up to an octave stays in one hand (95 %).
- hand.6 A long run or arpeggio is shared at most once: rising runs go left -> right, falling runs right -> left,
  handover near C4–D4. Never LH-RH-LH inside one run.
- hand.7 A single note isolated high in the left hand (far above the left-hand notes around it) goes to the right
  hand when the right hand plays at that moment within an octave of it (user, phase 14).
- range.1 The left hand makes the jumps (62–80 % of jumps over an octave). range.2 Waltz and dance bass: bass note
  on the downbeat and the chord after it are both left hand, never move the chord to the right hand.
- range.3 A hand keeps its frame: a note inside the range a hand used in the previous bar belongs to that hand.
- range.4 One hand covers about an octave per beat and 1–1.5 octaves per bar. range.5 Hands rarely cross.

Beams (an eighth or shorter joined to the next note of the same hand)
- beam.1 Never across the barline. beam.2 Never across the half bar of 4/4 or 12/8.
- beam.3 Sixteenths: one beam per beat (in 2/2 per quarter, in 3/8 per bar).
- beam.4 Eighths: 4/4 groups of 4 split at the half bar; 2/2 4 per half note; 6/8, 9/8, 12/8 3 per dotted beat;
  3/8 one per bar; 3/4 one beam for the whole bar when all notes are plain eighths, but split at every beat when
  the rhythm mixes figures; 2/4 4 in one beam or 2 + 2 (copy the previous bars).
- beam.5 32nds: one beam per eighth. beam.6 A tuplet is one beam; do not mix tuplet and plain notes in one beam.
- beam.7 Inside a beat keep the beam, also when the melody changes direction.
- beam.8 A beam may join notes of both staves when one figure moves between registers (rare).

Spelling (`#` or `b`)
- spell.1 Notes of the key signature keep its names (also E#, B#, Cb, Fb in remote keys).
- spell.2 Other notes: find the local key (the key whose scale holds most notes around), name from it.
- spell.3 Raised 4th of the (local) major key: `#` (F# in C). spell.4 Leading tone of the minor key: `#` or natural
  (G# in A minor). spell.5 Lowered 7th: `b` (Bb in C). spell.6 #1/b2: `#` (C# in C).
- spell.7 #2/b3 and #5/b6 follow the line: `#` when the next note is a step up, `b` when a step down; else `b`.

Clefs (left hand: the user's rules, a clean left hand first; right hand: measured)
- clef.L1 Priority for the left hand: (1) the bass clef, (2) the treble clef, (3) the treble clef with `8va`. Use
  the next one only when the one before is not readable. Never `8va` or `15ma` in the bass clef.
- clef.L2 Readable in the bass clef: notes up to C4 (one ledger line); a single note or chord up to about G4 (three
  ledger lines) may stay; an octave whose lower note is readable stays (C4-C5).
- clef.L3 Change to treble for a stretch of two or more onsets not readable in the bass clef, when the music after
  them stays high too. No onset stays four or more ledger lines above the bass staff (above about G4): write it in
  the treble clef, also when this needs a clef change for that one onset.
- clef.L4 In the treble clef, left-hand notes below A3 are hard to read. Low notes (below A3) that alternate with a
  high part not readable in the bass clef (a waltz bass note + chords, an arpeggio that climbs into the treble
  register, a bass note + one high chord): the low notes in the bass clef, the high part in the treble clef, also
  inside a beam (as Chopin's editions print it).
- clef.L5 A left hand very high even in the treble clef (from about E6 up): treble clef with `8va`.
- clef.L6 Otherwise change on a beat or between two beam groups, and go back to bass as soon as the hand is readable
  there. Fewer changes are better (a change is worth about 3 ledger lines saved). These rules are recommendations
  for a pleasant sheet: choose the cleanest option.
- clef.2 Right hand in bass clef when its notes sit around G3 or lower. clef.6 Right hand 8va from about G6 up.

Symmetry
- sym.1 Expect repeated figures mostly in the accompanying hand; write repeated figures the same way each time
  (same hands, same beams).

# Examples (real scores, other pieces)

## Example 1: A major arpeggio shared once: LH A2-A3, RH C#4-C#6; then LH accompaniment under a held RH note

Input (target):
```
F1 frames frameMs=40
key=3# clefs: R=treble L=bass
f0       ?: A2
[]x2
f3       ?: C#3
[]x2
f6       ?: E3
[]x2
f9       ?: A3
[]x3
f13      ?: C#4
[]x1
f15      ?: E4
[]x1
f17      ?: A4
[]x1
f19      ?: C#5
f20      ?: E5
[]x1
f22      ?: A5
f23      ?: C#6
[]x1
f25      ?: A3,E6
[]x5
f31      ?: E4
[]x6
f38      ?: C#4,E6
[]x5
f44      ?: E4
[]x5
f50      ?: B3,E6
[]x5
f56      ?: E4,G#4
[]x6
f63      ?: D4,G#4
[]x5
f69      ?: E4
[]x5
f75      ?: B3
[]x5
f81      ?: E4
[]x6
f88      ?: D4,G#4
[]x5
f94      ?: E4
[]x5
f100     ?: C#4,A4
[]x5
f106     ?: E4
[]x6
f113     ?: G#3,B4
[]x5
f119     ?: E4
[]x5
f125     ?: A3,C#5
[]x5
f131     ?: E4
[]x6
f138     ?: F#3,D5
[]x5
f144     ?: A3
```

Answer:
```
# quarter=12.5 frames meter=4/4
F1 bars
clefs: R=treble L=bass
bar 1 meter=4/4 key=3#
1 f0           L: A2:16 b1
1+1/4 f3       L: C#3:16 b1
1+1/2 f6       L: E3:16 b1
1+3/4 f9       L: A3:16 b1
2 f13          R: C#4:16 (t3 b2
2+1/6 f15      R: E4:16 t3 b2
2+1/3 f17      R: A4:16 t3 b2
2+1/2 f19      R: C#5:32 b3
2+5/8 f20      R: E5:32 b3
2+3/4 f22      R: A5:32 b3
2+7/8 f23      R: C#6:32 b3
3 f25          L: A3:8 b4  R: E6:4
3+1/2 f31      L: E4:8 b4
4 f38          L: C#4:8 b4  R: E6:4
4+1/2 f44      L: E4:8 b4
bar 2
1 f50          L: B3:8 b5  R: E6:8 b6
1+1/2 f56      L: E4:8 b5  R: G#4:16 b6
2 f63          L: D4:8 b5  R: G#4:2
2+1/2 f69      L: E4:8 b5
3 f75          L: B3:8 b7
3+1/2 f81      L: E4:8 b7
4 f88          L: D4:8 b7  R: G#4:4
4+1/2 f94      L: E4:8 b7
bar 3
1 f100         L: C#4:8 b8  R: A4:4
1+1/2 f106     L: E4:8 b8
2 f113         L: G#3:8 b8  R: B4:4
2+1/2 f119     L: E4:8 b8
3 f125         L: A3:8 b9  R: C#5:4
3+1/2 f131     L: E4:8 b9
4 f138         L: F#3:8 b9  R: D5:4
4+1/2 f144     L: A3:8 b9
```

## Example 2: 6/8: left hand eighths 3 + 3 (one beam per dotted beat)

Input (target):
```
F1 frames frameMs=40
key=5# clefs: R=treble L=bass
f0       ?: B2,D#5
[]x7
f8       ?: F#3
[]x2
f11      ?: D5
[]x3
f15      ?: F#4,D#5
[]x7
f23      ?: B2,D5
[]x6
f30      ?: F3
[]x3
f34      ?: C#5
[]x3
f38      ?: F4,D5
[]x6
f45      ?: B2,C#5
[]x7
f53      ?: E3
[]x7
f61      ?: E4
[]x6
f68      ?: B2
[]x7
f76      ?: G3,D#5
[]x6
f83      ?: G4,E5
```

Answer:
```
# quarter=15.2 frames meter=6/8
F1 bars
clefs: R=treble L=bass
bar 1 meter=6/8 key=5#
1 f0           L: B2:8 b1  R: D#5:8 b2
1+1/3 f8       L: F#3:4 F#3:8 b1
1+1/2 f11      R: C##5:16 b2
1+2/3 f15      L: F#4:8 b1  R: D#5:8 b2
2 f23          L: B2:8 b3  R: D5:8 b4
2+1/3 f30      L: F3:4 F3:8 b3
2+1/2 f34      R: C#5:16 b4
2+2/3 f38      L: F4:8 b3  R: D5:8 b4
bar 2
1 f45          L: B2:8 b5  R: C#5:4.
1+1/3 f53      L: E3:4 E3:8 b5
1+2/3 f61      L: E4:8 b5
2 f68          L: B2:8 b6
2+1/3 f76      L: G3:4 G3:8 b6  R: D#5:8 b7
2+2/3 f83      L: G4:8 b6  R: E5:8 b7
```

## Example 3: waltz: left hand bass on beat 1, chords on beats 2-3, jumps of 16+ semitones

Input (target):
```
F1 frames frameMs=40
key=4b clefs: R=treble L=bass
f0       ?: Eb3,Eb5
[]x7
f8       ?: B4
[]x6
f15      ?: Ab3,C4,Eb4,C5
[]x7
f23      ?: Ab5
[]x6
f30      ?: Ab3,C4,Eb4,B4
[]x7
f38      ?: C5
[]x6
f45      ?: Eb2,Eb5
[]x7
f53      ?: C5
[]x6
f60      ?: Bb3,Eb4,G4,Db5
[]x7
f68      ?: Bb5
[]x6
f75      ?: Bb3,Eb4,G4,C5
[]x7
f83      ?: Db5
[]x6
f90      ?: Ab3,Eb5
[]x7
f98      ?: B4
[]x6
f105     ?: Eb4,Ab4,C5
[]x7
f113     ?: C6
[]x6
f120     ?: Eb4,Ab4,D5
[]x7
f128     ?: Eb5
```

Answer:
```
# quarter=15.0 frames meter=3/4
F1 bars
clefs: R=treble L=bass
bar 30 meter=3/4 key=4b
1 f0           L: Eb3:4  R: Eb5:4 Eb5:8 b1
1+1/2 f8       R: B4:8 b1
2 f15          L: Ab3,C4,Eb4:4  R: C5:8 b1
2+1/2 f23      R: Ab5:4 Ab5:8 b1
3 f30          L: Ab3,C4,Eb4:4  R: B4:8 b1
3+1/2 f38      R: C5:8 b1
bar 31
1 f45          L: Eb2:4  R: Eb5:4 Eb5:8 b2
1+1/2 f53      R: C5:8 b2
2 f60          L: clef=treble Bb3,Eb4,G4:4  R: Db5:8 b2
2+1/2 f68      R: Bb5:4 Bb5:8 b2
3 f75          L: Bb3,Eb4,G4:4  R: C5:8 b2
3+1/2 f83      R: Db5:8 b2
bar 32
1 f90          L: clef=bass Ab3:4  R: Eb5:4 Eb5:8 b3
1+1/2 f98      R: B4:8 b3
2 f105         L: clef=treble Eb4,Ab4:4  R: C5:8 b3
2+1/2 f113     R: C6:4 C6:8 b3
3 f120         L: Eb4,Ab4:4  R: D5:8 b3
3+1/2 f128     R: Eb5:8 b3
```

# How to answer

Reply with the F1 bars text only, as one block in triple backticks: the comment line(s) starting with `#`, the line
`F1 bars`, the `clefs:` line, then the bars. A checker reads it: it checks that the text parses and that every onset of
the target is there exactly once. If it finds a problem, the next message lists the problems; then write the whole
corrected answer again, in the same way.
