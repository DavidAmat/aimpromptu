# Task 6.2.1 — Transcription settings and launch · progress report

Status: **done and browser-verified.** Date: 2026-07-27. This closes Epic 6.

## Summary

The Input tab now treats a selected passage as a real audio artifact, not an ephemeral pair of
numbers:

- a partial waveform selection must be named and saved before Run is enabled;
- the backend physically trims the normalized audio into a new audio-store item;
- segment metadata keeps the root source uuid and absolute source start/end time;
- a segment exposes only its own waveform and playback duration;
- **Back to original** restores the root audio so another passage or the entire track can be used;
- Run always starts a fresh transcription of the selected physical file and then opens Matrix.

Re-trimming an existing segment keeps absolute lineage to the root source rather than stacking
relative offsets. Whole-file “segments” are rejected.

## Progress correction

The ByteDance adapter now exposes its actual overlapping model-segment loop. It publishes
`model segment N/total` after every inference batch while preserving the package's original
deframing and note-event post-processing. The UI maps download, model transcription and all later
pipeline stages onto one monotonic 0–100% bar, so the bar no longer resets or remains at zero while
the backend is working.

## Errors found and solutions

- The former range lived only in browser state, so returning to Input and running the full source
  could navigate back to a stale segment result. Persisted segment audio plus forced fresh Run
  removes that ambiguity.
- Pipeline stages reported their own local fractions, making the browser bar jump backward.
  `useProgress` now applies stage bands and rejects backward motion.
- ByteDance previously emitted only one completion tick after all inference. Its real mini-batch
  loop is now instrumented, so longer audio advances segment by segment.

## Agreed deviation from the original task

The original task passed a transient time range into transcription. The supervisor requested the
stronger artifact model implemented here: physically trim first, retain source lineage, and make
the segment the only audio used by its matrix and Playground views.

## Verification

Automated coverage includes physical file duration and waveform checks, segment metadata,
nested-segment absolute lineage, invalid whole-range rejection, and monotonic model-segment
progress. A real ByteDance run completed successfully on the local Mac.

Browser verification used an eight-second source and a saved 2–5 second segment:

- Input showed only the three-second waveform and the root 2–5 second range;
- Matrix showed **SEGMENT**, local time and original-source time;
- **Back to original** followed by Run produced **ENTIRE TRACK** and 32 frames instead of reopening
  the former 12-frame segment;
- no browser warnings or errors were logged.

## Manual trial

Upload a known piece, choose and save a short named segment, and confirm its waveform shrinks to
the saved passage. Run it and confirm Matrix identifies the source range. Return to Input, click
**Back to original**, run again, and confirm Matrix identifies the entire track. Use a source over
ten seconds to see multiple `model segment N/total` progress updates.
