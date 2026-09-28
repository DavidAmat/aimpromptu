# Results: MuScriptor on the RTX 4090

Measured on 2026-09-28 on `david-ubuntu` (RTX 4090, driver 595.58.03, torch 2.13.0+cu130),
MuScriptor 0.3.0 at commit `7f213af`. Every run is conditioned on `acoustic_piano` unless it
says "free". "x real" is seconds of audio per second of processing.

# 1. Recommendation

| Choice | Value | Why |
|---|---|---|
| Model size | `large` | `medium` and `small` agree with `large` on only 84 to 86% of the notes (section 3) |
| dtype | **float16** | Exactly the same notes as float32 (agreement 1.000), 2.2 times faster, half the memory (3.5 GB) |
| Batch | **1, with prelude forcing** | Batching is 4 to 7 times faster but about 7% of the notes change and notes are cut at the 5 s borders. Chosen by the user (Q-7) |
| `torch.compile` | no | Slower (5.7 against 7.8 x real) and 70 to 110 s of warm-up |
| Conditioning | `acoustic_piano` (Q-3 unchanged) | Agrees more with ByteDance on 5 of 6 pieces; the free mode invents bass and drums in a solo piano |
| Lag | **one number per piece, measured on the audio** | The lag moves by 40 ms between pieces (section 5); a fixed number is wrong for some songs |
| `artifacts.py` | off for MuScriptor | It never fires (0 to 4 notes dropped per song, against up to 139 for ByteDance) |
| `leakage.py` | off for MuScriptor | It cannot fire (no velocity), and without its velocity test it would merge real repeated notes |

With these choices a whole song takes **5.3 to 8.6 x real**: 25 s for Superestrella (189 s),
48 s for The Winner Takes It All (356 s). The first note arrives after 0.04 to 0.24 s, and a
chunk takes 0.67 s (median; 1.0 s at most) on Superestrella.

# 2. The output format (task 1.3.1)

`out/format/superestrella-20s-large-{cuda,cpu}.events.jsonl` holds every event of the first
20 s, as it arrived, with its wall-clock second `t`.

- Three event types. `NoteStartEvent(pitch, start_time, index, instrument)`,
  `NoteEndEvent(end_time, start_event_index)` and `ProgressEvent(completed, total)`: one with
  `completed = 0` first, then one per chunk.
- **Times are exact multiples of 10 ms** (every `start_time` and `end_time` of every run).
- **Events stream token by token**, not chunk by chunk: the median wall-clock gap between two
  events is 22 ms. The notes of chunk N all arrive before any note of chunk N+1.
- The end of a note can arrive much later than its start (up to 1.4 s of wall clock in 20 s),
  because a sustained note stays open across chunk borders. With prelude forcing, no note of
  the whole song ends exactly on a chunk border: long notes cross them.
- **There is no velocity.** The velocity token has two values: 1 opens a note, 0 closes it. The
  model has no loudness to give (`tokenizer/notes.py`, `EventRange("velocity", 0, 1)`).
- CPU and GPU give the **same 102 notes** on those 20 s. The CPU is 10 times slower (0.45 x real).
- Note lengths follow the **key**, not the pedal: median 230 ms against 866 ms for ByteDance on
  the same song. The shortest notes are 110 ms (all 50 shortest), except one of 10 ms.

Example (the first events):

```json
{"t": 0.0004, "type": "ProgressEvent", "completed": 0, "total": 4}
{"t": 0.2672, "type": "NoteStartEvent", "pitch": 30, "start_time": 0.86, "index": 0, "instrument": "acoustic_piano"}
{"t": 0.278, "type": "NoteStartEvent", "pitch": 42, "start_time": 0.86, "index": 1, "instrument": "acoustic_piano"}
{"t": 0.2888, "type": "NoteStartEvent", "pitch": 70, "start_time": 0.86, "index": 2, "instrument": "acoustic_piano"}
{"t": 0.3213, "type": "NoteEndEvent", "end_time": 1.08, "start_event_index": 2}
```

# 3. Speed and memory (task 1.3.2)

120 s of Superestrella (24 chunks), after a 10 s warm-up. "F1" is the agreement with the
reference `large-float32-b1-prelude` (same pitch, onset within 50 ms). It measures how far an
option moves from the reference, not whether it is correct. "Border" counts the notes that end
exactly on a 5 s chunk border. Full table: `out/speed/quality.json`.

| Configuration | x real | first chunk (s) | GPU peak (GB) | notes | F1 | border |
|---|---:|---:|---:|---:|---:|---:|
| large float32, b1, prelude (reference, MuScriptor's default) | 3.5 | 1.16 | 7.06 | 815 | 1.000 | 0 |
| **large float16, b1, prelude** | **7.8** | **0.53** | **3.52** | **815** | **1.000** | **0** |
| large bfloat16, b1, prelude | 7.7 | 0.54 | 3.54 | 816 | 0.979 | 0 |
| large float16, b1, no prelude | 7.7 | 0.53 | 3.52 | 801 | 0.932 | 40 |
| large float16, b4 | 21.6 | 0.80 | 5.81 | 801 | 0.932 | 40 |
| large float16, b8 | 34.1 | 1.08 | 8.89 | 801 | 0.932 | 40 |
| large float16, b24 | 53.4 | 2.25 | 21.04 | 801 | 0.932 | 40 |
| large float32, b24 | out of memory | | | | | |
| large float16, b1, prelude, `torch.compile` | 5.7 | 0.73 | 3.53 | 816 | 0.997 | 0 |
| large float16, b8, `torch.compile` | 6.9 | 5.28 | 8.95 | 801 | 0.932 | 40 |
| medium float16, b1, prelude | 17.3 | 0.29 | 0.91 | 870 | 0.846 | 2 |
| medium float16, b24 | 164.3 | 0.73 | 6.92 | 849 | 0.862 | 27 |
| small float16, b1, prelude | 29.0 | 0.17 | 0.36 | 767 | 0.842 | 1 |
| small float16, b24 | 381.9 | 0.31 | 3.11 | 767 | 0.843 | 27 |

Observations:

- float16 on CUDA is a free gain. MuScriptor's default on CUDA keeps float32 weights and uses
  float16 autocast, so the compute is already half precision; float16 weights halve the memory
  read per token, and decoding one token at a time is limited by that memory traffic.
- The memory of a batch is mostly the key and value cache, which MuScriptor allocates for
  `max_gen_len = 2000` tokens per chunk: 17.6 GB at b8 in float32.
- `torch.compile` with `dynamic=True` recompiles as the cache grows and never pays back.
- Without prelude forcing, the model guesses which notes continue from the previous chunk.
  It guesses wrong often enough to change 7% of the notes, and 40 notes end on a border in 2
  minutes. This is the price of batching.
- `medium` and `small` are fast, but they are a different transcription (F1 0.84 to 0.86), not
  a faster copy of `large`.

The prompt hoped for 20 x real. `large` reaches it only with batching (b4: 21.6, b8: 34.1).

# 4. Conditioning (task 1.3.4)

First 60 s of Superestrella, then the whole of six pieces (`04_full_song.py ... -free`).

- On 60 s, the free run names **every** note `acoustic_piano` (387 notes), and the
  conditioned run finds 347. Of the 49 free notes missing in the conditioned run, 26 are in
  one chunk (30 to 35 s: 35 notes conditioned, 58 free, 63 ByteDance), and 24 of the 40 listed
  are also in ByteDance. So conditioning **lost real notes in one chunk of twelve**. The same
  chunk is lost with batching, so prelude forcing is not the cause.
- On the whole songs, the conditioned run agrees more with ByteDance on 5 of 6 pieces
  (F1 0.650 / 0.946 / 0.937 / 0.901 / 0.906 / 0.832 conditioned, against 0.625 / 0.943 / 0.906 /
  0.878 / 0.897 / 0.838 free). On Superestrella the free run adds 70 `electric_bass` notes and
  70 `drums` hits to a solo piano recording.

Conditioning stays (Q-3). The lost chunk is a local weakness the user can repair in the editor.

# 5. The lag (task 1.3.3)

MuScriptor's own method (`onset_delay` against a beat grid) **could not run on any of the six
pieces**: `beat_this` found beats, but `detect_grid` rejected them as "no fixed tempo" (2.8 to
6.1 s RMS against a constant tempo). The app must not store a BPM anyway (rule 3).

Two other methods, on six pieces (`out/lag/`):

- **Envelope**: a spectral-flux onset envelope of `normalized.wav` at 2 ms. For each engine, the
  lag that puts its onsets on the highest mean envelope. ByteDance sits between -16 and -19 ms
  on every piece, which makes it a stable anchor. MuScriptor moves between -2 and -38 ms.
- **Pairs**: the median signed onset difference of the matched notes (same pitch, 50 ms).

| Piece | MuScriptor envelope (ms) | ByteDance envelope (ms) | Difference (ms) | Pairs median, Mus - Byt (ms) |
|---|---:|---:|---:|---:|
| Superestrella | -2 | -19 | +17 | +15.3 |
| La Tortura | -30 | -18 | -12 | -12.2 |
| 7 Years | -38 | -16 | -22 | -16.0 |
| Grace Kelly | -32 | -16 | -16 | -13.4 |
| Birds of a Feather | -36 | -16 | -20 | -16.8 |
| The Winner Takes It All | -10 | -17 | +7 | +7.6 |

The two methods agree within 6 ms on every piece. So the lag of MuScriptor against ByteDance is
**not constant**: from 17 ms late to 22 ms early. The recommendation is to measure it per piece
from the audio alone: `lagCorrectionMs = envelope lag of the MuScriptor onsets - (-17 ms)`, clipped
to +-40 ms (MuScriptor's own limit, `MAX_ONSET_DELAY_S`). It costs about one second of CPU and
needs neither a BPM nor a ByteDance run. It is still "a fixed lag correction in milliseconds" of
the plan's rule 3 check: one number per piece, a timing fix, not a tempo.

# 6. The whole song against ByteDance (task 1.3.5)

`out/compare/*.json` and `*.pianoroll.png` (same pitch range on both sides, 5 s chunk borders dotted).

| Piece | MuScriptor notes | ByteDance notes | Matched within 50 ms (share of MuScriptor / of ByteDance) | x real |
|---|---:|---:|---:|---:|
| Superestrella | 1,351 | 1,343 | 875 (65% / 65%) | 7.6 |
| La Tortura | 2,027 | 2,154 | 1,977 (98% / 92%) | 5.4 |
| 7 Years | 1,437 | 1,458 | 1,357 (94% / 93%) | 8.1 |
| Grace Kelly | 2,142 | 2,144 | 1,931 (90% / 90%) | 5.3 |
| Birds of a Feather | 1,456 | 1,449 | 1,316 (90% / 91%) | 8.2 |
| The Winner Takes It All | 2,553 | 2,692 | 2,182 (86% / 81%) | 7.5 |

Superestrella is the outlier. Its ByteDance transcription is also the noisiest (139 notes under
20 ms, and many long, thin notes between MIDI 90 and 102 that look like overtones); MuScriptor
draws a regular chord pattern with bass octaves instead. Only listening can say which is right;
the user already judged MuScriptor good on this song.

# 7. The filters (task 1.3.6)

`out/filters/`. On the six pieces:

- `artifacts.py` drops 0, 1, 4, 0, 0, 0 MuScriptor notes (ByteDance: 139, 2, 0, 4, 5, 8).
- `leakage.py` merges **0** MuScriptor notes on every piece. Every MuScriptor note has the
  default velocity 64, so its fourth condition (the phantom is at least 3 quieter) never passes.
- With that condition switched off it would merge 19 to 58 pairs per piece, **all with a gap of
  0 ms**. These are MuScriptor's normal repeated notes: a new onset of a key closes the open note
  of that key at the same instant (for example B4 at 8.40 s and 8.84 s in the melody of
  Superestrella). Merging them deletes notes the pianist played.

Both filters are therefore turned off for MuScriptor. They stay on for ByteDance.

# 8. For the live view (Phase 7)

- MuScriptor's server sends one Server-Sent Events message per note event, and subtracts the
  lag from the drawn notes only at the end, when it is known. Our plan does the same.
- Their piano roll reveals each rectangle over 280 ms with an ease-out curve, and follows the
  newest note with a smoothed "frontier" (`web/src/pianoroll.ts`). The progress bar keeps an
  average of the chunk time and never reaches the next chunk before it arrives
  (`web/src/progress.ts`).
- At 7.8 x real a chunk arrives every 0.67 s. With batching, 8 chunks arrive together every
  1.2 s, so the view jumps instead of flowing.
