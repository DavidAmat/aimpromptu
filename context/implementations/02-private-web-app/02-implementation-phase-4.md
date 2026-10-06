# 02: Phase 4 report: users, login and the home network

Plan: [`02-plan.md`](02-plan.md) sections 9 and 18, and section 20, Phase 4. Checklist:
[`02-checklist.md`](02-checklist.md). Branch `feat/phase-4`, made from `master` at `7fb664c`
(Phase 3 merged at the start of this session). Done 2026-10-06 on the Ubuntu machine. The security
page of the app is new: [`../../08-security.md`](../../08-security.md).

# 1. Summary

| Story | Result |
|---|---|
| 4.1 The backend | `auth/` (Argon2id, a 30-day `HttpOnly` session cookie renewed on use, the slow-down after five wrong passwords), `/auth` and `/admin/users`; one check on every router (the session, then the rights of section 9.3 for the project the route names); the master user's first password from `.env`; jobs with an owner. 22 new tests, one per row of the rights table with two users |
| 4.2 The frontend | The sign-in page, the guards (every page needs a user, Admin needs the master user), the user menu (Change password, Light / Dark / System, Sign out), Admin → Users; the dark scheme for the drawing code, with the piano sheet kept white |
| 4.3 The network | The page on every address (`WEB_BIND`, default `0.0.0.0`), Vite's allowed host names; the backend stays on `127.0.0.1`. Checked from Ubuntu at `http://192.168.0.112:5173`, and by the user from the Mac at `http://ubuntu:5173` |
| 4.4 Documentation | `context/08-security.md` (new), and the pages of section 6 |

Checks at the end (section 5): backend 1,046 tests on the GPU, 1 failed (the known one); every
frontend check passes signed in, `check:flow` with the live transcription; `bench:sheet` and
`time:flow` at the Phase 3 numbers.

# 2. Story 4.1: the backend

## 2.1 Who the request is

`auth/context.py` holds the user of the request in a context variable. `auth/dependencies.py`
sets it in `signed_in`, which is **`async` on purpose**: a value set in the request's own task is
copied into the worker thread that runs a plain route, so every function under the route (above
all `db/users.current_user_id`, which `audio/store.create` uses for the owner of a new project)
sees the user. A value set in a sync dependency would stay in that dependency's own thread. Code
outside a request (the migration, the scripts, most tests) has no user and acts as the master user.

**Jobs** (`transcription/jobs.py`) record `owner_id`, run their work in a copy of the request's
context (so a YouTube download or a transcription makes its project for the user who started it),
and join a running job with the same key only for the same owner. The progress and status routes
answer 404 to another user; the master user follows every job (section 18).

## 2.2 Sign in and the session

- `POST /auth/login`, `POST /auth/logout`, `GET /auth/me`, `PUT /auth/password`
  (`api/auth.py`). A wrong username and a wrong password get the same answer.
- `auth/sessions.py`: 32 random bytes in the cookie `aitu_session`, only their SHA-256 in
  `sessions`; `HttpOnly`, `SameSite=Lax`, not `Secure` (plain HTTP at home); 30 days, renewed when a
  request comes more than an hour after the last renewal. A disabled user's sessions stop at once.
  Changing one's password ends every other session and keeps this one. Signing in deletes the
  expired sessions (each script run signs in).
- `auth/throttle.py`: five wrong passwords for one username within a minute make each next try wait
  2 s, 3 s, up to 10 s, before the password is checked; a correct one clears the count.
- Measured: signing in takes about 50 ms (Argon2); the session check adds about 1 ms to a request
  (`GET /audio/{id}` answers in 1.3 ms, `/health`, which has no check, in 0.6 ms).

## 2.3 The rights (Task 4.1.2)

`auth/rights.py` is the table of section 9.3. `main.py` adds two dependencies to every router of
the projects (`signed_in`, `project_rights`) and two to the master user's routers (`signed_in`,
`master_only`: `/admin`, `/frame-examples`). `project_rights` reads the project from the route's
path parameter (`audio_uuid`, the id of a part, or `project_id`):

- not readable: **404**, the same answer as a project that does not exist, so an address tells
  nothing about another user's work;
- readable, not writable: **403**;
- `GET` reads; any other method writes, except five `POST` routes that only compute an answer or copy
  into the user's own vault (`/time/{id}/score`, `/time/{id}/ladder-preview`,
  `/pieces/{id}/hands/predict`, `/audio/{id}/trim`, `/projects/{id}/duplicate`).
  `POST /matrix/transcribe` names its part in the body and checks it itself (`require_part`).

Two choices, written in the plan:

- **The master user has no right over another user's private projects.** The plan's table gives
  none, and an Admin who could read every library would make "private" a word the app does not keep.
- **The owner writes a Private Library project in place until Phase 6.** Section 9.3 says "through
  a copy in the vault"; that flow is Phase 6. Enforcing it now would have made the 30 migrated songs
  read only. One line of `rights.py` changes in Phase 6.

Lists are scoped: `GET /audio/` is the user's own projects; `GET /video` the user's own videos (the
master user sees all of them in Lab).

## 2.4 The master user and the users (Task 4.1.3)

`db/users.ensure_master_user` sets the master user's password from `AITU_MASTER_PASSWORD` **only
while it has none**, so a password changed in the app is never overwritten by `.env`.
`/admin/users` (master user only) lists, creates (username of 2 to 32 letters, digits, `.`, `_`,
`-`; a password of at least 8 characters), disables and enables, and resets a password; the master
user cannot be disabled.

**On this machine**, `.env` did not exist. It now holds a generated `AITU_MASTER_PASSWORD`
(`chmod 600`, ignored by git), so the user can sign in, and the browser scripts sign in with it.
The user changes the password from the user menu; the line in `.env` is then not read again.

*Later the same day:* the user changed the master password from the user menu (section 8), so the
line in `.env` no longer works for the browser scripts; they need `AITU_CHECK_USERNAME` and
`AITU_CHECK_PASSWORD` (the user's password, or a test user). The user also added
`AITU_DATABASE_DIR=/mnt/ssd2/aimpromptu/.database` to `.env` and removed the `.database` link from
the repository (the Phase 3 report, section 2.1).

**A defect found by the screenshots:** SQLite keeps no time zone, so a user created two minutes
earlier showed "2 h ago" (the browser read UTC as Barcelona time). Every time column now uses a
`UTCDateTime` type that reads the value back in UTC; Alembic finds no change to the tables.

## 2.5 The tests

Every test acts as the master user, with no cookie (`dependencies.test_user`, set in
`tests/conftest.py`), unless it is marked `real_login`; then it signs in through `/auth` like the
browser. The tests also clear `AITU_MASTER_PASSWORD`, which the container now receives from `.env`.

- `test_auth.py` (13): every route but signing in answers 401; the cookie's flags; one answer for a
  wrong user or password; the slow-down (2 s, 3 s, then 4 s waiting) and its minute; sign out; renewal
  and expiry; expired sessions deleted; changing a password (and the other sessions end); the master
  user's first password from `.env` and not overwritten later; Admin → Users end to end with a
  second user; Argon2id hashes.
- `test_rights.py` (9): **a test per row of the table** with the master user, anna and joan: the
  Personal Vault, the Private Library (shared and not), the Public Library (with a read-only
  `POST`), a request, Users and Lab; plus the scoped list, the owner of an upload, the owner of a
  job, a job that makes its project for its owner.

Three older tests needed a change: the waveform test asked an unknown project for a refused value
and now gets the 404 of the rights check first (it uses a real part now), and two tests that read
the user's library now read the real `.database/` (read only; they read the deleted
`aitu-backend/data/` before, and would have been skipped).

# 3. Story 4.2: the frontend

- **Sign in** (`/login`, `pages/LoginPage.tsx`): the logo, **Username**, **Password**, **Sign in**,
  and one line when it fails. It returns to the address the user came from (`?next=`, only an
  address of the app).
- **The guards** (`layout/RequireUser.tsx`): every page under the shell needs a user; while the
  page asks `GET /auth/me` it draws nothing (a few milliseconds). A **401** from any request
  (`SIGNED_OUT_EVENT` of `api/client.ts`) forgets the user and opens the sign-in page. Admin pages
  need the master user and show "Page not found" to anyone else.
- **The sidebar**: Projects; for the master user an Admin group with **Users** and **Lab**.
- **The user menu**: the username and the role, **Change password** (current, new; the other
  devices are signed out), the theme **Light / Dark / System**, **Keyboard shortcuts**, **Sign out**.
- **Admin → Users** (`pages/admin/UsersPage.tsx`): a table (username, role, status, created),
  **New user**, and per row **Reset password** and **Disable** (with a confirmation) or **Enable**.
- **A project the user cannot open** now says "There is no project of yours at this address." with
  **Open Projects**, instead of "404 — No audio with uuid …".
- **The Video choice** of the Source step is shown to the master user only, because a video project
  still opens in Lab until Phase 5 makes the video a step of the project.

## 3.1 The dark scheme

The Phase 1 report warned that the drawing code reads the light tokens directly. Now `ui` is a copy
that `applyScheme` changes in place, `SchemeSync` (in `main.tsx`) follows MUI's mode, and the
components that draw with `ui` call `useScheme()` and re-render; the waveform's paint effects take
the scheme in their dependencies. **Nothing is remounted**, so a sheet with unsaved changes keeps
them (screenshot 21: the Audio step switched from dark to light from the menu, repainted in place).
Lab's pages, development tools with many canvases, are drawn again from the start on a change.

**A defect found by the screenshots:** in dark mode the piano sheet's black engraving was drawn on
the dark page (plan P-8 says the sheet is white paper in both schemes). The sheet's box now has the
`paper` colour (screenshot 23). The piano roll keeps its own colours, as the plan says for the music.

# 4. Story 4.3: the network

- `compose.yaml`: the page on `${WEB_BIND:-0.0.0.0}:5173`; the backend unchanged on `127.0.0.1`.
- `vite.config.ts`: `allowedHosts` `localhost`, `ubuntu`, `david-ubuntu`, `david-ubuntu.local` and
  `AITU_ALLOWED_HOSTS`; addresses are always allowed.
- Measured on Ubuntu: `ss` shows 5173 on `0.0.0.0` and 8765 on `127.0.0.1`;
  `http://192.168.0.112:5173/login` answers 200; a request with another host name answers 403
  (Vite); the backend without a cookie answers 401.
- **Not measured from the Mac**: Ubuntu has no access to the Mac (implementation 08, Phase 0). The
  user checks `http://ubuntu:5173`.

**The browser scripts sign in** (`aitu-frontend/scripts/session.mjs`): the master user's name and
password from `.env` (or `AITU_CHECK_USERNAME` / `AITU_CHECK_PASSWORD`), the cookie added to every
`fetch` and to every Playwright page. `check:flow`, `bench:sheet`, `time:flow` and `screenshot` use
it; `screenshot` gains `--theme dark` and `--signed-out`. `aitu-backend/scripts/bench_pieces.py`
signs in too.

# 5. The checks

| Check | Result |
|---|---|
| Backend, `make test-backend` (GPU free) | 1,046 tests: 1,045 passed, 1 failed, the known `test_the_worked_example_at_00_46_prints_three_equal_corcheas` |
| `flake8`, `black`, `mypy` on the new modules | clean |
| `tsc -b`, `npm run lint`, `npm run build` | clean; the build has the chunk-size warning of Phase 0 |
| `check:render`, `check:history`, `check:note-names`, `check:geometry`, `check:cuts`, `check:notes` | 60, all, 15, all, all, all passed |
| `check:flow`, signed in, with the live transcription | every check passed, no console error |
| `bench:sheet` (Elefants, 4 moves) | a hand move 230 ms median (Phase 3: 215 ms with 6 moves) |
| `time:flow`, signed in, the first piano sheet | 0.6 s, 0.9 s, 0.5 s (Phase 3: 0.59, 0.90, 0.44) |
| `bench_pieces.py` (Elefants) | runs signed in |
| `scripts/docs/check-links.py` | passes |

The backend count grew from 1,024 (Phase 3) by the 22 tests of section 2.5.

# 6. The 13 checks of the 09 guidelines

Run on the pages this phase made or touched, with the screenshots of
[`screenshots/phase-4/`](screenshots/phase-4/). The pages with a second user were taken on a
**throwaway instance** (a backend on port 8766 and Vite on 5174, on a `.database/` in the
scratchpad, with the users anna and joan and one small project each), so no user was added to the
real database. Shots 23 to 26 are the real app, opened read only.

| # | Check | Result |
|---|---|---|
| 1 | One sentence | Sign in: enter the app. Users: manage who can sign in. User menu: my account and the theme |
| 2 | Every sentence a label, control or fact | Sign in has three words besides the fields; the only helper lines are format limits (username characters, 8 characters) |
| 3 | Words above the first content | Sign in: the name of the app; Users: "Users", "New user" |
| 4 | Very wide | The Users table keeps its width under the title, the button beside the title |
| 5 | Narrow (390 px, shots 11, 12) | 0 px of horizontal overflow on Users; the sign-in form fits |
| 6 | Longest, shortest, none | A long username truncates in the table and the menu, with the full name on hover |
| 7 | Buttons say what happens | "Sign in", "Create user", "Set the password", "Change password", "Disable joan", "Sign out", "Open Projects" |
| 8 | Helper lines | Only the format limits |
| 9 | Loading, empty, partial, error | Users: skeleton rows, an error with **Try again**; sign in: one line on a wrong password; a closed project: a sentence and **Open Projects** |
| 10 | Tab through it | Sign in: Username, Password, Sign in, Enter submits; the user menu is a menu with a segmented theme choice |
| 11 | Internal names | Gone from the closed-project page: "404", "uuid". No "session", "token" or "Argon2" on any screen |
| 12 | First-time user | Every label is the user's word |
| 13 | Anti-patterns | No lecture on the sign-in page, no "forgot password" link that does nothing |

| Shot | Page |
|---|---|
| 01, 02 | Sign in; a wrong password |
| 03 | The master user opens anna's project: "There is no project of yours at this address." |
| 04 to 06 | Projects of the master user; the user menu; Change password |
| 07 to 10 | Users; New user; a row's menu; Disable joan |
| 11, 12 | 390 px: sign in, Users |
| 13 to 16 | anna: her Projects (no Admin), New project without the Video choice, an Admin address (Page not found), the master user's project (not hers) |
| 17 to 22 | Dark: sign in, Projects, the user menu, the Audio step, switched back to light in place, Users |
| 23, 24 | Dark, real projects: Superestrella's sheet on white paper; Come on Eileen's notes |
| 25, 26 | Dark Lab; the real Projects (39 rows) signed in |

The console errors of these pages are the expected answers: `GET /auth/me` answers 401 while signed
out, and another user's project answers 404.

# 7. Documentation

- New: [`../../08-security.md`](../../08-security.md): the users, the session, the rights table,
  the network, and what this setup does not protect (plain HTTP on the Wi-Fi, Vite's development
  server, the open Docker port 2375 of the machine, the open API docs, the slow-down kept in memory,
  the password in `.env`).
- Updated: `endpoints.md` (`/auth`, `/admin`, the 401 / 403 / 404 rules, job owners), `api.md`,
  `backend/README.md`, `09-coding-conventions.md`, `02b-local-setup.md` section 12,
  `04-local-development.md`, `README.md`, `03-services-overview.md`, `00-index.md`,
  `00-documentation-instructions.md`, `00-project-complete-overview.md`, `02-tech-stack.md`,
  `frontend/README.md`, `pages.md`, `components.md`, `aitu-frontend/README.md`, `color-palette.md`,
  `aitu-backend/README.md`, `.env.example`.
- The plan: "as built in Phase 4" notes in sections 9.3 and 9.4.

# 8. Open points

- **The check from the Mac** of `http://ubuntu:5173` (Task 4.3.1): done by the user on 2026-10-06,
  who signed in and changed the master password from the user menu (`.env`'s line is no longer read).
- **The Docker port 2375** of the machine is open on the network with no authentication. It is not
  part of this app and it is the largest risk on the security page; closing it is the user's choice.
- **`projects.step`** is still not kept current at runtime (Phase 3 report); Phase 5 owns it.
- **A video project for a plain user** waits for Phase 5 (the Video choice is hidden for them).

# 9. Learnings for later phases

- **Set the user in an `async` dependency.** A context variable set in a sync dependency stays in
  that dependency's thread and the route never sees it.
- **A dependency that raises comes before the validation of the query**: a test that asked an
  unknown id for a refused value got the 404 first.
- **SQLite returns times without their zone**; keep `UTCDateTime` on every new time column.
- **The container gets `.env`**: tests must clear any variable that changes behaviour
  (`AITU_MASTER_PASSWORD`).
- **Screenshots with a second user** on a throwaway instance (`AITU_DATABASE_DIR` in the
  scratchpad, a native backend on 8766, Vite on 5174 with `AITU_API_PROXY`), so the real database
  gets no test users. Set `AITU_DATABASE_DIR` explicitly for such an instance: since 2026-10-06 the
  real folder is named by `.env`, and the default `<repository>/.database` no longer exists.
- **Look at the music in dark mode**: a page of the app can follow the theme while the drawing it
  holds must not.
