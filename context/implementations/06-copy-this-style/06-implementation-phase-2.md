# 06, Phase 2: the run in the backend

Plan: [`06-plan.md`](06-plan.md) sections 4.2 (the routes), 4.3 (the run), 4.4 (the marks). Checklist:
[`06-checklist.md`](06-checklist.md), Phase 2. Branch `feat/06-copy-this-style`. No AI request: stand-ins answer for the
AI in every test. The phase before: [`06-implementation-phase-1.md`](06-implementation-phase-1.md).

# 1. Summary

| Part | Where |
|---|---|
| The requests, their checks, the marks copied, the run in memory | `sheet/llm/style.py` (new) |
| The prompt files, `VERSION` 1 | `sheet/llm/prompt/style/` (`instructions.md`, `feedback.md`, `answer.md`, `VERSION`) |
| The match of a place the user ticked | `sheet/style/match.py`: `of_places` |
| The job: the dialog's list, the start, the work, Go on, Write this batch again | `part_sheet/job.py`: `style_passages`, `start_style`, `_style_work`, `_style_drawn`, `_again_style`, `style_cost`, `_style_inputs`; `continue_level` and `again_batch` send a `style` log to them |
| The store, one step of undo | `part_sheet/edits.py`: `apply_style` (through `_store_written`, as a level run) |
| The record and the log | `part_sheet/store.py`: `Record.styles`; `part_sheet/runs.py`: `create(kind=)`, `_short` (kind, reference, passages), `_saved_batches` (reads `styles` too) |
| The routes | `api/sheet.py`: `GET` and `POST /sheet/{uuid}/llm/style` |
| Tests | `tests/test_sheet_style_run.py` (15 tests) |

The backend suite on CPU: 1392 passed, 1 skipped. `flake8` on the changed files: clean.

# 2. The run

## 2.1 The routes

- `GET /sheet/{uuid}/llm/style?start=&end=&hand=&model=`: `job.style_passages`. Answers `reference`, `hand`,
  `model`, `passages` (`start`, `end`, `score`, `shift`, in song order), `threshold` (0.6), `max` (12), `tooLong`
  (the reference is longer than `BATCH_MAX_S`, 90 s), `tooShort` (fewer than `REF_COLUMNS` columns of the hand),
  `requests`, `usd`, `minutes`. The grid and the chords are cached per part (`_style_cache`, 8 parts, keyed by the
  hash of the drawn text and the notes revision).
- `POST /sheet/{uuid}/llm/style` (`StyleRequest`: `start`, `end`, `hand`, `words` up to 1,000 characters,
  `passages` `[[a, b], ...]`, `model`): `job.start_style` with `first=True`. 409: the AI not set up, or a run works
  on the part; 403: the sheet cannot be changed here; 400: no passage ticked, the reference too long or too short, a
  passage that overlaps the reference or another one, a passage too long, more than 12, or the notes changed since the
  dialog asked (below); 422: a passage that is not two numbers.
- Go on, Write this batch again, Stop, Revert, the history: the routes of the level runs, unchanged
  (`/llm/runs/{id}/continue`, `/llm/runs/{id}/batches/{k}/again`, `/llm/stop`, `/llm/revert`, `/llm/runs`).

## 2.2 The start (`job.start_style`)

The run matches again the ticked passages: `match.ranked(..., floor=0.0)` on the same sheet, notes and cached grid as
the dialog's list, then `match.of_places` takes, for each ticked place, the match that overlaps it most, cut to the
place (its frames, its column map inside them). A place with no match means the notes changed since the list was made:
400 "open it again". The log (`ai-runs/<id>.json`, `kind: "style"`) holds the request (`hand`, `start`, `end` of the
reference, `words`, `model`, `prompt`, `windows`) and `passages` (each `style.Passage`: `k`, frames, `score`, `shift`,
`columns`, `keep`, `why`).

## 2.3 The check (`style.check_prompt`, `style.read_check`)

The first request (`k` -1 in the log, its `plan` field, so the history keeps it as a level run's plan): the reference
as the user wrote it (the hands rewritten, the user's marks taken off, as every prompt), then each passage as the sheet
has it now, with its similarity and its shift, and the answer format `P1 keep | why`, `P2 drop | why`,
`P1 f1204-f1388 keep | why` to move edges. `read_check` refuses: a passage not named, named twice or unknown; an edge
moved more than `EDGE_NEGRAS` (2) negras (`2 * quarterMs / 40` frames, plus one); a kept passage over the reference or
another kept one. At most 3 replies; a check refused three times stops the run with `failed` and nothing written. The
log's `passages` take the answer (`keep`, `why`, the new frames), `request.windows` becomes the passages kept, and
the page's segments follow (`LiveRun.provisional`). Every passage dropped: `style: "dropped"`, the run ends `done`,
nothing written. The event `phase: "check"` tells the page how many were kept.

## 2.4 A passage (`style.batch_prompt`, `style.check_style`)

The request, in order: the user's words; the reference as written (both hands, the hand not rewritten said so); the
column map (`R: f877>f2477 ...`) and the shift in words; the passages written before in this run, the latest
`EARLIER_SHOWN` (2) of them; the decided context (4 s before, the sheet with the passages accepted so far); the target;
the fixed hand apart; the look-ahead (4 s after). The system prompt is the whole-run instructions (prompt 8) followed by
`prompt/style/instructions.md`, which overrides them where the run differs: the AI sets the figures (printed as set by
hand), it writes decoration notes by their figure, it declares the notes it changes.

`check_style` refuses:

- not F1, a parse error, a note with no hand, a note of the fixed hand, a note outside the passage;
- a note of the target missing without `# leave out f... pitch`, a note not in the target without `# add f... pitch`;
- more changes than `change_budget`: a tenth of the target (4 at least, as `frames.simplicity`), plus what the
  reference's way asks for through the column map: the notes a target column has more than its reference column, the
  notes of a target column with no reference column, the notes of a reference column with no target column;
- a note added whose pitch class the passage (both hands) does not play within a negra of it;
- a note of the right hand's top line (when the right hand is rewritten) that is not in the answer at its frame, with
  its pitch or an octave away, unless it is declared left out at a column with no reference column;
- the hard rules of every answer (`frames._structure`: beam groups, ledger lines, 15ma in the bass clef).

At most 3 replies; a passage refused three times keeps its notes and the run goes on with the next one; an error of
the AI itself (no credits) stops the run, and the passages accepted are stored.

## 2.5 The store (`job._style_drawn`, `style.copy_marks`, `edits.apply_style`)

**A change from the plan.** Section 4.3.5 said "as `apply_level`". The level path draws each answer again by the
app's rules (`levels.drawn`) and keeps the sheet's own clefs: the reference's clefs, 8va lines and beam groups, which
the AI copies, would be lost. So each accepted answer is spliced as a stretch is (`frames.splice`: its hands, beam
groups, clefs, 8va and figures; the other hand kept when one hand is rewritten), and the store lays the rules on it
(`build.reapply` in `_store_written`), as a stretch. What stays from `apply_level`: one range for the store (the first
passage's start to the last one's end; the sheet between them is unchanged, so nothing there is counted as changed),
the AI's figures printed as set by hand (`wrote`), the notes left out marked removed and the notes added put into
`notes.pmn` (`change_notes`), each note in the hand the sheet draws it in.

Then `copy_marks` (plan section 4.4) on the spliced sheet, per passage: the passage's own marks (spelling, finger,
switch) put back on the same notes (`frames.splice` keeps the finger, the fixed figure and the switch, not the
spelling), then from the reference through the column map (a column found 0 to 2 frames away too): a spelling to a note
of the same pitch class after the shift, named by moving the reference's letter with the interval (`moved_name`: a
tone higher, Bb -> C; no double signs, else the app's spelling); a finger and the switch to the same note (the same
pitch after the shift); a clef set by hand to the stretch of the passage between the first and the last column mapped
from it, unless the passage has one there. A mark is never put over the passage's own. The counts go into the log of
each batch (`copied`, `copiedText`: "1 spelling, 2 fingers and 1 clef copied") and into the record.

The step is labelled `Copy this style with AI, the right hand` (or `both hands`, `the left hand`), with `, passage
1` at the wait and `, the other passages` after Go on; `Passage N written again with AI` for an answer. The record's
`styles` entry: `hand`, `reference`, `words`, `prompt`, `run`, `passages` (`[a, b, status, why]`: `ok`, `failed`,
`dropped`, `waiting`), `copied`, `usd`, `requests`, `written`.

## 2.6 The first passage first, Go on, Write this batch again, Stop, Revert

- The route starts with `first=True`: the check and the first kept passage are written (`write_style(limit=1)`),
  stored, and the run waits (`waiting` in the summary and the log). When the first passage is refused three times,
  the run ends `failed` and does not wait, as a level run whose batch 1 fails.
- `continue_level` with a `style` log writes the kept passages not written yet, with the run's check (not asked again)
  and the passages written before read from the sheet (`earlier_before`, the latest two in the prompt).
- `again_batch` with a `style` log: `_again_style`, the passage's conversation with the user's answer
  (`prompt/style/answer.md`), checked as in the run, stored as one step.
- Stop: as a level run (the rule of 04-7): the request already sent ends first and its passage is kept; the next one is
  never asked; the passages accepted are stored; the log ends `stopped`. Revert: the snapshot taken before the first
  passage (`before` in every summary of the run, Go on included).
- A run left `running` after a crash: `runs.close_unfinished` reads the record's `styles` to know which passages reached
  the sheet.

## 2.7 The summary of the job's `done` message

`style` (`ok`, `dropped`, `failed`, `stale`, `gone`), `hand`, `batches` (passages written in the run so far), `total`
(passages kept), `dropped`, `usd`, `run`, `waiting`, `before`, `stopped`, `note`, `credits`; `again` for a passage
written again. The events: `phase` `style`, `check` (`status`, `kept`, `total`), `batch` (`done`, `total`, `status`),
`saved`. Phase 3 reads them.

## 2.8 The costs

`USD_STYLE_CHECK` 0.015, `USD_STYLE_BATCH` 0.025, `SECONDS_STYLE_CHECK` 10, `SECONDS_STYLE_BATCH` 45 (the level run's
numbers, not measured), times `llm_models.ratio` of the model. Phase 4 measures them.

## 2.9 The size of the prompts

Measured on the real songs (read only, no request): a 30-second reference of 7 Years, the right hand, 3 passages: the
check about 2,600 tokens, a batch about 3,700 tokens (with two earlier passages, the context and the look-ahead); both
hands about 1,700 and 2,200; My Way, 25 s: about 1,200 and 1,500. The system prompt is 31,600 characters (about 8,000
tokens), the same for every request of a run (cached by the provider). A batch fits one request with room to spare.

# 3. Tests (`tests/test_sheet_style_run.py`)

Pure: the check's reader (keep, drop, an edge moved within two negras and beyond, a passage missing, twice, unknown, a
passage over the reference); `check_style` (an accepted answer with declared changes, a missing note, a note outside,
the melody lost, the fixed hand, not F1); `change_budget` (the base limit, the reference's own changes on top, a note
added outside the harmony); `copy_marks` (a spelling a tone higher, fingers on the same notes only, the passage's own
finger kept, a clef set by hand, the counts and their text, `moved_name`).

The run, on the 40-second song of `test_part_sheet` (it repeats every 9 s; the reference is `f0-f225`): the dialog's
list (its passages, its cost, too short, too long); a run of three passages that checks, writes the first, waits, goes
on, with the AI's figures stored as set by hand, the notes left out marked removed, the log and the record, then Revert
and undo; a passage dropped by the check with one hand rewritten (the left hand unchanged); every passage dropped
(nothing written); a passage refused three times (its notes stay); a finger of the reference copied to the same note of
the passage; Stop (the passage in flight kept, the next never asked) and stale notes (nothing stored); a passage
written again with the user's answer; the routes (400, 403, 409); a run left running closed at the start; the size of
a batch prompt of a 30-second reference.

Two findings while writing them: the stand-in first left out the last note of a passage, which was a melody note, and
the check refused it three times, as it should; and a Stop pressed during a request lets that request end, so its
passage is kept (the level runs do the same).

# 4. Needed later

- Phase 3: the page reads `style` in the summary (not `level`), the event `check`, the log's `passages` (`keep`, `why`)
  and each batch's `copiedText`; the history's `_short` has `kind`, `reference`, `passages`.
- Phase 3: the words of the list ("very similar", "similar") from `score` (the threshold is 0.6; the study's bands:
  0.84 and more for exact repeats, 0.6 to 0.8 for variants and covers).
- Phase 4: the costs measured and written back (section 2.8).
