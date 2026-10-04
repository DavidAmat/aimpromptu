# Task 5.2.1 — Library promotion

`storage/promotion.py`: move a playground version into the consolidated library.

## Subtask 5.2.1.1 — Promotion flow

`promote(artist, track, version_gran, promotion_name, as_additional=False)`:

- copy the `.npz` and embed the version's `metadata.json` into `library/tracks/<artist_slug>/<track_slug>/metadata_library_track.json`
- default: replace the current promoted version, keeping full history; `as_additional=True` (dialog checkbox) keeps multiple promoted versions side by side
- `promotion_name` defaults to "<Track> - <Artist>" and is editable (e.g. "Levels (Chill) - Avicii") so users pick by name, never by `v3_gn` codes

## Subtask 5.2.1.2 — History and rollback

`metadata_library_track.json` keeps every promotion (source version, name, date). `rollback(track)` restores the previously promoted version. Rollback never deletes files, only moves the "current" pointer.

## Subtask 5.2.1.3 — Endpoints and dialog

- `POST /library/promote`, `GET /library/tracks`, `POST /library/rollback`
- Playground promotion button opens a dialog: suggested name, replace-vs-additional checkbox, confirm

## Acceptance

Promote, re-promote, rollback scenario test; multiple named versions of one track listable.
