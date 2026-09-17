# poc-piano-overlay

Phase 1 of implementation 05, the piano overlay found from the black keys:
[`../context/implementations/05-piano-overlay-from-black-keys/05-plan.md`](../context/implementations/05-piano-overlay-from-black-keys/05-plan.md).
Nothing here ships. Phase 3 ports `blackkeys.py` and the route A half of `routes.py` into
`aitu_backend/video/finder.py`; the line reader stays here as the tool the truth was read with.

The numbers are in [`RESULTS.md`](RESULTS.md). The pictures it reads are the 24 example
screenshots of 04, at 1280 px wide.

```bash
cd aitu-backend
uv run python ../poc-piano-overlay/scripts/run_blackkeys.py   # the black keys, out/blackkeys*.png
uv run python ../poc-piano-overlay/scripts/run_lines.py       # the thin dark lines, out/lines/, data/truth-draft.json
uv run python ../poc-piano-overlay/scripts/truth.py           # the truth, out/truth/, data/truth.json, the families
uv run python ../poc-piano-overlay/scripts/fall.py            # do the rectangles fall vertically
uv run python ../poc-piano-overlay/scripts/routes.py          # route A against route B, data/routes.json
```

| File | What it is |
|---|---|
| `scripts/common.py` | the pictures at 1280 px wide, the one rectangle per picture, the rectifier |
| `scripts/blackkeys.py` | the black key finder: the band, the candidates, the alignment against the pattern, the extrapolation through a hand and the check against the pixels |
| `scripts/lines.py` | the thin dark lines between two white keys, read on two rows in the front of the keys, and the borders visible at the top edge |
| `scripts/truth.py` | the three checks that make a line a truth border, the review sheets, the family table and the perspective table |
| `scripts/routes.py` | route A, route B, and the score of each against the truth |
| `scripts/fall.py` | the lean of the rectangles against the lean of the keys |
| `data/rects.json` | the one rectangle of every picture |
| `data/truth.json` | 901 white key borders, checked by eye; `data/eye-rejections.json` names the six the eye took out |
| `data/families.json`, `data/routes.json` | the family table and every border both routes produced |
| `out/` | every picture the eye checked, and the logs the tables were copied from |
