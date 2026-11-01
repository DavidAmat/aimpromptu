# 05, Phase 18: The libraries, playlists, requests and the Public Library (report)

Wave A. Plan section 6, Phase 18; checklist 18.1 and 18.2.

## Docs changed

- `context/music-library/private-library.md`: the **Edit** menu label is **Continue editing** while an edit copy is open (the code, `SongPage.tsx`); the Search line now says that the Public Library's suggestions come under the songs and projects (Phase 13); section 7 renamed "Later phases, and what is still open" (its table lists done phases); the removed `sheet-library.mjs` script is named without a path, so it is history, not a file to find.
- `context/frontend/playlists.md` (section 3, the songs playlists only; sections 1 and 2 are Phase 17's): the playlist's `⋯` menu is **Rename**, **Publish**, **Delete playlist** (the code, `PlaylistPage.tsx`), with a link to `requests.md`.
- `context/music-library/README.md`, `ontology.md`, `popularity.md`, `requests.md`, `genres.md`, `regional-sources.md`, `reconciliation.md`: no change. Their names and links were checked (see Not checked).

## What was stale

- Edit label: the song's version menu says **Continue editing** for a copy that is open; the page said only **Edit**. Fixed.
- Search: the dialog also lists the Public Library's matching songs and artists (Phase 13). The page did not say so. Fixed.
- The `sheet-library.mjs` script (removed in 03 Phase 10) was written as a path, which the name check flags. Now plain text.
- The `## 7. Not built yet` heading sat over rows that say "done". Renamed.
- The rest of `private-library.md`, `requests.md` and `ontology.md` matched the code: the routes (`/library/...`, `/public/...`, `/requests/...`, `/shares`, `/shared/...`, `/playlists/...`), the labels (**Make a playlist of N**, **Add a name**, **Make default**, **Merge into another artist**, **Propose this song**, **Change and send again**, **Finish your review**, **Send decision**), the tables (`private_versions`, `playlists`, `playlist_items`, `folders`, `folder_songs`, `private_tag_values`, `private_song_tags`, `tag_categories`), the folder areas (`projects`, `library`), the status names and the refusal rules (`requests.py`: `_plan_user_version`, `_refuse_known_song`, `_plan_metadata`, `_status`, `simple_name` at 24 characters, `MAX_GENRES` = 2). The popularity weights (`week_power` 8, `reference` 100) match the doc.

## Code and docs that disagree in a way that looks like a bug (for the user)

- None found. Code changed since 2026-10-19 in this scope (`library/folders.py`, `library/metadata.py`, `library/flow.py`, `library/pull.py`, `api/library.py`, `pages/library/SongsPage.tsx`, `SongPage.tsx`, `pages/requests/Conversation.tsx`) is covered by the 04-3 pages and the `components.md` section 1.1; nothing contradicts `requests.md`.

## New terms for the glossary (Phase 20)

- **Continue editing**: the version menu's label while an edit copy is open (the only label that changes).
- **Other versions**: the user versions of a public song, grouped by user (already in `ontology.md`).
- **Changes asked**, **Partly accepted**: the request statuses (`requests.md` section 5).

## Not checked

- `genres.md`, `regional-sources.md`, `reconciliation.md`: names and links only. Their modules changed no later than 2026-10-19 (the commit of the page). The counts (songs, weeks, regions) were not recomputed against the download.
- `ontology.md` section 3 counts (9,044 songs with a year and the others): not recomputed.
- `requests.md`: the refusal rules and the statuses were checked by name in `requests.py`, not line by line; the review layout was checked by its labels.
- `reconciliation.md` names: `import_note`, `song_decade`, `album_decade` are tables of the download (`library.sqlite`), not of the app; `/singles/bee-gees/stayin-alive` is a source path. They are correct as written and are reported as missing only because the name check looks at the app's code.
- Phase 1 counts in the inventory were not updated (they are the baseline); only the State column changed.

## Pending edits for shared files

1. **`documentation/services/frontend/components.md`**: in section 1 (Routes and shell), after the table of `### 1.2 The Public Library (implementation 02, Phase 13)` and before `## 2. The page of a project`, insert:

   ```
   ### 1.3 Shared libraries and requests (implementation 02, Phase 14)

   | File | Role |
   |---|---|
   | `pages/library/SharedPage.tsx` | **Shared** (`/library/shared`, `?from=<owner id>` picks one library): the songs of the libraries other users share, read only; **Whose library** and **Library of** when there are several |
   | `pages/library/SharedSongPage.tsx` | One song of a shared library (`/library/shared/songs/:id`): its versions, each with **Open** (read only), **Play**, **Add to my library** (`POST /shared/songs/{id}/pull`) |
   | `layout/ShareDialog.tsx` | **Share my library**: a switch per user (`PUT` and `DELETE /shares/{userId}`); opened from the user menu and from Shared |
   | `pages/requests/RequestsPage.tsx` | **Requests** (`/requests`, the author's list) and **Review** (`/admin/requests`, the master user's, with **All**) |
   | `pages/requests/RequestPage.tsx` | One request, laid out like a pull request: the title and status, then **Conversation** (`/requests/:id`) and **Sheet** (`/requests/:id/sheet`); the same page for the author and the review |
   | `pages/requests/Conversation.tsx` | The timeline: the request as sent, the comments (on a stretch of the sheet, with replies), the reviews and the events; **Comment on this stretch** writes `POST /requests/{id}/comments` |
   | `pages/requests/RequestSheet.tsx` | **Sheet**: the whole proposed piano sheet, read only, with its player; **Proposed** and **Now** when the Public Library has a version to replace; **Mark a stretch** |
   | `pages/requests/RequestItems.tsx` | What each item proposes (a new artist or song, the metadata changed in bold, a piano sheet, a playlist) |
   | `pages/requests/PublishDialog.tsx` | **Publish** a version or a playlist: the public song (**Propose this song** when none), the version name, **Send request** |
   | `pages/requests/SuggestChangeDialog.tsx` | **Suggest a change** (a public song or artist) and **Propose a song** |
   | `pages/requests/SmallRequestDialogs.tsx` | **Ask for a fixed version**, and the short dialogs of the Change and send again flow |
   | `pages/requests/ReviewDialog.tsx` | **Finish your review**: **Accept** (the name can change), **Ask for a change**, **Refuse**; **Send decision** |
   | `pages/requests/SongFieldsForm.tsx`, `songDraft.ts`, `items.ts`, `words.ts` | The song fields of a request and their state; the names of kinds, statuses and items on screen; the simple form of a version name |

2. **`documentation/services/backend/endpoints.md`**: no change. Section 7.1 to 7.5 match the route decorators of `api/library.py`, `public.py`, `requests.py`, `playlists.py`, `shares.py`.

3. **`context/00-index.md`**, **`documentation/services/README.md`**: no change (no new file in this phase).

## Left for later phases

- None in this scope. The `playlists.md` sections 1 and 2 (From other projects, the parts) stay with Phase 17.
- `private-library.md` section 2 (**Save to library**) and the Save to library dialog are Phase 14's check: the phase names them in its shared files; not touched here.

## Checks run

- `python3 scripts/docs/check-links.py`: 513 files, 0 broken links.
- `python3 scripts/docs/check-names.py` on the 9 files of the scope: 4 missing, all explained above (`reconciliation.md`: the download's table names and a source path). The `sheet-library.mjs` path is no longer flagged.
