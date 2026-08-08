/**
 * The staff, drawn from a wall-clock score.
 *
 * The figures come from the backend, note by note, and this view passes them straight through. It
 * does not work out what a note should be called from how many columns it covers, because a column
 * is a slice of time and says nothing about note values. That is the whole point of the change: the
 * position and the figure are two separate numbers now.
 */

import { useEffect, useRef } from "react";
import Box from "@mui/material/Box";
import {
  GridNotationRenderer,
  placeCursor,
  suggestKeySignature,
  type KeyChangeAnnotation,
  type SparseMatrix,
} from "@aimpromptu/grid-notation";
import type { FigureName, KeySignatureName, TimeScorePayload } from "../../api";

export interface TimeScoreViewProps {
  score: TimeScorePayload;
  /**
   * Figures the reader set by hand, keyed `hand:startFrame`. They win over the score's own.
   *
   * Applied here rather than sent back for a rebuild, because that is all an override is: one glyph
   * drawn differently. Nothing moves, nothing is renumbered, no other note is touched.
   */
  overrides?: Readonly<Record<string, FigureName>>;
  /**
   * Notes the reader asked to start a new beam, keyed `hand:startFrame`.
   *
   * Beaming groups what is regular, and a long arpeggio has nothing regular in it to cut at — so it
   * comes out as one shapeless slope. Where the phrase restarts is a reading of the music, not a
   * property of it, and this is where the reader's answer goes in.
   */
  beamBreaks?: ReadonlySet<string>;
  /**
   * Where the piece leaves the main signature and what it changes to, keyed by column.
   *
   * A transition rather than a range, so two edits can never disagree about what is sounding at a
   * given column. Giving a passage its own key writes two of them: one where it starts and one
   * where the piece goes back to what it was.
   */
  keyChanges?: readonly KeyChangeAnnotation[];
  /**
   * The stretch of columns picked on the ruler, so the highlight survives a redraw.
   *
   * The renderer owns the selection while it lives, but every change to the sheet builds a new one,
   * and a highlight that disappeared when you gave the passage a key would look like the selection
   * had been lost.
   */
  selectedRange?: { fromColumn: number; toColumn: number } | null;
  /**
   * Bumped by the host to drop every selection, both the stretch of columns and the notes.
   *
   * A number rather than a function call, because this component owns the drawn score and the page
   * owns the decision. Pressing Escape, or closing a toolbox, raises it.
   */
  clearSelectionsAt?: number;
  /** A notehead was clicked, as `hand:startFrame:row`. */
  onSelectNote?: (noteKey: string | null) => void;
  /**
   * Every notehead currently selected, as `hand:startFrame:row`.
   *
   * Click one, then hold Command (Control on Windows) and click others to add them. A finger
   * number or a stem direction belongs to a set of notes rather than to one, so the toolbox that
   * edits them has to know the whole set.
   */
  onSelectNotes?: (noteKeys: readonly string[]) => void;
  /** A stretch of the piece was selected on the ruler above the staves. */
  onSelectRange?: (range: { fromColumn: number; toColumn: number }) => void;
  /**
   * The signature the whole piece is written in. C when nobody has chosen.
   *
   * A transcription has no key: the recording says which keys were pressed and nothing about how
   * they should be spelled. In C every black key prints its own accidental, so a piece in five
   * flats comes out covered in them and is hard to read. Choosing the signature moves those
   * accidentals into the clef, where a player reads them once.
   *
   * It changes spelling and nothing else. No note moves, no figure changes, and the recording is
   * untouched.
   */
  keySignature?: KeySignatureName;
  /**
   * Which signature would print the fewest accidentals, and how many that would save.
   *
   * Reported rather than applied. A key is the reader's decision, and a count of accidentals is
   * only evidence for it: a piece can genuinely be written in a key that costs a few more.
   */
  onKeySuggestion?: (suggestion: { best: KeySignatureName; saved: number } | null) => void;
  /** Falls back to the container width when the layout has not settled yet. */
  availableWidth?: number;
  /**
   * Where the recording is, in seconds. Draws a line down the staves at that moment.
   *
   * A second is turned into a column by dividing, because a column is a fixed slice of wall clock
   * and nothing about the music is involved. The line then interpolates inside the column, so it
   * arrives at each note when the note sounds even though columns are not all the same width.
   *
   * Leave it out, or pass `null`, and no line is drawn.
   */
  playheadSeconds?: number | null;
}

export function TimeScoreView({
  score,
  overrides,
  beamBreaks,
  keySignature = "C",
  keyChanges,
  selectedRange,
  clearSelectionsAt,
  onKeySuggestion,
  onSelectNote,
  onSelectNotes,
  onSelectRange,
  availableWidth,
  playheadSeconds,
}: TimeScoreViewProps) {
  const host = useRef<HTMLDivElement | null>(null);
  // The stretch of columns is read when the score is built rather than watched, so picking one
  // never rebuilds the sheet. It is restored after a rebuild the sheet had to do for another
  // reason, which is what keeps the dashed outline on screen while a toolbox is open.
  const latestRange = useRef(selectedRange);
  const playhead = useRef<HTMLDivElement | null>(null);
  const renderer = useRef<GridNotationRenderer | null>(null);
  const system = useRef<number | null>(null);

  useEffect(() => {
    const container = host.current;
    if (!container) return;
    container.replaceChildren();

    const figures = new Map<string, string>();
    for (const note of score.notes) {
      figures.set(`${note.hand}:${note.startFrame}`, VEXFLOW_FIGURE[note.figure]);
    }
    for (const [key, figure] of Object.entries(overrides ?? {})) {
      figures.set(key, VEXFLOW_FIGURE[figure]);
    }

    // Which notes are a tresillo. Three notes filling the time the ladder gives to two have no
    // figure in a vocabulary of halves, so they carry an ordinary one and the 3 over them says the
    // rest. Without the mark a reader would play them as written and be wrong.
    const tuplets = new Map<string, { count: number; id: number }>();
    for (const note of score.notes) {
      if (note.tuplet && note.tupletId !== null && note.tupletId !== undefined) {
        tuplets.set(`${note.hand}:${note.startFrame}`, { count: note.tuplet, id: note.tupletId });
      }
    }

    const drawn = new GridNotationRenderer(container, {
      frameCount: score.envelope.frameCount,
      // A column is `frameMs` of wall clock. The renderer only uses this to turn a column into a
      // moment for the timestamps; nothing about the music is derived from it.
      timeStepSeconds: score.envelope.frameMs / 1000,
      availableWidth: availableWidth ?? container.clientWidth ?? 900,
      // No fixed column width on purpose. Left to itself the renderer makes each column as wide as
      // what is drawn in it, so a column where nothing starts collapses to a sliver and a long
      // silence takes a short space. Distance on the page then reads as how much is happening,
      // which is what a wall-clock grid is for. Setting `pixelsPerFrame` turns that off.
      keySignature,
      // Where the piece leaves that signature. The package draws the whole transition: naturals
      // cancelling the outgoing sharps or flats, both clefs again, then the incoming signature.
      annotations: { keyChanges: [...(keyChanges ?? [])] },
      staves: score.layout.hideLeftHand || score.layout.hideRightHand ? "single" : "grand",
      // The two wall-clock levels above the column. A dashed line every `frameMeasure` columns
      // says where the page is in time; a selection snaps to `frameGroup` columns, which is the
      // unit a passage is drawn in. Neither means anything musical.
      frameGroup: score.layout.frameGroup,
      frameMeasure: score.layout.frameMeasure,
      // What each passage prints above the staff where it starts, in place of a tempo mark.
      passageHeaders: score.passages.map((passage) => ({
        startFrame: passage.startFrame,
        label: passage.headerLabel,
      })),
      matrixEnvelope: {
        sparse: true,
        // A column is this many milliseconds, and that is the whole of what the header says about
        // time. It used to carry a tempo and a granularity code as well, which the drawing package
        // no longer has anywhere to put.
        frameMs: score.envelope.frameMs,
        matrixProcessingStep: "two-hands",
        rMatrix: score.envelope.rMatrix as SparseMatrix,
        lMatrix: score.envelope.lMatrix as SparseMatrix,
      },
      printedFigureFor: (hand: string, onsetFrame: number) =>
        figures.get(`${hand}:${onsetFrame}`) as never,
      tupletFor: (hand: string, onsetFrame: number) => tuplets.get(`${hand}:${onsetFrame}`),
      beamBreakAt: (hand: string, onsetFrame: number) =>
        beamBreaks?.has(`${hand}:${onsetFrame}`) ?? false,
      // Beams on. A run of short notes reads as one gesture, and the beam is what says so; a row
      // of separate flags reads as loose notes however evenly they were played.
      beamGroups: true,
      // No rests (D-16). Distance on this page is time, so a silence is already the space it takes
      // and the dashed lines crossing it. A rest glyph says the same thing again, in a note value
      // the rest of the page never uses.
      rests: false,
      showTimestamps: false,
      observeResize: true,
      interactive: Boolean(onSelectNote ?? onSelectNotes),
      onSelectionChange: (keys) => {
        onSelectNote?.(keys[0] ?? null);
        onSelectNotes?.(keys);
      },
      onFrameRangeSelect: (range) => onSelectRange?.(range),
    });

    renderer.current = drawn;
    if (latestRange.current) drawn.setSelectedRange(latestRange.current);

    // What the notes themselves suggest, measured on the same spelling rule the page prints with,
    // so the number reported is the ink actually saved rather than a second opinion about it.
    const music = drawn.getMusic();
    if (music && onKeySuggestion) {
      const ranked = suggestKeySignature(music, {
        fromColumn: 0,
        toColumn: score.envelope.frameCount,
        activeKeySignature: keySignature,
      });
      const best = ranked.candidates[0];
      onKeySuggestion(
        best && best.keySignature !== keySignature
          ? { best: best.keySignature, saved: ranked.savedAgainstActive ?? 0 }
          : null,
      );
    }

    return () => {
      renderer.current = null;
      drawn.destroy?.();
    };
  }, [
    score,
    overrides,
    beamBreaks,
    keySignature,
    keyChanges,
    onKeySuggestion,
    onSelectNote,
    onSelectNotes,
    onSelectRange,
    availableWidth,
  ]);

  useEffect(() => {
    latestRange.current = selectedRange;
    if (selectedRange) renderer.current?.setSelectedRange(selectedRange);
  }, [selectedRange]);

  useEffect(() => {
    if (clearSelectionsAt === undefined) return;
    renderer.current?.setSelectedRange(undefined);
    renderer.current?.clearSelection();
  }, [clearSelectionsAt]);

  // The line is moved rather than redrawn. At sixty ticks a second a full re-render would rebuild
  // every note sixty times to move one line a few pixels, which is the whole cost of the page.
  useEffect(() => {
    const marker = playhead.current;
    const drawn = renderer.current;
    if (!marker) return;

    const render = drawn?.getLastRender();
    if (playheadSeconds === null || playheadSeconds === undefined || !render) {
      marker.style.display = "none";
      return;
    }

    const frames = (playheadSeconds * 1000) / score.envelope.frameMs;
    const placement = placeCursor(render, frames);
    if (!placement) {
      marker.style.display = "none";
      return;
    }

    marker.style.display = "block";
    marker.style.left = `${placement.x.toFixed(2)}px`;
    marker.style.top = `${placement.topY.toFixed(2)}px`;
    marker.style.height = `${placement.height.toFixed(2)}px`;

    // Only when the music moves to another line. Scrolling on every tick would fight the reader.
    if (placement.systemIndex !== system.current) {
      system.current = placement.systemIndex;
      marker.scrollIntoView?.({ block: "nearest", inline: "nearest" });
    }
  }, [playheadSeconds, score.envelope.frameMs]);

  return (
    <Box sx={{ width: "100%", overflowX: "auto" }}>
      <Box sx={{ position: "relative", display: "inline-block", minWidth: "100%" }}>
        <Box ref={host} />
        <Box
          ref={playhead}
          sx={{
            position: "absolute",
            display: "none",
            width: "2px",
            borderRadius: "1px",
            bgcolor: "primary.main",
            opacity: 0.75,
            pointerEvents: "none",
          }}
        />
      </Box>
    </Box>
  );
}

/**
 * The Spanish figure names the backend sends, in the English names the drawing package uses.
 *
 * Two vocabularies for the same nine things. The backend's is the one the sheet and the reader use;
 * the package's predates the change and is renamed there later.
 */
const VEXFLOW_FIGURE: Record<string, string> = {
  redonda: "whole",
  blanca: "half",
  dottedBlanca: "dottedHalf",
  negra: "quarter",
  dottedNegra: "dottedQuarter",
  corchea: "eighth",
  semicorchea: "sixteenth",
  fusa: "thirtysecond",
  semifusa: "sixtyfourth",
};

export default TimeScoreView;
