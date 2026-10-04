# Pages and the shell

Every route, what lives on it, and the rules the shell enforces.

## Routes

`src/layout/routes.ts` is the single place a URL is written. Nothing hardcodes a path: navigation,
the top bar and the Playground tab strip all read from it.

The top bar starts with **Piece**, because a piece now starts there. Then **YouTube to Audio**,
**Video to Notes**, **Playground** and **Piano Library**.

| Path | Page | Notes |
|---|---|---|
| `/` | | Redirects to `/piece/new` |
| `/piece` | `PieceIndex` | The **Piece** entry: the working piece, or a new one |
| `/piece/new` | `PiecePage` | The flow page with only the Source tab |
| `/piece/:uuid` | `PiecePage` | Opens the piece on the furthest step that is ready |
| `/piece/:uuid/<step>` | `PiecePage` | One tab: `source`, `audio`, `notes`, `hands` or `sheet` |
| `/youtube` | `YouTubePage` | Probe a video, download its audio |
| `/video/*` | `VideoLayout` | Video to Notes |
| `/playground/input` | `InputPage` | Upload, record, the audio library, **Compose** |
| `/playground/notes-falling` | `NotesFallingPage` | |
| `/playground/rhythm` | `RhythmPage` | The **Piano Sheet** tab; the route kept its old name |
| `/playground/piano-roll` | | Redirects to `/piece` (the old Piano Roll, removed) |
| `/library` | `LibraryPage` | Browse, tag, playlists, playground version management |
| `/library/play/:id` | `PerformancePage` | Read-only, with overlay pills |
| `/dev/roll-bench` | `RollBenchPage` | Development builds only: the Notes tab's measurements |

## The flow page

`/piece/:uuid/<step>` is one page with five tabs in the order of the work: Source, Audio, Notes,
Hands, Sheet. The piece is in the address, so a reload or a shared link opens the same piece at the
same step. The backend says which steps are ready; a tab that is not ready is greyed and its tooltip
says what is missing. A tab with unsaved changes asks the reader to save or discard before any
navigation, and closing the browser tab shows the browser's own warning.

Detail: [flow-page.md](flow-page.md).

**The old Piano Roll tab is gone** (implementation 08, decision Q-4). The Notes and Hands tabs are
the piano roll visualization now, drawn on a canvas, with an editor. Notes Falling stays on the
Playground.

## The shared working artifact

`state/WorkingArtifactProvider` holds the piece the Playground tabs are about, in `sessionStorage`,
so moving between tabs does not lose it. The flow page sets it when it loads a piece, so the
Playground shows the same piece, and **Piece** in the top bar returns to it.

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

The flow page follows the same idea. On the Audio tab, the playhead is moved in the **time ruler**
at the top of the waveform (press or drag) or with a double-click; a drag in the waveform selects.
On the Notes and Hands tabs, the playhead is moved in the time ruler and on the bar under the piano
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
- [flow-page.md](flow-page.md): the flow page, step by step
- [rendering.md](rendering.md): the sheet itself
- [timestamps.md](timestamps.md): `mm:ss.cc`, and why it never wraps
