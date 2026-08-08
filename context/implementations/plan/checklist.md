# AImpromptu implementation checklist

Single status lookup for the whole plan. Status codes: `[x]` completed, `[p]` in progress, `[b]` blocked (state the blocker), `[c]` cancelled (state why), `[ ]` not started. Workers: mark `[p]` when starting, final status when finishing.

> **Epics 1–8, and Epic 9's Stories 9.1–9.6, were completed across the 2026-07-27 sessions** and are
> **awaiting the human supervisor's musical real-audio/manual trials**. The completed state is
> committed to `master`.
>
> - **Click-by-click verification guides**: [`../progress/user_review/`](../progress/user_review/README.md)
>   — start at `00-setup.md`. Guide 7 covers the new notation tab.
> - **What happened and what is still open**:
>   [`../progress/2026-07-27-overnight-session.md`](../progress/2026-07-27-overnight-session.md).
>
> No decisions are outstanding. The ligature-adjacency question was resolved on 2026-07-27 — the
> adjacency rule is binding; see Task 2.3.2.

# [x] Epic 1 — Skeleton

Structural foundation: backend module layout and tooling, frontend app shell with all sections/tabs, shared Pydantic/TS contracts, storage folder skeleton. Index: `epic-01-skeleton/epic-skeleton-index.md`.

## [x] Story 1.1 — Backend skeleton

- [x] Task 1.1.1 **Backend restructure**: module layout, migrate sequence.py, routers.
- [x] Task 1.1.2 **Backend tooling**: pre-commit (black, flake8, mypy), tqdm/progress convention, Makefile targets.

## [x] Story 1.2 — Frontend skeleton

- [x] Task 1.2.1 **App shell and navigation**: routing for all sections/tabs, typed API client, SSE progress hook.
- [x] Task 1.2.2 **UI kit and theme**: MUI standard, palette.ts with semantic color uses. *(Theme **reversed to light and pinned** on 2026-07-27 — on the original dark ground a struck matrix note (`grays.ink`) was invisible against a `grays.ink` background. New `surface` tokens stop a view assuming a ground again. See [`task-1.2.2-followup-light-mode.md`](../progress/epic-01/task-1.2.2-followup-light-mode.md).)*

## [x] Story 1.3 — Shared contracts

- [x] Task 1.3.1 **Matrix schemas**: sparse-COO piano matrix + envelope metadata, TS mirror, converters.
- [x] Task 1.3.2 **Metadata schemas**: slugs, granularity/version codes, metadata.json family.

## [x] Story 1.4 — Storage skeleton

- [x] Task 1.4.1 **Storage layout**: data/ tree, npz format decision, path helpers, gitignore policy.

# [x] Epic 2 — Matrix core

The pure-Python piano matrix engine: model, transition validation, granularity collapse/upsample, cleaning, duration approximation, hand split and structural operations. Index: `epic-02-matrix-core/epic-matrix-core-index.md`.

## [x] Story 2.1 — Model and validation

- [x] Task 2.1.1 **Matrix model**: PianoMatrix class, timing math, key mapping, npz round-trip.
- [x] Task 2.1.2 **Transition validator**: 0/1/-1 Markov rules, strict and normalize modes.

## [x] Story 2.2 — Granularity

- [x] Task 2.2.1 **Collapse and upsample**: pair-merge rules one hierarchy step at a time, chained collapse, upsample rules, vectorized.

## [x] Story 2.3 — Cleaning and approximation

- [x] Task 2.3.1 **Sustain cleaning**: Appendix B — sustains cut by foreign onsets.
- [x] Task 2.3.2 **Duration approximation**: Appendix C — closest writable duration, singles and dotted notes only. *(Adjacency contradiction **resolved 2026-07-27**: the rule is binding, non-adjacent ties are never generated, and 1.23 s → a plain negra. See [`task-2.3.2-followup-adjacency-rule.md`](../progress/epic-02/task-2.3.2-followup-adjacency-rule.md); the task file was updated with the supervisor's agreement.)*

## [x] Story 2.4 — Hands and operations

- [x] Task 2.4.1 **Two-hands split**: equal shapes, lossless recombination. *(The C4 threshold was **replaced on 2026-07-28** by the beam dynamic program from [`research-01-hand-inference`](research-01-hand-inference/02-system-prompt-hand-inference-poc.md), ported into `aitu_backend/hands/`. The rule remains as `split_hands_at_row` / `method="threshold"`. See [`task-2.4.1-followup-hand-inference.md`](../progress/epic-02/task-2.4.1-followup-hand-inference.md).)*
- [x] Task 2.4.2 **Matrix operations**: transposition, tempo insertion, slice/replace, validated cell edits. *(Also adds `tests/test_matrix_pipeline.py`, the epic's end-to-end exit criteria.)*

# [x] Epic 3 — Audio I/O

Audio ingestion and management: uuid audio store, uploads with ffmpeg normalization and waveform
peaks, browser recording with live bars, Audacity-like range selector, physically persisted audio
segments with root-source lineage, YouTube downloads. Index:
`epic-03-audio-io/epic-audio-io-index.md`.

## [x] Story 3.1 — Audio store

- [x] Task 3.1.1 **Audio store**: uuid folders, metadata.json, library CRUD endpoints, physical
  segment children with absolute root-source lineage.

## [x] Story 3.2 — Upload and formats

- [x] Task 3.2.1 **Upload endpoint**: suffix detection, ffmpeg normalization, waveform peaks endpoint.

## [x] Story 3.3 — Recording

- [x] Task 3.3.1 **Browser recording**: MediaRecorder, live bar waveform, name-and-save flow. *(Chrome question resolved: `.webm`/`.ogg` are now accepted and converted by ffmpeg server-side — the standard approach. Verified end to end. Awaiting your manual trial.)*

## [x] Story 3.4 — Range selection

- [x] Task 3.4.1 **Waveform range selector**: draggable handles, `mm:ss.cc` inputs, range playback
  with cursor, and read-only rendering for a persisted truncated segment. *(Browser-verified.)*

## [x] Story 3.5 — YouTube

- [x] Task 3.5.1 **YouTube download**: yt-dlp to mp3, alias metadata, tab UI; batch queue nice-to-have. *(Now invoked as `python -m yt_dlp` so it never depends on PATH; yt-dlp installs and runs in the sandbox. A real download still needs your trial.)*

# [x] Epic 4 — Transcription

Audio to matrix: piano transcription engine behind a swappable interface, note events to raw fusa matrix, and the orchestrated raw→collapsed→clean→two-hands pipeline with fast recompute and progress streaming. Index: `epic-04-transcription/epic-transcription-index.md`.

> The real ByteDance engine completed an end-to-end local Mac run. Its actual mini-batch inference
> loop now reports model-segment progress to the browser. A real piano performance is still the
> useful quality trial; follow
> [`user_review/epic-04-transcription.md`](../progress/user_review/epic-04-transcription.md).

## [x] Story 4.1 — Engine

- [x] Task 4.1.1 **Engine integration**: piano_transcription_inference default, Basic Pitch
  fallback, benchmark script. *(Real ByteDance call verified locally. Engines are an optional
  extra: `uv sync --extra transcription`. Python 3.12 is supported on Apple Silicon.)*

## [x] Story 4.2 — Events to matrix

- [x] Task 4.2.1 **Events to raw matrix**: grid construction, snapping, validation, raw artifact.

## [x] Story 4.3 — Pipeline

- [x] Task 4.3.1 **Pipeline orchestration**: five steps, persisted artifacts, sub-second recompute
  from raw, real ByteDance batch progress, monotonic SSE progress.

# [x] Epic 5 — Artifacts and versioning

Persistence of musical work: playground repository with vN_gX version folders and track history, promotion to library with named versions and rollback. Index: `epic-05-artifacts/epic-artifacts-index.md`.

## [x] Story 5.1 — Playground repository

- [x] Task 5.1.1 **Artifact repository**: save/load/list versions, comments, parent lineage, endpoints.

## [x] Story 5.2 — Promotion

- [x] Task 5.2.1 **Library promotion**: dialog with editable promotion names, replace-vs-additional, history and rollback. *(Backend + endpoints complete; the dialog itself belongs to Epic 7's promote button.)*

# [x] Epic 6 — Playground Input tab

Entry door of the Playground: five input sources (upload, record, library, text notation, JSON) plus BPM/granularity/range settings and pipeline launch. Index: `epic-06-playground-input/epic-playground-input-index.md`.

> Browser-verified with both a saved physical segment and its original full track. A musical
> real-audio quality trial remains.

## [x] Story 6.1 — Input sources

- [x] Task 6.1.1 **Input sources UI**: five source modes producing a working artifact. *(Text notation and matrix JSON populate the working artifact but do not persist yet — that needs Epic 7's save button.)*

## [x] Story 6.2 — Transcription settings

- [x] Task 6.2.1 **Transcription settings**: physically saved/named audio segments with source
  lineage, BPM, granularity, truthful model progress, fresh run + handoff to Matrix tab.

# [x] Epic 7 — Matrix tab

Spreadsheet-like matrix view: circles and edges grid with frozen headers, processing-step pills, JSON export/import, instant in-situ BPM/granularity recompute, frame search; editing and matrix player as nice-to-haves. Index: `epic-07-matrix-view/epic-matrix-view-index.md`.

> Complete and browser-verified with an imported five-note scale. The real-audio trial remains in
> [guide 5](../progress/user_review/epic-07-matrix-tab.md).

## [x] Story 7.1 — Grid

- [x] Task 7.1.1 **Matrix grid**: key columns EN+ES, frame rows with local/original timestamps for
  segments, onset/sustain circles, connector edges, frozen header. *(Row virtualization added — a
  five-minute piece is ~100k DOM nodes without it.)*

## [x] Story 7.2 — Steps and export

- [x] Task 7.2.1 **Step pills**: raw/collapsed/clean/two-hands switching, hand colors.
- [x] Task 7.2.2 **JSON export/import**: dense and sparse formats with metadata, session-portable round-trip. *(Export is a `GET` download; import normalizes and reports how many cells it corrected.)*

## [x] Story 7.3 — Recompute and search

- [x] Task 7.3.1 **In-situ recompute**: BPM/granularity change recomputed from raw, auto-redisplay.
- [x] Task 7.3.2 **Frame search**: jump by frame number or timestamp, deep link from Piano Roll. *(`MatrixGrid` takes a `focusFrame` prop — Epic 8's deep link sets the same one.)*

## [x] Story 7.4 — Editing and player (nice to have)

- [x] Task 7.4.1 **Cell editing**: palette placement, shift multi-select delete, validator-backed save.
- [x] Task 7.4.2 **Matrix player**: row cursor playback with piano tones and damped sustains.

# [x] Epic 8 — Piano roll and notes falling

Animated matrix views over the piano SVG: assets and key highlighting, horizontal roll view, shared playback engine (original audio vs synthesized piano), Synthesia-style falling view, drag editing nice-to-have. Index: `epic-08-piano-roll/epic-piano-roll-index.md`.

> Complete and browser-verified with an imported five-note scale: playback, key highlighting,
> drag staging and the Matrix deep link. Original-audio A/B and replacement illustrator assets
> still need the supervisor's manual trial ([guide 6](../progress/user_review/epic-08-piano-views.md)).

## [x] Story 8.1 — SVG assets

- [x] Task 8.1.1 **Piano SVG assets**: white-key base + normal black-key layer + pressed overlays,
  coordinate table, Piano component in both orientations. *(Programmatic placeholders per plan;
  replace the four SVG files when illustrator assets arrive.)*

## [x] Story 8.2 — Roll view

- [x] Task 8.2.1 **Roll view layout**: vertical piano left, note rectangles, dashed numbered guides, full-height fit, waveform watermark.

## [x] Story 8.3 — Player

- [x] Task 8.3.1 **Playback engine**: transport, key highlighting, original vs synthesized-piano sources, speed/BPM/granularity/range filters. *(Uses the specified WebAudio fallback rather than checked-in samples.)*

## [x] Story 8.4 — Falling view

- [x] Task 8.4.1 **Notes falling**: calibrated falling rectangles, velocity from window+BPM+granularity, swallow effect at Y=0. *(Note labels and borders reworked on 2026-07-27 at the supervisor's request — a fixed 10 px note name used to spill out of short rectangles. A green struck-key colour was tried the same day and reverted; the keyboard has one highlight colour. See [`task-8.4.1-followup-note-labels.md`](../progress/epic-08/task-8.4.1-followup-note-labels.md).)*

## [x] Story 8.5 — Drag editing (nice to have)

- [x] Task 8.5.1 **Drag note editing**: drag to key/frame with landing guides, staged changes, Save.

# [p] Epic 9 — Music notation

VexFlow sheet music: backend score-format builder, notation tab with responsive wrapping, engraving rules (stems/beams/no ties), key signatures and naturals, transposition, octave/clef displacement, beat guides and cut-measure, advanced ornaments at the end. Index: `epic-09-notation/epic-notation-index.md`.

> **Stories 9.1–9.6 completed 2026-07-27** and awaiting the supervisor's musical trial —
> [guide 7](../progress/user_review/epic-09-notation.md). Story 9.7 (nice-to-have ornaments) was
> not started, per the plan's "end of project" placement, so the epic header stays `[p]`.
>
> The score intentionally uses one readable voice per hand. Simultaneous onsets share the longest
> onset-to-next-onset chord duration; partial chord releases never create separate voices, rests or
> ties. Cross-barline gaps become leading rests in the following measure. See
> [`../progress/epic-09/task-9.3.1-followup-rest-and-chord-duration.md`](../progress/epic-09/task-9.3.1-followup-rest-and-chord-duration.md).

## [x] Story 9.1 — Score format

- [x] Task 9.1.1 **VexFlow score format**: backend digest to measures/voices/onset-led durations +
  annotation overlay, pre-generated per version. *(`notation/score_builder.py` + `spelling.py` +
  `durations.py` + `artifacts.py`; golden-file tests in `tests/golden/notation/`. Visible rests are
  limited to leading entrances and an unwritable measure tail.)*

## [x] Story 9.2 — Notation tab

- [x] Task 9.2.1 **Notation tab UI**: artifact picker, grand staff / single-hand, responsive wrap, save annotations, promote button. *(The VexFlow drawing is a plain function, `renderScore.ts`, so `npm run check:render` draws every golden document headlessly. The old `PianoSheet.tsx` is kept for the text-notation MVP pages.)*

## [x] Story 9.3 — Engraving

- [x] Task 9.3.1 **Stems, beams and no-tie policy**: stem direction rules, beam runs with arpeggio
  break, rests forbidden between sounding events, chord members unified to one duration, and no
  ties. *(An unwritable interior residue is an invisible timing spacer; an unwritable trailing
  residue may be a visible rest. Across a barline, the following measure may start with a rest.)*

## [x] Story 9.4 — Keys and transposition

- [x] Task 9.4.1 **Key signatures**: initial key, passage key changes, per-measure minimal-accidental suggestion, naturals preference. *(Spelling is a scored search, so "naturals over doubles" and E mayor keeping its A# both fall out of one table. Suggestions are surfaced per measure and never auto-applied.)*
- [x] Task 9.4.2 **Transposition**: semitone shift with short-range render preview. *(Accept shifts the **raw** matrix, so every granularity and every other tab follows; `POST /matrix/{uuid}/transpose?persist=true`.)*

## [x] Story 9.5 — Octaves and clefs

- [x] Task 9.5.1 **Octave displacement**: per-hand 8va/8vb/15ma/15mb thresholds, left-hand treble-clef switch. *(Thresholds are note names stored with the version; brackets group per passage and the printed pitch moves with them. The left-hand treble switch is barline-aligned and, with today's C4 hand split, only reachable by lowering its threshold.)*

## [x] Story 9.6 — Tempo guides

- [x] Task 9.6.1 **Beat guides and cut-measure**: dashed beat lines with frame numbers;
  cut-measure via timeline-column insertion. *(The preceding note/chord expands to the old
  barline when possible; the following note begins the new measure.)*

## [ ] Story 9.7 — Advanced ornaments (nice to have)

- [ ] Task 9.7.1 **Tuplets**: manual render-only tuplet grouping over a passage.
- [ ] Task 9.7.2 **Trills and chord grouping**: "tr" detection from raw events, near-simultaneous notes as chords.

# [ ] Epic 10 — Piano Library

Performer-facing section: browse/tag/filter consolidated and playground tracks, clean read-only performance view with overlay toggles, Spotify-like playlists with seamless next-piece flow. Index: `epic-10-library/epic-library-index.md`.

## [ ] Story 10.1 — Browsing

- [ ] Task 10.1.1 **Library browse**: tracks list, tags/filters/search, playground library management.

## [ ] Story 10.2 — Performance view

- [ ] Task 10.2.1 **Performance view**: read-only score page, overlay toggles, scroll/zoom UX.

## [ ] Story 10.3 — Playlists

- [ ] Task 10.3.1 **Playlists**: CRUD, ordering, version-by-name selection, playing mode with Next.

# [ ] Epic 11 — Range editing

Preview-first passage replacement: staged edit sessions with exact column enforcement, slow re-recording with metronome and trimming, transcribe-then-scale preview with accept/reject loop. Index: `epic-11-editing/epic-editing-index.md`.

## [ ] Story 11.1 — Staged sessions

- [ ] Task 11.1.1 **Staged edit session**: session model and folder, range selection, accept/cancel semantics.

## [ ] Story 11.2 — Slow recording

- [ ] Task 11.2.1 **Slow record flow**: slowdown factors, metronome and beat display, trimming, capture granularity.

## [ ] Story 11.3 — Preview and accept

- [ ] Task 11.3.1 **Replacement preview**: transcribe then scale timings, passage-only render, optional tempo-compressed audio, decision loop.

# [ ] Epic 12 — Annotations (nice to have)

Metadata overlays that never touch the matrix: lyrics over frame ranges, finger numbers with chord stacks, cue-size passages and grace notes; all responsive-wrap safe and toggleable. Index: `epic-12-annotations/epic-annotations-index.md`.

## [ ] Story 12.1 — Lyrics

- [ ] Task 12.1.1 **Lyrics annotations**: range-based authoring with passage-render iteration, stored per version.

## [ ] Story 12.2 — Fingering and small notes

- [ ] Task 12.2.1 **Finger numbers**: per-note 1–5, chord stacking, tunable text size.
- [ ] Task 12.2.2 **Small notes**: cue-size passages, acciaccatura/appoggiatura marks.

# [ ] Epic 13 — Composing live (nice to have)

Passage-by-passage composition: empty piece, stage-mode record/iterate, insert/append/overwrite placement, per-passage BPM conversion. Index: `epic-13-compose-live/epic-compose-live-index.md`.

## [ ] Story 13.1 — Live composition

- [ ] Task 13.1.1 **Compose live**: empty piece, passage stage, insertion modes, slow-recorded passage conversion.

# [ ] Epic 14 — Final documentation

Always last: bring `documentation/` up to the final codebase, refresh `context/` overviews and index, close the progress journal. Index: `epic-14-docs/epic-docs-index.md`.

## [ ] Story 14.1 — Documentation pass

- [ ] Task 14.1.1 **Final documentation**: detail tree rewrite, context refresh, journal retrospective.
