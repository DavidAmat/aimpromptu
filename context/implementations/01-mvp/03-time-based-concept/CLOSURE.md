# Time-based concept — closed

> **Status: CLOSED on 2026-08-10.** Nothing in this plan is waiting to be worked on. Two boxes were
> left undone on purpose; they are named below with the reason. **No task from this plan carries
> forward.**
>
> **Corrected 2026-09-13 by Task 14.1.1.** This document was written on the day the plan closed and
> described the app as it stood that morning. Work started again that same afternoon and did not
> stop, so several statements below — chiefly §3, "what was removed" — had been wrong for a month.
> §8 at the end is new and says what happened next; §3 now points at it. Nothing else has been
> rewritten: this is still the record of what the plan itself did.

This was the project's kickoff plan. It started as "fix the rhythm figures" and became a change of
model, which is why it grew from a fix into eight phases across two repositories. The model is now
in place and the app runs end to end on it, so the plan has done its job and is closed.

---

## 1. What the plan was for

The app used to write music the way a metronome hears it. You told it a tempo and a note
resolution, it built a grid of *note figures*, and it fitted your playing into that grid. Playing
that was even came out ragged — a run of equal notes printed as a mix of sixteenths and dotted
eighths, every time — because no human plays exactly on a grid and the grid was not asking.

The new model turns that around:

- **Where a note sits on the page is measured wall-clock time.** A column is a slice of real time
  (40 ms by default). Nothing is fitted to anything.
- **What a note is *called* is a label you choose.** You look at a picture of how the piece was
  actually played, click the gap that keeps repeating, and give it a name — "that is a quarter
  note". Every other note takes its name from that one choice.
- **There is no tempo anywhere in the app.** Not in the transcription, not in the drawing, not in
  the file formats.

Renaming notes moves nothing. Changing your mind costs one click and no re-timing.

---

## 2. What shipped

### The engine

Audio in → the notes as they were actually played → split into two hands → a picture of the gaps
between them → your chosen name → figures → a drawn staff. Every step re-derives itself from one
stored file of raw played notes, so nothing on the page can quietly disagree with the recording.

The drawing package (`@aimpromptu/grid-notation`) no longer contains a beat at all: no bars, no
time signature, no metre, no engraved spacing table, no tempo callback and no reader for the old
file format.

### The screens

The Playground has two tabs, **Upload / Input** and **Rhythm**, and the Rhythm tab is the whole
product: the picture of the playing, the naming, speed changes, the sheet, the player and every
editing control.

What a reader can do on the sheet today:

| | |
|---|---|
| Name the beat | Click a bar in the plot, give it a name, write the sheet |
| Write the whole piece longer or shorter | Two buttons, one step at a time |
| Say the piece changes speed | Mark a stretch, say what a gap is worth from there on |
| Rename one note, or a whole passage at once | The note toolbox; a marked band renames every chord it touches |
| Choose the key, for the piece or for a stretch | A picker beside the sheet; a suggestion is measured from the notes |
| Correct which hand plays a note | Written onto the recording, so everything downstream follows |
| Fingering 1–5 | Stacked in notehead order on a chord |
| Break or join a beam | On any note, applied after every automatic rule |
| Octave brackets | Only where you ask for one; nothing is suggested |
| Take a note off the page | For notes the transcriber invented out of a pedal blur |
| Save the reading with the piece | A floating bar that follows you down the page; **Remove all** clears everything |
| Print it | A4, real page re-wrapping, vector PDF, about five lines to a page |
| Play it and follow along | A line down both staves, read from the recording, and a bar you can click to seek |

### The evidence it works

Four of the six things we said would prove the model were measured and hold:

1. The passage at 00:46 that used to print as semicorchea / dotted corchea / semicorchea now prints
   as three equal eighth notes.
2. Renaming inside one stretch of a piece does not disturb any other stretch.
3. Two runs on the same audio give the identical result, with no tempo supplied.
4. A held left-hand chord under a fast right-hand run prints as one long note, correctly aligned.

---

## 3. What was removed, and what has since come back

The Playground had seven tabs. Five were deleted: **Matrix**, **Piano Roll**, **Notes Falling**,
**Notes Falling (raw)** and **Music Notation**. All five asked for a tempo and drew from a grid
built out of it, so they could not survive the model change.

> **Two of them came back on 2026-08-10**, the same day this was written, rebuilt on the wall clock:
> **Piano Roll** and **Notes Falling** now draw `GET /matrix/{id}/events` in seconds and ask for no
> tempo and no resolution. See §8. The paragraph below said otherwise for a month; it is kept, struck
> through, because deleting it would hide that this document was wrong rather than that the app
> changed.

~~Stated plainly, so nobody rediscovers it later: there is **no piano-roll view**, **no
falling-notes view**, no editing a cell by hand, and no matrix import or export.~~

What is still true: there is **no editing a cell by hand** and **no matrix import or export**.
**Matrix**, **Notes Falling (raw)** and **Music Notation** stay retired — the first two were views
of a grid that no longer exists, and Music Notation is the Piano Sheet tab now. The two ways of
making a piece without a recording, **Text notation** and **Matrix JSON**, are gone from
Upload / Input for the same reason as always: a sheet is written from recorded onsets and neither of
those had any.

If one of these should come back on the wall-clock path, it is a feature request, not unfinished
work.

---

## 4. What was left undone on purpose

Two things were open when the plan closed. **David's decision on 2026-08-10 was to close anyway**,
because the app works and the useful next input is a round of real piano playing, not more
checklist. They are recorded here as dropped, not as pending — nobody should pick them up as
inherited work.

**P1.7 — the data safety check.** There is a step in the backend that inspects the note data and
tidies up anything odd before it is drawn. It was written for the old beats model and never
rewritten for the time model. Nothing is currently guarding the output of a transcription.
*Dropped.* If a real piece produces something visibly wrong, that is the moment to write this, and
it goes into the new plan with an actual failing case attached — which is a better specification
than the one this box ever had.

**The sign-off phase — the last two success criteria.** Two of the six were never run: does the
sound stay lined up with the page over a full five-minute piece, and did every already-saved piece
make it across to the new format. *Dropped.* Both are answered better by using the app on real
music than by a test written against the one piece we already know. The migration and its warning
flag exist and are tested; only the "run it and record the result" step was skipped.

Also never done: a **regression on a second, straight-feel piece**, to prove the reading is not
overfitted to *Mr Blue Sky*. The round of real playing replaces it.

**One known gap, worth naming.** A piece that changes key part-way through can be drawn but not
saved. The drawing package handles it; nothing stores it.

> **Closed since.** `SavedRhythm.keyChanges` stores them now. A *different* gap of exactly the same
> shape was found on 2026-09-13 — octave brackets were sent by the page and dropped by the backend,
> so they did not survive a reload — and closed the same day. Both are stored. See
> [`rhythm-and-annotations.md`](../../../documentation/services/backend/rhythm-and-annotations.md).

---

## 5. The P8 numbering, resolved

There were two different things called P8, and this is the note that stops it costing anyone an
hour.

- `plan.md` reserved **Phase 8** for verification and documentation.
- On 2026-08-08 ten review-driven features shipped, and the commits were also numbered
  **P8.1 … P8.10**.

**The commits win.** In this repository, P8.1 through P8.10 mean the shipped features — the note
toolbox through to renaming a whole passage. They are described in
[`progress/P8.1-P8.10-the-review-stream.md`](progress/P8.1-P8.10-the-review-stream.md). The
verification phase is recorded in [`checklist.md`](checklist.md) as **Phase 9**, cancelled.

The next plan starts its own numbering from scratch and does not continue this one.

---

## 6. Where things are

Both repositories are on the branch **`time-based-concept`**, fully committed, working tree clean.
The last commit of the plan is `0f3b936` (2026-08-08 22:03), plus this closing documentation.

- Requirements and the frozen decisions: [`PRD.md`](PRD.md), [`decisions.md`](decisions.md)
  (D-01 … D-34)
- The interface between backend and drawing package: [`contract.md`](contract.md)
- Every box and its final state: [`checklist.md`](checklist.md)
- One report per task: [`progress/`](progress/README.md)
- What to open and click to see it all: [`user-reviews.md`](user-reviews.md)

`decisions.md` stays frozen and stays valid. A new plan that wants to change one of those decisions
has to say which, and why, in its own document — the record of what we decided and why is the part
of this plan that keeps working after it closes.

---

## 7. What happens next

David plays a round of varied piano music through the app and collects what is wrong or awkward.
That list becomes a new implementation plan, with its own PRD, its own numbering and its own
checklist, in a new folder under `context/implementations/`. This folder becomes history.

---

## 8. What actually happened next

**Added 2026-09-13 by Task 14.1.1.** The round of playing began the same afternoon, and what it
found was fixed immediately rather than collected into a new plan folder. So §7 is right about the
method and wrong about the bookkeeping: there was no new plan, the work went onto the existing epic
backlog, and for a month it had no reports at all.

**2026-08-10 to 2026-08-12 — the `plan-resume` branch.** Piano Roll and Notes Falling back on the
wall clock; picking notes on either view; taking a note off the recording, staged and saved; one
scrub bar for every page, with a draggable playhead; both ends of a marked stretch pullable to any
column; double-click blank ground to seek; and four measured changes that got Chopin's left hand
printing in corcheas. Reports, written late, are in
[`../01-epics-master-plan/progress/plan-resume/`](../01-epics-master-plan/progress/plan-resume/README.md).

**2026-08-12 — the remaining epics were rewritten for the wall clock.**
[`wall-clock-rewrite.md`](../01-epics-master-plan/plan/wall-clock-rewrite.md) restated Epics 10 to
14 against this model and set out the five rules any new work obeys.

**2026-08-12 to 2026-09-13 — Story 9.7 and Epics 10 to 14 shipped**: trills, the Piano Library with
playlists and a performance view, range re-recording, annotations (words, fingering, cue-size
stretches, grace notes), composing a piece one passage at a time, and this documentation pass.

`decisions.md` needed no change through any of it. That is the part of this plan that kept working
after it closed.
