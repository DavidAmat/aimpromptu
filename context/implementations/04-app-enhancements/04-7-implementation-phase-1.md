# 04-7 Phase 1: Housekeeping

Plan [`04-7-plan.md`](04-7-plan.md) sections 4.5, 4.6 and 5; checklist [`04-7-checklist.md`](04-7-checklist.md).
Branch `feat/04-7-open-points`. No edit of `aitu-backend/src` in this phase. 2026-11-03.

# 1. The checks before the work (1.1)

- `ps aux`: the frontend's vite, the backend's container, and other projects; no pytest or browser check of this
  project.
- `docker logs aimpromptu-backend-1`: only `GET /health` since the last reload (04-6).
- The 10 logs `ai-runs/*.json` (field `state`): 9 `done`, 1 `waiting` (a level run of My library waiting for **Go on
  with the other batches**). None `running`.

# 2. The TEMP projects (1.2)

The six ids of plan section 3.4, read first (read-only script in the container):

| Id | Layer | Title | Version row | `levelOf` |
|---|---|---|---|---|
| `47999e53` | vault | TEMP 04-5 A: Strict easy 1 with words | none | `7603ca29` |
| `952d4480` | vault | TEMP 04-5 A2: Strict easy 1, the pattern's register | none | `7603ca29` |
| `8e1c50a8` | vault | TEMP 04-5 B: Suggested easy 1 | none | `7603ca29` |
| `07b1c431` | vault | TEMP 04-5 C: Strict easy 5 | none | `7603ca29` |
| `3ed5bde6` | vault | TEMP 04-5 D: first batch, answer, go on | none | `7603ca29` |
| `39d92dbe` | private | TEMP 04-5 D: first batch, answer, go on · Easy, left hand | version 40 (`easy`) of song 21108 | none (`origin.levelOf` = `3ed5bde6`) |

None had dependents (`bundle.dependents`: passages, takes) or edit copies (`based_on`).

**Deleted**: the five of the vault, as `delete_project` of `api/projects.py` does (`flow.release_levels(owner, id)`, then
`bundle.delete_project(id)`), each checked first to be a `vault` row with a title starting `TEMP 04-5`. After: each
row gone and each folder gone.

**Deleted after the user's answer**: `39d92dbe`. It is the only version of a song "20 de enero" (song 21108, artist
La Oreja de Van Gogh) of My library, in the user's folder **Karaoke Viernes** (folder 4, 8 songs), saved on
2026-10-31 at 11:24; its undo log holds clefs set by hand (plan section 3.3). The app deletes a version of My library
with `flow.delete_version` (which also turns its edit copies into projects of the vault) and a song with
`flow.delete_song`, not `delete_project`; and deleting the last version leaves an empty song in the folder. The plan
asked for `delete_project`, written when the copy was thought a project of My projects (plan section 8). The options
were: delete the whole song, delete the version only (the song stays empty in Karaoke Viernes), or keep it. **The
user's answer (2026-11-03): delete the whole song.** Done with `flow.delete_song(21108, owner=1)` (what
`DELETE /library/songs/{id}` does), after a check that the song still had the one version `39d92dbe`. After: the song,
the project, its version row, its folder row and its folder gone; Karaoke Viernes holds 7 songs; the logs
`ai-runs/*.json` of the copy (one `waiting`) went with it.

Deleting `3ed5bde6` before `39d92dbe` was safe: `metadata.release_levels` reads the `level_of` column, which is empty
for `39d92dbe`, and `bundle.dependents` reads `passageOf` and `takeOf` only.

**Still there** (checked after: the row, the folder, the parts, the audio refs):

| Id | Layer | What |
|---|---|---|
| `7603ca29` | vault | the original song 20 de enero (never enhanced: `notes.pmn`, no `sheet.f1`; files last changed 2026-10-30) |
| `d6211999`, `7b9a41e4`, `0df15e84`, `b13cbcde`, `946c21f2` | vault | the user's level copies, each with its `sheet.f1` |

No project with a title starting `TEMP` is left.

Note for the plan: section 3.4 names six level copies of the user ("`7603ca29`, `d6211999`, ..."), but `7603ca29` is
the original song, so the user's level copies are five.

# 3. The Transkun tests (1.3)

- The failure on the CPU, as the plan says: the container sets `AITU_DEVICE=cuda`, the engine loads its weights with
  `map_location=device`, and with `CUDA_VISIBLE_DEVICES=` there is no GPU for `cuda`.
- The fix, in `tests/test_transcription_transkun.py` only: the two tests build `TranskunEngine(device="cpu")`, with a
  comment that says why. The engine's code does not change, so a transcription still runs on `config.device()`.
- `tests/test_transcription_transkun.py` on the CPU: 6 passed (2 failed before).
- The whole backend suite on the CPU (`docker exec -e CUDA_VISIBLE_DEVICES= -e NVIDIA_VISIBLE_DEVICES=void ...
  python -m pytest`): **1350 passed, 1 skipped, 0 failed**. The project's `addopts = "-q"` prints no summary line
  with a second `-q`: count the marks of the output, or run without `-q`.

# 4. The octaves of the user's words (1.4)

[`04-context.md`](04-context.md) 8.5: the line is closed, with the decision (user, 2026-10-31, 04-5 checklist,
Decisions) and the prompt that says it (`sheet/llm/prompt/levels/shared.md`, "The register"). The other lines of 8.5
are closed in Phase 5 (plan section 4.7).

# 5. For the next phases

- The parts with clefs set by hand (plan section 3.3) are now three: My Way (`c33860b5`) and two level copies of 20
  de enero (`7b9a41e4`, `946c21f2`).
- Phase 2 edits `src/`: do the checks of 1.1 again first (the backend reloads on each `.py` edit).
