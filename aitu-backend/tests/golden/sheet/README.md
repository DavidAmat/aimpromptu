# Golden files of aitu_backend.sheet

Made by `experiments/E15-product-core/golden.py` (research repository, phase 15) from the research outputs, and
copied here in implementation 03, Phase 1; checked by `../../test_sheet_core_golden.py`. A port of the core must
reproduce them.

| folder | input | expected output | cases |
|---|---|---|---|
| `engrave/passages/` | `<id>.f1`: the 41 rulebook passages of phase 3 (printed Chopin, Beethoven, Mozart, Schubert), F1 bars with frame anchors at the score tempo | `<id>.svg.gz` (gzip of the SVG of `render_song`, note ids on) and `<id>.cursor.json` (`bars`, `width`, `height`, `systems`, `columns`) | 41 |
| `engrave/songs/` | `<sid>.f1`: the 10 whole songs written by Sonnet 5.5 (phase 14 viewer) | as above | 10 |
| `engrave/clefs/` | `<passage>-<version>.f1`: the 13 left-hand clef passages of phase 14, every version (`written`, `user`, `current`, `new`, `new2`, `new3`, `new4`) | as above | 69 |
| `proposal/` | `<sid>.hands.f1`: a library song's hand sheet (F1 frames with hands: today's beam search with the saved hands) | `<sid>.proposal.f1`: first line `# {"key", "quarter_ms", "meter", "phase_ms"}`, then the algorithm's F1 bars (`propose(..., track=True)`) | 3 |
| `checker/cases.json` | `target` (F1 frames) and `reply` (a model's reply) | `errors` of `check(answer_text(reply), target)` and `guard_errors` of an accepted answer | 9 |
| `chain/43faf78e/` | `frames.f1` (Halleluyah, every onset cell), `hands.f1` (the algorithm's hands), `answers/window-<k>.md` (the 13 accepted Sonnet 5.5 answers of phase 14) | `song.f1` and `windows.json` of `write_song(..., guards=False)`, a fake model replying the recorded answer of the window it is asked for | 1 song |

Notes for a port:

- The frames text stands for a matrix with one 40 ms note per onset cell (`notes_of_frames` in the test).
- The SVG is compared as text; a port that draws the same geometry with other number formatting should compare the
  numbers instead (positions are written with 3 decimals).
- The chain case must give the same windows and the same joined text; it does not depend on any model.
