/**
 * How finely the piece is measured, in milliseconds per column.
 *
 * This replaces the BPM and the note-figure resolution that used to sit on the transcription form.
 * A column is now a slice of wall clock, so the only question is how fine that slice should be, and
 * the answer never changes what a note is called. 40 ms suits most playing; a fast passage reads
 * better at 20.
 *
 * Lives outside the component so React Fast Refresh keeps working (a `.tsx` file may export
 * components only).
 */

export const FRAME_MS_CHOICES = [
  { value: 20, label: "20 ms — fine (fast playing)" },
  { value: 30, label: "30 ms" },
  { value: 40, label: "40 ms — normal" },
  { value: 60, label: "60 ms — coarse (slow playing)" },
] as const;

export const DEFAULT_FRAME_MS = 40;
