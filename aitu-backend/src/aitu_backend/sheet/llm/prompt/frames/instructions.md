# Task

You turn a piano matrix notation into a piano sheet for the app aimpromptu. The matrix comes from a transcription
of audio: it only says which key starts at which frame (one frame = 40 ms). You write the same notes in the text
format **F1 frames**, with the decisions an engraver makes: the **hand** of each note (left hand = lower staff, right
hand = upper staff), the **beam groups**, the **clefs and 8va lines**, the **ornaments**, the **key signature of
each passage**, and the few notes that the **rules of simplicity** add or leave out.

This sheet is simpler than a classical score, because every song can be heard in the app while the sheet is read:

- There are **no bars, no bar lines, no meter and no tempo**. Notes are placed by their frames: what sounds together
  is drawn on one vertical line, and a playback cursor moves over the sheet.
- There are **no rests, no dots and no tuplets**. A blank space means that a hand plays nothing.
- **Figures are a rule of the app.** The figure of a note is the nearest plain figure to how long the note sounds,
  but not past the next note of the same hand. You do not choose figures; the app computes them again from the hands
  you choose.
- **Grace notes are a rule of the app.** Only a thirty-second or shorter (one or two of them) that sounds just
  before a note two figures longer becomes a small grace note. A sixteenth or longer is always written as a real
  note: part of the melody or of the rhythm. A lone short note just before a much longer note is written two
  figures shorter than that note (a sixteenth before a half note is written as an eighth); a run of three or more
  fast notes keeps its figures.
- **Accidentals are a rule of the app.** Every note outside the key signature prints its sign each time it appears
  (without bars there is no memory of earlier notes); there are no double sharps or double flats; a white key is
  written natural, unless its natural name is in the key signature (then it takes its other name with one sign, E#
  instead of F natural in E major); with sharps in the key signature the black keys take sharps, with flats they
  take flats.

The matrix is a **pop song played on the piano** (a cover recorded from YouTube and transcribed by a machine). Chords
are not perfectly together, and some notes may be missing or extra. The sheet is for an **amateur pianist**: write
every note of the target, except the few that the rules of simplicity change (section "Simplicity").

You work **window by window** (12 to 16 seconds of music; a window ends at a pause). Each window prompt gives you the
**target** (the notes to write), a **look-ahead** (the next notes, only to see what comes; do not write them) and,
from the second window on, the **decided context** (the end of the previous window, as you wrote it). Before the
first window, one request asks you for the reference figure (section "The reference figure").

# Input format: F1 frames

- The first line is `F1 frames frameMs=40 quarterMs=500`: one frame is 40 ms, and `quarterMs` is the **reference
  figure**, the length of one quarter note in this song (500 ms here). It is not a tempo and it is never printed.
- The second line gives the key signature (`key=3#` three sharps, `key=2b` two flats, `key=0` none) and the clef of
  each staff at the start (`clefs: R=treble L=bass`).
- A note line starts with its frame: `f57` is frame 57 of the song. A line `[]x10` means that 10 frames without any
  note start come before the next line. Notes that start within 40 ms of each other are already in one frame.
- After the frame come the notes: `?:` notes whose hand is not decided; `L:` left hand, `R:` right hand.
- A note is `pitch:figure`. The pitch is the scientific pitch name, spelled by the app's rule (C4 is middle C;
  `C#4`, `Bb2`). The figure is the note value the app computed from the note's length: 1 whole, 2 half, 4 quarter,
  8 eighth, 16 sixteenth, 32 thirty-second, 64 sixty-fourth. Notes that share the figure and all tags are written as
  one chord: `A2,C#3,E3:8`. Notes are ordered from low to high.
- `f57 key=2b` alone on a line changes the key signature at that frame.
- `clef=treble` or `clef=bass` right after `L:` or `R:` changes the clef of that staff at that frame.
- Tags after a note:
  - `b3`: the note belongs to beam group 3. Every note of one beam group carries the same number, on different
    lines. A note without a `b` tag has a flag or no beam.
  - `tr` trill, `mord` mordent, `turn` turn, `arp` rolled chord.
  - `orn`: an onset played inside the ornament of the note before it in the same hand (the alternating notes of a
    trill after its main note). It stays in the text, so that every onset is kept, but it is not drawn.
  - `8va`: the note is printed an octave lower under an 8va line (the pitch written here is the sounding pitch).

# Output format: F1 frames with your decisions

The same text with hands: the two header lines, then every note line of the target with its frame copied exactly,
its notes split into `L:` and `R:`, and the tags you decide. The `[]x` lines may be left out.

```
F1 frames frameMs=40 quarterMs=500
key=3# clefs: R=treble L=bass
f120     L: A2:4  R: C#5,E5:8 b1
f126     R: D5:8 b1
```

**Every onset exactly once.** Write every note of the target exactly once, in its frame and with its pitch. Do not
move a note to another frame, and do not write the look-ahead. Copy the figures as the input gives them (the app
computes them again), and do not write grace notes, dots or tuplets. The only notes you may leave out or add are
the ones of the section "Simplicity", and each one is declared in a comment line after the note lines:

```
# leave out f1822 G2
# add f4556 D1
```

A note of the target missing from the answer without its `# leave out` line, or a note that is not in the target
without its `# add` line, is an error.

# What you decide

## Hands

- hand.1 Keep a note in the hand of its figure: when the right hand holds a note and a new note starts below it
  inside a left-hand figure (the notes before and after are left hand), it is left hand, also above C4.
- hand.2 Do not decide the hand by middle C: a quarter to a third of left-hand notes are at or above C4 (Alberti
  bass, chords of the accompaniment).
- hand.3 At one moment all left-hand notes are below all right-hand notes.
- hand.4 One hand plays at most about a tenth at once; a wider chord in one hand is rolled (`arp`).
- hand.5 A run of up to an octave stays in one hand.
- hand.6 A long run or arpeggio is shared at most once: rising runs go left -> right, falling runs right -> left,
  with the change near C4-D4. Never left, right, left inside one run.
- hand.7 A single note isolated high in the left hand (far above the left-hand notes around it) goes to the right
  hand when the right hand plays at that moment within an octave of it.
- range.1 The left hand makes the jumps (bass note, then chord). range.2 Dance and pop bass: the bass note and the
  chord after it are both left hand; never move that chord to the right hand.
- range.3 A hand keeps its place: a note inside the range a hand used in the seconds before belongs to that hand.
- range.4 One hand covers about an octave at a time. range.5 Hands rarely cross.

## Beam groups

A beam joins consecutive eighths and shorter notes of one hand into one group. Without bars and beats, the groups
are your reading of the music: a group shows the eye one shape (a rise, a fall, an arpeggio, a bass and chord
pattern). Very long groups do not help: the eye cannot find a shape in them.

- beam.1 Only eighths (8) and shorter notes (16, 32, 64) as the input gives them, and only consecutive notes of
  one hand: a group never skips a note of its hand. Do not join two notes with more than an eighth of silence
  between them in that hand.
- beam.2 **One figure per group.** All notes of a group have one figure; one single note of another figure may
  open or close the group, never sit inside it, and a group never holds two parts of different figures. When the
  figure changes, start a new group. (The app cuts a group that breaks this rule.)
- beam.3 **At most 8 notes in a group** (a chord counts as one note). The checker rejects a longer group. Cut
  earlier whenever one of the next reasons applies.
- beam.4 **Cut at a jump**: when the next note is far from the previous one (about an octave or more), unless the
  jump belongs to the pattern (a bass note and its chord in one left-hand figure).
- beam.5 **Cut where the direction changes or the pattern breaks**: a rising line that turns down, a figure that
  stops repeating, a bass pattern whose bass note changes.
- beam.6 **Show a repeated contour**: when the notes go up and down, up and down, make the groups repeat the same
  shape (one group for each rise and fall, or for each repetition of the figure), so the eye sees the repetition.
- beam.7 A left-hand pattern (an arpeggio, a bass and chord figure, an octave bass) is one group, or groups of the
  same size that repeat. Never cut a pattern between the two hands.
- beam.8 Write repeated passages the same way each time (same hands, same group sizes).
- beam.9 Two short notes (eighths or shorter) just before a longer note of the same hand are one group, when their
  figures are one figure or one step apart.
- Other good musical reasons to cut are allowed; the rules above are the minimum.

## Clefs and 8va (left hand: the user's rules, a clean left hand first; right hand: measured)

- clef.L1 Priority for the left hand: (1) the bass clef, (2) the treble clef, (3) the treble clef with `8va`. Use
  the next one only when the one before is not readable. Never `8va` in the bass clef.
- clef.L2 Readable in the bass clef: notes up to C4 (one ledger line); a single note or chord up to about G4 (three
  ledger lines) may stay; an octave whose lower note is readable stays (C4-C5).
- clef.L3 Change to treble for a stretch of two or more onsets not readable in the bass clef, when the music after
  them stays high too. No onset stays four or more ledger lines above the bass staff (above about G4): write it in
  the treble clef, also when this needs a clef change for that one onset.
- clef.L4 In the treble clef, left-hand notes below A3 are hard to read. Low notes (below A3) that alternate with a
  high part not readable in the bass clef: the low notes in the bass clef, the high part in the treble clef, also
  inside a beam group.
- clef.L5 A left hand very high even in the treble clef (from about E6 up): treble clef with `8va`.
- clef.L6 Otherwise change between two beam groups or at a pause, and go back to bass as soon as the hand is
  readable there. Fewer changes are better (a change is worth about 3 ledger lines saved). These rules are
  recommendations for a pleasant sheet: choose the cleanest option.
- clef.2 Right hand in the bass clef when its notes sit around G3 or lower for a while. clef.6 Right hand `8va`
  from about G6 up.

## Ornaments

- orn.1 Write `tr` (trill), `mord` (mordent) or `turn` only when the notes clearly are one: a fast alternation of a
  note and its upper neighbour is a trill on the first note; the other onsets of the alternation get `orn`. When in
  doubt, write the notes as they are.
- orn.2 `arp` on a chord of one hand wider than a tenth.

## Simplicity (the rules of simplicity and the amateur pianist)

The sheets are read and played by an **amateur pianist**. The transcription makes small mistakes: a note missing
from an octave, an extra note in a chord. On the page, small variations of a pattern are hard to read, and quick
jumps of one hand are hard to play. Fix them, and only them:

- simple.1 **Uniform patterns.** A passage that repeats one pattern (octaves, chords, single notes, a bass and chord
  figure) is written the same way every time. A column that breaks the pattern is made to fit: a single note in a
  run of octaves gets its missing octave note (`# add`), an octave or a chord in a run of single notes loses its
  extra notes (`# leave out`), a repeated chord gets its missing note. Choose whichever reads simpler; you may also
  make the whole passage simpler (single notes instead of octaves in the whole run). This applies to both hands.
- simple.2 **The amateur pianist.** A quick note or chord (a sixteenth or shorter, or a grace note) just before a
  main note of the same hand, that makes the hand jump far (more than an octave: down, then quickly up, or the
  other way), keeps only the notes near the main note: leave out the far ones. Example: the left hand plays G2+G3 as
  a sixteenth just before the chord Bb3+D4: write G3, leave out G2. A quick single note stays (it has no near note
  to keep). No quick jump of one hand that only a professional plays.
- simple.3 **The notes keep their place.** Never move a note to another frame and never change a pitch to another
  name. An added note joins a column where its hand already plays, within an octave of a note of that column, with
  the name of a note of that column or of the same pattern around it (the missing note of an octave or of the
  repeated chord). A note left out always leaves a note of its column within an octave of it: never empty a column
  of a hand. Never add a melody note or change the rhythm.
- simple.4 **Change little.** Most windows need no change or a few: only the columns that break a pattern and the
  far notes of quick chords. The checker accepts at most a tenth of the notes of the target. When in doubt, write the
  notes as they are.

## Key signature of a passage

- key.1 The header of the target gives the key signature in force. Keep it unless a passage of several seconds
  (about 5 or more) has many notes outside it, so that many signs would be printed. Then change, at the start of
  that passage, to the key signature with the fewest signs for its notes, and change back (or again) when the
  passage ends: a line `f120 key=0` before the note line of frame 120, or a new `key=` in the header when the change
  is at the start of the target.
- key.2 Do not change for a few passing notes: a change prints a new key signature on both staves.

# The reference figure

Before the first window, one request gives the gaps between onsets of the whole song (the peaks of their histogram)
and the start of the song. Choose the length of one quarter note in ms, so that the sheet reads well:

- Every figure follows from it: a note that sounds 240 ms is an eighth when the quarter is 480 ms, and a sixteenth
  when the quarter is 960 ms.
- Usually the beat a listener taps is the quarter, and the most common short gaps become eighths or sixteenths.
  In most songs the quarter lasts 400 to 750 ms.
- Avoid a choice that makes most notes thirty-seconds, or most notes halves and wholes.

Answer that request with one block in triple backticks: the line `quarterMs=480` and one line `# why: ...`.

# Examples

## Example 1 (a classical score): an A major arpeggio shared once (left hand A2-A3, right hand C#4-C#6), one group per figure; the right hand's E6 and G#4 not joined (a jump); then a left-hand figure of four eighths (low, high, middle, high), one group each time it repeats

Input (target):
```
F1 frames frameMs=40 quarterMs=500
key=3# clefs: R=treble L=bass
f0       ?: A2:16
[]x2
f3       ?: C#3:16
[]x2
f6       ?: E3:16
[]x2
f9       ?: A3:16
[]x3
f13      ?: C#4:16
[]x1
f15      ?: E4:16
[]x1
f17      ?: A4:16
[]x1
f19      ?: C#5:32
f20      ?: E5:32
[]x1
f22      ?: A5:32
f23      ?: C#6:32
[]x1
f25      ?: A3:8 E6:4
[]x5
f31      ?: E4:8
[]x6
f38      ?: C#4:8 E6:4
[]x5
f44      ?: E4:8
[]x5
f50      ?: B3,E6:8
[]x5
f56      ?: E4:8 G#4:16
[]x6
f63      ?: D4:8 G#4:2
[]x5
f69      ?: E4:8
[]x5
f75      ?: B3:8
[]x5
f81      ?: E4:8
[]x6
f88      ?: D4:8 G#4:4
[]x5
f94      ?: E4:8
[]x5
f100     ?: C#4:8 A4:4
[]x5
f106     ?: E4:8
[]x6
f113     ?: G#3:8 B4:4
[]x5
f119     ?: E4:8
[]x5
f125     ?: A3:8 C#5:4
[]x5
f131     ?: E4:8
[]x6
f138     ?: F#3:8 D5:4
[]x5
f144     ?: A3:8
```

Answer:
```
F1 frames frameMs=40 quarterMs=500
key=3# clefs: R=treble L=bass
f0       L: A2:16 b1
f3       L: C#3:16 b1
f6       L: E3:16 b1
f9       L: A3:16 b1
f13      R: C#4:16 b2
f15      R: E4:16 b2
f17      R: A4:16 b2
f19      R: C#5:32 b3
f20      R: E5:32 b3
f22      R: A5:32 b3
f23      R: C#6:32 b3
f25      L: A3:8 b4  R: E6:4
f31      L: E4:8 b4
f38      L: C#4:8 b4  R: E6:4
f44      L: E4:8 b4
f50      L: B3:8 b5  R: E6:8
f56      L: E4:8 b5  R: G#4:16
f63      L: D4:8 b5  R: G#4:2
f69      L: E4:8 b5
f75      L: B3:8 b6
f81      L: E4:8 b6
f88      L: D4:8 b6  R: G#4:4
f94      L: E4:8 b6
f100     L: C#4:8 b7  R: A4:4
f106     L: E4:8 b7
f113     L: G#3:8 b7  R: B4:4
f119     L: E4:8 b7
f125     L: A3:8 b8  R: C#5:4
f131     L: E4:8 b8
f138     L: F#3:8 b8  R: D5:4
f144     L: A3:8 b8
```

## Example 2 (a classical waltz): left-hand bass and chords (quarters, no beams) with clef changes for the high chords; the right hand's six eighths repeat one shape, one group each

Input (target):
```
F1 frames frameMs=40 quarterMs=600
key=4b clefs: R=treble L=bass
f0       ?: Eb3:4 Eb5:8
[]x7
f8       ?: Cb5:8
[]x6
f15      ?: Ab3,C4,Eb4:4 C5:8
[]x7
f23      ?: Ab5:8
[]x6
f30      ?: Ab3,C4,Eb4:4 Cb5:8
[]x7
f38      ?: C5:8
[]x6
f45      ?: Eb2:4 Eb5:8
[]x7
f53      ?: C5:8
[]x6
f60      ?: Bb3,Eb4,G4:4 Db5:8
[]x7
f68      ?: Bb5:8
[]x6
f75      ?: Bb3,Eb4,G4:4 C5:8
[]x7
f83      ?: Db5:8
[]x6
f90      ?: Ab3:4 Eb5:8
[]x7
f98      ?: Cb5:8
[]x6
f105     ?: Eb4,Ab4:4 C5:8
[]x7
f113     ?: C6:8
[]x6
f120     ?: Eb4,Ab4:4 D5:8
[]x7
f128     ?: Eb5:8
```

Answer:
```
F1 frames frameMs=40 quarterMs=600
key=4b clefs: R=treble L=bass
f0       L: Eb3:4  R: Eb5:8 b1
f8       R: Cb5:8 b1
f15      L: Ab3,C4,Eb4:4  R: C5:8 b1
f23      R: Ab5:8 b1
f30      L: Ab3,C4,Eb4:4  R: Cb5:8 b1
f38      R: C5:8 b1
f45      L: Eb2:4  R: Eb5:8 b2
f53      R: C5:8 b2
f60      L: clef=treble Bb3,Eb4,G4:4  R: Db5:8 b2
f68      R: Bb5:8 b2
f75      L: Bb3,Eb4,G4:4  R: C5:8 b2
f83      R: Db5:8 b2
f90      L: clef=bass Ab3:4  R: Eb5:8 b3
f98      R: Cb5:8 b3
f105     L: clef=treble Eb4,Ab4:4  R: C5:8 b3
f113     R: C6:8 b3
f120     L: Eb4,Ab4:4  R: D5:8 b3
f128     R: Eb5:8 b3
```

## Example 3 (a pop song): an octave bass in eighths; the groups repeat the shape low, high, low, high, and a group ends where the bass note changes (E, D, F#); the right hand's chords in eighths are joined until a longer chord

Input (target):
```
F1 frames frameMs=40 quarterMs=500
key=3# clefs: R=treble L=bass
f0       ?: E2:8
[]x5
f6       ?: E3,E4,F#4,F#5:8
[]x5
f12      ?: E2,E3,F#4,F#5:8
[]x6
f19      ?: E3:8 A4,F#5,A5:4
[]x5
f25      ?: D2,D3:8
[]x5
f31      ?: D3,D4,G#4,E5,G#5:8
[]x5
f37      ?: D2,F#4,D5,F#5:8
[]x6
f44      ?: D3:8 F#4,D5,F#5:4
[]x5
f50      ?: D2:8
[]x5
f56      ?: D3,F#4,D5,F#5:8
[]x5
f62      ?: D2,F#4,D5,F#5:8
[]x6
f69      ?: D3:8 F#4,A4,F#5:4
[]x5
f75      ?: F#2,F#3:8
[]x5
f81      ?: F#2,F#4,A4,F#5:8
[]x5
f87      ?: F#3,F#4,A4,F#5:8
[]x6
f94      ?: E2,E3,E4,A4,E5:8
[]x5
f100     ?: E2:8
[]x5
f106     ?: E3,E4,B4,E5:8
[]x5
f112     ?: E2,E4,B4,E5:8
[]x6
f119     ?: E3,B4,B5:8
[]x5
f125     ?: D2,D3:8 C#5,A5,C#6:2
[]x5
f131     ?: D3:8
[]x5
f137     ?: D2:8
[]x6
f144     ?: D3:8
[]x5
f150     ?: D2:8
[]x5
f156     ?: D3:8
[]x5
f162     ?: D2:8
[]x6
f169     ?: D3:8 C#5,A5,C#6:4
```

Answer:
```
F1 frames frameMs=40 quarterMs=500
key=3# clefs: R=treble L=bass
f0       L: E2:8 b1
f6       L: E3,E4:8 b1  R: F#4,F#5:8 b2
f12      L: E2,E3:8 b1  R: F#4,F#5:8 b2
f19      L: E3:8 b1  R: A4,F#5,A5:4
f25      L: D2,D3:8 b3
f31      L: D3,D4:8 b3  R: G#4,E5,G#5:8 b4
f37      L: D2:8 b3  R: F#4,D5,F#5:8 b4
f44      L: D3:8 b3  R: F#4,D5,F#5:4
f50      L: D2:8 b5
f56      L: D3:8 b5  R: F#4,D5,F#5:8 b6
f62      L: D2:8 b5  R: F#4,D5,F#5:8 b6
f69      L: D3:8 b5  R: F#4,A4,F#5:4
f75      L: F#2,F#3:8 b7
f81      L: F#2:8 b7  R: F#4,A4,F#5:8 b8
f87      L: F#3:8 b7  R: F#4,A4,F#5:8 b8
f94      L: E2,E3:8 b9  R: E4,A4,E5:8 b8
f100     L: E2:8 b9
f106     L: E3:8 b9  R: E4,B4,E5:8 b10
f112     L: E2:8 b9  R: E4,B4,E5:8 b10
f119     L: E3:8 b9  R: B4,B5:8 b10
f125     L: D2,D3:8 b11  R: C#5,A5,C#6:2
f131     L: D3:8 b11
f137     L: D2:8 b11
f144     L: D3:8 b11
f150     L: D2:8 b12
f156     L: D3:8 b12
f162     L: D2:8 b12
f169     L: D3:8 b12  R: C#5,A5,C#6:4
```

## Example 4 (a pop song): a right-hand arpeggio that rises and falls on each chord; each rise is one group and each fall another, so the shape repeats; the last note of each figure stands alone (a pause follows)

Input (target):
```
F1 frames frameMs=40 quarterMs=400
key=0 clefs: R=treble L=bass
f0       ?: C5:8
[]x3
f4       ?: E3:1
[]x2
f7       ?: B4:32
[]x1
f9       ?: D5:32
[]x1
f11      ?: G5:16
[]x3
f15      ?: B5:8
[]x6
f22      ?: G5:16
[]x3
f26      ?: D5:16
[]x3
f30      ?: B4:8
[]x3
f34      ?: C3:1
[]x2
f37      ?: G4:32
[]x1
f39      ?: C5:32
[]x1
f41      ?: E5:16
[]x3
f45      ?: G5:8
[]x6
f52      ?: E5:16
[]x3
f56      ?: C5:16
[]x3
f60      ?: G4:8
[]x3
f64      ?: D3:1
[]x2
f67      ?: A4:32
[]x1
f69      ?: D5:32
[]x1
f71      ?: F#5:16
[]x3
f75      ?: A5:8
[]x6
f82      ?: F#5:16
[]x3
f86      ?: D5:16
[]x3
f90      ?: A4:8
[]x3
f94      ?: A3:1
[]x2
f97      ?: C5:32
[]x1
f99      ?: E5:32
[]x1
f101     ?: A5:16
[]x3
f105     ?: C6:8
[]x6
f112     ?: A5:16
[]x3
f116     ?: E5:16
[]x3
f120     ?: C5:8
```

Answer:
```
F1 frames frameMs=40 quarterMs=400
key=0 clefs: R=treble L=bass
f0       R: C5:8
f4       L: E3:1
f7       R: B4:32 b1
f9       R: D5:32 b1
f11      R: G5:16 b1
f15      R: B5:8 b2
f22      R: G5:16 b2
f26      R: D5:16 b2
f30      R: B4:8
f34      L: C3:1
f37      R: G4:32 b3
f39      R: C5:32 b3
f41      R: E5:16 b3
f45      R: G5:8 b4
f52      R: E5:16 b4
f56      R: C5:16 b4
f60      R: G4:8
f64      L: D3:1
f67      R: A4:32 b5
f69      R: D5:32 b5
f71      R: F#5:16 b5
f75      R: A5:8 b6
f82      R: F#5:16 b6
f86      R: D5:16 b6
f90      R: A4:8
f94      L: A3:1
f97      R: C5:32 b7
f99      R: E5:32 b7
f101     R: A5:16 b7
f105     R: C6:8 b8
f112     R: A5:16 b8
f116     R: E5:16 b8
f120     R: C5:8
```

## Example 5 (written for this prompt): the rules of simplicity. The left hand's quick octave G2+G3 before the chord Bb3+D4 keeps only G3 (simple.2); in the run of octaves, the two single D3 get their D2 (simple.1); the lead-in A2 is another note, not a broken octave, and stays

Input (target):
```
F1 frames frameMs=40 quarterMs=480
key=2b clefs: R=treble L=bass
f0       ?: G2,G3,C5:16
[]x4
f5       ?: Bb3,D4:4 D5:8
[]x11
f17      ?: C5:4
[]x11
f29      ?: A2:16
[]x2
f32      ?: D2,D3:16 G4,A4,D5:4
[]x2
f35      ?: D3:16
[]x2
f38      ?: D2,D3:16
[]x2
f41      ?: D2,D3:16
[]x2
f44      ?: D2,D3:16 G4,A4,D5:4
[]x2
f47      ?: D2,D3:16
[]x2
f50      ?: D3:16
[]x2
f53      ?: D2,D3:16
[]x2
f56      ?: Eb2,Eb3:2 Bb4,G5:4
```

Answer:
```
F1 frames frameMs=40 quarterMs=480
key=2b clefs: R=treble L=bass
f0       L: G3:16  R: C5:16 b1
f5       L: Bb3,D4:4  R: D5:8 b1
f17      R: C5:4
f29      L: A2:16 b2
f32      L: D2,D3:16 b2  R: G4,A4,D5:4
f35      L: D2,D3:16 b2
f38      L: D2,D3:16 b2
f41      L: D2,D3:16 b3
f44      L: D2,D3:16 b3  R: G4,A4,D5:4
f47      L: D2,D3:16 b3
f50      L: D2,D3:16 b3
f53      L: D2,D3:16 b3
f56      L: Eb2,Eb3:2  R: Bb4,G5:4
# leave out f0 G2
# add f35 D2
# add f50 D2
```

# How to answer

Reply with the F1 frames text only, as one block in triple backticks: the two header lines, the note lines, then the
`# leave out` and `# add` lines, if any. A checker reads it: it checks that every onset of the target is there
exactly once with a hand (but the declared changes, within the limits of simple.3 and simple.4), that no beam group
has more than 8 notes or skips a note of its hand, that `8va` is never in the bass clef, and that no note stands
four or more ledger lines above its staff (clef.L3; clef.L5 and clef.6: under `8va` in the treble clef). If it finds a problem,
the next message lists the problems; then write the whole corrected answer again, in the same way.
