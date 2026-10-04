# Picking notes, scrubbing the recording, and a rectangle worth reading

**Commit `db6673e`, 2026-08-10.** Reported 2026-09-13 by Task 14.1.1.3.

Ten changes from one review walk of the two restored views.

## Position has one home

Both views get a **scrub bar with a draggable handle** over the whole piece, and the roll's playhead
can be grabbed and dragged.

In exchange, **clicking the canvas no longer seeks — it selects.**

One surface, one meaning. That is what lets a click on a rectangle mean "this note" without also
jumping the recording somewhere nobody asked for. Space plays and pauses, standing down while a
text field has focus.

## Notes can be picked and deleted

Click one, ⌘-click to add, or drag a band over several, on either view. A floating panel says what
is selected and offers to take it off — **the same panel the sheet opens on a note**, deliberately.

**A delete is not a filter on one screen.** It is written onto the note event, next to the hand
correction and for the same reason: the printed length of a note is the gap to the next onset, so
removing one **renames its neighbour**.

Everything is derived from these events, so `removed` on `NoteEvent` plus one filter in
`impose_granularity_and_split` is the whole mechanism, and the roll, the gap plot and the sheet
agree without coordinating.

Measured: the printed sheet went 2639 → 2638 → 2639 across a delete and a restore. Flagged rather
than dropped, so it comes back, and `PUT /matrix/{id}/events/removed` is the same route both ways.

## The rectangles

They were drawn into an SVG stretched with `preserveAspectRatio="none"`, so the two axes scaled by
different amounts and **every label came out squashed — no font size could have fixed it**. Both
views now measure their box and use a viewBox of real pixels, which also means a 2 px border is
2 px.

On top of that:

- **Montserrat, self-hosted**, because the label is three characters inside a shape a few pixels
  tall and the UI stack's fallbacks vary by machine.
- **English names, not `Do#-5`.** `C#5` where it fits, `C#` where it does not, and nothing at all
  below that — the accidental is never dropped, since `C` for a C sharp is a *wrong* answer rather
  than a short one.
- **Centred on both axes**, and on the falling view horizontal rather than turned on its side.
- **Border weight follows the note's drawn length** and stops at 2 px, so a row of short notes stops
  reading as a dotted line and length is legible at a glance.
- **Fill is the light shade at 88 %**, so the waveform behind shows through and black text is
  readable on it; the border is the dark shade of the same hue.
- **Corners round with the short side** rather than at a fixed radius.

## Also

The **Rhythm** tab is now called **Piano Sheet**. Its route is still `/playground/rhythm`.

A band drag no longer highlights the ruler labels as if they were prose.

## Verified

In a browser against a real recording: scrub 00:00 → 02:02, playhead drag +2.00 s for 240 px at
120 px/s, canvas click leaves the position alone, band selects 21 on the roll and 16 on the falling
view, delete removes exactly the 26 picked, Space toggles both ways. Backend suite green.
