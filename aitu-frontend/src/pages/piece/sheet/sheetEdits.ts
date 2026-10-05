/**
 * The edits model of the Sheet step: every decision a reader makes about the piano sheet, in one
 * value, and how it is read from and written to the saved reading (`rhythm.json`).
 *
 * Split out of `RhythmPage.tsx` (implementation 02, Phase 2).
 */

import type {
  CueRange,
  FigureName,
  GraceNote,
  HandChoice,
  KeySignatureName,
  LyricLine,
  SavedRhythm,
  Trill,
} from "../../../api";
import type {
  Clef,
  ClefChangeAnnotation,
  EvenSpacingAnnotation,
  FingerNumber,
  KeyChangeAnnotation,
  KeySignature,
  OttavaAnnotation,
  OttavaKind,
  SpacingAnnotation,
  StaffGapOverride,
} from "@aimpromptu/grid-notation";
import {
  DEFAULT_LINE_SPACING,
  DEFAULT_NOTE_SPACING,
} from "../../../components/time/TimeScoreView";
import { frameOf, handOf, rowOf, type NoteRef } from "../../../music/renderOverrides";

export interface Stretch {
  /** The frame the stretch starts at. Everything before it keeps the previous name. */
  startFrame: number;
  /** What a gap is called from here on, in milliseconds. */
  anchorMs: number;
}

/**
 * Everything a reader decides about this sheet, in one value.
 *
 * One object rather than sixteen pieces of state, because undo is going back to the set of
 * decisions that was here a moment ago, and a set is only a thing you can go back to if it is one
 * thing. This is also exactly what `rhythm.json` stores, which is not a coincidence: the file is
 * the list of things nobody can derive, and so is this.
 *
 * What is *not* in here: which notes are picked, which stretch is marked, where a toolbox sits,
 * what is half-typed in a field, and which pile of gaps was named. None of those is a decision
 * about the sheet, and a Command-Z that took the reader's selection away would be a nuisance.
 */
export interface SheetEdits {
  /** The signature the whole piece is written in. C until somebody chooses. */
  keySignature: KeySignatureName;
  /**
   * Where the piece leaves that signature, and what it changes to.
   *
   * Transitions rather than ranges, which is how the drawing package stores them: at any column
   * exactly one signature is sounding, so two edits cannot disagree. Giving a passage its own key
   * writes two, one at each end.
   */
  keyChanges: KeyChangeAnnotation[];
  /**
   * Where each hand leaves the clef it normally reads, and what it changes to.
   *
   * Transitions rather than ranges, which is how the drawing package stores them and for the same
   * reason the key changes are: at any column each hand prints exactly one clef, so two edits
   * cannot disagree. Giving a passage its own clef writes two, one at each end.
   *
   * It is the honest answer to a hand that spends a page far outside its own staff, and a better
   * one than an octave bracket where the passage is long: under a bracket the notes are written an
   * octave from where they sound, on the other clef they are written exactly where they sound.
   */
  clefChanges: ClefChangeAnnotation[];
  /**
   * Where each hand is written an octave or two from where it sounds. **Entirely the reader's.**
   *
   * Nothing proposes these any more. The screen used to seed itself from what the register asked
   * for, which existed because the hand split left passages stranded on the wrong staff under a
   * pile of ledger lines and a bracket was the cheapest way to make them readable. P8.6 charged
   * the split for those ledger lines instead, so an automatic bracket is now mostly a bracket over
   * music that did not need one. A single high note still reads better under `8va`, and that is
   * one click on the Octave pill.
   */
  ottavas: OttavaAnnotation[];
  /**
   * Stretches printed as one held note with `tr` over them.
   *
   * The alternations stay in the recording and playback still sounds every one of them; what the
   * mark changes is which noteheads are drawn. They travel with the sheet request rather than
   * being applied here, because the printed length of the held note is the gap to the next onset
   * after the run, and only the backend measures that.
   */
  trills: readonly Trill[];
  /** Lines of words under the staff, over a stretch of columns. */
  lyrics: readonly LyricLine[];
  /** Stretches printed smaller than the rest of the page. */
  cueRanges: readonly CueRange[];
  /** Stretches the reader set wider or narrower than the page would set them. */
  spacings: SpacingAnnotation[];
  /**
   * Runs of one hand's notes the reader asked to have set an equal distance apart.
   *
   * The page measures every column from what is drawn in it, and both staves share the column — so
   * a run of even corcheas in the right hand comes out unevenly spaced wherever the left hand needs
   * room at one of those moments. Nothing is wrong with the page when that happens; the space
   * really is being used. It still reads as a mistake in the playing, because a beam of equal notes
   * that is not equally spaced is what an uneven performance looks like.
   *
   * So this is the reader choosing: make the run even, and let the width be whatever that costs.
   * `scale` is a multiple of the tightest even spacing the run allows — never less than one,
   * because a gap cannot close below the ink in its columns.
   */
  evenSpacings: EvenSpacingAnnotation[];
  /** Which finger plays each note, keyed `hand:startFrame:row`. */
  fingers: Record<string, FingerNumber>;
  /**
   * Figures set by hand on one chord, keyed `hand:startFrame`.
   *
   * Drawn on top rather than sent back for a rebuild, because an override is only a glyph: nothing
   * moves and no other note changes. Writing the sheet again keeps them.
   */
  overrides: Record<string, FigureName>;
  /**
   * Notes the reader has asked to start a new beam, keyed `hand:startFrame`.
   *
   * Beside the overrides and for the same reason: it changes how the page is grouped and nothing
   * about the music. A long arpeggio beams as one slope because no rule can see where the phrase
   * restarts — only the person reading can, so they say.
   */
  beamBreaks: ReadonlySet<string>;
  /**
   * Notes the reader asked to keep inside the beam they are in, keyed `hand:startFrame`.
   *
   * The other half of a beam break, and it has to be stored for the same reason: the page cuts a
   * beam where a run turns over at its lowest note, which is right for an arpeggio and wrong for a
   * scale that happens to dip. "These are one gesture" is a reading of the music, exactly as "the
   * phrase restarts here" is, and no rule has it.
   */
  beamJoins: ReadonlySet<string>;
  /**
   * Notes the reader took off the page, as `startFrame:row`.
   *
   * A transcriber inventing a note out of a pedal blur is the commonest thing wrong with a page,
   * and the honest fix is to stop drawing it, not to say it was never played. The recording is
   * evidence and stays as it is; this is a set of keys beside it. Bringing one back restores it
   * exactly.
   */
  hiddenNotes: ReadonlySet<NoteRef>;
  /**
   * Small notes leaning on a note of the music.
   *
   * Never inferred, and never played: a grace note is a reading of how a note should be
   * approached, and nothing in a recording distinguishes one from a very short note that was
   * really struck.
   */
  graceNotes: readonly GraceNote[];
  /** Whether the ornaments are left off the page. */
  dropDecorative: boolean;
  /** How large the marks over and under the staff are drawn, as a multiple of normal. */
  annotationScale: number;
  /**
   * How much white space there is between the staves of one line and the staves of the next, in
   * pixels. Nought puts one set of pentagrams directly under the one above.
   */
  lineSpacing: number;
  /**
   * Extra pixels between one note and the next, everywhere on the page.
   *
   * The twin of the space between lines, one axis over. The page measures each column from what is
   * drawn in it, which is right and can still be tighter than a person wants to play from — so this
   * is the reader's own answer, charged to the columns that carry a note and to no others. The
   * silences keep the width the wall clock gives them, because that is the one thing this page
   * already says well.
   */
  noteSpacing: number;
  /**
   * Lines spread wider or narrower than the rest, one at a time, keyed by a column inside each.
   *
   * The handle between the two staves of a line. It is per line rather than per page because the
   * reason for wanting it is per line: one wide chord, or one passage reaching down, needs room
   * that every other line on the score would only waste.
   *
   * Keyed by a column and not by a place down the page, because the page re-wraps to the window
   * and "the third line" is different music after it. A column never moves, which is what every
   * other mark here is addressed by.
   */
  staffGaps: readonly StaffGapOverride[];
  /**
   * Where the piece changes speed, and what a gap is called after each of them.
   *
   * A boundary is drawn by hand. Nothing detects them: a wrong hand-drawn one spoils one stretch,
   * while a wrong automatic one scatters speed changes through the piece and makes the sheet
   * unreadable. Frames are absolute wall clock, so a boundary never moves a note.
   */
  stretches: Stretch[];
}


/**
 * What each edit is called, on the two buttons and in their tooltips.
 *
 * A button that only says "Undo" asks a reader to remember what they last did, and on a page with
 * sixteen kinds of edit they often do not. One name per field, and a step that touches several
 * fields at once is named by the first of them — or explicitly, where that would read wrong.
 */
export const EDIT_LABELS: Readonly<Record<keyof SheetEdits, string>> = {
  keySignature: "Key signature",
  keyChanges: "Key of a stretch",
  clefChanges: "Clef of a stretch",
  ottavas: "Octave bracket",
  trills: "Trill",
  lyrics: "Words",
  cueRanges: "Small stretch",
  spacings: "Spacing",
  evenSpacings: "Even spacing",
  fingers: "Fingering",
  overrides: "Figure",
  beamBreaks: "Beam",
  beamJoins: "Beam",
  hiddenNotes: "Notes off the page",
  graceNotes: "Grace note",
  dropDecorative: "Decorative notes",
  annotationScale: "Mark size",
  lineSpacing: "Space between lines",
  noteSpacing: "Space between notes",
  staffGaps: "Line spread",
  stretches: "Speed change",
};

/** A piece nobody has read yet. Also what **Remove all** goes back to. */
export const NO_EDITS: SheetEdits = {
  keySignature: "C",
  keyChanges: [],
  clefChanges: [],
  ottavas: [],
  trills: [],
  lyrics: [],
  cueRanges: [],
  spacings: [],
  evenSpacings: [],
  fingers: {},
  overrides: {},
  beamBreaks: new Set<string>(),
  beamJoins: new Set<string>(),
  hiddenNotes: new Set<NoteRef>(),
  graceNotes: [],
  dropDecorative: false,
  annotationScale: 1,
  lineSpacing: DEFAULT_LINE_SPACING,
  noteSpacing: DEFAULT_NOTE_SPACING,
  staffGaps: [],
  stretches: [],
};

/**
 * The edits a saved reading carries, as the page holds them.
 *
 * The reading arrives as the baseline and not as a step: it is where the reader left off rather
 * than something they have just done.
 */
export function editsFromSaved(found: SavedRhythm): SheetEdits {
  return {
    keySignature: found.keySignature ?? "C",
    keyChanges: (found.keyChanges ?? []).map((change) => ({
      fromColumn: change.fromColumn,
      keySignature: change.keySignature as KeySignature,
    })),
    clefChanges: (found.clefChanges ?? []).map((change) => ({
      fromColumn: change.fromColumn,
      hand: change.hand === "left" ? ("left" as const) : ("right" as const),
      clef: change.clef as Clef,
    })),
    // Whatever the reader put there, and nothing when they put nothing. A reading saved
    // before brackets existed simply has none, which is now the same answer as any other
    // piece nobody has bracketed.
    ottavas: (found.ottavas ?? []).map((span) => ({
      kind: span.kind as OttavaKind,
      hand: span.hand === "left" ? ("left" as const) : ("right" as const),
      fromColumn: span.fromColumn,
      toColumn: span.toColumn,
      // Absent on a reading saved before a bracket could be hidden, which reads as drawn —
      // the same answer that reading was saved with.
      hidden: span.hidden ?? false,
    })),
    trills: found.trills ?? [],
    lyrics: found.lyrics ?? [],
    cueRanges: found.cueRanges ?? [],
    spacings: found.spacings ?? [],
    evenSpacings: (found.evenSpacings ?? []).map((run) => ({
      hand: run.hand === "left" ? ("left" as const) : ("right" as const),
      fromColumn: run.fromColumn,
      toColumn: run.toColumn,
      scale: run.scale,
    })),
    fingers: Object.fromEntries(
      (found.fingers ?? []).map((one) => [
        `${one.hand}:${one.startFrame}:${one.row}`,
        one.finger as FingerNumber,
      ]),
    ),
    overrides: Object.fromEntries(
      found.overrides.map((one) => [`${one.hand}:${one.startFrame}`, one.figure]),
    ),
    beamBreaks: new Set(found.beamBreaks.map((one) => `${one.hand}:${one.startFrame}`)),
    beamJoins: new Set((found.beamJoins ?? []).map((one) => `${one.hand}:${one.startFrame}`)),
    hiddenNotes: new Set((found.hiddenNotes ?? []).map((one) => `${one.startFrame}:${one.row}`)),
    graceNotes: found.graceNotes ?? [],
    dropDecorative: found.dropDecorative ?? false,
    annotationScale: found.annotationScale ?? 1,
    lineSpacing: found.lineSpacing ?? DEFAULT_LINE_SPACING,
    noteSpacing: found.noteSpacing ?? DEFAULT_NOTE_SPACING,
    staffGaps: found.staffGaps ?? [],
    stretches: found.speedChanges.map((change) => ({
      startFrame: change.startFrame,
      anchorMs: change.anchorMs,
    })),
  };
}

/** The marks that still have a note under them: what is drawn, and what is saved. */
export interface LiveMarks {
  ottavas: OttavaAnnotation[];
  beamBreaks: ReadonlySet<string>;
  beamJoins: ReadonlySet<string>;
  overrides: Record<string, FigureName>;
  fingers: Record<string, FingerNumber>;
  evenSpacings: EvenSpacingAnnotation[];
}

/** A note taken off the page, as the backend addresses it. */
export interface HiddenNote {
  startFrame: number;
  row: number;
}

/** The notes taken off the page, as the backend takes them. */
export function hiddenNotesOut(hiddenNotes: ReadonlySet<NoteRef>): HiddenNote[] {
  return [...hiddenNotes].map((ref) => {
    const [frame, row] = ref.split(":");
    return { startFrame: Number(frame), row: Number(row) };
  });
}

/**
 * The reading as `PUT /time/{uuid}/rhythm` takes it: the named gap, and every edit that still has
 * a note under it.
 */
export function savedRhythmOf(reading: {
  hand: HandChoice;
  frameMs: number;
  figure: FigureName;
  anchorMs: number;
  edits: SheetEdits;
  live: LiveMarks;
}): SavedRhythm {
  const { hand, frameMs, figure, anchorMs, edits, live } = reading;
  return {
    hand,
    frameMs,
    keySignature: edits.keySignature,
    keyChanges: edits.keyChanges.map((change) => ({
      fromColumn: change.fromColumn,
      keySignature: change.keySignature,
    })),
    clefChanges: edits.clefChanges.map((change) => ({
      hand: change.hand,
      fromColumn: change.fromColumn,
      clef: change.clef,
    })),
    anchorFigure: figure,
    anchorMs,
    speedChanges: edits.stretches.map((stretch) => ({
      startFrame: stretch.startFrame,
      anchorMs: stretch.anchorMs,
    })),
    overrides: Object.entries(live.overrides).map(([key, name]) => {
      const [side, frame] = key.split(":");
      // The row is not part of the key: an override belongs to a chord, not to one notehead, so
      // every note struck together takes it. Row 0 stands for "the group at this column".
      return {
        hand: side ?? "right",
        row: 0,
        startFrame: Number(frame),
        figure: name,
      };
    }),
    beamBreaks: [...live.beamBreaks].map((key) => {
      const [side, frame] = key.split(":");
      return { hand: side ?? "right", startFrame: Number(frame) };
    }),
    beamJoins: [...live.beamJoins].map((key) => {
      const [side, frame] = key.split(":");
      return { hand: side ?? "right", startFrame: Number(frame) };
    }),
    ottavas: live.ottavas.map((span) => ({
      kind: span.kind,
      hand: span.hand,
      fromColumn: span.fromColumn,
      toColumn: span.toColumn,
      // Whether the reader took the bracket off the page. The notes are written an octave from
      // where they sound either way, so a reading that lost this would come back with a wall of
      // dashed lines the reader had already decided against.
      hidden: span.hidden ?? false,
    })),
    spacings: edits.spacings.map((stretch) => ({
      fromColumn: stretch.fromColumn,
      toColumn: stretch.toColumn,
      scale: stretch.scale,
    })),
    evenSpacings: live.evenSpacings.map((run) => ({
      hand: run.hand,
      fromColumn: run.fromColumn,
      toColumn: run.toColumn,
      scale: run.scale,
    })),
    dropDecorative: edits.dropDecorative,
    hiddenNotes: hiddenNotesOut(edits.hiddenNotes),
    fingers: Object.entries(live.fingers).map(([noteKey, finger]) => ({
      hand: handOf(noteKey),
      startFrame: frameOf(noteKey),
      row: rowOf(noteKey),
      finger,
    })),
    trills: [...edits.trills],
    lyrics: [...edits.lyrics],
    cueRanges: [...edits.cueRanges],
    graceNotes: [...edits.graceNotes],
    annotationScale: edits.annotationScale,
    lineSpacing: edits.lineSpacing,
    noteSpacing: edits.noteSpacing,
    staffGaps: edits.staffGaps.map((one) => ({ fromColumn: one.fromColumn, gap: one.gap })),
  };
}
