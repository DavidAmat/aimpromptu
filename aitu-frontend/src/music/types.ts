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
  tempoBpm: number;
  timeStepSeconds: number;
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
  /** VexFlow key signature spec, e.g. "C", "G", "Bb". Omitted = no key sig. */
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

/** One merged note (a run of consecutive active cells in the same row). */
export type NoteEvent = {
  /** Custom note name, e.g. "Do-3", "Fa#-5". */
  note: string;
  /** VexFlow key with accidental baked into the pitch, e.g. "c/3", "f#/5". */
  vexKey: string;
  startStep: number;
  durationSteps: number;
};

/** A renderable slot: a chord (>=1 key) or a rest, with a VexFlow duration. */
export type VexPiece = {
  /** VexFlow keys with accidentals baked in, e.g. ["c/3", "f#/5"]. Empty for a rest. */
  keys: string[];
  /** VexFlow base duration token: "w" | "h" | "q" | "8" | "16". */
  duration: string;
  /** Augmentation dots (0 or 1) — a dotted note is 1.5× its base length. */
  dots: number;
  isRest: boolean;
  /** Matrix step where this piece starts; used to look up a lyric. */
  startStep: number;
};
