# 2026-07-27 — Epic 9, Stories 9.1 to 9.6

Scope agreed with the supervisor at the start of the session: **the six core notation stories, not
Story 9.7** (tuplets, trills and chord grouping), which the plan places at the end of the project.
Epic 10 was explicitly not started.

## What exists now that did not before

The matrix becomes sheet music. `Playground → Music Notation` renders a braced grand staff with real
barlines, correct figures and dots, beams, the no-tie policy, key signatures
with proper enharmonic spelling, ottava brackets, dashed beat guides, and a cut-measure edit.

The dividing line the whole epic is built on: **the backend decides, the frontend draws.** The score
document carries duration tokens, dot counts, accidental *glyphs*, stem directions, beam group ids
and the always-false compatibility tie flag — already decided. `renderScore.ts` contains no music
rules. That is
`project-features.md`'s "Backend ease the task for Frontend", taken literally, and it is what makes
the future GPU-host argument still available.

## New modules

**Backend** — `schemas/notation.py`, `notation/spelling.py`, `notation/durations.py`,
`notation/score_builder.py`, `notation/artifacts.py`; `api/notation.py` went from five `501`
placeholders to five working endpoints.

**Frontend** — `music/scoreDocument.ts`, `components/notation/` (`renderScore.ts`, `ScoreSheet.tsx`,
`PromoteDialog.tsx`, `KeySignaturePanel.tsx`, `OctavePanel.tsx`), and a rewritten `NotationPage.tsx`.

## The three decisions worth remembering

**Spelling is a search, not a lookup.** The matrix is sharps-only, so printing it literally puts an
accidental on every Bb in Sib mayor. Every letter that can name a pitch is scored — free if the key
covers it, 2 for one glyph, 6 for a double — and the cheapest wins. "Naturals over doubles" and
"E mayor keeps its A#" both fall out of that one table rather than needing special cases.

**The arpeggio beam break needed narrowing.** Read literally, "break at a note whose neighbours are
both higher" also fires on the Mi of Do-Sol-Mi-Sol, chopping an Alberti bass into pairs. The doc's own
words are *the lowest note of the pattern*, so a break now also requires the note to be the low point
of a small neighbourhood. This is a reading of the requirement, not a change to it.

**Transposition accepts into the raw matrix.** A row shift means the same thing at every granularity,
so shifting the source keeps every step, every granularity and every other tab consistent — where
shifting the displayed matrix would have needed a lossy re-expansion.

## Verification

| Check | Result |
|-------|--------|
| `pytest` | 563 passed, 1 skipped (72 new tests across five notation modules) |
| `flake8`, `mypy` | clean |
| `tsc -b`, `eslint` | clean |
| `npm run check:render` | six golden documents drawn headlessly, wrap assertion passes |

`npm run check:render` is new. It draws every golden score document under jsdom and asserts real
glyphs came out, because VexFlow's failure modes are asymmetric: a wrong modifier order throws, a
wrong tick count just draws nothing, and both look identical in the browser — a blank tab. It caught
the ottava bracket and mid-line clef change wiring before a browser saw either.

`aitu-frontend` gained `jsdom`, `tsx` and `@types/jsdom` as devDependencies for it, so run
`npm install` once.

## Waiting on you

A **musical trial**, not a smoke test: [`user_review/epic-09-notation.md`](user_review/epic-09-notation.md).
It follows the epic's own ladder — single scale, then chords, then two hands, then dotted durations,
then a key signature with accidentals — and finishes with the two steps most likely to reveal a real
problem: the Alberti beam break (9.4) and the Do-Re-Mi-Fa cut measure (9.9).

The question worth answering as you go is not "does it render" but **"is this how you would have
engraved it"**. Everything here is a rule that can be tuned.

### Supervisor follow-up: rest placement and chord duration

The first musical trial exposed visible rests between successive notes. The score is now onset-led:
after an entrance, the preceding note/chord fills the time to the next onset; all chord members
share that duration; and the final event expands toward the barline. Visible rests are limited to a
leading entrance or an unwritable trailing residue. An unwritable interior residue is retained only
as an invisible timing spacer. A cross-barline gap becomes a leading rest in the next measure,
never a tie.

## Known gaps, recorded rather than hidden

- **Polyphony stems.** The score intentionally stays one readable voice per hand. Simultaneous
  onsets share one onset-to-next-onset chord duration, so partial releases do not create polyphony.
- **Only major keys.** Fifteen of them. Minor keys share their relative major's signature, so nothing
  is musically wrong, but the dropdown says `G` where a musician might expect Mi menor.
- **Adjacent ottava kinds.** Do-1 followed by Re-1 produces 15mb then 8vb — literally what the
  thresholds say. A hysteresis pass is the obvious fix if it ever looks bad.
- **Story 9.7** untouched by design; annotation kinds `tuplet` / `trill` / `acciaccatura` /
  `appoggiatura` already pass through the format unread.

## For the next worker

Epic 10 (Piano Library) is the next epic in the plan. It will want the same `GET /notation/{artifact}`
the Notation tab uses — the performance view is that document rendered read-only with the overlay
toggles, which the renderer already supports through `showAnnotations` and `showBeatGuides`.
