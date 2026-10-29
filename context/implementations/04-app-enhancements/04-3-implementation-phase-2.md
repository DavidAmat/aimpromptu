# 04-3 · Phase 2: the gallery of patterns

Status: **approved by the user and merged into `master` on 2026-10-29** (after review 3: the right hand across Chopin's works; review 2 put every Chopin example in
the app's notation and gave the numbers). Built on the branch `feat/04-3-phase-2`, in the worktree
`/home/david/Documents/projects/music/aimpromptu-04-3-phase-2` (plan section 7.4: Phase 2 ran in parallel with Phase 1,
which owns the main checkout); the worktree was removed after the merge. No `src/` change, no AI call, no database
access. The status of `patterns.json` is now "approved"; the next phase is Phase 2b (frame numbers), then Phase 3.

Audience: the agents of this plan (the Phase 2 agent when the user answers, and Phase 3). Technical.

# 1. What was done

| Task | Result |
|---|---|
| 7.4 setup | Worktree made from `master` (`4950901`); first commit `717aaf5` holds the brief, the plan, `context/guidelines/` (all three files, untracked in the main checkout too) and the three images, copied unchanged from the main checkout |
| 2.1 the Chopin folder | Present: `/home/david/Documents/projects/music/chopin`, 17 PDFs. Nothing asked of the user |
| 2.2 to 2.4 sources and passages | 10 pieces used (section 2); the user's passages are all in (Ballade 1 pages 10 and 12, Ballade 4 pages 41 to 56, the Waltzes); left out: the scale-like runs, except as super hard |
| 2.5 drawn patterns | 33 drawn with the app's engine from F1 frames text: the 3 easy ones of the brief, and 30 variations (10 easy, 10 medium, 10 hard) asked in the user's review 1 (section 4) |
| 2.6 snapshots | 29 PNG in `images/chopin_passages/` (1.3 MB), cut by script, each checked zoomed against the score and the kern (section 3) |
| 2.7 the gallery | `gallery/04-3-phase-2/index.html` and `patterns.json` (105 patterns: 50 left hand, 55 right hand), from one list in `tools/build.py` |
| 2.8 review | Served at `http://ubuntu:8098/gallery/04-3-phase-2/index.html` (8099 was taken by another server). Review 1: 30 drawn variations; review 2: the Chopin examples in the app's notation and the numbers (section 4.3), and the catalog and frame-number decisions recorded in plan section 5.10 and Phase 2b |

# 2. Sources

The PDFs are scans (no text layer). Page numbers below are **PDF pages** (what a viewer shows), which differ from the
printed numbers in some books: `ballades.pdf` and `waltzes.pdf` have none; `preludes.pdf` printed = PDF - 2;
`nocturnes.pdf` printed = PDF + 3. The Waltzes index of incipits is PDF page 13 (Op. 18 p15, 34/1 p25, 34/2 p35,
34/3 p40, 42 p45, 64/1 p55, 64/2 p59, 64/3 p65, 69/1 p71, 69/2 p79, 70/1 p88, 70/2 p92, 70/3 p99, posthumous p103,
p108, p112, p115). Preludes: No. 4 p13, 7 p16, 13 p26, 15 p29, 20 and 21 p45. Nocturne Op. 9 No. 2: p10.

The kern files (`poc-aitu-research/data/raw/kern/humdrum-chopin-first-editions/kern/`) were read with music21
(`tools/kdump.py FILE A B`: notes per bar and hand; in these files the first part is the right hand). Every note
named in a one-line explanation was checked there. Bar numbers: the kern counts an upbeat as bar 1 in Waltz Op. 69
No. 1 and No. 2 (kern = edition + 1); in the other pieces used, kern and edition bars agree. `patterns.json` keeps
both (`bars` of the edition, `kernBars`).

The user's example line "Si2-Fa3-Lab3-Re4-Lab3-Fa3" is not in the Ballade 4 kern (searched as a sequence and as a
set of six notes starting on a Si); it reads as an example of the kind. The gallery gives that kind with Prelude 21
(`line-of-no-chord`).

The research's `patterns.md` (E11) has six excerpts at levels 3 to 5 of the old ladder (Nocturnes); they were not
reused as patterns, because the user's brief now defines the levels by name and asked for Ballades and Waltzes first.

# 3. The snapshots

## 3.1 How they were cut

`tools/layout.py` renders a page at 200 dpi (`pdftoppm`), straightens it (the angle that gives the sharpest row
profile in the middle 40 % of the page: the scans are rotated by up to 1.5°, and the Waltz pages are curved like a
book), finds the staves (five lines in the middle strip), pairs them into systems by distance, and lists barline
candidates (a column dark inside both staves). The candidates are good on the Ballades and noisy on the curved
Waltz pages, so the x edges of each crop were chosen by hand on an overview (`overview.py`, not kept: a page with
the candidates and an x scale drawn on it). `tools/crop.py` then cuts both staves of the bars, puts the other hand at
25 % ink, and, for a crop that starts in the middle of a system, puts the clef and key of that line in front with
the system's bar number blanked (it would name the wrong bar). Re-running `crop.py` reproduces all 29 files byte for
byte (checked).

## 3.2 What the zoomed check found and fixed

- The first clef pieces carried the system's bar number (65 before bars 68 to 71; 105 before 106 to 108): blanked.
- Five crops (Preludes 13, 15, 20, 21, the Nocturne) ended early: their overview sheet was shown to the agent scaled
  by 1/1.10 and the positions were read without the factor. Recut and checked again.
- Wrong descriptions caught against the kern: the Ballade 4 sweep goes to Lab4 (not Lab5: "two octaves", not
  three); the stretto octaves move by steps (Dob, Sib, Do, Sib), they do not jump; Prelude 4's first change moves
  two notes, not one; in Prelude 21 the two voices move apart (lower down by semitones, upper up).
- Left as they are (minor): the top fingering and a trill sign of Ballade 4 bars 50 to 52 are cut by the margin to
  the system above; fingerings under some Prelude crops are cut by the margin to the system below.

# 4. The patterns drawn by the app

## 4.1 First version: the three easy patterns of the brief

Chopin has no easy left hand in the sense of the brief, so the app drew three (`held-triad`, `low-note-then-chord`,
`triads-in-steps`) from F1 frames text with `aitu_backend.sheet.engrave.frames.render_frames` (`px_per_space=10`). It
runs in the backend container, as section 7.4 rule 4 says: `docker exec -i aimpromptu-backend-1 python - < drawn.py`,
writing to `/home/app/04-3-phase-2/` (host `/mnt/ssd2/aimpromptu/home/04-3-phase-2/`), then copied into
`gallery/04-3-phase-2/drawn/` (`.f1` and `.svg`).

## 4.2 The user's review 1 (2026-10-29): ten variations per level

The user found the gallery "perfect" and asked for more drawn left hands: at easy, the arpeggios that stay in one
position (up or down), a low note then two notes of the chord repeated, the three notes of the chord up and down, a
chord then two of its notes in a higher position, and every two-note chord (also after a bass note, or followed by an
arpeggio in corcheas); then about ten variations each at easy, medium and hard, without overlapping, with small
changes (two-note chords at easy, a new rhythm or chord note at medium, one more note in the chord at hard).

`tools/drawn.py` (it replaces `easy.py`) draws all 33. Every drawing has the same right-hand melody (Fa major) and the
same harmony (Fa two bars, Do one bar, Sib and Do half a bar each), so that only the left hand changes. A pattern is
a four-beat template over named notes of each chord (`t` the triad near Fa3, `four` the triad with its octava, `six`
with the sixth, `open` root-fifth-octava-tenth, `oct`, `low`, `fifth`, `sixth`, `dy`, `up2`, `th`); a harmony of two
beats takes the first half of the template. Two rules came from the zoomed check:

- The low note of the new patterns is near the chord (Fa2, Do3, Sib2): with Do2 and Sib1 an easy hand jumped two
  octaves. The approved `low-note-then-chord` keeps Do2 and Sib1 (key `deep`).
- A held note never starts on the same frame as the notes moving above it: the engine drew the held bass of
  `held-bass-under-moving-thirds` as part of the first corchea chord. The upper voice starts half a beat later.
  `held-bass-under-rocking-notes` first held Sib2 under Sib3-Re4 (16 semitones); it now rocks on the third above
  each bass (`th[0]`), 7 semitones.

The melody's last note is now Do5 (it was Mi4), so that no left-hand Mi4 doubles it in the last half bar; the three
first drawings changed only there.

`drawn.py` prints the widest chord and the widest range of a half bar (semitones), a first measure for Phase 3:

| Level | Widest chord | Widest range of a half bar |
|---|---|---|
| Easy (13 drawn) | 9 (a triad), two-note chords 5 to 9 | 7 to 12 in one position; 19 with a low note, 28 in `low-note-then-chord` |
| Medium (10 drawn) | 12 (the octava) | 9 to 16; 19 to 28 with a low note or an octava |
| Hard (10 drawn) | 12 (four-note chords) | 12 to 16; 24 to 31 with a low octava |

## 4.3 The user's review 2 (2026-10-29): every Chopin example in the app's notation, and numbers

The user asked that each passage shown only as a snapshot also be written in the app's notation and drawn as the
synthetic ones, and that the patterns be numbered inside each hand and level, so that the coming catalog of Enhance
with AI can name them (plan section 5.10).

`tools/transcribe.py` (research venv, music21) reads the bars of each Chopin example from the kern (`kern`,
`kernBars` in `patterns.json`), joins the ties, and writes the notes as the app stores them: onset and length in ms
(a negra = 600 ms), MIDI, hand (the part with the lower mean pitch is the left hand). Kern grace notes become notes of
50 ms just before their main note (60 ms per grace), so that the app's rule makes them decoration notes again. It
writes `tools/transcribe_run.py`, which runs in the container: `Notes` -> `propose_frames(notes, key=, quarter_ms=600)`
-> `f1.write(mode="frames")` -> `render_frames`; output in `transcribed/<snapshot name>.f1` and `.svg` (29 of each;
the left and right examples of the same bars are the same passage).

What the zoomed comparison with the snapshots found (23 different passages, drawing over snapshot):

- `kernBars` of five examples missed their upbeat (kern bar 0 in Waltz 64/2, Prelude 7, Nocturne 9/2; kern bar 1 in
  Waltz 69/1 and 69/2). Corrected in `build.py`.
- Waltz 69/2 came out in Do major: its kern has `*kcancel` after the armadura, which music21 reads as a second
  armadura with no signs at the same place. At one place the armadura with signs now wins.
- The armadura is the edition's. The app's own choice (`choose_keys`) was compared: it is worse on these short
  passages (Ballade 4, 38-40 in 5 sharps, 181-182 in 6 sharps), except Ballade 1, 106-108, which is on Mi towards La
  and which the edition writes with sharps over 2 flats: there the app's choice (3 sharps) is kept (`KEY` in
  `transcribe.py`), because under flats the app's rule spells the black keys as flats (Lab for Sol#).
- The rest follows the app's rules and is kept: one voice per hand (the held bass of Waltz 69/1 becomes a negra,
  cut by the next chord); a white key whose name is in the armadura takes its other name (Mi natural is Fab in Fa
  minor); the app's clefs (Nocturne 9/2, bar 2, takes the left hand to the treble clef); no tuplets (the groups of 7
  and 8 of Ballade 4, 152-153, are plain semicorcheas and fusas); the first edition's decoration notes of Waltz 42
  are at the start of bar 9 where the PWM edition has them at the end of bar 8.

Numbers: `build.py` gives each pattern `number` (from 1 inside its hand and level, in the order of `PATTERNS`) and
`ref` ("left hard 3"). A new pattern must be added at the end of its level in `PATTERNS`, so that approved numbers do
not change. The page shows "Hard 3" before each name, the app's drawing first and the edition's snapshot under it.

## 4.4 The user's review 3 (2026-10-29): the right hand across Chopin's works

The user asked for more right-hand patterns from more works, judged by hand motion: a static right hand is easy, also
with chords; hard is chords moving up and down in one run, or fast notes with no pattern, with many alterations or
ornaments; medium is in between (fast but with a shape that repeats; small chords of two or three notes, sometimes a
usual chord of four; a few alterations). The user suggested sampling about ten pages per work; the agent used the
kern files instead, because they cover every work with the bars as data, and looked at every candidate drawn by the
app.

- `tools/rh_study.py` (research venv, 30 processes, about 20 s): 198 pieces (one edition per opus and number; left
  out: Op. 3 and Op. 8 with cello and violin, Op. 65 whose kern has the cello only, Op. 74 songs, the violin files;
  files without two `**kern` spines), 22,274 windows of two bars. Per window of the right hand (the staff with the
  higher mean pitch): `fastest`, `density`, `chord_max/mean/share`, an octave hand tracker (`moves`, `shift`,
  `jumps`, `stretch`, `span`), `pattern` (share of beats whose shape repeats one of the two beats before), `chord_run`,
  `altered` (signs that differ from the armadura), `doubles`, `ornaments`, `graces`. The `*kcancel` armadura bug of
  section 4.3 appeared again here and was fixed the same way. Quartiles over all windows: fastest 0.25 / 0.33 / 0.5
  negras, moves 1 / 3 / 5, chord_mean 1 / 1.25 / 2, altered 0 / 0.13 / 0.29.
- `tools/rh_pick.py`: 20 kinds (6 easy, 5 medium, 5 hard, 4 super hard) as rules on the measures, two windows per
  kind at random (seed 4), one opus once only, so the 40 candidates come from 40 works. Drawn through the app's path
  (`rh_run.py`, generated, in the container) and checked one by one.
- Kept: 28 new Chopin patterns or examples (26 works); left out 12 (too close to a kept one, octavas in the right hand
  where a pattern was enough, a cross-hand passage of Scherzo 3, a chordal passage that the app draws without its
  triplets). The measures only find candidates: the level of each kept pattern was set by looking (for example the
  Op. 12 scale is fast and moves a lot but is the most regular pattern, so medium; Op. 66 repeats its figure but is
  fast and chromatic with a double sharp, so hard). Tempo is not in the kern, so "fast" means short figures.
- Changed by the user's rule: `melody-in-chords-one-rhythm` (Prelude 7) and `thirds-and-sixths-in-corcheas` (Waltz
  70/3) from hard to medium (static, a repeated shape). The right-hand numbers were not approved yet, so the numbers
  of the right-hand tab changed; the left-hand numbers did not.
- 18 drawn right-hand patterns (`drawn.py`, `RIGHT`: 5 easy, 5 medium, 5 hard, 3 super hard) for what the study did
  not give, over the held triad of the left hand and the shared harmony. Zoomed check fixes: "thirds in one position"
  also had fourths (renamed `two-note-chords-in-one-position`); the landing chord came only once (now at the end of
  each phrase, with notes of the harmony); the chromatic run only turned around a third (now eight semitones up and
  back).
- The study passages have no snapshot: their bars are kern bars, and the PDF pages were not looked up.

Result: the right-hand tab has 55 patterns (easy 10, medium 17, hard 17, super hard 11); the gallery 105.

# 5. The patterns

The list is in `patterns.json` (status `proposed`); the page shows the same list. Levels as the agent proposed them,
from the brief's section 5.1 of the plan:

The Chopin patterns (the 30 drawn variations of section 4.2 are listed in `patterns.json` and on the page):

| Hand | Easy | Medium | Hard | Super hard |
|---|---|---|---|---|
| Left (20) | `held-triad`, `low-note-then-chord`, `triads-in-steps` (drawn); `held-chord-repeated` (Ballade 1, 65-67) | `low-note-then-octave` (Prelude 7), `low-note-then-two-chords` (Waltzes 69/2, 64/3, 64/2), `held-bass-under-two-chords` (69/1), `low-note-then-two-chords-in-corcheas` (Nocturne 9/2), `same-chord-one-note-changes` (Prelude 4), `repeated-note` (Prelude 15), `octave-bass-in-negras` (Prelude 20), `low-note-then-small-wave` (Prelude 13), `simple-line-in-negras` (Ballade 1, 68-71) | `octave-then-chord-up-and-down` (Ballade 1, 106-108), `low-note-then-moving-chord` (Ballade 4, 9-11), `octaves-that-draw-the-chord` (Ballade 4, 38-40), `wave-in-one-position` (Ballade 4, 181-182), `line-of-no-chord` (Prelude 21) | `sweeps-over-two-octaves` (Ballade 4, 152-153), `fast-octaves-in-stretto` (Ballade 4, 198-200) |
| Right (9) | `slow-melody-single-notes` (Prelude 4), `melody-single-notes` (Waltz 69/2) | `second-note-on-long-notes` (Waltz 64/2, Ballade 1 68-71) | `melody-in-chords-one-rhythm` (Prelude 7), `melody-with-pieces-of-chords` (Ballade 4, 50-52), `melody-over-inner-line` (Waltz 42), `thirds-and-sixths-in-corcheas` (Waltz 70/3) | `full-chords-in-octaves` (Ballade 1, 106-108), `runs-in-groups` (Ballade 4, 152-153) |

Choices the user may want to change (for the review):

- `low-note-then-octave` (Prelude 7) is put at medium only because the brief puts octavas in the bass at medium; it
  is as easy to play as `low-note-then-chord`.
- `melody-in-chords-one-rhythm` (Prelude 7, right hand) is put at hard because it has three-note chords on every
  negra, beyond the brief's medium (two notes, three only to land). Its rhythm repeats and it is slow.
- `low-note-then-moving-chord` (Ballade 4, 9-11) is the brief's hard example almost exactly: the second chord is the
  first shape moved one step (down here; the brief's example goes up).
- Medium right hand has one pattern (two examples). Chopin's right hands are seldom at that level; more can be drawn
  by the app if the user wants them. Review 1 asked only for left hands.

# 6. Needed later

- **At the merge** (whichever of Phases 1 and 2 merges second): the folder's `README.md` gets rows from both phases,
  and section 10 of the plan gets a paragraph from each. Phase 1 commits the same brief, plan, guidelines and images
  as commit `717aaf5`; they must be identical (they were copied unchanged on 2026-10-29). If Phase 1 edited the plan
  in its branch, the merge of `04-3-plan.md` needs a manual pass.
- **At the merge**: stop the gallery server on port 8098 (`pkill -f "http.server 8098"`) and remove the worktree
  (`git worktree remove /home/david/Documents/projects/music/aimpromptu-04-3-phase-2`); then the gallery is served
  from the main checkout.
- **Phase 2b and Phase 4**: the catalog and the frame numbers of plan section 5.10. The catalog data is `patterns.json`
  with the F1 texts of `drawn/` and `transcribed/`; Phase 4 moves it into the backend's data.
- **Phase 3**: read `patterns.json` for the ids and levels (after the user's review sets `status` to approved); the
  kern refs give the notes for short F1 examples in the prompts. The licence of the kern files for prompt examples is
  an open point of Phase 5 (plan section 8).
- `/home/app/04-3-phase-2/` in the container holds the drawings' first output; it can be deleted after the merge.
