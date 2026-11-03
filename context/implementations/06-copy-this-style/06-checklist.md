# 06: Copy this style: checklist

The plan is [`06-plan.md`](06-plan.md), the brief [`04-4-prompt.md`](../04-app-enhancements/04-4-prompt.md). One
branch, `feat/06-copy-this-style`. Status letters: `[x]` complete, `[p]` in progress, `[b]` blocked, `[c]` cancelled,
`[ ]` not started.

## Decisions

- [x] The first discussion (user, 2026-11-03): plan section 2. The code finds the similar passages and the AI checks
  them as the first request of the run; a list in the dialog and on the sheet, with ticks; everything is copied,
  fingers only on the same note; the first passage first, one step of undo and Revert; 1.1 and 1.2 are part of 06, as
  the last phases; two songs (7 Years and a piano cover), the user edits the reference.
- [x] The gallery of the matcher (Phase 1): the threshold, the weights, the length range, `shift` searched or not.
  The user looked at the gallery (2026-11-03, "okey! revised! continue", no objection): the recommended options,
  `THRESHOLD` 0.6 and the shifts searched; the weights and the lengths as they are.
- [ ] The copies of the real test (Phase 4): the prompt and the check as they are, or changed.
- [ ] The temporary copies of Phase 4 deleted (Phase 7, at the user's word).

# [x] Phase 1: The matcher, the study and the gallery

- [x] 1.1 `ps aux`, `docker logs aimpromptu-backend-1`, no log `ai-runs/*.json` in `running`; the branch
  `feat/06-copy-this-style` from `master`.
- [x] 1.2 `sheet/style/match.py`: `similar` (the rhythm on the grid, the shape of the pitches, the harmony, `shift`),
  the reference as played (the notes the user took off included), the passages not overlapping, `STYLE_MAX`.
- [x] 1.3 Tests: an exact repeat found, a repeat with a note changed found, a repeat a tone higher found with its
  `shift`, another passage not found, a cover a little faster found; under a second for a song of 4 minutes.
- [x] 1.4 `scripts/style_study.py` (reads only) on 7 Years, My Way and two or three other songs; the numbers.
- [x] 1.5 The gallery `gallery/phase-1/` (the passages kept and the best ones under the threshold), each drawing
  checked zoomed in, served at `http://192.168.0.112:8099/06/`.
- [x] 1.6 The backend suite on CPU. Report `06-implementation-phase-1.md`; the user looks at the gallery (Decisions).

# [x] Phase 2: The run in the backend

- [x] 2.1 The routes `GET` and `POST /sheet/{uuid}/llm/style` (409, 403, 400).
- [x] 2.2 `sheet/llm/style.py`: the check request and its reader (keep, drop, edges of two negras at most).
- [x] 2.3 The batch prompt (the words, the reference as written, the column map and `shift`, the passages written
  before, the context, the look-ahead, the target, the fixed hand); the prompt files `prompt/style/`, `VERSION` 1.
- [x] 2.4 `check_style`: format, hand, frames, declared changes and their limits, the melody, the hard rules.
- [x] 2.5 The marks the code copies (plan section 4.4): spelling, fingers on the same note, the switch, `clefset`.
- [x] 2.6 `job.start_style`: the log (`kind: "style"`), the first passage first, Go on, Write this batch again, Stop,
  Revert, `runs.close_unfinished`; the store as `apply_level`, one step, the record's `styles`.
- [x] 2.7 The costs (`USD_STYLE_CHECK`, `USD_STYLE_BATCH`, the seconds), in the `GET` route.
- [x] 2.8 Tests with stand-ins (no credits): a run of two passages (waits after the first, goes on), a passage the
  check drops, a refused answer three times (the passage keeps its notes), one hand (the other unchanged), the marks
  copied and not copied, stale notes, Stop, Revert, undo. The backend suite on CPU. Report.

# [ ] Phase 3: The frontend

- [ ] 3.1 The tab **Copy this style** in `EnhanceDialog.tsx`: Which hand, the list with ticks, Select all and Deselect
  all, the words, the Model, the status line, the button; no passage found.
- [ ] 3.2 The reference and the passages on the sheet (`BatchPreview` with the reference).
- [ ] 3.3 The run's panel, the history and the run's detail for the kind `style` (the check: kept, dropped, why).
- [ ] 3.4 `npm run check:copy-style` with a stand-in; `check:enhance-dialog`, `check:ai-run-panel`,
  `check:ai-history`; `npx tsc -b`; the pass of 13 checks of the minimal UI. Report.

# [ ] Phase 4: The real test

- [ ] 4.1 Two temporary copies (7 Years, a piano cover); the user edits the reference on each (HUMAN INTERVENTION).
- [ ] 4.2 The matcher on the user's references (with and without the notes the user added).
- [ ] 4.3 The cost given, the user's yes; Copy this style run on both copies.
- [ ] 4.4 The gallery before and after per passage, each drawing checked zoomed in, served for the Mac; the user
  looks (Decisions).
- [ ] 4.5 The costs measured and written back into `job.py`; any prompt change with a new `VERSION`. Report.

# [ ] Phase 5: Stop a transcription

- [ ] 5.1 `jobs.stop`, the stop flag, a waiting job out of the GPU queue, a running one stopped at its next report,
  nothing kept; `POST /matrix/jobs/{job_id}/stop`; the job's state `stopped`.
- [ ] 5.2 How long a stop takes with MuScriptor (measured on a temporary copy, when the GPU is free).
- [ ] 5.3 The button **Stop the transcription** on the Notes page and the line after it.
- [ ] 5.4 Tests (`test_jobs.py`, the route with a stand-in engine), a browser check with a stand-in; the backend
  suite on CPU; `npx tsc -b`. Report.

# [ ] Phase 6: The paste

- [ ] 6.1 The page that logs the key and paste events; the user's reproduction on the Mac (HUMAN INTERVENTION).
- [ ] 6.2 The cause and the fix (or: it works now, no code).
- [ ] 6.3 The same steps on the Mac pass at the first ⌘V. Report.

# [ ] Phase 7: The docs and the closing

- [ ] 7.1 The docs of plan section 4.9 (`context/ai/copy-style.md` and the others).
- [ ] 7.2 `06-context.md`.
- [ ] 7.3 `check-links.py`, `check-names.py` on each doc changed.
- [ ] 7.4 The temporary copies deleted (at the user's word); the state lines of `README.md`, `../README.md`,
  `../../00-index.md`. The closing report.
