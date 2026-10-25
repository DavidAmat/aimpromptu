# 03: Phase 3 report: the engine without compases

Plan: [`03-plan.md`](03-plan.md) section 7, Phase 3. Checklist: [`03-checklist.md`](03-checklist.md). Branch
`feat/migrate-new-logic` (`master` had not moved since Phase 2, so nothing was merged in). Written 2026-10-23 on the
Ubuntu machine. No change visible in the app: no route or page uses the new engine yet. **Done 2026-10-24**: the
user checked the gallery ([`gallery/phase-3/index.html`](gallery/phase-3/index.html)) and said "perfect"; the two
decisions of section 10 were closed as section 10.3 says.

# 1. Summary

| Task | Result |
|---|---|
| 3.1 Study | The bars engine (`engrave/layout.py`) works per compás in its chords, voices, rests, accidentals, columns, spacing and line breaks; every function that draws one element is reused unchanged. The new layout is a new module, `engrave/frames.py` (about 600 lines); `layout.py`, `vrv.py`, `svg.py` and the 139 golden files did not change (section 2) |
| 3.2 Spacing | One x per drawn column for both hands; the gap is the measured spacing model of the time to the next column in either hand, with the reference figure as its negra; the time beyond a blanca between two columns keeps 30 % of its width; figures are not read (section 3) |
| 3.3 Line breaks | Never inside a beam group when a free place exists; the break after the longest pause once the line is 80 % full. A changed 10 s window moved no later line in 27 of 30 windows (section 4) |
| 3.4 Signs and changes | `frames.printed_signs` (rules 1 and 7); no rests, compás lines, meter or bar numbers; armadura changes (cancelling becuadros and the new armadura, optionally a thin double line), clef changes, grace notes in the clef they sound in (section 5) |
| 3.5 Cursor map and segments | `render_frames` gives the SVG with `data-note` ids, one row per column (system, frame, x, ms) and one box per system; `segment=(a, b)` draws only the systems that hold `[a, b)`, with the line breaks of the whole song (section 6) |
| 3.6 Speed | In the backend container: 58 ms per song warm (median of 33 songs; the bars engine drew in 190 ms in Phase 1), 31 ms per 10 s segment. uv's Python takes the container from 32 % to about 8 % slower than the host; the image is left for Phase 5 (section 7) |
| 3.7 Gallery | 8 passages, each drawn by vexflow-v2 (the app), the bars engine and the new engine, and one whole song; every case checked zoomed in and against the data (section 8) |

All 33 songs of My library draw without error, every note drawn once (no note missing, none extra), all 5,846 beam
groups of the algorithm drawn.

# 2. The study (task 3.1)

`layout.engrave` builds, per compás and staff, chords with voices and rests (`build_chords`, `rest_split`,
`_assign_voices`), prints accidentals with the memory of the compás (`_accidentals`, rule `spell.10`), builds columns
and gaps per compás with the time to the barline (`build_bars`), fills lines with whole compases (`break_lines`), and
draws barlines, the meter, bar numbers and measure rests. These are the parts that need compases.

Everything else works on one chord, one beam group or one system and is reused as it is: noteheads, stems and flags
(`_draw_chord`, `_draw_unbeamed_stem`), stem directions and beam groups (`_stems`, Verovio's `vrv._place`), the room
of a chord (`_extents`, Verovio's accidental placement), beams and cross-staff beams (`_draw_beam_group`,
`_draw_cross_beam`), grace notes (`_draw_graces`), ornaments, fingers, 8va lines (`_ottavas`), ledger lines
(`_vrv_ledgers`), the armadura (`_draw_key`), the brace, the staff gap from the ink, and `svg.to_svg`.

The new module therefore builds its own chords and columns from frames and calls those functions. In the new sheet
one hand has one chord per column with one figure (`frames.check`), so there are no voices, and with no rests the
stems follow Verovio's rules for a single voice.

# 3. Spacing (task 3.2)

## 3.1 The rule

Plan section 3.2 asks for one vertical line per moment for both hands, a width that grows with the notes of either
hand, and empty time drawn shorter than its time.

- **Columns.** Every drawn column (`Note.frame`, the column of the chord, D-04) with a main note in either hand gets
  one x. A grace note takes no x of its own: it is drawn before the next chord of its hand.
- **The gap** after a column is `model.gap(t / quarter_ms)`: `t` is the time to the next column in either hand,
  `quarter_ms` the reference figure, and `model` the spacing model measured on printed editions (research,
  `spacing_model.json`: semicorchea 1, corchea 1.29, negra 1.70, blanca 2.23, then x1.30 per doubling). Many short
  notes in one hand give many gaps, so the stretch widens for both hands, and the other hand has blank space.
- **Empty time.** When no hand starts a note for longer than a blanca, the time beyond the blanca keeps 30 % of the
  width it would add (`Options.silence`, `LONG_GAP`). The first version kept the full width while a note still
  sounded by its figure; it left the gap after a redonda at full width, which is the user's own example of a gap to
  shorten (brief, question 1), and it read figures as durations, which task 3.4 forbids. The rule now looks at time
  only. It touches few gaps: 105 of 25,869 gaps in the library are longer than a blanca, in 22 songs (median gap
  240 ms, 99 % under 760 ms). The longest, 12.4 s in Can't Stop the Feeling, is drawn about 6.5 staff spaces wide
  (a corchea gap is about 2.6).
- **The least gap** is what the glyphs need (accidentals, grace notes, flags, clef and armadura changes) plus the
  model's clearance (0.3 staff spaces), as in the bars engine. Lines are justified by adding the same amount to
  every gap (the research's `space.6`); the last line of a song is not stretched.

## 3.2 What is left to the user's eye

The constants are the research's measured model plus two new ones (the blanca limit and 30 %); the gallery shows
them on real passages. The density is close to the bars engine: the 10 viewer songs take 11 to 21 lines at 130 staff
spaces (median 17.5).

# 4. Line breaks (task 3.3)

The piece-by-piece view of Phase 5 redraws a segment when the LLM returns it; if its width changes, a greedy line
fill moves every later line. The rule (`_break_lines`):

1. From the start of a line, the longest run of columns that fits the width.
2. Among the breaks that leave the line at least 80 % full (`Options.fill`), the one after the longest time between
   two columns (a pause), so that two versions of the sheet tend to choose the same break again after a change.
3. A break never cuts a beam group when a free place exists in the line. Where both hands have beam groups one after
   the other along the whole line (Poker Face), the break cuts the fewest groups and never leaves a part of one note.

**Measured** (scratch script, 10 viewer songs, windows of 10 s at 25, 50 and 75 % of the song): the hands of the
window are changed to a split at middle C, which changes the beam groups, clefs and signs there, and the algorithm
writes the sheet again. Then the line breaks after the window are compared.

| Rule | Windows with a moved line after it | Lines after the windows | Moved | Most lines moved before the breaks match again |
|---|---|---|---|---|
| The longest pause once 80 % full | 3 of 30 | 238 | 8 | 6 (7 Years) |
| Fill each line to the end | 6 of 30 | 224 | 19 | 10 (7 Years) |

A real LLM segment changes less than this test (the onsets, and so the columns, never change). Phase 5 checks it in
the browser.

**Beam groups cut by a break**: 10 of the 5,846 groups of the library (Poker Face 4, What Makes You Beautiful 2,
four songs 1), each into two parts of two notes or more, each part beamed on its line.

# 5. Signs, clefs and armaduras (task 3.4)

- **Signs**: `frames.printed_signs` of the drawn sheet (rule 1, every note outside the armadura every time; rule 7,
  the courtesy sign after a becuadro), placed by Verovio's accidental rules. A test checks every head of a sheet
  against `printed_signs`.
- **Nothing of the compás**: no rests (one voice per hand), no compás lines, no meter, no bar numbers. The vertical
  line at the start of each system joins the two staves; the end of a line has no line.
- **An armadura change inside a line** prints becuadros for the signs of the old armadura that the new one cancels,
  then the new armadura, before the column, on both staves at the same x (Grace Kelly: Sol mayor to Do mayor). The
  first drawing left 0.5 staff spaces before it, and the lone becuadro read as an accidental of the next chord; it
  now has 1.5 before and 1.0 after. `Options.key_line` adds a thin double line before the change (not a compás
  line); the gallery shows both, for the user to choose (section 10). An armadura in force at a line's start is in
  its header.
- **A clef change inside a line** prints a small clef before the chord of that hand, 0.3 staff spaces after the note
  before it and 0.6 before the chord (the first version left 0.15 and the clef touched the notehead).
- **Grace notes keep the clef they sound in.** Grace Kelly f3065: a right-hand grace chord G4-G5 sounds before the
  right hand changes to the bass clef (f3068). The first version drew it in the bass clef with four ledger lines; now
  it is in the treble clef, then the small bass clef, then the main note.
- 8va lines, ornaments, cross-staff beams, fingers and `merge_unisons` come from the bars engine; a test draws a
  trill, 8va and a beam group across the hands. The automatic 8va of the bars engine is off: the sheet's own 8va
  (the clef rules) is the truth.

# 6. Cursor map, note ids and one segment (task 3.5)

`render_frames(text_or_sheet, Options(), segment=None)` returns:

- `svg`, with `data-note="<frame>:<midi>"` on every notehead, grace notes included (the drawn column, as in the
  research);
- `columns`: one row per drawn column, `system`, `frame`, `x` (SVG units, margin included), `ms` = frame x 40. A
  player moves the cursor between columns by the audio time and lights the heads of the column, as in the research
  viewer; a grace note lights with the column before its note (it sounds just before);
- `systems`: `index` in the whole song, `first` and `last` frame, `top`, `bottom`, `staff_top`, `staff_bottom`,
  `left`, `right`;
- `lines` (systems of the whole song) and `timings`.

**One segment.** `segment=(a, b)` plans the whole song (columns, room, line breaks) and draws only the systems that
hold a column of `[a, b)`, so that the page can replace those systems in place. A test checks that a system drawn
alone is the same as in the whole song. A 10 s segment touches 1.9 systems on average.

`scripts/draw_frames.py` draws parts, checks each drawing (every note drawn once, beam groups cut) and times the whole
song cold and warm and every 10 s segment.

# 7. Speed (task 3.6)

## 7.1 In the container

The backend container on 2026-10-23, the machine busy (load average 7 to 13, another project's containers running),
5 warm draws per song. Times in milliseconds, medians over the songs.

| | Whole song cold (first song of the process) | Warm | of which: read F1 / plan / draw / SVG | 10 s segment (max) |
|---|---|---|---|---|
| 33 songs of My library | 76 | 58 (max 122) | 8 / 22 / 17 / 6 | 31 (131) |
| The 10 viewer songs | 66 | 49 (max 94) | 7 / 19 / 14 / 5 | 28 (72) |

Phase 1 measured the bars engine at 190 ms per song warm in the same container (median of 33). The new engine is
faster because it has no voices and rests to build, and because the bars engine's spacing worked per compás with
fractions. A segment costs the plan of the whole song (about 20 ms) and the drawing of its systems; Phase 5 can keep
the plan of a song between two segments if that matters.

## 7.2 The container's Python

Phase 1 found the container about 30 % slower than the host and suspected Debian's Python build. Measured again on the
10 viewer songs (warm median per song, the same F1 texts, runs alternated): two throwaway images built from the
backend's base (`python:3.12-slim-bookworm`) with numpy 2.4.5 and pydantic 2.13.4 as `uv.lock` pins them, one with
Debian's Python 3.12.14 and one with uv's Python 3.12.13 (python-build-standalone), against the host (uv's Python).

| Where | ms per song |
|---|---|
| Host | 35.8 |
| Container image with uv's Python | 38.5 (36.7 to 41.8 over 4 runs) |
| Container image with Debian's Python | 47.3 (46.7 to 47.7 over 3 runs) |

uv's Python removes most of the difference (32 % slower to about 8 %). The backend image was not changed: a rebuild
restarts the running app, and 10 ms per song do not matter before a page uses the engine. **Needed later, at Phase 5
task 3**: build the backend image on uv's Python (`uv python install` in the Dockerfile, `UV_PYTHON_DOWNLOADS` allowed
for that step) before the engine is served. The two test images were removed.

# 8. The gallery (task 3.7)

[`gallery/phase-3/index.html`](gallery/phase-3/index.html) (1.6 MB with its pictures). Served on the machine with
`python3 -m http.server 8715 --bind 0.0.0.0` from the `gallery/` folder: `http://ubuntu:8715/phase-3/`.

Each case is a passage of My library with one sentence that says what to look at, drawn three ways:

1. **Today's sheet**: a screenshot of the app's Sheet step of that library version, only opened, never clicked
   (`aitu-frontend/scripts/vexflow-passages.mjs`). vexflow-v2 draws the whole part as one SVG with one
   `.grid-music-layer` per line and `data-onset-frame` on each onset group; the script brings each line of the
   passage into view (the page scrolls inside a container), clips the passage over its two staves, and scales it to
   10 px per staff space (vexflow-v2 draws about 7.5) so that the spacing compares directly.
2. **The bars engine**: the bars algorithm on the same starting hands, the compases that hold the passage.
3. **The new engine**: the lines of the whole song that hold the passage (the segment drawing), the passage on a
   light band. A first version drew the passage alone at its natural width, which looked tighter than the justified
   compases of the bars engine and than the song; the segment drawing shows the lines as they will be.

The 8 cases: a busy right hand over a quiet left hand (Hips Don't Lie), both hands together (7 Years), a pause after
a redonda (Drivers License), beam groups in both hands and the signs of rules 1 and 7 (Poker Face), grace notes
(Moonlight Shadow), clef changes and 8va (Superestrella cover), a grace note before a clef change (Grace Kelly), an
armadura change with and without the double line (Grace Kelly); and 7 Years whole (15 lines, about 35 ms).

**Checks before showing it.** Every case was looked at zoomed in (2x and 3x) and the doubtful places were checked
against the data. This found the three engine errors of section 5 (the grace chord in the wrong clef, a clef touching
its note, the becuadro of an armadura change that read as an accidental), all fixed, and two places that looked wrong
at a small size but were right in the data (the two becuadros of an armadura change are at the same x; the
sostenido of the header is on both staves). The vexflow-v2 capture took four versions before it showed the right
lines at the right size.

What the gallery does not judge: the notes themselves. Hands, figures, beam groups and clefs are the Phase 2
algorithm's, so the new sheet can differ from today's sheet in the notes, and some passages are crowded by the
figures (section 11).

# 9. Checks

| Check | Result |
|---|---|
| Backend, full run in the image **on the CPU** (the app's backend holds the GPU) | 1,313 tests (Phase 2 and rule 7: 1,304, plus the 9 new ones): 1,309 passed, 1 skipped, the same 3 failures as in Phases 0 to 2 (`test_the_worked_example_at_00_46_prints_three_equal_corcheas`, and the two Transkun tests that fail only without a GPU); 116 s |
| The golden files of the core | 139 of 139, unchanged: the bars engine did not change |
| `tests/test_sheet_engrave_frames.py` (new) | 9 tests: every note drawn once and one x per column for both hands, the signs, a grace note in its own clef, an armadura change on both staves and the double line, empty time, line breaks and justified widths, one segment equal to its system in the whole song, a cross-staff beam with ornaments, a bars sheet refused |
| `flake8`, `black` on the new and changed files | clean |
| `scripts/docs/check-links.py` | passed: 410 files, 0 broken links |

The frontend app was not changed; `vexflow-passages.mjs` is a new script that only opens pages. The running backend
reloaded when `engrave/frames.py` was written into `src/` (nothing imports it at start) and `/health` answered 200.

# 10. Decisions for the user

## 10.1 The look of the spacing (the plan's Phase 3 decision)

The gallery shows the spacing of section 3 next to today's sheet and the bars engine. The user checks it by eye; the
two numbers to change if a passage looks too loose or too tight are the blanca limit and the 30 % of empty time,
and the density of the whole sheet is the spacing model's base gap.

## 10.2 A thin double line before an armadura change

Without compases, an armadura change in the middle of a line has no barline before it, and a lone becuadro can read
as an accidental of the next chord. Classical scores put a thin double line there. Options: (a) no line, only the
room around the signs (the default now); (b) the thin double line, which is not a compás line. Gallery case 8 shows
both. The change is one option (`Options.key_line`).

## 10.3 How they were closed

The user answered the gallery with "perfect" (2026-10-24) and did not choose between the options of 10.2. The
spacing of section 3 is approved as it is, and the armadura change keeps the default (a), no line;
`Options.key_line` stays available if the user asks for the double line later.

# 11. Notes for later phases

- **Phase 4 (the LLM).** The gallery shows two effects of the Phase 2 rules that the LLM should improve: short
  staccato notes take a fusa or semifusa (their own length) and, with the rule of one figure per beam group, stay
  unbeamed with three or four flags (7 Years, second line); and octaves played unevenly become acciaccaturas in many
  places (7 Years, the left hand). Both are readings for the LLM (and the user) to judge in the Phase 4 gallery.
- **Phase 5.** The page draws a song with `render_frames` and replaces the systems of a segment with
  `render_frames(segment=...)` (section 6); the columns give the x of each column for a reveal column by column.
  The backend image takes uv's Python first (section 7.2). Line breaks depend on the width in staff spaces
  (`Options.width`, 130 here), so the page must choose its width before it draws.
- **The engine's state.** Like the bars engine, the frames engine keeps module state (the style and the glyph
  caches); `Options` carries everything else.
- The scratch scripts (the stability test, the Python images, the passage helper) are not kept; their numbers are in
  sections 4 and 7. `scripts/draw_frames.py --layer private --json` reproduces section 7.1.

# 12. Documentation

- `aitu-backend/src/aitu_backend/sheet/README.md`: the modules table and section 10 (the engine without compases).
- `aitu-backend/src/aitu_backend/sheet/engrave/__init__.py`: the module list and exports.
- `context/backend/README.md`: the engine and the two commands.
- [`03-plan.md`](03-plan.md): section 3.2 note, Phase 3 tasks with what was done, Phase 5 task 3, section 8,
  section 11. [`03-checklist.md`](03-checklist.md), [`README.md`](README.md), `../README.md`, `../../00-index.md`:
  the state.
