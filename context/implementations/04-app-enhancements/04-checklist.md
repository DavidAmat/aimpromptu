# 04: App enhancements: checklist

The status lookup for this implementation. The plan is [`04-plan.md`](04-plan.md), the brief is
[`04-1-prompt.md`](04-1-prompt.md). Each phase report is `04-implementation-phase-N.md`, written by the agent that
finishes the phase, following `context/language/communication-implementation-plans.md`.

One phase is one agent session, on its own branch `feat/04-phase-N` made from `master` (plan section 6.3; the names
`feat/phase-N` are taken by implementation 02). Every phase starts with its study and may change its own tasks and
later ones (plan section 6.2); a changed task is changed here and in the plan (section 9 of the plan says why). Every
phase also updates the documentation it makes stale and leaves `scripts/docs/check-links.py` passing.

Status letters: `[x]` complete, `[p]` in progress, `[b]` blocked, `[c]` cancelled, `[ ]` not started.

## Decisions

- [x] **First discussion** (user, 2026-10-27; plan section 3): the decoration-note rule (only fusas or shorter are decoration notes; a lone short note before a much longer one is lengthened to two figures shorter; the last note of a run is not); the rule on every sheet now, at draw time; the notes the AI adds or leaves out kept as Enhance with AI of a stretch does; the AI run on the My library version of 7 Years, after a test on a copy.
- [ ] **Phase 3**: the real 7 Years run, when Enhance it again with AI opens the existing edit copy in the Personal Vault (plan section 3.4).

# [p] Phase 1: The sheet page

- [x] Task 1.1 Study: the header, the floating toolbox and why a hidden one does not come back, the cursor and the click to seek, the zoom path.
- [x] Task 1.2 Command + scroll (and a trackpad pinch) over the sheet zooms it; the sheet is laid out again to the window; one request per pause of the wheel.
- [x] Task 1.3 The AI symbol (`AiMark`) next to the title instead of the green badge; tooltip "Enhanced with AI".
- [x] Task 1.4 The header toolbox: the floating toolbox's buttons, one list drawn in both places; the header stays at the top while scrolling.
- [x] Task 1.5 A hidden floating toolbox comes back (the fix, and a button in the header toolbox).
- [x] Task 1.6 The cursor is dragged and dropped, also across lines; `grab` and `grabbing`; the recording seeks on release.
- [p] Task 1.7 Checks: a browser check of the new hooks on a temporary copy, the existing checks, screenshots; the user checks in the browser.

# [ ] Phase 2: The decoration-note rule

- [ ] Task 2.1 Study: the decoration notes of My library today and what the new rule makes of them; the passages of the two images in 7 Years.
- [ ] Task 2.2 The rule (`find_graces`) and the lengthening step, the user's marks winning; unit tests for each row of plan section 3.1; golden files updated on purpose.
- [ ] Task 2.3 The rule on every sheet, also the stored ones (case 1 of `part_sheet.build`): nothing else changes, time of one drawing measured.
- [ ] Task 2.4 Gallery `gallery/phase-2/` (old and new, checked zoomed in); the user checks it and 7 Years in the browser.

# [ ] Phase 3: Simplicity in the AI's sheet, and 7 Years

- [ ] Task 3.1 Study: the passages of `left-patterns.png` and `complex-fast-notes.png` in 7 Years; how often a broken pattern and a far quick chord occur in My library.
- [ ] Task 3.2 Prompt version 6: the decoration-note text, the rules of simplicity, the amateur pianist rule, an example.
- [ ] Task 3.3 The check of note changes for a whole-song window, and its feedback; tests with recorded answers.
- [ ] Task 3.4 The left-out and added notes stored in `notes.pmn` at the end of a whole run (as `apply_stretch`); counted in the record; undo.
- [ ] Task 3.5 Test on a temporary copy of 7 Years: the image windows, then the whole song (the user asked before each); gallery `gallery/phase-3/`, prompt 5 against prompt 6.
- [ ] Task 3.6 The real run on 7 Years (My library version), after the user's ok and the decision above.
- [ ] Task 3.7 The user checks 7 Years in the browser.

# [ ] Phase 4: Documentation and closing

- [ ] Task 4.1 The documentation still stale: the core's `README.md`, the frontend pages of the sheet page, `context/implementations/README.md`, `context/00-index.md`.
- [ ] Task 4.2 `04-context.md` for later implementations; `03-context.md` section 2 pointed at it for the decoration-note rule.
- [ ] Task 4.3 The final checks; the open points.
