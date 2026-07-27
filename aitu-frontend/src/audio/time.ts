/**
 * `mm:ss.cc` time formatting and parsing — the one place that knows how a
 * timestamp looks in this app.
 *
 * **UI rule (see `context/frontend/timestamps.md`):**
 *
 * 1. **Two decimals, never three.** Hundredths are as fine as the eye needs and
 *    they keep every timestamp the same, short width.
 * 2. **A frame is labelled by its start only** — `f:12 · 00:00.25`. The end is
 *    the next frame's start, so printing `[start – end]` doubled the width of
 *    the label to say something the row below already says.
 * 3. **A timestamp never wraps.** Whatever holds one gives it room and sets
 *    `whiteSpace: "nowrap"` — see `timestampSx` / `FRAME_LABEL_WIDTH` in
 *    `src/ui/timestamps.ts`.
 *
 * Parsing stays forgiving (`3:03`, `183`, `1:23.456`) so pasted values from
 * other tools still work; only the *output* is pinned to two decimals.
 */

const pad = (value: number): string => String(value).padStart(2, "0");

/** `83.4567` -> `"01:23.46"`. Negative input clamps to zero. */
export function formatTime(seconds: number): string {
  const safe = Number.isFinite(seconds) && seconds > 0 ? seconds : 0;
  // Round to hundredths up front, so a carry into the next second — and from
  // there into the next minute — is handled once, here, and not per field.
  const hundredths = Math.round(safe * 100);
  return [
    pad(Math.floor(hundredths / 6000)),
    ":",
    pad(Math.floor(hundredths / 100) % 60),
    ".",
    pad(hundredths % 100),
  ].join("");
}

/** Short form for axis labels: `"1:23"`. */
export function formatTimeShort(seconds: number): string {
  const safe = Number.isFinite(seconds) && seconds > 0 ? seconds : 0;
  return `${Math.floor(safe / 60)}:${String(Math.floor(safe % 60)).padStart(2, "0")}`;
}

/**
 * The standard label for a time frame: `"f:12 · 00:00.25"`.
 *
 * Start only, by design — the frame's end is the next row's start. Use this
 * everywhere a frame is named next to its time, so the matrix grid, the piano
 * roll and any future frame list all read identically.
 */
export function formatFrameLabel(frame: number, startSeconds: number): string {
  return `f:${frame} · ${formatTime(startSeconds)}`;
}

/**
 * `"03:03.12"` -> `183.12`. Also accepts `"3:03"`, `"183"`, `"183.5"`, and
 * three-decimal input left over from elsewhere.
 * Returns `null` when the text is not a time, so a half-typed input does not
 * jump the handles around.
 */
export function parseTime(text: string): number | null {
  const trimmed = text.trim();
  if (!trimmed) return null;

  const match = /^(?:(\d+):)?(\d{1,2})(?:\.(\d{1,3}))?$/.exec(trimmed);
  if (match) {
    const [, minutes, seconds, fraction] = match;
    const milliseconds = fraction ? Number(fraction.padEnd(3, "0")) : 0;
    return Number(minutes ?? 0) * 60 + Number(seconds) + milliseconds / 1000;
  }

  // Bare seconds, possibly fractional and possibly > 59.
  const bare = /^\d+(?:\.\d+)?$/.exec(trimmed);
  return bare ? Number(trimmed) : null;
}

/** Keep a value inside `[min, max]`. */
export function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}
