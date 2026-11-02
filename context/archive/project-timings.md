# The timings of a project's steps (history)

> **Archived 2026-11-02** (implementation 05, Phase 20): moved out of
> [`frontend/projects.md`](../frontend/projects.md) to keep that page short. These are measures taken in
> implementations 08 and 03; they are not measured again.

Measured with `npm run time:flow` on the RTX 4090 (implementation 08, 2026-10-01; the first piano
sheet measured again in every phase of implementation 02):

| Piece | Length | Piece in | First note | Notes saved | Predict hands (gone since implementation 03, Phase 5) | First piano sheet |
|---|---|---|---|---|---|---|
| Superestrella, uploaded | 3:09 | 0.2 s | 0.3 s | 27 s | 0.9 s | 0.6 s |
| The Winner Takes It All, from the library | 5:56 | 0.2 s | 0.2 s | 52 s | 2.4 s | 1.0 s |
| A new YouTube URL | 2:21 | 3.8 s (download) | 0.3 s | 21 s | 1.4 s | 0.6 s |

The Hands step and its column are gone since implementation 03, Phase 5. On the new Sheet step
(`npm run check:frames-sheet -- --live`, 2026-10-25, a 40 s clip of 7 Years): the algorithm's sheet on screen
0.9 s after the step opened, the AI's first part back after about 19 s (the measure of implementation 03, Phase 5), the whole clip written in 91 s for
$0.18. A whole song takes 4 to 17 minutes and $0.5 to $1.7 (implementation 03, Phase 4).

**Read notes** of a video, measured with `aitu-backend/scripts/bench_video_read.py` (Phase 5) on a
copy of Superestrella's tutorial video (3:09, 1,892 frames, 1,495 notes): 61 s in all, of which
measuring the roll takes about 37 s and reading the notes about 22 s. In the browser, the first
**Read notes** took 66 s and a second one 25.5 s, because the roll is measured once per fitting.

