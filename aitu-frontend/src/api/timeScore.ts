/**
 * `/time` — the wall-clock path: where the rhythm piles up, what to call it, and the score.
 *
 * Three calls, and they are the three things the reader does. Ask where the gaps between notes pile
 * up, point at one pile and say what it is, then read the result on a staff.
 *
 * Nothing here is stored on the backend. Every call re-derives from the recorded notes, so changing
 * the time resolution is another request rather than a rebuild.
 */

import { ApiError, request } from "./client";

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

export type PrintedHand = "right" | "left";
export type HandChoice = PrintedHand | "both";

/** How a figure is written on screen, in the words the sheet uses. */
export const FIGURE_LABELS: Record<FigureName, string> = {
  redonda: "Redonda (whole)",
  blanca: "Blanca (half)",
  dottedBlanca: "Blanca with a dot",
  negra: "Negra (quarter)",
  dottedNegra: "Negra with a dot",
  corchea: "Corchea (eighth)",
  semicorchea: "Semicorchea (sixteenth)",
  fusa: "Fusa (thirty-second)",
  semifusa: "Semifusa (sixty-fourth)",
};

/** One pile of gaps in the distribution, as the plot draws it. */
export interface Peak {
  /** Where the pile is centred, in milliseconds. This is the number that gets named. */
  centreMs: number;
  medianMs: number;
  meanMs: number;
  count: number;
  /** Between 0 and 1. A pile holding half the gaps is the one worth naming. */
  share: number;
  loMs: number;
  hiMs: number;
}

export interface PeaksResponse {
  audioUuid: string;
  hand: HandChoice;
  frameMs: number;
  startSeconds: number;
  endSeconds: number;
  attackCount: number;
  gapCount: number;
  peaks: Peak[];
  /** Set when the gaps look machine-made rather than played. Plain language, shown as written. */
  warning?: string | null;
}

export interface FigureLadder {
  anchorFigure: FigureName;
  anchorMs: number;
  msByFigure: Record<FigureName, number>;
}

export interface LabelledPeak {
  peak: Peak;
  figure: FigureName;
  figureMs: number;
  /** How far the pile sits from the figure it was given, as a percentage. Small is good. */
  percentOff: number;
  /** Set when the pile is a third of a figure: three of these fill one of those. */
  tresilloOf?: FigureName | null;
  /** What to write next to the pile, for example `corchea de tresillo`. */
  name: string;
}

export interface LadderPreview {
  ladder: FigureLadder;
  /** For example `negra = 337 ms · ≈178 BPM`. */
  headerLabel: string;
  bpm: number;
  labelled: LabelledPeak[];
}

/**
 * A stretch printed as one held note with `tr` over it, instead of the alternations played.
 *
 * A reading of the page and nothing more: every alternation is still in the recording, playback
 * still sounds all of them, and dropping the mark prints them again exactly.
 */
export interface Trill {
  hand: PrintedHand;
  startFrame: number;
  /** One past the column of the run's last onset. */
  endFrame: number;
  /** The note that stays on the page — the lower of the two, because `tr` means "with the one above". */
  row: number;
}

/** One stretch the backend found two notes alternating in, offered to the reader. */
export interface TrillSuggestion {
  hand: PrintedHand;
  startFrame: number;
  endFrame: number;
  row: number;
  otherRow: number;
  /** What the two notes are called, for example `Si-3` and `Do-4`. */
  noteName: string;
  otherNoteName: string;
  noteCount: number;
  /** How many times the pair came round. Three is the threshold. */
  pairRepeats: number;
  medianGapMs: number;
  startSeconds: number;
  endSeconds: number;
}

export interface TrillsResponse {
  audioUuid: string;
  frameMs: number;
  suggestions: TrillSuggestion[];
}

/**
 * A small note leaning on a note of the music.
 *
 * A mark and not an event: it is not in the recording, it takes no column, nothing plays it, and no
 * figure is measured differently because of it. `row` is the grace note's own pitch; `targetRow` is
 * the note it leans on.
 *
 * An **acciaccatura** is crushed — as fast as possible — and prints with a slash through its stem.
 * An **appoggiatura** leans, taking time from the note it precedes, and prints without one.
 */
export interface GraceNote {
  hand: PrintedHand;
  startFrame: number;
  targetRow: number;
  row: number;
  kind: "acciaccatura" | "appoggiatura";
}

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
   * music went and this offset with them. Absent is a block nobody has moved.
   */
  offsetX?: number;
  offsetY?: number;
  /** How wide the block is drawn, in pixels. The words wrap inside it. */
  width?: number;
  /** How large the words are drawn, in pixels. Absent is the page's own size. */
  fontSize?: number;
}

/** A stretch printed smaller than the rest of the page. Asked for, never inferred. */
export interface CueRange {
  /** `"right"`, `"left"`, or `"single"` for both staves. */
  hand: string;
  fromColumn: number;
  /** Exclusive. */
  toColumn: number;
}

export interface SparseMatrix {
  format: "binary-coo";
  shape: [number, number];
  rows: number[];
  cols: number[];
  onset: number[];
}

export interface TimeMatrixEnvelope {
  schemaVersion: "2.0";
  sparse: true;
  frameMs: number;
  frameCount: number;
  durationSeconds: number;
  title?: string | null;
  keySignature?: string | null;
  matrixProcessingStep: "two-hands";
  rMatrix: SparseMatrix;
  lMatrix: SparseMatrix;
}

export interface Passage {
  id: string;
  startFrame: number;
  endFrame: number;
  ladder: FigureLadder;
  headerLabel: string;
}

export interface PrintedNote {
  hand: PrintedHand;
  row: number;
  startFrame: number;
  printedFrames: number;
  printedMsExact: number;
  figure: FigureName;
  fitError: number;
  groupId: number;
  /** How many notes this one is grouped with against the beat. 3 for a tresillo. */
  tuplet?: number | null;
  /** The notes of one tresillo share this. */
  tupletId?: number | null;
}

export interface LayoutHints {
  frameGroup: number;
  frameMeasure: number;
  silenceGroupPx: number;
  hideLeftHand?: boolean;
  hideRightHand?: boolean;
}

export interface TimeScorePayload {
  schemaVersion: "2.0";
  envelope: TimeMatrixEnvelope;
  passages: Passage[];
  notes: PrintedNote[];
  overrides: unknown[];
  layout: LayoutHints;
  /** How many ornaments were left off the page because the reader asked for it. */
  decorativeDropped?: number;
}

export interface PeaksQuery {
  hand?: HandChoice;
  frameMs?: number;
  startSeconds?: number;
  endSeconds?: number;
}

export const timeScoreApi = {
  peaks(audioUuid: string, query: PeaksQuery = {}, signal?: AbortSignal) {
    return request<PeaksResponse>(`/time/${audioUuid}/peaks`, {
      query: {
        hand: query.hand,
        frameMs: query.frameMs,
        startSeconds: query.startSeconds,
        endSeconds: query.endSeconds,
      },
      signal,
    });
  },

  ladderPreview(
    audioUuid: string,
    body: { anchorFigure: FigureName; anchorMs: number; hand?: HandChoice; frameMs?: number },
    signal?: AbortSignal,
  ) {
    return request<LadderPreview>(`/time/${audioUuid}/ladder-preview`, {
      method: "POST",
      body,
      signal,
    });
  },

  /**
   * The sheet: the two hand matrices, the passages, and every note with its figure already named.
   *
   * A POST, because the notes taken off the page travel with it and they are a list as long as the
   * reader likes. They have to be on this request rather than applied in the browser: the printed
   * length of a note is the gap to the next onset **in the same hand**, so hiding one lengthens
   * whatever came before it — which is the point of hiding a note the transcriber invented.
   * Nothing is written to the recording: the backend copies the split, folds the hidden set into
   * the copy, and names the figures from that.
   */
  score(
    audioUuid: string,
    query: {
      anchorFigure?: FigureName;
      anchorMs: number;
      frameMs?: number;
      /** Frames where a new stretch starts. Each stretch needs its own entry in `boundaryMs`. */
      boundaries?: number[];
      boundaryMs?: number[];
      /** Notes the reader took off the page. */
      hiddenNotes?: { startFrame: number; row: number }[];
      /**
       * Stretches the reader accepted as trills.
       *
       * On the request for the same reason the hidden notes are: the printed figure of a note
       * is the gap to the next onset in the same hand, so taking the alternations off the page
       * has to happen before any figure is named. Collapsed in the browser the held note would
       * print as a semicorchea with a `tr` over it.
       */
      trills?: Trill[];
      /**
       * Leave the ornaments off: a sixteenth or shorter printed right before an eighth or longer
       * in the same hand is taken off the page, and the note before it runs on. Nothing is
       * written in its place (D-16).
       */
      dropDecorative?: boolean;
    },
    signal?: AbortSignal,
  ) {
    return request<TimeScorePayload>(`/time/${audioUuid}/score`, {
      method: "POST",
      body: {
        anchorFigure: query.anchorFigure,
        anchorMs: query.anchorMs,
        frameMs: query.frameMs,
        boundaries: query.boundaries ?? [],
        boundaryMs: query.boundaryMs ?? [],
        hiddenNotes: query.hiddenNotes ?? [],
        trills: query.trills ?? [],
        dropDecorative: query.dropDecorative ?? false,
      },
      signal,
    });
  },

  /**
   * Where two notes are trading places fast enough to be worth one `tr`.
   *
   * A suggestion and nothing more. Nothing is written and the sheet does not change until the
   * reader accepts one: a missed trill costs a reader nothing, and a wrong one hides notes that
   * were really played.
   */
  trills(
    audioUuid: string,
    query: { frameMs?: number; minPairRepeats?: number } = {},
    signal?: AbortSignal,
  ) {
    return request<TrillsResponse>(`/time/${audioUuid}/trills`, {
      query: { frameMs: query.frameMs, minPairRepeats: query.minPairRepeats },
      signal,
    });
  },

  /**
   * The reading saved for this piece, or `null` when nobody has saved one.
   *
   * Everything else about a score is worked out from the recorded notes on each request. This is
   * the part that cannot be: nothing in a recording says which pile of gaps is the beat, or where a
   * phrase restarts. A 404 is the normal answer for a piece nobody has read yet, so it comes back
   * as `null` rather than throwing.
   */
  async rhythm(audioUuid: string, signal?: AbortSignal): Promise<SavedRhythm | null> {
    try {
      return await request<SavedRhythm>(`/time/${audioUuid}/rhythm`, { signal });
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 404) return null;
      throw caught;
    }
  },

  saveRhythm(audioUuid: string, body: SavedRhythm, signal?: AbortSignal) {
    return request<SavedRhythm>(`/time/${audioUuid}/rhythm`, { method: "PUT", body, signal });
  },

  forgetRhythm(audioUuid: string, signal?: AbortSignal) {
    return request<void>(`/time/${audioUuid}/rhythm`, { method: "DELETE", signal });
  },

  /**
   * Take notes off the recording, addressed by the column and row the sheet drew.
   *
   * The twin of `matrixApi.setRemoved`, which the roll uses with raw seconds. Two
   * calls because the two screens hold different things — a reader on the sheet
   * has clicked a notehead and knows only where it sits on the grid — but they
   * write the same thing, so a note taken off here is gone from the roll too and
   * from the gaps the rhythm is measured from.
   */
  setRemoved(
    audioUuid: string,
    frameMs: number,
    notes: { startFrame: number; row: number }[],
    removed: boolean,
    signal?: AbortSignal,
  ) {
    return request<{ changed: number; unmatched: number }>(`/time/${audioUuid}/removed`, {
      method: "PUT",
      body: { frameMs, notes, removed },
      signal,
    });
  },

  /**
   * Put notes into the recording, addressed by the column and row the sheet draws.
   *
   * The opposite of `setRemoved`, and written to the same place for the same reason. A reader
   * looking at the keyboard panel can see a note missing from a chord, and hanging an extra
   * notehead off the drawing would be the wrong fix twice over: the printed length of a note is
   * the gap to the next onset in the same hand, so a note appearing out of nowhere renames its
   * neighbour — and the roll, the falling view and playback would all go on disagreeing with the
   * page. The hand travels with it, pinned the way a corrected hand is.
   */
  addNotes(
    audioUuid: string,
    body: {
      frameMs: number;
      notes: {
        startFrame: number;
        row: number;
        hand: PrintedHand;
        /** How many columns it is held for. One is the shortest a note can be. */
        lengthFrames?: number;
      }[];
    },
    signal?: AbortSignal,
  ) {
    return request<{ added: number; duplicate: number }>(`/time/${audioUuid}/notes`, {
      method: "PUT",
      body,
      signal,
    });
  },

  /**
   * Say which hand plays these notes. Written onto the recording, not onto this page.
   *
   * A hand is a fact about the playing: it survives a change of column length, it decides the
   * printed length of the notes around it, and every figure, beam and bracket is derived from it.
   * So the correction goes upstream of all of that rather than being an overlay the drawing has to
   * remember, and the sheet is asked for again afterwards, built from the corrected matrix.
   */
  setHands(
    audioUuid: string,
    body: {
      frameMs: number;
      notes: { startFrame: number; row: number; hand: "right" | "left" }[];
    },
    signal?: AbortSignal,
  ) {
    return request<{ assigned: number; unmatched: number }>(`/time/${audioUuid}/hands`, {
      method: "PUT",
      body,
      signal,
    });
  },
};

/** Where the piece changes speed, and what a gap is worth from there on. */
export interface SpeedChange {
  startFrame: number;
  anchorMs: number;
}

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

/** One reader's reading of one piece: everything about a score that is not derived. */
export interface SavedRhythm {
  schemaVersion?: string;
  hand: HandChoice;
  /** The column length the columns below were numbered at. */
  frameMs: number;
  /**
   * The signature the whole piece is written in.
   *
   * Part of the reading rather than of the recording, exactly like the anchor: nothing in the
   * recorded notes says whether a black key is an F sharp or a G flat.
   */
  keySignature?: KeySignatureName;
  /**
   * Where the piece leaves that signature, and what it changes to, keyed by column.
   *
   * Transitions rather than ranges: at any column exactly one signature is sounding, so two edits
   * cannot disagree about what a reader is looking at. Giving a passage its own key writes two,
   * one where it starts and one where the piece goes back.
   */
  keyChanges?: { fromColumn: number; keySignature: KeySignatureName }[];
  /**
   * Where one hand starts printing a different clef, keyed by column.
   *
   * Transitions rather than ranges, exactly as the key changes are. A left hand that spends a page
   * above middle C reads better on a treble clef than under a stack of ledger lines, and nothing in
   * the recording says which a reader wants.
   */
  clefChanges?: { hand: PrintedHand; fromColumn: number; clef: "treble" | "bass" }[];
  anchorFigure: FigureName;
  anchorMs: number;
  speedChanges: SpeedChange[];
  overrides: { hand: string; row: number; startFrame: number; figure: FigureName }[];
  beamBreaks: { hand: string; startFrame: number }[];
  /**
   * Notes the reader asked to keep inside the beam they are in.
   *
   * The other half of a beam break. A break says "start a new group here"; a join says "do not",
   * and stands the automatic rule down where a run turns over at its lowest note but the player
   * hears one gesture. Neither is derivable, so both are stored.
   */
  beamJoins?: { hand: string; startFrame: number }[];
  /**
   * Where a hand is written an octave or two from where it sounds, as half-open column ranges.
   *
   * Part of the reading, not of the recording: the page proposes brackets where a hand runs far
   * outside its own staff, and the reader keeps, moves or clears them. Absent on a reading saved
   * before brackets existed, which is why it is optional — absent means "never decided", and the
   * page then takes its own suggestion, while an empty list means "decided, none".
   */
  ottavas?: {
    kind: "8va" | "8vb" | "15ma" | "15mb";
    hand: PrintedHand;
    fromColumn: number;
    toColumn: number;
    /**
     * The reader took the bracket off the page and kept the reading.
     *
     * Not a removal: the notes under it are still written an octave from where they sound, so this
     * is only the dashed line and the `8va` going. Absent on a reading saved before a bracket could
     * be hidden, which reads as drawn.
     */
    hidden?: boolean;
  }[];
  /**
   * Notes the reader took off the page, addressed without a hand.
   *
   * Right and left can never strike the same key in the same frame, so the pair already names one
   * note, and leaving the hand out is what lets a note keep its identity across a move to the other
   * staff. Nothing here is an edit to the recording: the matrix still holds every one of them.
   */
  hiddenNotes?: { startFrame: number; row: number }[];
  /** Which finger plays a note, by the staff it is drawn on. */
  fingers?: { hand: string; startFrame: number; row: number; finger: number }[];
  /** Stretches printed as one held note with `tr` over them. */
  trills?: Trill[];
  /** Small notes leaning on a note of the music. */
  graceNotes?: GraceNote[];
  /** Lines of words written under the staff. */
  lyrics?: LyricLine[];
  /** Stretches printed smaller than the rest of the page. */
  cueRanges?: CueRange[];
  /** Stretches the reader set wider or narrower than the page would set them. */
  spacings?: { fromColumn: number; toColumn: number; scale: number }[];
  /**
   * Runs of one hand's notes set an equal distance apart, whatever the other hand needs.
   *
   * `scale` is a multiple of the widest gap the run already had. One is the tightest spacing at
   * which nothing has to give way; below one the run is closed tighter than its columns measured
   * and the glyphs may touch, which the reader is allowed to ask for and can see.
   */
  evenSpacings?: {
    hand: PrintedHand;
    fromColumn: number;
    toColumn: number;
    scale: number;
  }[];
  /** Whether the ornaments are left off the page. A switch on the page, remembered here. */
  dropDecorative?: boolean;
  /**
   * How large the marks over and under the staff are drawn, as a multiple of their normal size.
   *
   * Per piece rather than per app: one piece is dense enough that fingering crowds it, another airy
   * enough that the same numbers are hard to read.
   */
  annotationScale?: number;
  /**
   * How much white space there is between one set of pentagrams and the next, in pixels.
   *
   * Per piece, for the same reason the mark size is: one fixed gap is more page than a piece that
   * stays inside its staves needs, and not enough for one where a low note of the left hand and a
   * high note of the next line's right hand reach towards each other through it.
   *
   * Absent means nobody was ever asked — a reading saved before the control existed — and the page
   * draws it with its own default.
   */
  lineSpacing?: number;
  /**
   * Lines the reader spread wider or narrower than the rest, one at a time.
   *
   * Keyed by a column inside the line rather than by its place down the page: the sheet re-wraps to
   * the window, so "the third line" is different music at another width, while a column never
   * moves.
   */
  staffGaps?: { fromColumn: number; gap: number }[];
  /**
   * Extra pixels between one note and the next, everywhere on the page.
   *
   * The twin of `lineSpacing`, one axis over. The page measures each column from what is drawn in
   * it, which is right and can still be tighter than a person wants to play from; this is their own
   * answer, charged to the columns carrying a note so the silences keep the width the wall clock
   * gives them.
   *
   * Absent means nobody was ever asked, and the page draws it with its own default.
   */
  noteSpacing?: number;
  savedAt?: string;
}
