# 06, Phase 1: the matcher, the study and the gallery

Plan: [`06-plan.md`](06-plan.md) sections 4.1 and 4.8. Checklist: [`06-checklist.md`](06-checklist.md), Phase 1.
Branch `feat/06-copy-this-style` (from `master` at `27918ec`). No AI request, no stored file changed.

# 1. Summary

- `aitu_backend/sheet/style/` (new package): `match.py`, with `similar` and `ranked`. Code only.
- `tests/test_sheet_style_match.py`: 10 tests (plan task 1.3), all pass.
- `aitu-backend/scripts/style_study.py`: `--find` (phrases of a part and what they find), `--study` (the numbers),
  `--out` (the gallery). Reads only.
- The gallery: [`gallery/phase-1/index.html`](gallery/phase-1/index.html), 12 references, 74 drawings, served at
  `http://192.168.0.112:8099/06/phase-1/` (a link `06` in the 04 gallery folder, which the 8099 server serves; the link
  is in `.git/info/exclude`).
- The user looked at the gallery (2026-11-03, "okey! revised! continue"): `THRESHOLD` 0.6 and the shifts searched, as
  recommended.

# 2. The matcher (`sheet/style/match.py`)

The module docstring is the reference. In short:

1. **Columns as played**: the live sheet's notes of the hands compared (no decoration notes, no notes covered by an
   ornament), plus the notes of `notes` marked removed, each joined to a column of its hand within `SNAP` (2) frames.
   Symmetric: the reference and every place are read the same way (plan 3.4 asked it of the reference; reading the
   passages the same way keeps the comparison fair when a whole run of the AI left notes out of some passages).
2. **The grid**: the song's negras from `levels.grid.song_grid` (`grid.points(..., "negra")`, with a margin of 200
   frames); a frame's place is interpolated between them. Each column goes to a bin: `2 * grid.division` bins per
   negra (a semicorchea, or a sixth of a ternary negra). The grid takes 0.3 to 0.6 s on a real song, so `similar` takes
   `grid=` and `harmony=` (computed when not given). **Phase 2: the GET route must cache them per part and notes
   revision.**
3. **Per negra** (`_Hand` arrays `(negras, bins)`): onset flags, pitch classes, and the contour (the step in semitones
   from the line's previous column; the line is the top note for staff 1, the lowest for staff 2). Harmony: the tones
   of the chord of `harmony.chords` at each negra (both hands, always).
4. **Similarity of two negras** (`_rhythm`, `_contour`, `_classes`, `_harmony`): rhythm, each onset matched in its bin
   (1) or the next one (0.5); contour, each step matched with the best step in its bin or the next (1 equal, 0.5 same
   way within 2 semitones, 0.25 same way); classes, cosine; harmony, shared tones over all tones. Two empty negras are
   the same (1). The classes and the harmony are computed for each `shift` of `SHIFTS` (-5..+6), the reference raised.
   With two hands, rhythm, contour and classes are the mean of the two hands. The reference's first and last negras
   compare only the bins the reference holds (`_masks`).
5. **Alignment** (`_align`): a subsequence alignment over negras, for all shifts at once (numpy): steps (1,1),
   (1,2) and (2,1), the last two at `STEP_COST` (0.3). Score = total / reference negras, less `SHIFT_COST` (0.03) when
   the shift is not 0. Length of a place in negras within `LENGTHS` (0.8 to 1.25) of the reference.
6. **Places** (`ranked`): all end cells sorted by score, greedy: a place that overlaps the reference or an accepted
   place is skipped. `similar` = `ranked` at `THRESHOLD` (0.6) or more, at most `STYLE_MAX` (12), in song order.
7. **The column map** (`Match.columns`, `(staff, reference frame, passage frame)`): for each aligned pair of negras,
   each reference column paired with a passage column of the same hand, in the same bin or the next one, one to one,
   ties to more shared pitch classes. Phase 2 uses it (the batch prompt, the marks copied).
8. **A reference too small** (fewer than `REF_COLUMNS` 4 columns or `REF_NEGRAS` 2 negras) finds nothing: found in the
   study, where a reference past the last note held one column and matched every place at 1.00. Phase 3: the dialog
   should say so ("Select a longer stretch").

`Match.parts` holds the mean of each part along the alignment and `steps` (negras of either side left alone).

# 3. Tests (`tests/test_sheet_style_match.py`)

Songs written as F1 text: sections of 16 negras (600 ms), a melody in corcheas over a chord every two negras.
Exact repeat found (score > 0.95, the column map moves every column by the section's offset); a note changed found with
a lower score; a repeat a tone higher found with `shift` 2 (and without the shifts searched it scores > 0.2 less);
another passage not found (the verses under the threshold when the reference is the bridge); a cover 10 % faster
found; one hand against both hands (the same melody over other chords scores less with both hands); the notes taken
off the reference count as played (and a removed note of the other hand changes nothing); no overlaps, the limit;
a song of 4 minutes in well under a second (each hand set under 0.5 s with the grid given; measured on the real songs:
3 to 25 ms); a reference with no column finds nothing.

One finding in the tests: in a left hand that plays block chords every two negras everywhere, the rhythm is 1.0 at
every place, so the bridge a fourth higher (shift +5) passed at 0.66 for the left hand. Real covers do not play that
evenly (the study below), but a left hand of steady chords is the weak case of the matcher.

# 4. The study (`scripts/style_study.py --study`)

## 4.1 The 8-second passages (the measure of plan section 3.1)

Each song cut into 8-second passages; for each, one hand: does `like_before` find an earlier passage, and does the
matcher (at 0.6) find an earlier one, or any other one.

| Song | Passages | `like_before` R / L | Matcher, earlier R / L | Matcher, any R / L | Seconds: sheet, grid, chords, matcher |
|---|---|---|---|---|---|
| 7 Years (AI sheet, `1a16a836`) | 28 | 22 / 16 | 24 / 21 | 27 / 26 | 0.07, 0.45, 0.11, 7 ms |
| Titanium (`f3680cb8`) | 29 | 22 / 22 | 24 / 25 | 26 / 29 | 0.80, 0.47, 0.15, 8 ms |
| Shut Up and Dance (`68e277fe`) | 27 | 21 / 20 | 18 / 22 | 23 / 25 | 0.10, 0.42, 0.13, 8 ms |
| My Way, piano cover (`c33860b5`) | 17 | 1 / 4 | 7 / 7 | 13 / 12 | 0.03, 0.40, 0.03, 3 ms |
| Superestrella, piano cover (`a585f9eb`) | 23 | 0 / 0 | 9 / 11 | 15 / 17 | 1.07, 0.61, 0.05, 3 ms |
| 99 Red Balloons (`b2db46eb`) | 24 | 2 / 7 | 8 / 13 | 13 / 18 | 1.13, 0.28, 0.23, 13 ms |

(The passage counts differ by one from plan 3.1 because the cuts here start at the first note.) On the clean songs the
matcher finds about what `like_before` finds; on the covers it finds 7 to 11 earlier passages where `like_before`
found 0 to 4. "Sheet" is `build.current` without its cache; the page has it cached.

## 4.2 The references

12 references chosen with `--find` (phrases that start after a pause of the right hand): 7 Years 3, My Way 5,
Superestrella 2, Titanium 2 (`CASES` in the script). The scores fall in three bands:

- **Exact repeats** (the clean songs): 0.84 to 0.98. A right-hand repeat note for note can score less (7 Years 3:35,
  0.87) because the harmony part reads both hands and the left hand plays other chords there (harmony 0.49).
- **Variants and the repeats of a cover**: 0.62 to 0.79 (My Way's second verse 0.68 to 0.76; Titanium's last chorus
  0.72; 7 Years' phrase with another ending 0.72).
- **Other passages**: mostly 0.40 to 0.58.

Near the line (seen zoomed in, section 5): My Way f2217 (1:28) does not keep f3134 (2:05, 0.59), which looks like the
same phrase played louder in octaves and full chords (its classes 0.55 and contour 0.37 fall because of the added
notes). Superestrella f1742 does not keep f2123 (0.59) and f2763 (0.57); Superestrella f590 keeps f259 (0.65), whose
order is turned around (contour 0.35). These are the questions for the user.

**Shift**: no kept place in the 12 references has a shift, and with no shift searched the kept lists are the same.
Shifted places appear only under the line (+5 or -5, 0.36 to 0.54). **Removed notes**: no change (these songs hold
almost none: My Way 2 of 717, the others 0); Phase 4 measures it on the user's edited references (plan task 4.2).

**Both hands and the left hand**: My Way's long reference (25 s, f609-f1222) finds the second verse with both hands
(0.68) and with the left hand (0.61); the next place is at 0.45 and 0.41. The left hand of a cover is the loosest
(its contour 0.26).

# 5. The gallery

`--out ../context/implementations/06-copy-this-style/gallery/phase-1`: per reference, the reference (blue frame),
the kept passages in song order, then the best 3 places under the line (dashed frame), each drawn alone from its
first column (`llm_frames._slice` of both hands, the clefs in force at its start), with the score and its parts.

Checked zoomed in (2x screenshots of each figure with Playwright): every reference and at least its first passage, and
every place near the line (21 of the 74 drawings), against the data: the frames and the time marks of the drawings
agree with the passages' frames; the passages read as listed above. Wide passages scroll sideways in their box; the
long reference wraps to two lines.

# 6. Learnings for the next phases

- The grid costs 0.3 to 0.6 s and the matcher 3 to 25 ms: Phase 2's `GET /sheet/{uuid}/llm/style` must cache the grid
  and the chords (the dialog asks again when the hand changes).
- The column map works on beats and bins; a passage played in octaves where the reference had single notes still
  maps column to column (the notes of the column differ, Phase 2 copies marks only to the same pitch class or note).
- zsh does not split an unquoted variable: a loop `for a in "x --hands 1"` passes one argument. Run the commands one
  by one.
- `pyproject.toml` has `addopts = "-q"`: a second `-q` hides the count line of pytest. Run the suite with no `-q`, and read the exit code of pytest itself, not of a `tail` after it. Result of this phase: 1377 passed, 1 skipped (CPU).

# 7. Needed later

- Phase 3: the dialog's message for a reference too small (`REF_COLUMNS`, `REF_NEGRAS`).
- Phase 7: the link `context/implementations/04-app-enhancements/gallery/06` is only for serving; it is excluded from
  git, nothing to delete in the repository.
