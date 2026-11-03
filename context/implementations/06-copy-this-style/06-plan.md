# 06: Copy this style: plan

The brief, with the user's words, is [`04-4-prompt.md`](../04-app-enhancements/04-4-prompt.md) (written during 04-3,
left for a larger plan by the user on 2026-11-03). The status of every task is in [`06-checklist.md`](06-checklist.md).
Each phase writes `06-implementation-phase-N.md`. The guidelines:
[`guidelines-implementation-plan.md`](../../guidelines/guidelines-implementation-plan.md) and
[`guidelines-communication-with-user.md`](../../guidelines/guidelines-communication-with-user.md). Read
[`03-context.md`](../03-apply-poc-research/03-context.md) and
[`04-context.md`](../04-app-enhancements/04-context.md) (sections 4, 8, 9 and 10) first, then
[`context/ai/README.md`](../../ai/README.md), [`stretch.md`](../../ai/stretch.md),
[`level-run.md`](../../ai/level-run.md) and [`run-history.md`](../../ai/run-history.md).

# 1. Context

The user selects a stretch of the sheet, edits it by hand (figures, spelling, octaves made thirds, beams, fingers...),
and says: "take this as the reference for the rest of the song". Every other place of the song that plays the same
kind of passage is then written again so that it looks like the reference, while it keeps what is really its own.

| Word | Meaning in this plan (the user's terms) |
|---|---|
| **the reference** | The stretch the user selected and edited by hand: its rhythm, figures, spelling (Sib for La#), chord shapes (octaves, thirds), beams, decoration notes, clefs and 8va, fingers |
| **a similar passage** | Another place of the song that plays the same kind of passage: repeated, with slight changes (another note, another ending, more or less ornament, maybe in another key). Similar, not equal |
| **Copy this style** | The new tab of **Enhance with AI**, open when a range is selected: **Both / Right / Left**, the user's words (optional), **no level** |
| **the check** | The first request of the run: the AI says which passages the code found are really the same kind of passage |
| **a batch** | One similar passage written again (one request, checked by code), as in a level run |

Three smaller requests of the brief: **1.1** a Stop button for a transcription (in this plan, Phase 5), **1.2** a paste
that does not work the first time (Phase 6), **1.3** Select all and Deselect all of the patterns, already done in
04-3 ([`04-3-plan.md`](../04-app-enhancements/04-3-plan.md) section 10).

# 2. The user's answers (the first discussion, 2026-11-03)

| Point | Answer |
|---|---|
| Who finds the similar passages | **The code finds them, then the AI checks them** |
| When the AI checks | **As the first request of the run.** The dialog lists the code's passages at once (free); the user unticks some and starts; the AI check drops the ones that are not the same kind of passage, with a reason shown in the run's panel, then the first passage is written |
| Does the user see the passages before the run | **Yes: a list in the dialog, and drawn on the sheet.** Each with its frames and how similar it is; the user unticks the ones not wanted |
| What a passage takes from the reference | **Everything**: rhythm, figures, spelling, chord shapes (octaves, thirds, notes left out or added), beams, decoration notes, clefs and 8va. **Fingers only on a note that is the same note as in the reference** |
| How the run writes and is undone | **The first passage first**, as a level run: it writes the check and the first passage and waits; the user checks it, answers the AI or goes on. The whole run is **one step of undo**, and **Revert**; each passage is a batch in **History of AI runs** |
| 1.1 and 1.2 of the brief | **Both are part of 06**, as the last phases, after Copy this style |
| The test case | **Two songs, and the user edits the reference**: 7 Years (clean repeats) and one piano cover with variations (for example My Way), each on a temporary copy; the user edits the reference in the browser, the agent runs the tests there |

Still the user's rules from earlier work (they bind here too): the AI starts only from a button (04-3); a run of two
batches or more writes its first batch and waits (04-5); the check decides what reaches the sheet, not the AI (04-5);
the page says "AI", never the model's name (04-2, 04-6); every run gives its cost and time before it starts; a new AI
run kind that changes notes uses `edits.change_notes` and one step of undo (04-context section 4).

# 3. What the code holds now (checked 2026-11-03)

## 3.1 Finding a passage like another: `like_before`

`sheet/llm/frames.py`, `like_before(sheet, staff, start, end, before)` (`LIKE_GRAM = 4`, `LIKE_SHARE = 0.3`): the
earlier passage of the same number of columns whose runs of 4 columns hold **the same keys** as the batch. It serves
the level runs ("an earlier passage like this one, as the run wrote it"). It finds exact repeats only. A read-only
measure on the 44 parts of My library (8-second passages, does an earlier one match?):

| Song | Passages | Found, right hand | Found, left hand |
|---|---|---|---|
| 7 Years (`1a16a836`, AI sheet) | 29 | 23 | 15 |
| Titanium (`f3680cb8`) | 29 | 22 | 22 |
| Shut Up and Dance (`68e277fe`) | 26 | 19 | 20 |
| My Way, piano cover (`c33860b5`) | 16 | 1 | 3 |
| Superestrella, piano cover (`a585f9eb`) | 22 | 0 | 0 |
| 99 Red Balloons (`b2db46eb`) | 24 | 2 | 8 |

A song made from a clean transcription repeats key for key; a cover played by a person almost never does (another
tempo, a note more, a chord played a little earlier). So the brief's "similar, not exactly the same" needs a new
matcher (section 4.1). `like_before` stays as it is for the level runs.

## 3.2 The runs that already exist

- **A stretch** (`frames.write_stretch`, `job.start_stretch`, `edits.apply_stretch`): one window conversation, the
  user's words first, the AI may change notes, hands, beams, clefs, 8va, ornaments and figures; with one hand the
  other is fixed (`window_prompt(fixed=)`, `check_answer(hand=)`, `splice(keep=)`). The figures the AI writes are
  stored as set by hand (`_store_written`, `wrote`).
- **A level run** (`levels.write_level`, `job.start_level`, `job._level_work`, `continue_level`, `again_batch`,
  `edits.apply_level`): a plan request, then batches, each checked by code (`check_level`), each seeing the batches
  written before it; the first batch first and **Go on with the other batches**; the log `ai-runs/<id>.json`
  (`part_sheet/runs.py`, `kind: "level"`), Stop, Revert (`edits.snapshot_before_run`, `revert_run`). Its store takes
  many stretches at once: `apply_level` with `wrote` (the notes the AI wrote) over `[start, end)`.
- **The costs** (`job.costs`, `job.batch_plan`, `GET .../llm/costs`, `GET .../llm/batches`): per-request constants
  measured with one model, scaled by `llm_models.ratio`.

## 3.3 The user's marks and the AI

| Mark | In the F1 text | Sent to the AI today | Kept by `reapply` and `splice` |
|---|---|---|---|
| A figure set by hand | `fix` | no (`_strip_marks`, `levels._bare`) | yes, on the same `(frame, midi)` |
| A spelling set by hand | `sp` | no; the note's name is in the text | yes |
| A finger | `fg<n>` | no | yes |
| The decoration-note switch | `asgrace`, `nograce` | no | yes |
| A clef set by hand | `clefset` line | no (`levels._bare` drops it) | yes (`Sheet.user_clefs`) |
| Beam groups | `b<n>` | yes (a stretch; not a level) | yes |
| Clefs, 8va, ornaments | clef lines, `8va`, `tr`... | yes (a stretch) | yes |

So the AI can write the notes, the hands, the figures, the beams, the clefs, the 8va and the ornaments of a passage;
the marks only the user writes (`sp`, `fg`, `asgrace`/`nograce`, `clefset`) must be copied by code (section 4.4).

## 3.4 The reference before the user's edits

The edits of the user change the notes of the reference (an octave made a third takes a note off: `removed: true` in
`notes.pmn`, kept, not deleted; an added note is a new event, with no flag). The similar passages still look like the
reference **as it was played**. So the matcher compares them with the reference's notes as played: the live notes and
the notes the user took off (section 4.1). The added notes cannot be told apart; Phase 1 measures whether that
matters.

## 3.5 The two small requests

- **1.1 Stop a transcription.** `POST /matrix/transcribe` (`api/matrix.py`) starts `pipeline.transcribe_audio` as a
  job of `transcription/jobs.py`, in the GPU queue (`_GpuQueue`: one at a time, the others wait, each told its place).
  The notes are written only at the end (`save_note_events`, then `clear_rhythm`, `clear_new_sheet`), after
  `history.snapshot_notes`. So a stop before that line leaves the part as it was, which is the user's answer
  ("nothing of the stopped run is kept"). No route stops a job; `jobs.Job` has no stop flag; the work reports often
  through its `reporter`. The page: `notes/useLiveTranscription.ts`, `pages/piece/NotesEditor.tsx`,
  `pages/piece/AudioTab.tsx`.
- **1.2 The first paste.** Not reproduced on Linux (headless Chromium pastes at the first Control+V). The user works on
  a Mac with ⌘V. No page reads the system clipboard (`passageClipboard.ts` reads `localStorage` and the paste event);
  every page-wide key handler steps aside in a text field. It needs a reproduction on the user's Mac first.

# 4. Design

## 4.1 The matcher (code, no AI)

A new module, `aitu_backend/sheet/style/match.py` (a package `sheet/style/` for this feature), with
`similar(sheet, notes, start, end, staffs) -> list[Match]`. A `Match` holds `start`, `end` (frames), `score` (0 to 1),
`shift` (semitones: a repeat in another key), and the parts of the score.

1. **The features of a stretch, per hand rewritten** (the right hand, the left, or both):
   - **the rhythm**: the onsets of its columns as places on the song's grid of negras and corcheas
     (`song_grid` in `sheet/levels/grid.py`), so a cover that is a little faster or slower still matches;
   - **the shape of the pitches**: the top note of each column for the right hand, the lowest for the left, as
     steps between columns (the contour), and the pitch classes of each column;
   - **the harmony**: the chords of the stretch (`chords` in `sheet/levels/harmony.py`), as roots relative to the key.
2. **The search**: every place of the song with about the reference's length in negras (from 80 % to 125 %, to be
   measured), on both sides of the reference, scored by a weighted sum of the three parts. The pitch parts take the
   best `shift` from -6 to +6 semitones (a last chorus a tone higher). The best places that do not overlap the
   reference or each other are kept, the most similar first, above a threshold, at most `STYLE_MAX` (first 12).
3. **The reference as played**: its live notes and the notes the user took off in it (section 3.4).
4. **Speed**: a song of 4 minutes is searched in well under a second (the dialog asks for it when the tab opens).
5. **The numbers** (the weights, the threshold, the length range, `STYLE_MAX`, whether `shift` is searched) are first
   guesses; Phase 1 chooses them by the study and the user's look at the gallery (section 4.7).

## 4.2 The dialog: the tab **Copy this style**

`EnhanceDialog.tsx` gets a third tab, **Copy this style**, after **A stretch**, open only when a range or notes are
selected (as **A stretch**: the frames of the selection are the reference).

- **Which hand**: **Both**, **Right**, **Left** (the same `Segmented` as A stretch). With one hand the other hand of
  every passage stays exactly as it is.
- **The similar passages**: the dialog asks the backend when the tab opens and when the hand changes (free, code);
  a list, one row per passage: a tick, its frames (`f1204-f1388`), its time (`mm:ss.cc`, the rule of
  [`timestamps.md`](../../frontend/timestamps.md)), how similar ("very similar", "similar"; the words chosen in Phase
  3), and "a tone higher" when `shift` is not 0. All ticked at first. **Select all** and **Deselect all**, as in the
  gallery of patterns. With no passage found: "No passage of the song is like this one." and the button is off.
- **On the sheet**: the reference and the passages are drawn as the batches are drawn today (`onPreview`,
  `BatchPreview`, `BATCH_COLOURS`), the reference in its own colour and named; an unticked passage is not drawn.
  The preview type gets a field for the reference.
- **The user's words** (optional, up to 1,000 characters, as A stretch): "What should the copy keep or change?"
- **No level**, no gallery of patterns, no chords field, no **Batches** control (each passage is a batch); the
  **Model** selector stays.
- **The status line**: "The reference stays as it is. N passages. About $x, about M minutes. Undo takes it back."
- **The button**: **Copy this style**.

The routes (in `api/sheet.py`):

| Route | What it does |
|---|---|
| `GET /sheet/{uuid}/llm/style?start=&end=&hand=` | The passages the code finds (section 4.1), with the cost and the minutes of a run over all of them |
| `POST /sheet/{uuid}/llm/style` | Starts the run: `start`, `end`, `hand`, `words`, `passages` (the ticked ones, `[[a, b], ...]`), `model`. 409 when a run works on the part, 403 when the sheet cannot be changed here (a version of My library), 400 when no passage is ticked |

## 4.3 The run (backend)

`job.start_style` (in `part_sheet/job.py`), built on the level run's flow (`_level_work`, its log, Stop, Revert,
**Go on with the other batches**), in a new module `sheet/llm/style.py` (`write_style`, the prompts, the check). The
log is `ai-runs/<id>.json` with `kind: "style"`.

1. **The check** (the first request; the plan of a level run): the reference as written, and each ticked passage as
   the sheet has it now, short (the F1 frames text of the hands rewritten). The AI answers one line per passage:
   `P2 f1204-f1388 keep | the second chorus, same melody` or `P3 drop | the bridge: another melody`. It may move a
   passage's edges a little (to where the passage really starts and ends: at most two negras, checked by code,
   never over the reference or another passage). The code checks the answer (every passage named once, the frames
   allowed), at most 3 replies. The passages dropped and the reasons go into the log; the run's panel and its detail
   show them. When the AI drops every passage, the run ends with nothing written and says so.
2. **The batches**: one per passage kept, in the order of the song. Each batch request holds, in this order:
   - the user's words, when there are some (of the utmost importance, as in a stretch);
   - **the reference as the user wrote it**: the F1 frames text with its figures, its note names (the spelling), its
     beams, decoration notes, clefs, 8va and ornaments, both hands (the hand not rewritten marked as such);
   - **the column map**: each column of the target next to the column of the reference it matches (from the
     matcher's alignment, section 4.1), and the `shift`;
   - the passages written before in this run, as written (each batch sees the ones before it);
   - the decided context (the sheet just before the passage) and the look-ahead (4 seconds after, not to write);
   - **the target**: the passage as the sheet has it now; the fixed hand apart when one hand is rewritten.
   The rule of the answer: write the target the way the reference is written (its rhythm and figures, its chord
   shapes, its beams, its clefs and 8va, its decoration notes); where the target plays other notes than the reference,
   keep the target's own notes and its harmony, in the reference's way of writing.
3. **The check by code** (`check_style`), each answer, at most 3 replies with the problems as feedback:
   - the format, the hand (the fixed hand is refused, as `check_answer(hand=)`), every note inside the passage;
   - the notes left out and added are **declared** (`# leave out f... pitch`, `# add f... pitch`, as prompt 6 of the
     whole run), and each is a change the reference made at the matching column (for example the reference has a
     third where the passage had an octave), or one note of the passage's own; the limit of the share is chosen in
     Phase 2 (first: as `frames.simplicity`, a tenth of the target, 4 at least, plus the reference's own changes);
   - the melody of the right hand stays: every note of its top line keeps its frame and its pitch or the same name an
     octava away, unless the reference took that note off at the matching column;
   - the hard rules of every answer (`frames._structure`, `beam_floor`): beam groups of at most 8 notes, no note four
     ledger lines or more above its staff, no 15ma in the bass clef.
   A passage the check refuses three times keeps its notes; the run goes on with the next one (as a level run).
4. **The marks the code copies** (section 4.4), on the accepted answer, before the store.
5. **The store**: as `apply_level` (`edits.change_notes` for the notes left out and added, each note in the hand the
   sheet draws it in, the AI's figures printed as set by hand through `wrote`), over the passages accepted; one step
   of undo, labelled "Copy this style with AI, the right hand" (or "both hands"); the record of `sheet.f1` gets a
   `styles` list: the reference, the hand, the words, the passages kept and dropped, the cost. The reference never
   changes.
6. **The first passage first**: the check and the first passage are written, stored and the run waits (`waiting`);
   **Go on with the other batches** writes the rest; **Write this batch again** (from the history, with the user's
   answer) works for a passage as for a level batch. **Stop** keeps the passages accepted (the rule of 04-7);
   **Revert** puts back the part as it was before the run.
7. **The prompt files**: `sheet/llm/prompt/style/` (`instructions.md`, `feedback.md`, `VERSION` 1). They take the
   rules of the whole-run prompt that still hold (the clef rule of 04-7, the hard limits, the octave as a third or a
   fifth), and say the purpose: the copy makes the song read the same way each time the passage comes back.
8. **The costs**: `USD_STYLE_CHECK`, `USD_STYLE_BATCH`, `SECONDS_STYLE_CHECK`, `SECONDS_STYLE_BATCH` in `job.py`,
   first taken from the level run's numbers (a batch prompt of the same size), then measured in Phase 4 and written
   back; scaled by `llm_models.ratio`.

## 4.4 The marks the code copies

After the matcher's column map (reference column → passage column) and the `shift`:

| Mark | Copied to a note of the passage when |
|---|---|
| Spelling (`sp`) | the note has the reference note's pitch class, moved by `shift`: it takes the reference's name, moved by `shift` (Sib a tone higher is Do) |
| Finger (`fg<n>`) | the note is **the same note as in the reference**: the same pitch after `shift`, at the matching column, in the same hand (the user's answer) |
| The decoration-note switch (`asgrace`, `nograce`) | the note is the same note as in the reference (as a finger) |
| A clef set by hand (`clefset`) | the reference holds a mark: the matching stretch of the passage gets the same mark, so the rule of the shortest clef stretch keeps it |
| A figure set by hand (`fix`) | not copied by code: the AI writes the figures, and they are stored as set by hand (`wrote`) |

A mark the passage already has from the user is never replaced. The copied marks are counted in the batch's log line
("3 spellings, 2 fingers copied").

## 4.5 The run's panel and the history

- `AiRunPanel.tsx`: the batches are the passages (with their frames); a passage dropped by the check is shown as
  dropped, with the reason. The waiting state and **Go on with the other batches** as for a level run.
- `AiHistoryPanel.tsx`, `AiRunDetail.tsx`: a run of kind `style` is "Copy this style, the right hand"; its detail
  shows the reference's frames, the check (kept, dropped, why) and each passage's conversation.
- `runs.listing` and `runs.close_unfinished` take the new kind (a run left after a crash is marked stopped, as a
  level run).

## 4.6 Stop a transcription (1.1)

- **Backend**: `jobs.Job` gets a stop flag and `jobs.stop(job_id)`; a job waiting in the GPU queue leaves it at once
  (`_GpuQueue` removes it and tells the others their new place); a running one stops at the next report of its
  `reporter` (a check that raises `Stopped`), before `save_note_events`. Nothing of the run is kept: the temporary
  clip is deleted, no history snapshot is made, the notes, the reading and the sheet stay as before the click. A new
  route `POST /matrix/jobs/{job_id}/stop` (the owner only, as the other job routes); the job ends with the state
  `stopped` and the page reads it. Phase 5 checks where MuScriptor's work can be stopped (between its chunks of
  audio; a call on the GPU is not cut in the middle) and how long a stop takes.
- **Frontend**: on the Notes page, while a transcription runs or waits, a button **Stop the transcription** at the
  top; after it, the page shows the part as it was (its earlier notes, or none) and a short line "The transcription
  was stopped. Nothing was kept."
- **Tests**: `tests/test_jobs.py` (a waiting job leaves the queue, a running one stops at its next report, the next
  job starts), a test of the route with a stand-in engine (no GPU), a browser check with a stand-in.

## 4.7 The paste (1.2)

1. **A reproduction on the user's Mac** (HUMAN INTERVENTION): a small page served by the dev server
   (`http://ubuntu:5173/...`, the Mac's browser) logs every `keydown`, `paste`, `beforeinput` and `input` event of
   the words box of **Enhance with AI** and of the ⌘K search; the user pastes once with ⌘V and sends the log (the
   browser and its version too).
2. **The cause and the fix**, from the log (for example a handler that calls `preventDefault` on ⌘V, a focus that
   moves at the first key, a dialog that opens its text box after the first paste).
3. **The check**: the same steps on the Mac pass at the first ⌘V, in every text box where the user saw it.

If the paste works on the Mac at the time of Phase 6 (it may have been fixed by a later change), the phase writes so
and closes with no code.

## 4.8 The study and the gallery of the matcher (Phase 1)

A script `aitu-backend/scripts/style_study.py`, run in the running container (it reads only):

- For each song of the study (7 Years, My Way, and two or three others of section 3.1), a few references (a verse, a
  chorus, an intro; then the user's real references once edited, Phase 4): the passages the matcher finds, their
  scores and parts, the `shift`, and the seconds it took.
- **The gallery** `gallery/phase-1/`: per reference, the reference and each passage found, drawn by the app, one above
  the other, with the score; also the best places **not** kept (just under the threshold), so the user sees where the
  line falls. Each drawing checked zoomed in against the data before the user sees it; served over HTTP for the Mac
  (`http://192.168.0.112:8099/06/`).
- The user looks: a passage the user calls the same kind of passage must be found; one the user calls another passage
  must be under the threshold, or the AI check must be able to drop it. The weights and the threshold change on the
  user's word (section 8).

## 4.9 The docs

- A new page `context/ai/copy-style.md` (what the user does, what the code finds, the check, the batches, the marks
  copied, what is stored, the messages, the limits); the table of kinds of run in `context/ai/README.md`;
  `run-history.md` (the kind `style`).
- `documentation/services/backend/ai-runs.md` (a section for the run: the functions, the constants, the prompt
  files), `endpoints.md` (the two routes of the run, the stop route of a transcription),
  `documentation/services/frontend/components.md` (the tab), `context/frontend/sheet-page.md` (the dialog),
  the page of the Notes step for the stop button (`context/frontend/projects.md`).
- `06-context.md`: what 06 changed and the decisions that bind, for later implementations (as `04-context.md`).
- The state lines of [`README.md`](README.md), [`../README.md`](../README.md) and
  [`../../00-index.md`](../../00-index.md).
- `python3 scripts/docs/check-links.py`; `scripts/docs/check-names.py` on each doc changed.

# 5. Phases

| Phase | Work | Checks | Ends with |
|---|---|---|---|
| 1 | The matcher (section 4.1), its tests, the study and the gallery (section 4.8). No AI, no change of any stored file | the backend suite on CPU; the study's numbers; each drawing checked zoomed in | **The user looks at the gallery** (a decision: threshold, weights, lengths, `shift`) |
| 2 | The run in the backend: the routes, the check, the batches, `check_style`, the marks copied, the store, the first passage first, Go on, Write this batch again, Stop, Revert, the log, the costs, the prompt files version 1; tests with stand-ins for the AI (no credits) | the backend suite on CPU | |
| 3 | The frontend: the tab, the list and its ticks, the reference and the passages on the sheet, the status line; the run's panel and the history for the kind `style`; a browser check `npm run check:copy-style` (a stand-in answers for the AI); the pass of 13 checks of [`09-minimal-ui-guidelines.md`](../01-mvp/09-minimal-ui/09-minimal-ui-guidelines.md) | `npx tsc -b`; `check:copy-style`, `check:enhance-dialog`, `check:ai-run-panel`, `check:ai-history` | |
| 4 | The real test: two temporary copies (7 Years and a piano cover), the user edits the reference on each (HUMAN INTERVENTION), the agent runs Copy this style on both (the cost asked first); a gallery before and after per passage; the costs measured and written back; prompt changes on the user's word (a new `VERSION`) | each drawing checked zoomed in against the data; the backend suite on CPU after any change | **The user looks at the copies** (a decision) |
| 5 | Stop a transcription (section 4.6), backend and frontend | `test_jobs.py`, the route test, the backend suite on CPU; `npx tsc -b`; a browser check with a stand-in | |
| 6 | The paste (section 4.7): the reproduction on the Mac (HUMAN INTERVENTION), the cause, the fix | the same steps on the Mac pass at the first ⌘V | |
| 7 | The docs (section 4.9), `06-context.md`, the closing report; the temporary copies deleted (at the user's word) | `check-links.py`, `check-names.py` | |

Phases 1 and 4 end with a decision of the user, so each is a phase of its own. Phases 5 and 6 do not depend on Copy
this style: an agent may do them at any time after Phase 1, but not while a browser check of another phase runs.

# 6. Rules

- One branch, `feat/06-copy-this-style`, from `master`. Merge into `master` only at the user's ok; no PR.
- The app runs in containers that mount this working tree: the backend reloads on every `.py` edit of `src/`, which
  stops a running AI run and a running transcription. Before the first edit of `aitu-backend/src` in a session:
  `ps aux`, `docker logs aimpromptu-backend-1`, no log `ai-runs/*.json` in `running`, and no transcription job
  running.
- Never print or copy a key from `.env`. A host script loads `.env` first (else it opens an empty `.database/`); the
  scripts of this plan run in the running container
  (`docker exec -i -w /work/aimpromptu/aitu-backend aimpromptu-backend-1 python scripts/...`).
- Tests on CPU (another project often holds the GPU): `docker exec -e CUDA_VISIBLE_DEVICES= -e
  NVIDIA_VISIBLE_DEVICES=void -w /work/aimpromptu/aitu-backend aimpromptu-backend-1 python -m pytest`. No AI request
  in the tests: stand-ins answer for the AI.
- **No real AI run without the user's yes, with the cost given first.** No browser check or script writes on a real
  library piece: temporary copies only, deleted at the end at the user's word. No edit of `src/` while a browser check
  runs (both services reload).
- The page says "AI", never the model's name (except the dialog's Model selector).
- Drawings go to the user zoomed in, checked against the data, over HTTP for the Mac (`http://192.168.0.112:<port>`,
  the gallery at `http://192.168.0.112:8099/06/`), never a file path.

# 7. Risks

- **The matcher finds the wrong passages** (a verse taken for a chorus, two halves of one passage). Three guards: the
  threshold chosen with the user in Phase 1, the user's ticks in the dialog, and the AI check of the run. A passage
  that is not the same kind and still gets through is one batch that the user can **Revert** with the run.
- **A cover's passages differ in length** (a note held longer, a bar more). The length range of the search and the
  check's edges (two negras) cover small cases; a passage with a whole bar more is written with the reference's way
  of writing where the columns match, and its own way elsewhere. Phase 4 shows such a case if the songs have one.
- **The column map is wrong** in a passage with many changes: a spelling or a finger copied to the wrong note. The
  code copies only to a note of the same pitch class (spelling) or the same note (finger, switch), never by place
  alone.
- **Cost**: 12 passages are 13 requests. The dialog shows the cost before the start, the first passage first lets the
  user stop early, and `STYLE_MAX` bounds it.
- **A long reference** makes long batches. A batch must fit one request: the reference and each passage at most
  `BATCH_MAX_S` (90 s); the dialog says "Select a shorter stretch" past it. Phase 2 checks the size of a batch prompt
  for a 30-second reference.
- **The edits of the reference added notes** that the matcher cannot tell from played ones (section 3.4). Phase 1
  measures the score with and without them on the user's references.
- **Stop a transcription mid-way on the GPU**: a model call cannot be cut; the stop waits for the end of the chunk
  being transcribed. Phase 5 measures it and says it on the page if it takes more than a few seconds.

# 8. Changes during the work

(Each phase adds its changes here, with the date and the user's words when the user decided.)

**Phase 1 (2026-11-03)**, report [`06-implementation-phase-1.md`](06-implementation-phase-1.md):

- The matcher works on the negras of the grid (bins of a semicorchea) with a subsequence alignment; its four parts are
  the rhythm, the **contour** (the steps of the line, the same in any key), the pitch classes and the harmony (section
  4.1 named the contour inside "the shape of the pitches"). First numbers: `WEIGHTS` rhythm 0.3, contour 0.25, classes
  0.2, harmony 0.25; `THRESHOLD` 0.6; `LENGTHS` 0.8 to 1.25; `SHIFTS` -5 to +6 with `SHIFT_COST` 0.03; `STEP_COST` 0.3;
  `STYLE_MAX` 12. The user looked at the gallery (2026-11-03, "okey! revised! continue", no objection to the two
  recommendations): `THRESHOLD` stays 0.6 and the shifts stay searched; the other numbers as they are.
- The notes marked removed count as played in the reference **and in every passage** (section 3.4 said the
  reference): the comparison stays fair where a run of the AI left notes out of some passages.
- `similar` takes the song's grid and chords (`grid=`, `harmony=`): the grid costs 0.3 to 0.6 s, the matcher 3 to 25
  ms. The route of Phase 2 caches them.
- A reference of fewer than 4 columns or 2 negras finds nothing (`REF_COLUMNS`, `REF_NEGRAS`); the dialog of Phase 3
  says so.
- The gallery is at `http://192.168.0.112:8099/06/phase-1/`.

**Phase 2 (2026-11-03)**, report [`06-implementation-phase-2.md`](06-implementation-phase-2.md):

- **The store splices each answer as a stretch** (`frames.splice`, then the rules when stored), not as `apply_level`
  (section 4.3.5): the level path draws an answer again by the app's rules and keeps the sheet's old clefs, so the
  reference's clefs, 8va and beam groups would be lost. One range, `wrote`, `change_notes` and one step stay as
  `apply_level` (`edits.apply_style`).
- The run matches the ticked passages again when it starts (`match.of_places`); when the notes changed since the
  dialog's list, the POST answers 400 "open it again".
- The limit of the notes changed (section 4.3.3, "chosen in Phase 2"): a tenth of the target (4 at least) plus what the
  reference's way asks for at the matching columns (`style.change_budget`); an added note takes a pitch class the
  passage plays within a negra; a melody note may be left out only at a column with no reference column.
- A batch sees the latest two passages written before (`EARLIER_SHOWN`), not all of them: the prompt stays small.
- When the first passage is refused three times the run ends `failed` and does not wait (as a level run).
- The job's summary names the run `style` (`ok`, `dropped`, `failed`, `stale`, `gone`); the check is the log's
  `plan` (`k` -1), the passages are the log's `passages`.

