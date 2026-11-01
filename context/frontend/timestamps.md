# Timestamps and frame labels — UI rule

How every time value is printed in the UI. One rule, one implementation: the format lives in
`src/audio/time.ts`, the styling in `src/ui/timestamps.ts`. Nothing formats a time inline.

## The rule

| # | Rule | Why |
|---|------|-----|
| 1 | **`mm:ss.cc` — two decimals, never three** | Hundredths are finer than anyone reads off a grid, and every timestamp then has the same short width. |
| 2 | **A frame is labelled by its start only**: `f:12 · 00:00.25` | The frame's end *is* the next frame's start, one row below. Printing `[start – end]` doubled the label's width to say what the next row already says. |
| 3 | **A timestamp never wraps** | Wrapped times shred a table into ragged multi-line rows. Whatever holds a timestamp gives it room and sets `whiteSpace: "nowrap"`. Horizontal space is cheap; a wrapped label is not. |
| 4 | **Monospace + `tabular-nums`** | Without tabular figures the digits shift sideways as a counter ticks, which reads as flicker. |

Rule 2 is about *frames*. A genuine **range** — the transcription range, a selection — still prints
both ends, because there is no next row to infer the end from.

Parsing stays deliberately forgiving: `parseTime` accepts `3:03`, `183`, `183.5` and three-decimal
values pasted from other tools. Only **output** is pinned to two decimals.

## Helpers

| Export | From | Use |
|--------|------|-----|
| `formatTime(seconds)` | `src/audio/time.ts` | `83.4567` → `"01:23.46"`. Clamps negatives to zero; rounding carries into the next second and minute. |
| `formatFrameLabel(frame, startSeconds)` | `src/audio/time.ts` | `"f:12 · 00:00.25"` — the standard frame label. No code calls it today (see "Where it applies today"). |
| `formatTimeShort(seconds)` | `src/audio/time.ts` | `"1:23"` for axis labels, list rows, durations. |
| `parseTime(text)` | `src/audio/time.ts` | Text → seconds, or `null` when it is not a time. |
| `timestampSx` | `src/ui/timestamps.ts` | Monospace, tabular figures, `nowrap`. Callers add size and colour. |
| `FRAME_LABEL_WIDTH` | `src/ui/timestamps.ts` | `140` — width of a frame-label column, sized so rule 3 holds. No code uses it today. |

## Where it applies today

| Place | Shows |
|-------|-------|
| `WaveformRangeSelector` (the Audio step) | Handle tooltips, start/end inputs (`mm:ss.cc`, `parseTime` reads them), "… selected" |
| `AudioTab`, `SourceTab`, `SourceFiles` | The lengths and the cuts of the audio files (`formatTime`, `formatTimeShort`, `timestampSx`) |
| `RollTimeBar` and `playback/ProgressBar.tsx` | The time ruler of the Notes step's roll and the bar under it |
| `ScorePlayer` (the sheet, Play mode) | The length of the piece written: `formatTime` |
| `PassagePage` (Recording in Sheet) | The times of the passage's cut (`formatTime`) |
| `VideoBar`, `FramePlayer`, `VideoNotesPage` (the Lab) | The times of the video (`formatTime`, `formatTimeShort`) |
| The sheet's toolboxes (note, range, lyrics, keyboard) | A frame's time as `mm:ss.cc`, from `formatSeconds` in `pages/piece/sheet/sheetConstants.ts`. It has the same output as `formatTime`, a second copy kept by the sheet's modules; no frame label (`f:N`) is printed there |
| The range toolbox's subtitle | Both ends of a marked stretch, `mm:ss.cc – mm:ss.cc` (a range: both ends are kept) |

**No frame label is printed today.** `formatFrameLabel` and `FRAME_LABEL_WIDTH` have no caller: the matrix grid that
printed `f:N · mm:ss.cc` (its rows, its header `frame · start`) is gone. Rule 2 applies again when a screen prints a
frame label.

Anything added later that prints a frame or a time uses these helpers rather than its own
formatting — that is the whole point of the rule.

## Where to look deeper

- [rendering.md](rendering.md) — where frames become notation
- [sheet-page.md](sheet-page.md) — the sheet page, where the sheet's times are shown
- [../09-coding-conventions.md](../09-coding-conventions.md) — frontend conventions table
- [../../documentation/services/frontend/components.md](../../documentation/services/frontend/components.md) — component detail
