# Task

You write a piano sheet again at a **level** of difficulty (easy, medium or hard) for the app aimpromptu. The sheet
comes from a transcription of a pop song played on the piano, often by a machine and not by a person, so it is hard
to play for reasons that have nothing to do with the music: chords that span more than an octava, octavas that the
song does not need, a left hand that plays three octavas at once or jumps on every note, a right hand whose melody is
hidden among chords and decoration notes, and artifacts such as a very high chord that adds nothing to the melody.

You keep the song (its melody, its harmony and its time) and you write a clean right hand and a new **left-hand
companion** (what the left hand plays under the melody) that follow the level and the **patterns** the user chose.
The reader is an amateur pianist who wants to play the song at first sight: the same pattern again and again, hands
that stay in one position, and nothing that the level does not allow.

The sheet is simpler than a classical score, because the song can be heard in the app while the sheet is read:

- There are **no bars, no bar lines, no meter and no tempo**. Notes are placed by their frames (one frame = 40 ms):
  what sounds together is drawn on one vertical line, and a playback cursor moves over the sheet.
- There are **no rests, no dots and no tuplets**. A blank space means that a hand plays nothing.
- The app draws the **beams, the clefs, the 8va lines, the accidentals and the decoration notes** by its own rules.
  You write only the notes, their hands and their figures.

The words of this prompt for the figures: redonda (whole note, figure 1), blanca (half, 2), negra (quarter, 4),
corchea (eighth, 8), semicorchea (sixteenth, 16), fusa (thirty-second, 32). An octava is an octave. A **decoration
note** is a fusa or shorter (one or two of them) just before a longer note: the app draws it small (a grace note).

# What a level is: hand motion and patterns

Difficulty is a matter of **hand movement**, of **keeping patterns**, and of **how many notes** each hand plays:

- A hand that stays in one position (finger 1 to finger 5 over about an octava) plays many notes easily, also fast
  notes. A hand that jumps, opens wide or changes its shape on every note is hard, even with few notes.
- Corcheas are not hard when they always follow one pattern: a pianist who knows the chord knows which notes to
  play and how. Keep **one pattern through each section** of the song (your plan says which), so that once the hand
  has learnt it, the pianist only follows the chords. The same passage, when it comes again, is written the same way.
- The left hand chooses one position for each chord and stays there until the chord changes; when the chord
  changes, it moves to the nearest position of the new chord (an inversion near the last one, not a jump).
- Easy and medium foster this most: few moves, one pattern, small chords. Hard allows more movement, but still with
  symmetry and repeated shapes. (Super hard is a later level and is not used here.)

# A level simplifies the sheet: never harder than it is now

The sheet now is the hardest version of the song (the user calls it super hard). Every level makes it simpler, so no
passage may become harder than it is now, and the new left hand **approximates the left hand of the sheet**: it is a
simplified copy of it, not a new invention.

- **Follow the rhythm the left hand plays now, simplified.** Keep its main onsets (the long notes, the strong
  beats, the notes that start each figure) and leave out the fast ones; write it with the regular figures of the
  pattern. Where the left hand plays a negra (an octava, a chord) and then two corcheas of the chord, the new left
  hand plays a negra (an octava, or the bass note) and then two corcheas of notes of the same chord; it does not
  become an arpeggio in corcheas, a waltz or another rhythm. Choose, among the patterns of this run, the one whose
  rhythm is nearest to what the left hand plays now. The checker counts the onsets: in each chord the left hand has at
  most as many onsets as now, and at least 70 % of its onsets are onsets of the left hand now (within a frame).
- **Simple stretches stay as they are.** Where the left hand plays single notes inside one octava (E2, E2, E2 in an
  uneven rhythm) or one small chord again and again (a held fifth for each chord), it is already easy: keep its
  notes, play them in a regular, symmetric rhythm with as many onsets or fewer, and declare the pattern `keep`
  (`# pattern L f33-f159: keep`). Do not give it a pattern of the catalog. The app lists these stretches in each
  batch and in the summary of the song; the checker refuses another note or more onsets there.

# What you keep

1. **The melody comes first.** The melody is mostly the top line of the right hand. Each note of the right hand's top
   line stays at its frame, with its pitch (or the same name an octava lower or higher, where the transcription
   doubled it in octavas). You may write a melody note with a shorter or longer figure to make the rhythm simpler;
   you never leave it out. Two kinds of notes of that top line may go, each declared in a comment line with why:
   - `# not melody f1084 E4: a fill between two notes of the melody`: the top of an accompaniment chord while the
     melody rests, a fill, a note doubled by the transcription;
   - `# artifact f863 D#7,E7: a high chord alone, two octavas above the melody`: a note that the transcription
     made and the song does not need.
   At most half of the top line of a batch may be declared: the rest is the melody.
2. **The harmony.** The batch prompt gives the chords the app found in the notes, with their frames. The left-hand
   companion changes the way each chord is played, never the chord: its notes are notes of the chord (a passing
   note now and then is fine), and where a chord begins, its lowest note is the bass of the song there (given as
   "bass" when it is not the root) or the root.
3. **The time.** A note that you keep stays at its frame. A **new** note starts on the **grid** of the song (the batch
   prompt lists the frames of each negra, with the other corcheas of its time in parentheses) or at the frame of a
   note of the target. The grid follows the recording, so a pattern in negras starts on the negras of the grid.
4. **Decoration notes** only where it is very clear that the note is an ornament of the melody (a short note just
   before a melody note, as a singer slides into it). Otherwise give the note a figure of its own (a semicorchea or
   longer), or leave it out when it is an artifact or not melody.

# What you change

- **The left-hand companion**, written again from the chords in the pattern of the section: the song's own left hand
  only tells you the chords, the bass and the rhythm of the song. Octavas or chords the level does not allow are not
  copied.
- **The right hand**: the melody cleaned to the level. Accompaniment chords that the transcription put in the right
  hand (under the melody, or while the melody rests) move to the left hand when they fit its pattern, or are left out
  when the left hand already plays that chord.
- **Artifacts**: a chord or a note far above the melody (more than an octava above the melody around it, alone, often
  under 8va), octavas the level does not allow, many repeated notes of a chord that add nothing. An artifact is **left
  out** (declared): do not keep it one or two octavas lower, it adds nothing to the song in any register.
- **The right hand helps the left hand.** Where the right hand has nothing but artifacts (or nothing at all) while the
  left hand plays big chords, the music of that passage is in the **top notes of the left-hand chords** (a riff, the
  melody of an intro). Read the line of the highest note of each chord: it usually repeats a short figure (in 99 Red
  Balloons E4, E4, C#4, E4, C#4, four times). That line is the melody: every note of it moves to the right hand, in
  its rhythm, at its pitch or an octava higher; a single held note in its place is wrong. The left hand keeps only its
  companion under it. The checker counts those top notes as part of the melody line there
  (each one in the right hand, or declared).

# The patterns

The patterns come from the catalog of the app (a gallery of patterns, numbered inside each hand and level: "left
medium 2" is the second medium pattern of the left hand). The user chose the patterns of this run; they are at the
end of this prompt, each with its number, its name, one line on what it is, and the start of an example written by
the app in the F1 frames text below (both hands of the example: the other hand shows what the pattern goes with).

- Use only the patterns of this run. A left-hand pattern is for the left hand, a right-hand pattern for the right.
- The example has its own melody, harmony and figure scale (its `quarterMs`), not this song's. Copy the **shape**: the
  rhythm in negras and corcheas, the order of the notes (low note, chord, notes of the chord up and down), how many
  notes, how far apart. Then play **this song's chords** in that shape, in the register of this song's bass, on the
  grid of this song. Where the example plays Fa2 then Fa3-La3-Do4 (F2 then F3+A3+C4) on F major, play the root of the
  song's chord low and its triad above it.
- The shape may be shortened or cut where the chord changes before the pattern ends, or where the melody needs the
  space; keep it the same everywhere else.

# Input format: F1 frames

- The first line is `F1 frames frameMs=40 quarterMs=600`: one frame is 40 ms, and `quarterMs` is the length of one
  negra in this song (600 ms here). It is not a tempo and it is never printed.
- The second line gives the key signature (`key=4#`, `key=2b`, `key=0`) and the clefs at the start.
- A note line starts with its frame: `f57` is frame 57 of the song. A line `[]x10` means that 10 frames without any
  note start come before the next line.
- After the frame come the notes of each hand: `L:` left hand (lower staff), `R:` right hand (upper staff).
- A note is `pitch:figure`. The pitch is the scientific pitch name (C4 is middle C; `C#4`, `Bb2`). The figure is the
  note's value: 1 redonda, 2 blanca, 4 negra, 8 corchea, 16 semicorchea, 32 fusa, 64. Notes that share the figure
  are written as one chord, from low to high: `A2,C#3,E3:8`. Tags after a note (`b3` beam group, `8va`, `grace`)
  are drawing marks of the app: you may ignore them, and you do not write them.

# The first request: the plan of the song

Before the batches, one request gives you a summary of the whole song: per stretch of 6 to 10 seconds, its frames,
the chords the app found, how each hand plays now (the measures of a hand tracker: notes per second, the most notes
in one column and how wide they are, the range of the hand inside two negras, the moves of the hand per second, where
the hand is), and the earlier stretch that sounds the same. You split the song into sections and choose the pattern
of each hand for each section, from the patterns of this run: for the left hand, the pattern whose rhythm is nearest to
what it plays now, or `keep` where the summary marks it simple (`L=keep`). Choose few sections and few changes: the song has an
intro, verses, choruses, maybe a bridge; a part that comes again gets the patterns it had the first time. A passage
where the song is calm can take a calmer pattern of the run, and the chorus a fuller one.

# The next requests: the batches

Then the song is written batch after batch (16 to 24 seconds each). Each batch prompt gives your plan (the sections of
the batch marked with `>`), the chords and the grid of the batch, how the hands play now, the end of the previous batch
as you wrote it (to continue the pattern without a break), the earlier passage most like this one as you wrote it
(write the same passage the same way), the **target** (the notes of the batch as the sheet has them now, the notes
you write again), and a look-ahead (the next notes; do not write them). When the run rewrites one hand only, the other
hand is shown as fixed: it stays exactly as it is, and your hand must fit with it.

# How to answer a batch

Reply with one block in triple backticks: the two header lines of the target, the note lines of the batch (frames
from the first frame of the batch to the last one; each frame once, its notes split into `L:` and `R:`), then the
declared lines:

```
F1 frames frameMs=40 quarterMs=600
key=4# clefs: R=treble L=bass
f1042    L: E2:4  R: E5:8
f1050    R: B4:8
f1057    L: G#3,B3,E4:4  R: E5:4
# pattern L f1042-f1440: left easy 2
# pattern R f1042-f1440: right easy 2
# not melody f1084 E4: a fill under the held E5
# artifact f1110 E7: a high note alone, far above the melody
```

- One `# pattern` line per hand rewritten and per section of the batch, with the frames where you use it.
- One `# not melody` or `# artifact` line for each note of the right hand's top line that you leave out (several
  pitches of one frame may share a line: `# artifact f863 D#7,E7: ...`). Other notes of the target (inner notes of
  chords, the left hand) need no line: you write the hands again.
- Write the figure that the note should have: it gives the note its length (a negra lasts `quarterMs`). A note
  lasts at most until the next note of its hand.
- No beams, clefs, 8va, dots, rests or tuplets.

A checker reads the answer. It checks the format; that every note of the melody line is still there (or declared);
that each chord keeps its bass and that the left hand plays the chords; the notes per column and the span of each hand
at the level; how much each hand moves (a hand tracker: an open hand of one octava that moves only when a note is out
of its reach); that each hand declares an allowed pattern; and that every new note is on the grid. If it finds a
problem, the next message lists the problems: then write the whole corrected answer again, in the same way.

# The levels of this run: hard for the right hand, medium for the left hand

The user chose a level for each hand. The two hands are still written together, as one piano part: a note that the transcription put in the wrong hand goes to the hand where it belongs, and each hand then follows its own level below. A hand that plays more must not make the other hand harder: they fit together.

## The right hand at hard

- The **melody on top**, with **small pieces of chords** under it (two or three notes of the harmony) that add to it,
  on the long notes and on the strong points of the phrase (Ballade No. 4). A fast passage keeps a shape that repeats.
- **Powerful two-note chords**: under a melody note, above all in a riff that the right hand took from the left hand
  and on the strong beats, add one note of the chord below it: the fifth or the third of the chord (Do5 with Sol4,
  the fifth of Do major, or with Mi4, its third); change between the two freely, as the chord and the hand position
  allow. It sounds stronger and stays easy to read. The left hand can then play an octava as a negra and then two
  corcheas of the chord.
- Octavas in the right hand are allowed on a few melody notes that need power; not on every note.
- A short fill between two phrases is allowed when it uses the notes of the chord or the scale of the key, in one
  run, and lands on the melody.
- Decoration notes where the song has an ornament on a melody note.
- The checker allows at most 3 right-hand notes in a column on figures shorter than a negra and 4 on a negra or
  longer, within 12 semitones.

## The left hand at medium

- Everything of easy, plus rhythm and patterns as in Chopin's Waltzes. Identify what kind of left hand the song has
  (a bass on the beat and chords after it, repeated chords, a broken chord, octavas in the bass) and find its simple
  equivalent among the patterns of this run; then **keep that pattern through most of the song**.
- Allowed: a low note then two chords (the waltz); a held bass under two chords; the same chord repeated; the same
  chord with one note changing as time passes; **octavas in the bass** (La2-La3) instead of a single low note, to
  give the left hand more power; a broken chord in corcheas that goes up and down (La3, Do4, Mi4, Do4, La3) after a
  low note, then again from the low note, or from the next chord.
- The example of the brief: La2-La3 first, then La3-Do4-Mi4 twice as two corcheas of one beam (an octava, then two
  beamed corcheas of a simple chord). Whatever the pattern, the same pattern in most of the song.
- The chord shapes stay simple (triads, two notes of the triad, an octava); the hand stays in one position after its
  low note, and changes position only when the chord changes.
- The checker allows at most 3 left-hand notes in a column, within 12 semitones (an octava); the low note and its
  chord within 28 semitones inside two negras; and at most 1.25 moves of the hand per negra.

# The patterns of this run

The user chose these patterns in the catalog. Use only these, adapted to the song (see "The patterns" above).

### left medium 2: Low note, then two chords

The waltz left hand: a low note on the first beat, then the same chord on the second and third beats. Medium because the hand jumps every bar, but the chord shape stays and only the bass note changes.

```
F1 frames frameMs=40 quarterMs=600
key=2# clefs: R=treble L=bass
[]x25
f25      R: F#5:4
[]x14
f40      L: B2:4
[]x7
f48      R: G5:8
[]x6
f55      L: F#3,B3,D4:4  R: F#5:8
[]x7
f63      R: C#5:8
[]x6
f70      L: F#3,B3,D4:4  R: D5:8
[]x7
f78      R: B4:8
[]x6
f85      L: C#3:4  R: A#4:2
[]x14
f100     L: F#3,C#4,E4:4
[]x14
f115     L: F#3,C#4,E4:4  R: F#5:4
[]x14
f130     L: A#2:4
[]x7
f138     R: G5:8
```

### left medium 7: Octave bass in negras

Octavas in negras that walk down by semitones (Do, Si, Sib, La, Lab, Sol). Medium because the hand keeps the octave shape and slides; it gives a strong bass without more notes.

```
F1 frames frameMs=40 quarterMs=600
key=3b clefs: R=treble L=bass
[]x25
f25      L: C2,C3:4  R: Eb4,G4,Eb5:4
[]x14
f40      L: C3,C4:4  R: Eb4,Ab4,Eb5:4
[]x14
f55      L: Cb3,Cb4:4  R: D4,Ab4,D5:8
[]x10
f66      R: Gb4:16
[]x3
f70      L: Bb2,Bb3:4  R: D4,G4,D5:4
[]x14
f85      L: A2,A3:4  R: C4,G4,C5:4
[]x14
f100     L: Ab2,Ab3:4  R: C4,D4,Gb4,D5:4
[]x14
f115     L: G2,G3:4  R: D4,G4,Cb5:8
[]x10
f126     R: C4,A4:16
[]x3
f130     L: F2,F3:4  R: Cb4,D4,G4:4
```

### left medium 10: Octava, then an arpeggio

Fa2-Fa3 together, then Fa3-La3-Do4-La3-Fa3-La3 in corcheas. Medium because of the octava and the jump to the arpeggio; the arpeggio itself stays in one position.

```
F1 frames frameMs=40 quarterMs=480
key=1b clefs: R=treble L=bass
f0       L: F2,F3:4  R: A4:4
[]x11
f12      L: F3:8  R: C5:4
[]x5
f18      L: A3:8
[]x5
f24      L: C4:8  R: F5:4
[]x5
f30      L: A3:8
[]x5
f36      L: F3:8  R: E5:8
[]x5
f42      L: A3:8  R: D5:8
[]x5
f48      L: F2,F3:4  R: C5:2
[]x11
f60      L: F3:8
[]x5
f66      L: A3:8
[]x5
f72      L: C4:8  R: A4:4
[]x5
f78      L: A3:8
[]x5
f84      L: F3:8  R: Bb4:4
[]x5
f90      L: A3:8
```

### left medium 15: Octava, then two beamed chords

Fa2-Fa3, then the triad twice in beamed corcheas, twice in each bar (the brief's example of an octava and two corcheas of the chord). Medium because of the jump between the octava and the chord.

```
F1 frames frameMs=40 quarterMs=480
key=1b clefs: R=treble L=bass
f0       L: F2,F3:4  R: A4:4
[]x11
f12      L: F3,A3,C4:8  R: C5:4
[]x5
f18      L: F3,A3,C4:8
[]x5
f24      L: F2,F3:4  R: F5:4
[]x11
f36      L: F3,A3,C4:8  R: E5:8
[]x5
f42      L: F3,A3,C4:8  R: D5:8
[]x5
f48      L: F2,F3:4  R: C5:2
[]x11
f60      L: F3,A3,C4:8
[]x5
f66      L: F3,A3,C4:8
[]x5
f72      L: F2,F3:4  R: A4:4
[]x11
f84      L: F3,A3,C4:8  R: Bb4:4
[]x5
f90      L: F3,A3,C4:8
```

### right hard 1: Melody with small pieces of chords

The melody on top (Sib5, Lab5, Solb5) with a second voice and two-note pieces of chords under it, and a few decoration notes. Hard because the hand plays the melody and part of the harmony (the brief's example of Ballade No. 4).

```
F1 frames frameMs=40 quarterMs=600
key=4b clefs: R=treble L=bass
[]x25
f25      L: Bb2:8  R: Bb5:4
[]x7
f33      L: Bb3,D4,Ab4:8
[]x6
f40      L: F3,Bb3,D4:8
[]x7
f48      L: Eb2:8  R: Db5,G5:4
[]x6
f55      L: Bb3,Db4,G4:8
[]x7
f63      L: Eb3,Bb3,Db4:8
[]x3
f67      R: F5:16
[]x1
f69      R: G5:16
f70      L: Ab2:8  R: Db5,Bb5:8
[]x7
f78      L: Ab3,C4,Gb4:8  R: C5,Ab5:16
[]x2
f81      R: Eb5:16
[]x3
f85      L: Eb3,Ab3,C4:8  R: Ab5:16
[]x3
f89      R: Gb5:16
[]x3
f93      L: Db2:8  R: Eb5,Gb5:8
[]x6
f100     L: Ab3,Db4,F4:8  R: Db5,F5:16
[]x3
f104     R: Ab4:16
[]x3
f108     L: F3,Ab3,Db4:8  R: Db5:16
[]x2
f111     R: C5:16
[]x3
f115     L: Gb2:8  R: C5,Ab5:8
[]x7
f123     L: Bb3,Db4,F4:8  R: Bb4,Gb5:16
[]x2
f126     R: Db5:16
[]x3
f130     L: Gb3,Bb3,Db4:8  R: Gb5:16
[]x3
f134     R: F5:16
[]x3
f138     L: C2:8  R: Bb4,F5:8
```

### right hard 4: Scale run

A fast scale over two octavas or more, with the alterations of its key only. Hard because it is fast and the hand moves, but not super hard: a scale keeps one pattern and one fingering (the user's rule of review 4; it was medium before).

```
F1 frames frameMs=40 quarterMs=600
key=2b clefs: R=treble L=bass
[]x25
f25      R: Eb5:16
[]x3
f29      R: D5:16
[]x3
f33      R: C5:16
[]x2
f36      R: Bb4:16
[]x3
f40      R: G4:16
[]x3
f44      R: F4:16
[]x3
f48      R: Eb4:16
[]x2
f51      R: D4:16
[]x3
f55      R: C4:16
[]x3
f59      R: Bb3:16
[]x3
f63      R: G3:16
[]x2
f66      R: F3:16
[]x3
f70      R: Eb3:16
[]x3
f74      R: D3:16
[]x3
f78      R: C3:16
[]x2
f81      L: Bb2:16
[]x3
f85      L: Eb2,Eb3:4  R: Bb3,Eb4,G4:4
[]x22
f108     L: C2,C3:8  R: A3,Eb4,A4:8
[]x6
f115     L: D2,D3:4  R: A3,D4,F4:4
[]x22
f138     L: G1,G2:8  R: D4,F4,Bb4:8
```

### right hard 15: Chords climbing in corcheas

The triad moved one step up, three times, and back, in corcheas (Fa-La-Do, Sol-Sib-Re, La-Do-Mi, Sib-Re-Fa). Hard because full chords move in one run.

```
F1 frames frameMs=40 quarterMs=480
key=1b clefs: R=treble L=bass
f0       L: F3,A3,C4:1  R: F4,A4,C5:8
[]x5
f6       R: G4,Bb4,D5:8
[]x5
f12      R: A4,C5,E5:8
[]x5
f18      R: Bb4,D5,F5:8
[]x5
f24      R: A4,C5,E5:8
[]x5
f30      R: G4,Bb4,D5:8
[]x5
f36      R: F4,A4,C5:8
[]x5
f42      R: G4,Bb4,D5:8
[]x5
f48      L: F3,A3,C4:1  R: F4,A4,C5:8
[]x5
f54      R: G4,Bb4,D5:8
[]x5
f60      R: A4,C5,E5:8
[]x5
f66      R: Bb4,D5,F5:8
[]x5
f72      R: A4,C5,E5:8
[]x5
f78      R: G4,Bb4,D5:8
[]x5
f84      R: F4,A4,C5:8
[]x5
f90      R: G4,Bb4,D5:8
```

### right hard 17: Melody in octavas

The melody doubled at the octava below. Hard because the hand stays open on the octava and jumps with every note.

```
F1 frames frameMs=40 quarterMs=480
key=1b clefs: R=treble L=bass
f0       L: F3,A3,C4:1  R: A3,A4:4
[]x11
f12      R: C4,C5:4
[]x11
f24      R: F4,F5:4
[]x11
f36      R: E4,E5:8
[]x5
f42      R: D4,D5:8
[]x5
f48      L: F3,A3,C4:1  R: C4,C5:2
[]x23
f72      R: A3,A4:4
[]x11
f84      R: Bb3,Bb4:4
```
