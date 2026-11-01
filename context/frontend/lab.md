# The Lab: the video reader's pages

The **Lab** is the master user's workbench for the video reader. The video reader reads a Synthesia-style
video (notes that fall down a roll) into the notes of a piece. The Lab is where the reader is measured:
each step of the reading has its own tab, and a detection rule ships only when its score over the example
screenshots is measured. The Lab is under **Admin**, for the master user only. The code is
`aitu-frontend/src/pages/video/` and `components/video/`, with the shell in `layout/LabLayout.tsx`.

## 1. Who can open it

- The Lab's addresses are `/admin/lab/<tab>` (`layout/routes.ts`, `LAB_TABS`). `RequireMaster` wraps them, so
  another user sees "Page not found" and the Admin group of the sidebar shows **Lab** only to the master user.
- The backend's `/frame-examples` router is a master router (`api/__init__.py`): any other user gets `403`.
- The backend's `/video` router is a user router. Each user reads and writes their own videos. The master
  user sees every video in the Lab, and the progress stream of a job answers `404` to anyone who did not
  start it, except the master user. See [endpoints.md](../../documentation/services/backend/endpoints.md),
  section 1.

## 2. The five tabs

The tabs are in the order of the work on a video. `/admin/lab` opens **Video**.

| Tab | Address | Page | What it does |
|---|---|---|---|
| **Video** | `/admin/lab/video` | `VideoPlayerPage.tsx` | Brings a video in from one YouTube link (`POST /video/download`: the video and the audio of that same video). Samples its frames at a chosen step in milliseconds (`POST /video/{uuid}/sample`, 100 ms by default) and steps through them. The player draws the sampled frames, not a video element, so the screen shows what the detector reads. |
| **Calibration** | `/admin/lab/calibration` | `VideoCalibrationPage.tsx` | Fits the piano on one sampled frame, with the calibration editor of the examples. Then it measures the scroll speed of the roll (`POST /video/{uuid}/measure`). The offset line follows from that measured speed, so the screen draws it rather than offering it. |
| **Detection** | `/admin/lab/detection` | `VideoDetectionPage.tsx` | Runs the detector over every sampled frame as one job (`POST /video/{uuid}/detect`) and steps through what it found (`GET .../detection`, `GET .../report`). A rectangle the momentum rule refused is drawn in its own colour, so a refusal can be looked at. |
| **Notes** | `/admin/lab/notes` | `VideoNotesPage.tsx` | Stitches the whole video into one tall picture (the roll, whose vertical axis is time) and reads the notes from it (`POST /video/{uuid}/notes`, a job). The notes can be corrected (`GET` and `PUT .../corrections`) before they are written into the piece (`POST /video/{uuid}/events`). Writing changes the piece and moves its music version on, and the screen says so before it writes. |
| **Examples** | `/admin/lab/examples`, `/admin/lab/examples/:slug` | `ExamplesPage.tsx` | The example screenshots (section 3). The work on one example goes left to right: fit the piano overlay, read the picture by hand (the manual annotation), then run the detector and look at where the two disagree. The score board (`GET /frame-examples/score`) shows what the detector found, invented and missed. |

The Lab pages draw in canvases and SVGs with many colours, so `LabLayout` draws them again from the start when
the colour scheme changes. The video picked on one tab is remembered for the other tabs (`video/selectedVideo`).

## 3. The examples

- The **example set** is a set of screenshots of Synthesia videos. The pictures are 3600 px wide and are read
  at the working width of the detector, so a coordinate placed in the calibration editor means the same thing
  to the detector. The screenshots stay where the user put them, in
  `context/implementations/01-mvp/04-synthesia-to-notes/examples/`. Only what is derived from them is data.
- Each example is one record, `.database/lab/frame-examples/<slug>.json`, with its calibration, its manual
  annotation and its flag for a picture with no roll. A cached copy of the picture sits beside it
  (`cache/<slug>.jpg`). Every example needs its own calibration, because every example is a different piano.
- A rule ships with its measured score over these pictures, or it does not ship (the rule V-20 named in the
  code). The score board is that measurement.

## 4. The modules of the video reader

The backend code is `aitu-backend/src/aitu_backend/video/`. Each module has one job:

| Module | Job |
|---|---|
| `download.py` | Downloads one YouTube video, capped at 720p, and the audio of the same video. |
| `store.py` | One video on disk: the file, its metadata, its calibration and its frames, all under `.database/tmp/<userId>/<partId>/video/`. The video is the source; the sampled frames are a cache. |
| `sampling.py` | Samples the frames of a video with ffmpeg, at the sampling step. |
| `images.py` | Reads a picture at the one resolution the rest of the code assumes. |
| `finder.py` | Finds the piano overlay from one rectangle that the user drags over the piano. |
| `geometry.py`, `upgrade.py` | Turns the overlay into every key and its lane. `upgrade.py` spells out an older grid calibration as per-key borders. |
| `plate.py` | The background plate: everything static is subtracted before anything is detected. |
| `detector.py` | One picture and one calibration in; onsets and sustains out. |
| `momentum.py` | A note is a rectangle that falls. Anything that does not fall (a title, a watermark, a guide line) is not a note. |
| `colour.py` | The second check: the colour of the rectangle must be one that notes are drawn in. |
| `motion.py` | The scroll speed of the roll and its two edges. |
| `reading.py` | Reads a whole video: the plate, then every sampled frame. |
| `stitch.py`, `notes.py` | Stitches the frames into the roll, then turns the roll into the notes of the piece. |
| `piece.py` | The step that makes the video into the piece; the Notes tab writes through it. |
| `examples.py`, `scoring.py` | The example set and the score board. |

The routes are in `api/video.py` (the user's videos, and the Lab's steps) and `api/frame_examples.py` (the
examples, master only). The client is `aitu-frontend/src/api/video.ts` and `api/frameExamples.ts`.

## 5. The Video step of a project

The Lab is not the only place the reader runs. A project made from a video has a **Video** step on its page
(`/projects/:id/audio`, implementation 02, Phase 5). `POST /video/upload` makes such a project from a file on
the user's disk, and **Read notes** (`POST /video/{uuid}/read`) reads it into the part's notes. Those routes
use the same modules as the Lab, and every user has them. The Lab opens the same video for measurements.
The Video step itself is on [projects.md](projects.md).

## 6. Production

The production version leaves out the YouTube download and the video reader
([05-deployment.md](../05-deployment.md)). The Lab is a development tool of the home version.

## Where to look deeper

- The routes: [endpoints.md](../../documentation/services/backend/endpoints.md), section 1 (the video paragraphs),
  and [paths-and-data.md](../../documentation/services/backend/paths-and-data.md) (the Lab records)
- The components: [components.md](../../documentation/services/frontend/components.md), section 1
- The pages and the guards: [pages.md](pages.md); who may open them: [08-security.md](../08-security.md)
- The reasoning of the reader and its examples: the implementation
  [`04-synthesia-to-notes`](../implementations/01-mvp/04-synthesia-to-notes/README.md)
- The Video step and the projects it makes: [projects.md](projects.md)
