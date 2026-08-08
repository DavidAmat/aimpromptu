/**
 * Music contracts shared with the backend. The Pydantic definitions in
 * `aitu-backend/src/aitu_backend/schemas/{score,matrix}.py` are authoritative —
 * keep this file in step with them. camelCase on the wire, as there.
 */

/** Sparse binary matrix (COO), sorted by column then row. */
export type SparseMatrix = {
  format: "binary-coo";
  /** [rowCount, columnCount]; rowCount is 88 (full grand piano). */
  shape: [number, number];
  /** rows[i]/cols[i] mark an active cell; everything else is silent. */
  rows: number[];
  cols: number[];
  /**
   * onset[i] === rows[i] when the cell is a struck onset, or -1 when the
   * cell is a sustain (the note keeps sounding without being struck again).
   * This disambiguates one held note from repeated strikes.
   */
  onset: number[];
};

export type MatrixScore = {
  title?: string;
  /**
   * How long one written frame lasts, in milliseconds. The only timing the
   * portable format carries. It replaced a `tempoBpm` and a `timeStepSeconds`
   * that said the same thing twice: a frame used to be a note figure whose
   * length came from a tempo, so the same text meant different music depending
   * on a number stored beside it.
   */
  frameMs: number;
  /**
   * Optional row-index -> note-name table. The 88-key order is canonical and
   * rebuilt by the frontend, so the backend no longer ships it.
   */
  rows?: string[];
  matrixEncoding?: "sparse-coo";
  /**
   * One hand: a single treble-clef matrix. Mutually exclusive with the
   * `r_matrix`/`l_matrix` pair below — exactly one form is present.
   */
  matrix?: SparseMatrix;
  /** Two hands, right hand — rendered on the treble clef. */
  r_matrix?: SparseMatrix;
  /** Two hands, left hand — always rendered on the bass clef. Shares the
   *  same column count as `r_matrix` so the hands stay time-aligned. */
  l_matrix?: SparseMatrix;
  /** One entry per matrix time step. Empty string means no lyric. */
  lyrics?: string[];
  /** Key signature spec, e.g. "C", "G", "Bb". Omitted = no key sig. */
  keySignature?: string;
};

// --------------------------------------------------------------------------
// Piano matrix contracts (mirror of schemas/matrix.py)
// --------------------------------------------------------------------------

/** Temporal resolution of one matrix column, named after the note figure. */
export type Granularity =
  | "redonda"
  | "blanca"
  | "negra"
  | "corchea"
  | "semicorchea"
  | "fusa"
  | "semifusa";

/** Duration of one column in beats, where a beat is a negra (quarter note). */
export const GRANULARITY_BEATS: Record<Granularity, number> = {
  redonda: 4,
  blanca: 2,
  negra: 1,
  corchea: 0.5,
  semicorchea: 0.25,
  fusa: 0.125,
  semifusa: 0.0625,
};

/** Coarse to fine. Collapsing walks this one step at a time. */
export const GRANULARITY_HIERARCHY: Granularity[] = [
  "redonda",
  "blanca",
  "negra",
  "corchea",
  "semicorchea",
  "fusa",
  "semifusa",
];

/** Short codes used in version folder names (`v2_gn`). */
export const GRANULARITY_CODES: Record<Granularity, string> = {
  redonda: "gr",
  blanca: "gb",
  negra: "gn",
  corchea: "gc",
  semicorchea: "gsc",
  fusa: "gf",
  semifusa: "gsf",
};

/** Where a matrix sits in the pipeline. */
export type MatrixProcessingStep = "raw" | "collapsed" | "clean" | "two-hands";

/** Which hand a matrix belongs to; "single" means not yet split. */
export type Hand = "single" | "left" | "right";

/** One matrix key, labelled in both languages the UI shows. */
export type KeyLabel = {
  /** Spanish solfège, the notation contract form: "Fa#-5". */
  es: string;
  /** English scientific pitch: "F#5". */
  en: string;
  /** Matrix row index, 0 = "La-0". */
  row: number;
};

/**
 * Everything needed to interpret one exported or imported matrix.
 *
 * Orientation warning — the two payloads are transposed relative to each other:
 * the sparse COO form is 88 x N (row = key, col = frame), while `denseMatrix`
 * is N x 88 (row = time frame, col = key), which is what `columnHeaders`
 * (88 key labels) and `rowTimestamps` (N frame times) describe and what the
 * Matrix tab renders.
 *
 * This is also, unchanged, what `@aimpromptu/grid-notation` reads: the renderer
 * takes the pipeline's own envelope rather than an engraved score, which is why
 * there is no score model in this app to keep in step with the matrix.
 */
export type PianoMatrixEnvelope = {
  tempoBpm: number;
  timeStepSeconds: number;
  granularity: Granularity;
  matrixProcessingStep: MatrixProcessingStep;
  /** True when the COO payload is used; false when the dense one is. */
  sparse: boolean;

  matrix?: SparseMatrix | null;
  rMatrix?: SparseMatrix | null;
  lMatrix?: SparseMatrix | null;

  /** Dense grids, frames x keys, of 1 (onset) / -1 (sustain) / 0 (silence). */
  denseMatrix?: number[][] | null;
  denseRMatrix?: number[][] | null;
  denseLMatrix?: number[][] | null;

  columnHeaders?: KeyLabel[] | null;
  rowTimestamps?: number[] | null;

  title?: string | null;
  keySignature?: string | null;
};

/** Cell values in the dense form. */
export const ONSET = 1;
export const SUSTAIN = -1;
export const SILENCE = 0;

/** One character per onset in the compact hand map: left or right. */
export type HandChar = "l" | "r";

/**
 * Which hand plays each onset — mirrors the backend `HandAssignments`.
 *
 * `handMap` is one character per onset in the matrix's canonical (column, row)
 * order, which is exactly the order the sparse COO payload lists its onsets in.
 * Sustains carry no character: a note is played by one hand from strike to
 * release, so they inherit their onset's hand. See `handMap.ts` for the reader.
 *
 * Computed once when the clean matrix is produced, not per render, so the
 * notation, piano-roll and falling-note views cannot disagree about who plays
 * what. Check `onsetCount` / `frameCount` / `granularity` against the matrix in
 * hand before trusting it — a mismatch means the matrix changed after the split.
 */
export type HandAssignments = {
  schemaVersion: string;
  /** "beam" | "greedy" | "exact" | "threshold" — which method produced this. */
  method: string;
  /** e.g. "rrlrlllrr". */
  handMap: string;
  onsetCount: number;
  granularity: Granularity;
  frameCount: number;
  /** Onsets whose decision margin was thin. A review hint, not an error count. */
  ambiguousOnsets: number;
  /** Groups no two hands could play. Non-zero means the transcription is off. */
  infeasibleGroups: number;
  warnings: string[];
  computedAt: string;
};
