# The whole run: Enhance it again with AI, Write it all again

The whole run is the AI writing the hands and the reading of the whole song again, from its notes. It is the first
kind of run the app had, and the one behind the button **Enhance with AI** on the Sheet step. It is one job in the
background: the page shows the sheet as it changes, and the user may stop it or take it back.

Code: `part_sheet/job.py` (`start`, `stop`, `commit`), `sheet/llm/frames.py` (`write_frames`). Details of the code:
[documentation/services/backend/ai-runs.md](../../documentation/services/backend/ai-runs.md).

## What the user does

1. On the Sheet step, the button is **Enhance with AI**. Once the part was enhanced, it reads **Enhance it again with
   AI**. It opens the dialog **Enhance with AI**.
2. The dialog has two tabs. With no notes selected, it opens on **The whole song**, where the whole run is the button
   **Write it all again**. (With notes or a stretch selected, the dialog opens on **A stretch**, which is told in
   `context/ai/stretch-and-simplify.md`, a page Phase 10 writes.)
3. The dialog asks for two things before the run:
   - **Model**: the AI model of the run. The choices are GPT-6.1 Terra (the default), GPT-6.1 Sol and Sonnet 5.5. The
     dialog is the one place that names the model.
   - **Batches**: how many parts the song is written in. The batches are of about the same time. Each one is drawn on
     the sheet while the dialog is open, so the user sees where each part starts and ends.
4. The dialog shows the cost and the time of the run, about, before it starts. They change with the batches and the
   model.
5. **Write it all again** starts the run. The dialog closes. A panel opens at the right of the sheet (where the dialog
   was) and the sheet is laid out beside it, so the batches show whole.

On a version of **My library**, the run is written in the copy that **Edit** opens. The original does not change.

## What the page shows while the AI writes

- **The panel of the run** lists the batches, each with its colour and its number, and its state:
  - **Waiting**: not yet started;
  - **Being written**: the AI is answering it now;
  - **Written**: the check accepted the answer;
  - **Kept as it was**: the check refused every reply, so the part keeps the algorithm's notes of that batch.
- **The sheet**: the notes of the batch being written sit under a pale veil that breathes slowly. A part that comes back
  appears column by column, from left to right.
- **The AI mark** before the song's name in the lists turns green once the AI has enhanced the part.

## Stop and Revert

- **Stop** (in the panel) asks for no more requests. The request the AI is answering ends first. What the AI wrote
  stays. The panel then says **Stopping after this batch**, and **Stopped** when the run has ended.
- **Revert** (in the panel, once the run has ended) puts the part back as it was before the run, whatever the run
  changed: its notes, its hands and its sheet. It is one step of the undo; undo brings the AI's work back. The panel
  then says the sheet is as it was before the run.
- **Close** hides the panel. The run's result stays in the part.

Two refusals the page shows: the sheet cannot be changed here (the user has no right to write it), or the AI is not
set up on this machine.

## How the AI writes the whole song

The song is cut into **windows** of 12 to 16 seconds, each ending at a pause. One window is one batch of the run,
unless the user chose batches.

1. **The reference figure.** The first request gives the AI the gaps between the notes, in words, and asks for the
   figure of a quarter note in milliseconds. A reply that is not a usable figure keeps the algorithm's figure.
2. **The algorithm.** The app makes its own sheet from the notes and the figure. Its parts are the fallback of each
   window.
3. **The windows.** Each window is one conversation with the AI. It gets the notes of the window, the next four
   seconds (to look ahead), the decisions of the last four seconds (the context), and the places the app found to
   check. The AI answers with the hands, the beam groups, the clefs and the 8va lines, the ornaments and the
   armadura of the passage.
4. **The check.** The app checks each reply: the notes, the beam groups (at least 30 % of the eighths and shorter notes
   carry a beam, and no beam group overlaps itself), the clefs and the octaves. A reply with a problem gets the list of
   problems, and the AI answers the window again. The AI has three replies at most per window.
5. **The fallback.** A window whose three replies all fail keeps the algorithm's notes. A window the AI wrote is
   **Written**. The part is then **by the AI** (every window written), **mixed** (some windows kept the algorithm) or
   **the algorithm** (none written).

The app then computes the figures of the notes, the grace notes and the spelling. It never asks the AI for them.

The AI decides the hands, the beam groups, the clefs and the 8va lines, the ornaments, the armadura of a passage and
the reference figure. The marks the user put on the sheet stay: the AI's marks are its new ones.

## Limits

- No credits, no network, or a refused request: the windows that could not be written keep the algorithm. A run that
  wrote no window at all keeps the hands as they were and the sheet of the algorithm, and the page does not start
  again by itself.
- A run that finds the notes changed while it works keeps its reading. The page lays it on the current notes when the
  sheet is drawn again.
- A part deleted while the AI works stops the requests at the next one: no cost is spent on a part that is gone.
- Each run writes one step of undo (the notes the AI left out or added are in the same step).

## Where to look deeper

- [documentation/services/backend/ai-runs.md](../../documentation/services/backend/ai-runs.md): the jobs, the windows,
  the check, the prompt and its version, the routes
- [README.md](README.md): the AI in the app, the kinds of run, the model and the cost
- `context/frontend/sheet-page.md` (Phase 4 writes it): the Sheet step's page and its header
