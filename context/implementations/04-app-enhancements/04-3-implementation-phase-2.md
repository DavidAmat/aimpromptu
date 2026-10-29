# 04-3 · Phase 2: the gallery of patterns

Status: **built, waiting for the user's review** (task 2.8). Branch `feat/04-3-phase-2`, in the worktree
`/home/david/Documents/projects/music/aimpromptu-04-3-phase-2` (plan section 7.4: Phase 2 ran in parallel with Phase 1,
which owns the main checkout). Not merged. No `src/` change, no AI call, no database access.

Audience: the agents of this plan (the Phase 2 agent when the user answers, and Phase 3). Technical.

# 1. What was done

| Task | Result |
|---|---|
| 7.4 setup | Worktree made from `master` (`4950901`); first commit `717aaf5` holds the brief, the plan, `context/guidelines/` (all three files, untracked in the main checkout too) and the three images, copied unchanged from the main checkout |
| 2.1 the Chopin folder | Present: `/home/david/Documents/projects/music/chopin`, 17 PDFs. Nothing asked of the user |
| 2.2 to 2.4 sources and passages | 10 pieces used (section 2); the user's passages are all in (Ballade 1 pages 10 and 12, Ballade 4 pages 41 to 56, the Waltzes); left out: the scale-like runs, except as super hard |
| 2.5 easy patterns | Three drawn with the app's engine from F1 frames text (section 4) |
| 2.6 snapshots | 29 PNG in `images/chopin_passages/` (1.3 MB), cut by script, each checked zoomed against the score and the kern (section 3) |
| 2.7 the gallery | `gallery/04-3-phase-2/index.html` and `patterns.json` (29 patterns: 20 left hand, 9 right hand), from one list in `tools/build.py` |
| 2.8 review | Served at `http://ubuntu:8098/gallery/04-3-phase-2/index.html` (8099 was taken by another server); waiting for the user |

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

# 4. The easy patterns drawn by the app

Chopin has no easy left hand in the sense of the brief, so `tools/easy.py` writes three F1 frames texts (key 1b,
`quarterMs=480`, a negra = 12 frames) with the same right-hand melody in Fa major and the three left hands of the
brief, and draws them with `aitu_backend.sheet.engrave.frames.render_frames` (`px_per_space=10`). It ran in the
backend container, as section 7.4 rule 4 says: `docker exec -i aimpromptu-backend-1 python - < easy.py`, writing to
`/home/app/04-3-phase-2/` (host `/mnt/ssd2/aimpromptu/home/04-3-phase-2/`), then copied into `gallery/04-3-phase-2/drawn/`
(`.f1` and `.svg`). The drawings were checked zoomed (headless Chrome screenshots): every chord against its text, the
ledger lines of Fa2, Do2 and Sib1. One fix: the melody first ended on La4 over a Do chord; it now ends Sol4, Mi4.

| id | Left hand |
|---|---|
| `held-triad` | Fa3-La3-Do4 redonda twice, Mi3-Sol3-Do4, Fa3-Sib3-Re4 blanca, Mi3-Sol3-Do4 blanca |
| `low-note-then-chord` | Fa2 negra then Fa3-La3-Do4 blanca; the same on Do2 and Sib1 |
| `triads-in-steps` | Fa-La-Do, Sol-Sib-Re, La-Do-Mi, Sol-Sib-Re, ... in blancas |

# 5. The patterns

The list is in `patterns.json` (status `proposed`); the page shows the same list. Levels as the agent proposed them,
from the brief's section 5.1 of the plan:

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
  by the app if the user wants them.

# 6. Needed later

- **At the merge** (whichever of Phases 1 and 2 merges second): the folder's `README.md` gets rows from both phases,
  and section 10 of the plan gets a paragraph from each. Phase 1 commits the same brief, plan, guidelines and images
  as commit `717aaf5`; they must be identical (they were copied unchanged on 2026-10-29). If Phase 1 edited the plan
  in its branch, the merge of `04-3-plan.md` needs a manual pass.
- **At the merge**: stop the gallery server on port 8098 (`pkill -f "http.server 8098"`) and remove the worktree
  (`git worktree remove /home/david/Documents/projects/music/aimpromptu-04-3-phase-2`); then the gallery is served
  from the main checkout.
- **Phase 3**: read `patterns.json` for the ids and levels (after the user's review sets `status` to approved); the
  kern refs give the notes for short F1 examples in the prompts. The licence of the kern files for prompt examples is
  an open point of Phase 5 (plan section 8).
- `/home/app/04-3-phase-2/` in the container holds the drawings' first output; it can be deleted after the merge.
