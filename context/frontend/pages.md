# Pages and the shell

Every route, what lives on it, and the rules the shell enforces.

## Routes

`src/layout/routes.ts` is the single place a URL is written. Nothing hardcodes a path: the sidebar,
the step tabs, the Lab tabs and the redirects all read from it. The table of every path, by phase,
is plan section 6.3 of [implementation 02](../implementations/02-private-web-app/02-plan.md).

| Path | Page | Notes |
|---|---|---|
| `/` | | Redirects to `/projects` |
| `/projects` | `ProjectsPage` | The projects, newest change first; **New project** |
| `/projects/new` | `PiecePage` | A new project, with only the Source step |
| `/projects/:id` | `PiecePage` | Opens the project on the furthest step that is ready |
| `/projects/:id/<step>` | `PiecePage` | One step: `source`, `audio`, `notes`, `hands` or `sheet` |
| `/projects/:id/notes-falling` | `NotesFallingPage` | Inside the project's page, from its `⋯` menu |
| `/admin/lab/<tab>` | `LabLayout` | `video`, `calibration`, `detection`, `notes`, `examples` (and `examples/:slug`) |
| `/dev/roll-bench` | `RollBenchPage` | Development builds only: the Notes step's measurements |

**Old paths** redirect to their new home, keeping the query string (`LEGACY_REDIRECTS`):
`/piece/...` to `/projects/...`, `/video/<tab>` to `/admin/lab/<tab>`, `/youtube` to
`/projects/new`, and `/playground/...` and `/library...` to `/projects`. Phase 15 removes them.

## The shell

`layout/AppLayout.tsx` puts the sidebar (`ui/Sidebar.tsx`) beside the page (`ui/AppShell.tsx`). The
sidebar is open on the list pages and closed inside a project; the reader's own choice holds until
they move between the two kinds of page. Under 900 px it stays closed, as a rail of icons with
their names in tooltips. `⌘K` (`Ctrl+K`) opens **Search** from anywhere (`layout/SearchDialog.tsx`):
it filters the projects by title as the reader types, the arrows move through the results, and
Enter opens one.

## The steps of a project

`/projects/:id/<step>` is one page with five steps in the order of the work: Source, Audio, Notes,
Hands, Sheet. The project is in the address, so a reload or a shared link opens the same project at
the same step. The backend says which steps are ready; a step that is not ready is grey and its
tooltip says what is missing. A step with unsaved changes asks the reader to save or discard before
any navigation, and closing the browser tab shows the browser's own warning.

Detail: [flow-page.md](flow-page.md).

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

`ProgressBar` is the same component on the sheet and on Notes Falling: a bar with a draggable
handle, over an `<audio>` element on the sheet and over the synthesised clock on Notes Falling. A
reader learns one control for both.

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
- [flow-page.md](flow-page.md): Projects and the steps of a project
- [rendering.md](rendering.md): the sheet itself
- [timestamps.md](timestamps.md): `mm:ss.cc`, and why it never wraps
