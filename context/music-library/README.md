# The music library

The music library is the catalogue: songs, artists (with their several names), albums, and the
versions that join a song to a project ([app context](../app/01-app-context.md), "Music Library").
It exists in two scopes that use the same tables (`songs`, `artists`, `artist_names`, ... of
[07-database.md](../07-database.md)):

| Scope | What it is | Built in |
|---|---|---|
| **Private Library** | Each user's own: finished projects, filed as versions of the user's own songs and artists, named as the user likes | Implementation 02, Phase 6: [private-library.md](private-library.md) |
| **Public Library** | Everyone's: the songs and artists of the chart history, and the versions the master user accepted | Phase 12: the downloaded data mapped onto the tables and its import ([reconciliation.md](reconciliation.md)); Phase 13: the import for real and the pages ([ontology.md](ontology.md), [popularity.md](popularity.md)) |

Requests to publish from one to the other (`requests.md`) come with Phase 14.

A project is the work; a song is the catalogue entry; a **version** joins them. Work in progress
lives in Projects (the Personal Vault, [frontend/projects.md](../frontend/projects.md)); finished
work lives in a library, under a song, as a version.

## Pages

| Page | |
|---|---|
| [private-library.md](private-library.md) | The Private Library: songs, artists and names, versions, **Save to library**, **Edit**, the history of a version |
| [ontology.md](ontology.md) | The entities, the two scopes and how a private row stands for a public one, the metadata of a public song, its versions, **Add to my library**, the Public Library pages |
| [popularity.md](popularity.md) | The popularity of a song: the formula and its weights, the popularity of a decade worked out on the request, how the pages show it |
| [reconciliation.md](reconciliation.md) | The downloaded music library mapped onto the app's tables: the gaps, the identity of a row across runs, the re-entries, the popularity on the real data, the seed list, the import |

## Where to look deeper

- The plan: [implementations/02-private-web-app/02-plan.md](../implementations/02-private-web-app/02-plan.md)
  sections 8.6, 15 and 16
- The parallel work that downloads the public data:
  [public-library-build/](../implementations/02-private-web-app/public-library-build/)
- The tables: [`paths-and-data.md`](../../documentation/services/backend/paths-and-data.md) section 6
