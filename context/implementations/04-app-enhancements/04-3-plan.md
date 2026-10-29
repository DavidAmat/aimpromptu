# 04-3 · Plan: folders and metadata, and the whole song simplification by levels

Status: written 2026-10-29, from the brief [`04-3-prompt.md`](04-3-prompt.md); not started. **This is the living
plan**: the agents update it when a phase changes direction (section 10 lists the changes, with the reason).

Audience: the AI agents that build it on the Ubuntu machine, and the user, who checks each phase in the browser at
`http://ubuntu:5173` from the Mac.

# 1. How to read and report

## 1.1 Read first

Every agent of this plan reads, before any work:

1. This file.
2. [`04-3-prompt.md`](04-3-prompt.md): the brief in the user's own words. When the brief and this plan differ, the
   brief wins, unless section 10 records a later decision of the user.
3. [`context/guidelines/guidelines-implementation-plan.md`](../../guidelines/guidelines-implementation-plan.md): how
   to report to the user (the walkthrough with SUMMARY, CRITICAL ISSUES, DECISIONS, HUMAN INTERVENTION and HAND OFF).
4. [`context/guidelines/guidelines-communication-with-user.md`](../../guidelines/guidelines-communication-with-user.md):
   how to write for the user (plain English, the user's terms, the reason before the action, numbered headings, no
   em dashes, no phrasal verbs).
5. [`04-context.md`](04-context.md) and [`../03-apply-poc-research/03-context.md`](../03-apply-poc-research/03-context.md):
   how the sheet, the AI runs and the Enhance with AI dialog work today, and the decisions that bind.
6. The report of the previous phase of this plan (`04-3-implementation-phase-N.md`), when there is one.

## 1.2 How each phase reports

Each phase ends with two texts, as `guidelines-implementation-plan.md` asks:

- **The phase report** `04-3-implementation-phase-N.md` in this folder. It is technical and is read by agents only.
  It holds the study, what was built, the measures, the checks, and the notes "needed later, at Phase M".
- **The walkthrough** in the chat, for the user. It follows the structure of `guidelines-implementation-plan.md`
  (SUMMARY, then CRITICAL ISSUES, DECISIONS and HUMAN INTERVENTION only when they exist, then HAND OFF only when the
  phase is fully done) and the writing rules of `guidelines-communication-with-user.md`. HUMAN INTERVENTION holds only
  what the user must do now. HAND OFF is one line, the prompt for the next agent, and nothing else.
- Every link to a page for the user (a gallery, a screenshot) is an `http://ubuntu:<port>/...` address served from
  Ubuntu (`python3 -m http.server 8099 --bind 0.0.0.0` in the folder), checked with `curl` first. The user works on
  the Mac and cannot open a file path of the Ubuntu machine.

## 1.3 The hand-off prompts

Each phase has its start prompt in section 8. They all have the same form, so that every new agent reads the two
guideline files and knows how to talk to the user:

> You are working on an implementation plan. Read @context/implementations/04-app-enhancements/04-3-plan.md,
> @context/implementations/04-app-enhancements/04-3-prompt.md, @context/guidelines/guidelines-implementation-plan.md,
> @context/guidelines/guidelines-communication-with-user.md and @context/implementations/04-app-enhancements/04-3-implementation-phase-<N-1>.md.
> Start Phase N.

## 1.4 Terms

The plan uses the user's words. When the code has another name, the code name is given once here and only used when
the plan points at code.

| The user's word | What it is | The code's name today |
|---|---|---|
| **My projects** | The page `http://ubuntu:5173/projects`: the projects of the Personal Vault | `projects` rows with `layer = "vault"` |
| **My Library** | The page `http://ubuntu:5173/library/songs`: the user's private songs and their versions | `songs` rows with `scope = "private"`, `private_versions` |
| **public library** | The songs shared with everyone. It gets **no folders** | `songs` rows with `scope = "public"` |
| **pills** | The three choices at the top of My projects and My Library: **Folders**, **All**, **Filter** | (new) |
| **folder**, **parent folder** | A named group of songs or projects, inside another folder or at the top | (new) `folders` |
| **metadata** | The information of a song that the user adds to group and filter: a **primary key** and a **secondary key** | tag category and tag value |
| **primary key** | The kind of metadata: Film, TV show, Video game, Advert (the same list as the public library) | `tag_categories`: `films`, `tv_shows`, `video_games`, `adverts` |
| **secondary key** | The value inside a primary key, such as "The Lord of the Rings" | `tag_values` (public), new private values |
| **info button** | The usual "i" icon on the sheet page and on the song page of My Library that opens the metadata | (new) |
| **Whole Song simplification** | Making a hard sheet (often a machine transcription) easy to play, at a chosen level | (new run kind) |
| **level**: **easy**, **medium**, **hard**, **super hard** | How hard the new sheet is to play. Super hard comes later and is not in this plan | (new) |
| **left-hand companion** | What the left hand plays under the melody (bass notes, chords, arpeggios) | |
| **pattern** | A way of playing that repeats, named in the gallery of patterns (for example, a low note and then a chord) | |
| **gallery of patterns** | The HTML page of Phase 2: snapshots of Chopin passages, one tab per hand, filtered by level | |
| **decoration note** | A very short note before a main note (the code calls it a grace note) | `Note.grace`, `find_graces` |

Music terms stay in Spanish as the user writes them: negra, corchea, semicorchea, fusa, blanca, redonda, octava. The
user names notes in solfège (Do, Re, Mi, Fa, Sol, La, Si); the sheet text and the code use letters (C, D, E, F, G, A,
B). Both appear in this plan: "Fa3-La3-Do4" is "F3+A3+C4".

# 2. Context

Implementation 04 (done on 2026-10-28) polished the sheet page and the AI's sheet: the decoration-note rule, prompt
version 6 with the rules of simplicity, and the **Enhance with AI** dialog with **Simplify** for one hand or both.
Using the app after that, the user found two new needs.

The first need is about order. My projects and My Library show every song in one flat list. When the user works on
several topics (the songs of one film, the songs of one project), there is no way to group them, and a playlist is
not the right tool for that. The user wants folders that nest as in the macOS Finder list view, and metadata (a
primary key and a secondary key, as the public library has) to filter by.

The second need is about the sheet itself. Many sheets come from audio transcriptions that a machine played, not a
human. The image [`images/whole-song-simplification.png`](images/whole-song-simplification.png) shows a typical case:
chords in the left hand that span more than one octave, octavas that the recording does not have, a left hand that
jumps on every note, and a right hand whose melody is hidden among chords and decoration notes. The image
[`images/99-red-ballons-issue.png`](images/99-red-ballons-issue.png) shows the worst case, from 99 Red Balloons: the
left hand plays three octaves at once, while the right hand plays nothing except a very high chord that adds nothing
to the melody.

Today's **Simplify** (implementation 04, Phase 4) cannot fix this. It was designed to make small corrections: it
changes at most a tenth of the notes of a batch, keeps every note at its place, never moves a note to the other hand,
and never writes a note at a time where its hand plays nothing. Those limits are correct for the rules of simplicity,
but a sheet like 99 Red Balloons needs a new left-hand companion and a new right hand. That is a different kind of AI
run, with a different prompt for each level.

The research already studied this kind of work. Research Phase 11 (folder
`/home/david/Documents/projects/music/poc-aitu-research`, `experiments/E11-difficulty-enrichment/README.md`) built a
five-level ladder (level 5 was Ballade No. 4), and the user's reviews of it gave three rules that this plan keeps:

- Difficulty is mostly **hand motion**, not the number of notes: a hand that stays in one position, or that repeats
  one shape, plays many notes easily.
- The **melody comes first**: the top note of the right hand is kept at its time, also when a simpler hand position
  would drop it.
- A simple right-hand line is kept whole; dropping a note of it needs a reason.

The research also graded the 32 transcriptions of the library with its difficulty model, and 99 Luftballons was the
hardest (grade 8.8 of 10). This is why it is the test song of this plan.

The research worked with compases (its format F1-bars). The app has no compases since implementation 03, so the
level runs must place their patterns on the time of the recording (section 5.3).

# 3. Objective

At the end of this plan:

1. My projects and My Library have three pills: **Folders**, **All** (the list of today) and **Filter**.
2. In **Folders**, the user creates folders, folders inside folders, and parent folders on top of existing folders,
   and puts a song or a project in one folder or in several. The list opens and closes folders as the Finder list view
   does, with the items of a folder indented under it.
3. In **Filter**, the user filters by artist and by each primary key and its secondary keys.
4. The user adds and changes the metadata of a song or a project with the **info button**, on the sheet page and on
   the song page of My Library.
5. A **gallery of patterns** from Chopin (Phase 2), with a tab for the right hand and a tab for the left hand, a name
   and a one-line explanation for each pattern, and pills to filter by level, approved by the user.
6. One prompt per level (easy, medium, hard), written from the approved gallery and approved by the user on passages
   of 99 Red Balloons.
7. **Enhance with AI** offers the levels: on a selected range (both hands, the right hand or the left hand) and on the
   whole sheet (the whole sheet, the right hand only, the left hand only).
8. 99 Red Balloons has an easy, a medium and a hard version that the user approved in the browser.

Not in this plan: the super hard level (the code keeps the list of levels open so that it can be added later); a
piano sound that plays the sheet (playback stays the recording, see section 9); folders in the public library.

# 4. Design: folders, the pills and the metadata (Phase 1)

## 4.1 What exists today

The code study of this plan found the following, so that Phase 1 starts from facts (Phase 1 confirms them):

- **My projects** (`aitu-frontend/src/pages/ProjectsPage.tsx`) is a list of `ListRow` rows (not a table) loaded from
  `GET /projects?layer=vault`. It has no search, no filter and no sort. Each row has a `⋯` menu (Open, Duplicate,
  Export, Rename, Play, Open the song, Delete).
- **My Library** (`aitu-frontend/src/pages/library/SongsPage.tsx`) is a `DataTable` (Title, Artist, Versions,
  Changed) loaded from `GET /library/songs`, with sortable columns, a text filter and row checkboxes ("Make a
  playlist of N").
- **Ids**: a project id is a uuid (`String(36)`); a song id is an integer.
- **The public library's metadata** is in `tag_categories` (fixed: `films`, `video_games`, `tv_shows`, `adverts`;
  `TAG_CATEGORIES` in `db/models.py`), `tag_values` (a value inside a category, such as "Shrek", added by request) and
  `song_tags`. The screen labels are in `pages/public/shared.ts` (`tagCategoryLabel`), and the public songs page
  filters with a `FilterChip` grouped by category. The private songs have no metadata today, and **Add to my
  library** (`library/pull.py`) copies no tags.
- **Playlists** (`library/playlists.py`, `api/playlists.py`) are the nearest model of a group of songs, but they are
  ordered lists of versions, not a tree.
- The UI kit (`aitu-frontend/src/ui/`) has `Segmented`, `Pill`, `FilterChip`, `DataTable`, `ListRow`, `RowMenu`,
  `ConfirmDialog`. The public library uses `FilterChip` for its filters.
- **Migrations**: Alembic, in `aitu-backend/src/aitu_backend/db/migrations/versions/` (the last is `0007_inferred.py`),
  with `HEAD_REVISION` in `db/database.py`. The running backend reloads on any `src/` change and **migrates the real
  database at once** (`context/07-database.md`, Migrations section).

## 4.2 Folders

The user wants a folder to keep its identity when the tree changes: when a parent folder is created on top of an
existing folder, the songs of that folder must not need any change. This is why a folder is a row with its own id and
the id of its parent folder, and a song points at the folder id, never at a path. The path of a folder is computed
from the parent ids when the page draws the tree, so moving a folder or creating a parent folder changes one row.

- **Table `folders`**: `id` (integer), `owner_id`, `area` (`projects` for My projects, `library` for My Library: two
  independent trees, as the brief asks), `parent_id` (null at the top, the id of the parent folder otherwise), `name`,
  `created_at`. Two folders with the same parent cannot have the same name.
- **Membership**, many to many (a song can be in several folders, as the brief asks): `folder_projects` (folder id,
  project id) for My projects and `folder_songs` (folder id, song id) for My Library. Two tables keep the foreign keys
  exact, because the two ids have different types. Deleting a project or a song deletes its memberships.
- **Operations**: create a folder (at the top or inside a folder); rename it; move it to another parent folder (the
  backend refuses a move into the folder itself or into one of its own children); create a parent folder on top of
  folders that are selected (one new folder, then those folders are moved into it); delete a folder.
- **Deleting a folder** deletes the folder and its child folders, never a song or a project: they stay in **All** and
  in their other folders. The confirmation says how many folders and items it touches.
- **Adding to a folder**: from the `⋯` menu of a row ("Folders…", a dialog with the tree and a checkbox per folder,
  so that one item can be in several folders), and by drag and drop of a row onto a folder in the **Folders** pill
  (this moves the row from the folder where the drag started; dropped from the top level, it adds the row). The study
  checks that the drag does not conflict with the row's own click.
- **Rights**: only the owner sees and changes his folders. The rights table (`tests/test_rights.py`) gets the new
  routes.
- **A project that leaves My projects** (Save to library moves its bundle to My Library with the same ids) loses its
  project folders, because the two trees are independent. The study checks this path and the Edit path (a vault copy
  `based_on` a library version), and writes what it decided in the report.

## 4.3 The pills

- The top of both pages gets three pills: **Folders**, **All**, **Filter**. **All** is the list of today, unchanged.
  The pill chosen is kept in the address (`?view=folders`) and in the browser, so that a reload and the back button
  keep it. The first visit opens **All**.
- **Folders** draws the tree: the folders of the top level first (sorted by name), each with a disclosure triangle;
  an open folder shows its child folders and its items under it, indented one step per level; then the items that are
  in no folder. The open folders are kept in the browser. A **New folder** button sits next to the pills; inside a
  folder's `⋯` menu, **New folder inside**, **Rename**, **Move to…**, **New parent folder**, **Delete**. On My
  Library, the rows keep their columns (Title, Artist, Versions, Changed): only the title cell is indented.
- **Filter** shows the list of **All** with dropdowns above it (`FilterChip`, as the public library): **Artist**, then
  one dropdown per primary key that the user's items use (for example **Film**), whose options are its secondary keys
  with their counts. Choices combine (an artist and a film). The filter is kept in the address. On My projects, the
  artist of a project comes from its link to My Library or from the sheet's titles; the study checks where each
  project has one and writes it in the report.
- Minimal UI (`context/09-coding-conventions.md` and the minimal UI rules of 03): no long texts, the words of the
  brief.

## 4.4 The metadata

The user wants the same primary keys as the public library, with free secondary keys of his own. The public
`tag_values` cannot hold them directly, because a value added there would be shown to every user of the public
library. This is why the private secondary keys need their own rows.

- **Primary keys**: the fixed list of the public library (`tag_categories`: Film, TV show, Video game, Advert). The
  user does not create new primary keys in this plan.
- **Secondary keys**: a new table `private_tag_values` (`owner_id`, `category_id`, `value`), unique per owner and
  category. The secondary-key field suggests both the user's own values and the public values of that primary key
  (so "The Lord of the Rings" is typed once and reused).
- **Links**: `project_tags` (project id, private tag value id) and `private_song_tags` (song id, private tag value
  id). A song or a project can have several metadata rows (for example a Film and a TV show).
- **Add to my library** copies the public song's tags as private metadata (a small change in `library/pull.py`), so a
  song taken from the public library arrives with its film. The study confirms that this does not touch the public
  rows.
- **The info button**:
  - On the sheet page (`FramesSheetPage.tsx`), in the header next to the title and the AI mark. It is about the song,
    not a tool of the sheet, so it is not part of `sheetButtons` and not in the floating toolbox. `SheetStep` does not
    know the project id today, so it is passed down from `SheetTab.tsx` (which has `projectId` and `library`).
  - On the song page of My Library (`pages/library/SongPage.tsx`), in the header next to Play and the song actions.
  - It opens one dialog, the same component in both places: the title and the artist (read only here: they keep their
    own dialogs), the **metadata** (rows of primary key and secondary key, add and remove; the fields of
    `pages/requests/SongFieldsForm.tsx` are the model), and the **folders** (the checkbox tree of section 4.2).
  - On a sheet that is read only for the user (a version of the public library), the dialog shows the metadata and
    does not allow changes. On the sheet of a My Library version, the dialog changes the metadata of the My Library
    song. On the sheet of a project of My projects (also an edit copy of a library version, such as the 99 Red Balloons
    project `c0e39afe`), it changes the project's metadata. The study confirms these three cases and writes them in
    the report.

## 4.5 The database revision

- One revision, `0008_folders_and_metadata.py`, with the five tables; `HEAD_REVISION = "0008"`.
- Before the revision file goes into `src/`: check the full process list (`docker ps` without `head`, `pgrep -fa
  uvicorn`), run `make db-backup`, then add the file. The running backend migrates the real database as soon as the
  file is in `src/`.
- After the merge of Phase 1, a branch made before it refuses the database (the code knows only revision 0007). The
  later phases of this plan therefore branch from `master` after Phase 1 is merged.

# 5. Design: the whole song simplification by levels (Phases 2 to 4)

## 5.1 What the levels are

The brief describes the levels in detail. The prompts of Phase 3 are written from the brief and from the approved
gallery; this section only fixes the main lines, in the brief's words, so that every phase uses the same definition.

The user's principle is that difficulty is a matter of hand movement, of keeping patterns, and of how many notes each
hand plays. Corcheas are not hard when they always follow one pattern: a pianist who knows the chord knows which notes
to play. The easy and medium levels must therefore keep one pattern through the song.

| Level | Right hand | Left hand (left-hand companion) |
|---|---|---|
| **Easy** | The main melody in single notes, no chords. Every note of the melody is kept; a short one may be simplified, never dropped. Accompaniment chords that the transcription put in the right hand move to the left hand, or are dropped when the left hand already plays chords | Simple chords: triads such as Fa-La-Do, major or minor (Fa-Lab-Do), symmetric. A low note and then the chord is allowed (Fa2, then Fa3-La3-Do4). Chords may move in steps when the melody climbs or falls. No hard chords such as Do-Mi-Sol-Sib |
| **Medium** | Single notes in fast passages (corcheas, semicorcheas). On negras, blancas and redondas, two notes (Do3-La3, Do3-Mi3, Do3-Fa3: no octavas, because the right hand must stay fluent); three notes only to land on a long note | As easy, plus rhythms and patterns as in Chopin's Waltzes: a low note then two chords; the same chord repeated; the same chord with one note changing as time passes; octavas in the bass; a broken chord in corcheas up and down (La4, Do5, Mi5, Do5, La4) after a low note. **One pattern kept through most of the song**: the agent identifies what kind of left hand the sheet has and finds its simple equivalent |
| **Hard** | The melody with small pieces of chords that add to it (Ballade No. 4) | The medium patterns with movement: the second chord moves (La4-Do5-Mi5, then Do5-Mi5-La5); irregular lines in corcheas that belong to no well-known chord (Si2-Fa3-Lab3-Re4-Lab3-Fa3). Once the hand is in a position, it does not make big jumps. Symmetric up and down figures (Ballade No. 1, page 12, `images/chopin_passages/ballade1-ex1.png`) |
| **Super hard** | Later, not in this plan. Typical hard classical pieces: fast runs up and down in the left hand with big jumps while the right hand also jumps (the hard parts of Ballade No. 4) | |

Rules for every level, from the brief and from the earlier decisions:

- **Decoration notes** only when it is very clear that the note is an ornament (the rule of implementation 04: one
  or two fusas or shorter before a main note). Otherwise a note gets its own figure, or it is an artifact.
- **Artifacts** of the transcription may go: for example a very high chord far above the melody (the 8va chord of
  `99-red-ballons-issue.png`), which only forces the left hand to cover for the right hand. In that case the right hand
  takes over notes that help the left hand, so that both hands become simple.
- The **melody is never lost**: the research rule "melody first" holds at every level.
- The harmony of the recording is kept: the left-hand companion changes the way the chord is played, not the chord.

## 5.2 Why a new run kind

Today's runs cannot write a level, because each one has limits that a level must break:

| Run (today) | Limit that a level must break |
|---|---|
| **Write it all again** (the whole run) | Changes at most a tenth of the notes of a window; notes keep their frame |
| **Simplify** (left, right, both) | The same limits; hands do not move; the answer is change lines only |
| **A stretch** with the user's words | One window; the check refuses notes at frames where the hand did not play |

A level rewrites the notes of a hand: it adds notes at new times (a bass note then a chord), drops many notes (the
octavas the recording does not have), and moves notes from one hand to the other. The new run (called here a **level
run**) therefore has its own prompt per level, its own answer format, and its own check. It still uses the parts of
implementation 04 that work: batches that see the earlier batches (the auto-regressive Simplify), the earlier passage
most like this one (`like_before`), declared changes, the check with feedback, and storing through
`edits.change_notes` with one step of undo.

## 5.3 The time of the new notes

The sheet has no compases, so a pattern cannot be written as "beat 1, beat 2". A new note of a pattern needs a time
that matches the recording, or the cursor and the lit notes will not match what the user hears. The proposal, which
the Phase 3 study measures on 99 Red Balloons before it is fixed:

- A new note may start only on the **grid of the song**: the onsets of the original notes (both hands), and the
  divisions of the reference figure (`quarterMs`, 600 ms in 99 Red Balloons) placed from the pulse of the algorithm.
- The study measures how stable that grid is in 99 Red Balloons (a machine played it, so the tempo should be steady)
  and in one song played by a human, and writes the decision in the report.

## 5.4 How a level run works

The user asked that the left hand keep one pattern through the song. A run that decides the pattern batch by batch
would change it often. This is why the run has two steps:

1. **The plan of the song** (one request): the AI receives a short summary of the whole song (the harmony of each
   passage as the app computes it from the notes, the passages that repeat as `like_before` finds them, the measures of
   section 5.6) and answers with the sections of the song and, for each section, the pattern of each hand, named as in
   the gallery of patterns (for example "the chorus: a low note then a chord, in negras").
2. **The batches**, one after the other, as Simplify: each batch receives the plan, the batches before it as they were
   written, the earlier passage most like it (a chorus is written the same way each time), and its own notes. It
   answers with the notes of the hand or hands it rewrites (in the F1 frames text), and comment lines that declare the
   pattern used, the melody notes shortened, and the notes dropped as artifacts, each with its reason.

**One hand only** (the right hand only, the left hand only, or a range with one hand): the other hand stays exactly as
it is, as implementation 04 decided for a stretch of one hand. The AI sees it and cannot change it. Accompaniment
chords of the right hand that the easy level would move to a fixed left hand are dropped instead, as the brief allows.

## 5.5 The check of a level run

The check is code, with no AI call. An answer that fails goes back with feedback, as today. The proposal, which Phase
3 measures on the test passages:

- **Melody**: every note of the right hand's top line is still there at its time (or the same name an octave lower,
  where an octava doubled it), unless the answer declares it an artifact and it is far from the melody around it (more
  than an octave above, alone). A shortened melody note keeps its onset.
- **Harmony**: the lowest left-hand note at each change of harmony keeps its name (the research's `check_up` did this
  per compás; here per change of harmony on the grid).
- **Playable at the level**: the number of notes per column and hand, and the span of one hand, within the limits of
  the level (for example easy: one note in the right hand, at most three in the left; medium: two in the right hand on
  short figures, three on long ones; no right-hand octavas below hard). Phase 3 fixes the numbers from the gallery.
- **Hand motion**: the moves of each hand per second (section 5.6) are not above the original, and a lower level does
  not move more than a higher one.
- **Pattern**: the declared pattern is one the level allows, and the notes of the passage follow it.
- **Time**: every new note starts on the grid of section 5.3.

## 5.6 The measures

The research's hand tracker (`poc-aitu-research/src/aitu_research/difficulty/hands.py`: an open hand of one octave
placed over the notes, which moves only when a note is out of reach; moves inside a repeated shape count less) and
its `measures` (notes per second, hand positions, jumps, chords) say how hard a passage is to play. They were written
per compás. Phase 3 ports them to the app's time (per second and per reference figure), so that:

- the gallery of each level shows numbers next to the sheet, and the user sees that easy moves less than medium;
- the check of section 5.5 can use them;
- the plan of the song (section 5.4) receives them.

## 5.7 The Enhance with AI dialog

Today's `EnhanceDialog.tsx` has two tabs: **A stretch** (Both, Right, Left, the user's words) and **The whole song**
(Simplify the left hand, the right hand, both hands; Write it all again). The levels are added to both, as the brief
asks, with the brief's words:

- **With a range selected**: Both, Right, Left (as today), and a level (Easy, Medium, Hard) in place of, or together
  with, the user's words. The study decides with the user whether the words stay possible with a level.
- **With nothing selected**: the whole sheet, the right hand only, the left hand only, and a level (Easy, Medium,
  Hard), next to today's Simplify and Write it all again.
- The cost estimate shows before the run, as today. The page says "AI", never the model's name.

## 5.8 Where a level version is stored

The brief does not say whether an easy version replaces the sheet or is kept beside it. The proposal of this plan,
which Phase 4 confirms with the user before it builds it:

- **A level of the whole sheet** writes a **new project** in My projects, a copy of the song named with the level (for
  example "99 Red Balloons · Easy"), and leaves the original sheet as it is. The reason is that each level must
  be written from the original transcription, not from another level, and the user will want to compare the levels.
  The public library already has versions named Easy, Medium and Hard (`song_versions`), so a level copy can later be
  saved to My Library as a version with that name.
- **A level of a range** changes the sheet in place, with one step of undo, as a stretch does today.

## 5.9 The AI model and the cost

The runs of today use Sonnet 5.5. A level run writes whole hands, so it costs more than Simplify (a tenth of a dollar
per hand on 7 Years) and is closer to a whole run (about $1.80 for 99 Red Balloons with prompt 5, 32 requests). These
are estimates. Phase 3 measures the cost of each level on the test passages and, if Sonnet 5.5 fails the level
prompts, tries Opus 5.5 on one passage (the research ladder used Opus). Every test that calls the AI is announced to
the user with its estimated cost and starts only after the user's ok.

# 6. Binding rules

From implementations 03 and 04 ([`03-context.md`](../03-apply-poc-research/03-context.md) section 2,
[`04-context.md`](04-context.md) section 2) and the project's standing rules. All are kept. The level run changes three
of them **on purpose and only for the level run**, as section 5.2 explains.

| Rule | In this plan |
|---|---|
| No compases, tempo, puntillos or silencios; the figure from the note's own length | kept: the patterns use the grid of the song (section 5.3) |
| The decoration-note rule of 04 | kept at every level |
| Hands: one numeric truth in `notes.pmn` | kept: the notes a level adds, drops or moves go there |
| A change of notes uses `edits.change_notes` and stores one step of undo | kept |
| An AI change of notes is declared in comment lines and checked by code | kept, with the new check of section 5.5 |
| Simplify and a whole run change at most a tenth of a window; notes keep their frame and hand | **not for a level run** (section 5.2); still true for Simplify and Write it all again |
| A run of one hand leaves the other hand exactly as it is | kept |
| The page says "AI", never the model's name; the enhanced mark is never lost | kept |
| A new sheet button goes into `sheetButtons` once | kept; the info button is not a sheet tool (section 4.4) |
| Minimal UI | kept |
| Credits: every test with the AI starts small and asks the user first | kept |
| Browser scripts work on temporary copies, never on a real library piece | kept: folders and metadata of tests are made on copies and deleted |
| A backend `.py` edit reloads uvicorn and stops a running AI job: check the logs first | kept |
| No `src/` edits while a browser check runs | kept |
| The running backend migrates the real database at once: check the processes and run `make db-backup` first | kept (Phase 1) |
| Every drawing is checked zoomed in and against the data before the user sees it | kept (galleries of Phases 2 to 4) |
| Every visible change is checked by the user in the browser at `http://ubuntu:5173` | kept |
| Pytest runs on the CPU when another project holds the GPU | kept |

# 7. Method

## 7.1 Documents

In this folder: `04-3-prompt.md` (the brief), this plan, `04-3-checklist.md` (the status lookup, written at the start
of Phase 1), one report per phase (`04-3-implementation-phase-N.md`), galleries in `gallery/04-3-phase-N/`,
screenshots in `screenshots/04-3-phase-N/`, the Chopin snapshots in `images/chopin_passages/`. The folder's
[`README.md`](README.md) lists them.

## 7.2 Every phase

1. **Study first**: read the code and the data the phase changes; write what exists in the report.
2. **Adapt the plan** from what the study found; section 10 says what changed and why.
3. **Ask the user** only for product choices that the code and the data cannot settle (DECISIONS of the walkthrough).
4. **Build small, then larger**: a few passages, then 99 Red Balloons; for Phase 1, a temporary user's data, then the
   user's pages.
5. **Show the result**: the app at `http://ubuntu:5173`; for a drawing, a gallery served at `http://ubuntu:8099`.
6. **Keep the checks green**: `pytest` in the container (on the CPU when another project holds the GPU), `tsc`,
   `lint`, `vite build`, the browser checks of `context/04-local-development.md` (one at a time, not during pytest),
   `scripts/docs/check-links.py`.
7. **Update the documentation** that the phase makes stale.
8. **Report**: the phase report, then the walkthrough as section 1.2 says.

## 7.3 Branch

Each phase on its own branch `feat/04-3-phase-N`, made from `master` (the names `feat/04-phase-N` are taken by the
first part of implementation 04). After the user's ok, merge into `master` locally and push `master`. No pull requests.
Phases 3 and 4 branch after Phase 1 is merged (section 4.5).

## 7.4 Phase 2 in parallel with Phase 1

The user decided on 2026-10-29 to run Phase 2 in a second session while Phase 1 runs, because the gallery needs
nothing from Phase 1. Two sessions in one folder would change each other's branch, so the Phase 2 session follows
these rules:

1. **Its own folder.** The main checkout (`/home/david/Documents/projects/music/aimpromptu`) belongs to Phase 1 (branch
   `feat/04-3-phase-1`). Phase 2 never runs `git checkout` or `git switch` there. It works in a git worktree (a second
   checkout of the same repository):
   `git -C /home/david/Documents/projects/music/aimpromptu worktree add -b feat/04-3-phase-2 /home/david/Documents/projects/music/aimpromptu-04-3-phase-2 master`.
2. **The documents of this plan.** When the plan was written, `04-3-prompt.md`, this plan and the images of
   `images/` (`99-red-ballons-issue.png`, `whole-song-simplification.png`, `chopin_passages/ballade1-ex1.png`) were not
   committed. Phase 2 copies them from the main checkout into its worktree and makes them its first commit. Phase 1
   commits the same files; identical files merge without a conflict.
3. **Shared files.** Phase 2 does not write `04-3-checklist.md` (Phase 1 writes it), and writes its status in its
   report and in its own paragraph of section 10. Whichever phase merges second resolves the small conflicts in
   section 10, the checklist and the folder's `README.md`.
4. **The app's engine.** The backend container mounts only the main checkout (`/work/aimpromptu`). To draw the easy
   patterns with the engine (task 2.5), Phase 2 sends its script to the container on standard input
   (`docker exec -i aimpromptu-backend-1 python - < script.py`) and writes the drawings to `/home/app/04-3-phase-2/`
   (on the host: `/mnt/ssd2/aimpromptu/home/04-3-phase-2/`). It then copies them into its worktree. It never writes
   into the main checkout, and it never edits `src/`.
5. **Serving the gallery.** Port 8099 may be in use by Phase 1. Phase 2 checks that the port is free and uses 8098 if it
   is not.
6. **Merging.** As every phase: after the user's ok, merge `feat/04-3-phase-2` into `master` and push, then remove the
   worktree (`git worktree remove`). Phase 3 starts after both Phase 1 and Phase 2 are merged.

# 8. Phases

The phases run in order, except Phase 2: it does not touch `src/` and needs no part of Phase 1, so it runs in a
second session while Phase 1 runs (the user's decision, section 7.4). Phases 3 and 4 need Phase 1 merged and Phase 2
approved and merged.

## Phase 1: Folders, the pills and the metadata

The **Basic Changes** of the brief (section 4). Backend, database and frontend; no AI call.

Start prompt:

> You are working on an implementation plan. Read @context/implementations/04-app-enhancements/04-3-plan.md,
> @context/implementations/04-app-enhancements/04-3-prompt.md, @context/guidelines/guidelines-implementation-plan.md,
> @context/guidelines/guidelines-communication-with-user.md and @context/implementations/04-app-enhancements/04-context.md.
> Start Phase 1.

1. Write `04-3-checklist.md` (one line per task of this plan, in the form of [`04-checklist.md`](04-checklist.md)) and
   add the new files to the folder's `README.md`.
2. Study: confirm section 4.1; the Save to library and Edit paths for folders (section 4.2); where a project of My
   projects has an artist (section 4.3); the three cases of the info button (section 4.4).
3. The revision `0008` and the models (sections 4.2, 4.4, 4.5), after the process check and `make db-backup`.
4. The routes: folders (create, rename, move with the cycle check, new parent folder, delete), membership (set the
   folders of an item), private metadata (list, add, remove, the suggestions), the filters' options; the rows of
   `GET /projects` and `GET /library/songs` carry their folder ids and metadata. Tests, also of the rights table.
5. **Add to my library** copies the public tags as private metadata (section 4.4).
6. The pills on both pages; **Folders** (the tree, open and close, indentation, New folder, the folder menu, drag and
   drop, the "Folders…" dialog); **Filter** (Artist and the primary keys).
7. The info button and its dialog on the sheet page and on the song page of My Library.
8. Checks: a new browser check `check:folders` on temporary data (create, nest, add a parent folder, move a song,
   filter, the info dialog; everything deleted at the end), `check:projects`, `check:library`, `check:frames-page`,
   the screenshots of both pages in `screenshots/04-3-phase-1/`. The documentation: `context/07-database.md`,
   `documentation/services/backend/paths-and-data.md`, `documentation/services/backend/endpoints.md`,
   `context/frontend/projects.md`, `context/music-library/private-library.md`,
   `documentation/services/frontend/components.md`.
9. The user checks both pages and the info button in the browser (HUMAN INTERVENTION of the walkthrough).

## Phase 2: The gallery of patterns

The first phase of the **Whole Song simplification**. It needs the user's action twice: to copy the Chopin folder to
Ubuntu, and to approve the gallery. No `src/` change, no AI call.

Start prompt:

> You are working on an implementation plan. Read @context/implementations/04-app-enhancements/04-3-plan.md,
> @context/implementations/04-app-enhancements/04-3-prompt.md, @context/guidelines/guidelines-implementation-plan.md,
> @context/guidelines/guidelines-communication-with-user.md and @context/implementations/04-app-enhancements/04-3-implementation-phase-1.md.
> Start Phase 2.

Start prompt when Phase 2 runs in parallel with Phase 1 (section 7.4; the files are read from the main checkout,
because the worktree does not exist yet):

> You are working on an implementation plan. Read @context/implementations/04-app-enhancements/04-3-plan.md,
> @context/implementations/04-app-enhancements/04-3-prompt.md, @context/guidelines/guidelines-implementation-plan.md,
> @context/guidelines/guidelines-communication-with-user.md and @context/implementations/04-app-enhancements/04-context.md.
> Start Phase 2 in parallel with Phase 1, following section 7.4.

1. **The Chopin folder**. The user's PDFs are on the Mac (`/Volumes/DevSSD/Documents/projects/music/chopin`), which
   the agent on Ubuntu cannot read. The user copies them (asked on 2026-10-29, while this plan was written) to
   **`/home/david/Documents/projects/music/chopin`**, a folder outside this repo. It is never copied into the repo and
   never committed: only the cropped snapshots go into `images/chopin_passages/`. **Done on 2026-10-29**: the folder
   holds 17 PDFs (189 MB), among them `ballades.pdf` (57 pages), `waltzes.pdf`, `nocturnes.pdf`, `mazurkas.pdf`,
   `preludes.pdf`. The agent only checks that the folder is still there. If it is not, the walkthrough asks the user
   (HUMAN INTERVENTION) to run the same command again on the Mac:
   `cd /Volumes/DevSSD/Documents/projects/music && zip -r -q chopin.zip chopin -x "*.DS_Store" && scp chopin.zip ubuntu:/home/david/Documents/projects/music/ && ssh ubuntu 'cd /home/david/Documents/projects/music && unzip -q chopin.zip && rm chopin.zip && ls chopin' && rm chopin.zip`.
2. **Sources**. Besides the PDFs, the research has the notes of the same works, which help to find patterns by rule
   and give the notes that the prompts of Phase 3 can quote: the kern files of the first editions
   (`poc-aitu-research/data/raw/kern/humdrum-chopin-first-editions/kern/`: `023` Ballade No. 1, `038` No. 2, `047`
   No. 3, `052` No. 4, the Waltzes `018`, `034`, `042`, `064`, `069`, `070`, the Nocturnes), the research's pattern
   library (`experiments/E11-difficulty-enrichment/ladder/patterns.md`) and its level texts
   (`src/aitu_research/difficulty/ladder.py`: `LEVELS`, `MOTION`).
3. **The passages the user named**: Ballade No. 1, page 10 (simple in both hands: an example of medium); Ballade No.
   1, page 12 (`images/chopin_passages/ballade1-ex1.png`: an octava, then a chord progression up and down that keeps
   the same notes: an example of hard); Ballade No. 4, pages 41 to 56 (several left-hand passages); the Waltzes (the
   user likes their variety of left hands). Other pieces are welcome.
4. **What to leave out**, as the user asked: left hands with many notes that run up and down like scales. Simple
   passages are preferred, also when they have jumps, if they are easy to play at their level.
5. **Easy patterns**: Chopin seldom writes an easy left hand. Where the PDFs have no example, the easy patterns of the
   brief (a held triad; Fa2 then Fa3-La3-Do4) are drawn with the app's engine from a few written notes and marked
   "from the brief, drawn by the app".
6. **Snapshots**: `pdftoppm` (installed) renders a page; a Python crop keeps the passage; files in
   `images/chopin_passages/` named `<piece>-<hand>-<n>.png` (for example `waltz-64-2-left-1.png`). Each one is
   checked zoomed in.
7. **The gallery** `gallery/04-3-phase-2/index.html`: a tab **Right hand** and a tab **Left hand**; pills to filter by
   level (All, Easy, Medium, Hard, and Super hard for the few passages that show where hard ends). Each pattern has a
   short stable name, one line on what the pattern is and why it has its level (the pattern it keeps, the symmetry,
   how much the hand moves), the source (piece, page, compases of the edition), and the snapshot. The same list is
   also written to `gallery/04-3-phase-2/patterns.json`, so that Phase 3 uses exactly the same names (one pattern,
   one name).
8. **The user's review** (HUMAN INTERVENTION): the gallery served at `http://ubuntu:8099/...`. The user may rename
   patterns, change their level, ask for more. The agent changes the gallery until the user approves it; the
   approved names and levels go into section 10.

## Phase 3: The level prompts, tested on 99 Red Balloons

The prompts for easy, medium and hard, written from the approved gallery and tested in memory (scratch scripts with
`ClaudeComplete`, no change in the app's data). Backend code for the measures and the check, no UI.

Start prompt:

> You are working on an implementation plan. Read @context/implementations/04-app-enhancements/04-3-plan.md,
> @context/implementations/04-app-enhancements/04-3-prompt.md, @context/guidelines/guidelines-implementation-plan.md,
> @context/guidelines/guidelines-communication-with-user.md and @context/implementations/04-app-enhancements/04-3-implementation-phase-2.md.
> Start Phase 3.

1. **Study of 99 Red Balloons**. The project of the brief is `c0e39afe-3122-47fb-aada-54952b014783`, which is the
   user's edit copy in the Personal Vault of the My Library version `b2db46eb-b4c7-4f70-b203-1fe02f4c847d`. Its sheet
   was written by the AI with prompt 5 ($1.80, 32 requests) and then edited by the user (stretches). The study finds
   the frames of the passages of `99-red-ballons-issue.png` and `whole-song-simplification.png`, picks two or three
   more passages (a verse, a chorus, a passage where the right hand plays nothing), and measures them (section 5.6).
2. **The measures** ported from the research's hand tracker to the app's time (section 5.6), with tests.
3. **The grid** of section 5.3, measured on 99 Red Balloons and on one song played by a human.
4. **The prompts**: a shared part (the task, the melody first, decoration notes, artifacts, the right hand that helps
   the left hand, the declared lines, the answer format) and one part per level (`easy.md`, `medium.md`, `hard.md`),
   with the pattern names of the gallery and short examples in the F1 frames text (from the kern of the gallery's
   passages or from the brief). The list of levels in the code stays open for super hard. A new `VERSION` for the new
   prompts.
5. **The plan of the song** (section 5.4) and its prompt.
6. **The check** of section 5.5, with its numbers fixed from the gallery and the test passages; tests with recorded
   answers (no credits).
7. **Tests with the AI** (the user asked first, with the estimated cost): the test passages at each level, Sonnet 5.5
   first, and Opus 5.5 on one passage if Sonnet 5.5 fails (section 5.9). The cost of each level is measured.
8. **The gallery** `gallery/04-3-phase-3/`: for each passage, the original and the easy, medium and hard versions,
   drawn by the app's engine, with the measures and the patterns used; checked zoomed in; served.
9. **The user's review** (HUMAN INTERVENTION). The agent changes the prompts until the user approves the three levels
   on these passages.

## Phase 4: The levels in the app

The level run behind **Enhance with AI** (sections 5.4, 5.7, 5.8). Backend and frontend.

Start prompt:

> You are working on an implementation plan. Read @context/implementations/04-app-enhancements/04-3-plan.md,
> @context/implementations/04-app-enhancements/04-3-prompt.md, @context/guidelines/guidelines-implementation-plan.md,
> @context/guidelines/guidelines-communication-with-user.md and @context/implementations/04-app-enhancements/04-3-implementation-phase-3.md.
> Start Phase 4.

1. Study: `EnhanceDialog.tsx`, `job.start_simplify`, `write_simplify`, `edits.apply_simplify`, the copy of a project
   (`/projects/{id}/duplicate`). Confirm section 5.8 with the user before building it (DECISIONS of the walkthrough,
   if the study found a reason to change it).
2. The dialog: the levels on a range (Both, Right, Left) and on the whole sheet (the whole sheet, the right hand only,
   the left hand only), with the cost.
3. The run: `start_level` and `write_level` (the plan of the song, then the batches that see the earlier batches),
   the check, the feedback, the stand-in tests.
4. Storing: a level of the whole sheet in a new project named with the level; a level of a range in place with one
   step of undo; the notes in `notes.pmn` through `edits.change_notes` (hands changed where notes moved); the record of
   `sheet.f1` keeps the level, the prompt version, the cost and the declared lines.
5. Tests with the AI on a temporary copy of 99 Red Balloons (the user asked first, with the cost): a range at each
   level, then the whole sheet at easy, medium and hard. Gallery `gallery/04-3-phase-4/` (the whole song, original
   and each level, with the measures); checked zoomed in.
6. Checks: `check:enhance-dialog` with the levels (a stand-in answers the requests that would start the AI), the
   existing checks; the user checks the three versions in the browser.
7. The real runs on 99 Red Balloons (`c0e39afe`), after the user's ok and with the cost said first.

## Phase 5: Documentation and closing

Start prompt:

> You are working on an implementation plan. Read @context/implementations/04-app-enhancements/04-3-plan.md,
> @context/implementations/04-app-enhancements/04-3-prompt.md, @context/guidelines/guidelines-implementation-plan.md,
> @context/guidelines/guidelines-communication-with-user.md and @context/implementations/04-app-enhancements/04-3-implementation-phase-4.md.
> Start Phase 5.

1. The documentation still stale: the core's
   [`README.md`](../../../aitu-backend/src/aitu_backend/sheet/README.md) (the level run, its prompts and its check),
   `context/frontend/annotations.md` and `rendering.md` (the dialog), `context/implementations/README.md`,
   `context/00-index.md`.
2. [`04-context.md`](04-context.md): a new section for 04-3 (folders and metadata, the level run, the decisions that
   bind, where the code is), so that later implementations read one page.
3. The final checks; the open points (the super hard level, a piano sound of the sheet, the licenses of the prompt
   examples taken from the kern files, to add to section 8 of the core's `README.md` before any release).

# 9. Risks

| Risk | What to do |
|---|---|
| The revision 0008 migrates the real database while the app runs | Process check and `make db-backup` before the file goes into `src/` (section 4.5) |
| A branch made before Phase 1 refuses the database after the merge | Phases 3 and 4 branch after the merge (section 7.3) |
| A private secondary key appears in the public library | Private values in their own table (section 4.4); a test checks that the public lists do not change |
| The Chopin PDFs are not on Ubuntu | Phase 2 asks the user to copy them first (task 2.1) |
| Chopin has few easy left-hand patterns | The easy patterns of the brief drawn by the app's engine (task 2.5) |
| The AI loses melody notes or changes the harmony | The check of section 5.5 refuses the answer and sends feedback |
| The left-hand pattern changes from batch to batch | The plan of the song first, and each batch sees the earlier ones (section 5.4) |
| New notes fall between the beats of the recording | The grid of section 5.3, measured first |
| Sonnet 5.5 cannot follow the level prompts | Opus 5.5 tried on one passage, with the cost said first (section 5.9) |
| Cost | Every AI test announced with its cost; passages first, then the whole song |
| **Playback is the recording**: the easy version shows notes that the user does not hear (new left-hand chords), and does not show some that the user hears | Stated in the walkthrough of Phase 4 when the user checks; a piano sound of the sheet is an open point for a later implementation |
| A level of the whole sheet replaces the user's edited sheet | A new project per level (section 5.8); the original stays |

# 10. Changes made by the phases

Each phase adds a dated paragraph here: what changed in the plan, and why.

**Before Phase 1** (2026-10-29, the planning session): the user copied the Chopin folder to
`/home/david/Documents/projects/music/chopin` (task 2.1 done), and decided to run Phase 2 in parallel with Phase 1
(section 7.4).

**Phase 2** (2026-10-29, in the worktree `aimpromptu-04-3-phase-2`): the gallery is built and waits for the user's
review (task 2.8). The plan changed in three small points. First, the gallery is served on port **8098**, because
8099 was taken (section 7.4 rule 5). Second, each snapshot shows both staves with the other hand in light grey, so
that the pattern is seen with the hand it accompanies; the file names stay `<piece>-<hand>-<n>.png`. Third, a
pattern can have several examples (`low-note-then-two-chords` has three Waltzes), so that one pattern keeps one name.
The patterns, their names and levels are in [`gallery/04-3-phase-2/patterns.json`](gallery/04-3-phase-2/patterns.json)
with the status "proposed"; the approved names and levels go here after the review. Details:
[`04-3-implementation-phase-2.md`](04-3-implementation-phase-2.md).

**Phase 2, review 1** (2026-10-29): the user liked the gallery and asked for more drawn left hands. The plan said that
the app draws only the easy patterns that Chopin does not have (task 2.5). The user now wants about ten drawn
variations at each of easy, medium and hard: positions that stay still, two-note chords at easy, a new rhythm or chord
note at medium, one more note in the chord at hard. The app drew 30 of them on one shared melody (the gallery now has
50 left-hand patterns). A rule for the drawings that Phase 3 also needs: an easy left hand jumps at most from a low note
to its chord, and every chord or figure after that stays in one position (9 semitones or less in the drawings).
