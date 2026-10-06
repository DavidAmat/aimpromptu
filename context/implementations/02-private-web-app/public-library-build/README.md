# 02-a: The public music library

**State: planned, 2026-10-05.** Eight decisions are in the plan (D-1 to D-8). Two questions are
raised only if the download or the years require them (Q-1, Q-2). Five phases, none started.

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
