# Folders, the pills and the metadata

The lists of **My projects** (the Projects page, the Personal Vault) and of **My library** (the Songs of the
Private Library) share one way to group and find their items: **folders**, three **pills** (**Folders**, **All**,
**Filter**), and **metadata** (a primary key and a secondary key per row) to filter by. The info dialog sets the
metadata and the folders. Built in implementation 04-3, Phase 1 (2026-10-29; the brief is
`context/implementations/04-app-enhancements/04-3-prompt.md`). The code is in `aitu-frontend/src/components/folders/`
(the file list is in [components.md](../../documentation/services/frontend/components.md) section 8.1).

## 1. Two trees, one way of working

- **Folders** are rows with their own id and the id of their parent folder (`NULL` at the top). Each folder belongs to
  one **area**: `projects` for My projects, or `library` for My library. The two trees do not know each other.
- An item points at folder ids, never at a path. Moving a folder, or making a **New parent folder** on top of it,
  changes that folder's row only.
- An item can be in several folders. A project can be in several folders of My projects; a song can be in several
  folders of My library.
- Deleting a folder deletes the folders inside it and the links to them. It never deletes a project or a song.

## 2. The pills

Three pills sit above the list, on the Projects page and on My library's Songs:

| Pill | What it shows |
|---|---|
| **Folders** | The tree of the folders (section 3), then the items in no folder |
| **All** | The flat list, unchanged. The first visit opens it |
| **Filter** | The flat list with the dropdowns of section 4 above it |

The pill chosen is in the address (`?view=folders`, `?view=all`, `?view=filter`), and in the browser, under
`aitu.projects.view` for My projects. An address with no `view` opens the browser's last choice, else **All**
(`listView.ts`, `ViewPills.tsx`).

## 3. The Folders view

- The folders of the top level come first, by name. Each has a triangle that opens and closes it. An open folder shows
  its folders and its items one step further in. An item with no triangle leaves an empty room where the triangle
  would be, so its mark sits under the icons of its sibling folders. After the folders, the items in no folder.
- An item in two folders is drawn under each of them.
- **New folder** sits beside the pills and makes a folder at the top.
- A folder's `⋯` menu has **New folder inside**, **Rename**, **Move to…**, **New parent folder** (a folder made where this
  one is, with this one inside it) and **Delete**. **Move to…** offers the top or any folder that is not this one or
  inside it. **Delete** asks, says how many folders go, and says that no item is deleted.
- Drag and drop: a row dragged onto a folder moves into it, out of the folder it was dragged from (from the top level it
  is added to the folder). A folder dragged onto a folder moves inside it. A drag never opens the row.
- The open folders are kept in the browser, one list per tree: `aitu.folders.open.projects` and
  `aitu.folders.open.library`. They are not in the database.

**Folders…** in a row's `⋯` menu opens the tree with a checkbox per folder. Ticking a folder adds the item to it;
unticking takes it out. The item keeps its other folders.

## 4. The Filter

The **Filter** pill shows one dropdown for the **Artist**, then one for each primary key the items use (**Film**,
**TV show**, **Video game**, **Advert**). Each dropdown offers the secondary keys (section 5) that the items have, with
the count of items that have each one. The counts follow the other choices made: an artist and a film together leave
the items that have both. The choices are kept in the address (`?artist=…&films=…`), so a filtered list can be sent or
bookmarked.

An edit copy in My projects has the artist of the song it edits, because it has no artist of its own. Other projects
have none.

## 5. The metadata

- **Primary keys** are a fixed list: **Film**, **TV show**, **Video game**, **Advert**. They are the categories of
  `tag_categories` (the public list of the Public Library).
- **Secondary keys** are the values under a primary key, such as "The Lord of the Rings" under **Film**. A user's own
  values are kept apart (`private_tag_values`), so the Public Library never shows them. The secondary-key field
  suggests the user's own values in use first, then the Public Library's.
- A value typed in other letters is the same secondary key as the one already there.
- An item has up to 30 rows of metadata. A row is one primary key with one secondary key.
- The metadata belongs to the **song**, never to one version. Every version of a song, and every edit copy of one,
  shows the same rows. A change from any of them changes them for all. This is why a project's metadata lives on its
  song when the project is a version of My library or an edit copy of one (section 6).

## 6. The info dialog

The **info** dialog (`InfoDialog.tsx`) has the same layout in three places: the **Info** of a row's `⋯` menu on the
Projects page, the song page of My library, and the info button of the Sheet step (the "i" beside
the title and the AI mark). It shows the title and the artist (read only here, they are changed in their own dialogs),
the metadata rows, and the folders the item is in. What it changes depends on what the sheet belongs to:

| The sheet belongs to | What the dialog reads and changes | Folders it changes |
|---|---|---|
| A project of My projects with no song | The project's own metadata | The folders of My projects ("Folders of My projects") |
| A version of My library, or an edit copy of one in My projects | The **song's** metadata: the line "For the whole song: every version has it" | The folders of My library ("Folders of My Library"). The edit copy's own place in My projects is set with **Folders…** |
| A version of the Public Library (or of a library shared with the user) | The public song's tags, read only | None |

The API is `GET /metadata/info/{projectId}`, which says which of these the sheet is (`kind`: `project`, `song`,
`public`, or `none` for a request's copy), and whether the user may change it (`editable`). The routes that change it
are `PUT /metadata/projects/{id}`, `PUT /metadata/songs/{id}`, `PUT /folders/projects/{id}` and
`PUT /folders/songs/{id}`. The full list is in [endpoints.md](../../documentation/services/backend/endpoints.md) section 7.1.1.

The info button is not a tool of the sheet. It is not in the floating toolbox. Play mode, a passage and **From other
projects** have no info button, because they have no song or project of their own to show.

## 7. Where it is kept

| What | Table |
|---|---|
| The folders, one tree per user and area | `folders` (`owner_id`, `area`, `parent_id`, `name`) |
| The projects in a folder | `folder_projects` |
| The songs in a folder | `folder_songs` |
| The user's own secondary keys | `private_tag_values` |
| The metadata of a project of My projects | `project_tags` |
| The metadata of a song of My library | `private_song_tags` |

The schema is in [07-database.md](../07-database.md) and [paths-and-data.md](../../documentation/services/backend/paths-and-data.md)
(section 6). None of it is in `project.json`: the bundle does not hold folders or metadata.

The rules of the routes: `404` for another user's folder, project or song, and for a folder of the other area; `403`
for a project of the Private Library (it changes through its song); `409` for a folder name its parent already has
(ignoring case) and for a move into the folder itself or into a folder inside it; `422` for an empty name or an unknown
primary key.

## 8. What the other pages say about it

- **Save to library** adds a project's metadata to the song it is saved as, and the project leaves the folders of My
  projects (the two trees are independent). See [music-library/private-library.md](../music-library/private-library.md)
  section 5.1.
- **Add to my library** gives a song the public song's tags.
- The project list (`GET /projects`) carries each row's `folders` and `tags`; the library's song list carries the same
  for songs. The page works out the Filter from them.

## Where to look deeper

- The components and their files: [components.md](../../documentation/services/frontend/components.md) section 8.1
- The routes: [endpoints.md](../../documentation/services/backend/endpoints.md) section 7.1.1
- The tables: [07-database.md](../07-database.md), [paths-and-data.md](../../documentation/services/backend/paths-and-data.md)
- The Projects page and the steps of a project: [projects.md](projects.md)
- My library, the songs and the versions: [music-library/private-library.md](../music-library/private-library.md)
- The plan of the feature: [`implementations/04-app-enhancements/04-3-plan.md`](../implementations/04-app-enhancements/04-3-plan.md) section 4
