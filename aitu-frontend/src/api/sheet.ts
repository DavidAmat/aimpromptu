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
  /**
   * The AI wrote this sheet, or part of it: the page shows **Enhanced with AI** for good, whatever changes later.
   * Only a new transcription (new notes) forgets it.
   */
  enhanced: boolean;
  /** How many AI runs wrote it. */
  runs: number;
  /** `none`: never written by Sonnet; `running`: a run is going; `done`: a run ended (it may have failed). */
  state: "none" | "running" | "done";
  jobId: string | null;
  /** The API key and the SDK are there. */
  available: boolean;
  /** A new transcription: the page starts Sonnet by itself. */
  auto: boolean;
  /** The page may offer **Enhance with AI**, or **Enhance it again with AI** (the user may change this part). */
  canRun: boolean;
  /** The owner's own version of My library: the button opens the edit copy and starts there. */
  viaEdit: boolean;
  usd: number | null;
  written: string | null;
}

/** One drawn note as its notehead names it (implementation 03, Phase 6), and its reading (Phase 7). */
export interface SheetNote {
  /** `"<frame>:<midi>"`: the `data-note` of its notehead (a head of merged unisons lists several). */
  ref: string;
  hand: "right" | "left";
  /** The name the sheet prints, as it sounds: `C#5`, `Bb3`. */
  pitch: string;
  /** The figure printed: 1 redonda, 2 blanca, 4 negra, 8 corchea, 16 semicorchea, 32 fusa, 64 semifusa. */
  figure: number | null;
  /** The beam group (a number unique in the sheet), or `null`. */
  beam: number | null;
  /** Drawn as a grace note. */
  grace: boolean;
  /** The figure was set by hand: the rule keeps it. */
  fixed: boolean;
  /** The user's grace note switch: `on` a grace note, `off` a normal note, `null` the rule decides. */
  graceRule: "on" | "off" | null;
  finger: number | null;
  /** `trill`, `mordent`, `turn`, `arpeggio`, `fermata`, `tremolo`. */
  ornaments: string[];
  /** The octave line over it: 1 8va, 2 15ma, -1 8vb, -2 15mb, 0 none. */
  ottava: number;
}

/** The armaduras and clefs of the sheet (Phase 7, the range toolbox). An armadura is in fifths: 3 is three
 * sostenidos, -2 two bemoles. */
export interface SheetReading {
  key: number;
  keyChanges: [number, number][];
  clefs: { right?: string; left?: string };
  clefChanges: [number, "right" | "left", string][];
}

/** One reading edit of the toolboxes (Phase 7): the backend's `POST /sheet/{uuid}/reading`. */
export interface ReadingEdit {
  action:
    | "figure"
    | "finger"
    | "beam-join"
    | "beam-break"
    | "grace"
    | "ornament"
    | "key"
    | "clef"
    | "clef-rule"
    | "ottava";
  notes?: readonly string[];
  start?: number;
  end?: number;
  staff?: "both" | "right" | "left";
  value?: number | number[] | string | null;
}

/** The armadura in force at a stretch, and the one that prints the fewest signs over it. */
export interface StretchKeys {
  key: number;
  signs: number;
  fewest: number;
  fewestSigns: number;
}

/** What the AI is asked to write again (Phase 7): a stretch of frames, with what was picked and the user's words. */
export interface StretchRequest {
  start: number;
  end: number;
  staff: "both" | "right" | "left";
  notes?: readonly string[];
  instruction: string;
}

/** What the next undo and redo of the part's steps are about (`null`: nothing). */
export interface SheetHistory {
  undo: string | null;
  redo: string | null;
}

export interface FramesSheet {
  svg: string;
  columns: SheetColumn[];
  systems: SheetSystem[];
  width: number;
  height: number;
  notes: SheetNote[];
  reading: SheetReading;
  segments: SheetSegment[];
  /** Who decided the hands and the reading: `llm`, `mixed` or `algorithm`. */
  source: "llm" | "mixed" | "algorithm";
  /** Written for older notes or hands, and laid again on the current ones. */
  stale: boolean;
  llm: SheetLlm;
  /** The user may change this part, and the AI is not writing it: the notes can be edited (plan section 3.7). */
  editable: boolean;
  history: SheetHistory;
  timings: Record<string, number>;
}

/** The answer of an edit: the sheet drawn again. */
export interface SheetEdited extends FramesSheet {
  /** A hand move: the notes whose hand changed, and the ones the sheet does not hold. */
  moved?: number;
  unmatched?: number;
  /** An undo or a redo: the step it walked (`null`: there was none). */
  walked?: string | null;
  /** A reading edit: the step it made (`null`: nothing changed). */
  edited?: string | null;
}

export const sheetApi = {
  /** The sheet now, drawn for a page `width` staff spaces wide. */
  get: (audioUuid: string, width: number, signal?: AbortSignal) =>
    request<FramesSheet>(`/sheet/${audioUuid}`, { query: { width: Math.round(width) }, signal }),

  /** Start Sonnet on the part (or get the run already going); follow it on `progressUrl(jobId)`. */
  runLlm: (audioUuid: string) =>
    request<{ jobId: string; status: string }>(`/sheet/${audioUuid}/llm`, { method: "POST" }),

  progressUrl: (jobId: string) => buildUrl(`/matrix/progress/${jobId}`),

  /** Give the notes to one hand, in the notes themselves (one step of undo); the sheet drawn again. */
  moveHands: (audioUuid: string, notes: readonly string[], hand: "right" | "left", width: number) =>
    request<SheetEdited>(`/sheet/${audioUuid}/hands`, {
      method: "POST",
      query: { width: Math.round(width) },
      body: { notes, hand },
    }),

  /** One reading edit of the toolboxes (one step of undo); the sheet drawn again. A refused edit says why. */
  read: (audioUuid: string, edit: ReadingEdit, width: number) =>
    request<SheetEdited>(`/sheet/${audioUuid}/reading`, {
      method: "POST",
      query: { width: Math.round(width) },
      body: edit,
    }),

  /** Take notes off the page: they leave the notes (one step of undo); the sheet drawn again. */
  remove: (audioUuid: string, notes: readonly string[], width: number) =>
    request<SheetEdited>(`/sheet/${audioUuid}/remove`, {
      method: "POST",
      query: { width: Math.round(width) },
      body: { notes },
    }),

  /** The armadura in force at a stretch, and the one with the fewest signs over it. */
  stretchKeys: (audioUuid: string, start: number, end: number, signal?: AbortSignal) =>
    request<StretchKeys>(`/sheet/${audioUuid}/stretch`, { query: { start, end }, signal }),

  /** The AI writes a stretch again with the user's words; follow the job on `progressUrl(jobId)`. */
  enhanceStretch: (audioUuid: string, stretch: StretchRequest) =>
    request<{ jobId: string; status: string }>(`/sheet/${audioUuid}/llm/stretch`, {
      method: "POST",
      body: stretch,
    }),

  /** Take the last step of the part back, or put it again; the sheet drawn again. */
  walk: (audioUuid: string, to: "undo" | "redo", width: number) =>
    request<SheetEdited>(`/sheet/${audioUuid}/${to}`, { method: "POST", query: { width: Math.round(width) } }),
};
