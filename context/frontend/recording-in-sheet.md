# Recording in Sheet: the page of a passage

A reader re-records a stretch of a song, or records a new passage into it, on a page of its own
(implementation 02, plan section 13, Phase 9; the app context's "Recording in Sheet"). The take is
read into a sheet like the song's, compared with the stretch, and **promoted** into the song in one
step that **Undo** takes back. The code is `aitu-frontend/src/pages/piece/passage/PassagePage.tsx`;
what the backend writes is in [`../backend/editing.md`](../backend/editing.md).

## 1. The page

**Record this passage** (the record icon in the title bar of the range toolbox) opens the page of
the marked stretch, `/projects/<id>/passages/<passageId>`. **Record a passage** on the floating bar,
and on a blank sheet, opens a new passage at the end of the piece. The sheet is saved first when it
has changes. Notes Falling has **Record this stretch** too.

The page shows the song's title, **Promote**, and two sheets:

- **Current** (with its times, "Current · 0:09 – 0:17", and a play button): the marked frames as they
  are, read only. A new passage has none.
- **Proposal**: a take. With no take yet, **Record** and **Add a take from a file**. **Record**
  opens a small panel: **Play the passage along** (the Current, slowed or hurried to the speed the
  take is played at), **Microphone** (when the computer has more than one; remembered in this
  browser), the level, and
  Record / Stop. A take is kept as soon as it stops ("Take 1", "Take 2"), raised to a level that reads (a
  microphone set low gives a quiet take). Its waveform then shows
  with the stretch to keep, and **Write the proposal** transcribes it, splits its hands and writes
  its sheet **in the passage's key and figure**, so the two sheets read alike. The Proposal is then
  drawn with every tool of the sheet and its own undo (its sheet toolbox has Key, Transpose and
  Layout); its edits are kept by themselves.

**A MIDI piano.** A piano with a MIDI connector, plugged into the computer, can play the take
instead: in the recorder, **Notes from: MIDI piano** (shown when the browser has Web MIDI; it asks
for MIDI once). The keys played are the notes, exactly, with no transcription: **Write the
proposal** keeps those of the chosen stretch, splits the hands and writes the sheet. **Sound**
chooses the microphone that records the take's sound at the same time, or **No sound** (the take
is then silent, as long as its keys). While recording the panel counts the keys played. A note ends
when its key comes up: the sustain pedal is not read.

## 2. The speed and the window

Beside **Proposal**: the take on show, and **the speed** (×0.25 to ×4): how many times as fast the
take goes into the song. A take played twice as slowly reads like the Current at ×2. Over the
Proposal lies **the window**, as long as the Current, with a grip to drag it by; on the Proposal's
bar, **Record a take**, **Choose the stretch of the take** (its waveform again) and **Fit the whole
take into the window** (the speed at which it fills it).

## 3. Promote

**Promote** offers:

| Choice | What changes |
|---|---|
| **Fit to the window**, with **Keep the original audio** or **Use my recording** | The notes under the window replace the passage's, scaled into it; with the recording, its audio too (played at the speed, its pitch kept). The song keeps its length |
| **Replace the whole passage** | The whole take, at the speed, replaces the passage; the song gets longer or shorter, and the dialog says by how much ("The song gets 3.2 s longer.") |

A new passage has one choice, **Put it in**. The dialog also names the marks of the passage that go
with it, when there are any. The sheet then opens with the promotion as its last step: **Undo**
puts the song back as it was, notes, audio and sheet, and **Redo** promotes again. Back on the whole
sheet nothing shows that the passage was re-recorded. The `⋯` menu deletes the take on show or
discards the passage (its takes go, the song stays as it was).

Leaving the page with the back arrow keeps the passage: **Record this passage** on the same frames
opens it again, takes and all, as long as the song has not changed since. A passage left open goes
when the project is deleted or saved to the library.

## 4. The microphone

**The microphone needs a secure page.** The browser lets a page record only over HTTPS or at
`localhost`: from the Mac at `http://ubuntu:5173` **Record** is disabled and says so; there, **Add a
take from a file** works, or the app is opened at `http://localhost:5173` through the SSH tunnel
([`04-local-development.md`](../04-local-development.md)).

## Where to look deeper

- The backend: [`../backend/editing.md`](../backend/editing.md),
  [`documentation/services/backend/editing-and-compose.md`](../../documentation/services/backend/editing-and-compose.md)
  section 3, [`endpoints.md`](../../documentation/services/backend/endpoints.md) section 5
- The code: [`documentation/services/frontend/components.md`](../../documentation/services/frontend/components.md)
  section 3.1
- The steps of a project around it: [projects.md](projects.md); the sheet: [annotations.md](annotations.md)
