# Task 5.2.1 — Library promotion · progress report

Status: **done**. Date: 2026-07-27. This closes Epic 5's backend.

## Summary

`storage/promotion.py` + the library half of `api/library.py`.

| Function | Role |
|----------|------|
| `promote(artist, track, folder, *, promotion_name, as_additional)` | copy a version into the library |
| `rollback(artist, track)` | restore the previously promoted version |
| `list_library_tracks(tag=, search=)` / `read_library_track` | browse |
| `set_tags` | replace a track's tags |
| `default_promotion_name(track, artist)` | `"Levels - Avicii"` |
| `load_promoted` / `promoted_matrix_path` | read a promotion back |

Endpoints: `POST /library/promote`, `POST /library/rollback`, `GET /library/tracks`,
`GET /library/tracks/{artist}/{track}`, `POST /library/tags`, and
`GET /library/promotion-suggestion/{artist}/{track}` — which pre-fills the dialog with the
suggested name and what is currently live.

## Three rules, all about not losing work

**Promotions are named, never numbered.** A performer picks *"Levels (Chill) - Avicii"*, not
`v3_gn`. The name defaults to `"<Track> - <Artist>"` and the dialog lets you edit it before
confirming — which is exactly why the suggestion endpoint exists separately from the promote one.

**Promotion copies, it does not reference.** The library gets its own `.npz` (both hands, when the
version has them) plus an **embedded snapshot** of the version's `metadata.json`. Deleting the
playground folder later cannot break a piece you play from. That embedding is why
`Promotion.versionMetadata` exists in the Task 1.3.2 schema.

**Nothing is ever deleted.** Re-promoting deactivates the previous entry and points `rollbackTo`
at it; `rollback` flips the two. The `promotions` list is append-only, so the full history of what
was live and when survives, and rolling *forward* again is just another rollback.

`as_additional=True` — the dialog's "keep the current one too" checkbox — leaves both live, which
is how one track carries two arrangements. A same-named promotion is still superseded in that
mode, so promoting the same arrangement twice does not leave two live copies of it.

## Errors found and how they were solved

1. **The re-promotion filter was unreadable and probably wrong.** My first version had a single
   list comprehension mixing three conditions (`name != x or not active or as_additional`) that I
   could not convince myself was correct. Split into two explicit branches — replace-all versus
   supersede-by-name — with a comment on each. The rollback tests are what forced the issue.
2. **`rollback_to` after an additional promotion.** Promoting `as_additional` must *not* move the
   rollback pointer: nothing was replaced, so there is nothing to roll back to. Handled explicitly
   rather than falling out of the general path.

## Deviations from the task file

- Added `GET /library/promotion-suggestion/...`, `POST /library/tags`, and
  `GET /library/tracks/{artist}/{track}`. The dialog needs the first, and Epic 10's browsing needs
  the other two — defining them here keeps the library metadata writes in one module.
- `rollback` returns the whole updated `LibraryTrackMetadata` rather than a status, so the UI can
  re-render without a second request.

## Verification

```
pytest tests/test_repository.py   # 28 passed (shared with Task 5.1.1)
pytest                            # 439 passed, 1 skipped
mypy, flake8, black               # clean
```

The acceptance criterion — promote, re-promote, rollback, multiple named versions — is covered by
five tests:

- promotion copies the `.npz` and embeds the metadata;
- the name is editable;
- re-promoting replaces but keeps the history, and sets `rollbackTo`;
- `as_additional` leaves two promotions live side by side;
- **rollback restores the previous one, deletes nothing, and can be repeated to roll forward.**

Plus: two-hands promotions copying both hand files, tag and name filtering, refusing a rollback
with no history (`409`), and a test that reads everything back from disk to prove the history
survives a restart.

The full HTTP flow — save two versions, load one, get the suggestion, promote, re-promote,
rollback, tag, filter — is one end-to-end test.

## Manual trial for the supervisor

Epic 5's exit criterion is *"from any Playground tab a matrix state can be saved as a version,
listed, reloaded, and promoted; history survives restarts and rollback restores the previous
version."* The backend half is testable now; the buttons are Epics 6, 7 and 10.

```bash
cd aitu-backend && make serve

# ...after saving two versions of avicii/levels (see the 5.1.1 report):
curl -s 127.0.0.1:8765/library/promotion-suggestion/avicii/levels
# {"suggestedName":"Levels - Avicii","currentPromotions":[]}

curl -s -X POST 127.0.0.1:8765/library/promote -H 'Content-Type: application/json' \
  -d '{"artistSlug":"avicii","trackSlug":"levels","versionFolder":"v1_gsc","promotionName":"Levels (Chill) - Avicii"}'

curl -s -X POST 127.0.0.1:8765/library/promote -H 'Content-Type: application/json' \
  -d '{"artistSlug":"avicii","trackSlug":"levels","versionFolder":"v2_gsc","promotionName":"Levels (Fast) - Avicii"}'

curl -s -X POST 127.0.0.1:8765/library/rollback -H 'Content-Type: application/json' \
  -d '{"artistSlug":"avicii","trackSlug":"levels"}' | python3 -m json.tool
```

After the rollback, `Levels (Chill)` is `active: true`, `Levels (Fast)` is `active: false`, and
both are still listed. **Then restart the backend and re-read it** — that is the "survives
restarts" half of the criterion.

Worth a look on disk: `data/library/tracks/avicii/levels/metadata_library_track.json`. If the
promotion names and dates do not read like a log you would trust, tell me.

## For the next worker

- **Epic 7's promote button**: call `GET /library/promotion-suggestion/...` to open the dialog
  pre-filled, then `POST /library/promote` with the (possibly edited) name and the checkbox state.
- **Epic 10** reads `GET /library/tracks?tag=&search=`; `active_promotions()` on each track is what
  the performer picks from, by name.
- **Epic 10, Story 10.3** (playlists) is the last `501` under `/library`. `PlaylistMetadata` and
  `paths.playlist_metadata_path` already exist from Tasks 1.3.2 and 1.4.1.
- Never delete a promotion. If the user wants one gone, deactivate it.
