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
- **An octava as a third or a fifth** (the user's way to make an octava easy to play; also whenever the user's words
  ask for "thirds or fifths instead of octavas"). Keep the note that matters (the melody note on top in the right
  hand, the bass at the bottom in the left hand) and replace the other note of the octava by the **third or the fifth
  of the chord that sounds there**, inside the octava. The user's example: under the chord Si-Re-Fa# (B minor), the
  right hand's Si3-Si4 becomes Re4-Si4 (Re is the third of the chord) or Fa#4-Si4 (Fa# is the fifth); in the left
  hand, under Mi major, Mi2-Mi3 becomes Mi2-Si2 (the fifth) or Mi2-Sol#2 (the third). When the note of the octava is
  itself the third or the fifth of the chord, take another note of the chord (its root or the other one); never a note
  out of the chord. Keep the same choice for the same note on the same chord, so the passage keeps one pattern. Use it
  where the level takes an octava away but allows two notes (the right hand at medium and hard, on the notes where
  it may play two; an octava bass), and everywhere the user's words ask for it. At easy the right hand still plays
  single notes.
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
what it plays now, or `keep` where the summary marks it simple (`L=keep`). A hand for which the user chose no
pattern (the end of these instructions says so) is `free`: write it by the rules of its level and the user's words only.
Choose few sections and few changes: the song has an
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
