# aitu_backend.sheet: the product core of the new piano sheet chain

Status: copied into the backend in implementation 03, Phase 1 (2026-10-23), from `src/aitu_notation/` of the
research repository (`poc-aitu-research`, git `a208a92`, version 0.1.0 of research plan 01, phase 15). Audience: the
agents of implementation 03 (`context/implementations/03-apply-poc-research/`). Everything below is the research
README with the names of the backend: `aitu_notation.X` of the research is `aitu_backend.sheet.X` here. The copy
changed no logic; the golden files of section 7 prove it.

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
| `sheet` | - | `Note`, `Bar`, `Sheet` (`sheet.data`); `f1.read(text) -> Sheet`, `f1.write(sheet, mode="bars"/"frames", anchors=bool) -> str`, `F1Error`; `matrix.sheet_from_matrix(notes, key=) -> Sheet` (frames sheet), `matrix.cells(notes)`; `pmn.notes_from_pmn(body) -> Notes`, `pmn.key_of_sheet_json(sheet_json) -> int` |
| `proposal` | `Notes` + hands -> F1 bars sheet | `propose(notes, *, key, key_changes=None, hand_sheet=None, track=False, quarter_ms=None, meter=None, phase_ms=None, beams="classical") -> Proposal` (`.sheet`, `.quarter_ms`, `.meter`, `.phase_ms`); `hand_sheet_of(notes, key=)` |
| `llm` | `Notes` -> F1 bars sheet | `write_song(notes, complete, *, key, sid="song", hand_sheet=None, max_checks=3, guards=True, max_windows=None, on_window=None) -> SongSheet`; `windows.check(answer, target) -> (errors, sheet)`, `windows.answer_text(reply)`, `guards.guard_errors(sheet)`; `prompts.instructions()`, `prompts.window_prompt(...)`, `prompts.feedback(errors)` |
| `engrave` | F1 bars sheet -> SVG | `engrave(sheet, Options()) -> Engraving`, `to_svg(engraving, px_per_space=10, note_ids=False, id_prefix="")`, `render(sheet)`; `cursor.render_song(text, note_ids=True) -> Rendered` |

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
| `proposal/beat_weights.json`, `meter_weights.json` | the quarter and meter estimates | `aitu_research.proposal.beat.fit`, `meter.fit` |
| `proposal/spelling_tables.json` | the spelling tables (`sig_then_local2`) | `aitu_research.baseline.rules.learn_tables` |

## 7. Tests and golden files

The tests are in the backend's `tests/` (pytest): `test_sheet_core_golden.py` checks the golden files of
`tests/golden/sheet/` (`golden/sheet/README.md`), `test_sheet_core_chain.py` the import boundary, the frozen files and
the chain (feedback turn, fallback). Any port (a TypeScript engine) must reproduce the golden files, and a phase that
changes them on purpose says why in its report.

## 8. Licenses to check before a release

`engrave/vrv.py` ports drawing rules from Verovio (LGPL-3.0); the Leipzig glyphs are SIL OFL 1.1
(`synthesis/04-engine.md` §4.6).
