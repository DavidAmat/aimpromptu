/**
 * `/sheet` — the new piano sheet of a part (implementation 03, Phase 5).
 *
 * The backend draws the sheet (the engine without compases of `aitu_backend.sheet`) for the width the page asks for,
 * and answers the SVG with the cursor map: one row per drawn column (its system, its x, its time) and one box per
 * system. While Sonnet writes the sheet in the background, the answer is the sheet of that moment, with the state
 * of each segment; the page follows the job's stream and asks again at each `sheet` message.
 */

import { buildUrl, request } from "./client";

/** One drawn column: what sounds together in either hand, at one x. */
export interface SheetColumn {
  system: number;
  frame: number;
  /** In SVG units (staff spaces), the margin included. */
  x: number;
  /** Audio time of the column, in ms. */
  ms: number;
}

/** One line of the sheet (a system: the two staves), in SVG units. */
export interface SheetSystem {
  index: number;
  first: number;
  last: number;
  top: number;
  bottom: number;
  staff_top: number;
  staff_bottom: number;
  left: number;
  right: number;
}

/**
 * A segment of the piece-by-piece view (one window of Sonnet): `llm` written by Sonnet, `algorithm` kept from the
 * algorithm (a window that failed), `working` at Sonnet now, `waiting` not sent yet.
 */
export interface SheetSegment {
  start: number;
  end: number;
  state: "llm" | "algorithm" | "working" | "waiting";
}

export interface SheetLlm {
  /** `none`: never written by Sonnet; `running`: a run is going; `done`: a run ended (it may have failed). */
  state: "none" | "running" | "done";
  jobId: string | null;
  /** The API key and the SDK are there. */
  available: boolean;
  /** A new transcription: the page starts Sonnet by itself. */
  auto: boolean;
  /** The page may offer **Write with Sonnet** (the user may change this part). */
  canRun: boolean;
  /** The owner's own version of My library: the button opens the edit copy and starts there. */
  viaEdit: boolean;
  usd: number | null;
  written: string | null;
}

export interface FramesSheet {
  svg: string;
  columns: SheetColumn[];
  systems: SheetSystem[];
  width: number;
  height: number;
  segments: SheetSegment[];
  /** Who decided the hands and the reading: `llm`, `mixed` or `algorithm`. */
  source: "llm" | "mixed" | "algorithm";
  /** Written for older notes or hands, and laid again on the current ones. */
  stale: boolean;
  llm: SheetLlm;
  timings: Record<string, number>;
}

export const sheetApi = {
  /** The sheet now, drawn for a page `width` staff spaces wide. */
  get: (audioUuid: string, width: number, signal?: AbortSignal) =>
    request<FramesSheet>(`/sheet/${audioUuid}`, { query: { width: Math.round(width) }, signal }),

  /** Start Sonnet on the part (or get the run already going); follow it on `progressUrl(jobId)`. */
  runLlm: (audioUuid: string) =>
    request<{ jobId: string; status: string }>(`/sheet/${audioUuid}/llm`, { method: "POST" }),

  progressUrl: (jobId: string) => buildUrl(`/matrix/progress/${jobId}`),
};
