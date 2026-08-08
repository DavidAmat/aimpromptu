# Task 9.5.1 — Octave displacement and clef switching · progress

Status: **done** on 2026-07-27. Rules in the builder, brackets in the renderer, thresholds in the UI.

## Thresholds (9.5.1.1)

`OctaveThresholds` in `NotationSettings`, stored with the version. Boundaries are **note names** in
Spanish solfège, not row numbers, because that is how a pianist states them ("anything above Do-6").
`None` switches a rule off.

| Field | Default | Rule |
|-------|---------|------|
| `rightOttavaUp` | Do-6 | right hand at or above -> 8va |
| `rightOttavaUpDouble` | Do-7 | -> 15ma (wins over 8va) |
| `leftOttavaDown` | Do-2 | at or below -> 8vb |
| `leftOttavaDownDouble` | Do-1 | -> 15mb (wins over 8vb) |
| `leftTrebleFrom` | Do-4 | left hand at or above -> temporary treble clef |

The downward rules apply to **both** hands, matching the doc's "very low notes (both right and left
hand)": a right hand that dives below the staff gets the same 8vb a left hand would.

## The left-hand rule (9.5.1.2)

An 8va in the left hand is disorienting, so a left-hand passage above its threshold switches to a
small treble clef instead — and the builder then suppresses any bracket for those measures, so the
two rules cannot fight.

The switch is **barline-aligned**: a measure qualifies only if every note in it is above the
threshold, and the clef change covers whole measures. A clef drawn mid-bar is not readable.

With today's C4 hand split the left hand is always below C4, so the default `Do-4` threshold never
fires in practice — the rule is there for when the split becomes smarter, and lowering the threshold
in the UI exercises it immediately.

## Rendering (9.5.1.3)

Directives are grouped **per passage, not per note**: consecutive entries sharing a bracket become one
`OttavaDirective` with a column range, and consecutive switched measures one `ClefDirective`.

The printed pitch moves with the bracket. Under an 8va the note is spelled an octave lower
(`octaveShift: -1`) and the bracket puts it back — which is what a bracket *means*, and why spelling
takes an `octave_shift` argument. The frontend draws a VexFlow `TextBracket` over the notes in range
and announces a changed clef mid-line as well as at a system start.

## Errors found

The bracket was first computed per column, which produced a new directive every time a chord's lowest
note moved. Grouping by **entry** instead gave stable passages.

Adjacent-but-different classes still produce adjacent brackets — Do-1 then Re-1 is 15mb then 8vb.
That is what the thresholds literally say, and it is rare enough in real music to leave alone; a
"hysteresis" pass is the obvious improvement if it ever looks bad.

## Manual trial

[`user_review/epic-09-notation.md`](../user_review/epic-09-notation.md) step 9.8 — lower the 8va
threshold to Do-5 on the reference scale and watch the bracket appear with the notes written an
octave down.

## For the next worker

Thresholds live in the document's `settings`, so they are saved by the same **Save annotations**
button as everything else on the tab. `tests/test_notation_registers.py` covers each rule with a
synthetic extreme-register passage, and `registers.json` in the golden set is what makes the frontend
render check exercise `TextBracket` and mid-line clef changes.
