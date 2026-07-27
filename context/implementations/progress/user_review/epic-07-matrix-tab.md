# 5 — Matrix tab (Epic 7)

**What this epic did:** made the matrix visible. Until now a transcription was a `.npz` file you
could only inspect with `curl`. This is the first page that shows you what the app actually heard.

About 20 minutes. You need a transcribed piece — the `Do Re Mi Fa Sol` recording from
[guide 3](epic-04-transcription.md) is ideal.

Everything happens on **http://localhost:5173/playground/matrix**.

---

## 5.1 — Read the grid ⭐

Load your transcribed recording on the **Input** tab, then click **Matrix**.

**What you should see:** a spreadsheet. Across the top, the 88 piano keys — English name (`C4`)
with the Spanish name (`Do-4`) turned sideways above it. Black keys have a darker column, so the
keyboard pattern is visible. Down the left, one row per moment in time, labelled
`f: 3 [00:03.000 – 00:04.000]`.

For your five-note scale you should see **five filled circles stepping down and to the right** —
down because time moves downward, right because the notes go up in pitch.

> **How to read a cell.**
> - **Filled circle** = the key was struck at that moment.
> - **Pale circle** = the same key still being held.
> - **A vertical line** joins them, so one note reads as a solid head with a pale tail.
> - **Nothing** = silence.
>
> That is the entire notation. A note lasting four frames is one filled circle followed by three
> pale ones, joined by a line.

Scroll down — the key names stay put at the top and the frame labels stay put on the left, like a
spreadsheet with frozen headers. Scrolling down is always moving forward in time.

> **A note on long pieces.** Only the rows you can see are actually drawn; the rest are reserved as
> empty space. A ten-minute piece scrolls just as smoothly as a five-second one, and looks
> identical. You should not be able to tell — if scrolling ever stutters, tell me.

---

## 5.2 — The four processing steps

Above the grid are four pills: **raw · collapsed · clean · two-hands**. Click each in turn.

| Pill | What you should see |
|------|---------------------|
| **raw** | Many more rows — the finest resolution, straight from the model |
| **collapsed** | Far fewer rows, same shape — merged to your chosen resolution |
| **clean** | Same rows, but held notes cut shorter |
| **two-hands** | Same again, now in **colour** |

> **These are the five pipeline stages from guide 3, made visible.** Every one of them is derived
> from the same stored raw matrix, so clicking a pill is a request — never a re-transcription. The
> line under the pills explains what each does.

**On `clean`, look for the difference.** If your recording has a low note held under a melody, it
is long on `collapsed` and short on `clean`. That single change is the difference between a
readable page and a wall of tied notes — it is the rule from Appendix B, and this is where you can
finally judge whether you agree with it.

**On `two-hands`**, the colours split at middle C:

- **Blue** — right hand (dark = struck, light = held)
- **Green** — left hand

A legend under the grid names them. If your scale was played above middle C, everything is blue and
the left hand is empty — that is correct, not a bug.

---

## 5.3 — Change the resolution, instantly ⭐

This is the payoff of the whole design.

In the controls under the pills, change **Resolution** from Semicorchea to **Corchea**.

**What you should see:** the grid **halves its number of rows, immediately**. No spinner worth
noticing, no progress bar, no waiting for the model.

Change it back. Change the **BPM** to 120 and watch the row labels' timestamps change while the
circles stay where they are.

> **Why this is instant.** The model's output was saved once at the finest resolution and is kept
> forever. Changing the resolution just re-merges from that — a few milliseconds of arithmetic —
> instead of listening to the audio again, which takes seconds. Changing the BPM does not even
> re-merge: the squares are the same, only what they *mean* in seconds changes.
>
> This is why the resolution dropdown feels like a filter rather than a job, and it is the single
> most important thing to confirm works.

---

## 5.4 — Jump to a moment

In **Go to frame or time**, type `2` and press Enter → the grid scrolls to frame 2.

Now type `0:03.000` and press Enter → it scrolls to whatever frame contains 3 seconds.

> Both work: a plain number is a frame index, anything with a colon or a decimal point is a time.
> The target lands about a third of the way down the view rather than at the very top, so you can
> see what leads into it.

Try something past the end — `9999`. You should get a specific message telling you how many frames
there are, not a silent failure.

---

## 5.5 — Export and re-import ⭐

Top right of the page: **Sparse JSON** and **Dense JSON**.

1. Click **Dense JSON**. A file downloads, named something like
   `do-re-mi-at-60-bpm_clean_semicorchea_dense.json`.
2. **Open it in a text editor.** This is the readable form — look for `columnHeaders` (all 88 keys
   with both names) and `rowTimestamps`. You should be able to work out what the piece is without
   the app.
3. Click **Sparse JSON** too. Much smaller — it lists only the cells that sound.

Now bring one back:

4. Go to **Input → Matrix JSON** and choose the file you just downloaded.
5. **What you should see:** a green message with the tempo, resolution, step and frame count.
6. Click **Matrix** → the grid is exactly what you exported.

> **What a round trip proves.** These files are self-contained: everything needed to reopen the
> piece travels with it. You can hand one to someone else, or keep one from six months ago, and it
> will open. That is what makes the matrix a *format* rather than an internal detail.

**Try breaking one on purpose.** Open the dense file, find any `0` in the first row of
`denseMatrix`, change it to `-1`, save, and import it. That says "this note is being held" with no
note before it to hold — impossible. You should see it import anyway, with a note saying **1 cell
was corrected**: a held note with nothing before it becomes a struck note.

---

## What "working" looks like

- Five filled circles stepping down-and-right for your scale, with readable key and frame labels.
- Headers stay frozen while scrolling; scrolling down moves forward in time.
- All four pills render, and `two-hands` splits into blue and green at middle C.
- **Changing the resolution halves or doubles the rows instantly.**
- Frame search works for both a number and a time, and refuses out-of-range input politely.
- Dense and sparse both download, and both re-import to an identical grid.
- A deliberately broken file imports with a correction note rather than an error.

## If it goes wrong

| Symptom | Likely cause | What to do |
|---|---|---|
| "No piece loaded" | Nothing selected | Go to Input, pick an audio, transcribe it |
| "…has not been transcribed yet" | Audio loaded but never run | Press **Run transcription** on the Input tab |
| The grid is empty | The `silent` engine was used | `uv sync --extra transcription`, transcribe again |
| Circles in the wrong columns | A key-mapping bug — **tell me**, this would be serious | — |
| Resolution change is slow | It should be milliseconds | Check the backend terminal for model activity |
| Scrolling stutters | Virtualization not doing its job | Tell me the piece length |
| Import rejected | The message names the missing field | Check you exported from this app |

Next: [6 — Artifacts and versioning](epic-05-artifacts.md) · back to the [index](README.md)
