# Deployment

**This version is deployed on one machine at home, and there is no hosted environment.** The app
context plans two stages: first a personal app, run locally on the owner's GPU and reached from the
home network; then, if it is worth it, a production version in the cloud
([app/01-app-context.md](app/01-app-context.md)). Implementation 02 built the first stage.

## What runs today

| Part | Where |
|---|---|
| The backend (`aitu-backend`), with the GPU | A Docker container on the Ubuntu machine (`david-ubuntu`, RTX 4090), on `127.0.0.1:8765` only |
| The page (`aitu-frontend`, Vite's development server) | A Docker container on the same machine, on port 5173 of every address (`WEB_BIND`), so any device at home opens `http://ubuntu:5173` |
| The data | One folder, `.database/`, on this machine `/mnt/ssd2/aimpromptu/.database` (`AITU_DATABASE_DIR` in `.env`), mounted into the backend ([07-database.md](07-database.md)) |

`make up` builds and starts both containers; there is no deploy step beyond it. How to start, stop,
test and reach it: [04-local-development.md](04-local-development.md). The machine itself:
[02b-local-setup.md](02b-local-setup.md) section 12. Who can sign in and what the home network does
not protect: [08-security.md](08-security.md).

**Moving the app to another machine** is the repository, a `.env`, and a backup of `.database/`
(`make db-backup` on the old machine, `make db-restore FILE=…` on the new one).

## What a production version needs

None of this is built. Each line is the production answer to a risk that
[08-security.md](08-security.md) accepts for a home network, or to a choice of the app context.

| Need | Why |
|---|---|
| A production build of the page, served with the API behind one reverse proxy (Caddy or nginx), with HTTPS | Today Vite's development server answers on the network and the traffic is plain HTTP |
| A cloud host with a GPU for the transcription, or a queue to one | MuScriptor runs on the local RTX 4090 |
| `.database/` as a volume of the instance, or the tables in Postgres and the files in object storage | The tables are SQLAlchemy models with Alembic revisions, so the same code can move to Postgres (plan P-2) |
| Sign-up, password recovery by email, a limit on sign-in tries per address | Users are made by the master user today |
| No YouTube download and no video reader | The app context leaves them out of the production version |
| Offline downloads per project (a Progressive Web App) | Decision Q-7: left for the production version |
| A CI pipeline that runs the backend tests, the frontend checks and the link checker | Today they run by hand on the Ubuntu machine ([04-local-development.md](04-local-development.md)) |
