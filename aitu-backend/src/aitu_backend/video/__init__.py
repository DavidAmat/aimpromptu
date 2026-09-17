"""Reading a Synthesia video, or one screenshot of one, into notes.

The plan is `context/implementations/04-synthesia-to-notes/04-plan.md` and the
frozen decisions are `04-decisions.md`. Nothing in here knows about `events.json`:
this package finds falling rectangles and says which keys are onset and which are
sustained. Turning that into the piece is Phase 4, through the writer that
already exists (V-02).

| Module | What it owns |
|--------|--------------|
| `geometry.py` | the piano overlay: two rectangles become every key and its lane |
| `images.py` | the one resolution every picture is read at |
| `plate.py` | the background plate, and how far a pixel is from it |
| `detector.py` | one picture and one calibration in, onsets and sustains out |
| `momentum.py` | a rectangle falls; anything that does not fall is not a note |
| `colour.py` | the optional second opinion on whether a run is a note |
| `examples.py` | the example screenshots, their calibrations and annotations |
| `scoring.py` | the score board that says whether a change helped |
| `finder.py` | the one rectangle in, every key inside it out (V-37) |
| `download.py` | one URL in, a video and the audio of it beside it (V-03) |
| `sampling.py` | ffmpeg into `video/frames/` at the sampling granularity |
| `store.py` | everything under `data/audio/<uuid>/video/`, read and written |
| `motion.py` | the scroll speed and the two edges of the roll, from motion |
| `reading.py` | the detector over every sampled frame, into `frames.jsonl` |
"""
