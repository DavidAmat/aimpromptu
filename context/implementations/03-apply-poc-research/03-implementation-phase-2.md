# 03: Phase 2 report: the new sheet without compases (format and algorithm)

Plan: [`03-plan.md`](03-plan.md) section 7, Phase 2. Checklist: [`03-checklist.md`](03-checklist.md). Branch
`feat/migrate-new-logic` (`master` had not moved since Phase 1, so nothing was merged in). Written 2026-10-23 on the
Ubuntu machine. No change visible in the app: no route, page or stored file uses the new sheet yet. **Done
2026-10-23**: the user checked the gallery after two review iterations (sections 13 and 14) and said "perfect,
proceed"; the two decisions of section 10 were closed as section 10.3 says.

# 1. Summary

| Task | Result |
|---|---|
| 2.1 Study | The F1 frames view already carries hands, figures and tags per column; nothing in it depends on bars. The algorithm needs the pulse only for the reference figure. Two measurements changed the plan's rules: note lengths under the pedal (section 2.2) and chords played unevenly (section 2.3) |
| 2.2 The format | The product sheet is F1 frames (`sheet/frames.py`): `quarterMs=` in the header, the tag `orn`, no bars, puntillos or tuplets; `frames.check` lists what breaks the rules; the round trip maps every note back to its onset cell (exact on 33 of 33 songs) |
| 2.3 Figures | `sheet/figures.py`: middle points from the negra up, **70 %** for the corchea and shorter (measured against 50, 60 and 80 %); the length is **capped at the next onset of the hand** (a decision for the user, section 10.1); one figure per chord (the most common, ties to the longer) and per run of even gaps |
| 2.4 Grace notes | The two-step rule on semicorcheas and shorter that sound just before their note (the user's review, section 13 replaced the first limits). 1,712 grace columns in the library (4.4 % of the columns) |
| 2.5 Alteraciones | `sheet/spelling.py`: rules 1 to 5 give one name for each of the 12 keys in each of the 15 armaduras (`check_rules`, a test). Do mayor: Do#, Mib, Fa#, Sol#, Sib (the research rulebook). The armadura of each passage: fewest signs, 12 signs per change |
| 2.6 The algorithm | `proposal/frames.py`, `propose_frames`. 33 of 33 songs of My library: a valid sheet (`frames.check` empty), the round trip exact; about 0.2 s per song (median) after 0.76 s for the starting hands (`pipeline.starting_hands`). Beam groups of one figure (section 13). `scripts/write_sheet.py` |
| 2.7 Gallery | 15 cases (14 checked by the user, case 14 on rule 7 added after) in [`gallery/phase-2/index.html`](gallery/phase-2/index.html), drawn by Verovio (`scripts/sheet_gallery.py`). Checked by the user after two iterations |

# 2. The study

## 2.1 What the F1 frames view carries

`f1.write(sheet, mode="frames")` writes one line per column with an onset (`f<frame>`), runs of empty columns
(`[]x<n>`), the key and clefs on line 2, `f<n> key=` lines for armadura changes, and on each note line both hands with
the same note tokens as the bars view: figure (`:8`), beam group (`b3`), tuplet, grace, ornaments, 8va, `clef=`. The
reader takes all of them in frames mode. Nothing of the view depends on bars or times, so the plan's "F1 frames view
with hands, figures and tags" needed only three additions (section 3).

The algorithm of the research (`proposal.pipeline`) used the pulse for four things: positions (quantization into
bars), figures (the time to the next onset, cut at the barline), beams (the metric levels), and tuplets. In the new
sheet positions are columns, figures come from the note's length and a reference figure, and beams follow the simple
rules of plan section 3.11. The pulse estimate (`beat.estimate`) is therefore used only for the reference figure.
Meter, phase and beat tracking are not used.

## 2.2 Note lengths against the gaps (the pedal)

The plan warned that MuScriptor's lengths may be noisy under the pedal. On the 10 viewer songs, with the saved hands,
the ratio of a note's length to the gap until the next onset of its hand (`study_lengths`, scratch script):

| Song | Median ratio, right hand | Notes sounding > 1.5 × the gap (R / L) |
|---|---|---|
| Halleluyah | 1.00 | 12 % / 3 % |
| Superestrella (cover) | 0.95 | 11 % / 3 % |
| 7 Years | 1.60 | 59 % / 29 % |
| Poker Face | 0.98 | 26 % / 40 % |
| Drivers License | 1.47 | 48 % / 37 % |
| Hips Don't Lie | 1.47 | 48 % / 23 % |
| Birds of a Feather | 1.07 | 42 % / 34 % |
| Moonlight Shadow | 1.95 | 60 % / 57 % |
| The One That Got Away | 1.56 | 51 % / 44 % |
| Shut Up and Dance | 0.90 | 21 % / 3 % (left hand median 0.46: staccato) |

Many notes sound much longer than the time until the hand plays again. With the raw length as the figure, these
notes become blancas and redondas followed at once by the next note. Section 4 measures what this does.

## 2.3 Chords played unevenly

The notes of a chord often fall one column apart (40 ms columns, rounded onsets). Kept in their own columns, the first
note becomes a separate onset 40 ms before the rest, and the grace note rule then makes it a false grace note. Today's
pipeline groups near onsets on raw times (D-04: 40 ms from the group's first onset, no chaining, both hands) and draws
the group at the column of its first onset. The new sheet does the same (`frames.from_notes`). A note is then drawn at
its own cell or one column before it, never further, and `frames.cells_of` maps it back (the earliest free cell of its
key at its column or the next one).

Columns of one hand that remain within 80 ms of each other are rare: 143 of 10,823 columns on the 10 viewer songs,
almost all in Superestrella (85) and Moonlight Shadow (48). 56 of them share a note name (an octave or a repeated note
played unevenly).

## 2.4 The reference figure

Three references on the 10 viewer songs (negra in ms):

| Song | Today's saved `anchorMs` as a negra | The pulse estimate (`beat.estimate`) | Sonnet's `# quarter=` (recorded research runs, median) |
|---|---|---|---|
| Halleluyah | 350 | 707 | 720 |
| Superestrella (cover) | 434 | 882 | 440 |
| 7 Years | 176 | 1000 | 1000 |
| Poker Face | 252 | 504 | 492 |
| Drivers License | 417 | 833 | 834 |
| Hips Don't Lie | 150 | 400 | 600 |
| Birds of a Feather | 286 | 571 | 768 |
| Moonlight Shadow | 231 | 467 | 464 |
| The One That Got Away | 214 | 428 | 860 |
| Shut Up and Dance | 234 | 937 | 470 |

The pulse estimate equals Sonnet's choice in 5 songs, is twice or half in 3, and 1.5 times in 2. Today's default (the
highest pile of gaps is a negra) is about half of Sonnet's negra in most songs: today's sheets name the corchea a
negra. The algorithm uses the pulse estimate, as the plan says; Phase 4 gives the choice to the LLM.

# 3. The format (task 2.2)

The product sheet is a `Sheet` with no bars whose notes carry `frame` (the drawn column), `staff` (1 right, 2 left),
the spelled pitch, a plain `figure`, and the tags. Changes to the core (the bars view and its golden files unchanged):

- `F1 frames frameMs=40 quarterMs=500`: the header carries the reference figure (`Sheet.quarter_ms`). It is not a
  tempo: no BPM or beat is derived from it (rule 3).
- `orn`: an onset played inside the ornament of the note before it (a trill's alternations). The note stays in the
  text, so the round trip keeps every onset, and the engine will not draw it (`Note.covered`). Today's app keeps the
  alternations of a trill in the recording too (`annotations-notes.md`).
- `Note.on_ms` and `Note.len_ms`: the measured onset (of the group) and length (to the note's own release). They are
  not written in F1; the algorithm needs them for the figures.
- **Tuplets are not in the product sheet.** Without a beat the algorithm cannot find a tresillo safely (D-32 needed
  three even notes dividing a beat), and the user's rule makes figures approximate. `frames.check` refuses `t3`;
  Phase 4 may reopen it if the LLM's triplets read better.
- `frames.check(sheet)`: no bars; every note with a column, a hand and a plain figure; no puntillo, no tuplet; the
  name given by the spelling rule in the armadura of its column; one figure per chord and hand; beam groups of 2 to 8
  consecutive columns of one hand with corcheas or shorter, no grace note inside; a grace note followed by a note;
  `orn` after an ornament; no 8va in the bass clef. Phase 4 uses it as the checker.

**Round trip.** `cells_of(read(write(sheet)), notes) == matrix_cells(notes)` (the onset cells of each hand's matrix,
the rule of `pmn.dense`: one cell per key, hand and column) holds for 33 of 33 songs, with no lost note.

# 4. Figures (task 2.3)

## 4.1 The rule

`figure_of_ms(ms, quarter_ms, split)` takes the plain figure whose boundary the length passes: for a pair (shorter,
longer), the boundary is the shorter figure's length times 1.5 when the shorter is a negra or longer, and times
(1 + split) for the pairs from corchea-negra down. The comparison is strict: with a negra of 200 ms, 300 ms is a negra
and 310 ms a blanca, as in the user's example. The pair corchea-negra counts as "corchea and shorter": a corchea is a
corchea up to 85 % of a negra.

## 4.2 The measurements

On the 10 viewer songs (`study_figures`, scratch script), with Sonnet's reference figure so that the comparison with
Sonnet's own figures is fair, the median over the songs:

| Length | Split | Notes in runs of even gaps whose figure differs from the run's | Same figure as Sonnet |
|---|---|---|---|
| raw | 0.5 | 36.6 % | 43.2 % |
| raw | 0.7 | 37.2 % | 43.4 % |
| raw | 0.8 | 37.5 % | 43.1 % |
| capped at the next onset of the hand | 0.5 | 4.6 % | 77.0 % |
| capped | 0.6 | 1.6 % | 77.2 % |
| capped | **0.7** | 3.5 % | 75.1 % |
| capped | 0.8 | 3.8 % | 68.0 % |
| capped, one figure per run of even gaps | **0.7** | 0 % (by construction) | **77.8 %** |

"Runs of even gaps": three or more onsets of one hand whose gaps are within 12 % of the run's first gap. Sonnet's
figures are not the truth (it wrote them from the gaps, with puntillos and tuplets), but they are a reading of the
rhythm that the research measured best on printed scores.

The cap is the large effect: without it, about a third of the notes in an even run change figure inside the run (the
ragged sheet that the time model describes), and less than half agree with Sonnet. The split matters little once the
lengths are capped. 0.6 and 0.7 are within 2 points; 0.7 is better on 7 Years (67 % against 59 %) and is one of the
user's two values; 0.8 loses 7 points (Halleluyah 66 % against 78 %, Superestrella 50 % against 58 %). **The split is
0.7** (the checklist decision of Phase 2).

One figure per run of even gaps raises the agreement on every song (median 75.1 % to 77.8 %; Shut Up and Dance, the
staccato song, 36.8 % to 43.0 %).

## 4.3 Chords

After the cap, 1.8 % of the chords (median) have notes of different figures. A chord takes the figure most of its
notes have, ties to the longer figure.

## 4.4 What the figures are on the library

On the 33 songs (64,744 notes): corchea 51 %, negra 21 %, semicorchea 17 %, fusa 4 %, blanca 3 %, semifusa 2 %,
redonda 1 % (grace notes not counted).

# 5. Grace notes (task 2.4)

The user's review replaced the limits of this section (section 13); the numbers below are the first version.

The two-step rule alone made many false grace notes: a corchea 480 ms before a blanca is two steps shorter, and so is
a note 160 ms before a corchea when the reference is long (7 Years: 151 grace columns, 14 % of its columns). A grace
note is played quickly, so a time limit was added (grace columns on the 10 viewer songs, the name rule included):

| Limit | Halleluyah | Superestrella | 7 Years | Moonlight Shadow | others |
|---|---|---|---|---|---|
| none | 27 | 83 | 151 | 84 | 5 to 60 |
| 80 ms | 2 | 53 | 0 | 34 | 0 to 4 |
| 100 ms | 11 | 58 | 0 | 54 | 0 to 6 |
| 120 ms | 12 | 58 | 0 | 56 | 0 to 6 |

100 ms was kept. In Superestrella most of the remaining ones were the lower note of an octave played 80 ms early; a
grace note is a neighbour or a leap, never the same note name, so a note that shares a name with the main chord is not
a grace note. The final rule (`find_graces`): one or two columns of one hand, each two figures or more shorter than
the next note, at most 100 ms before the next onset, sharing no name with the main chord; a longer chain stays
written. One grace note is a slashed corchea (`grace/`), two are unslashed semicorcheas (`grace`). Library: 327 grace
columns of 38,966.

# 6. Alteraciones (task 2.5)

## 6.1 Rules 1 to 5 are a function

`spelling.spell_pc(pc, key)`: a note of the armadura keeps its name; a white key outside it (its natural name is
altered by the armadura) takes the other name with one sign when it has one (Si# and Mi# in armaduras with sostenidos,
Dob and Fab with bemoles), otherwise the becuadro; a black key outside the armadura takes a sostenido or a bemol as
the armadura does; Do mayor uses its table. `check_rules()` goes over the 15 armaduras and 12 keys: every result
sounds right, no double sign, a becuadro only on a note of the armadura, no sign against the armadura's family. A test
keeps it.

Rule 4 needs one precision the plan did not state: Sol, Re and La in Mi mayor have no other name with one sign (Fa##,
Do##, Sol## are forbidden by rule 3), so they keep the becuadro.

## 6.2 Do mayor

Rule 5 gives no answer with no armadura. The research rulebook (classical scores) measured: Do# (spell.6, 78 to 89 %),
Fa# (spell.3, 93 to 98 %), Sib (spell.5, 84 %), Sol# (spell.4, the leading tone of La menor, 86 to 90 %), and for
#2/b3 the flat when there is no step (spell.7: "in major, prefer b"). The table is **Do#, Mib, Fa#, Sol#, Sib**.

## 6.3 The armadura of each passage

`choose_keys`: a shortest path over the columns with 15 states (the armaduras), the cost of a column being the signs
its notes print, plus 0.01 per column and per sign of the armadura (it only breaks ties), plus 12 signs per change,
and at least 48 columns between two changes. With 0.04 per sign of the armadura, Raise Your Glass changed to Do mayor
to save 4 signs; at 0.01 it does not.

On the library: the song's first armadura equals the saved `keySignature` in 28 of 33 songs. The 5 others: the two
parts of Superestrella and I Knew You Were Trouble take 6 sostenidos instead of 5 (the key Fa is then Mi#, a note of
the armadura: fewer signs), Party in the USA takes 6 sostenidos instead of 5 bemoles, and Can't Stop the Feeling starts
in La mayor (its first 14 s) before the saved Fa mayor. 5 armadura changes in 3 songs, each one saving many signs (Can't
Stop the Feeling: its passages in Mib mayor and Do mayor would print 98 and 510 signs in the first armadura, against 3
and 1).

## 6.4 How many signs

471 signs on 64,744 notes (0.7 %): 251 sostenidos, 155 bemoles, 65 becuadros. **Rule 4 prints 110 of them, in 12
songs**, and 95 of those 110 are in armaduras of one to three signs: 1973 (La mayor, the key Do as Si#, 45 notes),
Grace Kelly (Sol mayor, the key Fa as Mi#, 16), Raise Your Glass (Sol mayor, 14), The Winner Takes It All (Fa mayor,
the key Si as Dob, 10). This is section 10.2.

# 7. The algorithm on the library (task 2.6)

`propose_frames(notes, key=None, key_changes=None, quarter_ms=None)`: `frames.from_notes`, the reference figure, the
figures, the grace notes, the beam groups, the armaduras, the spelling, the clefs and 8va. The starting hands come
from `pipeline.starting_hands(audio_uuid)` (outside the core): a saved hand that was not guessed stays, every other
note takes the hand of `inferred_split(keep_saved=True)` read back by `saved_hands.hands_of_split`.

**Beam groups** (plan section 3.11): consecutive columns of one hand with corcheas or shorter, joined when the gap
between them is a corchea or shorter (`figure_of_ms(gap) >= 8`); cut at a jump of more than 12 semitones (the top note
of the right hand, the bottom note of the left), where the direction turns after three steps in one direction, and
into near-equal parts of at most 8 (12 notes are 6 + 6, not 8 + 4). Library: 5,891 groups, sizes 2 to 8 spread evenly
(2: 1,283; 8: 802); cuts at a jump 1,420, at 8 notes 1,277, at a turn 504.

**Clefs and 8va**: a shortest path per hand over (clef, 8va) states with the ledger lines of each column, 3 per change
(clef.L6), 3 more inside a beam group, 0.25 per column for the hand's second clef, 2.5 per column under 8va, and the
left hand never in the bass clef four ledger lines or more above the staff (clef.L3). The 8va cost started at 1:
Die Young then put 773 right-hand notes under 8va for chords topped by E6; at 2.5 an 8va needs notes around G6
(clef.6). Library: 500 clef changes, 1,921 notes under 8va.

Per song (measured in the backend container, 2026-10-23; "signs" counts the printed sostenidos, bemoles and becuadros,
"rule 4" the part of them that are Mi#, Si#, Dob or Fab):

| Part | Song | Notes | Armadura (saved) | Changes | Signs (rule 4) | Grace columns | Beam groups | Clef changes | 8va notes | Hands (ms) | Algorithm (ms) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `daf087e9` | 7 Years | 1,458 | 2b (2b) | 0 | 0 (0) | 0 | 193 | 2 | 0 | 594 | 196 |
| `f4c4de9a` | Superestrella (piano tutorial cover) | 1,503 | 6# (5#) | 0 | 8 (0) | 21 | 158 | 94 | 628 | 6 | 220 |
| `43faf78e` | Halleluyah | 985 | 0 (0) | 0 | 16 (0) | 2 | 113 | 4 | 50 | 1074 | 156 |
| `51b12412` | Party in the USA | 1,738 | 6# (5b) | 0 | 7 (0) | 10 | 169 | 15 | 0 | 1025 | 144 |
| `dff5097c` | Stronger | 2,076 | 0 (0) | 0 | 21 (0) | 1 | 193 | 2 | 0 | 541 | 159 |
| `d64acd29` | Club Can't Handle Me | 3,512 | 0 (0) | 0 | 3 (0) | 27 | 257 | 6 | 0 | 1546 | 234 |
| `12f777af` | Raise Your Glass | 1,814 | 1# (1#) | 0 | 26 (14) | 30 | 186 | 8 | 0 | 790 | 193 |
| `6eb7af4e` | I Knew You Were Trouble | 1,713 | 6# (5#) | 0 | 0 (0) | 13 | 188 | 16 | 0 | 769 | 280 |
| `b80e6f5a` | Birds of a Feather | 1,449 | 2# (2#) | 0 | 0 (0) | 0 | 130 | 8 | 0 | 511 | 705 |
| `fb0b0989` | The Winner Takes It All | 2,692 | 1b (1b) | 0 | 74 (10) | 15 | 270 | 12 | 90 | 1939 | 523 |
| `3633a0c3` | Fate of Ophelia | 2,026 | 1b (1b) | 0 | 0 (0) | 0 | 154 | 6 | 0 | 584 | 296 |
| `0815f602` | La Tortura | 2,154 | 0 (0) | 0 | 52 (0) | 0 | 162 | 0 | 0 | 730 | 237 |
| `2ed0f379` | Poker Face | 1,985 | 5# (5#) | 0 | 20 (0) | 0 | 212 | 2 | 0 | 548 | 194 |
| `f3680cb8` | Titanium | 2,221 | 3b (3b) | 0 | 0 (0) | 0 | 198 | 14 | 0 | 822 | 162 |
| `19187d10` | Wild Ones | 1,645 | 4b (4b) | 0 | 3 (1) | 12 | 181 | 12 | 0 | 597 | 102 |
| `4cb9cb38` | Hips Don't Lie | 1,614 | 5b (5b) | 1 | 4 (0) | 6 | 154 | 14 | 0 | 1050 | 121 |
| `e578f3c0` | Die Young | 2,485 | 4# (4#) | 0 | 7 (7) | 10 | 237 | 47 | 413 | 972 | 225 |
| `b064f815` | Airplanes | 2,056 | 3# (3#) | 0 | 4 (3) | 6 | 49 | 10 | 15 | 692 | 330 |
| `f285e4b7` | Can't Stop the Feeling | 2,675 | 3# (1b) | 2 | 49 (2) | 53 | 264 | 6 | 0 | 1497 | 242 |
| `e3d7c376` | What Makes You Beautiful | 2,161 | 4# (4#) | 0 | 7 (0) | 0 | 165 | 0 | 0 | 611 | 165 |
| `a585f9eb` | Superestrella | 1,343 | 6# (5#) | 0 | 6 (1) | 2 | 139 | 42 | 310 | 1349 | 146 |
| `68e277fe` | Shut Up and Dance | 1,992 | 5b (5b) | 0 | 4 (0) | 0 | 193 | 0 | 0 | 692 | 199 |
| `96768e80` | The Other Side | 2,019 | 3# (3#) | 0 | 10 (5) | 0 | 184 | 0 | 0 | 910 | 137 |
| `f73116dd` | 2002 | 1,615 | 4# (4#) | 0 | 0 (0) | 7 | 188 | 14 | 24 | 643 | 133 |
| `1a16a836` | 7 Years (viewer) | 1,458 | 2b (2b) | 0 | 0 (0) | 0 | 193 | 2 | 0 | 516 | 117 |
| `b2db46eb` | 99 Red Balloons | 2,599 | 4# (4#) | 0 | 30 (5) | 17 | 180 | 31 | 223 | 1217 | 174 |
| `bef90052` | Bonfire Heart | 1,677 | 0 (0) | 0 | 0 (0) | 30 | 214 | 57 | 93 | 1365 | 148 |
| `aa07c1c0` | Stay the Night | 1,470 | 2# (2#) | 0 | 10 (0) | 9 | 164 | 6 | 0 | 756 | 430 |
| `c0edc9b0` | Moonlight Shadow | 2,384 | 4# (4#) | 0 | 5 (1) | 50 | 269 | 44 | 75 | 1003 | 184 |
| `56543911` | Grace Kelly | 2,144 | 1# (1#) | 2 | 60 (16) | 3 | 135 | 4 | 0 | 673 | 125 |
| `3c8d4cfa` | Drivers License | 1,733 | 2b (2b) | 0 | 0 (0) | 0 | 142 | 4 | 0 | 551 | 202 |
| `a1c30047` | 1973 | 2,730 | 3# (3#) | 0 | 45 (45) | 0 | 171 | 12 | 0 | 837 | 608 |
| `92255337` | The One That Got Away | 1,618 | 4# (4#) | 0 | 0 (0) | 3 | 86 | 6 | 0 | 722 | 253 |

Medians: the starting hands 756 ms (max 1.9 s; the beam search, cached per process by `split_cache`; Superestrella's
cover has every hand saved, 6 ms), the algorithm 194 ms (max 705 ms), F1 write 5 ms, read 10 ms, F1 text 27 kB (max
43 kB).

The many clef changes of Superestrella's cover (94), Bonfire Heart (57) and Moonlight Shadow (44) come from the
starting hands: the left hand holds notes up to C6 and the right hand notes down to A1, which only another clef can
show. The LLM decides the hands in Phase 4.

# 8. The gallery (task 2.7)

`scripts/sheet_gallery.py` builds [`gallery/phase-2/index.html`](gallery/phase-2/index.html) (one file, 590 kB, the
drawings inline; `uv run --with verovio==6.3.0`, so Verovio is not a backend dependency). The engine for a sheet
without compases is Phase 3, and the bars engine draws rests, compás lines and the accidental memory of the compás,
so the gallery draws with Verovio from MEI: one measure per armadura, no meter, an invisible bar line, the gaps as
invisible `space`, every note outside the armadura with its own written sign, 8va as `octave` with the written octave.
Times are proportional where the figures allow it (a timeline in 1/32 of a negra, pushed later when a figure needs
more room); Verovio gives little width to the invisible space, so the drawing checks names, figures, grace notes and
beams, not the spacing.

The 14 cases: the cap (Bonfire Heart, with the raw-length drawing below), a short left-hand chord before 2.4 s of
silence (Hips Don't Lie), a run of even notes (7 Years), grace notes (Moonlight Shadow, Can't Stop the Feeling), an
octave played unevenly that is not a grace note (Superestrella), rule 4 in Mi mayor (Die Young, the user's example),
La mayor (1973), Sol mayor (Grace Kelly) and Fa mayor (The Winner Takes It All), each with the becuadro drawing below,
the becuadro when there is no other name (Poker Face), Do mayor (Stronger), a sign every time (Grace Kelly), an
armadura change (Grace Kelly). The page was checked by screenshots (Playwright) before it was shown.

The page is served on the machine with `python3 -m http.server 8715 --bind 0.0.0.0` from the `gallery/` folder:
`http://ubuntu:8715/phase-2/`.

# 9. Checks

| Check | Result |
|---|---|
| Backend, full run in the image **on the CPU** (the app's backend holds the GPU) | 1,303 tests after the review (Phase 1: 1,287, plus the 16 of `test_sheet_frames.py`): 1,299 passed, 1 skipped, the same 3 failures as in Phases 0 and 1 (`test_the_worked_example_at_00_46_prints_three_equal_corcheas`, and the two Transkun tests that fail only without a GPU); 114 s |
| The golden files of the core | 139 of 139, unchanged (`test_sheet_core_golden.py`, `test_sheet_core_chain.py`): the bars path did not change; the import boundary allows the new modules |
| `flake8` on `src/aitu_backend/sheet`, `pipeline.py`, `scripts`, the new test | clean |
| `black` | the changed files formatted |
| mypy on `src/aitu_backend` | the 20 errors of before (the core is still skipped) |
| `scripts/docs/check-links.py` | passed (section 11) |

The frontend was not changed. The running app reloaded when `pipeline.py` changed (`/health` on 8765 answered 200
after it).

# 10. Decisions for the user

## 10.1 The cap at the next onset

The plan (section 3.1) says the figure of a note comes from its own length. Under the pedal the measured length runs
past the next note of the same hand (section 2.2), and the raw length makes the even runs ragged (37 % against 3.5 %)
and halves the agreement with Sonnet (section 4.2). The algorithm caps the length at the next onset of the hand; a
short note followed by silence still keeps its own short figure, as the user asked. Gallery case 1 shows both.
Recommendation: keep the cap.

## 10.2 Rule 4 in armaduras of one to three signs

Rule 4 writes the white key Fa as Mi# in Sol mayor (a Fa mayor chord is Mi#-La-Do), Do as Si# in Re and La mayor (a Do
mayor chord is Si#-Mi-Sol), and Si as Dob in Fa mayor (a Sol mayor chord is Sol-Dob-Re). 95 of its 110 notes in the
library are in these armaduras. Options: (a) rule 4 everywhere, as written; (b) rule 4 only in armaduras of four signs
or more, a becuadro below (the user's own example, Mi mayor, is four); (c) always the becuadro. Gallery cases 7 to 10
show each rule 4 passage and its becuadro version. The change for (b) or (c) is one condition in `spell_pc`.

## 10.3 How they were closed

The user answered the gallery with "perfect, proceed" and did not choose between the options. The phase closed with
the agent's recommendation for 10.1 (the cap stays) and the user's rule as written for 10.2 (rule 4 everywhere, option
a). Either can still change with one condition: the cap in `proposal.frames.assign_figures` (`cap=`), rule 4 in
`spelling.spell_pc`. Phase 4 shows rule 4 again in its gallery (the LLM's armaduras change how often it prints).

# 11. Documentation

- [`03-plan.md`](03-plan.md): Phase 2 in progress; its tasks with what the study found; section 3.3 and 3.4 notes;
  section 11.
- [`03-checklist.md`](03-checklist.md), [`README.md`](README.md): the state; the decisions of Phase 2.
- `aitu-backend/src/aitu_backend/sheet/README.md`: section 9 (the new sheet), the modules table, the tests.
- `context/backend/README.md`: the new modules and the two commands.
- `scripts/docs/check-links.py`: passed.

# 12. Notes for later phases

- **Phase 3 (the engine).** It draws the frames sheet: `Note.frame` is the drawn column (both hands share it), grace
  notes sit at their own earlier column, `covered` notes are not drawn, `Note.ottava` marks the 8va notes (the pitch is
  sounding), clef changes are `(frame, staff, clef)`, armadura changes `(frame, key)`. Every note outside the armadura
  prints its sign from `frames.printed_signs` (rule 1, and the courtesy sign of rule 7, section 15). The figures can be longer than the gap to the next note (up to the boundary of
  their figure), so the spacing must not take a figure as a duration.
- **Phase 4 (the LLM).** The LLM's text must be mapped back to the notes (`frames.cells_of`) to recompute the
  figures, which are a rule (they need `on_ms` and `len_ms`). The reference figure is the LLM's choice; the pulse
  estimate agrees with Sonnet in 5 of 10 songs (section 2.4). Octaves and chords played unevenly over 40 to 80 ms are
  left as two columns (section 2.3); the LLM could join them with `arp`. Cuts at a jump are the most common beam cut
  (1,420): a left-hand bass note and a chord more than an octave above it are cut apart, which may split left-hand
  patterns that the user wants in one group; the phase 4 gallery shows it.
- **Phase 5.** `pipeline.starting_hands` costs 0.5 to 1.9 s on a song whose hands are not all saved (the hand split);
  the algorithm 0.1 to 0.7 s. The saved `keySignature` is not used by the algorithm (`key=None`); a part whose user
  chose its key should pass it (`key=`), which also disables the armadura changes unless `key_changes` are given.
- The scratch study scripts (lengths, splits, grace limits, the passage finder) are not kept; their numbers are in
  sections 2, 4 and 5. `scripts/write_sheet.py --layer private --json` reproduces section 7.

# 13. The user's review of the gallery (iteration 1, 2026-10-23)

The user looked at the left hand of gallery case 1 (Bonfire Heart, 2:20) and asked for three changes:

1. **A beam group is uniform.** A group holds one figure; when the figures differ, the group is cut. One single note
   of another figure is allowed, but only one, and the group must not hold several sub-groups (the first version
   beamed two pairs of semicorcheas and a corchea under one beam).
2. **Two figures apart is an acciaccatura**, without the extra limits: a fusa before a corchea must not stay written.
3. Fusas inside a beam group drew badly (partial beams).

What changed in `proposal/frames.py`:

- `_uniform` cuts each chain of beamable columns into runs of one figure. A single note one figure away may close a
  group or open the next one, never sit inside it, and only next to two notes or more of the group's own figure (an
  octave split as a semifusa and a fusa was drawn as a group of two notes under four beams). The jump, turn and
  maximum of 8 cuts then apply inside each group.
- `find_graces`: a semicorchea or shorter, two figures or more shorter than the next note of its hand, whose gap to
  that note is shorter than the note's own figure (it sounds just before it); one or two such columns, a longer chain
  stays written. The 100 ms limit and the note-name rule (octaves played unevenly, repeated notes) were removed, as
  the user asked: an octave played unevenly is now an acciaccatura of the upper note. The semicorchea limit and the
  gap condition keep the false grace notes of section 5 away (a corchea 480 ms before a blanca).
- The gallery leaves out a beam group that its passage cuts (case 1 drew a one-note beam at its start).

Library after the change (33 songs, every sheet valid, every round trip exact):

| Count | Before | After |
|---|---|---|
| Grace columns | 327 | 1,712 (4.4 % of 38,966 columns; Can't Stop the Feeling 171, 7 Years 143, Raise Your Glass 116) |
| Beam groups | 5,891 | 5,845 |
| Group sizes 2 / 3 / 4 / 5 / 6 / 7 / 8 | 1,283 / 803 / 728 / 829 / 766 / 680 / 802 | 1,490 / 1,466 / 919 / 671 / 461 / 385 / 453 |
| Cuts: figure change / jump / 8 notes / turn | - / 1,420 / 1,277 / 504 | 4,290 / 1,010 / 603 / 194 |
| Algorithm, median per song | 194 ms | 165 ms |

Tests: `test_a_beam_group_holds_one_figure`, and `test_grace_notes_by_the_two_step_rule` with the new limits (16
tests in `test_sheet_frames.py`).

# 14. The user's review (iteration 2, 2026-10-23)

Two errors the user found, both real:

1. **Three semicorcheas of one group drawn without their beam** (case 6, Superestrella). The sheet had them in one
   group (`b33`), but the gallery dropped every group its passage cut, to remove the one-note beam of iteration 1.
   The gallery now widens each passage to whole beam groups and to the grace notes of its first note
   (`whole_groups`); a check over the 14 cases confirms that every group touching a passage is drawn whole.
2. **Short beams that do not touch their stem.** The MEI put the invisible spaces (the gaps in time) inside
   `<beam>`, and Verovio drew a short beam for each space of a semicorchea or shorter, between two stems. The gallery
   now writes each group as a `beamSpan` whose `plist` lists its notes only.

The user also asked to be certain that consecutive notes of one figure are never separated without a reason. A check
over the library took every pair of consecutive columns of one hand with the same beamable figure and no shared beam.
It found 23 pairs separated by no rule: a turn cut left the last note of a chain alone, or a turn followed by a jump
left one note between them. `_split` now lets only a jump leave a note alone (a note that a turn would leave alone
stays with the group before or after it), and splits at the maximum of 8 into near-equal parts (never a lone note).
After the fix, every such pair has a reason: a gap longer than a corchea 533, a jump of more than an octave 868, a turn
or the maximum of 8 757, and one pair whose gap is 520 ms in whole columns but longer than the corchea limit (524 ms)
on the real onsets. Library: 5,846 beam groups, 33 of 33 sheets valid, every round trip exact.

# 15. Rule 7: a courtesy sign after a becuadro (the user, 2026-10-23)

After the phase closed, the user added one rule to the alteraciones (plan section 3.4, rule 7). When a note of the
armadura gets a becuadro, the next time that note is played at its armadura name it was an alteration, and the
becuadro no longer applies; to say so, its sostenido or bemol is printed again, although the armadura already gives
it. This is a deliberate abuse of notation, kept to two cases: the return is in the same beam group as the becuadro,
or it is the next note of the hand.

How it is read in the code (`frames.printed_signs(sheet)`, used by the gallery and, from Phase 3, by the engine):

- "the same note" is the same name and octave (the same line or space of the staff), in the same hand;
- only the first return after a becuadro counts; a later return prints nothing, and a new becuadro starts again;
- the return must be at the armadura's own alteration (Re# in Si mayor), after a becuadro of the same name and octave;
- the names do not change (`spelling.spell` is still a pure function); only the printed signs do, so F1 carries
  nothing new and `frames.check` is unchanged.

Library: 15 courtesy signs in 5 songs (Poker Face 9, Can't Stop the Feeling 2, 99 Red Balloons 2, Party in the USA 1,
Moonlight Shadow 1); `scripts/write_sheet.py` counts them as `courtesy`. Gallery case 14 (Poker Face, from 0:38) shows
both cases, and case 11 shows one inside a beam group. Test: `test_a_courtesy_sign_after_a_becuadro`.

The gallery also changed how it chooses a passage: each end moves at most 2 seconds to a column that cuts no beam
group, or else to one that leaves no group with a lone note (the earlier rule, "widen until no group is cut", grew
case 14 to 18 seconds because the groups of the two hands overlap). 12 of the 15 cases cut no group; in cases 10 and
14 a group goes on past an edge with two notes or more inside, beamed.

