# 04-7: The open points of implementation 04: checklist

The plan is [`04-7-plan.md`](04-7-plan.md), the brief [`04-7-prompt.md`](04-7-prompt.md). One branch,
`feat/04-7-open-points`. Status letters: `[x]` complete, `[p]` in progress, `[b]` blocked, `[c]` cancelled,
`[ ]` not started.

## Decisions

- [x] The first discussion (user, 2026-11-03): plan section 2. A passage is 5 columns or more, the right hand
  too; on sheets written by the AI only the short stretches go; 8va in the bass clef allowed (the 03 rule ends);
  Hard refuses figures shorter than a fusa; Stop keeps the accepted batches; the six TEMP projects deleted; the
  user runs the image rebuild.
- [x] The sixth TEMP copy (Phase 1, plan section 8): `39d92dbe` is the only version of the song "20 de enero" in
  My library (folder Karaoke Viernes). The user (2026-11-03): delete the whole song.
- [x] The drawn passages of the clef rule (Phase 3): the user's ok (2026-11-03, "all good"): `CLEF_MIN` 5 and the
  step stay as they are.

# [x] Phase 1: Housekeeping (no edit of `src/`)

- [x] 1.1 `ps aux`, `docker logs aimpromptu-backend-1`, no log `ai-runs/*.json` in `running`.
- [x] 1.2 The six TEMP projects of plan section 3.4 deleted the app's way (`release_levels`, `delete_project`),
  `39d92dbe` first; the original song and the level copies of 20 de enero still there. The five of the vault
  deleted; `39d92dbe` deleted with its song (`flow.delete_song`, the user's answer).
- [x] 1.3 The two Transkun tests build the engine with `device="cpu"`; the whole backend suite on CPU, 0 failed
  (1350 passed, 1 skipped).
- [x] 1.4 `04-context.md` 8.5: the line on the octaves of the user's words closed (decided 2026-10-31, in the prompt).
- [x] 1.5 Report: [`04-7-implementation-phase-1.md`](04-7-implementation-phase-1.md).

# [x] Phase 2: The clef rule

- [x] 2.1 `STATES`: the left hand's bass clef under 8va, the right hand's treble clef under 8vb (and its limit).
- [x] 2.2 `short_clefs` (`CLEF_MIN = 5`), at the end of `clefs_and_ottavas` and in `build.reapply`.
- [x] 2.3 The user's clefs win: the mark of a clef set by hand (`Sheet.user_clefs`, the `clefset` line); the three
  parts with clefs set before it keep them by the rule itself, no one-time step (plan section 8).
- [x] 2.4 "Never 8va in the bass clef" ended: `frames.check`, the AI's check, `reading.set_ottava`,
  `reading.set_clef`, the range toolbox's 8va chips; the 8va line over a bass staff drawn right.
- [x] 2.5 The whole-run prompt: the user's rule, `prompt/frames/VERSION` 8, `PROMPT_VERSION = "8"`.
- [x] 2.6 Tests (a high note alone, a passage of 5 columns, a wide chord, the right hand, a stored AI sheet, a clef
  set by hand); the backend suite on CPU (1362 passed, 1 skipped); `npx tsc -b`; `check:frames-tools`,
  `check:frames-page` (all passed).
- [x] 2.7 Report: [`04-7-implementation-phase-2.md`](04-7-implementation-phase-2.md).

# [x] Phase 3: The measure and the gallery

- [x] 3.1 `scripts/clef_study.py --study`: the old counts equal plan section 3.3; per sheet the clef changes and the
  8va and 8vb notes, old and new; nothing but clefs and octave lines changed; the seconds per sheet. Three faults of
  the Phase 2 rule found and fixed, with tests (plan section 8); the backend suite on CPU 1365 passed, 1 skipped.
- [x] 3.2 The gallery `gallery/04-7/` (every kind of plan section 4.2), each drawing checked zoomed in against the
  data, served at `http://192.168.0.112:8099/04-7/`.
- [x] 3.3 The user looks at the drawn passages (Decisions above): ok, no change.
- [x] 3.4 Report: [`04-7-implementation-phase-3.md`](04-7-implementation-phase-3.md).

# [x] Phase 4: Hard's figure check, Stop

- [x] 4.1 `LIMITS["hard"]` `shortest` 32; a decoration note does not fail a batch; the level prompt if it says
  otherwise (`prompt/levels/VERSION` 8).
- [x] 4.2 Tests with stand-ins: a semifusa at Hard refused, a fusa and a decoration note accepted.
- [x] 4.3 Stop keeps the accepted batches: a comment in `job._level_work`.
- [x] 4.4 The backend suite on CPU (1367 passed, 1 skipped). Report:
  [`04-7-implementation-phase-4.md`](04-7-implementation-phase-4.md).

# [x] Phase 5: The docs and the closing

- [x] 5.1 The docs of plan section 4.7 (`sheet/README.md`, `stretch.md`, `annotations-stretches.md`,
  `level-run.md`, `run-history.md`, `ai-levels.md`).
- [x] 5.2 `04-context.md` 8.5 and 9.3 closed, section 10; `03-context.md` section 2's row; the 04-5 checklist's clef
  line.
- [x] 5.3 `check-links.py`, `check-names.py` on each doc changed.
- [x] 5.4 The closing report [`04-7-implementation-phase-5.md`](04-7-implementation-phase-5.md), with the HUMAN INTERVENTION of the image rebuild.
- [x] 5.5 After the user's rebuild (2026-11-03; openai 3.41.0; the suite in the new container 1367 passed): `import openai` in a fresh container; 9.3 closed; the state lines of
  `README.md`, `../README.md`, `../../00-index.md`: 04 closed.
