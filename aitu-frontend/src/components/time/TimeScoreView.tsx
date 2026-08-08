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
import { GridNotationRenderer, placeCursor, type SparseMatrix } from "@aimpromptu/grid-notation";
import type { FigureName, TimeScorePayload } from "../../api";

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
  /** A notehead was clicked, as `hand:startFrame:row`. */
  onSelectNote?: (noteKey: string | null) => void;
  /** A stretch of the piece was selected on the ruler above the staves. */
  onSelectRange?: (range: { fromColumn: number; toColumn: number }) => void;
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
  onSelectNote,
  onSelectRange,
  availableWidth,
  playheadSeconds,
}: TimeScoreViewProps) {
  const host = useRef<HTMLDivElement | null>(null);
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
      keySignature: "C",
      staves: score.layout.hideLeftHand || score.layout.hideRightHand ? "single" : "grand",
      matrixEnvelope: {
        sparse: true,
        // Metadata the older reader still expects. Nothing downstream reads them for this score:
        // the figures arrive named and the positions come from the columns.
        tempoBpm: 60,
        timeStepSeconds: score.envelope.frameMs / 1000,
        granularity: "semicorchea",
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
      interactive: Boolean(onSelectNote),
      onSelectionChange: (keys) => onSelectNote?.(keys[0] ?? null),
      onFrameRangeSelect: (range) => onSelectRange?.(range),
    });

    renderer.current = drawn;
    return () => {
      renderer.current = null;
      drawn.destroy?.();
    };
  }, [score, overrides, beamBreaks, onSelectNote, onSelectRange, availableWidth]);

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
