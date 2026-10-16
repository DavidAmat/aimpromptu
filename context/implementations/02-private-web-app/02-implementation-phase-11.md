# 02: Phase 11 report: Play mode

Plan: [`02-plan.md`](02-plan.md) sections 6.3, 14 and 17, and section 20, Phase 11. Checklist:
[`02-checklist.md`](02-checklist.md). Branch `feat/phase-11`, made from `master` at `fd44bee` (Phase
10 merged and pushed, after the user's check). Built 2026-10-15 on the Ubuntu machine, while another
project of the user used the GPU: the user asked that the backend not use it (section 9).
`vexflow-v2` did not change.

# 1. Summary

| Story | Result |
|---|---|
| 11.1 The page | `/play/:projectId`, outside the shell: the sheet alone, **Close** (and **Next** in a songs playlist) at the top right, **Play / Pause** at the foot. While it plays, a new line of music is brought to the middle of the window, the buttons fade when the pointer rests, and each lyrics piece is drawn in full only while its frames sound (the others faint). Space, the arrows, Escape. **Notes Falling** is a view of the page (`?view=falling`), on the recording's clock |
| 11.2 Playlists | The parts of a project are drawn one after the other under their subheaders and played without a stop. `/play/playlist/:id`: one song at a time with **Next**, or **All songs** on one page; at the end of a song the next one opens and waits; a stretch starts and stops where it was chosen. **Close** goes back to the playlist with the song shaded. **Play** on a song, on a version (its `⋯` and its read-only page), on a project (Projects row, the project's `⋯`), on a playlist (header, a row, **Play from here**). `/projects/:id/notes-falling` and the old page are gone |
| 11.3 Documentation | `context/frontend/play-mode.md` (new); `pages.md`, `projects.md`, `playlists.md`, `recording-in-sheet.md`, `frontend/README.md`, `00-project-complete-overview.md`, `00-index.md`, `music-library/private-library.md`; `components.md` (section 4 rewritten, 6, 9, 10), `endpoints.md`, `editing-and-compose.md`, `aitu-frontend/README.md`; the plan's "as built in Phase 11" notes |

Also found and fixed: **Replace the version** failed (`422`) on a version made of one pasted file
(section 5). Checks at the end (section 7): backend 1,094 tests on the CPU, the 3 known CPU failures
and 1 skip; every frontend check passes, the new `check:play` too (30 checks), except
`check:passage`, which needs the GPU and is to be run again (section 9).

# 2. The design

## 2.1 Each part is the Sheet step's page

Phase 9's learning was to reuse a whole page through a role. Play mode does the same: each part is
`SheetPage` with `step.play` (`PlayView`), so the sheet in Play mode is drawn exactly as it is
edited (the saved figure length, the key and clef changes, the brackets, fingers, lyrics, spacing),
with nothing to keep in step. The role removes what is not playing:

| | Sheet step | Play role |
|---|---|---|
| Title lines | yes | no: the page draws the song's title and byline, and each part's subheader |
| Scrub bar | `ScorePlayer compact` | `ScorePlayer headless` (nothing drawn but a refused start) |
| Floating bar, toolboxes, copy and paste | yes | no |
| `TimeScoreView` | interactive | `readOnly`: no note or stretch picked, no handle to spread a line |
| Following the cursor | the nearest place | `followCentre`: a new line to the middle of the window |
| Lyrics | all drawn | `litLyrics` while it plays |
| Space | the player's own | off; the page's keys |

`library/loadPerformanceScore.ts`, kept since Phase 1 "for Play mode", was not used: it read fewer
marks than the sheet page (no clef changes, spacing, beam joins) and would have drawn a different
sheet. It is deleted.

## 2.2 The page (`pages/play/`)

`playQueue.ts` reads what to play as a list of songs, each with its parts: a project is one song
(`GET /projects/{id}` and `/parts`), a songs playlist its items (`GET /playlists/{id}`; a version of
several parts reads its parts too). `PlayPage.tsx` draws each part as a memoised `PlaySegment`,
mounted when it comes within 800 px of the window and kept. Each part has its own player; the page
keeps a map of their transports and the **active** part (the one playing, or the one whose cursor
the reader moved): Space and the button act on it, and a part that starts stops any other. Only the
active part and the next one load their whole audio file; the others only their length
(`ScorePlayer preload`, changed on the element, because a new element would stop the music).

**How the end of a part is handled** follows the app context's two kinds of playlist:

- the parts of one song (an integrated playlist) play on: the next part starts as soon as its player
  is there (`startWhenReady`);
- a songs playlist is played song by song: the next song opens (or, with **All songs**, the page
  scrolls to it) and waits for Play. This is a choice made without the user (section 8).

A stretch of a playlist starts at `fromMs` (sought once the sheet is drawn) and stops at `toMs`
(`ScorePlayer stopAt`, checked on each animation frame, which then reports `onEnded`).

**Notes Falling** (`FallingView.tsx`) draws the notes of the active part from `GET
/matrix/{uuid}/events`, on a `PlayClock` fed by the active part's player, read with
`useSyncExternalStore`, so the sheets are not drawn again sixty times a second. It has no sound of
its own (the old page could synthesise a piano; the app context plays only recorded audio) and
picks no notes.

**The fading buttons**: 2.5 s after the last pointer move while the music plays. The **lyrics**:
the pieces whose `[fromColumn, toColumn)` holds the cursor's frame keep full ink, the others are
drawn at 18 % through a style of the sheet. That style is now scoped to its own sheet
(`data-score-view`, `useId`): `TimeScoreView` wrote global rules, which was harmless with one sheet
on a page and wrong with several.

## 2.3 Where the plan's wording was read

- "With Play mode closed, the playlist page shows the songs on the left to choose one or reorder
  them": **Close** goes to the songs playlist's page, which lists the songs and reorders them, with
  the song it was on shaded (`?at=`), and a click on a row plays from it. No second list page.
- "A **Continuous** option": **All songs** in the menu, beside **One song**, remembered in the
  browser.
- "Next appears only in a songs playlist": and only when a song follows.
- "The arrow keys scroll": up and down by 40 % of the window.

# 3. Story 11.2: the entry points

| Where | Control |
|---|---|
| Song (My library) | **Play** in the header (first version); **Play** in a version's `⋯` |
| A version, read only | **Play** beside **Edit** |
| Projects | **Play** in a row's `⋯` (was **Notes Falling**), enabled once the project reached its Sheet step |
| A project's page | **Play** in the header's `⋯` (was **Notes Falling**): the whole project, whichever part is on show |
| A songs playlist | **Play** (primary; **Add a song** became secondary), a click on a row, **Play from here** in its `⋯` (**Open** stays, for the version) |

`/projects/:id/notes-falling` redirects to `/play/:id?view=falling` (`LEGACY_REDIRECTS`;
`LegacyRedirect` now joins a target's own query with the old one). Removed with the old page:
`NotesFallingPage.tsx`, `playback/usePlayback.ts`, `PlayerToolbar.tsx`, `PlaybackTransport.tsx`,
`hooks/useStagedRemovals.ts`, `components/notes/NoteSelectionToolbox.tsx`, `PendingRemovalsBar.tsx`,
`describeEvents`, `library/loadPerformanceScore.ts`. Two things went with that page: taking notes off
the recording from Notes Falling (the Notes step does it), and its **Record this stretch** button of
Phase 9 (the range toolbox's **Record this passage** opens the same page). `PUT
/matrix/{uuid}/events/removed` stays in the backend with its tests; no page calls it now.

# 4. Tests and checks written

| File | What |
|---|---|
| `aitu-frontend/scripts/check-play.mjs` (new, `npm run check:play`) | 30 checks on copies (section 7): the page, Space, the fading buttons, the cursor at 50 % of the window's height after a line change, the lyrics by frames (one piece at opacity 1, the other below 0.5), the arrows, a double-click moving the cursor, Notes Falling and its old address, Escape; an integrated playlist of two parts, the second played on; two copies saved as songs, **Play** on a song and on a version, a playlist with **Next**, a stretch that stops by itself, **All songs**, Close back with `?at=1`; 390 px; dark. Uses no GPU |
| `aitu-backend/tests/test_parts.py` | 1 new (section 5) |
| The other browser checks | Each picks its source project as the **shortest title** containing the name: the user's own "Elefants - Oques Grasses Playlist" (79 notes, made after Phase 10) had become the first match, on which `check:lyrics` could not find a second line. `check:passage` allows one audio frame on the song's length (section 9) |

# 5. A defect found on the way: Replace the version on a part of one pasted file

`check:library` failed at **Replace the version** with `422`: "Input should be 'upload', 'recording',
'youtube', 'segment' or 'composed' … input_value='passage'". A file put in by a paste is named kind
`passage` in the timeline (Phase 8). When a part is left with one file, its description takes that
file's kind. Phase 9 made the paste write `segment` instead; **Save to library**, writing the audio
again (`audio/compact.py`), and removing a file on the Source step (`audio/store.py`) still copied
`passage`. The saved version could then not be read, so its edit copy could not replace it.
`segment` was not right either: the audio metadata refuses a segment without the file and range it
was cut from.

The fix is one helper, `schemas.metadata.source_kind`: an upload's word stays, anything else is
`composed` (the word of a project made by From scratch or From other projects). The paste, the
compaction and the file removal use it. The test makes a song of one stretch (From other projects),
saves it to the library, reads its audio, edits it and replaces it; without the fix it fails with
the metadata's error. **No real project was affected**: the 43 projects of `.database/` all have
accepted kinds (read only, checked with a script).

# 6. Speed

Measured in the browser on copies, the machine loaded by another project (load average 5 to 12):

- **Play mode, from the address to the first notehead**: Elefants (3:53) 650 to 740 ms, Superestrella
  tutorial (3:10) 735 to 765 ms (three runs each). It is the sheet page's own drawing time (section
  7, `time:flow` 0.6 s and 1.0 s in Phase 10) plus the project and parts reads.
- `bench:sheet`, median of a hand move: Elefants 224 ms, Superestrella tutorial 282 ms, The Other
  Side 510 ms (Phase 10: 222 to 229, 275 to 280, 525 to 616). The sheet page did not get slower.

# 7. The checks

| Check | Result |
|---|---|
| Backend, full run **on the CPU** | 1,094 tests: 1,090 passed, 1 skipped (the real-model test), 3 failed: the known `test_the_worked_example_at_00_46_prints_three_equal_corcheas` and the two Transkun tests that fail only without a GPU. Phase 10: 1,093 |
| `black`, `flake8`, `mypy` on the changed backend modules | clean (the new test reformatted by `black`) |
| `tsc -b`, `npm run lint`, `npm run build` | clean; the chunk-size warning of Phase 0 |
| `check:render`, `check:history`, `check:note-names`, `check:geometry`, `check:cuts`, `check:notes` | 60, all, 15, all, all, all passed |
| `check:play` (new), signed in | 30 checks passed, no console error, nothing left behind |
| `check:projects`, `check:library`, `check:transpose`, `check:lyrics`, `check:paste`, `check:compose`, `--only clefs`, `check:flow --no-transcribe`, signed in | every check passed, no console error, nothing left behind (`check:library` after the fix of section 5; `check:lyrics` after the source fix of section 4) |
| `check:passage` | **Not passed in this phase**: one run (by mistake, section 9) failed only "the song keeps its length" (233.348 s → 233.35 s, the same audio counted in frames); the check now allows one audio frame. To run again when the GPU is free |
| `time:flow`, `check:flow` with the live transcription | Not run: they transcribe on the GPU |
| `make db-check` on the real `.database/` | no problem, after every script |
| `scripts/docs/check-links.py` | passes |

The browser scripts signed in with `AITU_MASTER_PASSWORD` of `.env` and worked on copies only.

# 8. The 13 checks of the 09 guidelines

Run on Play mode (a project, an integrated playlist, a songs playlist, Notes Falling), the new
**Play** buttons and the playlist page, with the screenshots of
[`screenshots/phase-11/`](screenshots/phase-11/), taken by `check-play.mjs` on its copies.

| # | Check | Result |
|---|---|---|
| 1 | One sentence | Play the song from its sheet, with nothing else on the page |
| 2 | Every sentence a label, control or fact | No sentence: the title, the byline, the subheaders. "This playlist has no songs yet." only when it applies |
| 3 | Words above the first content | The song's title and byline (2 lines) |
| 4 | Very wide | The sheet takes the width; Close and Next at the top right, Play centred at the foot, the menu at the top left (shot 01) |
| 5 | Narrow (390 px, shot 10) | 0 px of sideways scroll; a long title is cut with "…" |
| 6 | Longest, shortest, none | A long title or subheader cut (full on hover); one part: no subheader; a part with no subheader: "Part 2"; a playlist with no song: one line; no byline for a project of the vault |
| 7 | Buttons say what happens | "Play", "Play from here", "Close", "Next: <song>", "Pause", "Sheet" / "Notes Falling", "One song" / "All songs" (their tooltips say what each does) |
| 8 | Helper lines | None |
| 9 | Loading, empty, partial, error | A spinner while the list is read; each part keeps its own sheet loading; an error in the backend's words; a refused start is one line |
| 10 | Tab through it | Every control is a button or a segmented choice; Space, arrows and Escape work without the pointer |
| 11 | Internal names | None: no "part id", "segment", "queue" on screen. "Part 2" is the parts panel's own word |
| 12 | First-time user | "Play", "Next", "Notes Falling", "All songs" |
| 13 | Anti-patterns | Nothing but the music while it plays: the buttons fade |

| Shot | Page |
|---|---|
| 01 | Play mode on a project with two lyrics pieces |
| 02 | Playing: the lyrics piece of the frames sounding in full, the other faint |
| 03 | Playing with the pointer at rest: the buttons gone |
| 04 | The cursor on the second line, in the middle of the window |
| 05 | Notes Falling |
| 06 | An integrated playlist: two parts, the second under "Coda" |
| 07 | A songs playlist on its first song, with Next |
| 08 | All songs |
| 09 | Closed: the playlist with the song it was on shaded, **Play** |
| 10, 11 | 390 px; dark |

# 9. Open points

- **`check:passage` is to be run again** with the GPU: its **Write the proposal** is a transcription.
  It ran once in this phase by mistake, after the user had asked that the backend not use the GPU;
  the running backend then kept the model in 11 GB of GPU memory until it was restarted (done at
  once; the GPU showed 41 MB used after). Nothing of Phase 11 touches the passage page.
- **A songs playlist's next song waits for Play** (section 2.2), and the parts of one song play on.
  Chosen from the app context's two kinds of playlist; easy to change.
- **A stretch of a version of several parts** plays on the version's first part: the playlist keeps
  no part (Phase 10). A stretch shows the whole sheet, the rest not dimmed.
- **Play mode needs the Sheet step open** (notes with their hands): **Play** is disabled before.
- Offline playing is left for the production version (Q-7).

# 10. After the user's first look (2026-10-16)

- **The words did not look black.** The drawing package prints lyrics in a dark grey
  (`LYRIC_TEXT_FILL`, `#3b3f46`), so a piece "shown in full" still read as grey beside the notes.
  In Play mode the words are now black (`TimeScoreView` `lyricsInk`, a style scoped to the sheet);
  the Sheet step keeps the grey. `check:play` now checks the colour of the piece sounding (shot 02).

# 11. Learnings for later phases

- **A style a component writes into the page must be scoped to the component** when two of them can
  share a page: `useId` and an attribute on its root.
- **A check that picks its fixture by "the first title that contains X" changes with the user's
  data.** Pick by a rule that names one project (the shortest title), and say which one in the
  output.
- **A length read from a part of one file is the file's own; from several files, whole 10 ms
  frames.** Compare lengths with one frame of slack.
- **When the GPU is reserved, a browser check that writes a proposal or transcribes uses it through
  the running backend**, which then keeps the model loaded: skip those checks, and restart the
  backend if one ran.
- **A media element's settings change on the element**: a prop in the effect that creates it makes
  a new element and stops the music.
