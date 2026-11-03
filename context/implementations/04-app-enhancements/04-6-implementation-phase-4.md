# 04-6, Phase 4: Simplify removed

Plan: [`04-6-plan.md`](04-6-plan.md) section 4.3. Branch `feat/04-6-run-safety-and-model`. Before the first edit of
`aitu-backend/src`: `ps aux`, `docker logs aimpromptu-backend-1` (no AI request), and the 10 logs of
`/mnt/ssd2/aimpromptu/.database` (`AITU_DATABASE_DIR`; `.database/` at the repo root holds none): none `running`. No
browser check ran during an edit of `src/`.

## 1. What was removed

Backend (644 lines out):

- **`api/sheet.py`**: `POST /sheet/{uuid}/llm/simplify` and `SimplifyRequest`; the module docstring's line. The route
  now answers 404 (tested).
- **`part_sheet/job.py`**: `start_simplify` (and from `__all__`), the imports `simplify_windows` and `write_simplify`,
  `USD_BATCH`, `SECONDS_BATCH` (the comment of the estimates no longer names Simplify), the `simplify-*` keys of
  `costs`. `HANDS` and `_as_drawn` stay (the level runs and the stretch use them); so do `LiveRun.done`, `staff`,
  `outcomes` and `advanced` (the level runs and the stretch in batches use them; their comments now say so).
- **`part_sheet/edits.py`**: `apply_simplify`, `SIMPLIFY_LABELS`, the docstring's paragraph. An old Simplify step in a
  part's undo log keeps its label as text, so undo and redo of it still work.
- **`sheet/llm/frames.py`**: `SIMPLIFY_MS`, `SIMPLIFY_ONSETS`, `SIMPLIFY_CONTEXT_MS`, `SAME_PLACE`, `HAND_NAMES`,
  `Change`, `Simplified`, `simplify_windows`, `like_columns`, `simplify_prompt`, `_CHANGE`, `_NO_CHANGE`,
  `check_simplify`, `renamed`, `_changed`, `simplify_feedback`, `write_simplify`; the module docstring's paragraph.
  **Kept** (the level runs import them, `sheet/llm/levels.py`): `like_before`, `_like_columns_of`, `LIKE_GRAM`,
  `LIKE_SHARE`, `_slice`, under a new section title "An earlier passage like a batch (the level runs)".
  `check_answer(simplify=...)` stays: it is the whole run's rules of simplicity (prompt 6), not the Simplify run.
- **`part_sheet/store.py`**: the record's `simplified` field stays (old sheets hold it); its docstring says the app
  no longer runs Simplify.
- **`sheet/llm/levels.py`**: two comments that compare with Simplify say it was removed (history of the design).
- **`scripts/simplify_gallery.py`**: deleted (`simplicity_gallery.py`, which the level galleries import, stays).

Frontend:

- **`api/sheet.ts`**: `sheetApi.simplify` removed; `SongRun` is `"all"` only (the type stays: the dialog, the page,
  the navigation state and `SheetTab` use it); the `staff` comment of a segment says "a level or a stretch".
- **`navigation.ts`**: `RUNS` is `["all"]`: an old navigation state asking `simplify-*` starts nothing.
- **`FramesSheetPage.tsx`**: `SIMPLIFY_HANDS` and the call of `simplify` removed; `startSong` runs the whole run; the
  module docstring says **a level** or **Write it all again**.
- **`useFramesSheet.ts`**: `simplify`, the `simplify`, `added`, `leftOut` fields of `RunSummary`, the Simplify
  messages, `HAND_WORDS` and `notes()` removed (`hand` stays: a level's summary sends it).
- **`EnhanceDialog.tsx`**: the docstring no longer speaks of "the older Simplify run".
- **`scripts/check-enhance-dialog.mjs`**: its stand-in route no longer lists `/simplify`. Its check "no Simplify
  without a level" stays (it keeps Simplify from coming back in the dialog).

## 2. The tests

- `tests/test_sheet_simplify.py` → **`tests/test_sheet_stretch_one_hand.py`** (`git mv`). The plan said to delete
  the file, but 4 of its 12 tests test code that stays: the one-hand stretch (3 tests: `check_answer(hand=1)`,
  `start_stretch(staff=1)`, `splice(keep=2)`) and `like_before`. They stay. The 7 Simplify tests go. The route test
  becomes `test_the_costs_of_the_dialog_and_no_simplify_route`: the keys of `GET /llm/costs` without `simplify-*`,
  and `POST /llm/simplify` answers 404 or 405.
- The Simplify test "while one hand is simplified the segments name its staff" also checked that **after** a run no
  segment names a staff. `test_sheet_levels_app.py::test_a_level_of_one_hand_on_a_range_keeps_the_rest` already
  checked the staff during a run; it now checks the "after" too.

## 3. Findings

- **The fresh image has no `openai`.** `docker compose run ... backend` (the command of the memory "tests on CPU")
  uses the image of 2026-10-25, built before `openai` entered `pyproject.toml`; 2 tests that build an
  `OpenAIComplete` fail there with `ModuleNotFoundError`. The running container has `openai` 3.41.0 (installed in
  it). The suite therefore ran in the running container: `docker exec -e CUDA_VISIBLE_DEVICES= -e
  NVIDIA_VISIBLE_DEVICES=void -w /work/aimpromptu/aitu-backend aimpromptu-backend-1 python -m pytest` (the tests use
  a temporary database, `tests/conftest.py`). A rebuild of the image (`docker compose build backend`) would fix the
  fresh one; not done (it is the user's running app).
- **Two Transkun tests fail on the CPU**, in both containers: `test_transcription_transkun.py::
  test_it_satisfies_the_engine_protocol` and `test_a_missing_file_is_a_file_error_not_a_model_error`, with "Attempting
  to deserialize object on a CUDA device but torch.cuda.is_available() is False" (the checkpoint was saved on the
  GPU and is loaded without `map_location`). They skip only when Transkun is not installed; it is in the image since
  2026-10-25. Not related to this work (no file of `transcription/` changed in 04-6 but a comment of Phase 2). Phase
  2's run had 3 skipped where this one has 1: these two were very likely skipped or run on the GPU then. Not fixed
  (out of scope).
- `sheet/llm/levels.py:42` imports `bisect_left` unused (flake8 F401), already on `HEAD` before this phase. Left.
- `aitu-backend/src/aitu_backend/sheet/README.md` line 71 still names `frames.check_simplify`: a doc, Phase 5
  (plan section 4.4).

## 4. Checks

- flake8 on every changed `.py`: clean (but the old F401 above).
- Backend suite on CPU (running container): **1348 passed, 1 skipped, 2 failed** (the two Transkun tests above).
  1351 tests in all: Phase 2's 1358 (1355 + 3 skipped) less the 7 Simplify tests removed.
- After the last edits (comments of `levels.py`): the stretch, level and frames tests, 68 passed.
- `npx tsc -b`: passes. `npx eslint` on the changed files of `src/`: passes. `node --check` on the check.
- `npm run check:enhance-dialog`: **all passed** (the setting's model by default, the backend's models, the cost of
  GPT-6.1 Sol $0.55 = the backend's, the level and stretch runs sent, no request reached the AI).
- `git grep -n -i simplif -- aitu-frontend`: only the check's guard, the `SongRun` docstring that says Simplify was
  removed, the levels' "whole song simplification" and the dialog's "Simplifying a hand is a level of that hand".
