# 04-7: The open points of implementation 04: the brief

Written 2026-11-03 at the end of 04-6, from the user's words: implementation 04 stays open until these points are
done (the user did not want to close it with them still open). Plan it with
[`../../guidelines/guidelines-implementation-plan.md`](../../guidelines/guidelines-implementation-plan.md) and report
with [`../../guidelines/guidelines-communication-with-user.md`](../../guidelines/guidelines-communication-with-user.md).
Read [`04-context.md`](04-context.md) sections 4, 8 and 9 first. 04-4 ("Copy this style") is **not** part of this:
it is left for a later, larger implementation plan.

## The user's words

> Keep 04 open. Please address this thing that is open and create a handoff prompt so that I can implement it in a
> new AI session.

When every point below is done or decided, 04 is closed: the state lines of [`README.md`](README.md),
`../README.md` and `../../00-index.md` say so.

## The open points (read 2026-11-03, check each again)

### 1. The clef of the left hand (04-5 checklist, Decisions, the one task not done)

- **The user's rule (2026-10-31)**: the left hand changes to the treble clef only when a whole passage lies high. One
  or two high notes are written with ledger lines or an 8va line, in the bass clef.
- **The prompt already says it** (level prompts, `sheet/llm/prompt/levels/shared.md`, "The register"), but the AI does
  not draw the clefs: the app does, in `sheet/proposal/frames.py` `clefs_and_ottavas` (a cheapest path over the
  columns of each hand: `STATES`, `CLEF_PREFER`, `OTTAVA_COST`, `BASS_LIMIT = 4`). Today a left-hand note 4 ledger
  lines or more above the bass staff makes the bass clef impossible for that column (`BASS_LIMIT`), so a single high
  note can force the treble clef. Check whether that is what the user sees.
- **The risk** (04-context section 4): every stored sheet is laid again when it is drawn, so a change of this rule
  changes every sheet of My library at once. Measure it before and after on every stored sheet (the way 04 Phase 2
  measured the decoration-note rule with `scripts/grace_gallery.py --study`): count the clef changes and the 8va
  notes per sheet, and show the user the passages that change, drawn by the app. Only the clefs and the 8va may
  change.
- To settle with the user in the plan: what "a whole passage" is (how many columns or seconds, how many high notes),
  and whether the right hand gets the same rule (it also has a bass-clef state).

### 2. Hard and the figure check (04-context 8.5)

- `sheet/llm/levels.py` `LIMITS["hard"]` has `shortest` 64, and the check refuses a new note only when
  `n.figure > lim.shortest`, so at Hard the figure check never refuses anything (easy and medium use `steady`
  instead). Ask the user: is that intended (Hard may write any figure), or should Hard refuse figures shorter than a
  fusa (32)? If intended, say so in a comment and in `context/ai/level-run.md`; if not, change it and test it.

### 3. Stop keeps the batches it accepted (04-context 8.5)

- A **Stop** of a level run keeps the batches already accepted and saved (the page of the level run says so;
  `part_sheet/job.py` `_level_work`). Ask the user: keep it (the user can still **Revert** the run), or should a Stop
  of a level run throw away the whole run? If it changes, the dialog's words, the history and the docs change with it.

### 4. The temporary copies of 20 de Enero (04-context 8.5)

- The real runs of 04-5 (Phase 2) worked on temporary copies of the song 20 de Enero, kept until the user had looked
  at the pages. Find them (their names and ids are in
  [`04-5-implementation-phases-1-to-4.md`](04-5-implementation-phases-1-to-4.md); the database is
  `AITU_DATABASE_DIR` of `.env`, a host script loads `.env` first), list them to the user, and delete them only after
  the user's ok. Never touch the original song.

### 5. The octaves of the user's words (04-context 8.5)

- Already decided (04-5 checklist, Decisions, 2026-10-31: the octaves are only examples; the AI chooses what reads
  best on the staff) and in the prompt ("The register"). The line in 8.5 is out of date: close it there, no code.

### 6. From 04-6 (04-context 9.3)

- **The fresh backend image has no `openai`** (04-6 Phase 4 report, section 3). `docker compose build backend` fixes
  it, but it restarts the user's app: ask the user for the time, or leave it to the user as a step in HUMAN
  INTERVENTION.
- **Two Transkun tests fail on the CPU** (`tests/test_transcription_transkun.py`: "Attempting to deserialize object
  on a CUDA device"): the Transkun checkpoint is loaded without `map_location`. Make the tests pass on the CPU
  (load the checkpoint on the device of the run, or skip the two tests when there is no GPU), without changing a
  transcription on the GPU.

## Open points to settle with the user in the plan

Short, the recommended option first: the size of "a whole passage" for the clef (point 1), Hard's shortest figure
(point 2), a Stop of a level run (point 3), the copies to delete (point 4), the time of the image rebuild (point 6).

## Rules

- One branch, `feat/04-7-open-points`, from `master`. Merge into `master` only at the user's ok.
- The app runs in containers that mount this working tree: the backend reloads on every `.py` edit, which stops a
  running AI run. Before the first edit of `aitu-backend/src`: `ps aux`, `docker logs aimpromptu-backend-1`, and no
  log `ai-runs/*.json` in `running`.
- Never print or copy a key from `.env`. Tests on CPU (another project often holds the GPU); no AI request in the
  tests. The backend suite runs in the running container (`docker exec -e CUDA_VISIBLE_DEVICES= ...`, the 04-6
  Phase 4 report).
- No browser check or script writes on a real library piece: use temporary copies. The measure of point 1 only
  reads the stored sheets.
- Show the user the drawn passages of point 1 zoomed in, checked against the data, served over HTTP for the Mac
  (`http://192.168.0.112:<port>`), never a file path.
- At the end: the docs (`context/ai/level-run.md`, `run-history.md`, the sheet's clef rule in
  `aitu-backend/src/aitu_backend/sheet/README.md`), `04-context.md` (8.5 and 9.3 closed, a section for 04-7),
  `python3 scripts/docs/check-links.py`, `scripts/docs/check-names.py` on each doc changed.
