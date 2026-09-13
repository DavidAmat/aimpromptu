# Epic 12 — Annotations · progress

Status: **done** on 2026-09-13. All three tasks.

One sentence covers all of them: **none of these marks touches the recording.** They live in
`rhythm.json` beside the key, the renamed figures and the beam breaks, they are keyed by frame, they
survive a re-wrap and a PDF export, and **Remove all** clears them with everything else.

## Task 12.1.1 — Lyrics

The frames toolbox has a **Words** tab. Mark a stretch, type the line, press **Write it here**; it
is drawn under the lower staff across that stretch. Hand-independent, because words belong to the
piece rather than to a staff.

A lyric never widens the layout — the spacing of the page comes from the notes (D-22, D-23) — so a
line over a long rest keeps its start and stays there. The performance view hides them with a
**Words** pill beside **Fingering**.

## Task 12.2.1 — Finger numbers

The numbers themselves shipped as P8.1. The two remainders closed here:

- **Mark size.** **Smaller** / **Larger** under the sheet, from half to twice, stored per piece.
  One number for the fingering, the words and the `tr` marks together — three sliders that can
  disagree is three chances to make a page look accidental. Nothing about the staff, the noteheads
  or the spacing depends on it, so changing it can never move a note, and the PDF matches the
  screen. This needed a small feature in `@aimpromptu/grid-notation` (`annotationScale`).
- **The performance-view toggle** was already there.

## Task 12.2.2 — Small notes and grace notes

**Cue-size.** The frames toolbox **Small** tab prints a marked stretch smaller, for one hand or
across both staves. The drawing package already knew how to draw a cue-sized passage; what was
missing was a way to ask for one and somewhere to keep the answer. Widths inside the mark change,
as the task file said they would; nothing outside it moves.

**Grace notes.** Pick one notehead and the note toolbox offers a small note a semitone, a tone or a
third above or below it, **Crushed** (acciaccatura, slashed stem) or **Leaned on** (appoggiatura,
plain). One per note.

Two decisions worth recording:

1. **Intervals, not a pitch picker.** Nearly every grace note in piano music is a step or a third
   from its principal note, and six buttons are faster to use and easier to read back than a picker
   offering all eighty-eight rows.
2. **Drawn in the annotation layer.** A grace note takes no column, so nothing about the spacing of
   the page is measured from it and adding one moves no note — pinned by a test that compares every
   notehead's x before and after. The cost is that a very dense stretch can print one tight against
   what is before it. That is the honest trade: the alternative is a mark that moves the music it is
   only commenting on.

The package gained `graceNotes` in its annotation envelope and a drawing for them
(`src/annotations/grace-notes.ts`, `draw-grace-notes.ts`, six tests). It reuses the cue-size ink
and the existing flag glyph, so no new font metrics were needed — which is what made this task much
smaller than the note in the task file feared.

## Manual trial

Rhythm tab. Mark a bar, **Words**, type a line — it appears under the staff. **Small** on a florid
run — the notes shrink and the other hand does not move. Click one notehead, **Grace note**, *Tone
above*, *Crushed* — a small slashed note appears just before it. **Smaller** twice — every mark
shrinks and no note moves. **Save this rhythm with the piece**, reload: all four come back. Open the
piece in the Library performance view: they are there, and **Words** hides the lyrics.
