# documentation/issues

Troubleshooting runbooks and incident notes, one per problem, each written from a real case.

| Runbook | The symptom it diagnoses | State |
|---|---|---|
| [piano-matrix-sustains-and-phantom-onsets.md](piano-matrix-sustains-and-phantom-onsets.md) | A held chord prints short, or a chord has a note too many | **Live** |
| [hand-split-ledger-lines.md](hand-split-ledger-lines.md) | A hand is printed far outside its own staff, under a pile of ledger lines | **Live** |
| [rhythm-figures-and-tempo.md](rhythm-figures-and-tempo.md) | An evenly played passage prints as a mix of corcheas and semicorcheas | **Retired 2026-08-10** |

## Why one is retired rather than deleted

`rhythm-figures-and-tempo.md` diagnosed a class of bug that **cannot happen any more**. Playing was
fitted to a grid of note figures built from a BPM, and no human plays on a grid; that grid was
deleted on 2026-08-08. A column is now a slice of real time and a figure is a label the reader
chooses, so there is nothing left to round against and no BPM to be wrong about.

It is kept because it is the clearest surviving statement of *why* the wall-clock model exists, with
the arithmetic worked through on a real file. Its banner says all of this; read the banner first.

## A note on column numbers in these runbooks

The two live runbooks were written in 2026-08 and their worked examples quote **semicorchea
columns** from the old model. Those numbers do not correspond to 40 ms columns. The passages
themselves, in seconds, are still the right cases — work the column range out from the seconds and
the `frameMs` you are reading at.

## Where to look deeper

- [`../services/backend/transcription-pipeline.md`](../services/backend/transcription-pipeline.md)
  — every filter and the measurement behind each threshold
- [`../services/backend/events-to-sheet.md`](../services/backend/events-to-sheet.md)
  — the order the filters run in, and why moving one re-breaks something
- [`../../context/music/transcription-quality.md`](../../context/music/transcription-quality.md)
  — which of the four layers a bad passage came from
