# 04-7 Phase 4: Hard's figure check, Stop

Plan [`04-7-plan.md`](04-7-plan.md) sections 4.3, 4.4 and 5; checklist [`04-7-checklist.md`](04-7-checklist.md).
Branch `feat/04-7-open-points`. 2026-11-03.

# 1. The checks before the edit of `src/`

`ps aux`: no pytest or browser check; the backend's last lines are its own reloads (12:44 UTC, after the Phase 3
edits); no log `ai-runs/*.json` in `running`.

# 2. Hard refuses figures shorter than a fusa (the user's answer, plan section 2)

- `sheet/llm/levels.py` `LIMITS["hard"]`: `shortest` 64 -> **32**, with a comment (the user, 2026-11-03).
- The check (`check_level`, "the time of new notes, and their figures"): a new note of a hand that is not steady
  (hard) with a figure shorter than its level's shortest is **refused**, unless:
  - the answer wrote it as a decoration note (`n.grace`, an F1 `acc` or `unacc` token), or
  - the app draws it as one: the answer is drawn once by the app's rules (`levels.drawn`, the same
    `propose_frames` as the sheet), and a note that comes out `grace` there (one or two fusas or shorter just before
    a longer note, `find_graces`) is left out. The drawing runs only when a note is too short, so a batch without
    one costs nothing more.
- The message of Hard is its own: "N notes are shorter than the level allows (at hard the shortest figure is a fusa;
  only one or two quick notes just before a longer note may be shorter: the app draws them as decoration notes):
  ...". The message of easy and medium (a semicorchea, the steady rhythm) is unchanged.
- The check sees the figures **as the answer wrote them** (`f1.read` of the reply), so the plan's question of section
  4.3 ("which figures the check sees") has this answer: the AI's figures, and a semifusa there may be a decoration note
  the app draws. That is why the drawing above is needed.

## 2.1 The prompt (level prompts version 8)

`prompt/levels/hard.md`, the right hand's checker line: "and no figure shorter than a fusa for a new note, in either
hand (one or two quicker notes just before a longer note are drawn by the app as decoration notes, and they are
allowed)". No text said that Hard may write any figure; the line was added because the easy and medium prompts state
their figure limit and Hard's did not, so the AI would learn it only from a refusal. `prompt/levels/VERSION` 7 -> 8;
`test_the_system_prompt_has_the_level_and_only_the_patterns_of_the_run` checks 8. No real run (credits).

## 2.2 Tests (`tests/test_sheet_levels.py`, stand-ins for the AI, no credits)

- `test_hard_refuses_a_semifusa_that_is_not_a_decoration_note`: three semifusas before a negra (a run, not
  decoration notes) are refused with Hard's message.
- `test_hard_accepts_fusas_and_a_decoration_note`: three fusas are accepted; one semifusa just before a negra (the
  app draws it as a decoration note) is accepted.
- With the old limit put back (`shortest` 64), the refusal test fails (checked by hand in the container).

# 3. A Stop of a level run (plan section 4.4)

No change of the code. A comment in `part_sheet/job.py` `_level_work` (at `asked`, where the Stop is seen): a Stop
keeps the batches already accepted and saved, on the level copy (the song does not change); **Revert** removes the
whole run; the user's answer of 2026-11-03. The docs (`context/ai/level-run.md` line 32 already says it;
`run-history.md`) are Phase 5's.

# 4. Checks

- `tests/test_sheet_levels.py` and `tests/test_sheet_levels_app.py`: 48 passed.
- The whole backend suite on the CPU: **1367 passed, 1 skipped, 0 failed** (1365 of Phase 3 + 2 new).

# 5. For Phase 5 (done in the same session)

- `context/ai/level-run.md`: Hard's fusa and the decoration-note exception; a row "Shortest figure of a new note" in
  the table of the limits; Stop and Revert. `run-history.md`: a `stopped` run keeps its batches, Revert takes the run
  back. `documentation/services/backend/ai-levels.md`: the shortest figure in the list of the checks.
