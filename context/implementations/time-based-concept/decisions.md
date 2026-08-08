# Frozen decisions

Every task in [`plan.md`](plan.md) cites these by id. **A task may not reinterpret a decision.** If
implementation shows a decision is wrong, record it in [`progress/issues.md`](progress/) and stop.

Rationale is kept short here; the argument is in [`PRD.md`](PRD.md).

---

## A. The time model

**D-01 — A frame is a fixed number of milliseconds.**
Default **40 ms**. Configurable per piece, recorded in the matrix metadata header as `frameMs`.
No BPM is involved in building the matrix, ever.

**D-02 — Onsets snap to the nearest frame.**
Column index = `round(onset_seconds * 1000 / frameMs)`. Deterministic; the same audio always
produces the same columns.

**D-03 — The unsnapped float timestamps stay the source of truth.**
`events.json` remains authoritative for every measurement and for playback. The matrix is a
*derived, quantised view*, never the record of what was played.

**D-04 — Chord and arpeggio grouping happens on raw times, before snapping.**
Window **20 ms**, non-chaining — a group admits later onsets within 20 ms of the group's **first**
onset, not of the previous one. The whole group then snaps to a single frame together.
*Why:* two notes 39 ms apart can straddle a frame boundary, so "same frame = same chord" is
phase-dependent and unreliable if grouping is done after snapping.

**D-05 — Notes shorter than one frame are dropped.**
A sub-40 ms note is an engine artifact, not a note.

**D-06 — Measured sustain is stored, capped at one redonda of the active ladder.**
Anything beyond the cap is silence. The stored sustain is *measurement*; it does not decide the
printed figure (see D-14).

## B. Measurement

**D-07 — All peak finding and ladder fitting runs on raw timestamps. Never on snapped columns.**
*Why:* snapping splits every peak. A real 337 ms gap becomes 8 or 9 frames depending on phase, so
it appears as 320 ms ~57 % of the time and 360 ms the rest — one clean spike holding half the data
becomes two half-height spikes. Measured, not assumed.

**D-08 — Peaks are computed for the whole piece by default, and for any user-selected passage on
demand.**

**D-09 — The app never chooses the ladder. The user does.**
Interval statistics fix the ladder only up to a rational factor; on this piece's second half two
candidates scored within 0.1 % of each other. The app presents; it does not decide.

**D-10 — Naming one peak fixes the whole ladder by proportion, and the UI shows the consequence
immediately.**
Click the 337 ms peak → "negra" → every other peak is instantly labelled (211 → corchea,
125 → corchea, 674 → blanca …) so the user can judge the choice before committing.

## C. Figure assignment

**D-11 — A gap maps to the nearest figure by proportion, not by milliseconds.**
Compare `|log2(gap / candidate)|`, not `|gap − candidate|`.
*Why:* with negra = 320, a 120 ms gap is exactly 40 ms from both 160 and 80 — a coin toss in
absolute terms. Proportionally it is 25 % vs 50 %, so corchea wins cleanly and always.

**D-12 — Figure vocabulary is closed.**
`redonda, blanca, negra, corchea, semicorchea, fusa, semifusa`, plus **dots on `blanca` and `negra`
only**. No other dotted figure exists.
*Why:* with dotted corcheas banned, the swing pair 211 / 125 both land on *corchea* — exactly what
the printed sheet shows. Allowing the dot pulls 211 to a dotted corchea and recreates the ragged mix.

**D-13 — No ties, no ligatures.** Ever. A duration that needs one takes the nearest single figure.

**D-32 — Three even notes dividing a beat are marked as a tresillo, not rounded to the nearest
figure.**
The vocabulary of D-12 is a ladder of halves, and a ladder of halves has no name for three even
notes filling one beat: at a negra of 300 ms they land 100 ms apart, which is a bad corchea (150) and
a bad semicorchea (75). Forced onto the nearest figure they print as a ragged mix, which is the exact
failure this refactor exists to remove, one level down.
The rule is deliberately narrow, because a wrong tresillo is worse than a missed one. **Three notes
in a row in the same hand qualify only when their three gaps match each other (within 12 %) and that
gap is a third of a figure the ladder already knows (within 15 %).** Requiring the gaps to match is
what says the player was dividing a beat into three rather than playing something else at a similar
speed. Groups do not overlap: six even notes are two tresillos, never four.
The three notes keep the **ordinary figure one step below** the one they divide — a tresillo of a
negra is three corcheas. The number 3 and its bracket are what make it a tresillo, so the glyphs stay
conventional. `fitError` is zero for them: they are exactly what the mark says they are.
Dotted figures cannot be divided, because a dotted figure already divides into three and a triplet of
one would be a second way of writing the same rhythm.
On the peak plot, a pile at a third of the **negra** — and only the negra, within 8 % — is named
"corchea de tresillo" rather than a 33 %-wrong corchea. Only the negra, because two thirds of a negra
is also a third of a blanca and the long half of a swung pair lands almost exactly there; naming that
a tresillo would tell a reader the piece is in triplets when it is shuffled.

**D-14 — Printed length = time from this onset to the next onset in the same hand.**
Per **hand**, not per key. A chord is the group from D-04; its length runs to the next onset in that
hand.
*Accepted cost:* a held note inside one hand is cut short when that hand plays anything else. This is
deliberate — the alternative fills the page with ties, rests and inner voices, which is the ugliness
being removed. The player already knows the piece.

**D-15 — Maximum printed value is one redonda.** Longer gaps print a redonda; the remainder is
silence.

**D-16 — No rest glyphs.** Silence is read from consecutive frame-group dashed lines with small
padding between them.

**D-17 — Per-note figure override.**
Stored in the score metadata as a `figure-override` keyed by (hand, column, row). Changes that one
glyph and nothing else: no re-flow, no renumbering, no effect on any other note.

**D-34 — The reader can break a beam on any note, and that beats every automatic grouping.**
Beaming groups what is *regular*: one hand, one key, one clef, no tuplet boundary. A long run
climbing through an arpeggio has none of those inside it, so it beams as one shapeless slope with
stems reaching across two octaves — where a player hears two gestures. The package already cuts a
run at a **returning low note**, which catches the common arpeggio; it cannot catch the rest,
because where a phrase restarts is a reading of the music rather than a property of it.
So there is one grouping input that is a judgement: select a note, press **Break the beam here**,
and that note begins the next group. It is applied last, after every automatic split, because a
person's answer beats the rules rather than competing with them.
Stored as `BeamBreak { hand, startFrame }` — the note's own column and nothing else. It is the twin
of D-17: it changes how the page is grouped and nothing about the music, no note is renamed, and
because a column never moves it survives a ladder change untouched.
A break that would strand the first note alone is not an error: that note takes a flag, which is what
a lone corchea is.

**D-18 — "Figure shift": re-point the whole ladder by one or more steps.**
`negra = 300` becomes `blanca = 300`, and everything below shifts with it. Used to rewrite a fast
passage as corcheas rather than semicorcheas. Purely a relabelling; positions do not move.

## D. Passages

**D-19 — Passage boundaries are drawn by hand. No automatic segmentation in v1.**
*Why:* a wrong hand-drawn boundary spoils one section; a wrong automatic one scatters tempo changes
across the piece and makes the sheet unreadable. The sliding-window scan is deferred to a later
iteration as a *suggestion* the user may ignore.

**D-20 — Each passage prints its ladder in its header: `negra = 320 ms`, plus the equivalent BPM.**
This replaces the old `♩ = 178` tempo mark. Both are shown because they carry the same information
and some users think in BPM.

**D-21 — Changing a passage's ladder must not move anything outside that passage.**
Verified by diffing rendered x positions, not by inspection.

## E. Layout

**D-22 — One `time → x` map for the whole system, built from both hands' onsets merged.**
Every staff, every ruler and every overlay reads from that one map. This is already the documented
contract of `FrameGrid` in the renderer ("the only frame ↔ x transformation in the package") and it
gains variable widths rather than changing shape.
*Consequence:* the "which hand is limiting this region" question disappears — it falls out.

**D-23 — Silence is compressed.**
A run of frames with no onset on either hand collapses to a small fixed padding per frame group, so
a 5-second rest shows as five closely-spaced dashed lines rather than five seconds of blank page.

**D-24 — Onsets within the near-simultaneous window share one x, across both hands.**
Same 20 ms window as D-04. Hands that land 15–30 ms apart are drawn aligned; hands that land
150 ms+ apart are drawn visibly apart.

**D-25 — A note with no counterpart on the other hand is placed by its time fraction.**
A left-hand note 100 ms into a 400 ms gap between two right-hand notes sits a quarter of the way
across, not halfway.

**D-26 — Spacing between consecutive events is constant within a passage.**
Falls out of D-22; not a separate mechanism.

**D-33 — A beamed run is set tighter than the same notes unbeamed, and renaming a passage
therefore moves the notes inside it.**
A beam carries the eye across a group, so the whitespace between its noteheads is doing no work and
full width makes a run read as loose separate notes. A beamed onset keeps 35 % of the usual space
after it, and the empty columns inside a run shrink by the same fraction — but only columns nothing
else has claimed, so a column carrying the other hand keeps its width.
*The cost, stated plainly:* the width of a column now depends on the printed figure, and renaming a
ladder changes printed figures. So the notes inside a renamed passage shift horizontally. **D-21 and
success criterion 2 still hold** — nothing outside the renamed passage moves, which is the property
that matters, because correcting the end of a piece must not make a reader re-read the beginning.
What does not hold is the stronger "renaming moves nothing at all", which was true before beaming
existed. `vexflow-v2/tests/ladder-locality.test.ts` pins both halves of this.

**D-27 — Two aggregation levels above the frame.**
`frameGroup` = N frames, the selectable/clickable unit in the UI.
`frameMeasure` = M frames, where a dashed vertical line is drawn.
Both configurable; both are pure wall-clock, both are UI concepts with no musical meaning.

**D-28 — No bar lines, no time signature, no metre.** The concepts are removed, not hidden.

## F. Playback, storage, pipeline

**D-29 — Every player plays the original recorded onset times.** Nothing inferred is ever heard.

**D-30 — The sparse matrix stays the portable format**, with a metadata header carrying `frameMs`.
The raw transcription (onsets + measured durations) does not have to be a matrix; the matrix is the
converged form everything downstream operates on.

**D-31 — The hand split runs on the snapped time matrix**, after conversion, before everything else.

---

## Decision index

| id | one line |
|---|---|
| D-01 | frame = fixed ms, default 40, in metadata, no BPM |
| D-02 | onsets snap to nearest frame |
| D-03 | raw float timestamps stay the source of truth |
| D-04 | chord grouping on raw times, 20 ms non-chaining, before snapping |
| D-05 | drop notes shorter than one frame |
| D-06 | store measured sustain, capped at one redonda |
| D-07 | measure on raw times, never on columns |
| D-08 | peaks per piece and per selected passage |
| D-09 | the user names the ladder, never the app |
| D-10 | naming one peak labels the rest by proportion, shown immediately |
| D-11 | nearest figure by proportion, not milliseconds |
| D-12 | closed vocabulary; dots only on blanca and negra |
| D-13 | no ties, no ligatures |
| D-14 | printed length = onset to next onset in the same hand |
| D-15 | max printed value is a redonda |
| D-16 | no rest glyphs |
| D-17 | per-note figure override, local effect only |
| D-18 | figure shift re-points the whole ladder |
| D-19 | passage boundaries drawn by hand; no auto segmentation |
| D-20 | header prints `negra = X ms` and the BPM equivalent |
| D-21 | a ladder change moves nothing outside its passage |
| D-22 | one merged time → x map for the whole system |
| D-23 | silence compressed to padding per frame group |
| D-24 | near-simultaneous onsets share one x across hands |
| D-25 | orphan notes placed by time fraction |
| D-26 | constant spacing between events within a passage |
| D-27 | frameGroup (selection) and frameMeasure (dashed lines) |
| D-28 | no bars, no time signature, no metre |
| D-29 | players play the recorded times |
| D-30 | sparse matrix stays portable, header carries frameMs |
| D-31 | hand split runs on the snapped time matrix |
| D-32 | three even gaps at a third of a known figure are a tresillo, marked not rounded |
| D-33 | beamed runs set tighter; renaming moves notes inside the passage, never outside it |
| D-34 | the reader may break a beam on any note; it beats every automatic grouping rule |
