# 7 — Music Notation (Epic 9)

**What this epic did:** turned the matrix into actual sheet music. The backend decides every
engraving question — which figure, where the beams and ties go, which way stems point, which
accidental to draw, when to use an 8va — and the browser only draws the answer.

About 30 minutes. Reuse the slow `Do Re Mi Fa Sol` recording from guide 2, and have a second, busier
recording ready for the beaming steps.

> **Before you start.** The frontend gained two dev dependencies for its render check, so run
> `npm install` in `aitu-frontend` once. Then the usual two terminals:
> `cd aitu-backend && make serve` and `cd aitu-frontend && npm run dev`.

---

## 9.1 — The score appears

Open **Playground → Music Notation**.

The **Score** dropdown lists two kinds of thing:

- `<name> (working)` — whatever you have transcribed, still being iterated on;
- `<Track> - <Artist> (v1_gn)` — a version you saved, which rendered its sheet music the moment you
  saved it.

Pick your `Do Re Mi Fa Sol` take. You should see a **braced grand staff**: treble above, bass below,
a time signature on the first measure, real barlines, and the five notes as negras.

> **What happens when you click.** The frontend asks `GET /notation/<id>` and gets back a plain
> description of the page: measures, each with a list of slots carrying a duration token, dots, an
> accidental glyph, a stem direction and a beam id. It contains no pixels and no music rules — it is
> a shopping list the renderer works through. For a **saved version** that list was written to
> `score.json` when you saved, so the tab is a file read.

The chips under the dropdown should agree with the Matrix tab: measure count, BPM, granularity,
"Grand staff".

**Check the barring.** At 60 BPM with negra resolution, four notes fill one 4/4 measure. Five notes
means two measures; the fifth note expands toward the second measure's closing barline rather than
being followed by a row of rests. A yellow warning says the final event/rest was completed to the
barline. Barlines only mean anything if measures are whole.

Tick **Single hand (treble only)**: the brace disappears and everything moves onto one treble staff.
Untick it.

---

## 9.2 — It wraps like text ⭐

Drag the browser window narrower, slowly.

The sheet must **re-wrap into more systems**, never scroll sideways or overflow. Both staves always
break at the *same* measure, so a treble note and its bass note stay in the same vertical column at
every width.

Now drag the **Measure width** slider. Fewer, wider measures per line, or more, tighter ones.

While you resize, watch the dashed beat guides and their frame numbers: they must stay glued to the
right beats. Nothing on this page has a stored position — every overlay is recomputed from where
VexFlow actually put the notes.

**If it goes wrong:** a sheet that overflows sideways rather than wrapping, or guides that drift away
from the notes after a resize, is the bug this step exists to catch.

---

## 9.3 — Durations and no-tie policy

Look at how long notes were written.

- A note held for two beats inside a 4/4 measure is a **blanca** — one symbol, not two tied negras.
- A note held for three beats is a **dotted blanca**, not blanca-tied-to-negra.
- A note that starts on the last beat fills to the barline. If the following onset is later, the
  next measure begins with a rest; the pitch is not repeated and no tie is drawn.
- Between successive onsets there is **no visible rest**: the preceding note fills that interval.
- Notes struck together remain one chord for that whole interval, even if the recording releases
  some chord keys earlier.
- At a measure ending, the last event expands to one readable figure; only a small unwritable
  remainder becomes a visible trailing rest.

> **Why.** Most transcription software drowns the page in ties and rests trying to be
> millimetre-accurate about releases a human played approximately. This project refuses: the onset
> sequence owns the readable rhythm, chord members share a duration, and an unwritable interior
> residue is only an invisible timing spacer.

---

## 9.4 — Beams, and the Alberti break ⭐

Record something busier: **Do Sol Mi Sol, twice, as corcheas** — a plain Alberti-style
accompaniment. Transcribe it at corchea or semicorchea resolution and open Notation.

Two things to check:

1. Consecutive corcheas of the same length are **beamed together**. A lone corchea keeps its flag.
2. The beam **breaks at each low Do**, starting a new group — not at every dip. `Do Sol Mi Sol` is
   two groups over eight notes, not four pairs.

> **Why this one is fiddly.** The rule is "break at the lowest note of the pattern". Read too
> literally it also fires on the Mi (which is lower than the Sols either side) and chops the
> accompaniment into pairs, which is exactly the visual mush the rule exists to prevent. The
> implementation requires the note to be the low point of its neighbourhood, not merely a dip.

Also check the **stems**: everything in one beamed group points the same way, chosen by the group's
average height. Below the middle staff line stems go up, above it down.

---

## 9.5 — Key signatures and accidentals

With any piece open, change **Key signature** to `Bb`.

The staff gains two flats, and — the point of the step — notes that were printed `A#` are now printed
**Bb with no accidental at all**, because the key already covers them. Set it back to `C` and the
sharps return.

> **What happens when you click.** The key is saved with the version and the whole document is
> rebuilt. Naming a pitch is a small search: for each key on the piano, every letter that could name
> it is scored, and the cheapest wins — free if the key signature covers it, one glyph if it needs an
> accidental, and heavily penalised if it would need a double sharp or double flat. That last penalty
> is why you should never see a `##` or `bb` anywhere.

Two more things to look for:

- **A repeated accidental is not repeated.** The second F# of a measure carries no glyph; an F
  natural after it does carry one. Accidentals last until the barline, as in any printed score.
- **Intentional accidentals survive.** In `E`, an A# stays an A# — it is the normal tension note of
  that key, and no key signature removes it.

Now scroll to **Key signatures**. Add a change: from frame `8`, key `G`. The staff gains a new key
signature at that measure and everything after it is respelled.

Under it, **Per-measure suggestions** lists measures that would draw fewer accidentals in another
key, as clickable chips. Click one to apply it as a passage change.

> These are **suggestions and nothing else**. Nothing is applied automatically, on purpose: a
> composer's deliberate accidental is not a mistake to be optimised away.

---

## 9.6 — Transposition: preview, then accept ⭐

Scroll to **Transposition preview**. Set **From frame** `0`, **To frame** `16`, slide **Semitones** to
`+2`, press **Preview**.

The sheet is replaced by that short passage, transposed. A blue banner says so. Nothing has been
saved — close the banner and the full score comes back unchanged.

This is the check the feature exists for: does the detected key, BPM and granularity actually fit the
audio? A short passage answers that in seconds.

Now press **Accept shift**.

> **What happens when you click.** The shift is applied to the **raw** matrix — the one everything
> else is derived from — and the pipeline re-runs. That is why every other tab follows: open the
> Matrix tab and the rows have moved; open Piano Roll and the notes are two semitones higher.

Check exactly that: go to **Matrix**, confirm the shift, come back.

**Accept shift is disabled for saved versions.** A saved version is immutable; editing one means
loading it in the Playground and saving a new version.

---

## 9.7 — Save annotations, and promote

Press **Save annotations**.

Everything the page decided — key signature, key changes, octave thresholds, and any lyrics or finger
numbers — is written into the version's metadata. **The matrix is never touched from this tab.** That
separation is the whole point of the annotation model: notation choices are a layer over the music,
not the music.

Reload the page and reopen the same artifact: your key signature and key changes are still there.

Now select a **saved version** in the dropdown (if you have none, save one from the Matrix tab first)
and press **Promote to library**.

The dialog pre-fills a name like `Levels - Avicii`, lists anything already promoted, and offers
**keep the existing promotion too** for when you want a second arrangement rather than a replacement.
Promote, then open **Piano Library** and confirm it is there.

---

## 9.8 — Octaves and clefs

Scroll to **Octaves and clefs**. Set **8va from** to `Do-5`.

Any right-hand passage at or above C5 now sits under an **8va bracket**, and — check this — the notes
themselves are written an **octave lower**. That is what a bracket means: play what you read, one
octave up. Set it back to `Do-6` and the bracket disappears.

Set **8vb below** to `Do-3` and watch the left hand get its bracket, written an octave higher.

> **The left hand never gets an 8va.** A left-hand passage that climbs above **Left treble from**
> switches to a small treble clef instead, for a whole measure at a time. With today's middle-C hand
> split the left hand is always below C4, so the default never fires — lower the threshold to see it.

Every threshold has a `—` option that switches that rule off entirely.

---

## 9.9 — Cut measure up to here ⭐

This is the doc's own example, so use exactly its material: play **Do Re Mi Fa as slow negras at
60 BPM**, transcribe at negra resolution, and open Notation. You should see **one 4/4 measure**
containing the four notes.

Tick **Cut measure up to here**. The sheet becomes clickable and a blue hint appears.

Click the dashed guide **at the Mi**. Confirm the dialog.

You should now see:

```
| Do  Re  Mi(blanca) |  Fa ...
```

Two measures. Mi expands to the first barline; Fa opens the second one.

> **What happens when you click.** This is not only a notation trick — timeline columns are inserted
> into the matrix at that frame (exactly enough to reach the next barline), which is the same
> "add tempo" operation the Matrix tab offers. The score does not print those columns as a middle
> rest: it expands Mi to the barline. The pre-edit matrix is kept as `raw_before_edit.npz`.

Two refusals worth confirming:

- clicking a guide that **already starts a measure** says there is nothing to cut;
- with a **saved version** selected, the toggle is disabled and a note explains why.

---

## If it goes wrong

| Symptom | Likely cause |
|---------|--------------|
| Dropdown is empty | Nothing transcribed or saved yet — do guide 4 or 5 first |
| "Building the score…" never finishes | Backend not running, or the artifact has no raw matrix |
| Blank staves, no notes | Run `npm run check:render` in `aitu-frontend`: it draws every known score shape headlessly and will name the one that fails |
| Notes are there but wildly wrong rhythmically | Check BPM and resolution in the Matrix tab first — the notation only reflects them |
| Sheet overflows sideways instead of wrapping | The bug step 9.2 is for; report it with the window width |
| A `##` or `bb` appears anywhere | Spelling bug — the scoring is meant to make doubles unreachable |
| Beams do not break in an arpeggio | Step 9.4; report the actual note sequence, since the rule is neighbourhood-based |

The engineering detail for each step is one folder up in
[`epic-09/`](../epic-09/task-9.1.1-progress.md).

---

## What is deliberately not here yet

- **Tuplets, trills and chord grouping** (Story 9.7) — the nice-to-have ornaments, left for the end
  of the project as the plan says.
- **Authoring lyrics and finger numbers** — the renderer draws them and the format stores them, but
  the UI to *place* them is Epic 12.
- **Two independent voices in one hand.** The score deliberately uses one readable chord voice:
  simultaneous onsets share the duration to the next onset, so partial releases do not split it.
