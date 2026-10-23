# 03: The new sheet in aimpromptu: checklist

The status lookup for this implementation. The plan is [`03-plan.md`](03-plan.md), the brief is
[`03-prompt.md`](03-prompt.md). Each phase report is `03-implementation-phase-N.md`, written by the agent that
finishes the phase, following `context/language/communication-implementation-plans.md`.

One phase is one agent session, on the branch `feat/migrate-new-logic` (plan section 6.3). Every phase starts with
its study and may change its own tasks and later ones (plan section 6.2); a changed task is changed here and in the
plan (section 11 of the plan says why). Every phase also updates the documentation it makes stale and leaves
`scripts/docs/check-links.py` passing.

Status letters: `[x]` complete, `[p]` in progress, `[b]` blocked, `[c]` cancelled, `[ ]` not started.

## Decisions

The decisions of the second discussion are in plan section 3 (answered 2026-10-23). The ones still open are raised by
their phase, after its study (plan section 8).

- [x] **Phase 2**: the figure thresholds (agent: 0.7, measured against 0.5, 0.6 and 0.8) and the spelling in Do mayor (agent: Do#, Mib, Fa#, Sol#, Sib, the research rulebook). The user checks them in the gallery.
- [x] **Phase 2**: the cap of a figure at the next onset of its hand: kept (the agent's recommendation; the user said "perfect, proceed").
- [x] **Phase 2**: rule 4 in armaduras of one to three signs: as written, everywhere (the user did not change it; one condition in `spelling.spell_pc` if they do).
- [ ] **Phase 3**: the look of the spacing without compases (user, in the gallery).
- [ ] **Phase 4**: the API key (human intervention); how many songs the credits cover (information); the beam groups and the maximum of 8 notes (user, in the gallery).
- [ ] **Phase 5**: existing projects, keep their corrections or write them again with the LLM; merge into `master` early or at the end.
- [ ] **Phase 6**: may a new LLM run change hands that the user moved; the engine in the backend or in the browser.
- [ ] **Phases 7 and 8**: the tools that no longer make sense without compases: keep, change or drop.

# [x] Phase 0: The research folder on Ubuntu, the branch, the inventory

Done 2026-10-23. Report: [`03-implementation-phase-0.md`](03-implementation-phase-0.md).

- [x] Task 0.1 The research folder on Ubuntu: `uv sync`, the core tests (139) and the golden files pass; the whole research suite too (367).
- [x] Task 0.2 The branch `feat/migrate-new-logic` and this folder (`README.md`, `03-prompt.md`, `03-plan.md`, this checklist).
- [x] Task 0.3 The inventory, high level: every screen and tool that uses vexflow-v2 or `TimeScorePayload`, with the phase that moves it.
- [x] Task 0.4 The baseline screenshots of every screen that shows a sheet (`scripts/baseline-sheets.mjs`, 22 screens), and the counts of the checks.

# [x] Phase 1: The core inside the backend

Done 2026-10-23. Report: [`03-implementation-phase-1.md`](03-implementation-phase-1.md).

- [x] Task 1.1 `aitu_notation` copied into the backend (`aitu_backend/sheet/`), with its frozen files; golden tests in `tests/` (`test_sheet_core_*.py`, `tests/golden/sheet/`); `sheet.pmn` replaced by `aitu_backend.pmn` and `aitu_backend.matrix.keys` (identical, checked again).
- [x] Task 1.2 The golden tests pass inside the backend container (139); the other backend tests are unchanged.
- [x] Task 1.3 `scripts/draw_sheet.py` draws library songs with the bars engine: all 33 of My library, identical to the research core byte for byte; time per song in the report.

# [x] Phase 2: The new sheet without compases (format and algorithm)

Done 2026-10-23. Report: [`03-implementation-phase-2.md`](03-implementation-phase-2.md).

- [x] Task 2.1 Study: what the F1 frames view carries, what the algorithm needs from the pulse estimate (only the reference figure); the lengths under the pedal and the uneven chords measured.
- [x] Task 2.2 The format: hands, plain figures, beam groups, graces, ornaments (`orn`), clef changes, armadura per passage, 8va, `quarterMs=`; no rests, no compases, no tuplets. Reader, writer, `frames.check`, round trip with the matrix (33 of 33 songs exact).
- [x] Task 2.3 Figures from the note's own length, capped at the next onset of the hand, with the reference figure; split 0.7 measured on the 10 viewer songs; one figure per chord per hand, and per run of even gaps.
- [x] Task 2.4 Grace notes from the two-step rule: a semicorchea or shorter that sounds just before its main note (after the user's review). Beam groups of one figure (one odd note at an edge at most).
- [x] Task 2.5 Alteraciones: rules 1 to 5 as a rule of the core (`spelling`); Do mayor decided; the armadura with the fewest signs per passage.
- [x] Task 2.6 The algorithm (`propose_frames`) writes this sheet for every library song, with the simple beam rules; its starting hands from `pipeline.starting_hands` (the saved hands and the hand split).
- [x] Task 2.7 Gallery for the user (figures, graces, alteraciones, the unusual cases of rule 4): `gallery/phase-2/index.html`, 14 cases, checked by the user after two iterations (beam groups of one figure, acciaccaturas, whole groups drawn).

# [ ] Phase 3: The engine without compases

- [ ] Task 3.1 Study: which parts of `engrave` depend on compases.
- [ ] Task 3.2 Spacing: one x per onset frame for both hands, width from the notes in either hand, compressed empty time.
- [ ] Task 3.3 Line breaks without compases, stable when one segment changes.
- [ ] Task 3.4 Accidentals on every altered note; no rests, compás lines, meter or bar numbers.
- [ ] Task 3.5 Cursor map and note ids; one segment drawn on its own.
- [ ] Task 3.6 Speed per song and per segment, cold and warm, on the 10 viewer songs, in the container (its Python build: Phase 1 measured it about 30 % slower than the host).
- [ ] Task 3.7 Gallery: vexflow-v2, the bars engine and the new engine side by side.

# [ ] Phase 4: The LLM step for the new sheet

- [ ] Task 4.1 HUMAN INTERVENTION: the API key in `.env` (`ANTHROPIC_API_KEY`); three test requests with their `usage` and time.
- [ ] Task 4.2 `complete(system, messages)` with the `anthropic` SDK, `claude-sonnet-5-5`, prompt caching, time limits, retries.
- [ ] Task 4.3 The prompt version 5: the new format, the histogram of gaps in words, the alteraciones rules, the beam group criteria, the clef rules version 4; windows by onsets or time.
- [ ] Task 4.4 The checker and the guards for the new format (at most 8 notes per beam group); the fallback to the algorithm.
- [ ] Task 4.5 A few windows, then the 10 viewer songs; comparison with the recorded Sonnet sheets; cost per song.
- [ ] Task 4.6 Gallery: the algorithm and Sonnet side by side.

# [ ] Phase 5: The new Sheet step (to see and to hear)

- [ ] Task 5.1 Study; question to the user on existing projects.
- [ ] Task 5.2 The flow: Hands step removed; Notes Falling playable without hands; the negra choice removed.
- [ ] Task 5.3 The algorithm's sheet at once; the LLM job in the background; grey segments; a finished segment appears little by little; no text.
- [ ] Task 5.4 The LLM's hands saved in `notes.pmn`.
- [ ] Task 5.5 The new sheet saved beside `sheet.json`; reopening does not call the LLM again.
- [ ] Task 5.6 Playback: cursor, lit notes, click to seek.
- [ ] Task 5.7 vexflow-v2 reachable for editing (a switch inside `SheetPage`) until Phase 8; waiting segments not editable.
- [ ] Task 5.8 The browser checks of the Sheet step moved to `data-*` hooks of the new view.
- [ ] Task 5.9 No line naming the figure and a tempo above the passages.
- [ ] Task 5.10 Question to the user: merge into `master` now or at the end.

# [ ] Phase 6: Editing the new sheet (the edit model, hands, undo)

- [ ] Task 6.1 Study: how the vexflow-v2 editor applies a change (selections, `sheet.json` writes, undo and redo).
- [ ] Task 6.2 The edit model, with undo and redo.
- [ ] Task 6.3 First tool: move notes between hands; the LLM run again receives the current hands; question to the user.
- [ ] Task 6.4 The time of one edit; the decision on where the engine runs.

# [ ] Phase 7: The note and range tools

- [ ] Task 7.1 Study and inventory of the two toolboxes; the list of tools that may no longer make sense goes to the user.
- [ ] Task 7.2 The tools on the edit model.
- [ ] Task 7.3 The engine features the tools need, kept light.

# [ ] Phase 8: The other screens and the sheet toolbox

- [ ] Task 8.1 Study and inventory (the sheet toolbox, the keyboard panel, Find trills, Play mode, Recording in Sheet, copy and paste, parts and playlists, the PDF, the Transpose preview, From other projects, the requests review).
- [ ] Task 8.2 Lyrics in the format and in the engine.
- [ ] Task 8.3 Each screen on the new engine; vexflow-v2 no longer draws or edits anywhere; its browser checks moved.

# [ ] Phase 9: The saved data

- [ ] Task 9.1 Study of `.database/`: parts, correction fields in use, how often.
- [ ] Task 9.2 The corrections mapped onto the new sheet, or written again by the LLM, or both (the user's answer of Phase 5).
- [ ] Task 9.3 The migration: `make db-backup` first, a dry run, a count of what moved and what could not.

# [ ] Phase 10: vexflow-v2 removed, documentation, closing

- [ ] Task 10.1 Remove `@aimpromptu/grid-notation`, the `TimeScorePayload` routes, `notation/`, the negra ladder for the sheet, the Hands step page and Predict hands (`aitu_backend/hands/` stays).
- [ ] Task 10.2 Documentation: the time model, the project steps, the sheet pages, rendering, the API.
- [ ] Task 10.3 All checks; the final screenshots against the Phase 0 baseline (`node scripts/baseline-sheets.mjs --out .../phase-10`); merge into `master` after the user's ok.
- [ ] Task 10.4 Licenses before any release (Verovio rules, Leipzig glyphs, the prompt examples).
