# 03: The new sheet in aimpromptu (applying the research)

**State: live. Phases 0 to 5 done (Phase 5 on 2026-10-25, merged into `master`); Phase 6 is next.** Opened 2026-10-23 on the branch
`feat/migrate-new-logic` (one branch for the whole migration, plan section 6.3).

Research plan 01 (the folder `/home/david/Documents/projects/music/poc-aitu-research` on the Ubuntu machine) built a
new chain for the piano sheet: an algorithm, an LLM step with Sonnet 5.5, and an engine that draws the sheet as SVG.
This implementation replaces vexflow-v2 (`@aimpromptu/grid-notation`) with that chain, adapted to the user's
decisions of 2026-10-23: no compases, no tempo, no puntillos and no silencios on the sheet, the Hands step removed,
and the LLM working in the background while the algorithm's sheet is already on screen.

The brief is [`03-prompt.md`](03-prompt.md), the plan is [`03-plan.md`](03-plan.md) and the status lookup is
[`03-checklist.md`](03-checklist.md). Phase reports go beside them as `03-implementation-phase-N.md`, following
[`../../language/communication-implementation-plans.md`](../../language/communication-implementation-plans.md).

| File | What it is |
|---|---|
| [`03-apply-research-prompt.md`](03-apply-research-prompt.md) | The first message to the Phase 0 agent, in the user's words |
| [`03-prompt.md`](03-prompt.md) | The brief: the user's answers of the second discussion (in Spanish), a copy of the research's `05-final-report-prompt.md` |
| [`03-plan.md`](03-plan.md) | The plan: the decisions, the binding rules, what is reused, the method, eleven phases (0 to 10), the decision points, the risks, and the changes the phases made (section 11). A copy of the research's `05-final-report.md`, now the living plan |
| [`03-checklist.md`](03-checklist.md) | The status lookup, and the open decisions |
| [`03-implementation-phase-0.md`](03-implementation-phase-0.md) | Phase 0: the research folder checked on Ubuntu, the branch, the inventory of everything that uses vexflow-v2, the baseline (screenshots in [`screenshots/phase-0/`](screenshots/phase-0/), test counts) |
| [`03-implementation-phase-1.md`](03-implementation-phase-1.md) | Phase 1: the research core copied into the backend as `aitu_backend/sheet/`, its golden tests in the container, `scripts/draw_sheet.py` and the time per song of My library |
| [`03-implementation-phase-2.md`](03-implementation-phase-2.md) | Phase 2: the new sheet without compases (the F1 frames view), the figure, grace note and spelling rules measured on the songs, the algorithm on all of My library, two decisions for the user |
| [`gallery/phase-2/index.html`](gallery/phase-2/index.html) | The Phase 2 gallery: 15 passages as F1 text and as notes (built by `aitu-backend/scripts/sheet_gallery.py`) |
| [`03-implementation-phase-3.md`](03-implementation-phase-3.md) | Phase 3: the engine without compases (`engrave/frames.py`): spacing, line breaks, one segment, speed in the container, the gallery |
| [`gallery/phase-3/index.html`](gallery/phase-3/index.html) | The Phase 3 gallery: 8 passages drawn by vexflow-v2, the bars engine and the new engine, and one whole song (built by `aitu-backend/scripts/frames_gallery.py` and `aitu-frontend/scripts/vexflow-passages.mjs`) |
| [`03-implementation-phase-4.md`](03-implementation-phase-4.md) | Phase 4: the LLM step for the new sheet (`sheet/llm/frames.py`, prompt version 5, `sheet_llm.py`): the design, the 10 viewer songs with Sonnet 5.5, the cost, the gallery |
| [`gallery/phase-4/index.html`](gallery/phase-4/index.html) | The Phase 4 gallery: 10 passages written by the algorithm and by Sonnet (built by `aitu-backend/scripts/llm_gallery.py`) |
| [`03-implementation-phase-5.md`](03-implementation-phase-5.md) | Phase 5: the new Sheet step in the app: the Hands step removed, the new sheet at once, Sonnet in the background segment by segment, the hands saved in the notes, the cursor, the switch to the old sheet, the checks |
