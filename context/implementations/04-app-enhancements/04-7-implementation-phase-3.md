# 04-7 Phase 3: The measure and the gallery

Plan [`04-7-plan.md`](04-7-plan.md) sections 4.2 and 5 (and its section 8, the Phase 3 changes); checklist
[`04-7-checklist.md`](04-7-checklist.md). Branch `feat/04-7-open-points`. 2026-11-03.

State: the measure and the gallery are done; **the user's look at the drawn passages is pending** (checklist 3.3).

# 1. The checks before the edits of `src/`

The measure found three faults of the Phase 2 rule (section 3), fixed in `sheet/proposal/frames.py`. Before the first
edit: no pytest, browser check or script of this project in `ps aux`; the last request of the app 20 minutes earlier
(the user deleted project `17f5379d` at 12:15 UTC); no log `ai-runs/*.json` in `running` (2 logs, both `done`). The
backend reloads only on `src/` (`--reload-dir src`), so the script in `scripts/` never reloaded it.

# 2. The script: `aitu-backend/scripts/clef_study.py`

Made like `scripts/grace_gallery.py`. It runs in the running container and only reads (`build._compute`, nothing
stored):

```sh
docker exec -i -w /work/aimpromptu/aitu-backend aimpromptu-backend-1 python scripts/clef_study.py --study
docker exec -i -w /work/aimpromptu/aitu-backend aimpromptu-backend-1 python scripts/clef_study.py \
    --out ../context/implementations/04-app-enhancements/gallery/04-7
docker exec -i -w /work/aimpromptu/aitu-backend aimpromptu-backend-1 python scripts/clef_study.py --find <part> [--around F]
```

- `rule("old")` puts back the old `STATES` (three a hand), the old limit (`old_fits`: only the left hand's, clef.L3),
  `short_clefs` off (in `proposal`, `build` and `edits`, which import it by name) and the old `OTTAVA_LOWEST`
  (`{"G2": 72}`). `rule("new")` is today's code, with the counts of the last `short_clefs` of the drawing.
- `--study`: per part of the `private` layer, drawn old and new: clef changes, 8va and 8vb notes of each hand, the
  short stretches (1 to 4 columns of the other clef) old and new, the stretches taken away and kept, the grace columns
  off the line of their main column, the seconds of one drawing (after a first drawing that warms the caches; without
  it the first drawing of a rule sheet took up to 1.7 s and the comparison was false), and `others`: every field of
  every note and of the sheet but the clefs and `ottava` must be equal. Then the old left-hand treble stretches by
  length (plan section 3.3) and the three parts with clefs set by hand, read by id in any layer.
- `--out`: the gallery, old above new, a band on each column whose clef or line changed, the list of those columns
  from the data; a case fails on a new `frames.check` problem or any other change.
- `--find`: the changed passages of one part (to choose the cases).

# 3. Three faults of the Phase 2 rule, found by the measure and fixed

| Fault | Seen in | Fix (`proposal/frames.py`) | Test (`tests/test_sheet_clefs.py`) |
|---|---|---|---|
| The cheapest path wrote ordinary right-hand chords under 8vb: G3 B3 D4 G4 costs 3 ledger lines, the 8vb state 2.5 | Grace Kelly, 124 notes under 8vb from 0:00 (178 in the library) | `clefs_and_ottavas`: the line of the hand's own clef (left 8va, right 8vb) only for a column that does not read without it | `test_a_right_hand_chord_readable_with_ledger_lines_takes_no_8vb` |
| The new right-hand limit (no note D3 or lower in the treble clef without a line) sent a chord too wide for 8vb to the bass clef, with E6 eight ledger lines up | Die Young f1369 (A2 E3 E4 A4 E5 E6), f4720 | the right hand's limit holds only where its 8vb line reads the column; else the cost decides, as before 04-7. The left hand's limit (clef.L3 of 03) is unchanged | `test_a_right_hand_chord_too_wide_for_8vb_keeps_the_treble_clef` |
| A grace column and its main column under different lines. The engraver draws grace notes with the main column and under its line, but writes each head by its own line: the grace chord B4 D#5 (8va) before F#4 (no line) was written B3 D#4 outside the line, an octave off | Superestrella (AI) f1586, seen zoomed in case 2; 21 grace columns in the `private` layer already with the old rule (33 with the vault), 10 more with Phase 2 | `_grace_lines`, at the end of `short_clefs` (every drawn sheet): the main column takes the grace notes' line when it reads under it (fewer than 4 ledger lines each side), else the grace notes take the main column's | `test_grace_notes_and_their_main_column_share_one_octave_line` |

Each new test fails without its fix and passes with it. One more effect of the third fix: a grace column with two
lines inside it is stored by F1 as two grace slots (one line a token); with one line it is one chord again, so its
`gslot` changes (Halleluyah f3927 and f4140, 99 Red Balloons first minute f1019 and f2907: 10 notes). Before, the slot
without a line was drawn under the main column's 8va, an octave off. `others` counts it apart ("gslot of a grace chord
split by its lines") and accepts nothing else.

The whole backend suite on the CPU after the three fixes: **1365 passed, 1 skipped, 0 failed** (1362 + 3 new).
Note: the project's pytest config already adds `-q`; `pytest -q` then prints no summary line, so run it without `-q`.

# 4. The measure (`--study`, the `private` layer, 43 parts, the fixes in)

## 4.1 The old counts equal plan section 3.3

| | Plan 3.3 | The study, old rule |
|---|---|---|
| Left-hand treble stretches, sheets of the rule | 89: 43 of 1-2 columns, 18 of 3-4, 7 of 5-8, 21 of 9+ | 89: 43, 18, 7, 21 |
| ... of 1 to 4 columns with a note B4 or higher | 56 | 56 (counted by ledger lines, as 3.3 did: a Bb4 is also 4 ledger lines up; by pitch it is 55) |
| Left-hand treble stretches, AI sheets (prompt 5) | 85, 77 of 1-4, 74 with B4 or higher | 85, 77, 74 |
| Level sheets (`mixed`) | none | none |

43 parts, not 44: the song 20 de enero of My library (`39d92dbe`) was deleted in Phase 1; it was a level sheet with
no treble stretch.

## 4.2 Old and new, all sheets

| | Old | New |
|---|---|---|
| Clef changes, right hand | 153 | 116 |
| Clef changes, left hand | 344 | 96 |
| Short stretches (1 to 4 columns), right / left | 50 / 139 | 29 / 15 |
| Notes under 8va, right / left | 1754 / 37 | 1779 / 462 |
| Notes under 8vb, right / left | (not counted; the old rule had no 8vb state) | 61 / 0 |
| Short stretches taken away / kept | | 164 / 44 |
| Notes under a new line (by `short_clefs`) | | 476 |
| Grace columns off their main column's line | 21 | 0 (27 matched) |
| New problems of `frames.check` | | 0 |
| Anything else changed | | nothing (the 10 `gslot` of section 3 only) |

The 25 more right-hand 8va notes are the main columns that took their grace notes' 8va (`_grace_lines`). The 44
kept stretches: a column reads neither way, mostly a note so far that even the octave line leaves it 4 ledger lines
out (right hand G1 G2 or Bb1 Bb2 in Titanium, Bonfire Heart, Die Young; left hand G6, B6, C6 in Bonfire Heart), and a
few wide chords (Die Young f4222 E2 B4). They keep the other clef, as the old rule drew them.

## 4.3 Per sheet

Columns: clef changes right / left, old -> new; 8va notes right / left, old -> new; 8vb right / left, new; short
stretches right / left, old -> new; stretches taken away / kept; seconds of one drawing, old / new; anything else.

| Song | Part | Sheet | Clef changes R / L, old -> new | 8va R / L, old -> new | 8vb R / L, new | Short stretches R / L, old -> new | Taken away / kept | s old / new | Anything else |
|---|---|---|---|---|---|---|---|---|---|
| Frank Sinatra - My Way ｜ Piano Cov | f07958ba | level | 2 / 0 -> 2 / 0 | 0 / 0 -> 0 / 0 | 0 / 0 | 0 / 0 -> 0 / 0 | 0 / 0 | 0.02 / 0.02 | - |
| Nino Bravo - Un beso y una flor ｜  | 3201f6b9 | level | 0 / 0 -> 0 / 0 | 0 / 0 -> 0 / 0 | 0 / 0 | 0 / 0 -> 0 / 0 | 0 / 0 | 0.01 / 0.01 | - |
| Frank Sinatra - My Way ｜ Piano Cov | c33860b5 | rule | 2 / 0 -> 2 / 0 | 0 / 0 -> 0 / 0 | 0 / 0 | 0 / 0 -> 0 / 0 | 0 / 0 | 0.03 / 0.03 | - |
| Juanes - La camisa negra ｜ Instrum | c4d9ab95 | level | 0 / 0 -> 0 / 0 | 0 / 0 -> 0 / 0 | 0 / 0 | 0 / 0 -> 0 / 0 | 0 / 0 | 0.02 / 0.02 | - |
| Carolina - M-Clan Piano Tutorial ( | 4a606fde | level | 0 / 0 -> 0 / 0 | 0 / 0 -> 0 / 0 | 0 / 0 | 0 / 0 -> 0 / 0 | 0 / 0 | 0.01 / 0.02 | - |
| Amaral - Marta, Sebas, Guille y lo | ebd61ffa | level | 0 / 0 -> 0 / 0 | 0 / 0 -> 0 / 0 | 0 / 0 | 0 / 0 -> 0 / 0 | 0 / 0 | 0.02 / 0.02 | - |
| La Playa - La Oreja de Van Gogh ｜  | b41efc2f | AI p6 | 0 / 0 -> 0 / 0 | 0 / 0 -> 0 / 0 | 0 / 0 | 0 / 0 -> 0 / 0 | 0 / 0 | 0.02 / 0.02 | - |
| Jarabe de Palo - La Flaca (Piano T | 2f133ebc | level | 0 / 0 -> 0 / 0 | 0 / 0 -> 0 / 0 | 0 / 0 | 0 / 0 -> 0 / 0 | 0 / 0 | 0.02 / 0.02 | - |
| 99 Red Balloons — Nena · first min | 99381667 | level | 0 / 0 -> 0 / 0 | 0 / 0 -> 0 / 0 | 0 / 0 | 0 / 0 -> 0 / 0 | 0 / 0 | 0.02 / 0.02 | - |
| 99 Red Balloons — Nena · first min | cde7b40a | AI p5 | 0 / 0 -> 0 / 0 | 84 / 0 -> 86 / 0 | 0 / 0 | 0 / 0 -> 0 / 0 | 0 / 0 | 0.08 / 0.07 | - |
| 7 Years | daf087e9 | rule | 2 / 0 -> 0 / 0 | 0 / 0 -> 0 / 0 | 2 / 0 | 1 / 0 -> 0 / 0 | 1 / 0 | 0.18 / 0.14 | - |
| AITANA - SUPERESTRELLA | PIANO TUT | f4c4de9a | AI p5 | 0 / 154 -> 0 / 10 | 432 / 0 -> 445 / 322 | 0 / 0 | 0 / 72 -> 0 / 0 | 72 / 0 | 0.05 / 0.07 | - |
| Halleluyah - Pinchivi | 43faf78e | AI p5 | 0 / 16 -> 0 / 4 | 27 / 0 -> 33 / 6 | 0 / 0 | 0 / 6 -> 0 / 0 | 6 / 0 | 0.04 / 0.04 | - |
| Party in the USA | 51b12412 | rule | 6 / 7 -> 0 / 5 | 0 / 0 -> 0 / 0 | 11 / 0 | 3 / 1 -> 0 / 0 | 6 / 0 | 0.21 / 0.25 | - |
| Stronger — Kelly Clarkson | dff5097c | rule | 0 / 2 -> 0 / 0 | 0 / 0 -> 0 / 0 | 0 / 0 | 0 / 1 -> 0 / 0 | 1 / 0 | 0.21 / 0.22 | - |
| Club Can't Handle Me — David Guett | d64acd29 | rule | 0 / 6 -> 0 / 2 | 0 / 0 -> 0 / 5 | 0 / 0 | 0 / 2 -> 0 / 0 | 2 / 0 | 0.30 / 0.33 | - |
| Raise Your Glass | 12f777af | rule | 2 / 6 -> 2 / 2 | 0 / 0 -> 0 / 1 | 1 / 0 | 0 / 2 -> 0 / 0 | 3 / 0 | 0.22 / 0.25 | - |
| I Knew You Were Trouble | 6eb7af4e | rule | 12 / 4 -> 12 / 0 | 0 / 0 -> 0 / 3 | 7 / 0 | 3 / 2 -> 2 / 0 | 5 / 2 | 0.26 / 0.17 | - |
| Birds of a Feather | b80e6f5a | AI p5 | 0 / 0 -> 0 / 0 | 0 / 0 -> 0 / 0 | 0 / 0 | 0 / 0 -> 0 / 0 | 0 / 0 | 0.07 / 0.05 | - |
| The Winner Takes It All | fb0b0989 | rule | 6 / 6 -> 6 / 4 | 90 / 0 -> 90 / 2 | 0 / 0 | 1 / 1 -> 1 / 0 | 1 / 1 | 0.32 / 0.34 | - |
| Fate of Ophelia — Taylor Swift | 3633a0c3 | rule | 6 / 0 -> 6 / 0 | 0 / 0 -> 0 / 0 | 0 / 0 | 3 / 0 -> 3 / 0 | 0 / 3 | 0.24 / 0.25 | - |
| La Tortura — Shakira | 0815f602 | rule | 0 / 0 -> 0 / 0 | 0 / 0 -> 0 / 0 | 0 / 0 | 0 / 0 -> 0 / 0 | 0 / 0 | 0.18 / 0.20 | - |
| Poker Face — Lady Gaga | 2ed0f379 | AI p5 | 0 / 0 -> 0 / 0 | 0 / 0 -> 0 / 0 | 0 / 0 | 0 / 0 -> 0 / 0 | 0 / 0 | 0.07 / 0.10 | - |
| Titanium — David Guetta | f3680cb8 | rule | 14 / 0 -> 14 / 0 | 0 / 0 -> 0 / 0 | 6 / 0 | 7 / 0 -> 7 / 0 | 5 / 7 | 0.22 / 0.26 | - |
| Wild Ones — Sia | 19187d10 | rule | 2 / 10 -> 2 / 8 | 0 / 0 -> 0 / 2 | 1 / 0 | 1 / 2 -> 1 / 1 | 2 / 2 | 0.13 / 0.16 | - |
| Hips Don't Lie — Shakira | 4cb9cb38 | AI p5 | 0 / 0 -> 0 / 0 | 0 / 0 -> 0 / 0 | 0 / 0 | 0 / 0 -> 0 / 0 | 0 / 0 | 0.06 / 0.06 | - |
| Die Young — Kesha | e578f3c0 | rule | 11 / 36 -> 8 / 6 | 408 / 1 -> 410 / 24 | 6 / 0 | 5 / 18 -> 3 / 3 | 17 / 6 | 0.22 / 0.22 | - |
| Airplanes — B.o.B | b064f815 | rule | 8 / 2 -> 8 / 2 | 15 / 0 -> 15 / 0 | 0 / 0 | 1 / 1 -> 1 / 1 | 0 / 2 | 0.17 / 0.19 | - |
| Can't Stop the Feeling — Justin Ti | f285e4b7 | rule | 6 / 2 -> 6 / 0 | 0 / 0 -> 0 / 1 | 1 / 0 | 0 / 1 -> 0 / 0 | 2 / 0 | 0.30 / 0.42 | - |
| What Makes You Beautiful | e3d7c376 | rule | 0 / 0 -> 2 / 0 | 0 / 0 -> 0 / 0 | 0 / 0 | 0 / 0 -> 0 / 0 | 0 / 0 | 0.26 / 0.19 | - |
| Superestrella — Aitana | a585f9eb | rule | 4 / 38 -> 2 / 22 | 315 / 2 -> 317 / 28 | 0 / 0 | 2 / 10 -> 1 / 2 | 9 / 3 | 0.10 / 0.18 | - |
| Shut Up and Dance — Walk the Moon | 68e277fe | AI p5 | 0 / 0 -> 0 / 0 | 4 / 0 -> 4 / 0 | 0 / 0 | 0 / 0 -> 0 / 0 | 0 / 0 | 0.07 / 0.08 | - |
| The Other Side — Jason Derulo | 96768e80 | rule | 0 / 0 -> 0 / 0 | 0 / 0 -> 0 / 0 | 0 / 0 | 0 / 0 -> 0 / 0 | 0 / 0 | 0.16 / 0.19 | - |
| 2002 — Anne-Marie | f73116dd | rule | 10 / 4 -> 4 / 0 | 24 / 0 -> 24 / 5 | 1 / 0 | 4 / 2 -> 1 / 0 | 5 / 1 | 0.21 / 0.16 | - |
| 7 Years — Lukas Graham | 1a16a836 | AI p5 | 0 / 0 -> 0 / 0 | 0 / 0 -> 0 / 0 | 0 / 0 | 0 / 0 -> 0 / 0 | 0 / 0 | 0.06 / 0.06 | - |
| 99 Red Balloons — Nena | b2db46eb | rule | 20 / 11 -> 16 / 3 | 197 / 26 -> 197 / 35 | 6 / 0 | 4 / 4 -> 2 / 0 | 10 / 2 | 0.18 / 0.26 | - |
| Bonfire Heart — James Blunt | bef90052 | rule | 28 / 30 -> 18 / 28 | 85 / 8 -> 85 / 13 | 13 / 0 | 10 / 9 -> 5 / 8 | 8 / 13 | 0.16 / 0.23 | - |
| Stay the Night — James Blunt | aa07c1c0 | rule | 2 / 4 -> 2 / 0 | 0 / 0 -> 0 / 3 | 2 / 0 | 0 / 2 -> 0 / 0 | 3 / 0 | 0.12 / 0.22 | - |
| Moonlight Shadow — Mike Oldfield | c0edc9b0 | AI p5 | 0 / 0 -> 0 / 0 | 64 / 0 -> 64 / 0 | 0 / 0 | 0 / 0 -> 0 / 0 | 0 / 0 | 0.13 / 0.14 | - |
| Grace Kelly — Mika | 56543911 | rule | 2 / 2 -> 0 / 0 | 9 / 0 -> 9 / 4 | 2 / 0 | 1 / 1 -> 0 / 0 | 2 / 0 | 0.13 / 0.14 | - |
| Drivers License — Olivia Rodrigo | 3c8d4cfa | AI p5 | 0 / 0 -> 0 / 0 | 0 / 0 -> 0 / 0 | 0 / 0 | 0 / 0 -> 0 / 0 | 0 / 0 | 0.05 / 0.06 | - |
| 1973 — James Blunt | a1c30047 | rule | 8 / 4 -> 4 / 0 | 0 / 0 -> 0 / 8 | 2 / 0 | 4 / 2 -> 2 / 0 | 4 / 2 | 0.40 / 0.45 | - |
| The One That Got Away — Katy Perry | 92255337 | AI p5 | 0 / 0 -> 0 / 0 | 0 / 0 -> 0 / 0 | 0 / 0 | 0 / 0 -> 0 / 0 | 0 / 0 | 0.05 / 0.09 | - |

The sheets that change most: Superestrella (AI, `f4c4de9a`) left hand 154 -> 10 clef changes, 320 notes under 8va in
the bass clef; Die Young 36 -> 6; Superestrella (rule, `a585f9eb`) 38 -> 22; Halleluyah (AI) 16 -> 4. The level
sheets, My Way and the AI sheets with no left-hand treble stretch do not change.

## 4.4 The parts with clefs set by hand (by id, any layer)

| Part | Where | Phase 2 read in the undo log | Now |
|---|---|---|---|
| `c33860b5` My Way | My library | the right hand's own clef (treble) set twice | no column changed; its 18-column bass stretch (f1262-f1544) stays |
| `946c21f2` 20 de enero, level copy | Personal Vault | the left hand's own clef (bass) set | no column changed; treble stretches of 5 (f1886-f1906) and 6 (f1998-f2023) columns stay |
| `7b9a41e4` 20 de enero, level copy | Personal Vault | the treble clef for the left hand at f1998 | the user's stretch f1998-f2023 (6 columns) stays; 4 columns changed elsewhere: a short treble stretch f1805-f1825 (C3 E3 A3 E3) goes back to the bass clef |

## 4.5 Speed

One drawing (after a warm one), old -> new: rule sheets 0.03 to 0.40 s (mean 0.20) -> 0.03 to 0.45 s (mean 0.23); AI
sheets mean 0.07 -> 0.07; level sheets 0.02 -> 0.02. The measures are noisy by a few hundredths (an earlier run gave
0.19 -> 0.20). The time of one edit (0.28 s in 04 Phase 2) was not measured here; `short_clefs` and
`_grace_lines` are linear in the columns and add a few hundredths at most to a drawing.

# 5. The gallery: `gallery/04-7/index.html`

Served by the running `http.server` on 8099 (its folder is `gallery/`): **http://192.168.0.112:8099/04-7/**. Width
110, the app's engraver. 11 cases, 0 problems (no new `frames.check` problem, nothing but clefs and lines changed).
Each drawing was screenshot (Playwright, 2x) and looked at zoomed against `--find`'s data:

| # | Case | Kind | Checked |
|---|---|---|---|
| 1 | Superestrella (AI) f30-f330, high chords of the left hand | AI sheet | F#4 A#4 C#5 written F#3 A#3 C#4 in the bass clef under one 8va line f42-f86; F#4 B4 D#5 under a second; the right hand unchanged |
| 2 | Superestrella (AI) f1520-f1780, one line over several columns | AI sheet, joined line, grace notes | G#3 written G#2 (bottom line) inside the line; the grace chord B4 D#5 and F#4 now under the line together (before the fix the grace chord stood after the hook, section 3) |
| 3 | Halleluyah (AI) f1650-f1860, single high notes | AI sheet | C5 under 8va written C4; A4 and G4 with three ledger lines |
| 4 | Superestrella (rule) f100-f300 | rule sheet | D#5, B4 and the chord F#3 B3 D#4 B4 under 8va (written F#2 B2 D#3 B3) |
| 5 | Die Young f4900-f5000, a wide chord under the line | rule sheet, wide chord | B2 E3 B4 G#5 written B1 E2 B3 G#4 (two ledger lines below, three above) |
| 6 | Die Young f40-f160, the right hand | right hand, 8vb | G#3 with ledger lines; B2, C#3, C#3 G#3 under one 8vb line, written B3, C#4, C#4 G#4 |
| 7 | What Makes You Beautiful f3900-f4000 | right-hand passage of 6 columns | the bass clef for the six columns (C#3 E4 ... C#3 E4), the treble clef after |
| 8 | Bonfire Heart f4860-f4960 | kept | no band: the three C6 stay in their treble stretch (4 ledger lines even under 8va) |
| 9 | 20 de enero `7b9a41e4` f1790-f2045 | the user's clef | C3 E3 A3 E3 back in the bass staff; the user's 6-column treble stretch at 1:20 stays |
| 10 | 20 de enero `946c21f2` f1870-f2045 | passages kept | no band: the treble stretches of 5 and 6 columns stay |
| 11 | Grace Kelly f3030-f3110 | both hands | right G2 G3 written G3 G4 under 8vb in the treble clef; left F#4 B4 D5 F#5 under 8va in the bass clef |

# 6. Findings for later

- `946c21f2` (case 10): the 5-column treble stretch f1886-f1906 of the stored level sheet holds B3 D4 B3 D4 and a
  **G2**, drawn in the treble clef with eight ledger lines. Old and new draw it the same; the rule counts columns and
  keeps any passage of 5. Not changed here; a question for the user only if the gallery shows it worth it.
- The 44 kept stretches are notes the transcription gave to the far hand (a right-hand G1 G2 octave): the other clef
  is the best the rule can do; 15ma or 15mb are not part of the rule.

# 7. For the next step

- The user looks at the gallery (checklist Decisions, 3.3): ok, or a change of `CLEF_MIN` or of the step (then back
  to Phase 2, written in plan section 8). The study and the gallery run again in about a minute after any change.
- When the user says ok: checklist 3.3 done, Phase 3 done; Phase 4 (Hard's figure check, Stop) can start.
