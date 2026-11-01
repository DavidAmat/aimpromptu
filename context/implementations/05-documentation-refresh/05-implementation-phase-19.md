# 05, Phase 19: Play mode, the Lab, users and admin, the routes and the shell

Written for: the join of wave A and the agent of Phase 20. Plan section 6, Phase 19; wave A.

## Docs changed

- `context/frontend/lab.md` (new, 92 lines): the Lab as the master user's tools for the video reader. No page
  described it; before, it was one line in five pages. Covers who may open it, the five tabs, the example set and
  the score board, the video modules, and the Video step of a project.
- `context/frontend/play-mode.md`: the Up and Down arrows scroll 40 % of the window's height, not "half a window",
  and do nothing in Notes Falling (`pages/play/PlayPage.tsx`, the keys).
- `context/frontend/pages.md`: the `/projects/:id/<step>` row (`hands` is a redirect to `sheet` since
  implementation 03, Phase 5, `App.tsx`); the Projects row menu (**Open**, **Folders…**, **Info** added; **Play** only
  from the Sheet step); the `/dev/ui` row (development builds only, missing before); a link to `lab.md`; "Sonnet"
  replaced by "the AI" in the Long work section (the rule of the docs: the app says "the AI").
- `context/08-security.md`: `POST /auth/logout` needs no session (it is in `OPEN_ROUTERS`); the old sentence said
  only `/health` and `POST /auth/login` were open. `GET /auth/me` and `PUT /auth/password` do ask for one.
- `context/implementations/05-documentation-refresh/05-inventory.md`: four rows set (`lab.md` added, three updated).

## What was stale

- `pages.md`: the `hands` step (removed); the Projects row menu (three items missing); the `/dev/ui` route; the
  model name in the Long work section.
- `08-security.md`: the list of routes open without a session (logout missing).
- `play-mode.md`: the arrow-key distance.
- The Lab had no page of its own (the gap of the plan, Phase 19).

## Code and docs that disagree in a way that looks like a bug (for the user)

- The Lab's page headers still use old names: `VideoPlayerPage.tsx` says "the Piano Sheet tab", and the headers of
  the Lab pages cite "Stories" and "Task" numbers of implementation 04. The comments are stale, not the behaviour.
  No change made (docs-only phase).
- `endpoints.md` line 20 says only `GET /health` and `POST /auth/login` are open; `OPEN_ROUTERS` also opens
  `POST /auth/logout` (the handler reads no session). The pending edit below fixes the page; the code is not wrong
  about the session check, but the sentence is.

## New terms for the glossary (Phase 20)

- **Lab**: the master user's tools for the video reader (the five tabs). Not in `context/app/01-app-context.md`.
- **Example set**: the Synthesia screenshots the detector is measured on.
- **Score board**: what the detector found, invented and missed over the example set.
- **The roll**: the falling notes of a Synthesia video; the **stitched roll** is the whole video as one picture.
- **Video step**: the step of a project made from a video (`/projects/:id/audio`).

## Not checked

- `play-mode.md` sections 6 to 8 (the wait between songs, the loading of the audio, a stretch of a version): read the
  page, not the code of `PlayPage.tsx` in full (575 lines, read by function list and search only).
- `pages.md`: the sidebar groups and the **Discard changes** / **Open the song** wording of an edit copy in the Projects
  menu (the code has only Open, Duplicate, Export, Rename, Folders…, Info, Play, Delete, plus the edit menu not read).
- `08-security.md`: `chmod 600` of `.env`; the default `WEB_BIND=0.0.0.0` and the backend port `127.0.0.1:8765`
  (`config.py` and `vite.config.ts` not read for these values); the Docker API on port 2375 (a finding of
  implementation 08, not in this code); the test files' contents (they exist: `test_rights.py`, `test_auth.py`,
  `test_requests.py`).
- `lab.md`: the detection rules and their numbers (in the implementation folders, not read); the Detection and
  Notes pages in full (`VideoDetectionPage.tsx` 306 lines, `VideoNotesPage.tsx` 578 lines) read by header and API
  calls only.
- The `/video` Lab routes: the purpose of each one comes from its name and its response model, not from its body
  (except `/read`, `/upload`, `/download`, which endpoints.md already describes).

## Check results

- `check-names.py` on the four files: 201 names, two listed, both expected:
  - `context/frontend/pages.md:43` `/projects/:id/notes-falling`: an old path, listed on purpose.
  - `context/08-security.md:111` `/api/docs`: FastAPI's default `/docs`, served under `/api` by the Vite proxy
    (`aitu-frontend/vite.config.ts` rewrites `/api` away). No change.
- `check-links.py`: 516 files, 2 broken, both in `05-checklist.md` (lines 47 and 70): the reports of Phases 5 and 9,
  not written yet. Not mine to fix; they pass once those phases end.

## Pending edits for shared files

**E1. `documentation/services/backend/endpoints.md`, the intro of section 1.** Replace
"except `GET /health` and
`POST /auth/login`." with "except `GET /health`, `POST /auth/login` and `POST /auth/logout` (the logout needs no session:
it ends the session the cookie names, if any)."

**E2. `endpoints.md`, the paragraph "The video reader's routers ...".** Replace "are not described on this page."
with "are described in the next section and in [lab.md](../../../context/frontend/lab.md)."

**E3. `endpoints.md`, insert before the heading `### 1.1 \`/auth\`: signing in`** this block:

```
#### The video reader's routes (the Lab, and the Video step)

`/video` (`api/video.py`, a user router) and `/frame-examples` (`api/frame_examples.py`, a master router). The Video
step uses `upload` and `read`; the Lab's pages use the rest. The pages are in [lab.md](../../../context/frontend/lab.md).

| Method and path | What |
|---|---|
| POST `/video/download` | `201`. One YouTube URL: the video and the audio of it. |
| POST `/video/upload` | `201`. A video file from the user's disk, as a project (see above). |
| GET `/video` | The user's own videos; every video for the master user. |
| GET `/video/{uuid}` | One video's metadata. |
| POST `/video/{uuid}/sample` | `202`, a job: the sampled frames. |
| GET `/video/{uuid}/frames/{index}` | One sampled frame, as a picture. |
| GET, PUT `/video/{uuid}/calibration` | The piano calibration of the video. |
| POST `/video/{uuid}/find` | The piano overlay from one rectangle. |
| POST `/video/{uuid}/measure` | `202`, a job: the scroll speed of the roll. |
| POST `/video/{uuid}/detect` | `202`, a job: the detector over every frame. |
| POST `/video/{uuid}/frames/{index}/detect` | The detector on one frame. |
| GET `/video/{uuid}/detection`, `GET /video/{uuid}/report` | What the detector found; its report. |
| POST `/video/{uuid}/read` | `202`, a job: **Read notes** (see above). |
| POST `/video/{uuid}/notes` | `202`, a job: stitch the roll and read the notes. |
| GET `/video/{uuid}/notes` | The notes read from the roll. |
| GET, PUT `/video/{uuid}/corrections` | The corrections of the notes. |
| POST `/video/{uuid}/events` | Writes the notes into the piece. |
| GET `/video/progress/{jobId}` | The progress of a job (a stream). `404` to anyone who did not start it, except the master user. |

`/frame-examples`: the master user only (`403` otherwise).

| Method and path | What |
|---|---|
| GET `/frame-examples` | The example set. |
| GET `/frame-examples/score` | The score board. |
| GET `/frame-examples/{slug}` | One example. |
| GET `/frame-examples/{slug}/image` | Its picture, at the working width. |
| PUT `/frame-examples/{slug}/calibration` | Its calibration. |
| POST `/frame-examples/{slug}/find` | Its piano overlay from one rectangle. |
| POST `/frame-examples/{slug}/geometry` | Its piano geometry. |
| PUT, DELETE `/frame-examples/{slug}/annotation` | Its manual annotation (`DELETE` takes `offsetPx`). |
| PATCH `/frame-examples/{slug}` | Sets `noRoll`. |
| POST `/frame-examples/{slug}/detect` | The detector on the example. |
```

**E4. `documentation/services/frontend/components.md`, the routes table of section 1.** After the row
`| (development only) | \`/dev/roll-bench\` | ...` add:
`| (development only) | \`/dev/ui\` | \`pages/dev/UiGalleryPage.tsx\`, lazy, only when \`import.meta.env.DEV\` |`

**E5. `components.md`, insert before the heading `## 2. The page of a project`** this section:

```
### 1.3 The Lab (the video reader)

The Lab's tabs and their order are in `LAB_TABS` (`layout/routes.ts`); the shell is `layout/LabLayout.tsx`. What
each tab does: [`context/frontend/lab.md`](../../../context/frontend/lab.md).

| File | What |
|---|---|
| `pages/video/VideoPlayerPage.tsx` | **Video**: the YouTube link, the sampling, the frames |
| `pages/video/VideoCalibrationPage.tsx` | **Calibration**: the piano on one frame, the scroll speed |
| `pages/video/VideoDetectionPage.tsx` | **Detection**: the detector over every frame |
| `pages/video/VideoNotesPage.tsx` | **Notes**: the stitched roll, the notes, the corrections, the write into the piece |
| `pages/video/ExamplesPage.tsx` | **Examples** and `examples/:slug`: the example set, the manual annotation, the score board |
| `components/video/` | `AnnotationEditor.tsx`, `CalibrationEditor.tsx`, `DetectionView.tsx`, `FrameCanvas.tsx`, `FramePlayer.tsx`, `NotesOnFrame.tsx`, `OffsetLine.tsx`, `PianoOverlay.tsx`, `PianoRect.tsx`, `ScoreBoardTable.tsx`, `TimeFrameLines.tsx`, `VideoBar.tsx`, `overlayColours.ts`, `videoSteps.ts` |
| `video/selectedVideo.ts` | The video the Lab's tabs share (read and written by the Video and Notes tabs) |
```

**E6. `context/00-index.md`, the frontend table.** After the row `| [frontend/pages.md](frontend/pages.md) | ...` add:
`| [frontend/lab.md](frontend/lab.md) | **The Lab**: the video reader's five tabs (Video, Calibration, Detection, Notes, Examples), the example set and its score board, the modules, who may open it |`

**E7. `context/frontend/projects.md` (owner Phase 14), the sentence at line 160-161** "stay in **Lab**, for the master
user." → `stay in **Lab** ([lab.md](lab.md)), for the master user.` (the link is relative to `projects.md`)

## Left for later phases

- Phase 20: `context/frontend/README.md` (the Lab row, line 32) and `aitu-frontend/README.md` (lines 12, 93, 100, 116):
  link to `lab.md` where they name the Lab.
- Phase 20: the glossary terms of section "New terms" above.
- Phase 20: `context/08-security.md` is already fixed; `context/00-project-complete-overview.md` (line 120) and
  `context/03-services-overview.md` (line 65) name the Lab in one line each, which is accurate.
