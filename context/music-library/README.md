# The music library

The music library is the catalogue: songs, artists (with their several names), albums, and the
versions that join a song to a project ([app context](../app/01-app-context.md), "Music Library").
It exists in two scopes that use the same tables (`songs`, `artists`, `artist_names`, ... of
[07-database.md](../07-database.md)):

| Scope | What it is | Built in |
|---|---|---|
| **Private Library** | Each user's own: finished projects, filed as versions of the user's own songs and artists, named as the user likes | Implementation 02, Phase 6: [private-library.md](private-library.md) |
| **Public Library** | Everyone's: the songs and artists of the chart history, and the versions the master user accepted | Phases 12 and 13 (`reconciliation.md`, `ontology.md`, `popularity.md`, to come) |

Requests to publish from one to the other (`requests.md`) come with Phase 14.

A project is the work; a song is the catalogue entry; a **version** joins them. Work in progress
lives in Projects (the Personal Vault, [frontend/projects.md](../frontend/projects.md)); finished
work lives in a library, under a song, as a version.

## Pages

| Page | |
|---|---|
| [private-library.md](private-library.md) | The Private Library: songs, artists and names, versions, **Save to library**, **Edit**, the history of a version |

## Where to look deeper

- The plan: [implementations/02-private-web-app/02-plan.md](../implementations/02-private-web-app/02-plan.md)
  sections 8.6, 15 and 16
- The parallel work that downloads the public data:
  [public-library-build/](../implementations/02-private-web-app/public-library-build/)
- The tables: [`paths-and-data.md`](../../documentation/services/backend/paths-and-data.md) section 6
