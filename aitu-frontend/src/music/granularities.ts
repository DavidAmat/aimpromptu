/**
 * The granularities offered in the transcription settings dropdown.
 *
 * A subset of the seven the engine supports: `redonda`, `blanca` and `semifusa`
 * are legal matrix granularities but make no sense as a *transcription target* —
 * nobody asks for a piece quantized to whole notes, and semifusa is now the raw
 * grid itself, i.e. the resolution everything is snapped *from* rather than one
 * anybody wants printed as 64th notes. Task 6.2.1 names these four.
 *
 * Lives outside the component so React Fast Refresh keeps working (a `.tsx`
 * file may export components only).
 */

import type { Granularity } from "./types";

export const TRANSCRIPTION_GRANULARITIES: { value: Granularity; label: string }[] = [
  { value: "negra", label: "Negra (quarter)" },
  { value: "corchea", label: "Corchea (eighth)" },
  { value: "semicorchea", label: "Semicorchea (sixteenth)" },
  { value: "fusa", label: "Fusa (thirty-second)" },
];

/**
 * How finely the piece is measured, in milliseconds per column.
 *
 * This replaces the BPM and the note-figure resolution that used to sit on the transcription form.
 * A column is now a slice of wall clock, so the only question is how fine that slice should be, and
 * the answer never changes what a note is called. 40 ms suits most playing; a fast passage reads
 * better at 20.
 */
export const FRAME_MS_CHOICES = [
  { value: 20, label: "20 ms — fine (fast playing)" },
  { value: 30, label: "30 ms" },
  { value: 40, label: "40 ms — normal" },
  { value: 60, label: "60 ms — coarse (slow playing)" },
] as const;

export const DEFAULT_FRAME_MS = 40;
