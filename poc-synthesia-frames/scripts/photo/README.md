# The second rendering: a roll drawn over a photograph

The study behind `context/implementations/04-synthesia-to-notes/04-second-rendering-study.md`.
Every script is run from `aitu-backend` with its own interpreter and takes a scratch folder as
its first argument, where it reads and writes its `.npy` and `.json` intermediates:

```text
cd aitu-backend && .venv/bin/python ../poc-synthesia-frames/scripts/photo/<script>.py <scratch folder> [...]
```

The two videos are hardcoded by uuid: `b99bc3ae-…` is AITANA — SUPERESTRELLA (the photograph)
and `ddd8bce8-…` is Elektronomia — The Other Side (the plain rendering Phase 3 and 4 read). Both
are under `data/audio/` on the machine the study ran on and are gitignored.

| script | what it measures |
|---|---|
| `study_plate.py`, `eval_plates.py` | every candidate plate over all frames, the lane occupancy, frame 65 against each |
| `static_plate_workers.py`, `regress_first_video2.py`, `proposed_pipeline.py` | the long-still plate, measured and rejected: it fails on a held chord and on an end screen |
| `still_median.py` | the plate the study proposes: the median of what stands still, on both videos, with the score |
| `still_pairs.py` | a still-roll pair told from the raw frames alone |
| `lit_keys2.py`, `score_notes.py`, `score_first.py` | the keyboard's own strikes, and a reading scored against them |
| `study_vote.py`, `study_profiles.py`, `study_blocks.py` | the scroll speed: voted by the rectangles, and three correlation profiles |
| `study_bounds.py` | the roll bounds on raw grey and on the plate difference |
| `extent_core.py`, `local_valleys.py`, `test_valleys.py`, `sweep_prominence.py` | the extent against the core; the valley against a local plateau; the threshold sweep |
| `seams.py`, `seams_first.py` | where the split rule cuts, in frame rows |
| `flatfield.py` | a per-pixel gain, measured and rejected |
| `rebuild.py`, `rebuild2.py`, `draw_notes.py`, `perframe_final.py` | a reading with a given plate and rules, drawn back on a frame; the per-frame reading |
