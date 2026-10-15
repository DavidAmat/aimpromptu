# From other projects, and the playlists

A reader can make a new project out of passages of other projects, keep a project as several
**parts** (the sub-songs of an **integrated playlist**), and list songs of their library in a
**songs playlist** (implementation 02, plan sections 10.4 and 14, Phase 10; the app context's "From
Other Projects" and "Playlists"). What the backend writes is in
[`../backend/editing.md`](../backend/editing.md); the routes in
[`endpoints.md`](../../documentation/services/backend/endpoints.md) section 7.

## 1. From other projects

**New project → From other projects** opens `/projects/compose`, in the app context's three moves:

1. **Choose a project**: a list of every project with notes, of Projects and of My library (a
   version is named "<song> (<version>)"), with a filter.
2. Its piano sheet opens **read only**. Mark a stretch above the staves and press **Add this
   stretch** in the *Frames* panel, or press **Add the whole sheet**. A project of several parts
   offers a **Part** choice above it. A project with no piano sheet yet can only be added whole.
3. The passages are listed on the left in the order they will play, each with its stretch or
   "Whole". Between two passages a choice says how they join: **Sequential** (the second plays on
   from the first, in the same part) or **Subheader** (it starts a new part, with the **Title**
   typed there, or its own title). A passage is dragged to another place, or moved and removed from
   its `⋯`. **+** adds another.

**Save as song** or **Save as integrated playlist** asks a title and makes the project in Projects,
which opens on its Sheet step. The passages are **copies**: their notes, their marks (with the key,
the clefs and the speed each had) and their audio (ranges of the stored files, no byte copied);
nothing of the sources changes. The two differ only in what the project is: an integrated playlist
plays as sub-songs in Play mode (Phase 11). Until it is saved, the list is kept in this browser, so
leaving the page or reloading it loses nothing.

## 2. The parts of a project

A project of more than one part shows its **parts** on the left of its Sheet step: each named by its
subheader ("Part 2" when it has none) with its length, the one on show shaded. A click opens that
part; the step tabs then follow it (every step works on one part). The sheet of a part is titled by
its subheader.

| Action | Where | What it does |
|---|---|---|
| **Rename** | The part's `⋯` | Its subheader |
| **Move up**, **Move down**, drag | The part's `⋯`, its handle | Another place in the order |
| **Join with “…”** | The part's `⋯` | One part with the one before it, played without a break |
| **Start a new part here** | The range toolbox's title bar, on a marked stretch | What follows the stretch's start becomes a new part right after this one (the sheet's unsaved edits are saved with it) |

A split works on any project, so a song of one part can be split too; the panel then appears. Joins
and splits are not on the sheet's undo: a split is taken back by a join, and the other way round.
**Save to library** saves every part; a version of the library shows the parts read only.

## 3. Songs playlists

**My library → Playlists** lists the songs playlists and the integrated playlists of the library (a
row of an integrated one opens its song). **New playlist** asks a title.

A songs playlist lists songs of the library in the order they play, each on a **version** and, when
chosen, a **stretch** of it ("0:12 – 1:05", else "Whole"). Nothing of a song can be changed here,
only chosen: a row opens the version (read only); its `⋯` has **Use “<version>”** for each other
version, **The whole song** when it has a stretch, **Move up**, **Move down** and **Remove from the
playlist**; a row is dragged to another place. **Add a song** puts a song of the library at the end
on its first version. The header's `⋯` renames or deletes the playlist (its songs stay).

Three more ways in:

- **Songs**: tick songs, then **Make a playlist of N** (the app context's playlist made from a
  selection), each on its first version.
- A song's version, `⋯` → **Add to a playlist**: the whole version, into a playlist or a new one.
- A version's read-only sheet: mark a stretch, then **Add to a playlist** in the *Frames* panel.

A version deleted from the library leaves its rows on the song's first version; a song deleted takes
its rows with it. **Play** comes with Play mode (Phase 11).

## Where to look deeper

- The backend: [`../backend/editing.md`](../backend/editing.md),
  [`editing-and-compose.md`](../../documentation/services/backend/editing-and-compose.md) section 4,
  [`endpoints.md`](../../documentation/services/backend/endpoints.md) sections 7 and 7.2
- The storage of parts and playlists: [`../07-database.md`](../07-database.md)
- The code: [`components.md`](../../documentation/services/frontend/components.md)
- The steps of a project: [projects.md](projects.md); My library:
  [`../music-library/private-library.md`](../music-library/private-library.md)
