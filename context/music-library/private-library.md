# The Private Library

The Private Library is layer 2 of the app context: each user's own library of finished work, the
"main branch" that work in progress (the Personal Vault, layer 1) is saved into. Nobody else reads
it, unless the owner shares it (Phase 14). Built in implementation 02, Phase 6. The pages are
**My library → Songs** and **Artists** in the sidebar.

## 1. What it holds

The user's own ontology, in the `private` scope of the music library's tables, each row with its
owner:

- **Artists**, each with one or more **artist names**, one of them the default. "The Jackson 5" and
  "Jackson Five" are two names of one artist; two artists can be **merged** into one (every name of
  one becomes a name of the other), as the app context asks.
- **Songs**: a title, and the artist names it is credited to (a song points at an artist *name*,
  which points at its artist). Two songs may share a title when their artists differ ("Heaven" of
  Bryan Adams and of Avicii).
- **Versions** (`private_versions`): a free name ("original", "easy", "acoustic"), unique in its
  song ignoring case, pointing at one project of the Private Library
  (`users/<id>/library/<projectId>/`).

Names are compared ignoring case and repeated spaces, so "aitana" finds "Aitana".

## 2. Save to library

A project of Projects shows **Save to library** once its Sheet step is ready (the piano sheet is
saved and current). The dialog asks three things, now and not before (app context, "From Source"):
**Artist**, **Song** (each offers what the library has, and takes a new name as typed) and
**Version name** ("original" at first). Saving:

1. **moves** the project from the vault to the library (the same ids, the same bundle);
2. **writes its audio again with only the ranges in use** (decision Q-3): each audio file the
   timeline uses only in part becomes a new FLAC file of just its kept ranges, joined with the 5 ms
   fade of a cut; the cuts disappear, nothing the user hears or reads moves (the notes are in the
   time of the joined audio, and the audio revision does not change), and the old file is deleted
   once no project uses it. A part of several files keeps its files, their order and their names;
3. **deletes the temporary files**: a video and its frames, the open edit sessions, and the history
   of the parts (its earlier states point at the audio just written again);
4. files the project under the song (found by title and artist, or made) as a new version, and
   opens the song.

Measured on a copy of Elefants (two cuts): 23,335 kept frames (233 s) before and after, the notes
unchanged to the millisecond (`npm run check:library`).

## 3. A version is changed through a copy

A version opens **read only**: every step shows what it holds (the sheet draws, plays and prints;
the roll plays; the waveform plays), and nothing on it changes anything. The header goes back to the
song, and its one action is **Edit**.

**Edit** makes a copy in Projects that points at the version (`basedOn`; no audio bytes copied) and
opens it. The version itself does not change. While a copy is open, the song says **Editing** beside
the version, Projects says **Editing** on the copy, and **Edit** opens that same copy again. The copy
is an ordinary project; its **Save to library** offers two things:

- **Replace “<version>”**: the version gets the copy's content (the library project keeps its id
  and its parts' ids, so links to it still work), its previous content goes to its **history**, and
  the copy is deleted;
- **New version**: the copy becomes another version of the same song (or of another song).

**Discard changes** (the copy's `⋯`, or Delete on Projects) deletes the copy; the version stays as
it was.

## 4. The history of a version

Each **Replace** keeps the state it replaced: `.database/history/<projectId>/v<N>/` holds its
`project.json` and its parts' files, and `audio_refs` keeps the audio those name. **History** on a
version lists the earlier states, newest first, each with **Restore**. A restore keeps the state it
replaces too, so nothing is lost by trying one.

## 5. The pages

| Page | Address | What is on it |
|---|---|---|
| Songs | `/library/songs` | A table (title, artist, versions, changed) with a filter by title or artist; a row opens the song |
| A song | `/library/songs/:id` | The title, its artists (each a link), and its versions. A version row opens it read only; its `⋯`: Open, Edit, Duplicate, Export, Rename, History, Delete. The header's `⋯`: Rename song, Artists, Delete song |
| Artists | `/library/artists` | A table (name, other names, songs) with a filter |
| An artist | `/library/artists/:id` | Its names (Make default, Rename, Remove; **Add a name**) and its songs. The header's `⋯`: Merge into another artist, Delete artist (once it has no song) |

**Duplicate** of a version makes an independent project in Projects; **Export** saves its `.aitu`
file. **Search** (`⌘K`) finds songs by title and artist, and projects by title.

## 6. Who can do what

Only the owner reads and changes their library: another user gets `404` for its songs, artists and
projects (the master user too, [08-security.md](../08-security.md)). The owner never writes a
library project in place: the step routes answer `403`, and the changes go through **Edit** and
**Save to library**, which check the owner themselves.

## 7. Not built yet

| Thing | When |
|---|---|
| Playlists of My library | Phase 10 |
| **Shared** (a library another user shares with you) | Phase 14 |
| Suggestions from the Public Library in the dialog, and **Add to my library** from it | Phase 13 |
| Play mode for a version (**Play**) | Phase 11 |
| Offline downloads per project | Q-7 (raised in Phase 6) |

The 30 songs the migration of Phase 3 put in the master user's library were saved before Phase 6:
their cuts are still ranges, and their audio is written again the first time each is replaced.

## Where to look deeper

- The routes: [`endpoints.md`](../../documentation/services/backend/endpoints.md) §7 and §7.1
- The folders and tables: [`paths-and-data.md`](../../documentation/services/backend/paths-and-data.md)
- The steps of a project: [frontend/projects.md](../frontend/projects.md)
- The plan: [implementations/02-private-web-app/02-plan.md](../implementations/02-private-web-app/02-plan.md)
  sections 8.5, 10.2, 10.6, 15.1 and 15.2
- The code: `aitu-backend/src/aitu_backend/library/` (`rows.py`, `flow.py`),
  `audio/compact.py`, `api/library.py`; `aitu-frontend/src/pages/library/`,
  `pages/piece/SaveToLibraryDialog.tsx`
