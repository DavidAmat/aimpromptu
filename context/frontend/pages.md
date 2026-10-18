# Pages and the shell

Every route, what lives on it, and the rules the shell enforces.

## Routes

`src/layout/routes.ts` is the single place a URL is written. Nothing hardcodes a path: the sidebar,
the step tabs, the Lab tabs and the redirects all read from it. The table of every path, by phase,
is plan section 6.3 of [implementation 02](../implementations/02-private-web-app/02-plan.md).

| Path | Page | Notes |
|---|---|---|
| `/login` | `LoginPage` | **Sign in**: Username, Password. Outside the shell and open to all. Returns to `?next=` (an address of this app only) |
| `/` | | Redirects to `/projects` |
| `/projects` | `ProjectsPage` | The Personal Vault, newest change first; **New project** (From source, From scratch, From other projects, Import); per row Duplicate, Export, Rename, **Play**, Delete (**Discard changes** and **Open the song** on an edit copy, which says **Editing**) |
| `/projects/new` | `PiecePage` | A new project, with only the Source step |
| `/projects/compose` | `ComposePage` (`pages/compose/`) | **From other projects** (Phase 10): choose passages, then **Save as song** or **Save as integrated playlist** ([playlists.md](playlists.md)) |
| `/projects/:id` | `PiecePage` | Opens the project on the furthest step that is ready |
| `/projects/:id/<step>` | `PiecePage` | One step: `source`, `audio`, `notes`, `hands` or `sheet`. **Save to library** once the Sheet step is ready; a version of My library opens read only, with **Edit**. `:id` may be any part of a project of several parts, whose Sheet step lists them (Phase 10) |
| `/projects/:id/passages/:passageId` | `PassagePage` | Recording in Sheet (Phase 9): the Current and the Proposal of a passage, **Promote** ([recording-in-sheet.md](recording-in-sheet.md)) |
| `/library/songs` | `SongsPage` (`pages/library/`) | My library (Phase 6): the songs, a table with a filter |
| `/library/songs/:id` | `SongPage` | One song: **Play** (its first version), its artists and its versions (Open, Play, Edit, Duplicate, Export, Add to a playlist, **Publish** (Phase 14), Rename, History, Delete) |
| `/library/artists` | `ArtistsPage` | The artists with their other names, a table with a filter |
| `/library/artists/:id` | `ArtistPage` | One artist: its names (Add a name, Make default, Rename, Remove) and its songs; Merge, Delete |
| `/library/shared` | `SharedPage` | The libraries other users share with the user (Phase 14): the songs of one owner (`?from=`), **Share my library** |
| `/library/shared/songs/:id` | `SharedSongPage` | One shared song: its versions (open read only, Play), **Add to my library** |
| `/requests`, `/requests/:id` | `RequestsPage`, `RequestPage` (`pages/requests/`) | The user's requests to the Public Library (Phase 14); one laid out like a pull request: **Conversation** (the timeline, comments, comments on a stretch with the stretch drawn, replies, reviews) and **Sheet** (`/sheet`: the whole proposed sheet, **Comment on this stretch**); **Withdraw**, **Change and send again** |
| `/admin/requests`, `/admin/requests/:id` | `ReviewPage`, `RequestPage` | **Review** (master user, Phase 14): the open requests oldest first (or **All**); one request as above, with **Review** opening **Finish your review** (a decision per item) |
| `/library/playlists` | `PlaylistsPage` | The songs playlists and the integrated playlists of My library (Phase 10), **New playlist** |
| `/public/songs` | `PublicSongsPage` (`pages/public/`) | The Public Library (Phase 13): a search, the filter chips (Decade, Region, Genre, Tag), a table sorted by popularity, year or title, one page at a time; the address keeps it all; **Propose a song** (Phase 14) |
| `/public/songs/:id` | `PublicSongPage` | One public song: byline, facts, **On the chart** (the line of its places), **Versions** and **Other versions** (Play, like, Add to my library; **Ask for a fixed version** on the user's own, Phase 14), Lyrics; **Play**, **Add to my library**, **Open in My library**; **Suggest a change** (Phase 14) |
| `/public/artists`, `/public/artists/:id` | `PublicArtistsPage`, `PublicArtistPage` | The public artists (search, sort); one with its songs and albums by popularity, **Add to my library** |
| `/public/playlists`, `/public/playlists/:id` | `PublicPlaylistsPage`, `PublicPlaylistPage` | The public songs playlists; one with **Play** (Play mode with `?from=public`) and **Add to my library** |
| `/library/playlists/:id` | `PlaylistPage` | One songs playlist: **Play**, its songs with their version and stretch (a click plays from that song; `?at=` shades the song Play mode was closed on), **Add a song** |
| `/play/:projectId` | `PlayPage` (`pages/play/`) | **Play mode** (Phase 11), outside the shell: a project or a version, every part; `?view=falling` is Notes Falling ([play-mode.md](play-mode.md)) |
| `/play/playlist/:id` | `PlayPage` | Play mode on a songs playlist: `?at=` the song, `?all=1` every song on one page |
| `/admin/users` | `UsersPage` (`pages/admin/`) | Master user only. Every user; **New user**, **Reset password**, **Disable** / **Enable** |
| `/admin/lab/<tab>` | `LabLayout` | Master user only. `video`, `calibration`, `detection`, `notes`, `examples` (and `examples/:slug`) |
| `/dev/roll-bench` | `RollBenchPage` | Development builds only: the Notes step's measurements |

**Old paths** redirect to their new home, keeping the query string (`LEGACY_REDIRECTS`):
`/piece/...` to `/projects/...`, `/video/<tab>` to `/admin/lab/<tab>`, `/youtube` to
`/projects/new`, `/playground/...` to `/projects`, `/library` and `/library/play/...` (the old
Piano Library) to `/library/songs`, and `/projects/:id/notes-falling` to Play mode on Notes Falling
(Phase 11). Phase 15 removes them.

## Signing in and the guards

Since implementation 02, Phase 4 every page except `/login` needs a signed-in user. Two guards of
`layout/RequireUser.tsx` wrap the routes in `App.tsx`:

- **`RequireUser`** wraps the whole shell. While the page asks the backend who is signed in
  (`GET /auth/me`, once when the page opens) it draws nothing; with nobody signed in it opens
  `/login?next=<the address asked for>`, and the sign-in page returns to that address after the sign in.
- **`RequireMaster`** wraps **Users** and **Lab**. A user who is not the master user sees
  "Page not found", so an Admin address tells them nothing. The backend refuses those routes on its
  own (`403`).

`state/AuthProvider.tsx` holds the signed-in user (`useAuth()` of `state/authContext.ts`). When any
request answers `401` (the session ended elsewhere, the password was reset, or 30 days passed),
`api/client.ts` sends `SIGNED_OUT_EVENT`, the provider forgets the user, and `RequireUser` opens the
sign-in page. A project the user may not open answers `404` from the backend, like a project that
does not exist, and the project page shows "There is no project of yours at this address." with
**Open Projects**. The rules are in [`../08-security.md`](../08-security.md).

## The shell

`layout/AppLayout.tsx` puts the sidebar (`ui/Sidebar.tsx`) beside the page (`ui/AppShell.tsx`). The
sidebar shows **Projects**, a **My library** group with **Songs**, **Artists** (Phase 6) and
**Playlists** (Phase 10) and **Shared** (Phase 14), a **Public library** group with **Songs**,
**Artists** and **Playlists** (Phase 13), **Requests** (Phase 14), and for the master user an
**Admin** group with **Review** (Phase 14), **Users** and **Lab**. The number beside **Requests** is
the user's requests with changes asked, and beside **Review** the requests waiting for a review;
both are counted again on every move between pages and when a request changes. **Play mode** (`/play/...`, Phase 11)
is outside the shell, like the sign-in page: the sheet alone, with no sidebar
([play-mode.md](play-mode.md)).
The user menu at its foot shows the username and the role, then **Change password**
(`layout/PasswordDialog.tsx`), **Share my library** (`layout/ShareDialog.tsx`, Phase 14), the theme (**Light**, **Dark** or **System**), **Keyboard shortcuts**
and **Sign out**. The sidebar is open on the list pages and closed inside a project; the reader's own choice holds until
they move between the two kinds of page. Under 900 px it stays closed, as a rail of icons with
their names in tooltips. `⌘K` (`Ctrl+K`) opens **Search** from anywhere (`layout/SearchDialog.tsx`):
it filters the songs of My library (by title and artist) and the projects (by title) as the reader
types, then lists the most popular public songs and artists that match (Phase 13); the arrows move
through the results, and Enter opens one.

## The steps of a project

`/projects/:id/<step>` is one page with five steps in the order of the work: Source, Audio, Notes,
Hands, Sheet. The project is in the address, so a reload or a shared link opens the same project at
the same step. The backend says which steps are ready; a step that is not ready is grey and its
tooltip says what is missing. A step with unsaved changes asks the reader to save or discard before
any navigation, and closing the browser tab shows the browser's own warning.

Detail: [projects.md](projects.md).

## The shared working artifact

`state/WorkingArtifactProvider` holds the working piece in `sessionStorage`: the project page sets
it when it loads a project, and it carries the column length (`frameMs`) the sheet and Notes Falling
read the piece at. It was made for the Playground tabs, which are gone; the project in the address
is now what every page works on.

It drops one piece of legacy state on read: a temporary time range used to live in session state,
before trimmed audio became a real child audio with its own uuid, and leaving it there could make a
later whole-file run reuse the wrong matrix.

## Position has one home

A rule that took a review walk to arrive at, and it is worth stating because it explains several
gestures that look arbitrary.

**The scrub bar moves the recording. The canvas selects.** One surface, one meaning: that is what
lets a click on a note rectangle mean "this note" without also jumping the recording somewhere
nobody asked for.

Which leaves the sheet needing a way to say "here". It is a **double-click on ground that answers to
nothing else**: the strip above the top stave, the gaps between systems, the margins. A single click
there already means nothing, and every element that does mean something is listed rather than
inferred.

The steps of a project follow the same idea. On the Audio step, the playhead is moved in the **time ruler**
at the top of the waveform (press or drag) or with a double-click; a drag in the waveform selects.
On the Notes and Hands steps, the playhead is moved in the time ruler and on the bar under the piano
roll visualization. There a double-click on empty space adds a note, so it does not move the
playhead.

`ProgressBar` is the scrub bar of the sheet: a bar with a draggable handle over an `<audio>`
element. (Notes Falling had the same bar until Phase 11; in Play mode it has no bar and follows the
sheet's recording.)

**The page does not scroll after a seek.** Not after a scrub, not after a double-click. The reader
is looking at the place they just pointed at, and moving them to it would take that place away.
Space is the one thing that brings the page to the line: it centres the cursor and plays from it.

So the sequence is: drag to the moment you want, press Space, and the page comes to you.

**The playhead follows the music only while the recording is sounding.** A drag sweeps the line
through a hundred staves in a second; the page chasing it made the gesture impossible to finish.

## Long work never blocks

`hooks/useProgress.ts` consumes a job's Server-Sent Events stream (a connection on which the backend
keeps sending progress messages), so a run that takes tens of seconds reports real progress rather
than a spinner. The transcription, the YouTube download and **Predict hands** all run as jobs. On the
Notes tab the same stream also carries the notes, so the rectangles appear while the piece is
transcribed.

## Where to look deeper

- [`documentation/services/frontend/components.md`](../../documentation/services/frontend/components.md):
  every component and where it sits
- [projects.md](projects.md): Projects and the steps of a project
- [rendering.md](rendering.md): the sheet itself
- [timestamps.md](timestamps.md): `mm:ss.cc`, and why it never wraps
