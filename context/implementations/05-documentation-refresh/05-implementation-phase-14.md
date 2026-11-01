# 05, Phase 14: Projects, folders, metadata, parts, Save to library (report)

Wave A. Plan section 6, Phase 14. Written for: the join of wave A and the agents who touch `projects.md` later.

## Docs changed

- **New** `context/frontend/folders-and-metadata.md` (132 lines): the three pills, the folders of My projects and My
  library, the Filter, the metadata (primary and secondary keys), the info dialog and what it changes per kind of
  sheet, where it is kept, the route rules. Why: `projects.md` was over the limit and had no page for the folders.
- `context/frontend/projects.md` (314 to 286 lines): section 1.1 (pills, folders, metadata) replaced by a pointer;
  the info-button bullet of the Sheet step replaced by a pointer (section 6 of the new page); the Parts sentence of
  section 7 corrected (see below); "Sonnet" to "the AI" in section 1 and in the timings of section 8; a link to the new
  page in "Where to look deeper".
- `context/07-database.md`: "Sonnet" to "the AI" in the `sheet.f1` record line and in the `sheet.pending` line (the
  code's `sheet.pending` still exists: `storage/paths.py`).
- `documentation/services/backend/paths-and-data.md`: section 2.1 says folders and metadata are not in the bundle
  (they are rows, section 6); section 10 drops the rows of `bench_pieces.py` and `bench_payloads.py` (the files are gone
  from `aitu-backend/scripts/`) and says so.
- `05-inventory.md`: the states of the three edited files; a row for the new page.

## What was stale

- `projects.md` said the Parts panel lets a user **split** a part. The panel has **Rename**, **Move up**, **Move down**
  and **Join with** the one before (`PartsPanel.tsx`). A part is split off from the range toolbox, **Start a new part
  here** (the panel's own header comment says so). Corrected.
- `paths-and-data.md` section 10 named two bench scripts that no longer exist.
- `07-database.md` and `projects.md` named the model ("Sonnet") where pages should say "the AI".

## Code and docs that disagree in a way that looks like a bug (for the user)

- `aitu-backend/src/aitu_backend/storage/paths.py` (line 185, the docstring of `part_frames_pending_path`) still says
  "asks Sonnet to write the sheet". A comment, not a behaviour; the user may want it to say "the AI".

## New terms for the glossary (Phase 20)

- **the pills** (All, Folders, Filter): the three choices above a list (already in use in the code's comments).
- **Folders view**, **the Folders…** of a row (the tree with a checkbox per folder).
- **primary key** and **secondary key** (metadata: Film, TV show, Video game, Advert; and the user's own values).
- **the info dialog** (the "i" dialog: sheet, song page, row menu).
- **Join with** (a part joined to the one before it, in the Parts panel).

## Not checked

- Routes and bodies of `api/projects.py`, `api/folders.py`, `api/metadata.py` were read only through their headers and
  route list; `library/folders.py` and `library/metadata.py` were not read. The rules in the new page (404, 403, 409, 422)
  come from the module docstrings and from `endpoints.md` section 7.1.1, not from the code.
- `editing/parts.py` (join, split) and `storage/bundle.py` were not read; the parts routes in `endpoints.md` were not
  re-checked against code.
- `pages/ProjectsPage.tsx` only through its menu labels and the New project menu labels (all match).
- The app was not run (rule of section 5).
- `check-names.py` on `paths-and-data.md` still lists six names, all history or container paths: `session.json`
  (until Phase 9, removed), `scripts/migrate/to_database.py` (removed in Phase 15 of implementation 02), `AITU_DATA_DIR`
  (removed), `/hf/hub` (a path in the container), `bench_pieces.py` and `bench_payloads.py` (removed; now named as
  removed). `07-database.md` lists `scripts/migrate/to_database.py` as history too.
- `context/music-library/private-library.md` is owned by Phase 18 (wave A, done). Its Save to library part was checked
  here, and the edits are below as pending edits.

## Pending edits for shared files

1. **`documentation/services/backend/endpoints.md`**, section 7, the table of "The row", the `running` row: replace
   `while Sonnet writes the sheet of a part (implementation 03, Phase 5)` with
   `while the AI writes the sheet of a part (implementation 03, Phase 5)`.
2. **`documentation/services/backend/endpoints.md`**, section 7.1.1: at the end of the paragraph that starts
   "`api/folders.py`, `api/metadata.py`", after "`422` for an empty name or an unknown primary key.", add a new line:
   `The page that tells them: [folders-and-metadata.md](../../../context/frontend/folders-and-metadata.md).`
3. **`documentation/services/frontend/components.md`**, section 8.1: directly under the heading
   `### 8.1 Folders, the pills and the metadata (implementation 04-3, Phase 1)`, add a new line:
   `The page that tells them: [folders-and-metadata.md](../../../context/frontend/folders-and-metadata.md).`
4. **`context/00-index.md`**: add the file `frontend/folders-and-metadata.md`, with the one-line description
   "Folders, the pills, the Filter, the metadata and the info dialog", after the line of `frontend/projects.md`.
   (Check the index's own format first.)
5. **`context/music-library/private-library.md`** (owner Phase 18, done):
   a. Section 5.1 heading `### 5.1 Folders and metadata (implementation 04-3, Phase 1)`: directly under it, add the line
      `The page that tells them: [folders-and-metadata.md](../frontend/folders-and-metadata.md).`
   b. Section 7 ("Not built yet"), the paragraph "The 30 songs the migration of Phase 3 put in": replace
      `(`aitu-frontend/scripts/sheet-library.mjs`: **Edit**` with `(the script `sheet-library.mjs`, since removed: **Edit**`.
      The path is gone, so `check-names.py` lists it today.

## Left for later phases

- **Phase 4**: the "4. Sheet" section of `projects.md` (about lines 165 to 230) still names Sonnet several times ("goes to
  Sonnet", "Sonnet's sheet", "Sonnet 5.5 today"). Phase 4 turns that section into a short summary with a link, so
  these go with it. Phase 4 also removes the old text it summarises.
- **Phase 16**: the Notes section of `projects.md` says "Until Sonnet decides them" (about line 158).
- **Phase 15**: the Source and Audio parts of `projects.md`.
- **Phase 20**: `projects.md` is 286 lines, over the about-200 limit. Phase 4's summary saves about 40 lines, which gets it
  near 245. The **Timings** section 8 (about 20 lines, measurements from implementation 08) could move to an archive
  page; a decision for the user or for Phase 20.
- **Phase 17**: the **From other projects** part of section 7 is short and was left as it was, apart from the Parts
  sentence.
