# Security

The app runs on one Ubuntu machine and is opened from the devices of one home network
(implementation 02, plan section 9). This page says who can sign in, what each user can read and
write, how the session works, and **what this setup does not protect**. The production version
(HTTPS, a cloud host, sign-up) is later work.

## Users

- **The master user** is made on the first start from `AITU_MASTER_USERNAME` (default `master`).
  Its first password is `AITU_MASTER_PASSWORD` of `.env`, read only while the user has no
  password: a password changed in the app is never overwritten by `.env`. The master user reviews
  requests (Phase 14), owns the Public Library, manages the users and uses Lab.
- **Other users** are made by the master user in **Admin → Users**: a username (2 to 32 letters,
  digits, dots, dashes, underscores) and a first password (at least 8 characters), which the user
  changes from the user menu. The master user can disable a user and reset a password; both end the
  user's sessions at once. There is no sign-up and no reset by email.
- Passwords are stored as **Argon2id** hashes (`argon2-cffi`, its default parameters). The plain
  password is never stored or logged.

## The session

`POST /auth/login` checks the password and sets a cookie, `aitu_session`:

| Property | Value | Why |
|---|---|---|
| Content | 32 random bytes | Only the SHA-256 of it is in the `sessions` table, so a copy of the database holds no usable session |
| `HttpOnly` | yes | No script of the page can read it |
| `SameSite` | `Lax` | Another site cannot send a request that carries it, except a plain link |
| `Secure` | **no** | The app is plain HTTP on the home network (below) |
| Lifetime | 30 days, renewed on use | A request more than an hour after the last renewal moves the expiry 30 days ahead |

The browser sends the cookie by itself: the page, the API (`/api`, through Vite), the audio files
and the progress streams are all on the page's own address. `POST /auth/logout` deletes the session.
Changing one's own password ends every other session of the user and keeps the current one.

**Wrong passwords.** Five wrong passwords for one username within a minute slow every next try:
2 s, then 3 s, up to 10 s, before the password is even checked. A correct password clears the
count. A wrong username and a wrong password get the same answer, so the answer does not say which
usernames exist.

## Who can read and write what

One check runs on every route before anything else (`aitu_backend/auth/dependencies.py`): without a
valid session the answer is **401**; then the rights below apply to the project the route names.

| Thing | Read | Write |
|---|---|---|
| A project in a Personal Vault | Its owner | Its owner |
| A project in a Private Library | Its owner; users it is shared with (Phase 14) | Its owner (*) |
| The Public Library | Every user | The master user, by accepting requests |
| A request | Its author and the master user | Its author until reviewed; the master user (the decision) |
| Users, Lab | The master user | The master user |

(*) Since Phase 6 a library project is never written in place: its owner reads it (a write answers
**403**), and changes it through **Edit** (a copy in the vault) and **Save to library** (which
replaces the version). Those flows, and the `/library` routes, check the owner themselves. Until
Phase 6 the owner edited it in place.

- A project the user may not read answers **404**, the same as a project that does not exist, so
  an address tells nothing about another user's work. One the user may read but not write answers
  **403**.
- **The master user has no extra right over another user's private projects.** An Admin who could
  read every library would make "private" a word the app does not keep.
- **Export and import** (Phase 5): exporting a project is a read, so a user exports only what they
  may read. An import always makes a new project in the importer's own Personal Vault; the zip is
  read member by member by the names the app expects (a name in it never becomes a path on the
  disk), its size and number of entries are capped, and each audio file must match the hash in its
  name.
- Lists are the user's own: `GET /projects` and `GET /audio/` list the user's projects, and
  `/library` the user's songs and artists (another user's answers `404`); Lab lists every video for
  the master user only.
- A background job (a transcription, a download) records its owner, runs as them (a project it
  makes is theirs), and is followed only by them and the master user.
- `/health` and `POST /auth/login` are the only routes open without a session.

The tests: `aitu-backend/tests/test_rights.py` checks each row of the table with two users and the
master user; `test_auth.py` the sign in, the cookie, the slow-down and Admin → Users.

## The network

- The page (Vite, port 5173) listens on **every address of the Ubuntu machine** (`WEB_BIND`, default
  `0.0.0.0`): any device at home opens `http://ubuntu:5173` or `http://192.168.0.112:5173` and signs
  in. `WEB_BIND=127.0.0.1` in `.env` keeps it to the machine and the SSH tunnel.
- Vite answers only to known host names (`localhost`, `ubuntu`, `david-ubuntu`, the IP addresses,
  and `AITU_ALLOWED_HOSTS`), which blocks a page elsewhere from reaching it through a name it
  controls (DNS rebinding).
- **The backend stays on `127.0.0.1:8765`.** The browser reaches it only through the page's `/api`.
- CORS of the backend is open but without credentials: a page of another origin cannot send the
  session cookie.

## What this does not protect

These are accepted for a personal app on a home network. Each has its production answer.

| Risk | Why it is accepted now | The production answer |
|---|---|---|
| **The traffic is plain HTTP**: a password and the session cookie cross the home Wi-Fi unencrypted, and anyone on the network who captures them can sign in as that user | One home network, few devices, people the owner trusts | HTTPS behind a reverse proxy (Caddy or nginx), then `Secure` on the cookie |
| **Vite's development server** is what answers on the network: it serves the source code of the page, and its own development endpoints | The page's code is not a secret; the data is behind the backend's session check | A production build served by the reverse proxy |
| **Docker's API, port 2375, is open on the network with no authentication** on this machine (found in implementation 08). Anyone at home who reaches it can run any container, and so read `.database/` | It predates this app, and other projects of the machine use it | Close it, or bind it to `127.0.0.1`, or put TLS in front of it. This is the largest risk of the list, independent of this app |
| The FastAPI pages `/api/docs` and `/api/openapi.json` are open | They describe the routes, not the data; every route still needs a session | Turn them off in production |
| The slow-down is per username and in memory: a restart clears it, and many usernames tried in turn are not slowed together | A home network | A limit per address, in a store that survives a restart |
| `.env` holds the master user's first password in plain text | It is read only until the password is changed in the app, and `.env` is ignored by git and readable only by its owner (`chmod 600`) | A secret store |
| A user can read the files of `.database/` on the disk if they have a shell on the machine | Only the owner has an account on the machine | Disk and backup encryption; the database in a managed service |

## Where to look deeper

- The plan: [implementations/02-private-web-app/02-plan.md](implementations/02-private-web-app/02-plan.md)
  section 9.
- The routes: [../documentation/services/backend/endpoints.md](../documentation/services/backend/endpoints.md)
  (`/auth`, `/admin`).
- Opening the app at home: [04-local-development.md](04-local-development.md) and
  [02b-local-setup.md](02b-local-setup.md) section 12.
- Where the users and sessions are stored: [07-database.md](07-database.md).
