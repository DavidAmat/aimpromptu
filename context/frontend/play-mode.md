# Play mode

**Play mode** is the piano sheet and nothing else, for a reader who wants to play a song rather than
edit it (implementation 02, plan section 17, Phase 11; the app context's "Play Mode"). It plays a
project, a version of My library, an integrated playlist or a songs playlist. The code is
`aitu-frontend/src/pages/play/`.

## 1. Ways in

| From | Control | Opens |
|---|---|---|
| A song of My library | **Play** in its header | Its first version |
| A version of a song | **Play** in its `⋯`; **Play** beside **Edit** on the version's read-only page | That version |
| Projects | **Play** in a row's `⋯` (once the project reaches its Sheet step) | That project, every part |
| A project's page | **Play** in the header's `⋯` | The whole project, whichever part is on show |
| A songs playlist | **Play** in its header; a click on a row; **Play from here** in a row's `⋯` | The playlist, on its first song or on that one |

The addresses are `/play/<projectId>` and `/play/playlist/<id>`. Play mode is outside the app's
shell: no sidebar. Notes Falling, which was a page of a project until Phase 11, is one of its views
(`/play/<id>?view=falling`).

## 2. The page

```
┌───────────────────────────────────────────────────────────────────────────────┐
│ [Sheet | Notes Falling] [One song | All songs]                      ⏭   ✕    │
│                                                                               │
│  Superestrella                                                                │
│  Aitana · original                                                            │
│                         piano sheet, wide, scrollable                         │
│                                                                               │
│                                   ▶                                           │
└───────────────────────────────────────────────────────────────────────────────┘
```

- **Close** (top right) leaves Play mode: back to where it was opened, or for a playlist to the
  playlist with the song it was on shaded. **Next** beside it, only in a songs playlist with a song
  after this one; its tooltip names that song.
- **Play / Pause** at the foot of the window plays the recording with the cursor.
- The **title** of the song, and under it its artists and version (for a song of the library).
  A song of several parts (an integrated playlist) has each part under its subheader, drawn one
  after the other.
- The small menu at the top left chooses the view (**Sheet**, **Notes Falling**) and, in a songs
  playlist, **One song** or **All songs**.

Nothing on the sheet opens a toolbox: a press picks no note and no stretch. **The cursor** is still
moved by dragging it, or by a double-click on the sheet, as on the Sheet step.

**While the music plays**, the buttons and the menu fade when the pointer rests (2.5 s) and come back
when it moves; while paused they stay.

## 3. Following the music

The page scrolls by itself while the music plays: **each time the cursor reaches another line, that
line is brought to the middle of the window**, so the line before and the line after are both on
screen and a reader who plays a little ahead or behind the cursor keeps the music in view.

**Lyrics show and hide with their frames.** A lyrics piece is placed on a stretch of frames (the
Lyrics tab of the sheet toolbox, [annotations-sheet.md](annotations-sheet.md)). While the music
plays, the piece whose frames are sounding is drawn **black and bold**; in Play mode every other piece
is also faint. Paused, every piece is drawn alike (black in Play mode). The layout does not move.
The Sheet step does the same while it plays, without the fading, and from the lyrics on the page,
so a piece just placed and not saved yet lights up too.

## 4. The keys

| Key | Does |
|---|---|
| Space | Play or pause |
| Up and Down arrows | Scroll by about half a window |
| Escape | Close |

## 5. Notes Falling

The notes of the part being played drop onto a keyboard and are swallowed at the moment they sound,
the keys light as they sound, each hand in its colour. It shows the next 3 seconds. Its clock is the
recording's: switching between **Sheet** and **Notes Falling** keeps the place in the music, and
Space plays and pauses both. Only the recording is heard: the page that was here until Phase 11 also
played a sound made from the notes, which the app context excludes. Taking notes off the recording,
which that page also did, is on the Notes step.

## 6. Parts and playlists

The two kinds of playlist of the app context play differently, as they are meant to:

- **The parts of one song play on without a stop.** At the end of a part the next one starts by
  itself: an integrated playlist is played nonstop, from one sub-song to the next.
- **A songs playlist is played song by song.** At the end of a song the next one opens, and waits
  for **Play**: a reader playing a concert takes a breath between songs. **Next** opens it before
  the end.
- **One song** (the default) shows one song at a time. **All songs** draws every song of the
  playlist on one page, one after the other, so scrolling goes from one song to the next; at the end
  of a song the page scrolls to the next one. The choice is kept in this browser.
- **A song with a stretch** (chosen when it was added to the playlist) starts at the start of the
  stretch and stops by itself at its end. The whole sheet is drawn.

## 7. What it is built from

Each part is the Sheet step's own page, `SheetPage`, in a **play** role (`step.play`): the same
drawing, with no title lines, no scrub bar, no floating bar and nothing that opens a toolbox. Since
implementation 03, Phase 5 the drawing is the new sheet ([rendering.md](rendering.md), "The new sheet"): a click
on it moves the cursor, and the page keeps the cursor's line in the middle while it plays. The new sheet has no
lyrics yet: they come back in implementation 03, Phase 8 (4 parts of the database had lyrics on 2026-10-25). Reusing the page means the sheet in Play mode is exactly the
sheet that was edited. Every part has its own player; the page says which one plays, and starting
one stops any other. A part is drawn when it comes near the window (and kept after), so a long
playlist on one page does not draw every song at once; only the part playing and the next one load
their whole audio file in advance.

## 8. Limits

- **A stretch of a version of several parts** plays on its first part: a songs playlist keeps a
  stretch and a version, not the part it was marked on (Phase 10).
- A stretch shows the whole sheet; the music outside the stretch is not dimmed.
- **Record this stretch**, the button Notes Falling had since Phase 9, went with that page:
  **Record this passage** in the range toolbox of the Sheet step opens the same page.
- Offline playing (the app context's private library as a cache) is left for the production
  version (decision Q-7).

## Where to look deeper

- The code: [`components.md`](../../documentation/services/frontend/components.md) section 4
- The sheet it reuses: [annotations.md](annotations.md), [rendering.md](rendering.md)
- The playlists it plays: [playlists.md](playlists.md); My library:
  [`../music-library/private-library.md`](../music-library/private-library.md)
- The plan: [`implementations/02-private-web-app/02-plan.md`](../implementations/02-private-web-app/02-plan.md)
  section 17, and the Phase 11 report
