# 04-3 · Phase 1 report: folders, the pills and the metadata

Audience: the agents of the later phases of [`04-3-plan.md`](04-3-plan.md). Technical; the walkthrough for the user
is in the chat. Branch `feat/04-3-phase-1`, made from `master` at `4950901`. State: built and checked on 2026-10-29;
changed the same day after the user's first look (section 2.5: the metadata belongs to the song); waiting for the
user's check in the browser (task 1.9), then the merge.

# 1. Summary

My projects (`/projects`) and My Library (`/library/songs`) have three pills, **Folders**, **All** and **Filter**.
Folders are a tree per user and area (`projects`, `library`), each folder pointing at its parent's id; an item points
at folder ids, so a parent folder made on top of a folder changes one row. An item can be in several folders. The
metadata is a primary key of the Public Library's fixed list and a secondary key of the user's own, in its own table.
The **info button** is on the sheet page and on the song page of My Library, and **Info** is in the `⋯` of a row of
both pages. The metadata and the folders of My Library belong to the **song**, never to one version: an edit copy in
My projects shows and changes its song's. Revisions `0008` and `0009`; the real database is at `0008` since
2026-10-29 19:06 (backup `/mnt/ssd2/aimpromptu/.database-20261029-190549.tar.zst`, 1.4 GB, taken just before) and at
`0009` since 23:13 (backup `.database-20261029-221243.tar.zst`).

# 2. Study

## 2.1 Section 4.1 of the plan

Confirmed as written: `ProjectsPage.tsx` is a list of `ListRow`s with no search; `SongsPage.tsx` a `DataTable` with a
text filter and checkboxes; project ids are uuids, song ids integers; `tag_categories` fixed (`films`, `video_games`,
`tv_shows`, `adverts`), `tag_values` 87 rows and `song_tags` 121 rows on the real database; private songs had no
metadata; `pull.py` copied no tags; the UI kit has `Pill`, `FilterChip`, `DataTable`, `ListRow`, `RowMenu`; the last
revision was `0007`. Also found: `project_rights` (`auth/dependencies.py`) checks any route with a `project_id` path
parameter, so `PUT /folders/projects/{project_id}` and `PUT /metadata/projects/{project_id}` get `403` on a library
project and `404` on another user's before the route runs, and `GET /metadata/info/{project_id}` gets the read check
(public, shared libraries) for free.

## 2.2 The real data (read only)

- 13 projects of the Personal Vault (kind `song` or `integratedPlaylist`), 2 of them edit copies (`based_on`): 7 Years
  (`477086a0`) and 99 Red Balloons (`c0e39afe`). 33 private songs, 1 linked to a public song.
- **Where a project has an artist** (plan section 4.3): only the edit copies, through `ProjectRow.editing.artists`.
  The sheet's title lines (`sheet.f1`, `artist "…"`) have an artist only on 7 Years, which also has the link. Decision:
  the Filter's Artist on My projects reads `editing.artists` (or `library.artists`), nothing else (plan section 10,
  point 4).

## 2.3 Save to library, Edit, Duplicate

- **Save to library** (`flow.save`) moves the bundle and changes `projects.layer` to `private` on the same row, so
  `folder_projects` rows would stay on a project that is not in My projects any more. `flow.save` now deletes them
  (`folders.drop_project_folders`) and gives the song the project's metadata (`metadata.add_project_tags_to_song`,
  which also deletes the `project_tags`).
- **Replace** (`flow._replace`) deletes the copy (its links go with the row, `ON DELETE CASCADE`); the song gets the
  copy's metadata first.
- **Edit** (`flow.open_edit`) gives the copy no metadata: an edit copy reads and changes its song's (section 2.5).
  A copy saved as a new version of **another** song gives that song its song's metadata too
  (`metadata.add_song_tags_to_song`, with the song read before the move clears `based_on`).
- **Duplicate** (`POST /projects/{id}/duplicate`, `_copy_organized`): a project of My projects gives its copy its
  metadata and its folders; a version of My Library gives the copy the song's metadata; another user's (shared) or a
  public project gives nothing. `bundle.new_bundle_from` keeps `based_on`, so the duplicate of an edit copy is an
  edit copy of the same version (it was before this phase): it gets no rows of its own and shares the song's.
- **Delete a version** (`flow.delete_version`, `_forget_edits_of`): its edit copies become ordinary projects, and
  each gets the song's metadata as its own first (`metadata.copy_song_tags`).

## 2.4 The three cases of the info button

`GET /metadata/info/{projectId}` (`api/metadata.py`, `info`):

| Sheet | `kind` | What it shows | `editable` |
|---|---|---|---|
| A project of My projects with no song | `project` | the project's `project_tags` and `folder_projects` | owner |
| A version of My Library (`layer = private`), or an edit copy of one (99 Red Balloons `c0e39afe`, 7 Years `477086a0`) | `song` | the song's `private_song_tags` and `folder_songs`, the same for every version | owner only; a library shared with the user is read only, with no folders |
| A version of the Public Library (`layer = public`, through `song_versions` or `user_versions`) | `public` | the public song's tags | never |
| A request's copy, or a project with no song | `none` | nothing | never |

## 2.5 The metadata belongs to the song (the user, 2026-10-29)

After the first walkthrough the user asked that whatever the info button changes, on the song page or on the sheet
of `c0e39afe`, belong to the song, not to one version: a song has an original, an easy and a hard version, and the
metadata is about the song. The song page and the sheet of a version of My Library already wrote the song's rows.
The edit copy did not: it had a copy of the song's metadata in `project_tags`, so a change there stayed on the copy
until **Save to library**, and the copy's dialog offered the folders of My projects.

Now `metadata.edited_songs` finds the song of an edit copy (`projects.based_on` → `private_versions.song_id`, vault
only; a copy whose version was deleted has none). `tags_of_projects` answers the song's rows for it,
`set_project_tags` writes the song's, and `GET /metadata/info` answers `kind: song`. So the info button, the row's
**Info** of My projects (which now reads `GET /metadata/info` instead of building the target on the page) and the
Filter all go to the song. The dialog says "For the whole song: every version has it" and names the tree of its
folders ("Folders of My Library", "Folders of My projects"). The copy's place in the folders of My projects stays
with **Folders…**. Revision `0009_song_level_metadata.py` moved the `project_tags` of edit copies to their songs:
the real database had one, the user's Film "A Star Is Born" on the 7 Years copy, now on the song 7 Years (song 4).
The user's folders Test and Test1 (both edit copies in Test1) are folders of My projects and did not change.

`SheetStep` did not know the project id; `SheetTab` now passes `projectId` (`audio.projectId ?? uuid`). Play mode, a
passage and From other projects do not pass it, so they have no info button.

# 3. What was built

## 3.1 Database (revision `0008_folders_and_metadata.py`, `HEAD_REVISION = "0008"`)

| Table | Columns | Notes |
|---|---|---|
| `folders` | `id`, `owner_id` (cascade), `area` (`projects`, `library`; check `area_allowed`), `parent_id` (self, cascade), `name` (200), `created_at` | index `(owner_id, area)`, `parent_id`. Names unique among siblings ignoring case, checked by `library/folders._check_name` (SQL cannot: `NULL` parents) |
| `folder_projects` | `folder_id`, `project_id` | both cascade; PK the pair |
| `folder_songs` | `folder_id`, `song_id` | both cascade |
| `private_tag_values` | `id`, `owner_id` (cascade), `category_id` (`tag_categories`), `value` (200) | unique `(owner_id, category_id, value)`; compared with `rows.same` in Python (SQLite `lower` is ASCII only) |
| `project_tags` | `project_id`, `tag_value_id` | both cascade; never on an edit copy (revision `0009`) |
| `private_song_tags` | `song_id`, `tag_value_id` | both cascade |

`alembic.autogenerate.compare_metadata` against the models: no difference for these tables. Only tables are added.
Revision `0009_song_level_metadata.py` changes no table: it moves the `project_tags` rows of edit copies to their
song's `private_song_tags` (`INSERT OR IGNORE`) and deletes them; its downgrade leaves them on the song.

## 3.2 Backend

- `library/folders.py`: `list_of`, `create`, `rename`, `move` (refuses into itself or a folder inside it, `_inside`),
  `make_parent` (children must share a parent; the new folder's name may equal a child's), `delete_folder` (deletes
  the subtree and links explicitly too, so it holds with foreign keys off), `set_project_folders` (vault projects of
  the owner only), `set_song_folders`, `folders_of_projects`, `folders_of_songs`, `copy_project_folders`,
  `drop_project_folders`.
- `library/metadata.py`: `Tag`, `edited_songs` (section 2.5), `set_project_tags` (an edit copy's goes to its song),
  `set_song_tags` (the whole list; `MAX_TAGS = 30`), `tags_of_*` (an edit copy's is its song's),
  `add_song_tags_to_song`,
  `public_tags_of`, `suggestions` (own values in use, then public values the user does not have), `copy_public_tags`,
  `copy_song_tags`, `copy_project_tags`, `add_project_tags_to_song`, `_forget_unused` (runs after every set: deletes the
  owner's values no item uses).
- `api/folders.py` (`/folders`) and `api/metadata.py` (`/metadata`), both in `USER_ROUTERS`. The routes:
  [`documentation/services/backend/endpoints.md`](../../../documentation/services/backend/endpoints.md) section 7.1.1.
- `ProjectRow` and `SongRow` / `SongDetail` carry `folders` and `tags` (one query each for a whole list:
  `_organized` in `api/projects.py`).
- `pull.private_song_for`: a song made, or linked now, gets the public song's tags; a song already linked keeps the
  user's metadata.

## 3.3 Frontend

- `api/folders.ts`, `api/metadata.ts`; `folders` and `tags` on `ProjectRow`, `SongRow`, `SongDetail`.
- `components/folders/`: `listView.ts` + `ViewPills.tsx` (the pills, `?view=` then `localStorage`
  `aitu.projects.view` / `aitu.library.view`, else `all`), `folderTree.ts` (`treeLines`, `inside`, `pathOf`, `reach`,
  `folderCount`), `useFolderTree.tsx` (state, open folders in `aitu.folders.open.<area>`, the folder menu and dialogs,
  drag and drop), `MoveFolderDialog.tsx`, `FolderLeading.tsx` (+ `TriangleRoom`), `FolderChecklist.tsx`
  (+ `FoldersDialog`), `listFilter.ts` + `FilterBar.tsx`, `tagWords.ts` (Film, TV show, Video game, Advert),
  `InfoDialog.tsx`.
- `ui/ListRow.tsx`: `indent`, `rowProps`, `INDENT_STEP = 28`, the outline of `[data-drop-over]`.
  `ui/DataTable.tsx`: `rowProps(row)`.
- `ProjectsPage.tsx`: the pills, **New folder**, the tree (`role=tree`, `treeitem` with `aria-expanded`), the Filter,
  `⋯` **Folders…** and **Info**. `SongsPage.tsx`: the same, the tree drawn as the table's rows (no sort in Folders,
  rows per page 200), a `⋯` column (**Info**, **Folders…**; a folder row has the folder's menu there).
  `SongPage.tsx`: the info button in the header. `FramesSheetPage.tsx`: the info button after `AiMark` when
  `step.projectId` is given (not in `sheetButtons`).
- Drag and drop is HTML5 (`draggable` rows). The browser sends no click after a drag, so the row's own click does
  not fire. A folder row accepts an item that was not dragged from it, and a folder that is not itself, not its own
  parent's child already, and not one of its ancestors.

# 4. Checks

| Check | Result |
|---|---|
| `tests/test_folders_and_metadata.py` (new, 8 tests; `test_the_metadata_is_the_songs_for_every_version` for section 2.5) | pass |
| `tests/test_rights.py` (13, one new: `test_folders_and_metadata_are_their_owners`) | pass |
| The whole backend suite, on the CPU (the GPU was held by another project) | pass, except `test_transcription_transkun.py::test_it_satisfies_the_engine_protocol` and `::test_a_missing_file_is_a_file_error_not_a_model_error`: the model file is loaded on a CUDA device and the GPU is hidden on the CPU run (`torch.load` without `map_location`). Not from this phase |
| `black`, `flake8` (the two remaining warnings are in untouched files), `mypy` on the new modules | clean |
| `tsc`, `npm run lint`, `npm run build` | clean (the chunk-size warning was there before) |
| `npm run check:folders` (new, 24 steps; 21 run three times, then the 24 after section 2.5) | all ok; nothing left (0 folders, 0 songs, 0 projects, 0 secondary keys; checked on the real database too) |
| `check:projects` (26), `check:library` (30), `check:frames-page`, `check:enhance-dialog` | all ok |
| `scripts/docs/check-links.py` | 437 files, 0 broken links |
| The whole backend suite after section 2.5, on the CPU | 1278 passed, 3 skipped (the two transcription tests passed this time) |

`check:folders` works on two duplicates of Elefants: one stays in My projects, the other is saved to My Library as
"check-folders song" by "check-folders artist". It walks the pills, New folder, New folder inside, New parent folder,
Folders…, a drag onto a folder, a reload, Info (a Film), Filter, Delete (the confirmation's text), My Library's folders
and a drag from one folder to another, the song page's info button (a TV show), Filter, and the sheet's info button on
the project and on the library version, then an edit copy of that version, whose **Info** in My projects shows the
song's TV show and adds a Film that the version's sheet then shows. Its metadata is emptied before its items are deleted, so its secondary keys go
too. Screenshots: [`screenshots/04-3-phase-1/`](screenshots/04-3-phase-1/) (each looked at; two first runs were taken
before the sheet and a dialog had finished drawing, and the check now waits for them).

Two problems found by the check and fixed: the delete message said "the 1 project in it stay" (now "the project in it
stays"); the indentation of an item under a folder was 8 px of text, too little to read, because the item's mark sat
under the folder's triangle (now `TriangleRoom`: the mark is under the folder icon, the title 30 px right of the
folder's name).

# 5. Decisions taken in the phase

All are in plan section 10 (Phase 1 paragraph): six tables; the Filter's options counted on the page; metadata set as
one list; the artist of a project from its link only; the metadata follows Edit, Save to library and Duplicate;
**Info** in the row menus; suggestions only of values in use; **New parent folder** on one folder from the menu (the
route takes several); the Finder's indentation; and, asked by the user after the first walkthrough, the metadata of
the song for every version (point 10, section 2.5).

# 6. Notes for later phases

- **Needed later, at Phase 3 and 4**: branch from `master` after this phase is merged (plan section 4.5). A branch made
  before it refuses the database, which is at `0008`.
- **Needed later, at Phase 4**: a level of the whole sheet writes a new project (plan section 5.8). It must share
  the song's metadata, never have its own (the user's rule, section 2.5). Made with `POST /projects/{id}/duplicate`
  from an edit copy, it is an edit copy of the same version and shares it already. From a project with no song,
  Phase 4 needs a link to the original project that `tags_of_projects` and `set_project_tags` follow (plan section
  5.8).
- A secondary key whose last item is deleted stays in `private_tag_values` until the owner's next change of metadata
  (`_forget_unused`). It is never suggested meanwhile (`suggestions` filters by use).
- The Phase 2 session runs in its worktree (`/home/david/Documents/projects/music/aimpromptu-04-3-phase-2`, branch
  `feat/04-3-phase-2`, plan section 7.4). Whichever phase merges second resolves the small conflicts in plan section
  10, the checklist and the folder's `README.md`.
