# Pages and the shell

Every route, what lives on it, and the two rules the shell enforces.

## Routes

`src/layout/routes.ts` is the single place a URL is written. Nothing hardcodes a path: navigation,
the top bar and the Playground tab strip all read from it.

| Path | Page | Notes |
|---|---|---|
| `/youtube` | `YouTubePage` | Probe a video, download its audio |
| `/playground/input` | `InputPage` | Upload, record, the audio library, **Compose** |
| `/playground/piano-roll` | `PianoRollPage` | |
| `/playground/notes-falling` | `NotesFallingPage` | |
| `/playground/rhythm` | `RhythmPage` | The **Piano Sheet** tab — the route kept its old name |
| `/library` | `LibraryPage` | Browse, tag, playlists, playground version management |
| `/library/play/:id` | `PerformancePage` | Read-only, with overlay pills |

## The shared working artifact

`state/WorkingArtifactProvider` holds the piece the Playground tabs are about, in `sessionStorage`,
so moving between tabs does not lose it.

It drops one piece of legacy state on read: a temporary time range used to live in session state,
before trimmed audio became a real child audio with its own uuid, and leaving it there could make a
later whole-file run reuse the wrong matrix.

## Position has one home

A rule that took a review walk to arrive at, and it is worth stating because it explains several
gestures that look arbitrary.

**The scrub bar moves the recording. The canvas selects.** One surface, one meaning — that is what
lets a click on a note rectangle mean "this note" without also jumping the recording somewhere
nobody asked for.

Which leaves the sheet needing a way to say "here". It is a **double-click on ground that answers to
nothing else**: the strip above the top stave, the gaps between systems, the margins. A single click
there already means nothing, and every element that does mean something is listed rather than
inferred.

`ProgressBar` is the same component on every page — a bar with a draggable handle — over an
`<audio>` element on the sheet and over the synthesised clock on the two visual views. A reader
learns one control for the whole app.

**The page does not scroll after a seek.** Not after a scrub, not after a double-click. The reader
is looking at the place they just pointed at, and moving them to it would take that place away.
Space is the one thing that brings the page to the line: it centres the cursor and plays from it.

So the sequence is: drag to the moment you want, press Space, and the page comes to you.

**The playhead follows the music only while the recording is sounding.** A drag sweeps the line
through a hundred staves in a second; the page chasing it made the gesture impossible to finish.

## Long work never blocks

`hooks/useProgress.ts` consumes the transcription job's Server-Sent Events stream, so a run that
takes tens of seconds reports real model progress rather than a spinner.

## Where to look deeper

- [`documentation/services/frontend/components.md`](../../documentation/services/frontend/components.md)
  — every component and where it sits
- [rendering.md](rendering.md) — the sheet itself
- [timestamps.md](timestamps.md) — `mm:ss.cc`, and why it never wraps
