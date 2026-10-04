# Task 5.1.1 — Playground artifact repository · progress report

Status: **done**. Date: 2026-07-27.

## Summary

`storage/repository.py` + the playground half of `api/library.py`.

| Function | Role |
|----------|------|
| `save_version(artist, track, matrix, *, comment, overwrite, version, parent, audio)` | write a `vN_gX` folder |
| `save_two_hands(artist, track, right, left, …)` | one folder, two `.npz` |
| `load_version` / `load_latest` / `load_parent` | read back |
| `list_tracks` / `find_tracks(query)` / `list_versions` | browse |
| `ensure_track` / `rename_track` | track-level metadata |
| `parent_pointer(version)` | build the `parentMatrix` to record |
| `delete_version` | remove a folder and its history entry |

Endpoints: `GET/POST /library/playground`, `GET/PATCH /library/playground/{artist}/{track}`,
`GET/DELETE /library/playground/{artist}/{track}/{folder}`. The frontend's
`src/api/library.ts` was rewritten to match, with `PlaygroundTrack` and `VersionHistoryEntry` as
true mirrors of the Pydantic models.

## Three decisions worth reading

**A version is a musical state; a granularity is a view of it.** `save_version(..., version=1)`
pins the number, which is how `v1_gsc` and `v1_gn` end up as the same take collapsed two ways
rather than as two versions. `v2` means the *music* changed. This is what makes the
`avicii/levels` tree in `project-features.md` come out right, and the scenario test builds exactly
that tree.

**Renaming a track never moves its folder.** `rename_track` changes `artistName`/`trackName` and
leaves `artistSlug`/`trackSlug` alone. A folder move would break every `parentMatrix` pointer and
every library promotion referencing it — the slug is an identity, the name is a label. Search
(`find_tracks`) matches the **real names**, so the user never has to know slugs exist.

**Edits record lineage instead of history.** `save_version(..., parent=parent_pointer(base))`
writes a `parentMatrix` pointing at the folder the edit came from. "Back to the original" is
`load_parent()` — loading a real saved state, not undoing — and the edited version stays exactly
where it is. That is subtask 5.1.1.3's rule made structural.

## Errors found and how they were solved

1. **Overwrite duplicated history entries.** The first version appended a second
   `VersionHistoryEntry` for the same folder, so `v1_gsc` appeared twice with different comments.
   `_record_history(..., replace=True)` now drops the existing entry for that folder first. Pinned
   by a test asserting the history has exactly one `v1_gsc` carrying the *new* comment.
2. **The smoke test's `501` list shrank again** — `/library/tracks` is real now; only
   `/library/playlists` remains a placeholder (Epic 10).

## Deviations from the task file

- Added `delete_version`, `load_latest`, `find_tracks`, `save_two_hands` and the
  `GET/DELETE .../{folder}` endpoints.
- `save_two_hands` writes the right hand as the version's primary matrix **and** both hands as
  `_right`/`_left` files. One metadata, one folder, three `.npz` — Epic 9 reads the pair, Epic 7
  reads the primary.

## Verification

```
pytest tests/test_repository.py   # 28 passed (shared with Task 5.2.1)
pytest                            # 439 passed, 1 skipped
mypy, flake8, black               # clean
npx tsc -b, npm run lint          # clean
```

The acceptance criterion is `test_the_avicii_levels_scenario`, which builds `v1_gsc`, `v1_gn`,
`v2_gn` and asserts both the history order and the files on disk.

Also covered: matrix round-trip through save/load, version numbering, the overwrite flag and its
history behaviour, two-hands saving and its shape check, parent lineage including the original
staying untouched, search by real name, renaming keeping the slug, deletion, and every endpoint
including the `409` on a duplicate save and `404`s on unknown paths.

## Manual trial for the supervisor

```bash
cd aitu-backend && make serve
```

```bash
# Save the same matrix twice; the second is v2.
M=$(curl -s "127.0.0.1:8765/matrix/<audio-uuid>?granularity=negra")   # or any envelope
curl -s -X POST 127.0.0.1:8765/library/playground -H 'Content-Type: application/json' \
  -d "{\"artistName\":\"Avicii\",\"trackName\":\"Levels\",\"comment\":\"first\",\"matrix\":$M}"
curl -s 127.0.0.1:8765/library/playground | python3 -m json.tool
```

Then look at `aitu-backend/data/playground/avicii/levels/` on disk. `metadata_track.json` is
meant to be readable by a human — if the history entries do not tell you what you did and why,
say so, because that is the file you will be reading in six months.

## For the next worker

- **Epic 6/7 save buttons**: `POST /library/playground` with the matrix envelope and a comment.
  Pass `parentVersion` whenever the user is saving an *edit* of something they loaded.
- **Epic 11** (range editing) is the main consumer of `parent_pointer` / `load_parent`.
- Never move a track folder. If a rename needs to change a slug, that is a copy-and-repoint
  operation, not a rename.
