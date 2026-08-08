/**
 * The staff, drawn from a wall-clock score.
 *
 * The figures come from the backend, note by note, and this view passes them straight through. It
 * does not work out what a note should be called from how many columns it covers, because a column
 * is a slice of time and says nothing about note values. That is the whole point of the change: the
 * position and the figure are two separate numbers now.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Box from "@mui/material/Box";
import {
  frameAtPoint,
  GridNotationRenderer,
  placeCursor,
  suggestKeySignature,
  suggestOttavas,
  type FingerAnnotation,
  type FingerNumber,
  type KeyChangeAnnotation,
  type KeySignature,
  type OttavaAnnotation,
  type SparseMatrix,
} from "@aimpromptu/grid-notation";
import type { FigureName, KeySignatureName, TimeScorePayload } from "../../api";
import {
  applyRenderOverrides,
  NO_RENDER_OVERRIDES,
  type NoteRef,
  type RenderOverrides,
} from "../../music/renderOverrides";

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
   * Where a hand is written an octave or two from where it sounds, and how far.
   *
   * A passage far outside its own staff prints as a stack of ledger lines that nobody counts
   * accurately; under a bracket it prints inside the staff and the bracket says how to read it. The
   * spans are held by the page, not worked out here, so the reader can clear or change any of them.
   */
  ottavas?: readonly OttavaAnnotation[];
  /**
   * Notes the reader took off the page and notes they sent to the other staff.
   *
   * Folded into a copy of the matrix here, one step before it is drawn. Neither is an edit: the
   * recording still says a key went down, and dropping the pair restores the note exactly, because
   * nothing was ever taken away from the score this view was handed.
   */
  renderOverrides?: RenderOverrides;
  /**
   * Which finger plays each note, keyed `hand:startFrame:row` by the staff the note is drawn on.
   *
   * Several notes of one chord each carry their own, and the drawing package stacks them over the
   * chord in the order of the noteheads, which is how fingering is printed.
   */
  fingers?: Readonly<Record<string, FingerNumber>>;
  /** Told when a move could not be made because the far staff already holds that key. */
  onMovesRefused?: (refused: readonly NoteRef[]) => void;
  /**
   * The brackets this score would ask for, reported once the music has been read.
   *
   * Reported rather than applied, for the same reason a key signature is: the engraver deciding it
   * on its own is what made the old implementation impossible to override (D38). The page seeds
   * itself from this the first time it sees a score and owns them from then on.
   */
  onOttavaSuggestion?: (spans: OttavaAnnotation[]) => void;
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
   * A corner mark was clicked, so the stretch it belongs to should be selected again.
   *
   * Every stretch carrying markup draws two corners in its own colour, at the top and the bottom of
   * the system. They are there so a reader can see where a thing they applied begins and ends
   * without selecting anything, and so they can get back to it: the corners are the handle.
   */
  onSelectMarkedRange?: (marker: {
    kind: string;
    label: string;
    fromColumn: number;
    toColumn: number;
  }) => void;
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
  /**
   * The cursor was dragged to a new moment, in seconds. Move the recording there.
   *
   * Leave it out and the cursor is not draggable, which is what a printed view wants.
   */
  onScrub?: (seconds: number) => void;
  /**
   * Bumped by the page to bring the cursor on screen — pressing space, or clicking the progress bar.
   *
   * A number rather than a call, because the page decides *when* and this view is the only thing
   * that knows *where*: the cursor is placed from a render only this component holds.
   */
  scrollCursorAt?: number;
}

export function TimeScoreView({
  score,
  overrides,
  beamBreaks,
  keySignature = "C",
  keyChanges,
  ottavas,
  onOttavaSuggestion,
  renderOverrides = NO_RENDER_OVERRIDES,
  fingers,
  onMovesRefused,
  selectedRange,
  clearSelectionsAt,
  onKeySuggestion,
  onSelectNote,
  onSelectNotes,
  onSelectRange,
  onSelectMarkedRange,
  availableWidth,
  playheadSeconds,
  onScrub,
  scrollCursorAt,
}: TimeScoreViewProps) {
  const host = useRef<HTMLDivElement | null>(null);
  // The positioned box the score is drawn into. Both the cursor's placement and a drag over it are
  // measured from its top-left corner, which is also the SVG's, so the two agree with no offset.
  const stage = useRef<HTMLDivElement | null>(null);
  const [dragging, setDragging] = useState(false);
  // The stretch of columns is read when the score is built rather than watched, so picking one
  // never rebuilds the sheet. It is restored after a rebuild the sheet had to do for another
  // reason, which is what keeps the dashed outline on screen while a toolbox is open.
  const latestRange = useRef(selectedRange);
  const playhead = useRef<HTMLDivElement | null>(null);
  const renderer = useRef<GridNotationRenderer | null>(null);
  const system = useRef<number | null>(null);

  // The page edits, folded into a copy of the matrix. Memoised because it walks every cell and the
  // playhead effect below runs sixty times a second.
  const drawnMatrix = useMemo(
    () =>
      applyRenderOverrides(
        score.envelope.rMatrix as SparseMatrix,
        score.envelope.lMatrix as SparseMatrix,
        renderOverrides,
      ),
    [score.envelope.rMatrix, score.envelope.lMatrix, renderOverrides],
  );

  useEffect(() => {
    if (drawnMatrix.refused.length > 0) onMovesRefused?.(drawnMatrix.refused);
  }, [drawnMatrix, onMovesRefused]);

  useEffect(() => {
    const container = host.current;
    if (!container) return;
    container.replaceChildren();

    // Where each note is actually drawn. A note the reader sent to the other staff takes its figure
    // and its tuplet mark with it, or the page would print the glyph on one staff and name it on
    // the other. Notes that are off the page name nothing.
    const staffOf = (note: { hand: string; startFrame: number; row: number }): string | null =>
      drawnMatrix.handOf.get(`${note.startFrame}:${note.row}`) ?? null;

    const figures = new Map<string, string>();
    for (const note of score.notes) {
      const staff = staffOf(note);
      if (!staff) continue;
      // First one wins. A moved note joining a chord that is already on the far staff reads as part
      // of that chord, and a chord has one figure.
      const key = `${staff}:${note.startFrame}`;
      if (!figures.has(key)) figures.set(key, VEXFLOW_FIGURE[note.figure]);
    }
    for (const [key, figure] of Object.entries(overrides ?? {})) {
      figures.set(key, VEXFLOW_FIGURE[figure]);
    }

    // Which notes are a tresillo. Three notes filling the time the ladder gives to two have no
    // figure in a vocabulary of halves, so they carry an ordinary one and the 3 over them says the
    // rest. Without the mark a reader would play them as written and be wrong.
    const tuplets = new Map<string, { count: number; id: number }>();
    for (const note of score.notes) {
      const staff = staffOf(note);
      if (!staff) continue;
      if (note.tuplet && note.tupletId !== null && note.tupletId !== undefined) {
        tuplets.set(`${staff}:${note.startFrame}`, { count: note.tuplet, id: note.tupletId });
      }
    }

    // One annotation per numbered notehead. They are grouped by hand and onset when they are drawn,
    // so a chord's numbers come out as one column without being asked to.
    const fingerAnnotations: FingerAnnotation[] = Object.entries(fingers ?? {}).map(
      ([noteKey, finger]) => {
        const [staff, startFrame, row] = noteKey.split(":");
        const column = Number(startFrame);
        return {
          anchor: {
            hand: staff === "left" ? "left" : "right",
            columns: { fromColumn: column, toColumn: column + 1 },
            rows: [Number(row)],
          },
          finger,
        };
      },
    );

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
      annotations: {
        keyChanges: [...(keyChanges ?? [])],
        // Octave brackets, which take a passage out of the ledger lines and into the staff.
        ottavas: [...(ottavas ?? [])],
        fingers: fingerAnnotations,
      },
      staves: score.layout.hideLeftHand || score.layout.hideRightHand ? "single" : "grand",
      // The two wall-clock levels above the column. A dashed line every `frameMeasure` columns
      // says where the page is in time; a selection snaps to `frameGroup` columns, which is the
      // unit a passage is drawn in. Neither means anything musical.
      frameGroup: score.layout.frameGroup,
      frameMeasure: score.layout.frameMeasure,
      // The room the empty columns of one group share. Silence is charged per group and not per
      // column, so a stretch of long notes stays compact instead of spreading across the page.
      silenceGroupPx: score.layout.silenceGroupPx,
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
        rMatrix: drawnMatrix.rMatrix,
        lMatrix: drawnMatrix.lMatrix,
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
      // Two corners per marked stretch, each pair in its own colour so two overlapping stretches
      // are told apart, and clickable so a reader can pick one up again without hunting for it.
      rangeMarkers: true,
      onRangeMarkerSelect: (marker) =>
        onSelectMarkedRange?.({
          kind: marker.kind,
          label: marker.label,
          fromColumn: marker.fromColumn,
          toColumn: marker.toColumn,
        }),
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

    // What the register asks for, measured against the staff each hand actually prints on. Reported
    // on every rebuild; the page keeps the first answer and its own edits after that.
    if (music && onOttavaSuggestion) {
      onOttavaSuggestion(
        suggestOttavas(music, { keySignature: (keySignature ?? "C") as KeySignature }),
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
    drawnMatrix,
    fingers,
    keySignature,
    keyChanges,
    ottavas,
    onKeySuggestion,
    onOttavaSuggestion,
    onSelectNote,
    onSelectNotes,
    onSelectRange,
    onSelectMarkedRange,
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
    // The strip is `GRAB_WIDTH` wide with the line down its middle, so it is offset by half of that
    // to keep the line itself exactly on the moment.
    marker.style.left = `${(placement.x - GRAB_WIDTH / 2).toFixed(2)}px`;
    marker.style.top = `${placement.topY.toFixed(2)}px`;
    marker.style.height = `${placement.height.toFixed(2)}px`;

    // Only when the music moves to another line. Scrolling on every tick would fight the reader.
    if (placement.systemIndex !== system.current) {
      system.current = placement.systemIndex;
      marker.scrollIntoView?.({ block: "nearest", inline: "nearest" });
    }
  }, [playheadSeconds, score.envelope.frameMs]);

  // Bring the cursor on screen because the page asked — space, or a click on the progress bar. The
  // recording may be four minutes down a page that wraps a hundred times, and playing something the
  // reader cannot see is the same as not playing it.
  useEffect(() => {
    if (scrollCursorAt === undefined) return;
    const marker = playhead.current;
    if (!marker || marker.style.display === "none") return;
    marker.scrollIntoView?.({ block: "center", inline: "center", behavior: "smooth" });
  }, [scrollCursorAt]);

  /** Where a pointer is, as a moment in the recording. */
  const secondsAt = useCallback(
    (event: React.PointerEvent<HTMLDivElement>): number | undefined => {
      const render = renderer.current?.getLastRender();
      const box = stage.current?.getBoundingClientRect();
      if (!render || !box) return undefined;
      const frames = frameAtPoint(render, event.clientX - box.left, event.clientY - box.top);
      return frames === undefined ? undefined : (frames * score.envelope.frameMs) / 1000;
    },
    [score.envelope.frameMs],
  );

  // Grab the cursor and it follows the pointer; let go and the recording is there. Dragging *the
  // cursor* rather than clicking anywhere on the sheet, because a click on the sheet already means
  // something — it picks a notehead or a stretch of columns — and one gesture cannot mean both.
  //
  // Pointer capture is what makes a drag that leaves the two-pixel line keep working, and it is
  // also what lets the drag go *down* onto another system: the page wraps, so the moment a reader
  // wants is often on a line below rather than to the right.
  const startDrag = (event: React.PointerEvent<HTMLDivElement>) => {
    if (!onScrub || event.button !== 0) return;
    event.preventDefault();
    event.stopPropagation();
    event.currentTarget.setPointerCapture?.(event.pointerId);
    setDragging(true);
    const seconds = secondsAt(event);
    if (seconds !== undefined) onScrub(seconds);
  };

  const continueDrag = (event: React.PointerEvent<HTMLDivElement>) => {
    if (!dragging || !onScrub) return;
    event.preventDefault();
    const seconds = secondsAt(event);
    if (seconds !== undefined) onScrub(seconds);
  };

  const endDrag = (event: React.PointerEvent<HTMLDivElement>) => {
    if (!dragging) return;
    event.currentTarget.releasePointerCapture?.(event.pointerId);
    setDragging(false);
  };

  return (
    <Box sx={{ width: "100%", overflowX: "auto" }}>
      <Box
        ref={stage}
        sx={{
          position: "relative",
          display: "inline-block",
          minWidth: "100%",
          // The sheet is a drawing. Without this, shift-clicking a second group of columns makes
          // the browser select everything between the two clicks and paint it in the highlight
          // colour, which looks like an error until the next click clears it.
          userSelect: "none",
        }}
      >
        <Box ref={host} />
        <Box
          ref={playhead}
          onPointerDown={startDrag}
          onPointerMove={continueDrag}
          onPointerUp={endDrag}
          onPointerCancel={endDrag}
          title={onScrub ? "Drag to move the recording — sideways, or down onto another line" : undefined}
          sx={{
            position: "absolute",
            display: "none",
            width: `${GRAB_WIDTH}px`,
            // The line is two pixels wide and a hand is not. The strip around it is what makes the
            // cursor catchable without widening the line itself, which has to stay exactly on the
            // moment it marks.
            pointerEvents: onScrub ? "auto" : "none",
            cursor: onScrub ? (dragging ? "grabbing" : "grab") : "default",
            touchAction: "none",
            "&:hover .aitu-cursor-line, & .aitu-cursor-line[data-dragging='true']": {
              opacity: 1,
              width: "4px",
              marginLeft: "-1px",
            },
            "&:hover .aitu-cursor-grip, & .aitu-cursor-grip[data-dragging='true']": {
              opacity: 1,
            },
          }}
        >
          <Box
            className="aitu-cursor-line"
            data-dragging={dragging ? "true" : "false"}
            sx={{
              position: "absolute",
              top: 0,
              bottom: 0,
              left: `${GRAB_WIDTH / 2 - 1}px`,
              width: "2px",
              borderRadius: "1px",
              bgcolor: "primary.main",
              opacity: 0.75,
              transition: "width 120ms, opacity 120ms",
            }}
          />
          {/* The handle. Something round to aim at says "this one moves" without a tooltip. */}
          <Box
            className="aitu-cursor-grip"
            data-dragging={dragging ? "true" : "false"}
            sx={{
              position: "absolute",
              top: "-5px",
              left: `${GRAB_WIDTH / 2 - 5}px`,
              width: "10px",
              height: "10px",
              borderRadius: "50%",
              bgcolor: "primary.main",
              opacity: dragging ? 1 : 0,
              transition: "opacity 120ms",
            }}
          />
        </Box>
      </Box>
    </Box>
  );
}

/** How wide the invisible strip around the cursor is, in pixels. Two is a line; this is a target. */
const GRAB_WIDTH = 14;

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
