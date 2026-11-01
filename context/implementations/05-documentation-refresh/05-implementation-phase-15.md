# 05, Phase 15: From the audio to the notes: Source, Audio, the transcription (report)

Written 2026-11-01. Wave B. The plan is [`05-plan.md`](05-plan.md), the phase is section 6, Phase 15.

## Docs changed

- `context/backend/pieces-and-revisions.md`: the `audioRevision` row lists what raises it now (cuts, a file added,
  moved or removed, a passage pasted in or taken out). It was "cuts, or a file is added".
- `context/backend/muscriptor.md`: the code list names `pmn/muscriptor.py`; a link to the Audio step's section.
- `context/music/transcription-quality.md`: the engine is MuScriptor since implementation 08; the filters of layers 2
  and 3 are off on a MuScriptor piece (`pipeline.filters_for`); the Piano Roll it named is gone (the Notes step's
  roll is `PianoRollCanvas`); a dashed note is a guessed hand, not a filtered note (the old claim was wrong).
- `documentation/services/backend/transcription-pipeline.md`: the MIDI piano's notes (`engine` `midi`) get no filters,
  in the order diagram, the filter table and §4; the range-edit preview paragraph removed (`editing/preview.py` was
  deleted in implementation 02, Phase 9).
- `context/frontend/projects.md` (Source and Audio, section 4): the stale-notes text of the Source step, the rules of
  **Remove**, the Audio tools (**Only keep the selected part**, **Discard the changes**), the labels of the primary
  action (from `AudioTab.tsx`), **Read notes again** on the Video step.
- Not changed, checked and right: `context/backend/muscriptor.md` settings and live stream (the constants of `lag.py`
  and `live.py`), the routes of `api/pieces.py`, `api/youtube.py`, `api/audio.py`, `documentation/services/frontend/components.md`
  section 2.2.

## What was stale

- The quality page said layers 1 to 3 ran as they did for ByteDance, and named a Piano Roll that no longer exists.
- The pipeline page said the range-edit preview applied the filters; the file is gone.
- The Audio tab's new tool (**Only keep the selected part**) and its Transcribe labels were not in `projects.md`.
- The Source step's stale-notes sentence was not the one on screen.

## Code and docs that disagree (for the user)

- `aitu-backend/src/aitu_backend/audio/frames.py` (module docstring): says the cuts are stored in `metadata.json`.
  They are the gaps of `timeline.json` (`audio/store.py`).
- `aitu-backend/src/aitu_backend/audio/piece_audio.py` (module docstring): says `piece-r<N>.flac` is written beside the
  original. The code writes it into `cache/<partId>/` (`storage/paths.py`, and `pieces-and-revisions.md` is right).
- `pipeline.filters_for` turns the filters off for `midi`. `GET /matrix/{uuid}/events` may still label artifacts on a
  MIDI piece: not read (see Not checked).
- `context/frontend/projects.md` is 286 lines, over the limit of about 200. Section 4 (the Sheet step) is most of it;
  Phase 4 makes that part a summary.

## New terms for the glossary (Phase 20)

- **the axis**: the files of the Audio step laid end to end (the timeline of a part; `audio/timeline.py`).
- **the piece**: the kept frames joined; the notes are in its time (`audio/frames.py`). Check whether the glossary has it.
- **Only keep the selected part**: the Audio tool that cuts everything outside the selection at once.
- **edited audio** (`piece-r<N>.flac`): the joined audio of a part with cuts, written for its revision.
- **listen copy** (`listen-<name>.flac`): a lossless copy played for a compressed file with no cuts.

## Not checked

- No run of the app (plan section 5). The frontend was read in its code only: `SourceFiles.tsx` drag and drop, the
  waveform painters, `WaveformRangeSelector` and `useCutPlayer` were not read in full.
- `audio/youtube.py` download and `audio/sources.py` `ensure_listen`: read from their docstrings only.
- `GET /matrix/{uuid}/events` on a MIDI piece: whether it still labels artifacts. Not read.
- The `missing` count of `transcription-pipeline.md` is 8 in the inventory and stays at 8: all are deliberate
  history (the deleted `matrix/granularity.py`, `isochrony.py`, `tempo_map.py`, `bands.py`, `to_score_payload`,
  `tests/test_migration.py`), or a value (`electric_bass`). `check-names.py` lists them; they are not errors.
- `check-links.py`: 3 broken links, all in other phases' files (`05-checklist.md` line 85, Phase 3's and Phase 6's
  reports). None in mine.

## Pending edits for shared files

- **E15.1** `documentation/services/backend/endpoints.md`, the YouTube table (heading "YouTube", row `POST /youtube/download`):
  replace the text "Download the audio as mp3, in the request." with "Download the audio as mp3, in the request. Answers
  `201` and the stored audio's metadata."

No other shared file needs an edit: `components.md` section 2.2 is accurate for these files (checked).

## Left for later phases

- Phase 16: `projects.md` section "3. Notes" still says "Until Sonnet decides them, the notes have no hand colours"
  (the Notes part is Phase 16's).
- Phase 4: `projects.md` section "4. Sheet" (the Sheet step's summary) names Sonnet in several places; Phase 4 owns it.
- Phase 20: the glossary terms above; the `Missing` count of the inventory row for `transcription-pipeline.md`.
