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
  /** While the AI writes one hand only (Simplify or a stretch of one hand): its staff, 1 right or 2 left. */
  staff?: 1 | 2;
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
  /** The frame it stops sounding at (Phase 8: the keyboard panel lights the keys still held). */
  end?: number | null;
}

/**
 * A lyrics piece of the new sheet (implementation 03, Phase 8): its words (`\n` breaks a line) over the frames
 * `[start, end)`, drawn above the upper staff from `start`; `size` in staff spaces (`null`: the sheet's own),
 * `lift` in staff spaces above the line of words of its system. The drawing names it `data-lyric` by its place
 * in this list.
 *
 * Phase 8A++ (the user's request): a block moved by hand sits where it was put, whatever its frames: `at` is the
 * frame of the column under its left edge, `dx` how far right of that column it starts, `dy` its last line's
 * baseline below the top staff line (`null`: in the line of words, as before), all in staff spaces. `width` wraps its
 * words (the backend wraps them); `font`, `bold` and `italic` are its style. The frames say only when it sounds.
 */
export interface SheetLyric extends SheetLyricBlock {
  start: number;
  end: number;
  text: string;
  size: number | null;
  lift: number;
}

/** The fonts of a lyrics block (the backend's `LYRIC_FONTS`). */
export type LyricFont = "lora" | "geist" | "montserrat";

/** Where a lyrics block was put, how wide it is and its style (all optional: absent is the default). */
export interface SheetLyricBlock {
  at?: number | null;
  dx?: number;
  dy?: number | null;
  width?: number | null;
  font?: LyricFont;
  bold?: boolean;
  italic?: boolean;
}

/** The title lines printed above the new sheet. */
export interface SheetTitles {
  title?: string;
  subtitle?: string;
  artist?: string;
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
    | "ottava"
    // The sheet toolbox (Phase 8): the whole sheet.
    | "titles"
    | "piece-key"
    | "line-space"
    | "lyrics"
    | "figures";
  notes?: readonly string[];
  start?: number;
  end?: number;
  staff?: "both" | "right" | "left";
  value?:
    | number
    | number[]
    | string
    | null
    | SheetTitles
    | { pieces: readonly SheetLyric[]; label?: string };
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

/** A run of the AI over the whole song (implementation 04, Phase 4): **Simplify** one hand or both, or the full run. */
export type SongRun = "simplify-left" | "simplify-right" | "simplify-both" | "all";

/** About what one run of the Enhance with AI dialog costs: its requests and US dollars. */
export interface LlmCost {
  requests: number;
  usd: number;
}

export type LlmCosts = Record<SongRun | "stretch", LlmCost> &
  Partial<Record<`level-${LevelHand}` | `level-stretch-${LevelHand}`, LlmCost>>;

/** The levels of the whole song simplification (implementation 04-3, Phase 4). Super hard comes later. */
export type LevelName = "easy" | "medium" | "hard";
/** The hands a level writes: both, or one (the other stays exactly as it is). */
export type LevelHand = "both" | "right" | "left";

/** A level run: the level of each hand, the hands, the patterns selected in the catalog, the user's words. */
export interface LevelChoice {
  right: LevelName;
  left: LevelName;
  hand: LevelHand;
  patterns: string[];
  words: string;
}

/** A level of a range: in place, one step of undo. */
export interface LevelRequest extends LevelChoice {
  start: number;
  end: number;
}

/** A level of the whole sheet: written into a new project of My projects (the level copy). */
export interface LevelCopy {
  jobId: string;
  projectId: string;
  partId: string;
  title: string;
}

/** A pattern of the catalog of Enhance with AI (the gallery of patterns). */
export interface CatalogPattern {
  /** `"left medium 2"`. */
  ref: string;
  hand: "left" | "right";
  level: "easy" | "medium" | "hard" | "super hard";
  number: number;
  name: string;
  line: string;
  source: string | null;
  bars: string | null;
}

export interface LevelCatalog {
  patterns: CatalogPattern[];
  /** `hand -> level -> refs`: the patterns a run uses for a hand when none is selected. */
  defaults: Record<"left" | "right", Record<string, string[]>>;
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
  /** What the user wrote about the whole sheet (Phase 8): the title lines, the lyrics pieces, the reference figure
   * (one negra, in ms) and the one the spacing keeps after Transpose figures, the space between lines (`null`: the
   * engine's own, 5 staff spaces). */
  titles: SheetTitles;
  lyrics: SheetLyric[];
  quarterMs: number | null;
  spaceMs: number | null;
  lineSpace: number | null;
  /** The audio's revision: a paste, or its undo, changes the audio too, and the player loads it again. */
  audioRevision: number;
  timings: Record<string, number>;
}

/** A sheet as an edit would leave it (a preview: nothing stored), with what it would do. */
export interface SheetPreview {
  svg: string;
  columns: SheetColumn[];
  systems: SheetSystem[];
  width: number;
  height: number;
  edited: string;
  /** Transpose notes: the notes moved, and those that would leave the keyboard. */
  moved?: number;
  outside?: number;
}

/** One page of the sheet on paper (Print to PDF): an SVG in staff spaces, and the frames of its first and last
 * columns. */
export interface SheetPage {
  svg: string;
  width: number;
  height: number;
  first: number;
  last: number;
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
  /** A paste: where the passage went and how long it is, in ms of the part. */
  atMs?: number;
  lengthMs?: number;
}

// ------------------------------------------------------------------ the vocabulary of a reading

/** The pasted lyrics of a part and its pool of pieces not placed yet. */
export interface SheetWords {
  text: string | null;
  pool: string[] | null;
}

/** The plain figures, and the two dotted ones a figure set by hand on an old sheet could name. */
export type FigureName =
  | "redonda"
  | "blanca"
  | "dottedBlanca"
  | "negra"
  | "dottedNegra"
  | "corchea"
  | "semicorchea"
  | "fusa"
  | "semifusa";

/**
 * The fifteen signatures a staff can be written in, sharpest to flattest.
 *
 * A transcription arrives with no key at all: the recording says which keys were pressed and
 * nothing about how they should be spelled. Until someone chooses, everything is written in C and
 * every black key prints an accidental.
 */
export const KEY_SIGNATURES = [
  "C",
  "G",
  "D",
  "A",
  "E",
  "B",
  "F#",
  "C#",
  "F",
  "Bb",
  "Eb",
  "Ab",
  "Db",
  "Gb",
  "Cb",
] as const;

export type KeySignatureName = (typeof KEY_SIGNATURES)[number];

/**
 * What each signature is called on a picker, with the major key first.
 *
 * Both names are shown because a reader who knows the piece is in D minor should not have to
 * remember that D minor and F major print the same one flat.
 */
export const KEY_LABELS: Record<KeySignatureName, string> = {
  C: "C major / A minor — no sharps or flats",
  G: "G major / E minor — 1 sharp",
  D: "D major / B minor — 2 sharps",
  A: "A major / F# minor — 3 sharps",
  E: "E major / C# minor — 4 sharps",
  B: "B major / G# minor — 5 sharps",
  "F#": "F# major / D# minor — 6 sharps",
  "C#": "C# major / A# minor — 7 sharps",
  F: "F major / D minor — 1 flat",
  Bb: "Bb major / G minor — 2 flats",
  Eb: "Eb major / C minor — 3 flats",
  Ab: "Ab major / F minor — 4 flats",
  Db: "Db major / Bb minor — 5 flats",
  Gb: "Gb major / Eb minor — 6 flats",
  Cb: "Cb major / Ab minor — 7 flats",
};

/** A line of words under the staff, over a stretch of columns. */
export interface LyricLine {
  fromColumn: number;
  /** Exclusive. */
  toColumn: number;
  text: string;
  /**
   * Where the reader dragged the block, in pixels from where the page would have put it.
   *
   * The columns are still what the words belong to, so a re-wrap carries them to wherever that
   * music went and this offset with them. Absent (or `null`, as the backend answers) is a block
   * nobody has moved.
   */
  offsetX?: number | null;
  offsetY?: number | null;
  /** How wide the block is drawn, in pixels. The words wrap inside it. */
  width?: number | null;
  /** How large the words are drawn, in pixels. Absent is the page's own size. */
  fontSize?: number | null;
  /**
   * The new sheet only (implementation 03, Phase 8A++): where the block was put, its width and style, in the new
   * sheet's units, carried as they are through every change of the list.
   */
  block?: SheetLyricBlock;
}

/** What **Copy** puts in the clipboard: a stretch of a part, in milliseconds (plan section 12). */
export interface PassageRef {
  part: string;
  fromMs: number;
  toMs: number;
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

  /** The AI simplifies one hand, or both, over the whole song; follow the job on `progressUrl(jobId)`. */
  simplify: (audioUuid: string, hand: "left" | "right" | "both") =>
    request<{ jobId: string; status: string }>(`/sheet/${audioUuid}/llm/simplify`, {
      method: "POST",
      body: { hand },
    }),

  /** About what each run of the Enhance with AI dialog would cost (with a range: a level of that range too). */
  llmCosts: (audioUuid: string, signal?: AbortSignal, range?: { start: number; end: number }) =>
    request<LlmCosts>(`/sheet/${audioUuid}/llm/costs`, { signal, ...(range ? { query: range } : {}) }),

  /** The AI writes a range again at a level, in place; follow the job on `progressUrl(jobId)`. */
  level: (audioUuid: string, body: LevelRequest) =>
    request<{ jobId: string; status: string }>(`/sheet/${audioUuid}/llm/level`, { method: "POST", body }),

  /** A level of the whole sheet, in a new project of My projects: open `partId`'s sheet to follow it. */
  levelCopy: (audioUuid: string, body: LevelChoice) =>
    request<LevelCopy>(`/sheet/${audioUuid}/llm/level-copy`, { method: "POST", body }),

  /** The catalog of patterns and the patterns used when none is selected. */
  levelCatalog: (signal?: AbortSignal) => request<LevelCatalog>("/sheet/levels/catalog", { signal }),

  /** What a reading edit would leave, without storing it (the preview of Transpose figures). */
  previewRead: (audioUuid: string, edit: ReadingEdit, width: number) =>
    request<SheetPreview>(`/sheet/${audioUuid}/reading`, {
      method: "POST",
      query: { width: Math.round(width), preview: true },
      body: edit,
    }),

  /** Transpose notes: every note of the part moved, the sheet with it (one step of undo); `preview` writes nothing. */
  transpose: (audioUuid: string, semitones: number, width: number, preview = false) =>
    request<SheetEdited & SheetPreview>(`/sheet/${audioUuid}/transpose`, {
      method: "POST",
      query: { width: Math.round(width), ...(preview ? { preview: true } : {}) },
      body: { semitones },
    }),

  /** A note added on the keyboard panel, into the notes (one step of undo); the sheet drawn again. */
  addNote: (
    audioUuid: string,
    note: { frame: number; midi: number; hand: "right" | "left"; lengthMs?: number },
    width: number,
  ) =>
    request<SheetEdited>(`/sheet/${audioUuid}/add`, {
      method: "POST",
      query: { width: Math.round(width) },
      body: note,
    }),

  /** The sheet on paper: whole lines dealt onto pages `height` staff spaces high (`first` for page one). */
  pages: (
    audioUuid: string,
    paper: { width: number; height: number; first: number; gap: number },
    signal?: AbortSignal,
  ) =>
    request<{ pages: SheetPage[] }>(`/sheet/${audioUuid}/pages`, {
      query: {
        width: Math.round(paper.width * 10) / 10,
        height: Math.round(paper.height * 10) / 10,
        first: Math.round(paper.first * 10) / 10,
        gap: Math.round(paper.gap * 10) / 10,
      },
      signal,
    }),

  /** Paste a copied passage at `atMs`, or over `[atMs, replaceToMs)`: its notes, sheet and audio (one step of undo). */
  paste: (
    audioUuid: string,
    body: { source: { part: string; fromMs: number; toMs: number }; atMs: number; replaceToMs?: number },
    width: number,
  ) =>
    request<SheetEdited>(`/sheet/${audioUuid}/paste`, {
      method: "POST",
      query: { width: Math.round(width) },
      body,
    }),

  /** Take the last step of the part back, or put it again; the sheet drawn again. */
  walk: (audioUuid: string, to: "undo" | "redo", width: number) =>
    request<SheetEdited>(`/sheet/${audioUuid}/${to}`, { method: "POST", query: { width: Math.round(width) } }),

  /**
   * The pasted lyrics and the pool of the part (the Lyrics tab's **Save lyrics**): the song's words, kept in
   * `project.json` and not in the sheet, so they outlive a new transcription. `pool` is `null` until saved there.
   */
  words: (audioUuid: string, signal?: AbortSignal) =>
    request<SheetWords>(`/sheet/${audioUuid}/words`, { signal }),

  /** Save the pasted lyrics and the pool with the part. An empty text removes them. */
  saveWords: (audioUuid: string, text: string, pool: readonly string[], signal?: AbortSignal) =>
    request<SheetWords>(`/sheet/${audioUuid}/words`, { method: "PUT", body: { text, pool }, signal }),
};
