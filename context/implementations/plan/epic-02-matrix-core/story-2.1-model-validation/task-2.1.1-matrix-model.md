# Task 2.1.1 — Matrix model

`matrix/model.py`: the PianoMatrix class every other module manipulates.

## Subtask 2.1.1.1 — Core class

- Backed by `scipy.sparse` COO (int8 values 1 and -1; 0 implicit). 88 rows (`La-0` … `Do-8`), N columns (time frames).
- Attributes: `granularity`, `tempo_bpm`, `time_step_seconds` (derived: `beats_per_column * 60 / bpm`), `processing_step`.
- Methods: `to_dense()`, `from_dense()`, `to_coo_payload()` / `from_coo_payload()` (wire format of Task 1.3.1), `save_npz()` / `load_npz()`.

## Subtask 2.1.1.2 — Timing math

Helpers translating between frames, seconds and note figures (the tables in `01-matrix-notation-logic.md`): `frame_to_time(f)`, `time_to_frame(t)`, `beats_per_column(granularity)`. Beat = negra. Granularity hierarchy constant:

```python
HIERARCHY = ["redonda", "blanca", "negra", "corchea", "semicorchea", "fusa", "semifusa"]
```

## Subtask 2.1.1.3 — Row/key mapping

Canonical 88-key order with EN (`C4`) and ES (`Do-4`) names, shared with the text-notation parser. One module owns it (`matrix/keys.py`).

## Acceptance

Property tests: dense<->sparse<->npz round-trips; timing helpers match the worked examples in the notation-logic doc (60 BPM, 0.5 s column = corchea, etc.).
