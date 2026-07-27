/**
 * The granularities offered in the transcription settings dropdown.
 *
 * A subset of the seven the engine supports: `redonda`, `blanca` and `semifusa`
 * are legal matrix granularities but make no sense as a *transcription target* —
 * nobody asks for a piece quantized to whole notes, and semifusa is finer than
 * the raw matrix itself. Task 6.2.1 names these four.
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
