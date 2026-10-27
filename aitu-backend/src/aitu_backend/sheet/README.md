# aitu_backend.sheet: the product core of the new piano sheet chain

Status: copied into the backend in implementation 03, Phase 1 (2026-10-23), from `src/aitu_notation/` of the
research repository (`poc-aitu-research`, git `a208a92`, version 0.1.0 of research plan 01, phase 15). Audience: the
agents of implementation 03 (`context/implementations/03-apply-poc-research/`). Everything below is the research
README with the names of the backend: `aitu_notation.X` of the research is `aitu_backend.sheet.X` here. The copy
changed no logic; the golden files of section 7 prove it. Phase 2 added the new sheet without compases (section 9),
Phase 3 its engine (section 10), Phase 4 its LLM step (section 11), Phase 5 put it in the app (section 12), Phase 6 made it editable
(section 13), Phase 7 added the note and range tools (section 14), and Phase 8 the sheet toolbox, lyrics and the sheet
on paper (section 15), Phase 8B the sheet through every change of a part's length (section 16), and Phase 9 the marks
of the old sheets (section 17): the bars path below is unchanged, and so are its golden files.

## 1. What it does

```text
notes.pmn (piano matrix notation, saved hands)
   |                                   |
   | proposal.propose (the algorithm)  | llm.write_song (the LLM step, offline, window by window;
   |                                   |   the algorithm is its fallback)
   v                                   v
                F1 bars sheet (text, synthesis/01-f1-format.md)
                               |
                               | engrave.cursor.render_song (on each click, ~140 ms per song)
                               v
             SVG (with note ids) + cursor map + system boxes + timings
```

Run time: Python 3.12, the standard library and numpy. Every asset is a frozen file inside the package (§6).

## 2. Modules

Imports go one way: `sheet` <- `proposal`, `llm`, `engrave`; `llm` -> `proposal` only for the window 1 tempo and the
fallback. `experiments/E15-product-core/imports.py check` (research repository) and `tests/test_sheet_core_chain.py`
enforce it.

| module | input -> output | public functions |
|---|---|---|
| `sheet` | - | `Note`, `Bar`, `Sheet` (`sheet.data`); `f1.read(text) -> Sheet`, `f1.write(sheet, mode="bars"/"frames", anchors=bool) -> str`, `F1Error`; `matrix.sheet_from_matrix(notes, key=) -> Sheet` (frames sheet), `matrix.cells(notes)`; `pmn.notes_from_pmn(body) -> Notes`, `pmn.key_of_sheet_json(sheet_json) -> int`. The new sheet (section 9): `frames.from_notes(notes, key=) -> Sheet`, `frames.check(sheet) -> list[str]`, `frames.cells_of(sheet, notes)`, `frames.matrix_cells(notes)`, `frames.key_at(sheet)`, `frames.printed_signs(sheet)`; `figures.figure_of_ms(ms, quarter_ms, split=0.7)`; `spelling.spell(midi, key)`, `spelling.sign(step, alter, key)`, `spelling.check_rules()` |
| `proposal` | `Notes` + hands -> F1 bars sheet | `propose(notes, *, key, key_changes=None, hand_sheet=None, track=False, quarter_ms=None, meter=None, phase_ms=None, beams="classical") -> Proposal` (`.sheet`, `.quarter_ms`, `.meter`, `.phase_ms`); `hand_sheet_of(notes, key=)`. The new sheet: `frames.propose_frames(notes, *, key=None, key_changes=None, quarter_ms=None) -> FramesProposal` (`.sheet`, `.quarter_ms`, `.info`) |
| `llm` | `Notes` -> F1 bars sheet | `write_song(notes, complete, *, key, sid="song", hand_sheet=None, max_checks=3, guards=True, max_windows=None, on_window=None) -> SongSheet`; `windows.check(answer, target) -> (errors, sheet)`, `windows.answer_text(reply)`, `guards.guard_errors(sheet)`; `prompts.instructions()`, `prompts.window_prompt(...)`, `prompts.feedback(errors)`. The new sheet (section 11): `frames.write_frames(notes, complete, *, sid, key=None, quarter_ms=None, hands=False, max_checks=3, guards=True, max_windows=None, on_window=None) -> FramesSong`; `frames.windows_of(sheet)`, `frames.check_answer(reply, target)`, `frames.assemble(algo, parts, clefs="llm")`, `frames.gap_peaks(sheet)`, `frames.reference_prompt(...)`, `frames.window_prompt(...)`, `frames.instructions()`, `frames.SkipWindow` |
| `engrave` | F1 bars sheet -> SVG; F1 frames sheet -> SVG | `engrave(sheet, Options()) -> Engraving`, `to_svg(engraving, px_per_space=10, note_ids=False, id_prefix="")`, `render(sheet)`; `cursor.render_song(text, note_ids=True) -> Rendered`. The new sheet (section 10): `frames.render_frames(text_or_sheet, frames.Options(), segment=None) -> frames.Rendered`, `frames.plan(sheet, opts) -> Layout`, `frames.draw(layout, systems=None) -> Engraving`, `frames.engrave_frames(sheet, opts)` |

In the research, `sheet.pmn` held copies of `aitu_backend.pmn` (`notes`, `columns`, `dense`) and
`aitu_backend.matrix.keys`. Here the core imports the backend's own modules (identical, imports aside, checked on
2026-10-23), and `sheet/pmn.py` keeps only the `notes.pmn` loader (`notes_from_pmn`, `key_of_sheet_json`, `KEYS`).
These two backend modules are the only imports from outside the core (`tests/test_sheet_core_chain.py`).

## 3. Data

- **Notes** (`aitu_backend.pmn.notes.Notes`): parallel numpy arrays `key` (0 = A0), `on_ms`, `len_ms`, `hand` (0 none,
  1 right, 2 left), as aimpromptu's `notes.pmn`. `notes_from_pmn(body)` drops the removed notes.
- **Sheet** (`sheet.data`): `notes: list[Note]`, `bars: list[Bar]` (empty in a frames sheet), `clefs` (`{1: "G2", 2:
  "F4"}`), `clef_changes` (time or frame, staff, clef), `key` and `key_changes` (frames sheets). A `Note` has `time`
  (quarters from the start, exact `Fraction`; `None` in a frames sheet), `staff` (1 right hand, 2 left hand, 0
  unknown), spelled sounding pitch (`step`, `alter`, `octave`; `.midi`), `figure` and `dots`, `tuplet` ("3/2"),
  `beam` and `tgroup` (group numbers), `grace`, `gslot`, `ornaments`, `ottava`, `frame` (the 40 ms matrix column).
- **F1** text: `synthesis/01-f1-format.md`. Both views, frame anchors. `f1.read` raises `F1Error` (a `ValueError`)
  with the line number.

## 4. The rendered song (JSON of the viewer API, `viewer/server.py`)

`render_song(text)` returns `Rendered`; the viewer sends it as JSON:

| field | content |
|---|---|
| `svg` | one SVG text: glyph paths in `<defs>`, one `<use>` per glyph, lines, beam polygons; user units = staff spaces, `width`/`height` attributes at 10 px per staff space; black on a white `<rect>`. Each notehead (graces too) carries `data-note="<frame>:<midi>"`; a head that stands for merged unisons (same pitch, same time, same hand: the user's rule) lists them all, separated by spaces (`[data-note~="31:82"]`). |
| `columns` | one row per engraved column, in order: `system` (0-based), `bar` (label), `x` (SVG units, margin included), `ms` (audio time: the first frame anchor of its notes x 40; a rest-only column is interpolated) |
| `systems` | one box per system: `top`, `bottom` (ink), `staff_top`, `staff_bottom` (staff lines), `left`, `right` |
| `width`, `height`, `bars` | SVG size in staff spaces, number of bars |
| `timings` | `parse_ms`, `layout_ms`, `svg_ms`, `cursor_ms`, `total_ms` |

A player moves a line between two columns by `audio.currentTime` (x interpolated by ms; to the end of the system
when the next column is on the next one), and lights the heads whose frame is in [this column's ms / 40, the next
column's ms / 40). `viewer/index.html` is the reference (≈ 350 lines).

The engine draws one sheet per call and keeps module state (the style and the glyph caches): call `set_style` only
at start (the product uses the default style, "verovio").

## 5. The LLM step

`write_song(notes, complete, key=...)` runs the window chain of the research (phases 7 and 14) in memory:

1. The algorithm (`proposal.propose`, the given `hand_sheet` or the notes' own hands) gives the tempo and meter of
   window 1 and the fallback bars.
2. Each window (about 8 bars, at most 200 onsets) is one conversation through the product's function:

   ```python
   complete(system: str, messages: list[{"role": "user" | "assistant", "content": str}]) -> str
   ```

   `system` = `prompts.instructions()` (frozen); `messages[0]` = the window prompt (target, look-ahead, decided
   context). The reply is the F1 bars text in one fenced block (`answer_text` takes the blocks out). The checker
   (`windows.check`) and, with `guards=True`, the phase 14 guards (`guards.guard_errors`: beam share, beam
   overlaps) list the problems; a rejected reply gets `prompts.feedback(errors)` as the next user message, and the
   model writes the whole answer again. At most `max_checks` (3) replies per window.
3. An accepted answer: its last bar is decided again by the next window (unless the song ends), the kept bars give
   the next window's tempo and its decided context. A window that fails every check keeps the algorithm's bars of
   its frames; the next window starts without context.
4. `SongSheet`: `.sheet` and `.text` (the joined kept bars, F1 bars with frame anchors), `.windows`
   (`WindowLog`: start, end, first bar, status `ok`/`failed`, replies, the errors of each rejected reply),
   `.summary` (windows, ok, ok at the first check, failed, requests).

The core imports no LLM SDK. A `complete` for the Anthropic API is a few lines in the product (`messages.create`
with `system`, `messages`, the model `claude-sonnet-5-5` by default, the decision of 2026-10-22); a `complete` that
raises stops the chain with that error (the product decides retries and time limits).

## 6. Frozen files

| file | what | made by (research repository) |
|---|---|---|
| `llm/prompt/instructions.md` | the system prompt (version in `llm/prompt/VERSION`, `prompts.PROMPT_VERSION`) | `aitu_research.llm.prompts.product_instructions()`; `experiments/E13-synthesis/export_prompts.py --freeze` |
| `llm/prompt/feedback.md` | the message after a rejected reply | by hand |
| `engrave/leipzig.json` | the Leipzig glyphs (SIL OFL 1.1) | `aitu_research.engrave.glyphs.export_bundle` |
| `engrave/spacing_model.json` | the spacing model (12 numbers measured on printed editions) | `aitu_research.engrave.spacing.fit` |
| `engrave/lyric_fonts.json` | the advance widths of the lyrics fonts (Lora, Geist, Montserrat; four looks each), implementation 03 Phase 8A++ | `aitu-frontend/scripts/measure-lyric-fonts.mjs` (this repository) |
| `proposal/beat_weights.json`, `meter_weights.json` | the quarter and meter estimates | `aitu_research.proposal.beat.fit`, `meter.fit` |
| `proposal/spelling_tables.json` | the spelling tables (`sig_then_local2`) | `aitu_research.baseline.rules.learn_tables` |

## 7. Tests and golden files

The tests are in the backend's `tests/` (pytest): `test_sheet_core_golden.py` checks the golden files of
`tests/golden/sheet/` (`golden/sheet/README.md`), `test_sheet_core_chain.py` the import boundary, the frozen files and
the chain (feedback turn, fallback). Any port (a TypeScript engine) must reproduce the golden files, and a phase that
changes them on purpose says why in its report.
`tests/test_sheet_frames.py` checks the new sheet of section 9 (figures, spelling, grace notes, beam groups, the
armadura, the frames text and the round trip, the starting hands).

## 8. Licenses to check before a release

The app runs on the home machines and is not distributed, so none of these is an obligation today. Before the code,
the prompt or the app is given to anyone outside (a public repository, a package, a hosted service), each row needs its
action. Inventory of implementation 03, Phase 10 (2026-10-27), from the research's `synthesis/05-recommendations.md`
§5.6 checked against what this package holds.

| What, where | License or source | Action before a release |
|---|---|---|
| `engrave/vrv.py`: stem lengths, beam slopes and partial beams ported from Verovio 6.3's C++ | LGPL-3.0 (Verovio) | a legal check of the port, or the rules written again from their description |
| `engrave/leipzig.json`: the Leipzig glyphs (outlines of the music font) | SIL OFL 1.1 (shipped with Verovio) | keep the font's license notice beside the file |
| `llm/prompt/frames/instructions.md`, Example 1 (the A major arpeggio) and `llm/prompt/instructions.md` (example `hand-3`) | Beethoven Op. 2 No. 2, finale, from the `craigsapp/beethoven-piano-sonatas` encoding, which has no license file | replace with a passage of a CC BY or CC0 edition, or confirm the license |
| the same prompts, Example 2 (the waltz) and examples `beam-4`, `range-1` | NIFC Chopin first editions, CC BY 4.0 | attribution |
| `llm/prompt/frames/instructions.md`, Examples 3 and 4 | short transcriptions of two commercial pop songs (The Other Side at 84 s, La Tortura at 196 s) | sent to the API only; before the prompt itself is published, replace them with passages written for the purpose |
| `proposal/beat_weights.json`, `meter_weights.json` (the pulse estimate of the algorithm) | learned on the research's train split, which includes Mozart kern and ASAP (CC BY-NC-SA 4.0) | confirm, or fit again on the CC BY / CC0 part (a few dozen numbers) |
| `engrave/lyric_fonts.json`: advance widths of Lora, Geist and Montserrat | the fonts are SIL OFL 1.1 (`aitu-frontend/public/fonts/*-LICENSE.txt`) | none: widths measured from the fonts, the notices are already shipped with the files |
| the songs sent to Anthropic by the LLM step | the user's own transcriptions | accepted by the user for the product (implementation 03, Phase 4) |

The research's difficulty and fingering models (PSyllabus, PDMX, NIFC) are not in this package. The Bravura font of
the vexflow-v2 sheet left with it (Phase 10); the PDF writes only base fonts and the engine's own outlines.

## 9. The new sheet without compases (implementation 03, Phase 2)

The product sheet is the F1 **frames** view with the user's rules (plan section 3): no compases, no tempo, no
puntillos, no tuplets, no silencios. Measurements and reasons: `context/implementations/03-apply-poc-research/
03-implementation-phase-2.md`.

```text
notes.pmn + starting hands (pipeline.starting_hands: the saved hands, the hand split for the rest)
   |
   | proposal.frames.propose_frames (the algorithm, ~0.2 s per song)
   v
F1 frames sheet:  F1 frames frameMs=40 quarterMs=500
                  key=3# clefs: R=treble L=bass
                  f8       L: E3:4  R: C#5:8 b1
```

- **Drawn column.** Notes are grouped on raw onsets, 40 ms from the first onset of a group, both hands, no chaining
  (D-04), and drawn at the column of the group's first onset: a note sits at its own onset cell or one column
  before. `frames.cells_of` maps a sheet back to the onset cells (the round trip with the matrix: exact on the 33
  songs of My library).
- **Figures** (`figures`): the nearest plain figure to the note's own length, not past the next onset of its hand;
  middle points from the negra up, 70 % of the way for the corchea and shorter; one figure per chord and per run of
  even gaps. The reference figure is `Sheet.quarter_ms` (the pulse estimate of `proposal.beat` unless given).
- **Spelling** (`spelling`): one name per key and armadura, by the user's rules 1 to 5; in Do mayor Do#, Mib, Fa#,
  Sol#, Sib. Every note outside the armadura prints its sign every time (`spelling.sign`), and after a becuadro the
  first return of that note (same name and octave, same hand) to its armadura name prints its sostenido or bemol
  again when it is in the same beam group or the next note (rule 7, `frames.printed_signs`: what the engine prints).
- **The algorithm** (`proposal.frames`) also writes grace notes (one or two fusas or shorter, two figures shorter
  than the next note and sounding just before it; implementation 04, Phase 2), lone short notes written longer
  (`lengthen_lone`: one or two other notes more than two figures shorter than the next note, sounding just before
  it, are written two figures shorter than it, a semicorchea before a blanca a corchea; the end of a run of three or
  more keeps its figures), beam groups (corcheas and shorter no farther apart than a corchea, of one
  figure with at most one odd note at an edge; cut at a jump of more than an octave, at a turn after three steps, and
  into parts of at most 8), the armadura of each passage (fewest signs, a cost per change), clefs and 8va (the
  left-hand rules of the prompt, version 4).
- **F1 additions** (both views; the bars output is unchanged): the header field `quarterMs=` of the frames view, and
  the tag `orn` (an onset played inside the ornament of the note before it: kept for the matrix, not drawn). Phase 7
  adds the user's marks (section 14): `fg3` (finger), `fix` (a figure set by hand), `asgrace` / `nograce` (the grace
  note switch); they are never in an LLM prompt.
- **Data additions**: `Note.covered` (`orn`), `Note.on_ms` and `Note.len_ms` (measured, not written in F1),
  `Sheet.quarter_ms`.
- `frames.check(sheet)` lists what breaks the product rules (no compases, a hand and a plain figure on every note,
  the spelling rule, one figure per chord, beam groups of 2 to 8 consecutive notes, grace notes followed by a note,
  no 8va or 15ma in the bass clef; an 8vb is allowed since Phase 7). The LLM step of Phase 4 uses it as its checker,
  with its own stricter rules (`llm.frames._structure`: no octave line at all in the bass clef).
- Commands: `scripts/write_sheet.py` (the sheet of parts, checked), `scripts/sheet_gallery.py` (the Phase 2
  gallery, drawn by Verovio).

## 10. The engine without compases (implementation 03, Phase 3)

`engrave/frames.py` lays out an F1 frames sheet and draws every element with the bars engine's functions
(`layout`, `vrv`, `svg`): the look is the same, the layout is new. Measurements and reasons:
`context/implementations/03-apply-poc-research/03-implementation-phase-3.md`.

```text
F1 frames text (or its Sheet)
   |  frames.plan: chords per hand and column, signs (frames.printed_signs), stems, room of each column,
   |               gaps from the time between columns, line breaks            (~20 ms per song)
   v
Layout ---- frames.draw (all systems, or some: one segment) ---> Engraving --- svg.to_svg ---> SVG
```

- **Columns.** One x per drawn column for both hands. A grace note is drawn before the next chord of its hand (one
  slot per grace column), in the clef it sounds in: when the clef changes between a grace note and its note, the
  small clef goes between them. `covered` notes are not drawn. One voice per hand: no rests, voices, compás lines,
  meter or bar numbers. `merge_unisons` keeps one head per pitch, column and hand.
- **Spacing.** The gap after a column is `model.gap(t / quarter_ms)` (the measured spacing model; `t` is the time to
  the next column in either hand, `quarter_ms` the reference figure) up to a blanca (`LONG_GAP`); the time beyond
  keeps `Options.silence` (0.3) of the width it would add. Figures are not read. The least gap is what the glyphs
  need (accidentals, grace notes, flags, clef and armadura changes) plus the model's clearance. Lines are
  justified by adding the same amount to every gap; the last line of a song is not stretched.
- **Line breaks.** Greedy, from the line start: among the breaks that fill the line to `Options.fill` (0.8) or more,
  the one after the longest time between two columns; a break never cuts a beam group when a free place exists
  (otherwise the fewest groups, never leaving a part of one note).
- **Armadura and clef changes** inside a line: the cancelling becuadros and the new armadura before the column
  (`Options.key_line` adds a thin double line before it), a small clef before the chord of that hand. Changes that
  fall where that hand plays nothing meet before its next chord: only the last is drawn, and none when it gives back
  the clef in force (two clefs on one spot in 7 Years, the user's report of 2026-10-26); a line starts with the clef
  drawn before its first column (`Column.clef_in`). Two clefs at one column remain only around grace notes read in
  another clef than their note.
- **Rendered** (`render_frames`): `svg`, `columns` (one row per drawn column: `system`, `frame`, `x` in SVG units
  with the margin, `ms` = frame x 40), `systems` (`index` in the whole song, `first` and `last` frame, `top`,
  `bottom`, `staff_top`, `staff_bottom`, `left`, `right`), `width`, `height`, `lines` (systems of the whole song),
  `timings` (`parse_ms`, `plan_ms`, `draw_ms`, `svg_ms`, `cursor_ms`, `total_ms`). Note ids as in section 4
  (`data-note="<frame>:<midi>"`, the drawn column). `segment=(a, b)` draws only the systems that hold a column of
  `[a, b)`, with the line breaks of the whole song.
- Tests: `tests/test_sheet_engrave_frames.py`. Commands: `scripts/draw_frames.py` (draw, check and time parts),
  `scripts/frames_gallery.py` (the Phase 3 gallery).

## 11. The LLM step of the new sheet (implementation 03, Phase 4)

`llm/frames.py` writes the F1 frames sheet with an LLM behind the same function as the bars chain,
`complete(system, messages) -> text`; the product's function is `aitu_backend.sheet_llm.ClaudeComplete` (Sonnet 5.5,
outside the core). Measurements and reasons: `context/implementations/03-apply-poc-research/03-implementation-phase-4.md`.

```text
notes (starting hands)
   |  reference request: the peaks of the gaps between onsets in words -> quarterMs     (1 request, ~5 s)
   |  propose_frames(quarter_ms): the input's figures, the fallback; windows_of: 12-16 s, ending at a pause
   v
window k: target (no hands, the rule's figures) + look-ahead + context -> F1 frames with hands, beams, clefs, 8va,
          ornaments, armadura changes -> check_answer (at most 3 replies) -> Part (or the algorithm's Part)
   v
assemble: decisions on the notes, then the rules: figures (capped by the new hands), grace notes, beam groups cut by
          the figures (one figure, one odd note at an edge), spelling, nearby 8va joined -> frames.check holds
```

- **What the LLM decides**: hands, beam groups (at most 8 notes, a hard check), clefs and 8va (the version 4
  rules; no note four or more ledger lines above its staff, a hard check), ornaments (`orn` for the onsets inside
  one), the armadura of a passage, and the reference figure. **What the app computes**: figures, grace notes,
  spelling.
- **Windows** are known before any request (they depend on the notes and the algorithm), and every answer is kept
  whole. The decided context of window k is the end of answer k-1.
- **Errors**: `SkipWindow` from `complete` fails one window (a refusal); any other exception keeps the algorithm for
  that window and the rest of the song (`WindowLog.status`, `.note`).
- **Frozen files**: `llm/prompt/frames/instructions.md` (version 5, four examples checked by
  `test_the_prompt_examples_pass_the_checker`), `feedback.md`, `VERSION`.
- Tests: `tests/test_sheet_llm_frames.py`. Commands: `scripts/llm_sheet.py` (test requests, runs, replays of a
  run's logged replies or of the research's recorded sheets), `scripts/llm_gallery.py` (the Phase 4 gallery).

## 12. The new sheet in the app (implementation 03, Phase 5)

The core is used by `aitu_backend/part_sheet/` (outside the core) and the routes of `api/sheet.py`. Measurements and
reasons: `context/implementations/03-apply-poc-research/03-implementation-phase-5.md`.

```text
GET /sheet/{part}?width=N ── part_sheet.build.current ──┬─ sheet.f1 (current, or for older notes or hands)
                                                        │    ── build.reapply: the rules of today on the stored
                                                        │       decisions (the file is not written)
                                                        └─ none ── propose_frames on the starting hands (the key
                                                                   and a renamed figure of an old sheet.json kept)
                         (while Sonnet writes: job.LiveRun.text, the parts decided so far + the algorithm's)
                         ── build.draw (engrave.frames.render_frames) ── SVG + columns + systems + segments

POST /sheet/{part}/llm ── part_sheet.job.start ── write_frames(on_start, on_part) with sheet_llm.ClaudeComplete
                         ── event: sheet on /matrix/progress/{job} at the reference figure and at each window
                         ── commit: the hands into notes.pmn (save_edit), the sheet into sheet.f1
```

- `write_frames` has two callbacks for the page: `on_start(algo, windows)` once the reference figure is known, and
  `on_part(log, part)` after each window; nothing else of the chain changed.
- `sheet.f1` is the F1 frames text with one `# aitu-sheet {...}` record line on top (`part_sheet.store.Record`: the
  source, the `handsRevision` it was written for, the windows and their source, the reference figure, the model,
  the prompt version, the cost). `sheet.pending` marks a part whose new notes ask Sonnet to write the sheet (a
  transcription or a video read writes it; the job removes it).
- The hands of a sheet go back to the notes by `build.hands_of_sheet` (each live note at its drawn column and key).
- `scripts/import_llm_sheets.py` stored the Phase 4 sheets of the 10 viewer songs (`viewer-final`) this way.
- Tests: `tests/test_part_sheet.py`.

## 13. Editing the new sheet (implementation 03, Phase 6)

`aitu_backend/part_sheet/edits.py` (outside the core) and the routes `POST /sheet/{part}/hands`, `/undo`, `/redo` of
`api/sheet.py`. Measurements and reasons: `context/implementations/03-apply-poc-research/03-implementation-phase-6.md`.

```text
POST /sheet/{part}/hands {notes: ["<frame>:<midi>", ...], hand}      (the refs are the noteheads' data-note)
   |  under the part's lock: the refs -> note ids (drawn column D-04 + key, as build.hands_of_sheet)
   |  notes.pmn: the hands of every note first when they were never saved as a whole, then the moved ones (save_edit)
   |  sheet.f1 (a stored AI sheet): build.reapply on the new hands -> stored for the new handsRevision, record kept
   |  the step -> sheet.edits.json: each note's hand before and after, one line patch of sheet.f1 both ways
   v
the answer of GET /sheet/{part} (the sheet drawn again)                ~0.15 s in the backend, ~0.25 s to the page
```

- **What an edit changes**: the numeric truth (the hands in `notes.pmn`, plan section 3.7) and the stored sheet.
  A sheet the algorithm wrote is not stored: it is a function of the notes and their hands.
- **Clefs around a moved note** (`build.fit_clefs`, inside `reapply`): a note on another staff than in the stored
  sheet (or new to it) gets the clefs and 8va of the algorithm's rule (`proposal.frames.clefs_and_ottavas`, the
  clef rules version 4) on the stretch of its staff where the rule and the stored sheet differ; the stored clefs and
  8va stay everywhere else. `frames.check` holds on the result.
- **Undo and redo** (`edits.undo`, `edits.redo`): a step touches only what is still as it left it (a guessed hand
  counts as no hand); `sheet.f1` is patched only when it is the text the step left, for the hands it left. The log
  keeps 50 steps; `job.commit` and `store.clear` start it again. It is not in the file lists of a copy.
- **The LLM run again** (`job.start`): on a sheet the AI enhanced, `write_frames(hands=True)`, and the window prompt
  says the shown hands are a suggestion the LLM may change (`llm.frames.window_prompt`); the record's prompt is
  `5+hands`. The cached instructions (version 5) did not change.
- `GET /sheet/{part}` also answers `notes` (`build.drawn_notes`: ref, hand, printed pitch), `editable` and
  `history`.
- Tests: `tests/test_sheet_edits.py`. Browser check: `npm run check:frames-edit` (aitu-frontend).

## 14. The note and range tools (implementation 03, Phase 7)

`aitu_backend/part_sheet/reading.py` (the edits, pure functions on a frames sheet), `edits.edit_reading`,
`edits.remove_notes`, `edits.apply_stretch`, `job.start_stretch`, and the routes `POST /sheet/{part}/reading`,
`/remove`, `GET /sheet/{part}/stretch`, `POST /sheet/{part}/llm/stretch`. Measurements and reasons:
`context/implementations/03-apply-poc-research/03-implementation-phase-7.md`.

```text
POST /sheet/{part}/reading {action, notes | start, end, staff, value}
   |  reading.plan -> change(sheet drawn now) -> the step's label, or Refused (400 with the reason)
   |  build.reapply(changed sheet, notes): the rules run again and keep the decisions
   |  holds(settled) and frames.check: what was asked must still hold, and no new rule may break
   |  sheet.f1 stored (an algorithm sheet: record "edited"), one step of sheet.edits.json
   v
the answer of GET /sheet/{part}                                        ~40-70 ms of rules + ~50 ms of drawing
```

- **The user's marks in the core.** `Note.finger` (written `fg3`), `Note.fixed` (`fix`: the figure was set by the
  user; `assign_figures` keeps it and `find_graces` never makes it a grace note) and `Note.grace_rule` (`asgrace`:
  a grace note of the next note of its hand whatever the rule says; `nograce`: never one). `assemble` carries them
  from the decided notes; `assemble(join=False)` (used by `build.reapply`) keeps the 8va lines as decided, so a line
  the user removed is not joined again.
- **The edits** (`reading`): a figure (on whole chords of one hand), fingers (on one chord from the lowest note: the
  smallest numbers first in the right hand, the largest in the left), a beam joined (or taken away when the picked
  notes are already one group) and cut (or joined to the group before), the grace note switch, an ornament (`trill`,
  `mordent`, `turn` over onsets of one hand that follow one another: the first carries it, the others are `orn`;
  `arpeggio` and `fermata` on chords), and over a stretch `[start, end)`: the armadura, the clef of one hand, the clef
  rules (`clef_rule`: `clefs_and_ottavas` on the stretch only) and an octave line (`8va`, `15ma`, `8vb`, `15mb`). The
  armadura, clef and 8va in force after the stretch come back at its end. `fewest_signs` is the armadura with the
  fewest signs over a stretch.
- **Stored.** An edit on an algorithm sheet stores it with `Record.edited` (`Record.decided`: laid again on new notes
  instead of computed again). `Record.stretches` lists the stretches the AI wrote again.
- **A new AI run** keeps the user's marks (`build.user_marks`, `build.with_marks` on the parts before `assemble`); the
  AI's own kinds (beams, clefs, 8va, armaduras, ornaments) are written again, as the hands are (the user's answer of
  Phase 7).
- **A stretch with the user's words** (`llm.frames.write_stretch`): one window conversation whose target is the
  stretch as it is now (both hands, with its hands, beam groups, clefs, 8va and ornaments), the sheet before it as
  context, the music after it as look-ahead, and `stretch_request` before the answer section: the user's words come
  first ("of the utmost importance": they override the AI's usual choices; only the format and the hard limits
  stay), the purpose behind them (a sheet simpler to read and to play: uniform patterns, the same pitch for the same
  role, a named figure applied everywhere), what was picked, and what the answer may change: hands, beams, clefs,
  8va, ornaments, and with words also which notes stay, their pitches, added notes and figures
  (`check_answer(drop=True, free=(start, end))`). The reply goes through `check_answer` and the beam guard, then
  `splice` puts it in the sheet (the clefs and armadura after it come back; the user's marks stay). The product
  stores it as one step (`edits.apply_stretch`): the hands, the notes left out removed in `notes.pmn`, the notes
  added written there (at the onset of the column they join, as long as their figure), the sheet, and every figure
  the AI wrote that the rule would print otherwise set as by hand (`fix`). `build.reapply` finds a stored note whose
  drawn column moved by a frame or two (the first note of its chord taken off).
- Tests: `tests/test_sheet_reading.py`. Command: `scripts/tools_gallery.py` (the Phase 7 gallery). Browser check:
  `npm run check:frames-tools` (aitu-frontend; `--live` makes one stretch request, about $0.01).

## 15. The sheet toolbox, lyrics and the sheet on paper (implementation 03, Phase 8A)

What the user writes about the whole sheet, stored in the sheet itself (so every copy, history snapshot and undo
step that carries `sheet.f1` carries it too). Measurements and reasons:
`context/implementations/03-apply-poc-research/03-implementation-phase-8.md`.

- **The format** (`sheet.f1`, frames view only; written only when set, so every older sheet and golden file is
  unchanged; never in an LLM prompt, whose sheets are built anew): `spaceMs=` and `lineSpace=` in the header, then
  after the clefs line `title "..."`, `subtitle "..."`, `artist "..."` and one `lyric f<start> f<end> "words"
  [size=..] [lift=..]` per lyrics piece (`\n` breaks a line; size and lift in staff spaces).
- **The data**: `Sheet.titles`, `Sheet.lyrics` (`Lyric`: start, end, text, size, lift), `Sheet.space_ms`,
  `Sheet.line_space`; `carry_extras(source, target)` copies them onto a sheet made from another: `build.reapply`,
  `llm.frames.splice`, and the AI job (its live sheet and its commit) call it.
- **The engine**: the spacing reads `Sheet.space_ms` before `quarter_ms`, so Transpose figures renames figures and
  keeps the spacing's figure (D-18; the rules that read names, grace notes and flags, may still move some columns);
  `Sheet.line_space` is the gap between systems; a lyrics piece is a text primitive (`Prim` kind `"t"`) above the
  upper staff of the line that holds its first column, all pieces of a line on one baseline above the ink under
  them, `lift` raising one further. The SVG writes `<text class="lyric" data-lyric data-start data-end>` (Lora
  italic, a soft charcoal) with one `tspan` per line. `render_pages(sheet, opts, page_height=, first_height=, gap=)`
  draws the song once at the paper's width and deals whole lines onto pages (Print to PDF).
- **The edits** (`part_sheet.reading`, through `edits.edit_reading`, one step each): `titles`, `piece-key` (the
  armadura the sheet starts with), `line-space`, `lyrics` (the whole list, checked: no two pieces share a frame),
  `figures` (Transpose figures: `quarter_ms` x 2^steps, `space_ms` kept, figures set by hand moved; the record's
  `reference` becomes `user`, and a new AI run keeps the named figure: no reference request).
  `edits.preview_reading` answers the result without storing it.
- **Transpose notes** (`edits.transpose_notes`): every note of `notes.pmn` moved, the stored sheet with it
  (`reading.transpose_sheet`: pitches and armaduras moved, so `reapply` keeps every decision; clefs fitted where a
  note reads four ledger lines or more from its staff, `reading.far_notes` and `build.fit_clefs`); notes leaving the
  88 keys taken off; one step (`_Step.keys`: each note's key before and after). A preview stores nothing.
- **A note added** on the keyboard panel (`edits.add_note`): at the onset of the drawn column, one step.
- **Lyrics blocks** (Phase 8A++, the user's request): a `lyric` line may also carry `at=f<frame> dx= dy=` (a block
  put anywhere: drawn from the column of `at` plus `dx`, its last baseline `dy` below the top staff line, whatever
  its frames; a block put on another line than its first frame's stays whole there), `width=` (its words wrap to
  it), `font=` (`lora`, `geist`, `montserrat`), `bold=1`, `italic=0`; all left out at their defaults, so older sheets
  write as before. The engine wraps the words with `engrave/lyric_text.py` and the advance widths of the app's own
  font files (`engrave/lyric_fonts.json`, measured in the browser by `aitu-frontend/scripts/measure-lyric-fonts.mjs`),
  so the page, the line heights and the PDF print the same lines. A piece in the line of words whose frames cross a
  line break is drawn in one part per line (`data-part`), its words shared by the width its frames take on each line
  (`lyric_parts`, `_share_words`). No block passes the end of its line. The SVG `<text>` adds `data-base` (its last
  baseline, from which the page places a dragged block), `data-width`, `font-weight` and `font-style`.
- Routes: `POST /sheet/{part}/reading?preview=true`, `POST /sheet/{part}/transpose` (`preview`),
  `POST /sheet/{part}/add`, `GET /sheet/{part}/pages`; `GET /sheet/{part}` answers `titles`, `lyrics`, `quarterMs`,
  `spaceMs`, `lineSpace`, and each note's `end` frame.
- Tests: `tests/test_sheet_toolbox.py` (the blocks: format, wrapping, drawing, a piece over a line break, the
  route). Browser check: `npm run check:frames-toolbox` (aitu-frontend).

## 16. The sheet through a change of a part's length (implementation 03, Phase 8B)

`aitu_backend/part_sheet/lengths.py` (outside the core) is the new sheet's version of `editing/marks.py`; every change
of a part's length goes through `editing/paste.py` (`paste`, `cut`), which calls it in the same write. Measurements and
reasons: `context/implementations/03-apply-poc-research/03-implementation-phase-8.md` section 10.

```text
read_passage(source, a, b) ── lengths.read: the source's sheet as its page draws it, extract(a, b)
                              (+ the hand each note is drawn in, + the AI's segments inside)
paste(target, at, length)  ── lengths.target (before), then after the notes are written:
                              lengths.store_after: cut_out(the stretch pasted over) -> put_in(passage, at, length)
                              -> build.reapply on the new notes -> sheet.f1 for the new handsRevision
promotion at a speed       ── lengths.scaled(passage, speed, window): frames and reference figures / speed
```

- **The four moves** (pure, on a copy): `shift` (a beam group across the frame is cut in two, a lyrics piece ends
  there), `cut_out` (the armadura and clefs in force after the stretch are kept from its start; the header when no note
  is before it), `extract` (counted from 0, with the armadura and clefs in force at its start as its own), `put_in` (the
  passage's armadura and clefs from `at`, the target's again after it when music follows). Covered onsets whose
  ornament note is on the other side are drawn again; a beam group of one note is no group; the changes are tidied
  (one per frame and staff, none that changes nothing).
- **When it stores**: the target's sheet holds decisions (`Record.decided`), or the passage's does, or the target had
  no music (a blank sheet, a new part: its first sheet is stored, so its Sheet step is written). Two algorithm sheets
  store nothing: they are computed from the notes. The record's windows and stretches move too; an AI passage in an
  algorithm sheet makes it `mixed`.
- **Record in Sheet**: the Current and each take are written with the song's reference figure (the take's at its
  speed) and the song's armadura where the passage starts (`keep_figure`: an algorithm record with `reference: song`
  and `key`; `build.algorithm(key=)`; an AI run keeps a `song` reference as it keeps a `user` one).
- **Undo**: `edits.paste_passage` and a promotion record one step whose undo restores the history version the paste
  kept (`_Step.versions`), as the old page did.
- Tests: `tests/test_sheet_lengths.py`. Browser checks: `check:paste`, `check:compose`, `check:passage -- --played`.

## 17. The marks of the old sheets (implementation 03, Phase 9)

`aitu_backend/part_sheet/legacy.py` (outside the core) lays the marks of an old `sheet.json` (vexflow-v2) on a frames
sheet; `build.with_legacy` settles the result (`reapply`) and keeps the beam marks only when no rule of `frames.check`
breaks. Measurements and reasons: `context/implementations/03-apply-poc-research/03-implementation-phase-9.md`.

```text
sheet.json ── reading_of (Phase 5): the armadura, a renamed reference figure ──> propose_frames
           ── legacy.carry: titles, lyrics, space between lines   (when the sheet has none of that kind)
                            figures set by hand (fix), fingers     (every sheet: the user's marks)
                            beam breaks and joins                  (not on a sheet the AI wrote: the AI's kind)
           ── not carried: clef changes, octave lines (the user's answer of 2026-10-26: the new clef rules
                            everywhere), spacing, even spacing, print smaller, decorations, trills
```

- **Where the marks land.** An old mark names a note by its onset cell (`startFrame`, `fromColumn`: the 40 ms column of
  its onset); `legacy.Cells` gives the drawn column of its chord (D-04). A figure override names a chord of one hand
  (its `row` is 0); a finger names one note. A lyrics piece keeps its frames, its size and lift converted as the page
  converts them (12 px = 1.4 staff spaces), its old `width` as the width its words wrap to; a piece over the frames of
  the one before it is left out. The space between lines keeps its ratio to the default (72 px = 5 staff spaces).
- **Beams.** A break starts a new group where the new sheet has the chord inside a group; a join puts a chord with the
  group of the chord before it (`reading.break_beam`, so a group still holds one figure and at most 8 notes). A mark
  the new sheet's groups already follow is `held`; one that cannot hold is `lost`.
- **When.** `build._compute` draws a part with no stored sheet (or a plain algorithm record) with its old marks, so a
  history version or an old `.aitu` that brings back a `sheet.json` keeps them; nothing is stored by drawing.
  `scripts/migrate_sheets.py` (a dry run unless `--write`, after `make db-backup`) stores them: an algorithm sheet as
  edited by the user (`Record.edited`, `reference: user` for a renamed figure), a stored sheet with the kinds it lacks;
  `Record.legacy` says what was carried, and a part that has it is skipped.
- Tests: `tests/test_sheet_legacy.py`.
