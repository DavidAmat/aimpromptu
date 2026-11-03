# 06-copy-this-style

**State: Phase 1 done (2026-11-03, the gallery seen by the user); Phase 2 in progress.** The user selects a stretch, edits it by hand, and **Copy this style**
(a new tab of **Enhance with AI**) writes every similar passage of the song again in the reference's way of writing.
Also two small requests of the same brief: a Stop button for a transcription, and a paste that works the first time.
One implementation, so its files sit at the top of the group folder. Branch `feat/06-copy-this-style`.

| File | What it is |
|---|---|
| [`06-prompt.md`](06-prompt.md) | Where the brief is, and what of it this implementation does |
| [`06-plan.md`](06-plan.md) | **The plan.** The user's answers, what the code holds, the design, seven phases, the rules |
| [`06-checklist.md`](06-checklist.md) | THE status lookup, and the decisions |
| [`06-implementation-phase-1.md`](06-implementation-phase-1.md) | Phase 1: the matcher, its tests, the study, the gallery |
| [`gallery/phase-1/`](gallery/phase-1/index.html) | The passages the matcher finds for 12 references (served at `http://192.168.0.112:8099/06/phase-1/`) |
