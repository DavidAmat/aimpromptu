> Context: [context/backend/api.md](../../../context/backend/api.md) ·
> [context/backend/time-model.md](../../../context/backend/time-model.md) ·
> [context/backend/piano-matrix-notation.md](../../../context/backend/piano-matrix-notation.md)

# Endpoints

FastAPI app: `aitu-backend/src/aitu_backend/main.py`, title "AImpromptu Backend API". One router per
product section, all of them listed in `api/__init__.py` as `ALL_ROUTERS`.

**The live authority on every field is `http://127.0.0.1:8765/docs`.** The generated OpenAPI page is
built from the same Pydantic models the handlers use, so it cannot drift. This file says what each
route is *for*, which decisions it obeys, and where the model lives. A schema dump does not say
those things.

Every request and response body is camelCase, produced by Pydantic aliases. CORS allows all origins
(`allow_origins=["*"]`) but without credentials (`allow_credentials=False`), so a page of another
origin can never send the session cookie. The page itself calls the backend as `/api` through the
Vite server, on its own origin, so the browser sends the cookie by itself.

**Every route needs a session** (implementation 02, Phase 4), except `GET /health` and
`POST /auth/login`. The session is the cookie `aitu_session` that `POST /auth/login` sets; its
properties and the reasons for them are in [`context/08-security.md`](../../../context/08-security.md).
`main.py` includes the routers in three groups (`api/__init__.py`):

| Group | Routers | Check before the handler (`auth/dependencies.py`) |
|---|---|---|
| `OPEN_ROUTERS` | `/auth` | None for `POST /auth/login` and `POST /auth/logout`; `GET /auth/me` and `PUT /auth/password` ask for the session themselves |
| `USER_ROUTERS` | `/audio`, `/library`, `/matrix`, `/passages`, `/pieces`, `/playlists`, `/projects`, `/public`, `/requests`, `/shares` and `/shared`, `/youtube`, `/time`, `/video` | `signed_in`, then `project_rights` |
| `MASTER_ROUTERS` | `/frame-examples`, `/admin` | `signed_in`, then `master_only` |

The answers of these checks:

- **401** `{"detail": "Sign in first."}`: no cookie, an unknown one, or an expired one. The page then
  opens the sign-in page.
- **404**: the route names a project by its path parameter (`audio_uuid`, the id of a part, or
  `project_id`) and the user may not read it. The answer is the same as for a project that does not
  exist, so an address tells nothing about another user's work.
- **403** "You can open this project but not change it.": the user may read the project but the
  request writes. A `GET` reads; every other method writes, except five `POST` routes that compute an
  answer and change nothing (`READ_ROUTES`): `/time/{uuid}/score`, `/time/{uuid}/ladder-preview`,
  `/pieces/{uuid}/hands/predict`, `/audio/{uuid}/trim` and `/projects/{id}/duplicate`.
- **403** "Only the master user can open this.": a route of `/frame-examples` or `/admin` asked by
  another user.

The rights table these checks apply is in [`context/08-security.md`](../../../context/08-security.md).
A route that names its project in the body instead of the path checks it itself
(`require_part`): `POST /matrix/transcribe` needs write on the part of its `audioUuid`, and `POST
/projects/compose` read on the part of every passage. The
functions below a route know the user of the request (`auth/context.py`), so a project or a job the
route makes belongs to that user (`db/users.py`, `current_user_id`).

Times read from the database (for example `createdAt` of a user) are returned in UTC with their
offset, because every time column has the `UTCDateTime` type (`db/models.py`). A browser therefore
shows them right in its own time zone.

**JSON answers are compressed.** `JsonGZipMiddleware` (`aitu_backend/compression.py`, implementation
08, Phase 2) compresses a JSON answer of 1 KB or more with gzip at level 5 when the client sends
`Accept-Encoding: gzip`. Audio files and the SSE progress stream are never compressed. The piano
sheet answer is about 11 times smaller this way (634 KB median, 56 KB sent). A `curl` without
`--compressed` receives plain JSON.

---

## 1. The whole surface in one table

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness: `{"status": "ok"}`. Open without a session. |
| **Signing in** | `api/auth.py` | |
| POST | `/auth/login` | Check the password, set the session cookie (implementation 02, Phase 4). Open without a session. |
| POST | `/auth/logout` | End the session. |
| GET | `/auth/me` | The signed-in user. |
| PUT | `/auth/password` | Change one's own password. |
| **Admin** | `api/admin.py` | Master user only |
| GET | `/admin/users` | Every user. |
| POST | `/admin/users` | Make a user with a first password. |
| PATCH | `/admin/users/{id}` | Disable or enable a user, reset a password. |
| **Audio** | `api/audio.py` | |
| GET | `/audio/` | Every ingested audio of the current user's projects. |
| POST | `/audio/upload` | Upload a file; ffmpeg normalises it. |
| POST | `/audio/recording` | Store a browser recording. |
| GET | `/audio/{uuid}` | One entry. |
| PATCH | `/audio/{uuid}` | Rename. |
| DELETE | `/audio/{uuid}` | Delete the project of this part, with its whole bundle. |
| POST | `/audio/{uuid}/add` | **Add audio**: another file at the end of the part's audio (implementation 02, Phase 5). |
| GET | `/audio/{uuid}/files` | The files of the part's audio in order: names, origin, place on the axis, cut frames. |
| PATCH | `/audio/{uuid}/files/{index}` | Name one file. |
| PUT | `/audio/{uuid}/files/order` | Put the files in a new order; each keeps its cuts. |
| DELETE | `/audio/{uuid}/files/{index}` | Take one file out (not the last one). |
| POST | `/audio/{uuid}/trim` | Persist a range as a new child audio, with lineage. Refused on a piece with cuts. |
| GET | `/audio/{uuid}/file` | Stream the audio of the piece (the edited audio once cuts are saved). |
| GET | `/audio/{uuid}/range` | Stream one range of `normalized.wav`. |
| GET | `/audio/{uuid}/waveform` | Min/max peaks for the waveform view, of the edited audio when there are cuts. |
| GET | `/audio/{uuid}/frames/peaks` | One min/max pair per 10 ms time frame of the original (implementation 08). |
| GET PUT | `/audio/{uuid}/cuts` | The selected region: the cuts and the frame table (implementation 08). |
| **Transcription** | `api/matrix.py` | |
| GET | `/matrix/engines` | The engines the page may offer. Only `muscriptor` now. |
| GET | `/matrix/engine` | The one engine: installed, device, loaded, waiting jobs, load error (implementation 08). |
| POST | `/matrix/transcribe` | Start MuScriptor; returns `202` and a job id. |
| GET | `/matrix/{uuid}/job` | The waiting or running transcription of a piece (implementation 08). |
| GET | `/matrix/progress/{jobId}` | SSE stream of any job: progress, live notes, `done`. |
| GET | `/matrix/jobs/{jobId}` | The same state, for pollers. |
| GET | `/matrix/{uuid}/events` | Every note the model reported, in seconds. Notes Falling (Play mode) draws it. |
| PUT | `/matrix/{uuid}/events/removed` | Mark notes as removed, by pitch and second. No page calls it since implementation 02, Phase 11. |
| **The flow page** | `api/pieces.py` | |
| GET | `/pieces/{uuid}/status` | Every step of the piece, its state, and the step it opens on (implementation 08). |
| GET | `/pieces/{uuid}/notes` | The live notes as columns, with the revisions (implementation 08). |
| PATCH | `/pieces/{uuid}/notes` | A list of operations on notes named by id (implementation 08). |
| POST | `/pieces/{uuid}/hands/predict` | The hand split as one hand per note. Writes nothing (implementation 08). |
| POST | `/pieces/{uuid}/hands/predict/job` | The same, as a job with progress (implementation 08). |
| **The score** | `api/time_score.py` | |
| GET | `/time/{uuid}/peaks` | Where the gaps between attacks gather into piles. |
| GET | `/time/{uuid}/default-reading` | The figure ladder a sheet is written from by default: the highest pile is a negra. |
| POST | `/time/{uuid}/ladder-preview` | Name one peak, see what every other becomes. |
| GET | `/time/{uuid}/score` | The drawable score payload. |
| POST | `/time/{uuid}/score` | The same, with the reader's page edits applied. |
| GET | `/time/{uuid}/trills` | Alternating runs, offered as suggestions. |
| PUT | `/time/{uuid}/hands` | Correct which hand plays a note. Written by note id since implementation 08. |
| PUT | `/time/{uuid}/removed` | Mark notes as removed from the page, by column and row. |
| PUT | `/time/{uuid}/notes` | Add notes to the recording, by column and row. |
| GET PUT | `/time/{uuid}/lyrics` | The song's words saved with the part (`project.json`), for the Lyrics tab (Phase 7). |
| POST | `/time/{uuid}/transpose` | Move every note of the part by a number of semitones; a preview counts, an undo is exact (Phase 7). |
| POST | `/time/{uuid}/paste` | Put a copied passage (notes, marks, audio) into the part at a moment, or over a stretch; everything after moves (Phase 8). |
| POST | `/time/{uuid}/versions/{n}/restore` | Put an earlier state of the part back: the undo and the redo of a paste (Phase 8) and of a promotion (Phase 9). |
| GET PUT DELETE | `/time/{uuid}/rhythm` | The saved reading. |
| **The new sheet** | `api/sheet.py` | Implementation 03, Phases 5 and 6 |
| GET | `/sheet/{uuid}?width=N` | The new sheet of a part drawn for a page `N` staff spaces wide: the SVG, the cursor map, the segments of Sonnet's windows and their state, and what the page may do with Sonnet (section 4.1). |
| POST | `/sheet/{uuid}/llm` | Start Sonnet on the part (or answer the run already going); follow `GET /matrix/progress/{jobId}`. |
| POST | `/sheet/{uuid}/hands` | Phase 6: give notes to one hand, in `notes.pmn` (one step of undo); the sheet drawn again (section 4.1). |
| POST | `/sheet/{uuid}/undo`, `/sheet/{uuid}/redo` | Phase 6: walk the part's steps back or forward; the sheet drawn again. |
| POST | `/sheet/{uuid}/reading` | Phase 7: one reading edit of the toolboxes (figure, finger, beam, grace note switch, ornament; armadura, clef, clef rules, octave line of a stretch); the sheet drawn again (section 4.1). |
| POST | `/sheet/{uuid}/remove` | Phase 7: take notes off the page (marked removed in `notes.pmn`, one step of undo); the sheet drawn again. |
| GET | `/sheet/{uuid}/stretch?start=A&end=B` | Phase 7: the armadura in force at a stretch and the one with the fewest signs over it. |
| POST | `/sheet/{uuid}/llm/stretch` | Phase 7: the AI writes a stretch again with the user's words, in the background; follow `GET /matrix/progress/{jobId}`. |
| POST | `/sheet/{uuid}/transpose` | Phase 8: Transpose notes, every note of the part and the sheet with them (one step of undo); `preview=true` stores nothing (section 4.1). |
| POST | `/sheet/{uuid}/add` | Phase 8: a note added on the keyboard panel, into `notes.pmn` (one step of undo). |
| GET | `/sheet/{uuid}/pages` | Phase 8: the sheet on paper, whole lines dealt onto pages (Print to PDF). |
| **Recording in Sheet** | `api/passages.py` | Implementation 02, Phase 9 |
| POST | `/passages` | **Record this passage**: a passage of a part (a stretch, or a moment for a new passage); its Current is made. |
| GET PATCH DELETE | `/passages/{id}` | The passage; the take on show, the speed, the window; discard it. |
| POST | `/passages/{id}/takes` | A recording (multipart `file`) kept as a new take. |
| DELETE | `/passages/{id}/takes/{take}` | Delete a take. |
| POST | `/passages/{id}/takes/{take}/read` | **Write the proposal**: keep a stretch of the take, transcribe it, split the hands, write its sheet (a job). |
| POST | `/passages/{id}/promotion` | What a promotion would do, without writing. |
| POST | `/passages/{id}/promote` | **Promote**: the take into the part in one write; the passage is closed. |
| **Projects** | `api/projects.py` | Implementation 02, Phase 5 (duplicate since Phase 3; library since Phase 6) |
| GET | `/projects` | The current user's projects, newest change first, with the step each reached. `?layer=` repeats. |
| POST | `/projects` | An empty project: no audio; with `scratch`, a blank sheet that opens on the Sheet step (From scratch, Phase 8). |
| POST | `/projects/import` | A `.aitu` file made into a new project of the Personal Vault. |
| GET | `/projects/{id}` | One project, as the list shows it. |
| PATCH | `/projects/{id}` | Rename. |
| DELETE | `/projects/{id}` | Delete, with its history, its temporary files and the audio no other project uses. |
| POST | `/projects/{id}/duplicate` | A copy in the Personal Vault, with new ids. |
| GET | `/projects/{id}/export` | The `.aitu` file: the bundle and the audio files it uses. |
| POST | `/projects/{id}/library` | **Save to library**: the project becomes a version of a song of the Private Library; or an edit copy replaces its version. |
| POST | `/projects/{id}/edit` | **Edit** a version of the Private Library: its copy in the Personal Vault. |
| POST | `/projects/compose` | **From other projects** (Phase 10): a new project made of passages of readable parts; a subheader join starts a new part. |
| GET, PUT | `/projects/{id}/parts` | The parts in order, with their subheader and length; put them in another order (Phase 10). |
| PATCH | `/projects/{id}/parts/{part}` | The subheader of a part. |
| POST | `/projects/{id}/parts/{part}/join` | The part joined to the one before it. |
| POST | `/projects/{id}/parts/{part}/split` | What follows `atMs` becomes a new part after it. |
| **Library** | `api/library.py` | Implementation 02, Phase 6: the user's Private Library |
| GET | `/library/songs` | The user's songs, with their artists and how many versions. |
| GET, PATCH, DELETE | `/library/songs/{id}` | One song with its versions; rename it or give it its artists; delete it with every version. |
| PATCH, DELETE | `/library/versions/{id}` | Rename a version; delete it with its project. |
| GET | `/library/versions/{id}/history` | The earlier states of a version. |
| POST | `/library/versions/{id}/history/{n}/restore` | Make an earlier state the version again. `409` when that state has no ready piano sheet (a version of the library always has one); the version is then unchanged and no history entry is added. |
| GET | `/library/artists` | The user's artists, each with every name it has. |
| GET, DELETE | `/library/artists/{id}` | One artist with its names and its songs; delete one with no song. |
| POST | `/library/artists/{id}/names` | Another name of the artist. |
| PATCH, DELETE | `/library/artists/{id}/names/{nameId}` | Rename a name or make it the default; remove a name. |
| POST | `/library/artists/{id}/merge` | Every name of this artist becomes a name of another one. |
| **Public library** | `api/public.py` | Implementation 02, Phase 13: the Public Library, read by every user ([§7.3](#73-public-the-public-library)) |
| GET | `/public/songs` | The public songs, searched, filtered (decade, region, genre, tag), sorted and paged, with the count of each filter value. |
| GET | `/public/songs/{id}` | One public song: metadata, chart history, fixed versions, Other versions by user. |
| GET | `/public/songs/{id}/lyrics` | Its words. |
| POST | `/public/songs/{id}/pull` | **Add to my library** with the chosen versions. |
| GET | `/public/artists`, `/public/artists/{id}` | The public artists, searched and sorted; one with its songs and albums. |
| POST | `/public/artists/{id}/pull` | **Add to my library**: its songs that have a version. |
| GET | `/public/playlists`, `/public/playlists/{id}` | The public songs playlists; one with its songs. |
| POST | `/public/playlists/{id}/pull` | **Add to my library**: a songs playlist of the user's own. |
| PUT, DELETE | `/public/likes/{project}` | Like a public version, or take the like back. |
| GET | `/public/suggest` | The most popular matching songs and artists (Save to library, Search). |
| GET | `/public/lists` | The genres, regions and tag categories a request can give a song (Phase 14). |
| **Requests** | `api/requests.py` | Implementation 02, Phase 14: requests to the Public Library ([§7.4](#74-requests-requests-to-the-public-library)) |
| GET, POST | `/requests` | The user's requests; send one (its kind in the body). |
| GET | `/requests/counts` | The numbers beside **Requests** and **Review** in the sidebar. |
| GET | `/requests/publish-info`, `/requests/playlist-info` | What the **Publish** dialog starts from, for a version or a playlist of My library. |
| GET, PUT | `/requests/{id}` | One request, for its author and the master user; send it again after changes were asked. |
| POST | `/requests/{id}/withdraw` | Withdraw a request not reviewed yet. |
| POST | `/requests/{id}/comments` | A comment: on the request, a reply, or on a stretch of the proposed sheet. |
| GET | `/admin/requests` | **Review** (master user): the open requests, oldest first, or every one. |
| POST | `/admin/requests/{id}/decision` | A decision for every waiting item; what is accepted is published in one transaction. |
| **Sharing** | `api/shares.py` | Implementation 02, Phase 14: a Private Library shared read only ([§7.5](#75-shares-and-shared-a-shared-library)) |
| GET | `/shares` | The other users, who the user shares with, and who shares with the user. |
| PUT, DELETE | `/shares/{userId}` | Share the whole library with a user, or stop. |
| GET | `/shared/{ownerId}/songs`, `/shared/songs/{id}` | The songs of a library shared with the user; one with its versions. |
| POST | `/shared/songs/{id}/pull` | **Add to my library**: the chosen versions, copied. |
| **Playlists** | `api/playlists.py` | Implementation 02, Phase 10: the songs playlists of the Private Library |
| GET, POST | `/playlists` | The user's playlists; a new one, empty or with songs. |
| GET, PATCH, DELETE | `/playlists/{id}` | One playlist with its songs; rename it or put its songs in another order; delete it. |
| POST | `/playlists/{id}/items` | Songs added at the end. |
| PATCH, DELETE | `/playlists/{id}/items/{item}` | Another version or a stretch of the song; take it out. |
| **YouTube** | `api/youtube.py` | |
| POST | `/youtube/probe` | Title and length, without downloading. |
| POST | `/youtube/download` | Download the audio as mp3, in the request. |
| POST | `/youtube/jobs` | The same download as a job; returns `202` and a job id (implementation 08). |
| POST | `/youtube/batch` | Queue several. |
The text-notation MVP routes (`GET /scores`, `POST /sequence`) were deleted in implementation 02,
Phase 1. See [§9](#9-the-text-notation-mvp-routes). The old Piano Library router (`/library`) was
deleted in Phase 3; `/library` is the Private Library since Phase 6 ([§7.1](#71-library-the-private-library)).

The video reader's routers (`/video` in `api/video.py`, `/frame-examples` in
`api/frame_examples.py`, implementations 04 to 07) are not described on this page. Their reasoning
is in `context/implementations/01-mvp/04-synthesia-to-notes/` and `05-piano-overlay-from-black-keys/`.
Since implementation 02, Phase 4 their access is this: `/frame-examples` (Lab) answers only the
master user (`403` otherwise). `/video` checks the rights of the project of its `audio_uuid` like
the other routers; `GET /video` lists the user's own videos, and every video for the master user;
`GET /video/progress/{jobId}` answers `404` to a user who did not start the job, except the master
user.

Two `/video` routes serve the **Video step of a project** (implementation 02, Phase 5, plan section
10.2), for every user:

- `POST /video/upload` (multipart `file`, `.mp4 .mov .m4v .webm .mkv`) makes a project from a video
  file on the user's disk, as `POST /video/download` does from a YouTube link: the audio is taken
  out with ffmpeg and stored like an upload, and the video becomes a temporary file of the part
  (`tmp/<userId>/<partId>/video/source.mp4`). Answers `201` with the video's metadata, whose
  `audioUuid` is the part; `422` for another kind of file.
- `POST /video/{uuid}/read` is **Read notes**: one job (`202`, follow it on
  `GET /video/progress/{jobId}`) that samples the frames when there are none, measures the roll
  when it was never measured for this piano overlay, stitches the video, reads the notes and writes
  them into the part (`plate`, `follow`, `stitch`, `notes`, `shapes`, `write` stages). Its key is
  `video-read:<uuid>`, so a second press joins the running job and the Notes step shows it running.
  `409` when the piano is not fitted. A video whose scroll speed is not stable ends with an error
  that says so (V-06).

`PUT /video/{uuid}/calibration` also keeps `measuredFor`, the overlay the stored measurement was
made with, so **Read notes** measures again only after the piano was fitted again.

### 1.1 `/auth`: signing in

`api/auth.py`, plan section 9.2. The session itself (the cookie, its lifetime, the slow-down after
wrong passwords) is described in [`context/08-security.md`](../../../context/08-security.md); the
code is in `aitu_backend/auth/` (`sessions.py`, `passwords.py`, `throttle.py`).

| Route | Body | Answer |
|---|---|---|
| `POST /auth/login` | `{username, password}` | `200` `{id, username, role, isMaster}` and the cookie `aitu_session` (`HttpOnly`, `SameSite=Lax`, not `Secure`, 30 days, renewed on use). `401` "The username or the password is wrong." |
| `POST /auth/logout` | none | `204`. The session is deleted and the cookie removed. |
| `GET /auth/me` | none | `200` `{id, username, role, isMaster}`; `401` without a session. The page asks it when it opens. |
| `PUT /auth/password` | `{current, new}` | `204`. `403` when `current` is wrong; `422` when `new` is shorter than 8 characters. Every other session of the user ends; the current one stays. |

- `POST /auth/login` gives the same `401` for an unknown username, a wrong password and a disabled
  user, so the answer does not say which usernames exist. The username is compared without case.
- **The slow-down.** After five wrong passwords for one username within a minute, each next try
  waits before the password is checked: 2 s, then 3 s, and so on, at most 10 s. A correct password
  clears the count. The count is in memory, so a restart clears it too.
- `role` is `master` or `user`; `isMaster` is true for the master user.

### 1.2 `/admin`: the users

`api/admin.py`, plan section 9.1. The whole router answers only the master user (`403` "Only the
master user can open this." otherwise). It is the backend of **Admin → Users**, and of **Admin →
Review** (Phase 14, [§7.4](#74-requests-requests-to-the-public-library)).

| Route | Body | Answer |
|---|---|---|
| `GET /admin/users` | none | Every user, by id: `[{id, username, role, disabled, createdAt, hasPassword}]`. `hasPassword` is false for the master user until `AITU_MASTER_PASSWORD` gives it one. |
| `POST /admin/users` | `{username, password}` | `201` and the user. `409` when the username is taken (without case). `422` for a username that is not 2 to 32 letters, digits, `.`, `_` or `-`, or a password under 8 characters. |
| `PATCH /admin/users/{id}` | `{disabled?, password?}` | `200` and the user. `404` for an unknown id. `422` for a short password, or to disable the master user. |

Disabling a user and resetting a password both end every session of that user at once. A new user
signs in with the first password and changes it from the user menu (`PUT /auth/password`).

---

## 2. `/audio`: the working store

One project with one part per ingested audio, whatever the source. Since implementation 02, Phase 3
the uuid of these routes is the id of the **part** (plan P-6), and a project made by this app has
the id of its first part, so the two are the same uuid. The bundle and the audio store are described
in [`paths-and-data.md`](paths-and-data.md). Upload, browser recording and YouTube all
converge on `audio/ingest.py`, so the rest of the system never asks where a recording came from.

`POST /audio/upload` accepts `.mp3 .aac .m4a .wav .webm .ogg`. Browser recordings arrive as webm or
ogg because Chrome records nothing else, and ffmpeg converts them on the server. **Without `ffmpeg`
on `PATH` this route answers `503`** with that instruction rather than failing obscurely.

`POST /audio/{uuid}/trim` writes a **physical** child audio with absolute lineage back to its root
source, rather than remembering a range. A named segment survives the parent being deleted and can
itself be trimmed again. A piece with cuts is refused with `422`, because the seconds of the range
selector are those of the piece and the file's are not: such a piece is cut on the Audio tab of the
flow page instead.

`POST /audio/{uuid}/add` (multipart `file`, the formats of the upload) is **add audio**
(implementation 02, Phase 5): the file is stored once by its content, normalized to its own 16 kHz
copy and measured, and appended to the part's timeline. The Audio step then shows the files end to
end (the **axis**), the cuts keep their frames, and `audioRevision` goes up by one, so the notes are
stale. `422` for a file ffmpeg cannot read (its bytes are not kept), `409` for a part with no audio
yet. A part of several files plays a joined FLAC as its original (`?original=true`), and its
`normalized.wav` is the files' 16 kHz copies joined, so every other route works on the axis
unchanged ([`paths-and-data.md`](paths-and-data.md) §3).

**The files of the audio** (the Source step, Phase 5). `POST /audio/{uuid}/add` takes an optional
form field `name`. `GET /audio/{uuid}/files` answers `{audioRevision, files}` (the fields of the
`files` of the cuts answer). `PATCH /audio/{uuid}/files/{index}`, body `{name}` (1 to 200
characters), names a file and changes nothing else. `PUT /audio/{uuid}/files/order`, body
`{order, baseRevision}` where `order` lists the current places in the new order (`[2, 0, 1]` puts
the third file first): each file keeps its cuts. `DELETE /audio/{uuid}/files/{index}?baseRevision=`
takes a file out; the last one stays (`422`), and so does a file whose removal would leave only cut
audio. Both raise `audioRevision`, so the notes become stale; a stale `baseRevision` answers `409`,
an unknown index `404`. A YouTube link is added to a part with `POST /youtube/jobs`, body
`{url, appendTo: <uuid>}` (the rights of that part are checked, `404` for another user's): the job
adds the audio at the end, named after the video, instead of making a project.

`GET /audio/` lists only the parts of the current user's own projects, in the Personal Vault and
the Private Library (since implementation 02, Phase 4). `GET /audio/` and `GET /audio/{uuid}` answer
the `AudioMetadata` shape. Since Phase 3 there is no
`metadata.json`: `audio/store.py` builds that shape from `project.json` and `timeline.json`. The
routes add computed fields: `hasNotes`, `hasVideo` (the part has a video: its Audio step is the
Video step, Phase 5), `projectId`, `layer` and `basedOn` (the part's project, its layer, and the
library project an edit copy edits: a part of the Private Library opens read only, Phase 6),
`needsRederivation`, `originalDurationSeconds`, and `updatedAt` (the newest modification time of the
part's files and of `project.json`, one `stat` per file; the Projects page sorts by it and shows
it; added in implementation 02, Phase 1). Once cuts are saved, `durationSeconds` is the
length of the piece (the original minus the cuts) and `originalDurationSeconds` keeps the length of
the untouched file.

### 2.1 GET and PUT /audio/{uuid}/cuts

Before implementation 08, the only way to remove part of a recording was **Create segment**, which
copies the audio. The flow page needed a selected region that a reader can change and restore, and
that maps directly onto the notes. A cut is therefore a range of 10 ms time frames of the original
audio, `[startFrame, endFrame)`. Since implementation 02, Phase 3 a cut is stored as the gap
between two segments of the part's `timeline.json`. The piece is every frame that no cut
deletes. The model is in `audio/frames.py` (`FrameTable`, `normalize_cuts`, `join_kept`).

The answer of both methods (`CutsResponse`):

| Field | Meaning |
|---|---|
| `audioUuid` | |
| `audioRevision` | Rises by one each time the cuts change. Notes made from another revision are stale. |
| `frameMs` | Always `10`: one time frame, 160 samples of the 16 kHz `normalized.wav`. |
| `totalFrames` | Frames of the original audio. |
| `pieceFrames` | Frames of the piece, once the cuts are removed. |
| `cuts` | Sorted `[startFrame, endFrame)` pairs of the original. |
| `kept` | The frame table: one row per kept range, `{pieceStart, originalStart, length}` in frames. |
| `notesStale` | True when the stored notes were transcribed from other cuts. |
| `files` | The files of the audio laid end to end, in order (Phase 5): `{index, name, kind, originalFilename, url, startFrame, frames, cutFrames}` each. One entry for most parts; several after **add audio**. |

`PUT` body: `{ "cuts": [[start, end], ...], "baseRevision": n }`. `baseRevision` is optional.

- The cuts are sorted, clipped to the audio and merged where they overlap or touch.
- `audioRevision` rises only when the cuts really change, so saving the same cuts twice does not make
  the notes stale (`store.set_cuts`).
- `409` when `baseRevision` is not the stored revision, so a page never writes over a newer
  selection. `422` when the cuts would delete the whole audio. `409` from both methods when the audio
  has no `normalized.wav` yet.
- A change writes the edited audio, `piece-r<N>.flac` and `piece-r<N>.wav`
  ([`paths-and-data.md`](paths-and-data.md#41-cachepartid-derived-files)), and
  deletes the cached `waveform.json`. `500` when ffmpeg cannot write the edited audio.
- The route does **not** start a transcription. It makes the stored notes stale. The next
  `POST /matrix/transcribe` then transcribes again without `force`, and the old notes are copied to
  `.database/history/<projectId>/parts/<partId>/vN/` first.

### 2.2 GET /audio/{uuid}/file

The audio of the piece, for every player. Two query flags, both `false` by default:

| Piece | No flag | `normalized=true` | `original=true` |
|---|---|---|---|
| No cuts, a WAV or FLAC | The file the user gave (the stored file) | `normalized.wav` | The stored file |
| No cuts, a compressed file (MP3, M4A, a recording) | `listen-<stored name>.flac`, a lossless copy of it | `normalized.wav` | The stored file |
| With cuts | `piece-r<N>.flac` | `piece-r<N>.wav` | The stored file |

The stored file is `.database/audio/<sha256>.<ext>`, named by its content; the download keeps the
name of the file the user gave. `normalized.wav`, `piece-r<N>.*` and `listen-*.flac` are in the part's `cache/`
folder. The lossless copy exists because an `<audio>` element jumps inside an MP3 by guessing the byte of a time:
on a file of variable bitrate a jump landed up to about 0.6 s away from the time the player reported, and the music
no longer matched the notes until the next jump (measured in Chromium, 2026-10-25; `piece_audio.listen_copy`).

Until Phase 6 every player played the untouched original, so on a cut piece the audio ran ahead of
the notes by the length of the cuts before the playhead. The user's rule (2026-09-29) is that once
the cuts are saved, the edited audio is the audio of the piece. Only the Audio tab asks for
`original=true`, because it draws the cuts on the original so a reader can restore one. A missing
edited file is written on the first request (`audio/piece_audio.py`, `ensure`).

Every answer of this route carries `Cache-Control: no-cache`, because the same address serves other
bytes after the cuts change. `GET /audio/{uuid}/range` and the range edit still read
`normalized.wav` in the time of the original.

### 2.3 GET /audio/{uuid}/frames/peaks

The waveform of the Audio tab. A cut snaps to one 10 ms frame, so the tab needs the waveform at that
step for every zoom level. One pair of values per frame for the whole audio is only 2 bytes per
frame, so the route sends all of it at once and the page draws every zoom from memory.

| Field | Meaning |
|---|---|
| `audioUuid` | |
| `frameMs` | `10` |
| `totalFrames` | Frames of the original audio: the same count as `GET /audio/{uuid}/cuts`. |
| `peak` | The loudest sample of the audio, 0 to 1. The values below are scaled so that it is 127. |
| `min`, `max` | Base64 of one signed byte per frame: the lowest and the highest sample of that frame. |

It reads `normalized.wav` (the original, not the piece), so frame `f` here is frame `f` of a cut.
`409` when there is no `normalized.wav` or when it is not 16 kHz. There is no cache. On Superestrella
(18,917 frames) the answer is 50.6 KB of JSON, 35 KB sent, in 8 to 30 ms.

---

<a id="3-matrix--running-the-model"></a>

## 3. `/matrix`: running the model

Before implementation 08, these routes let the reader choose ByteDance or Transkun, ran one job per
request with a new model each time, and reported progress only. Now there is one engine, MuScriptor,
loaded once, with one transcription at a time on the GPU, and the progress stream also carries the
notes as they are heard. The engine itself is described in
[`transcription-pipeline.md`](transcription-pipeline.md#engines).

**Nothing here returns a grid.** A grid is a view of the recorded notes at a chosen frame length, so
it is built while the request is answered and served from `/time` instead.

### 3.1 GET /matrix/engines and GET /matrix/engine

`GET /matrix/engines` returns `{engine: bool}` for the engines the page may offer. It now lists only
`{"muscriptor": true}`; `false` means the `muscriptor` extra is not installed. With one entry the
Input page shows no engine choice.

`GET /matrix/engine` is the startup check of the one engine:

```json
{"name": "muscriptor", "installed": true, "device": "cuda",
 "loaded": ["muscriptor-large (cuda, float16)"], "waiting": 0, "error": null}
```

`device` is `AITU_DEVICE`. `loaded` is what the model registry (`transcription/models.py`) holds.
`waiting` counts the transcriptions queued behind the running one. `error` says, in plain words, why
the preload failed (a missing Hugging Face token or licence, for example). When a transcription ends
at once with no notes, check this route first: a container can lose its GPU after the host's service
manager reloads (Phase 7 report, 6.3).

### 3.2 POST /matrix/transcribe

```json
{ "audioUuid": "…", "frameMs": 40, "startSeconds": null,
  "endSeconds": null, "engine": "muscriptor", "force": false }
```

There is one number in that body and it is a length of time. It does not decide what any note is
called: the figures are chosen afterwards, from a ladder the reader names (D-01, D-09). Here
`frameMs` only says which hand split to prepare in the cache after the save.

- **The engine is forced.** `engine` is kept for older clients and defaults to `muscriptor`. Any
  other value answers `422`: "Unknown transcription engine" for a name that does not exist, and a
  message saying the engine is kept in the code but cannot be chosen for `bytedance`, `transkun`,
  `basic-pitch` and `silent`. A missing audio answers `404` before that check.
- **When the model runs.** It runs when `force` is true, when a range is given, or when the piece
  has no current notes (no `notes.pmn`, or notes made from another `audioRevision`). Otherwise the
  job reads the stored notes, prepares the split and ends: `force` is needed only to replace current
  notes.
- **The GPU queue.** A job that runs the model goes into the GPU queue of `transcription/jobs.py`:
  one worker thread, in order of arrival. While another transcription runs, the job's status is
  `waiting` and its stream sends a `waiting` stage ("Waiting for 1 other transcription to finish").
  **Write the proposal** of a take (`POST /passages/{id}/takes/{take}/read`, Phase 9) uses the
  same queue.
- **One job per piece.** The job carries the key `transcribe:<uuid>`. While a job of the same user
  with that key is waiting or running, this route returns that job instead of starting a second one,
  so a double click or a second browser tab cannot transcribe the same piece twice.
- **A range** (`startSeconds` and `endSeconds`) is the older path: the WAV is sliced first and the
  cuts are not applied.
- **Rights.** The part is named in the body, so the route checks it itself: a part the user may not
  read answers `404`, one they may read but not write answers `403`. The job runs as the user who
  started it.

Answers `202` with `{ "jobId", "status" }`, where `status` is usually `running` or `waiting`. A full
transcription of Superestrella (189 s) takes about 25 s on the RTX 4090.

### 3.3 GET /matrix/{uuid}/job

`{ "jobId", "status" }` of the transcription of this piece that is waiting or running, or `404` when
there is none. A page that is opened or reloaded during a transcription uses it to find the stream
again, then reads every frame from the start.

### 3.4 GET /matrix/progress/{jobId}

A Server-Sent Events stream (`text/event-stream`, `Cache-Control: no-cache`,
`X-Accel-Buffering: no`) of **any** job of `transcription/jobs.py`: a transcription, a YouTube job
(`POST /youtube/jobs`) or a hand prediction (`POST /pieces/{uuid}/hands/predict/job`). It has three
kinds of frame.

**Progress frames** have no event name:
`{stage, current, total, fraction, message, timestamp}`. A MuScriptor transcription reports the
stages `waiting` (only when queued), `transcribe` (one step per 5-second chunk, message
`chunk n/total`) and `timing` (the lag measurement, message `lag correction +15 ms`).

**`event: chunk` frames** carry the live notes of a MuScriptor transcription (`transcription/live.py`):

```json
{"type": "chunk", "done": 3, "total": 38, "upToMs": 15000, "durationMs": 189160,
 "open":   {"id": [41, 42], "key": [40, 52], "onMs": [14210, 14800]},
 "closed": {"id": [30, 31], "key": [39, 44], "onMs": [9900, 11000], "lenMs": [1200, 800]}}
```

- One frame is sent when a chunk ends (`done` counts whole chunks), at most every 0.25 s inside a
  chunk when a note started or ended, and once more at the end for the notes MuScriptor closes after
  its last chunk.
- `closed` holds only the rectangles that ended since the previous frame. `open` holds every
  rectangle still sounding, which the page draws up to `upToMs`.
- The ids are the ids of the saved notes. The times are whole milliseconds of the piece, **before**
  the lag correction, which is known only at the end. The page reads the saved notes after `done`.
- An `EventSource` that listens only to unnamed frames never receives these, because a named event
  goes only to a listener of that name.

**The final frame** is `event: done`: `{type: "done", status, error, ...}` with `status` `done` or
`error`. Each kind of job adds its own fields:

| Job | Extra fields of `done` |
|---|---|
| Transcription | `audioUuid`, `revision` (the new `notesRevision`), `lagCorrectionMs`, `noteCount` |
| YouTube download | `audioUuid`, `alias`, `durationSeconds` |
| Hand prediction | every field of the `POST /pieces/{uuid}/hands/predict` answer |

**Reconnection.** Every frame except the final `done` carries an SSE `id:`, which is its index in the
job's list of frames. A reader that connects late first receives every frame already sent, in order,
then the new ones; each reader keeps its own position, so two tabs never take frames from each
other. A reconnecting `EventSource` sends `Last-Event-ID` and resumes after that frame. A comment
line (`: keep-alive`) is sent after 15 s with no frame. An unknown job id answers one `event: error`
frame and a `done` frame with `status: "error"`.

**The owner of a job.** Since implementation 02, Phase 4 every job records the user who started it
(`owner_id` in `transcription/jobs.py`) and runs as that user, so a project it makes is theirs. This
stream, `GET /matrix/jobs/{jobId}` and `GET /video/progress/{jobId}` answer `404` to any other user,
as for an unknown job; the master user can follow every job.

Jobs live in memory: the last 50 finished jobs are remembered, and a restart of the backend (also
any `--reload`) loses them. The notes themselves are on disk.

### 3.5 GET /matrix/jobs/{jobId}

`{jobId, status, error, stage, fraction}` from the last progress frame, for clients that cannot hold
an SSE connection. `status` is `waiting`, `running`, `done` or `error`. `404` for an unknown job,
and for a job another user started (except for the master user).

### 3.6 GET /matrix/{uuid}/events

Every note the model reported, in seconds, with the discards **marked rather than removed**. The
artifact filter is applied here only as a label, because the point of the route is to show what the
rest of the system chose not to use: a filter that can be checked instead of taken on trust. On a
`muscriptor-*` piece no filter runs in the hand split, so no note is labelled (`artifactCount: 0`).

Each event carries:

- `id`, the stable note id of `notes.pmn`, which `PATCH /pieces/{uuid}/notes` names it by;
- `hand`: the saved hand, or `null` (since implementation 03, Phase 5 the hand split is no longer shown before
  Sonnet decides the hands: a new transcription plays in Notes Falling without hand colours; `frameMs` is kept
  for the pages that send it);
- `removed`, `artifact`, `octaveBelow`.

The answer also carries `revision` and `handsRevision`, which a page needs to send a `PATCH`.
`409` when the piece has no `notes.pmn`.

**Notes Falling**, a view of Play mode, draws this. The Playground's Piano Roll page, which also drew it, was removed in
Phase 9: the Notes and Hands tabs of the flow page replace it, and they read
`GET /pieces/{uuid}/notes` instead.

### 3.7 PUT /matrix/{uuid}/events/removed

Marks notes as removed from the recording, addressed by pitch and start second (`midiNote`, `start`,
matched to 4 decimals). `removed: false` restores them. `removed` is a flag on the note event, so
nothing is deleted and restoring a note returns it exactly as it was. Answers `{changed, unmatched}`.

There are **two** routes that write this flag, and that is deliberate: the two screens genuinely
held different things. Notes Falling knew raw seconds; a reader on the sheet has clicked a notehead
and knows a column and a row, which is `PUT /time/{uuid}/removed`. Same field, same consequences.
Since implementation 02, Phase 11 Notes Falling is a view of Play mode that only plays, so only the
sheet's route is called; this one stays, with its tests.

Removing a note is not a filter on one screen. A note's printed length is the gap to the next onset
in the same hand (D-14), so removing one **renames its neighbour**. That is why it is written onto
the recording rather than drawn over.

Since implementation 08 the write goes through `pipeline.save_edit`: `notesRevision` and
`handsRevision` rise by one, and a saved piano sheet becomes stale, because this page is not the
sheet.

---

<a id="4-time--the-wall-clock-score"></a>

## 4. `/time`: the wall-clock score

Everything here is derived from the stored notes (`notes.pmn`), so reading a piece at 20 ms instead of 40
is a different query string rather than a migration. One thing is kept in memory: the hand split of
each piece, in the shared split cache (`transcription/split_cache.py`), keyed by the uuid, `frameMs`
and the modification time of `notes.pmn` in nanoseconds. Any save of `notes.pmn` is a new key, so
an old split is never served. When every placed note has a saved hand, the split is painted from
those hands in a few milliseconds instead of running the inference (D-31, changed in implementation
08, Phase 5).

### GET /time/{uuid}/peaks

| Query | Default | Meaning |
|---|---|---|
| `hand` | `right` | `right`, `left` or `both`. |
| `frameMs` | 40 | |
| `startSeconds` | 0 | Measure a stretch rather than the piece. |
| `endSeconds` | none | |

Returns the piles of gaps between attacks, each with its centre, median, mean, count, share and
edges, plus `attackCount`, `gapCount` and an optional plain-language `warning`.

Measured on the **raw recorded times, never on the columns** (D-07). Snapping first splits every
pile in two: a real 337 ms gap becomes 8 or 9 frames depending on phase, so one clean spike holding
half the data becomes two half-height spikes and the reader is asked to name a peak nobody played.

Each hand is measured on its own, because the gap between a right-hand run and a held left-hand
chord is not a rhythm and would hide the peak that matters.

### GET /time/{uuid}/default-reading

| Query | Default | Meaning |
|---|---|---|
| `hand` | `right` | The hand whose gaps are measured (the saved reading's hand, when there is one). |
| `frameMs` | 40 | |

Returns `{audioUuid, hand, frameMs, anchorFigure, anchorMs, centreMs, attackCount, gapCount,
endSeconds}`. `anchorFigure` is always `negra` and `anchorMs` is the median gap of the pile holding
the most gaps (`matrix/ladder.py::default_anchor`): D-09 as changed by implementation 02, Phase 2.
When the hand asked for has no pile, both hands are measured and `hand` says `both`. `anchorMs` is
`null` for a piece with no gaps (nothing played yet, or one chord), which is not an error. `404` for
an unknown audio, `409` when it has no notes. The Sheet step calls it on every visit and draws the
sheet from it; the saved reading's `anchorFigure`, when there is one, replaces the negra.

### POST /time/{uuid}/ladder-preview

```json
{ "anchorFigure": "negra", "anchorMs": 480, "hand": "right",
  "frameMs": 40, "startSeconds": 0, "endSeconds": null }
```

Returns the resulting `FigureLadder`, a `headerLabel` such as `negra = 480 ms · ≈125 BPM`, the
equivalent `bpm`, and every detected peak labelled under that ladder with how far off it fits.

This exists because the app never chooses the ladder (D-09) and the reader has to be able to judge
a choice before committing to it (D-10). A pile at a third of the **negra** is named
`corchea de tresillo` rather than a 33 %-wrong corchea (D-32).

### GET /time/{uuid}/score

| Query | Default | Meaning |
|---|---|---|
| `anchorFigure` | `negra` | |
| `anchorMs` | **required** | |
| `frameMs` | 40 | |
| `boundaries` | `""` | Passage boundaries as frame numbers, e.g. `250,900`. |
| `boundaryMs` | `""` | One anchor per passage: **one more value than boundaries**. |

Returns a `TimeScorePayload`: the two hand matrices, the passages, every printed note with its
figure already chosen, and the layout hints. Field detail in
[`time-matrix.md`](time-matrix.md#29-timescorepayload).

A mismatched count of boundaries and anchors is a `422` that says both numbers.

Both score routes encode the payload once (`_json`, a `Response` with `model_dump_json`) instead of
letting FastAPI validate every cell a second time. `response_model` stays on the decorators for the
documentation (Phase 2).

### POST /time/{uuid}/score

The same answer, with the reader's page edits applied **before any figure is named**. Body adds
`hiddenNotes` and `trills` to the query parameters above, and `dropDecorative`. `transpose`
(semitones, -87 to 87, default 0) draws the sheet as if every note were moved, writing nothing: the
preview of a notes transposition (implementation 02, Phase 7). The notes are moved by
`notation/transpose.py` and split by `pipeline.split_events`, the way `split_of` splits stored
notes, without the cache; `hiddenNotes` and `trills` are then addressed on the moved keys.

The edits have to be applied on this side rather than in the browser for one reason: hiding a note
changes the gap to its neighbour, and therefore that neighbour's printed figure. An overlay drawn
after the figures were chosen would show the right noteheads with the wrong names.

Each pass works on `_editable_copy`, which copies only the two hand grids and shares everything else
with the cached split. A deep copy of the whole split used to be about two thirds of a request with
decorative notes removed, which copies once per pass (Phase 8).

### GET /time/{uuid}/trills

`frameMs`, and `minPairRepeats` (2–20, default 3). Returns stretches where two notes a whole tone or
less apart trade places at least three times, evenly, under 300 ms, measured on the raw attack times
per hand.

**A suggestion and nothing more.** Nothing is written and the sheet does not change until the reader
accepts one: a missed trill costs a reader nothing, and a wrong one hides notes that were really
played, so the reader has the last word.

### PUT /time/{uuid}/hands

Which hand plays a note is a fact about the *playing*, not about the page: it survives a change of
column length and it decides the printed length of its neighbours. So it is written onto the note
event rather than stored as an annotation, and everything downstream follows without coordinating.

Body: `{ "frameMs": 40, "notes": [{ "startFrame", "row", "hand": "right" | "left" }] }`. Answers
`{assigned, unmatched}`.

Since implementation 08, Phase 5, the route is light, because a reader moves hands often:

1. The cell (`startFrame`, `row`) is resolved to a **note id** in the cached split the page already
   shows (`build.event_ids`). No hand split runs because of the request.
2. When the piece has no saved hands yet, the first change first saves the hand of every live note
   as that split draws it, then applies the change. The page looks the same, and from then on the
   sheet is painted from the saved hands.
3. The hand is written onto the note by id, and `hand_guessed` is cleared.
4. `pipeline.save_edit` raises `handsRevision`. The page that made the change already draws it, so a
   saved reading that was current moves forward with it and stays current (`sheet_follows`).

Measured on Superestrella: 8 to 12 ms for the `PUT` and 33 to 36 ms for the sheet request after it,
where it used to cost a new hand split (1.1 to 1.5 s).

### PUT /time/{uuid}/removed and PUT /time/{uuid}/notes

`PUT /time/{uuid}/removed` addresses notes by column and row. Restoring one cannot be resolved
against the current matrix (the note is not in it, which is what removed means), so a restore builds
its lookup from a split with every removal undone, which is the numbering the columns were recorded
with. One extra split, paid only on an undo.

`PUT /time/{uuid}/notes` is its opposite, and writes to the same place for the same reason. A reader
looking at the keyboard panel can see a note missing from a chord. Drawing an extra notehead beside
the score would be the wrong fix twice. First, the printed length of a note is the gap to the next
onset in the same hand, so a note that appears from nowhere renames its neighbour. Second, Notes
Falling and playback would continue to disagree with the page.

The times are the column's own: a note added at f120 starts 120 column-lengths into the piece. That
is only ever a few milliseconds from where a played note would have landed, and the whole page is
drawn on that grid anyway. The hand travels with it, pinned the way a corrected hand is. A key
already struck in that column is **refused and counted** rather than merged, because the matrix
rejects a frame where both hands hold one key and merging would lose a note.

`PUT /time/{uuid}/notes` answers `{"added": n, "duplicate": n}`; `PUT /time/{uuid}/removed` answers
`{changed, unmatched}`. Both go through `pipeline.save_edit` with `sheet_follows`, like the hand
route.

### POST /time/{uuid}/transpose

**Transpose → Notes** of the sheet toolbox (implementation 02, Phase 7, plan section 11.4). Body:
`{"semitones": 2, "preview": false, "hold": [], "restore": []}`. Every note of the part (the ones
taken off the page too) moves by `semitones`; no time moves, so every mark keyed by a column stays
on its music, and each note keeps its hand. A note that would leave the 88 keys is **taken off**
(`removed`) and stays on its key. Answers `{moved, outside, held, takenOff, putBack}`: the notes on
the page that moved, the ones taken off, and the ids an undo needs. `preview` counts and writes
nothing.

**The undo is the same route**: the opposite `semitones`, `hold` set to the answer's `held` (those
notes stay where they are) and `restore` to its `takenOff` (those are put back on the page). Every
note is then as it was, note for note (`tests/test_time_score_api.py`). A write goes through
`pipeline.save_edit` with `notes_changed`, `hands_changed` and `sheet_follows`: the notes revision
rises, the hands stay complete, and a saved sheet that was current stays current. `422` for
`semitones` 0; it is a write, so a version of the Private Library answers `403`.

### POST /time/{uuid}/paste

**Paste** of the Sheet step (implementation 02, plan section 12, Phase 8). Body:

```json
{"source": {"part": "…", "fromMs": 20000, "toMs": 32000},
 "atMs": 30000, "replaceToMs": null, "sheet": { …SavedRhythm… }}
```

Puts the stretch `[fromMs, toMs)` of the source part (snapped to whole columns of its sheet) into
this part at `atMs` (snapped to a column of this part's sheet), or in place of `[atMs, replaceToMs)`
when `replaceToMs` is given: its notes, its marks and its audio; every note, mark and second of
audio after the insertion point moves by the passage's length. `sheet` is the sheet as the page
holds it, unsaved edits included: the marks move in it, and it is saved by the paste; without it the
saved sheet is used. Answers `{beforeVersion, atMs, lengthMs, notesIn, notesMoved, notesRemoved,
durationSeconds, sheet}`: `beforeVersion` is the earlier state the paste kept (the undo), `sheet` the
part's sheet as saved (or `null`). The rules: [`editing-and-compose.md`](editing-and-compose.md)
section 9.

The source is read with the rights of section 9.3 of the plan (`require_part(write=False)`): any
part the user may read; another one answers `404`, the same as one that does not exist. The target
is written: a version of the Private Library answers `403`. `409` for an empty stretch, a stretch
pasted over that does not come after `atMs`, and a target with audio but no notes yet.

### POST /time/{uuid}/versions/{n}/restore

Puts the snapshot `v<n>` of the part's history back (notes, sheet, audio timeline, the names of its
files) after keeping the current state as the next snapshot. Answers `{keptVersion, sheet}`:
restoring `keptVersion` is the redo. `404` when the part has no such snapshot, or one that cannot be
put back whole (a snapshot taken before a new transcription has no timeline). A write.

### GET / PUT /time/{uuid}/lyrics

The words of the song as the reader pasted them in the Lyrics tab, and the lyrics pieces of its
pool, saved by **Save lyrics** (implementation 02, Phase 7). Body and answer:
`{"text": "…", "pool": ["…", "…"]}`; the text at most 20,000 characters, trimmed, an empty text saves
`null`; the pool's empty pieces are dropped, and a `PUT` without `pool` leaves the saved pool as it
is. `GET` answers `pool: null` until a pool was saved here. Stored as `parts[].lyrics` and
`parts[].lyricsPool` in `project.json`, not in `sheet.json`, so
they outlive **Remove all** (`DELETE /time/{uuid}/rhythm`) and a new transcription, and travel with
a duplicate, an edit copy, a Replace and an export. Nothing else of the project changes. `PUT` is a
write: a version of the Private Library answers `403`.

### GET / PUT / DELETE /time/{uuid}/rhythm

The reader's saved reading: the anchor, the key, clef changes, speed changes, renamed figures, beam
breaks and beam joins, hidden notes, fingering, trills, grace notes, lyrics, cue-size stretches and
how far apart the notes and the lines stand. One per piece: a second reading replaces the first. See
[`rhythm-and-annotations.md`](rhythm-and-annotations.md).

`PUT` stamps `handsRevision` with the current value from `notes.pmn`; the client's value is
ignored. A later edit of the notes or the hands outside the Sheet tab makes the reading stale, and
the Sheet tab asks the reader to press **Write the sheet** again. `409` when the piece has no notes.
Since implementation 02, Phase 2 the reading also carries `title`, `subtitle` and `artist` (each
optional, at most 200 characters): what the sheet prints above the music. Since Phase 7 the page
filled `lyricsPool` (the lyrics pieces of the pool; since **Save lyrics** saves the pool, a `PUT`
without it keeps the one saved here, and the page reads it only when the part has no pool of its
own) and `figuresFrom` (where the next figures transposition starts), and `lyrics` holds the lyrics pieces, each starting and ending on a frame.

`DELETE` answers `204` and is what **Remove all** calls.

---

<a id="5-passages--recording-in-sheet"></a>

### 4.1 `/sheet`: the new sheet (implementation 03, Phases 5 to 7)

`GET /sheet/{uuid}?width=130` (60 to 320 staff spaces, the staff width; the SVG adds 8 of margins) answers:

```json
{"svg": "<svg …>", "width": 138, "height": 444.2,
 "columns": [{"system": 0, "frame": 177, "x": 10.97, "ms": 7080.0}, …],
 "systems": [{"index": 0, "first": 177, "last": 552, "top": 3.0, "bottom": 20.2,
              "staff_top": 5.03, "staff_bottom": 19.68, "left": 3.0, "right": 135.0}, …],
 "notes": [{"ref": "177:62", "hand": "right", "pitch": "D4", "figure": 8, "beam": 3, "grace": false,
            "fixed": false, "graceRule": null, "finger": null, "ornaments": [], "ottava": 0}, …],
 "reading": {"key": -2, "keyChanges": [[602, -1], [700, -2]], "clefs": {"right": "treble", "left": "bass"},
             "clefChanges": [[1002, "left", "treble"]]},
 "segments": [{"start": 177, "end": 577, "state": "llm"}, …],
 "source": "llm", "stale": false,
 "llm": {"state": "done", "jobId": null, "available": true, "auto": false, "canRun": false,
         "viaEdit": false, "usd": 0.68, "written": "2026-10-25T15:40:00+00:00"},
 "editable": true, "history": {"undo": "Move a note to the left hand", "redo": null},
 "timings": {"parse_ms": 6.1, "plan_ms": 18.0, "draw_ms": 12.9, "svg_ms": 4.7, "cursor_ms": 0.1, "total_ms": 41.8}}
```

- The sheet is the stored one (`sheet.f1`) when it was written for the current `handsRevision`; laid again on the
  current notes when they or the hands changed (`stale: true`); the algorithm's on the starting hands when none
  is stored. While Sonnet writes it is the sheet of that moment.
- `segments`: Sonnet's windows (`working`: at Sonnet now; `waiting`; `llm`; `algorithm`: a window that failed);
  empty on a sheet Sonnet never wrote.
- `llm.auto`: a new transcription asked for Sonnet (`sheet.pending`) and the user may change the part: the page
  starts it. `canRun`: **Enhance with AI** is offered (on a sheet the AI enhanced, as **Enhance it again with AI**).
  `enhanced`: the AI wrote this sheet or part of it (`sheet.f1` with source `llm` or `mixed`); it stays through
  every later change of the notes or the hands. `runs`: how many AI runs wrote it. `viaEdit`: the owner's
  version of My library, which changes through its edit copy.
- `notes` (Phase 6): each drawn note as its notehead names it (`ref` is the `data-note` of the SVG,
  `"<frame>:<midi>"`, the drawn column and the sounding key), its hand and the name the sheet prints. `editable`:
  the user may change the part and the AI is not writing it. `history`: what the next undo and redo of the part's
  steps are about (`null`: none). Since Phase 7 each note also says its figure (4 a negra), its beam group, whether
  it is a grace note, the user's marks (`fixed`: a figure set by hand; `graceRule`; `finger`), its ornaments and its
  octave line (1 8va, 2 15ma, -1 8vb, -2 15mb); `reading` gives the armaduras (fifths) and the clefs of the sheet;
  `segments` lists after the windows the stretches the AI wrote again with the user's words (`llm`). Since Phase 8
  each note says the frame it stops sounding at (`end`, from `notes.pmn`), and the answer carries what the user wrote
  about the whole sheet: `titles` (`title`, `subtitle`, `artist`), `lyrics` (`[{start, end, text, size, lift}]`, in
  the order of the SVG's `data-lyric`), `quarterMs` (the reference figure), `spaceMs` (the spacing's figure after
  Transpose figures, or `null`), `lineSpace` (`null`: the engine's own 5 staff spaces).
- `409` before the notes exist; the usual `404` of the rights.

`POST /sheet/{uuid}/llm` answers `202 {"jobId", "status"}` (`409` when no API key or SDK is set up). The job's
stream sends `event: sheet` with `{"phase": "reference" | "windows" | "window" | "saved", "done", "total"}`, then
`event: done` with `source`, `windows`, `usd`. The job stops asking Sonnet when the part is deleted. On a sheet the
AI enhanced, the run reads the current hands (the user's moves among them) as a suggestion it may change (Phase 6);
a first run reads the notes without hands.

**Editing (Phase 6, `part_sheet.edits`).** Each route below changes the stored truth in one write under the part's
lock, records one step in the part's log (`sheet.edits.json`), and answers the sheet drawn again, as `GET` does
(with the same `width` query), so one edit is one request. All three answer `409` while the AI writes the sheet,
and need the right to write the part (a version of My library answers `403`: it changes through its edit copy).

- `POST /sheet/{uuid}/hands?width=130` `{"notes": ["177:62", …], "hand": "left"}`: the notes (by ref) go to that
  hand in `notes.pmn`. A part whose hands were never saved as a whole first saves the hand the sheet draws for every
  note. A stored sheet (`sheet.f1`) is laid again on the new hands and stored for them, so it stays current and
  keeps its record (the AI mark); around a note that changed staff the clefs and 8va of the algorithm's rule replace
  the stored ones where they differ (`build.fit_clefs`). The answer adds `moved` (notes whose hand changed) and
  `unmatched` (refs the sheet does not hold).
- `POST /sheet/{uuid}/undo?width=130` and `POST /sheet/{uuid}/redo?width=130`: walk the last step back or forward.
  A step touches only what is still as it left it: a hand changed since by something else stays, and a `sheet.f1`
  changed since is laid again on the hands instead of patched. The answer adds `walked`, the step's label (`null`
  when there was none). The log keeps 50 steps; an AI run that writes the sheet and a new transcription start it
  again.

**The tools (Phase 7, `part_sheet.reading`).** Same rules as above (one write, one step, the sheet drawn again,
`409` while the AI writes, the right to write the part). A refused edit answers `400` with the reason in words.

- `POST /sheet/{uuid}/reading?width=130` `{"action", "notes": [refs], "start", "end", "staff": "both" | "right" |
  "left", "value"}`. With notes: `figure` (`value` 1 to 64, or `null` back to the rule), `finger` (`[3]`, or one
  number per note of a single chord; `[]` removes them), `beam-join` (the picked chords as one group; on one group
  already, the beam goes away), `beam-break` (a new group at the first picked chord, or joined to the group before),
  `grace` (`"on"`, `"off"`, `null`), `ornament` (`trill`, `mordent`, `turn`: over onsets of one hand that follow
  one another; `arpeggio`, `fermata`: on chords; pressed again, off). With a stretch `[start, end)`: `key` (fifths,
  or `null`: the armadura of the piece), `clef` (one `staff`; `treble`, `bass`, or `null`: the hand's own),
  `clef-rule` (the clef rules over the stretch), `ottava` (one `staff`; 1, 2, -1, -2, or 0). The edit is laid on
  the notes so the rules run; it is refused when the result would not hold what was asked or would break a rule of
  the sheet. An algorithm sheet is then stored (record `edited`). The answer adds `edited`, the step's label.
- `POST /sheet/{uuid}/remove?width=130` `{"notes": [refs]}`: the notes are marked removed in `notes.pmn`; the
  answer adds `moved` and `unmatched`. Undo puts them back.
- `GET /sheet/{uuid}/stretch?start=A&end=B`: `{"key", "signs", "fewest", "fewestSigns"}`.
- `POST /sheet/{uuid}/llm/stretch` `{"start", "end", "staff", "notes": [refs], "instruction"}` (at most 1,000
  characters): `202 {"jobId", "status"}`; `409` while the AI already works on the part or when it is not set up,
  `403` without the right to write. One window request whose target is the stretch as it is now (both hands, with
  its hands, beams, clefs, 8va, ornaments) and the user's words first in the prompt; with words, the answer may leave
  notes out, change pitches, add notes inside the stretch and set figures. The stretch is the `working` segment
  meanwhile. The answer is stored as one step (hands; notes left out removed and notes added in `notes.pmn`; the
  sheet, with the AI's figures set by hand where the rule differs; an algorithm sheet becomes `mixed`). The job's `event: done`
  carries `stretch`: `ok`, `failed` (no reply accepted: nothing changes) or `stale` (the notes changed meanwhile),
  and `usd`.

**The sheet toolbox (Phase 8).** The same rules again.

- `POST /sheet/{uuid}/reading` takes the sheet's own actions too, with no notes and no stretch: `titles` (`value`:
  `{"title": "…"}`, an empty one removed), `piece-key` (fifths), `line-space` (2 to 16 staff spaces, or `null`),
  `lyrics` (`value`: `{"pieces": [{start, end, text, size, lift}], "label"}`: the whole list; two pieces never share
  a frame; since Phase 8A++ each piece may also carry `at`, `dx`, `dy` (a block put anywhere: the frame of the
  column under its left edge, how far right of it, its last baseline below the top staff line; `dy: null` is the
  line of words), `width` (its words wrap to it, in staff spaces), `font` (`lora`, `geist`, `montserrat`; another is
  refused), `bold` and `italic`; `GET /sheet/{uuid}` answers them in `lyrics`), `figures` (Transpose figures: `value` steps, positive toward shorter figures; the spacing keeps its
  figure, and a new AI run keeps the user's). With `preview=true` nothing is stored and the answer is the drawing
  of the result (`svg`, `columns`, `systems`, `width`, `height`, `edited`).
- `POST /sheet/{uuid}/transpose?width=130` `{"semitones": 2}`: every note moved in `notes.pmn`, the stored sheet
  with them (armaduras renamed with fewer signs, decisions kept, clefs fitted where a note reads four ledger lines
  or more from its staff); notes that would leave the 88 keys are taken off. The answer adds `edited`, `moved`,
  `outside`. With `preview=true` nothing is written and the answer is the drawing of the result.
- `POST /sheet/{uuid}/add?width=130` `{"frame", "midi", "hand", "lengthMs"}`: a note at the onset of the drawn column
  `frame` (`lengthMs` absent: a negra of the reference figure); `400` when that key is already struck there.
- `GET /sheet/{uuid}/pages?width=W&height=H&first=F&gap=G` (staff spaces: the staff width, the page's room, page
  one's room under its title, the space between lines): `{"pages": [{"svg", "width", "height", "first", "last"}]}`,
  whole lines on each page.

## 5. `/passages`: Recording in Sheet

Implementation 02, Phase 9 (plan section 13). A passage is a stretch of a part being re-recorded,
or a moment of it where a new passage goes. It and its takes are projects of the user's Personal
Vault, hidden from every list (`kind = 'passage'`); their parts answer every route of a part
(`/time`, `/audio`, `/pieces`), which is how the page draws them. The path names the passage's
project, so the rights of a project apply; opening one checks the user may write the part (a
version of the library answers `403`).

**`POST /passages`** `{part, fromMs, toMs}` (`toMs == fromMs`: a new passage) answers `201` and the
passage:

```json
{"id": "…", "part": "…", "projectId": "…", "title": "Elefants", "current": "…",
 "fromMs": 9000, "toMs": 16960, "anchorMs": 440.0, "anchorFigure": "negra",
 "takes": [{"id": "…", "name": "Take 1", "state": "ready", "seconds": 16.2,
            "fromSeconds": 0.0, "toSeconds": 15.92, "jobId": null, "audioRevision": 2}],
 "take": "…", "speed": 2.0, "windowMs": 0.0, "takeMs": 15920}
```

`current` is the part holding the copy of the stretch. A take's `state` is `recorded`, `reading`
(its `jobId` is followed on `GET /matrix/progress/{jobId}`) or `ready`.

**`PATCH /passages/{id}`** `{take?, speed?, windowMs?}`: the speed goes from ×0.25 to ×4 (`409`
otherwise); a take of another passage is `404`. **`DELETE`** discards it with its takes (`204`).

**`POST …/takes`** (multipart `file`, any audio the upload takes, and/or `notes`, the JSON list of
the keys played on a MIDI piano, `[{midiNote, start, end, velocity}]` in seconds from the start of the
recording) adds a take and shows it; a take has `midi: true` when it has keys.
**`POST …/takes/{take}/read`** `{fromSeconds, toSeconds}` answers `202` with `{jobId, status}`: the
stretch becomes the take's cuts, then the transcription, the hand split and the first sheet run as
one job of the GPU queue (key `take:<id>`).

**`POST …/promotion`** and **`POST …/promote`** take `{mode, audio, sheet?}`: `mode` is `window`
(the take under the window, fitted into the passage) or `whole` (the whole take in place of the
passage); `audio` is `original` (a window only: the notes change, the audio does not) or
`recording`; `sheet` is the Proposal's sheet as the page holds it. The first answers what would
happen:

```json
{"mode": "whole", "audio": "recording", "notesOut": 6, "notesIn": 9,
 "marksDropped": {"fingers": 1}, "lengthChangeMs": 4480, "durationSeconds": 239.91}
```

The second writes, deletes the passage, and answers `{part, projectId, beforeVersion, atMs,
lengthMs, sheet}`: `POST /time/{part}/versions/{beforeVersion}/restore` is its undo.

Errors: `404` for a passage or take that is not there, `409` for a promotion that cannot be made
(no take read yet, a window on a new passage, the original audio with another length), `503` when
ffmpeg is missing, `422` when a conversion fails.

Detail in [`editing-and-compose.md`](editing-and-compose.md) section 3. The staged session of
Epics 11 and 13 (`/audio/{uuid}/edits`, `POST /audio/compose`) was removed in Phase 9.

---

## 6. `/pieces`: the steps of a project

The page of a project (`/projects/:id/:step` in the frontend, the "flow page" of implementation 08)
has four steps: Source, Audio, Notes, Sheet (the Hands step was removed by implementation 03, Phase 5).
Before implementation 08 nothing on the backend could say which of these steps a piece had
completed, and the notes could only be edited through the sheet's columns and rows. The `/pieces`
router (`api/pieces.py`, Phase 5) gives the page one status answer to enable its tabs from, the notes
in the compact columns form, and edits by note id with a revision check. The model is in
`aitu_backend/pieces/` (`status.py`, `edits.py`) and `transcription/saved_hands.py`. The revision
chain is described in
[`context/backend/piano-matrix-notation.md`](../../../context/backend/piano-matrix-notation.md#3-on-disk-notespmn-pmnnotes_filepy-pmnevents_filepy).

### 6.1 GET /pieces/{uuid}/status

```json
{"audioUuid": "…",
 "steps": [{"step": "notes", "state": "ready", "enabled": true, "reason": null,
            "details": {"noteCount": 1351, "engine": "muscriptor-large"}}, …],
 "resume": "sheet",
 "revisions": {"audio": 0, "notes": 1, "notesAudio": 0, "hands": 2,
               "handsNotes": 1, "sheetHands": 2},
 "scratch": false}
```

- `steps` holds `source`, `audio`, `notes`, `sheet`, in that order.
- `state` is `missing` (never made), `running` (a transcription is working on it), `stale` (made
  from an older revision of an earlier step) or `ready`.
- `enabled` is true when every step before it is ready. A stale Sheet tab stays enabled, because it
  opens with a banner that asks the reader to write the sheet again.
- `reason` is a sentence the page shows as it is, as the tab's tooltip or a banner.
- `details`: `audio` gives `audioRevision` and `cuts` (a count); `notes` gives `noteCount` and
  `engine`, plus `jobId` and `jobStatus` while running; `sheet` gives `newSheet` (a `sheet.f1` is stored),
  `legacy` (the state of the old `sheet.json`) and, while Sonnet writes, `jobId` and `jobStatus`.
- `resume` is the furthest enabled step that is ready or running (or a stale Sheet): the tab a piece
  opens on.
- `revisions` are the numbers the states are computed from: `audio` (`timeline.json`), `notes`,
  `notesAudio`, `hands`, `handsNotes` (`notes.pmn`), and `sheetHands` (`sheet.json`).
- `scratch` (Phase 8): a part made from scratch (its source is `composed`) with no audio yet. Its
  Source and Audio steps are `missing` and the Audio tab closed ("Record or paste a passage first."),
  `resume` is `sheet`, and the page shows only the sheet. A paste or a recorded passage that brings
  audio ends it.

The Notes step is `stale` when `notesAudio` differs from `audio` (a cut was saved after the
transcription). The Sheet step is enabled once the notes are ready, `running` while Sonnet writes, `ready` with a
stored new sheet or a current `sheet.json`, and `stale` when only a `sheet.json` is left and `sheetHands` differs
from `hands`.

`404` for an unknown uuid. The answer takes 5 to 24 ms.

### 6.2 GET /pieces/{uuid}/notes

The live notes in the columns form of the piano matrix notation (`pmn/columns.py`): one list per
field, sorted by onset then key, whole milliseconds of the piece.

```json
{"revision": 7, "handsRevision": 3, "durationMs": 189160, "stale": false,
 "id": [0, 1, 2], "key": [39, 43, 46], "onMs": [3070, 3363, 3364],
 "lenMs": [1220, 587, 137], "hand": "llr", "guessed": []}
```

`hand` has one character per note: `r`, `l`, or `-` for no hand. `guessed` lists the ids whose hand
came from the quick rule. `stale` is true when the selected region changed after the transcription.
`409` when the piece has not been transcribed. About 4 ms and 10 KB sent for Superestrella.

### 6.3 PATCH /pieces/{uuid}/notes

The page never sends the whole piece. It sends a list of operations on notes named by their id, and
the backend applies them in order (`pieces/edits.py`).

```json
{"baseRevision": 7, "baseHandsRevision": 3,
 "ops": [{"op": "move", "id": 12, "onMs": 3050, "lenMs": 400},
         {"op": "add", "tempId": -1, "key": 40, "onMs": 5000, "lenMs": 250, "hand": "l"},
         {"op": "hand", "ids": [3, 4, 5], "hand": "r"}]}
```

| `op` | Fields | Changes |
|---|---|---|
| `move` | `id`, `onMs`, `lenMs`, optional `key` (0 to 87) | the notes: move or resize, and change key when `key` is given |
| `delete` | `ids` | the notes: marked removed (the id is kept) |
| `restore` | `ids` | the notes: a removed note returns with its id and hand |
| `add` | `tempId` (negative), `key`, `onMs`, `lenMs`, optional `hand` (`r` or `l`) | the notes |
| `hand` | `ids`, `hand` (`r` or `l`) | the hands |

`ops` holds 1 to 50,000 operations. Times are milliseconds of the piece.

**The rules.**

- **One key sounds one note at a time.** After the operations, on every key an operation touched, a
  note that runs into the next onset of its key is shortened to that onset. Only pairs where one
  note was placed or moved by an operation are changed, so overlaps already in old ByteDance files
  stay as they were. Two notes of one key that start less than 0.5 ms apart are refused.
- A note may not end more than 1 ms after the end of the piece.
- A `move` on a removed note is refused ("Restore it first").
- A request that changes nothing answers `saved: false` and writes nothing.

**The answer** (`NotesPatchResult`):

| Field | Meaning |
|---|---|
| `revision`, `handsRevision` | The new revisions, to send as the base of the next `PATCH`. |
| `saved` | False when nothing changed. |
| `added` | `[{tempId, id}]`: the id the backend chose for each added note. |
| `changed` | Columns (`id`, `key`, `onMs`, `lenMs`, `hand`, `guessed`) of every note the backend changed beyond the request: added notes, notes the same-key rule shortened, notes the quick rule gave a hand. The page replaces its copy of each. |
| `sheetStale` | True when a saved piano sheet was current before this edit and is stale now. |

**The revisions** (`pipeline.save_edit`): a notes operation raises `notesRevision`; any operation
raises `handsRevision`; a hand edit that leaves every placed live note with a hand sets
`handsNotesRevision` to the new `notesRevision`. When the hands were already saved as a whole, a
live note with no hand (an added note, a restored note) receives the hand of its neighbours by the
quick rule and is marked `guessed`.

**Errors.** Nothing is written when a request is refused.

- `404`: unknown uuid.
- `409`: `baseRevision` is not the stored `notesRevision`, or `baseHandsRevision` (when given) is
  not the stored `handsRevision`; the notes are stale because the selected region changed ("Transcribe
  again"); the piece has not been transcribed.
- `422`: an operation cannot be applied (an unknown id, a reused `tempId`, a note past the end, two
  onsets of one key at the same time), with a message naming the operation, or a body that does not
  match the schema.

The route holds `pipeline.piece_lock(uuid)` from its read to its write, so a revision check and its
write cannot interleave with another request.

### 6.4 POST /pieces/{uuid}/hands/predict

**Predict hands** on the Hands tab. The same hand split the piano sheet has always run (the inference
on the snapped time matrix, D-31), read back as one hand per note id. **Nothing is written**: the page
shows the answer as unsaved changes, and **Save** sends it as two `hand` operations of a `PATCH`.

Body: `{ "baseRevision": n, "frameMs": 40, "replace": false }`. With `replace: false` the saved hands
the user set are kept and only the notes without a hand, or with a guessed hand, are predicted.
`replace: true` predicts every note again.

| Field | Meaning |
|---|---|
| `revision`, `handsRevision`, `frameMs` | What the prediction was made from. |
| `id` | The live notes, in the order of `GET /pieces/{uuid}/notes`. |
| `hand` | One character per note of `id`: `r`, `l`, or `-` for a note the split could not place. |
| `changed` | How many notes would change hand if this is saved (a note with no hand counts). |
| `unplaced` | How many notes are `-`. They are drawn red for the user to delete or assign. |
| `elapsedMs` | |

`409` when `baseRevision` is old or the piece has not been transcribed. The inferred split is cached:
the first prediction on Superestrella takes about 1.2 s, a second one about 9 ms.

### 6.5 POST /pieces/{uuid}/hands/predict/job

The same prediction as a job, so the page can show real progress. Same body; answers `202` with
`{jobId, status}`. The checks (`404`, `409`) run before the job starts.

The page follows `GET /matrix/progress/{jobId}`. The stages are `events` (building the matrix) and
`two-hands` (the inference, in hundredths: the beam search reports 0 to 60, the refine rounds 60 to
100). The `done` frame carries every field of the direct answer. The job key is
`hands:<uuid>:<notesRevision>:<frameMs>:<replace>`, so a second request with the same options while
the first runs returns the same job. When the split is already cached, the job ends at once. It does
not use the GPU queue.

---

<a id="7-projects-the-personal-vault"></a>

## 7. `/projects`: the Personal Vault

`api/projects.py`, implementation 02 plan sections 8.3, 8.8 and 10.1. A project's id is the id of
its first part, the uuid the step routes take. Every route checks the rights of the project it
names (`404` for one the user may not read); the list is scoped by owner. A project of the Private
Library is **read only** to its owner (`403` on a write, Phase 6): it changes through `POST
/projects/{id}/edit` and `POST /projects/{copy}/library`. The old `/library` router (playground
versions, `.npz` matrices, promotions, tags, playlists) was **deleted in Phase 3**; `/library` is
the Private Library since Phase 6 (§7.1).

**The row** (`GET /projects`, `GET /projects/{id}`, and the answer of create, rename and import):

| Field | Meaning |
|---|---|
| `id`, `title`, `kind`, `layer`, `mine` | `kind`: `song` or `integratedPlaylist`; `layer`: `vault`, `private`, `public`, or `request` (the copy a request sent, Phase 14); `mine`: the user owns it (a library project of another user is one shared with them, Phase 14) |
| `step` | The lowest `resume` of the parts (`source`, `audio`, `notes`, `hands`, `sheet`), kept in `projects.step` and worked out again only after a part changed |
| `running` | `transcribing` or `reading` while a job works on a part, `writing` while Sonnet writes the sheet of a part (implementation 03, Phase 5), else `null` |
| `enhanced` | The AI wrote the sheet of a part of it (its `sheet.f1` record says `llm` or `mixed`; implementation 03, Phase 5) |
| `parts` | The ids of the parts, in order |
| `source` | Where the first part's audio came from (`upload`, `youtube`, `recording` ...) |
| `hasVideo`, `hasNotes` | The first part has a video; it has notes |
| `basedOn`, `createdAt`, `updatedAt` | `basedOn`: the library project an edit copy edits. `updatedAt` is the newest file of the parts and `project.json` |
| `library` | A project of the Private Library: `{songId, songTitle, artists, versionId, versionName, projectId}` of its song and version (Phase 6), else `null` |
| `editing` | An edit copy (`basedOn` set): the same fields for the version it edits, else `null` |

- `GET /projects?layer=vault&layer=private`: the current user's projects of those layers (default
  `vault`), newest change first.
- `POST /projects`, body `{ "title": string, "scratch": bool }`: an empty project in the Personal
  Vault, with no audio. Without `scratch` it has no notes either and its status opens on Source.
  With `scratch` (**From scratch**, Phase 8) its part's source is `composed`, it has an empty
  `notes.pmn` at `frameMs` 40, and its status is `scratch` and opens on the Sheet step.
- `PATCH /projects/{id}`, body `{ "title": string }` (1 to 300 characters, trimmed; `422` when
  empty).
- `DELETE /projects/{id}` answers `204`. The bundle, the history, the temporary files (a video and its
  frames) and every audio file no other project uses are deleted.
- `POST /projects/{id}/duplicate`, body `{ "title": string | null }`: a copy in the current user's
  Personal Vault with new ids. The audio files are shared, not copied; history, staging and the
  video are not copied. `201` with `{id, title, parts}`. A read for the rights check: the original
  does not change and the copy is the asker's. (Made in Phase 3 for the scripts that work on
  copies.)
- `GET /projects/{id}/export` answers the `.aitu` file (`application/zip`, named `<title>.aitu`):
  `export.json`, `project.json`, `parts/<partId>/notes.pmn|sheet.json|timeline.json`, and
  `audio/<sha256>.<ext>` for every file a timeline names.
- `POST /projects/import` (multipart `file`) makes a new project in the current user's Personal
  Vault, with new ids, the same title, and `origin: {"importedFrom": <id>}`. Every member is read by
  the name this route expects (a name in the zip never becomes a path), each part file must read as
  what it is, and each audio file is hashed again and must match its name. `422` with the reason
  otherwise, and nothing is left behind.
- `POST /projects/{id}/library` (Phase 6, plan sections 8.5, 10.2 and 10.6), body
  `{ "songId": int | null, "song": string, "artist": string, "version": string, "replace": bool,
  "publicSongId": int | null, "publicArtistId": int | null }`. *Phase 13:* `publicSongId` files the
  project under the user's song that stands for that public song (linked by `public_id`, or the
  user's song of the same title and first artist, linked now, or a new one made with the public
  song's title, year and artists); `publicArtistId` with `song` makes a new song by the user's
  artist that stands for that public artist (found or made the same way).
  **Save to library**: the project, which must be in the asker's Personal Vault with every part's
  Sheet step `ready`, moves to their Private Library as the version `version` of the song `songId`,
  or of their song titled `song` by `artist` (found ignoring case and spaces, made when missing; a
  new artist name makes a new artist). On the way each audio file the timeline uses only in part is
  written again with only the ranges in use (FLAC, `audioRevision` unchanged, so the notes stay
  current), the old file is deleted when no project uses it, and the video, its frames, the edit
  sessions and the history of the parts are deleted. With `replace: true` an edit copy (`basedOn`
  set) gives its content to the version it edits instead: the library project keeps its ids, its
  previous content goes to `history/<projectId>/v<N>/`, and the copy is deleted. `201` with
  `{songId, versionId, projectId}`. `409` with the reason: the piano sheet is not saved, a job is
  writing the notes, the song already has a version of that name, or the version an edit copy
  edits was deleted.
- `POST /projects/{id}/edit` (Phase 6): the copy in the asker's Personal Vault that edits this
  version of their Private Library, with `basedOn` pointing at it and `origin: {"editOf": id}`; the
  copy already open is answered instead of a second one. No audio bytes are copied. A read for the
  rights check (the version does not change); `409` for a version of another user's library. Answers
  the copy's row. Deleting the copy (`DELETE /projects/{copy}`) discards the changes.

**From other projects and the parts** (Phase 10, plan sections 8.4, 10.4 and 14.1;
`editing/parts.py`, [`editing-and-compose.md`](editing-and-compose.md) section 4):

- `POST /projects/compose`, body `{ "title": string, "kind": "song" | "integratedPlaylist",
  "passages": [{ "part", "fromMs"?, "toMs"?, "join": "sequential" | "subheader", "subheader"? }] }`
  (1 to 200 passages; `fromMs` and `toMs` both absent for the whole part). Every `part` must be one
  the user may read (`404` otherwise). A new project of the Personal Vault: one part per run of
  sequential passages, a new part at each `subheader` join, titled by its `subheader` or the
  source's title (no subheader when there is one part). Each passage is a paste at the end of its
  part, so it brings its notes, marks and ranges of the stored audio; no audio byte is copied.
  `origin` is `{"composedFrom": [...]}`. `201` with the row; `409` with the reason (a source with
  nothing in it, a source with audio and no notes), and nothing is left behind.
- `GET /projects/{id}/parts`: `{parts: [{id, subheader, durationMs}], part: null}`. A read; the other
  routes write (`403` on a version of the library).
- `PUT /projects/{id}/parts`, body `{ "order": [partId] }`, every part once (`422` otherwise).
- `PATCH /projects/{id}/parts/{part}`, body `{ "subheader": string | null }` (trimmed; empty takes it
  away).
- `POST /projects/{id}/parts/{part}/join`: the part put at the end of the one before it, as a paste;
  the joined part keeps the first one's subheader. The part whose id is the project's is always the
  one kept (its music goes in at the start of the other's otherwise). `part` of the answer is the
  part that holds both. `409` for the first part.
- `POST /projects/{id}/parts/{part}/split`, body `{ "atMs": number, "subheader": string | null,
  "sheet": SavedRhythm | null }`: from `atMs` (snapped to a column) to the end becomes a new part
  right after it (a paste into an empty part), then that stretch is cut out of the first (its audio
  becomes cuts). `sheet` is the page's sheet, saved with it. `part` of the answer is the new part.
  `409` when `atMs` is not inside the part.

The answer of the four writes is `{parts, part}` as for `GET`.

Storage layout in [`paths-and-data.md`](paths-and-data.md).

<a id="71-library-the-private-library"></a>

### 7.1 `/library`: the Private Library

`api/library.py` and `library/` (`rows.py`, `flow.py`), implementation 02 Phase 6, plan sections 15.1
and 15.2. Every route works on the current user's rows only and answers `404` for another user's,
`409` for a change the library refuses (with the reason), `422` for an empty or too long name.

| Route | Answer |
|---|---|
| `GET /library/songs` | `[{id, title, artists: [{artistId, nameId, name}], versions, editing, updatedAt}]`, by title. `editing`: a version has an edit copy open |
| `GET /library/songs/{id}` | `{id, title, artists, versions: [{id, name, projectId, parts, step, createdAt, updatedAt, editCopy, history}], publicId}`. `editCopy`: the open edit copy's id; `history`: how many earlier states; `publicId`: the public song it stands for (Phase 13) |
| `PATCH /library/songs/{id}` | Body `{title?, artists?: [string]}`: rename; the artists by name, in order (an unknown name makes a new artist) |
| `DELETE /library/songs/{id}` | `204`: every version and its project, then the song |
| `PATCH /library/versions/{id}` | Body `{name}`: 1 to 60 characters, unique in the song ignoring case (`409`) |
| `DELETE /library/versions/{id}` | `204`: the version, its project, its history, the audio no other project uses. An edit copy of it stays as an ordinary project |
| `GET /library/versions/{id}/history` | `[{number, savedAt, reason}]`, newest first. `reason`: "Replaced by an edit" or "Replaced by a restore" |
| `POST /library/versions/{id}/history/{n}/restore` | The state `n` becomes the version's content; the state it replaces is kept first. Answers the song |
| `GET /library/artists` | `[{id, name, names: [{id, name, isDefault}], songs}]`, by default name |
| `GET /library/artists/{id}` | The same, with `songList: [{id, title, versions}]` |
| `POST /library/artists/{id}/names` | Body `{name}`: another name. `409` when another artist has it (merge them instead) |
| `PATCH /library/artists/{id}/names/{nameId}` | Body `{name?, isDefault?}` |
| `DELETE /library/artists/{id}/names/{nameId}` | Not the default (`409`); songs saved with it point at the default name |
| `POST /library/artists/{id}/merge` | Body `{into}`: every name moves to `into`, which keeps its default; answers `into` |
| `DELETE /library/artists/{id}` | `204`; `409` while the artist has songs |

### 7.2 `/playlists`: songs playlists

`api/playlists.py` and `library/playlists.py`, implementation 02 Phase 10, plan section 14.2. A songs
playlist points at songs of the user's Private Library, each on a version and optionally a stretch;
nothing in it is a copy. Every route works on the user's own playlists (`404` for another user's,
and for a song or a version that is not the user's), `422` for an empty title or a stretch that ends
before it starts.

| Route | Answer |
|---|---|
| `GET /playlists` | `[{id, title, songs, updatedAt}]`, the newest change first |
| `POST /playlists` | Body `{title, items?: [{songId, projectId?, fromMs?, toMs?}]}`: `201` with the playlist. `projectId` is a version of the song (its first when absent) |
| `GET /playlists/{id}` | `{id, title, updatedAt, items: [{id, songId, songTitle, artists, projectId, versionName, parts, versions: [{projectId, name}], fromMs, toMs}]}` in order. An item whose version was deleted shows the song's first; an item whose song was deleted is dropped |
| `PATCH /playlists/{id}` | Body `{title?, order?: [itemId]}` (every item once) |
| `DELETE /playlists/{id}` | `204`; the songs and their versions stay |
| `POST /playlists/{id}/items` | Body `{items: [...]}`: added at the end |
| `PATCH /playlists/{id}/items/{item}` | Body `{projectId?, fromMs?, toMs?, whole?}`: another version, a stretch (both ends), or `whole: true` for the whole song |
| `DELETE /playlists/{id}/items/{item}` | The playlist without it |

<a id="73-public-the-public-library"></a>

### 7.3 `/public`: the Public Library

`api/public.py` and `library/` (`catalogue.py`, `public.py`, `pull.py`), implementation 02 Phase 13,
plan sections 15.1 to 15.3 and 15.6. Every signed-in user reads it; nothing here changes a public
row. A pull or a like changes only the user's own rows. `404` for a row that is not public, `409`
with the reason for a pull that cannot be done, `422` for an unknown region.

| Route | Answer |
|---|---|
| `GET /public/songs` | Query `q` (words in any order, title and artists, accents ignored), `decade` (its first year: `1980`), `region` (a code), `genre`, `tag` (ids), `sort` (`popularity`, `year`, `title`), `dir` (`asc`, `desc`), `offset`, `limit` (at most 200). `{total, rows: [{id, title, artists: [{artistId, name}], year, popularity, versions, regionPopularity: [{region, popularity, basis}]}], facets: {decades, regions, genres, tags: [{value, label, count, group}]}}`. With a `region` other than `worldwide` (Phase 16), `popularity` is that region's (`song_region_popularity`); with a `decade`, it is the one of that decade's chart weeks of the region (worldwide when none is given), worked out on the request; a facet counts what each value would leave given the other filters. An inferred value (Phase 17) counts as the song's popularity in its region, or worldwide for a song on no chart, but not in a decade. `popularity` is `null` for a song with no value in the region shown (a Spain-only song worldwide), which sorts last both ways; `regionPopularity` is the song's all-time value in each region other than worldwide. A song with no year sorts last both ways |
| `GET /public/songs/{id}` | `{id, title, year, decade, popularity, artists, albums: [{id, title, year, track}], genres, regions, tags: [[category, value]], regionPopularity: [{region, popularity, basis}], charts: [{name, region, size, best, weeks, first, last, history: [[week, rank]]}], hasLyrics, defaultVersion, fixed: [version], others: [{username, versions: [version]}], inLibrary}`; a version is `{projectId, parts, name, creator, likes, liked, createdAt, ready, inLibrary}`. `inLibrary`: the user's song (or, on a version, the user's copy). `popularity` is worldwide; `regionPopularity` (Phase 16) gives each other region's, with its `basis` (`weeks`, `number_ones`, `estimated`; Phase 17: `inferred`, from YouTube views, for a song no chart of the region lists, and the only kind a `Worldwide` entry has: a song on no chart at all); a chart's `size` 1 is a list of number ones only |
| `GET /public/songs/{id}/lyrics` | `{text}`; `404` when it has none |
| `POST /public/songs/{id}/pull` | Body `{projects: [id]}` (the default version when empty): `201` `{id, songs, versions, already}`, `id` the user's song. `409` "This song has no version yet"; `404` for a project that is not a version of the song. A version already pulled is not pulled again |
| `GET /public/artists` | Query `q`, `sort` (`popularity`: the artist's most popular song; `name`; `songs`), `dir`, `offset`, `limit`. `{total, rows: [{id, name, otherNames, songs, popularity, withVersions}]}` |
| `GET /public/artists/{id}` | `{id, name, otherNames, songs: [{id, title, year, popularity, versions}], albums: [{id, title, year, popularity}], withVersions, inLibrary}`, songs and albums by popularity |
| `POST /public/artists/{id}/pull` | `201` `{id, songs, versions, already}`, `id` the user's artist; each song with a version, on its default version. `409` when none has one |
| `GET /public/playlists` | `[{id, title, songs, updatedAt}]` by title |
| `GET /public/playlists/{id}` | As `GET /playlists/{id}`, without `versions` on an item |
| `POST /public/playlists/{id}/pull` | `201` `{id, ...}`, `id` the user's new songs playlist (the one made before, when pulled again); songs with no version left out. `409` when none has one |
| `PUT`, `DELETE /public/likes/{project}` | `{likes, liked}`. Once per user; `404` for a project that is not a public version. The path parameter is not named `project_id`, so the router's rights check does not read a like as a write of the public project |
| `GET /public/suggest` | Query `q`, `artist`, `limit` (8): `{songs, artists}`, the most popular songs whose title matches `q` by an artist matching `artist`, and the artists whose names match `q` |

| `GET /public/lists` | `{genres, regions: [{code, name}], tagCategories}`: the fixed lists of section 15.3 (Phase 14) |

A public version is a project of `.database/public/`, made by an accepted request (Phase 14,
[§7.4](#74-requests-requests-to-the-public-library)): `library/public.copy_to_public` copies the
project and `point_version` points the version at it, inside the review's transaction
(`place_version` does both for the tests and the browser checks' fixture,
`library/public_fixture.py`). Every user reads it through the step routes and Play mode; only the
master user may write it.

<a id="74-requests-requests-to-the-public-library"></a>

### 7.4 `/requests`: requests to the Public Library

`api/requests.py`, the review routes of `api/admin.py`, and `library/requests.py`; implementation 02
Phase 14, plan section 16 ([`context/music-library/requests.md`](../../../context/music-library/requests.md)).
A request is read by its author and the master user, and `404` for anyone else. The path parameter
is `request_id`, never `project_id`, so the router's rights check leaves it alone. `404` for a row
that is not the user's, `409` with the reason for a refusal (the same version already asked, a
request already reviewed, an item accepted without what it needs), `422` for a field out of its
rules (a version name that is not a simple name, three genres, nothing changed).

**The body of `POST /requests` and `PUT /requests/{id}`** (a *proposal*), by `kind`:

| `kind` | Fields | Items made |
|---|---|---|
| `userVersion` | `version` (a version of My library), `versionName` (lowercase letters, digits, hyphens, at most 24), `song`: `{publicId}` or `{new: SongFields}`, optional `privateId` (the user's own song) | `newArtist`* (one per new artist name), `newSong`?, `project` |
| `metadata` | `song: {publicId}` with `changes: SongFields`; or `song: {new: SongFields}`; or `artist: {publicId, name?, addNames}` | `newArtist`*, then `metadata` or `newSong` |
| `fixedVersion` | `userVersion` (the public project of the user's accepted user version), `name` (`hard`, `medium`, `easy` or a custom simple name) | `versionPointer` |
| `playlist` | `playlist` (a songs playlist of My library), `title` | `playlist` |

Every kind takes `note`, a few words for the master user. `SongFields` is `{title, year?, artists:
[{publicId} or {newName}, privateId?], genres (at most 2 of the 13), regions (codes; `worldwide`
when none), tags: [{category, value}]}`. A `userVersion` copies the project into the layer
`request` when it is sent ([paths-and-data.md](paths-and-data.md)).

| Route | Answer |
|---|---|
| `GET /requests` | `[summary]`, newest change first. A summary is `{id, kind, status, author, title, subject, createdAt, updatedAt, decidedAt, waiting, items}`; `status` is `open`, `changesAsked`, `accepted`, `partlyAccepted`, `refused` or `withdrawn` |
| `GET /requests/counts` | `{mine, review}`: the user's requests with changes asked; the open requests (`0` unless the master user) |
| `GET /requests/publish-info?version=` | `{versionId, versionName, suggestedName, ready, songId, songTitle, artists: [{privateId, name, publicId, publicName}], publicSongId, publicSongTitle, ownVersions, waitingRequest}` |
| `GET /requests/playlist-info?playlist=` | `{title, items: [{songId, projectId, fromMs, toMs, title, versionName}], left: [title]}`: the songs with a public version (pulled from it, or published by the user), and the ones left out |
| `POST /requests` | `201` `{id}` |
| `GET /requests/{id}` | A summary with `mine`, `itemList: [{id, kind, decision, comment, payload, compare}]`, `comments` (the conversation, oldest first: `[{id, kind, author, body, createdAt, itemId, parentId, details}]`; `kind` is `comment`, `review`, `sentAgain` or `withdrawn`; `details` of a comment on a stretch: `{partId, fromMs, toMs, excerpt, excerptPart, anchorMs}`, of a review: `{items: [{id, kind, decision, comment}]}`), `proposal` (the body that would send it again). `payload` carries names (`artists: [{publicId or ref, name, isNew}]`) and, once accepted, `made` (`artistId`, `songId`, `projectId`, `playlistId`). `compare` (a `project` or `versionPointer` item): `{current, proposed}`, each `{projectId, parts, creator, name, kept}` or `null` |
| `PUT /requests/{id}` | The author, on a request with changes asked: the items not accepted are replaced by the new proposal's (the accepted ones stay); the request is `open` again. `409` otherwise |
| `POST /requests/{id}/withdraw` | The author, while `open` or `changesAsked`: `withdrawn`; what was accepted stays |
| `POST /requests/{id}/comments` | The author or the master user (`404` for anyone else). Body `{body, parentId?, itemId?, partId?, fromMs?, toMs?}`: `201` and the request. `parentId` answers a comment (a reply to a reply joins its thread). With `itemId`, `partId`, `fromMs`, `toMs`: a comment on a stretch of the item's proposed sheet, at most two minutes; a project of just that stretch is made in the layer `request` (owned by the author, kind `passage`) and named in `details`. `404` for a part that is not proposed; `422` for an empty comment, an empty or too long stretch |
| `GET /admin/requests?everything=` | The open requests, oldest first; with `everything`, every request, newest change first |
| `POST /admin/requests/{id}/decision` | Body `{items: [{id, decision, comment?, changes?}], comment?}`: one decision (`accepted`, `refused`, `changesAsked`) for **every** waiting item. `changes` renames on accepting: `name` (`newArtist`, `versionPointer`), `title` and `year` (`newSong`), `title` (`playlist`), `versionName` (`project`). The accepted items are written in one transaction (new public rows, the project copied to `public/` and pointed at, the author as creator, the author's song and artists linked by `public_id`); `409` when an accepted item needs one that is not accepted. Answers the request as `GET /requests/{id}` |

<a id="75-shares-and-shared-a-shared-library"></a>

### 7.5 `/shares` and `/shared`: a shared library

`api/shares.py` and `library/shares.py`, implementation 02 Phase 14, plan section 15.4. The owner
shares their whole Private Library, read only (`library_shares`); the rights check lets the other
user read its projects (`404` once the share ends). `404` for a library that is not shared with the
user.

| Route | Answer |
|---|---|
| `GET /shares` | `{people: [{id, username}], sharedWith: [userId], sharedWithMe: [{id, username, songs}]}`: the other enabled users, the ones the user shares with, the ones who share with the user |
| `PUT /shares/{userId}`, `DELETE /shares/{userId}` | Share with a user, or stop; answers as `GET /shares`. `404` for an unknown or disabled user |
| `GET /shared/{ownerId}/songs` | `{owner, songs: [{id, title, artists, versions}]}` by title |
| `GET /shared/songs/{id}` | `{id, title, artists, ownerId, owner, versions: [{id, name, projectId, parts, inLibrary}], inLibrary}` |
| `POST /shared/songs/{id}/pull` | Body `{versions: [id]}` (every version when empty): `201` `{songId, versions, already}`. Each version is copied into the user's library (no audio bytes), named `<version> (<owner>)`, under the user's own song: the one for the same public song, or the same title and first artist, or a new one. A version added before is not added again (`origin.sharedVersion`) |

---

## 8. `/youtube`

`yt-dlp` is a normal Python dependency and is invoked as `python -m yt_dlp` on the backend's own
interpreter, so it never depends on `PATH`. In the container `deno` is installed beside it, because
yt-dlp needs a JavaScript runtime to read YouTube's player.

The body of the three single-video routes is `{ "url": string, "fileName": string | null }`;
`fileName` is the display name and defaults to the video title. Errors keep yt-dlp's own words:
`422` for a link that is not a YouTube URL, `503` when yt-dlp is missing, `502` when the download
fails.

- `POST /youtube/probe` reads a video's title, length and uploader without downloading anything.
- `POST /youtube/download` extracts mp3 and ingests it like any upload, inside the request.
- `POST /youtube/batch` downloads several in order; one failure does not stop the rest.

### 8.1 POST /youtube/jobs

The Source tab of the flow page needed a download that shows its progress and does not hold a
request open for the whole download. This route runs the same download as a background job and
answers `202` with `{jobId, status}` at once.

- The URL and the presence of yt-dlp are checked before the job exists, so a wrong link is `422` at
  once.
- The page follows `GET /matrix/progress/{jobId}`: a `download` stage in percent, then a `store`
  stage while the audio is converted, then `event: done` with `audioUuid`, `alias` and
  `durationSeconds`, or with `status: "error"` and yt-dlp's message.
- The job key is `youtube:<url>`: a second request for the same URL while the first runs returns
  the first job.
- It does not use the GPU queue. A 19 s video reached the Audio tab in 2.5 s.

---

## 9. The text-notation MVP routes

`GET /scores` and `POST /sequence`, the project's original seed (a line-per-time-frame text notation
converted into a sparse 88-key score), were **deleted in implementation 02, Phase 1** (decision Q-4),
with `api/scores.py`, `schemas/score.py` and `data/example-scores.json`. No screen had called them
since P4.2. Both paths now answer `404` (a test says so). `matrix/text_notation.py` stays, as a
builder of test matrices. The old pages are in `documentation/deprecated/`
([`sequence-logic.md`](../../deprecated/sequence-logic.md), [`schemas.md`](../../deprecated/schemas.md)).

---

## 10. What used to be here and is not

Stated plainly so nobody searches for it. These routes belonged to the tempo-based model and were
deleted in P4.2 with the Playground tabs that called them:

- reading one processing step of a stored matrix (`raw`, `collapsed`, `clean`)
- switching granularity, and any BPM parameter
- editing a matrix cell
- transposition
- matrix JSON import and export

If one of these should return on the wall-clock path, it is a new feature request with its own
reasoning, not unfinished work.

Implementation 02 deleted the text-notation routes in Phase 1 (§9) and the old `/library` router in
Phase 3 (§7).

Implementation 08 deleted no route. It removed two choices and one page:

- **The engine choice.** `POST /matrix/transcribe` refuses every engine except `muscriptor` with
  `422`, and `GET /matrix/engines` no longer lists ByteDance or Transkun. Both engines stay in the
  code with their tests, and pieces they transcribed keep their filters.
- **A new model per job.** The model is loaded once per process (`transcription/models.py`), and
  only one transcription runs on the GPU at a time.
- **The Playground's Piano Roll page**, removed in Phase 9. `/playground/piano-roll` redirected
  to the flow page until implementation 02, Phase 15. `GET /matrix/{uuid}/events` stays, because Notes Falling (a view of Play mode
  since implementation 02, Phase 11) draws it. `PUT /matrix/{uuid}/events/removed` stays with its
  tests; no page has called it since Phase 11, when Notes Falling stopped taking notes off.

---

## 11. Where to look deeper

- [`context/08-security.md`](../../../context/08-security.md): the users, the session, the rights
  table, the home network and what this setup does not protect
- [`context/backend/piano-matrix-notation.md`](../../../context/backend/piano-matrix-notation.md):
  `notes.pmn` (and the in-memory shape of `events.json`), the columns form, the revisions
- [`time-matrix.md`](time-matrix.md): every schema 2.0 field
- [`events-to-sheet.md`](events-to-sheet.md): how a response is derived
- [`editing-and-compose.md`](editing-and-compose.md): the splice and the insertion
- [`rhythm-and-annotations.md`](rhythm-and-annotations.md): `sheet.json`
- [`transcription-pipeline.md`](transcription-pipeline.md): what happens before any of this
- [`paths-and-data.md`](paths-and-data.md): where each file of these routes lives
- `http://127.0.0.1:8765/docs`: the generated, always-current field reference
