/**
 * `mm:ss.mmm` time formatting and parsing.
 *
 * The range selector's text inputs speak this format (e.g. `03:03.123`), and so
 * do the tooltips, so both live here rather than being re-derived per component.
 */

/** `83.4567` -> `"01:23.457"`. Negative input clamps to zero. */
export function formatTime(seconds: number): string {
  const safe = Number.isFinite(seconds) && seconds > 0 ? seconds : 0;
  const minutes = Math.floor(safe / 60);
  const wholeSeconds = Math.floor(safe % 60);
  const milliseconds = Math.round((safe - Math.floor(safe)) * 1000);
  // Rounding can carry into the next second.
  const carried = milliseconds === 1000;
  return [
    String(carried && wholeSeconds === 59 ? minutes + 1 : minutes).padStart(2, "0"),
    ":",
    String(carried ? (wholeSeconds + 1) % 60 : wholeSeconds).padStart(2, "0"),
    ".",
    String(carried ? 0 : milliseconds).padStart(3, "0"),
  ].join("");
}

/** Short form for axis labels: `"1:23"`. */
export function formatTimeShort(seconds: number): string {
  const safe = Number.isFinite(seconds) && seconds > 0 ? seconds : 0;
  return `${Math.floor(safe / 60)}:${String(Math.floor(safe % 60)).padStart(2, "0")}`;
}

/**
 * `"03:03.123"` -> `183.123`. Also accepts `"3:03"`, `"183"`, `"183.5"`.
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
