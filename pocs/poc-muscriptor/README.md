# PoC: MuScriptor on the RTX 4090

**Status:** research spike for implementation 08, Phase 1
([`../../context/implementations/01-mvp/08-new-algorithm-notes-detection-muscriptor/08-plan.md`](../../context/implementations/01-mvp/08-new-algorithm-notes-detection-muscriptor/08-plan.md)).
Nothing here is wired into the app. It reads the stored audio of Superestrella and the
stored ByteDance `events.json`, and writes only under `out/`.

The results and the recommendation are in [`RESULTS.md`](RESULTS.md).

## What it answers

| Task | Question | Script |
|---|---|---|
| 1.3.1 | What does MuScriptor output, and in what order? | `01_output_format.py` |
| 1.3.2 | How fast is each size, dtype and batch option, and what does speed cost in notes? | `02_speed.py`, `13_speed_quality.py` |
| 1.3.3 | Is there a constant lag in the onset times? | `04_full_song.py`, `11_lag.py` |
| 1.3.4 | Does conditioning on `acoustic_piano` lose piano notes? | `03_conditioning.py` |
| 1.3.5 | How does the whole song compare with ByteDance? | `04_full_song.py`, `10_compare_bytedance.py` |
| 1.3.6 | Do `artifacts.py` and `leakage.py` help or harm? | `12_filters.py` |

## Two environments

The backend does not depend on MuScriptor yet (Phase 4 adds the extra), so:

- the **model** scripts `0*_*.py` run in MuScriptor's own environment, cloned beside
  this repository at `../muscriptor` (from the repository root: `../muscriptor`);
- the **analysis** scripts `1*_*.py` run in the backend environment, because they need
  `librosa`, `matplotlib` and the app's filters. They only read `out/`.

`scripts/common.py` imports neither package at module level, so both use it.

## Setup (once)

```bash
cd ~/Documents/projects/music
git clone https://github.com/muscriptor/muscriptor.git
cd muscriptor && uv sync
# the web UI of `muscriptor serve` (gitignored build)
cd web && npx -y pnpm@10.20.0 install --frozen-lockfile && npx -y pnpm@10.20.0 run build
```

The weights are gated: accept the licence on the Hugging Face page of each size, and
have `HF_TOKEN` in the environment. `common.py` sets `HF_HUB_CACHE=/mnt/ssd2/hf/data/hub`
so the 1 to 6 GB of weights go to the second disk.

## Run

```bash
cd ~/Documents/projects/music/muscriptor
P=../aimpromptu/pocs/poc-muscriptor/scripts
uv run python $P/01_output_format.py            # 20 s, large, GPU then CPU
uv run python $P/02_speed.py                    # every size x dtype x batch, 120 s
uv run python $P/02_speed.py --sizes large --dtypes float16 --compile
uv run python $P/03_conditioning.py             # 60 s, with and without conditioning
uv run python $P/04_full_song.py --config large-float32-b1-prelude

cd ~/Documents/projects/music/aimpromptu/aitu-backend
P=../pocs/poc-muscriptor/scripts
uv run python $P/10_compare_bytedance.py
uv run python $P/11_lag.py
uv run python $P/12_filters.py
uv run python $P/13_speed_quality.py
```

## Layout

- `scripts/`: the code above.
- `data/`: empty; the audio is read in place from `aitu-backend/data/audio/`.
- `out/format/`: the raw events of task 1.3.1, one JSON line per event, as they arrived.
- `out/speed/`: one row per configuration (`index.json`), the notes of each, and `quality.json`.
- `out/conditioning/`, `out/full/`, `out/compare/`, `out/lag/`, `out/filters/`: one folder per task.
