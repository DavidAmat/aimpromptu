# Levels: the catalog of patterns, the grid, the chords of the song

> Context: [context/ai/README.md](README.md). The code of the levels is in
> [documentation/services/backend/ai-levels.md](../../documentation/services/backend/ai-levels.md).

A **level** is how hard a hand plays a passage of the sheet: **Easy**, **Medium** or **Hard**. A level run
(**Enhance with AI**, the levels part of the dialog) writes a hand again at the level the user chose, in the shape of
a **pattern** the user picked from the catalog. This page tells the levels themselves: the catalog, the grid and
the harmony the AI works on, the chords of a guitar guide, and the two ways a level is written (in place, or as a
copy of the whole song). How a level run writes, checks and stops is in [level-run.md](level-run.md).

## What the user does

In the **Enhance with AI** dialog (see [README.md](README.md) and [whole-run.md](whole-run.md)):

- **A stretch** tab, with a range selected: choose a level for the right hand, the left hand or both. The level
  is written in place, one step of undo.
- **The whole song** tab: choose a level per hand. The level goes into a new project (a level copy); the original
  does not change.
- Under the level, the **gallery of patterns** of those hands (`PatternGallery`, in `PatternCatalog.tsx`). Each
  pattern is drawn from its example, with its name, one line of what it is, and its source. The gallery has four
  tabs: **Easy**, **Medium**, **Hard**, **Super hard**.
- The patterns approved for a level are ticked by default. **Deselect all** unticks a hand (that hand then has no
  pattern, and the AI writes it by the rules of its level and the words only). **Approved** ticks the approved
  patterns again.
- **Words** (optional): the user's own words for the AI.
- **Chords of the song (optional)**: a guitar guide pasted with the lyrics. See section "The chords of the song".

The level choice itself offers **Easy**, **Medium** and **Hard** only. The gallery's **Super hard** tab shows the
super hard patterns, which the catalog holds (section "The catalog"); no level writes at super hard yet.

## The catalog of patterns

The catalog is the list of patterns the AI may use. It lives with the backend
(`sheet/llm/catalog/patterns.json`, with an example of each pattern as an F1 file in `catalog/examples/`). It holds
**114 patterns**:

| Hand | Easy | Medium | Hard | Super hard |
|---|---|---|---|---|
| Left | 15 | 19 | 18 | 2 |
| Right | 10 | 17 | 20 | 13 |

- A pattern has a **ref** such as `right easy 1` (hand, level, number). The number is inside its hand and level, in
  the order of the gallery. A new pattern takes the next number of its level.
- Many patterns come from the real pieces the research used (a prelude, the ballades). Others were drawn for the
  project; their examples are named `drawn-…`.
- **Left easy 1** is **The song's chords** (2026-10-31, the user): the chord of each stretch in steady blancas. The
  other left easy patterns moved one number up.
- The **approved set** (the patterns used when a hand has none ticked): right easy 2 and 1; right medium 1, 14, 13;
  right hard 1, 17, 15, 4; left easy 1, 3, 2, 4, 13; left medium 15, 2, 10, 7; left hard 11, 2, 3, 16. The left
  hard set was not tested in the research; it is the hard form of the left medium set.
- The **super hard** patterns (2 left, 13 right) are in the catalog and in the gallery. No level of the dialog
  writes at super hard yet, so they are only shown there.

## The grid: where a note may start

The sheet has no bars, so a level cannot say "beat 1, beat 2". A level adds notes at new times (a bass note, then
a chord). Those times must match the recording, or the cursor and the lit notes would not match what the user hears.

The **grid** of the song gives the times where a new note may start, in frames of 40 ms:

- the **negras** and the **corcheas** of the song, from the beat tracker (the pulse is tracked at two periods and
  the steadier one is kept);
- the division of a negra into two corcheas, or three when the song is ternary;
- the **semicorcheas**;
- the **onsets** of the original notes, in both hands (a level may always start a note where the recording has one).

A frame is on the grid when it is within one frame of a point.

## The harmony: the chords the app finds

A level changes how a chord is played, never the chord. The app finds the chord of each stretch from the notes of
the sheet, with no AI: each negra of the grid gets a weight per pitch class (the lowest left-hand note counts more),
and the weights are matched with the chord templates (major and minor triads, the dominant seventh, the diminished
triad, on the 12 roots). Negras with the same chord join into a **stretch**. Chords are named with letters
(`E`, `C#m`, `B7`, `D#dim`).

The chords of each stretch go into the plan of the song and into the check of an answer: the AI must keep the
harmony the recording has, and the check tells it where the harmony changes and which bass it has there.

## The hands: how hard a passage is

Difficulty is a matter of the hand's movement, of the patterns it keeps, and of how many notes it plays. For each
hand of a passage the app measures: the notes and the columns per second, the widest column (the span), the
widest range of the hand in two negras (the jump to a chord counts here), the moves per negra, the big moves and
the fast moves, and the share of moves that repeat a shape. The measures are per second and per negra, so a pattern
moves as often per negra at any tempo. They go into the summary of the song the plan reads, and the check of a
level measures each answer against them.

## The chords of the song

A guitar guide gives the chords above the lyrics. The user can paste it into the dialog (**Chords of the song
(optional)**, saved with the song). The app reads every line whose words are all chord symbols (`C  F  C`,
`Am  Em`, `C4` for a Csus4), and the AI follows their order to find where each part of the guide sounds in the
song. The guide shows the order of the chords, not their exact time, so the AI matches its sequence to the notes.
If the recording is in another key than the guide, the AI moves the guide's chords to the key of the recording.

The guide is saved with the **part** (`parts[].chords` in `project.json`), so the dialog shows it again and a level
copy has it. Every level request sends it to the AI.

## A level in place, and a level copy

- **In place**: a range of the sheet at a level is written again in the part. One step of undo.
- **A level copy**: the whole song at a level becomes a new project in **My projects**, named with the song and the
  level (`99 Red Balloons · Easy`, `Easy, left hand`, `Right hard, left medium`). The original does not change. The
  copy shares the song's metadata, and it takes the original's folders when the original is in My projects. It is
  not an edit copy. A copy can be made only of the user's own
  projects and versions of My Library. A level of a level has the same original as the first copy.

## Limits

- The gallery shows the super hard patterns, but no level of the dialog writes at super hard yet.
- The left hard set was not tested in the research (section "The catalog").
- A level copy is for the user's own songs; the original is never changed by it.

## Where to look deeper

- [documentation/services/backend/ai-levels.md](../../documentation/services/backend/ai-levels.md): the catalog's
  files, the grid, the harmony, the hands, the chords, the level copy, the routes
- [documentation/services/backend/ai-runs.md](../../documentation/services/backend/ai-runs.md): the jobs and the
  routes that every run shares
- [whole-run.md](whole-run.md): the whole run, the other way to rewrite a song
- [README.md](README.md): the AI in the app, the kinds of run
