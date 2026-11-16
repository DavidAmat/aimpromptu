# 06-copy-this-style

**State: paused during Phase 4 (2026-11-16).** Phases 1 to 3 are done (2026-11-04); Phase 4 (the real test) waits for the user's edits
of the two copies. On 2026-11-16 the user merged `feat/06-copy-this-style` into `master` as it was, so that implementation 07 (the PDF sheet
reader, `07-pdf-sheet-reader/`) could start from `master`. 06 resumes after 07, on a new branch `feat/06-copy-this-style-resume` from `master`:
07 changes the sheet code in between (new F1 marks, fixes of the drawing), so the resumed Phase 4 checks first what 07 changed. The user selects a stretch, edits it by hand, and **Copy this style**
(a new tab of **Enhance with AI**) writes every similar passage of the song again in the reference's way of writing.
Also two small requests of the same brief: a Stop button for a transcription, and a paste that works the first time.
One implementation, so its files sit at the top of the group folder. Branch `feat/06-copy-this-style` (Phases 1 to 3), then `feat/06-copy-this-style-resume`.

| File | What it is |
|---|---|
| [`06-prompt.md`](06-prompt.md) | Where the brief is, and what of it this implementation does |
| [`06-plan.md`](06-plan.md) | **The plan.** The user's answers, what the code holds, the design, seven phases, the rules |
| [`06-checklist.md`](06-checklist.md) | THE status lookup, and the decisions |
| [`06-implementation-phase-1.md`](06-implementation-phase-1.md) | Phase 1: the matcher, its tests, the study, the gallery |
| [`06-implementation-phase-2.md`](06-implementation-phase-2.md) | Phase 2: the run in the backend, its routes and tests |
| [`06-implementation-phase-3.md`](06-implementation-phase-3.md) | Phase 3: the tab, the list, the drawing, the panel, the history, the browser check |
| [`gallery/phase-1/`](gallery/phase-1/index.html) | The passages the matcher finds for 12 references (served at `http://192.168.0.112:8099/06/phase-1/`) |
