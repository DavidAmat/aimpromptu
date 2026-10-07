# 02-a: The public music library

**State: finished, 2026-10-07.** Phases 1 to 5 are done. How the download ran, where the files
were moved, and what `library.sqlite` contains is
[`02-a-public-library-build-implementation.md`](02-a-public-library-build-implementation.md).
Phase 12 and Phase 13 of the app plan read that file. Q-1 was not raised. Q-2 was not large.

The brief is [`02-a-public-library-build-prompt.md`](02-a-public-library-build-prompt.md). The plan is
[`02-a-public-library-build-plan.md`](02-a-public-library-build-plan.md). The status lookup is
[`02-a-public-library-build-checklist.md`](02-a-public-library-build-checklist.md).

## What it is for

Download the worldwide charts from musicchartsarchive.com and store songs, artists, albums, lyrics
and rankings in `data/music-library/library.sqlite` (next to the repository, not inside it). Popularity is calculated from the rankings with the
formula already chosen in the app plan.

## What it does not do

It does not import anything into the app, and it does not edit the app plan. Spain, Catalan, genre
and tags are not on this site, so they are not in this database.
