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
