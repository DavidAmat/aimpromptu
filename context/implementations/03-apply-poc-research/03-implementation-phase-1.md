# 03: Phase 1 report: the core inside the backend

Plan: [`03-plan.md`](03-plan.md) section 7, Phase 1. Checklist: [`03-checklist.md`](03-checklist.md). Branch
`feat/migrate-new-logic` (`master` had not moved since Phase 0, so nothing was merged in). Done 2026-10-23 on the
Ubuntu machine. No change visible to the user: no route, no page and no stored file uses the new package yet.

# 1. Summary

| Task | Result |
|---|---|
| 1.1 The copy | `aitu_notation` (research git `a208a92`) is `aitu-backend/src/aitu_backend/sheet/` (27 Python files, the 7 frozen files, the README). The core's `sheet.pmn` copies are gone: the core imports `aitu_backend.pmn.{notes,columns,dense}` and `aitu_backend.matrix.keys`, checked identical again (section 2.2). The tests are `tests/test_sheet_core_golden.py` and `tests/test_sheet_core_chain.py`, the golden files `tests/golden/sheet/` |
| 1.2 The golden tests in the container | 139 of 139 pass inside the backend image, as in the research; the full suite has the Phase 0 results plus these 139 (section 5) |
| 1.3 The command | `aitu-backend/scripts/draw_sheet.py` draws parts with the algorithm and the bars engine. In the container it drew all 33 songs of My library without error: about 1.2 s per song in all (median), of which 1.0 s is the algorithm and 0.19 s the drawing. For all 33 songs the F1, the SVG and the cursor map are byte-identical to the research core run on the same `notes.pmn` (section 4) |

The phase changed three later tasks (plan section 11): the algorithm of Phase 2 needs the beam search hands for the
notes with no saved hand (section 6.1), and the speed of Phase 3 is measured in the container, whose Python build is
slower (section 4.3).

# 2. The copy

## 2.1 Layout and names

The core keeps its inner layout, so `aitu_notation.X` of the research is `aitu_backend.sheet.X` here, including the
inner package `sheet` (`aitu_backend.sheet.sheet.f1`, `.data`, `.matrix`, ...). The doubled name is not pretty, but a
one-to-one map keeps every later comparison with the research (code, golden files, recorded runs) a plain rename,
and Phases 2 to 4 still compare against it. The plan's proposed folder `aitu_backend/sheet/` was used as it was.

| Research (`src/aitu_notation/`) | Backend |
|---|---|
| `__init__.py`, `README.md`, `sheet/`, `proposal/`, `llm/`, `engrave/` with their frozen files | `src/aitu_backend/sheet/`, same files; the two READMEs and the docstrings say where the copy came from |
| `sheet/pmn/keys.py`, `notes.py`, `columns.py`, `dense.py`, `_compat.py` | not copied: `aitu_backend.matrix.keys`, `aitu_backend.pmn.notes`, `.columns`, `.dense` (and, through `dense`, `matrix.time_grid.validate_frame_ms` and `schemas.matrix` for the cell values, which `_compat.py` copied) |
| `sheet/pmn/load.py`, `sheet/pmn/__init__.py` | one module `sheet/sheet/pmn.py`: `notes_from_pmn`, `key_of_sheet_json`, `KEYS`, and the same re-exports (`Notes`, `HAND_*`) |
| `tests/test_core_golden.py`, `tests/test_core_chain.py` | `tests/test_sheet_core_golden.py`, `tests/test_sheet_core_chain.py` (the backend's `pytest` collects only `tests/`) |
| `tests/golden/` (120 engraving cases, 3 proposal songs, 9 checker cases, 1 chain song) | `tests/golden/sheet/` |

The import rewrite was a `sed` of the import lines and `:mod:` references (the `pmn` paths first, then
`aitu_notation.` to `aitu_backend.sheet.`); no other text of the code changed before black (section 2.3).

The boundary test (`test_imports_stay_inside_the_core`) now allows the standard library, numpy, the core itself and
exactly the four backend modules above. Importing the backend's `pmn.dense` brings in the pydantic schemas (about
77 ms once per process); this is acceptable inside the backend.

## 2.2 The `pmn` modules checked again

The plan asked to check again that the backend modules did not change since the research copied them. With the
import lines and the copy header left out, `notes.py`, `columns.py`, `dense.py` (against `aitu_backend/pmn/`) and
`keys.py` (against `aitu_backend/matrix/keys.py`) are identical. The newest commit that touched them, or the three
modules `_compat.py` took values from, is `ce87760` (2026-10-04), before the research copy (`ac45f0c`, 2026-10-16).

## 2.3 Formatting and static checks

The backend's conventions are black (line length 100), flake8 and mypy (`context/09-coding-conventions.md`); the
pre-commit hook is not installed on this machine, and black passed on the whole backend before the copy. The core
was written at about 120 columns.

- **black** reformatted 24 of the 29 new files. black only changes layout (it checks that the syntax tree is the
  same), and the golden tests passed before and after it.
- **flake8** found 16 points in the copy. Four were fixed with no change of behaviour: an f-string with no field
  (`engrave/svg.py`), an unused variable (`engrave/vrv.py`, `beam_overlap`), an unused import (`proposal/pipeline.py`,
  `meter_quarters`, which nothing imports through `pipeline`), and a lambda marked `# noqa: E731` as the core already
  did once in `pipeline.py`. The other 12 are one-letter names `l` in `engrave/layout.py` and `engrave/vrv.py`, which
  keep Verovio's names; `.flake8` has `per-file-ignores` for `src/aitu_backend/sheet/engrave/*.py: E741,E743`.
  `flake8 src tests` now reports only the one point the backend had before (`events_to_matrix.py:68`, E402).
- **mypy** found 148 errors in the copy, mostly optional fields (a frames sheet has `Note.time = None`). The rest of
  `src/` already had 20 errors in 7 files, and `make lint`'s mypy stops before checking anything on the duplicate
  module name of `tests/test_regional_import.py` (the `from tests.X import` style; the new chain test uses it too).
  mypy is therefore not one of the checks the plan keeps green. `pyproject.toml` has an override
  `[[tool.mypy.overrides]] module = ["aitu_backend.sheet.*"], ignore_errors = true`, with the reason written next to
  it; mypy on `src/aitu_backend` is back to the 20 errors of before. Phases 2 to 4 rewrite most of the core and should
  type it and remove the override.

# 3. The golden tests inside the container

| Run | Result |
|---|---|
| Host, backend `.venv`, before black | 139 passed in 5.6 s |
| Host, after black and the flake8 fixes | 139 passed in 6.5 s |
| Backend image (`docker compose run --rm --no-deps backend python -m pytest`, GPU hidden) | 139 passed in 6.8 s |

# 4. The command: `scripts/draw_sheet.py`

## 4.1 What it does

The plan asked for a small route or command that draws a library song with the bars engine, to prove the chain runs
in the container. A command was chosen: a route needs a router, a row in `tests/test_rights.py` and a test, and gives
the user nothing before Phase 5. The command only reads the database.

For each part it reads `notes.pmn` and the key of `sheet.json` (`notes_from_pmn`, `key_of_sheet_json`), runs
`propose(notes, key=key, track=True)` with the notes' own saved hands (the core's default, `hand_sheet_of`), writes
F1 bars with frame anchors, and draws it with `render_song` once cold and `--repeat` times warm. `--out` keeps the
`.f1`, `.svg` and `.cursor.json` of each part; `--layer private` takes every part of My library.

```bash
docker exec aimpromptu-backend-1 python scripts/draw_sheet.py 1a16a836-62b9-483b-af46-d89d0ab1b2d8 --out /work/aimpromptu/.run/sheet-draw/7years
docker exec aimpromptu-backend-1 python scripts/draw_sheet.py --layer private --json /work/aimpromptu/.run/sheet-draw/library.json
```

## 4.2 Byte comparison with the research core

The golden tests prove the copy on the research's own inputs. To prove it also on real data read through the
backend's own `pmn` modules, the same steps ran with the research core (`aitu_notation`, in the research
environment) on the same `notes.pmn` and `sheet.json` files of `.database/` (a scratch script, not kept). For **33 of
33** songs the F1 text, the SVG and the cursor map are byte-identical.

## 4.3 Time per song

Measured in the running backend container on 2026-10-23, while the machine was busy (load average about 12 on 32
threads, another project's containers running), `--repeat 3`. Times in milliseconds.

| Step | Median | Min | Max |
|---|---|---|---|
| Read `notes.pmn` and `sheet.json` | 8 | 2 | 11 |
| The algorithm (`propose`, beat tracking on) | 979 | 559 | 1,591 |
| F1 write | 14 | 7 | 24 |
| Draw, cold (first draw of the song in the process) | 189 | 104 | 380 |
| Draw, warm (median of 3) | 190 | 91 | 427 |
| All, cold | 1,195 | | 1,954 |

The songs have 985 to 3,512 notes (median 1,985) and 52 to 259 bars (median 105). Drawing costs about 2.0 ms per bar
(median), and the SVG is 291 to 872 kB (median 572 kB). "Cold" and "warm" are close because the glyph caches are
filled by the first song of the process, not of each song.

**The container is slower than the host on the same code.** The research measured 138 ms per song (median, phase
15). To find whether the copy or the container causes the difference, the 10 golden songs (the Sonnet sheets of the
viewer) were drawn at the same moment three ways (warm, median of 5 per song, then the median of the 10):

| Where | Code | Median per song |
|---|---|---|
| Host, research environment | `aitu_notation` | 115 ms |
| Host, backend `.venv` | `aitu_backend.sheet` | 118 ms |
| Backend container | `aitu_backend.sheet` | 155 ms |

The copy costs nothing; the container costs about 30 %. The two Pythons differ: the container has Debian's Python
3.12.15 (`python:3.12-slim-bookworm`, GCC, `--enable-shared`), the host has uv's Python 3.12.13 (clang, BOLT, a
static interpreter); numpy is 2.4.5 in both. A shared `libpython` is known to be slower, so the build is the likely
cause. This is an inference: the two builds were not compared alone. The image was not changed now, because a
rebuild restarts the running app; Phase 3 measures the speed (task 3.6) and can try uv's Python in the image.

## 4.4 Every song

The 10 viewer songs of the research are marked. Two parts hold 7 Years (`daf087e9` and `1a16a836`); both have the
same notes.

| Part | Song | Notes | Bars | Algorithm (ms) | Draw cold (ms) | Draw warm (ms) | SVG (kB) |
|---|---|---|---|---|---|---|---|
| `a1c30047` | 1973 — James Blunt | 2,730 | 134 | 1127 | 220 | 221 | 687 |
| `f73116dd` | 2002 — Anne-Marie | 1,615 | 88 | 782 | 165 | 189 | 582 |
| `daf087e9` | 7 Years | 1,458 | 58 | 1255 | 259 | 194 | 498 |
| `1a16a836` (viewer) | 7 Years — Lukas Graham | 1,458 | 58 | 1483 | 165 | 155 | 498 |
| `b2db46eb` | 99 Red Balloons — Nena | 2,599 | 92 | 1429 | 264 | 261 | 872 |
| `b064f815` | Airplanes — B.o.B | 2,056 | 165 | 742 | 184 | 186 | 596 |
| `f4c4de9a` (viewer) | AITANA - SUPERESTRELLA \| PIANO TUTORIAL / COVER | 1,503 | 54 | 1013 | 133 | 135 | 504 |
| `b80e6f5a` (viewer) | Birds of a Feather | 1,449 | 91 | 635 | 129 | 131 | 432 |
| `bef90052` | Bonfire Heart — James Blunt | 1,677 | 55 | 1029 | 203 | 188 | 635 |
| `f285e4b7` | Can't Stop the Feeling — Justin Timberlake | 2,675 | 129 | 1466 | 362 | 427 | 841 |
| `d64acd29` | Club Can't Handle Me — David Guetta | 3,512 | 122 | 1591 | 334 | 350 | 848 |
| `e578f3c0` | Die Young — Kesha | 2,485 | 113 | 910 | 278 | 264 | 726 |
| `3c8d4cfa` (viewer) | Drivers License — Olivia Rodrigo | 1,733 | 70 | 1437 | 159 | 198 | 423 |
| `3633a0c3` | Fate of Ophelia — Taylor Swift | 2,026 | 114 | 1231 | 189 | 189 | 537 |
| `56543911` | Grace Kelly — Mika | 2,144 | 93 | 721 | 180 | 178 | 663 |
| `43faf78e` (viewer) | Halleluyah - Pinchivi | 985 | 98 | 612 | 104 | 91 | 291 |
| `4cb9cb38` (viewer) | Hips Don't Lie — Shakira | 1,614 | 172 | 619 | 173 | 183 | 544 |
| `6eb7af4e` | I Knew You Were Trouble | 1,713 | 59 | 979 | 164 | 178 | 584 |
| `0815f602` | La Tortura — Shakira | 2,154 | 176 | 762 | 306 | 287 | 647 |
| `c0edc9b0` (viewer) | Moonlight Shadow — Mike Oldfield | 2,384 | 161 | 1085 | 316 | 294 | 737 |
| `51b12412` | Party in the USA | 1,738 | 107 | 721 | 175 | 166 | 545 |
| `2ed0f379` (viewer) | Poker Face — Lady Gaga | 1,985 | 107 | 1051 | 267 | 257 | 552 |
| `12f777af` | Raise Your Glass | 1,814 | 120 | 1047 | 186 | 228 | 572 |
| `68e277fe` (viewer) | Shut Up and Dance — Walk the Moon | 1,992 | 72 | 1093 | 199 | 198 | 598 |
| `aa07c1c0` | Stay the Night — James Blunt | 1,470 | 108 | 659 | 138 | 148 | 457 |
| `dff5097c` | Stronger — Kelly Clarkson | 2,076 | 105 | 878 | 221 | 213 | 537 |
| `a585f9eb` | Superestrella — Aitana | 1,343 | 52 | 691 | 111 | 111 | 462 |
| `92255337` (viewer) | The One That Got Away — Katy Perry | 1,618 | 259 | 702 | 181 | 190 | 477 |
| `96768e80` | The Other Side — Jason Derulo | 2,019 | 97 | 888 | 221 | 232 | 510 |
| `fb0b0989` | The Winner Takes It All | 2,692 | 240 | 1502 | 380 | 383 | 871 |
| `f3680cb8` | Titanium — David Guetta | 2,221 | 121 | 946 | 225 | 216 | 624 |
| `e3d7c376` | What Makes You Beautiful | 2,161 | 83 | 1184 | 201 | 188 | 641 |
| `19187d10` | Wild Ones — Sia | 1,645 | 66 | 559 | 134 | 133 | 453 |

# 5. Checks

| Check | Result |
|---|---|
| Backend, full run in the image **on the CPU** (the app's own backend held 11 GB of the GPU) | 1,287 tests (Phase 0: 1,148, plus the 139 of the core): 1,283 passed, 1 skipped (the real-model test needs a GPU), 3 failed, the same 3 as in Phase 0 (`test_the_worked_example_at_00_46_prints_three_equal_corcheas`, failing on `master` since 02 Phase 0, and the two Transkun tests that fail only without a GPU); 118 s |
| `flake8 src tests` | only the point of before (`events_to_matrix.py:68`, E402) |
| `black --check` on the new files | passed |
| mypy on `src/aitu_backend` | the 20 errors of before; the core is skipped (section 2.3) |
| `scripts/docs/check-links.py` | passed: 408 files, 0 broken links |

The frontend was not changed, so its checks were not run. The running app reloaded once when `sheet/` was written
into `src/` (no request had come in the 30 minutes before, and nothing imports the package at start), and `/health`
answered after it.

# 6. Notes for later phases

## 6.1 Notes without a saved hand (Phase 2)

1,652 notes in 32 of the 33 library songs have no saved hand (`hand = 0` in `notes.pmn`). The core's default
(`hand_sheet_of`) gives such a note the right hand from Do 4 (MIDI 60) up and the left hand below, which is what
`draw_sheet.py` used. The research instead gave the algorithm a hand sheet from its copy of today's pipeline (the
saved hands, and the beam search for the rest: `aitu_research.llm.song.algo_sheet`). Phase 2 task 6 now says the
algorithm starts from the backend's beam search (`aitu_backend.hands`) for those notes, passed as `hand_sheet`. The
research's hand sheet also groups near onsets as today's pipeline does (D-04), so its frames can differ from
`hand_sheet_of`; Phase 2 should compare the two on the library songs.

## 6.2 Other notes

- The full suite inside the image needs the GPU hidden while the app's own backend keeps MuScriptor loaded:
  `docker compose run --rm --no-deps -e CUDA_VISIBLE_DEVICES= -e NVIDIA_VISIBLE_DEVICES=void backend python -m pytest`.
- `draw_sheet.py` writes only where `--out` and `--json` say; `.run/` at the repository root is ignored by git and is
  mounted in the container, so it is a good place for its output.
- The core's README (`src/aitu_backend/sheet/README.md`) is the contract of the package, with the backend names; the
  golden README (`tests/golden/sheet/README.md`) says how each golden file was made in the research.
- The algorithm chose a quarter of 1,000 ms for 7 Years (the song is about 120 BPM, so this is a half note). With
  no tempo on the new sheet (plan section 3.1) this matters only as the reference for the figures, which Phase 2
  decides again (section 3.3).
- The output of the command on 7 Years is in `.run/sheet-draw/7years/` (`1a16a836.svg` opens in a browser).

# 7. Documentation

- `aitu-backend/README.md`, `context/backend/README.md`, `context/03-services-overview.md`,
  `context/00-project-complete-overview.md`, `context/09-coding-conventions.md`: the new package `sheet/`.
- `src/aitu_backend/sheet/README.md`, `tests/golden/sheet/README.md`: where the copy came from, the backend names.
- [`03-plan.md`](03-plan.md): Phase 1 done; Phase 2 task 6 and Phase 3 task 6 changed; section 11.
- [`03-checklist.md`](03-checklist.md), [`README.md`](README.md), `../README.md`, `../../00-index.md`: the state.
