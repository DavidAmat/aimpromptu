# 4 — Playground Input (Epic 6)

**What this epic did:** put the five ways of starting a piece behind one tab, added the BPM and
resolution settings, and wired the **Run** button that starts everything.

About 15 minutes. Everything on **http://localhost:5173/playground/input**.

> A successful run sends you to the **Matrix** tab, which is now real —
> [guide 5](epic-07-matrix-tab.md) covers it in full.

---

## 4.1 — The five sources

Across the top of the page there are five tabs: **Upload audio · Record · Audio library ·
Text notation · Matrix JSON**.

The first three you already used in [guide 2](epic-03-audio-io.md). Two are new.

**Notice the layout changes.** On the three audio tabs the page is split — sources on the left,
**Range** and **Transcription settings** on the right. On the two matrix tabs those panels
disappear entirely.

> **Why.** Text notation and a saved matrix file already *are* matrices — there is no audio to
> listen to and no tempo to guess, so asking you for BPM and a resolution would be meaningless.

---

## 4.2 — Text notation

Click **Text notation**. There is a pre-filled example.

Press **Parse notation**.

**What you should see:** a green *"Parsed 8 frame(s) from text notation."*, and the working-piece
strip under the tabs changes to **Text notation**.

> **What this is for.** One line per moment in time. `*Do-4` means *strike* that key, `Do-4` on the
> next line means *keep holding it*, `A || B` on one line means play both together, and an empty
> line is silence. It goes straight to the same matrix everything else produces — **no model
> involved**, which makes it the fastest way to test a musical idea or reproduce a bug.

Now the two-hands case:

1. Turn on the **Two hands** switch → a second box appears for the left hand (bass clef).
2. Type four lines into it while the right still has eight.
   → The left box **turns red**: *"4 frame(s) — must match the right hand's 8"*, and
   **Parse notation** is disabled.
3. Make them the same length → the red clears, the button re-enables.

> **Why they must match.** The two hands are printed one above the other on a grand staff. If they
> had different lengths, the bar lines would not line up. Catching it here — as you type — is
> better than a server error after you press the button.

---

## 4.3 — Matrix JSON

Click **Matrix JSON**.

You have no exported files yet — exporting is Epic 7 — so test the guard instead: pick **any**
`.json` file on your machine.

**What you should see:** a red message naming what is missing, e.g. *"Missing `tempoBpm`."* or
*"This says `sparse: false` but carries neither `denseMatrix` nor `denseRMatrix`."*

> **Why check in the browser.** The server validates properly too, but its answer would be a raw
> `422`. Checking the shape here means the message names the actual missing field.

---

## 4.4 — Transcription settings ⭐

Click **Audio library** and select your `Do Re Mi at 60 BPM` recording.

The right-hand side now shows **Range** (from guide 2) and **Transcription settings** below it.

**Look at the settings before touching anything:**

- **BPM**: `60`
- **Temporal resolution**: a dropdown — Negra, Corchea, Semicorchea, Fusa
- **Engine**: `bytedance`, if you installed it
- A line reading **"Transcribing the whole audio. Select a range above to restrict it."**

> **If a yellow warning says no model is installed**, you skipped `uv sync --extra transcription`.
> You can still press Run — every piece will just come out silent.

**Now the two things worth reading on this panel:**

- BPM's helper text says *"The tempo you played at"* — because everything is snapped onto a grid
  derived from this number, and getting it wrong drifts your notes.
- The resolution's says *"Changeable later without re-transcribing"* — which is the promise you
  verified at the end of guide 3.

### Restrict the range

Drag the range handles to cover roughly the middle three notes.

**What you should see:** the line under the settings changes to
**"Transcribing only 00:01.000 – 00:04.000"**.

> Dragging a handle out and back does **not** count as a range — only a selection genuinely
> narrower than the file restricts anything.

### Run it

Set the resolution to **Negra** and press **Run transcription**.

**What you should see, in order:**

1. The button disables.
2. A progress bar appears, and the label above it **changes as it goes**: `transcribe`, then
   `events`, `collapse`, `clean`, `two-hands`.
3. When it finishes, the app **jumps to the Matrix tab** — which shows the Epic 7 placeholder.

> **What happened when you pressed Run.** The browser asked the backend to start the job and got
> back a ticket number immediately — it did not wait. It then opened a live connection to follow
> that ticket, which is what moves the bar. Meanwhile the backend ran the five stages from guide 3
> on a background thread. When the connection reports the job is finished, the app moves you on.
>
> This is the first moment where the progress plumbing built in Epic 1 meets the pipeline built in
> Epic 4 — **the most likely thing on this page to need a fix.**

### Look at the result

```bash
ls aitu-backend/data/audio/<uuid>/matrices/
curl -s "127.0.0.1:8765/matrix/<uuid>?granularity=negra&step=clean" | python3 -m json.tool | head -20
```

If you restricted the range to three notes, the matrix should have roughly **three columns**, not
five.

---

## 4.5 — The whole loop

To feel the intended flow end to end:

1. **Record** tab → record a new short phrase → save it.
2. It is selected automatically; its waveform appears.
3. Drag a range around the bit you like.
4. Set BPM and resolution.
5. **Run transcription** → watch the stages → land on Matrix.

That is the loop the whole product is built around. Everything from Epic 7 onwards is about
*seeing* what comes out of it.

---

## What "working" looks like

- Five source tabs; the layout adapts for the two matrix ones.
- Text notation parses and reports its frame count; mismatched hands are caught as you type.
- A wrong JSON file is rejected with a message naming the field.
- Selecting an audio fills the range panel and enables **Run**.
- A range narrower than the file changes the "Transcribing only…" line.
- **Run** shows the five stage names in the progress bar and lands on the Matrix tab.
- The matrix files exist and reflect the range you chose.

## If it goes wrong

| Symptom | Likely cause | What to do |
|---|---|---|
| **Run** disabled | No audio selected | Pick one from the library first |
| Bar sits at 0%, terminal shows progress | The live connection is not reaching the browser | Check the console for an `EventSource` error and tell me |
| Bar reaches 99% and stops | The "finished" signal is not arriving | Same — this is the contract between Epics 1 and 4 |
| Never navigates to Matrix | The job errored | The bar turns red with the reason; also check the terminal |
| Matrix comes out empty | The `silent` engine is selected | `uv sync --extra transcription`, then pick `bytedance` |
| Range ignored | Your selection is the whole file | Check the "Transcribing only…" line before pressing Run |

Next (optional, terminal only): [5 — Matrix core](epic-02-matrix-core.md)
