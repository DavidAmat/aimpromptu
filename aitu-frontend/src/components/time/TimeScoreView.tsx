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
  type FingerAnnotation,
  type FingerNumber,
  type KeyChangeAnnotation,
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
import { palette, surface } from "../../ui";

export interface TimeScoreViewProps {
  score: TimeScorePayload;
  /**
   * Figures the reader set by hand, keyed `hand:startFrame`. They win over the score's own.
   *
   * Applied here rather than sent back for a rebuild, because that is all an override is: one glyph
   * drawn differently. Nothing moves, nothing is renumbered, no other note is touched.
   *
   * The one thing a named figure does take with it is the tresillo mark over the same chord — see
   * where the tuplets are gathered below.
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
   * Whether the recording is sounding.
   *
   * The page only follows the line onto a new stave while this is true. Following it at all times
   * sounds harmless and is not: dragging the scrub bar sweeps the line through a hundred staves in
   * a second, and each one scrolled the page, so the bar the reader was holding shot off the top of
   * the window and the drag became impossible to finish. Moving the recording without playing it is
   * something the reader is doing *to* the page, not something the page should chase.
   */
  followPlayhead?: boolean;
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
  /**
   * The live renderer, handed up whenever the sheet is rebuilt, and `null` when it goes.
   *
   * Printing needs it: a printed page has to carry over the widths this render measured and every
   * choice the reader made, and the renderer is the only thing that holds all of them together.
   * Handing the object up rather than adding a `print()` prop here keeps this view about drawing.
   */
  onRendererChange?: (renderer: GridNotationRenderer | null) => void;
  /**
   * A printed view: no note picking, no marked stretch, no toolbox. The playhead still moves.
   * Pointer events on the SVG are turned off so the ruler cannot start a selection either.
   */
  readOnly?: boolean;
  /** Dashed time lines above the staves. On unless the performance overlay turns them off. */
  showGuides?: boolean;
  /** Tresillo (and similar) marks. On unless the performance overlay turns them off. */
  showTuplets?: boolean;
  /** Finger numbers. On unless the performance overlay turns them off. */
  showFingers?: boolean;
}

export function TimeScoreView({
  score,
  overrides,
  beamBreaks,
  keySignature = "C",
  keyChanges,
  ottavas,
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
  followPlayhead = false,
  onScrub,
  scrollCursorAt,
  onRendererChange,
  readOnly = false,
  showGuides = true,
  showTuplets = true,
  showFingers = true,
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
  // One handle per end of the marked stretch. Positioned imperatively, like the playhead, because
  // they move with a render the host never asked for — a re-wrap, a change of width — and a React
  // state holding pixels would be a frame behind every one of them.
  const rangeFrom = useRef<HTMLDivElement | null>(null);
  const rangeTo = useRef<HTMLDivElement | null>(null);
  const [draggingEdge, setDraggingEdge] = useState<"from" | "to" | null>(null);
  const renderer = useRef<GridNotationRenderer | null>(null);
  // Held in a ref rather than listed as a dependency: a page that passes an inline function would
  // otherwise rebuild every note on every one of its own renders.
  const reportRenderer = useRef(onRendererChange);
  useEffect(() => {
    reportRenderer.current = onRendererChange;
  }, [onRendererChange]);
  const system = useRef<number | null>(null);

  /**
   * Put the two edge handles where the ends of the marked stretch are.
   *
   * The same arithmetic the playhead uses, run twice: a column is a slice of wall clock, so a
   * frame's place on the page is a lookup into the render rather than anything musical. Called
   * after every redraw as well as on every change of range, because a re-wrap moves both ends
   * without the range itself changing at all.
   */
  const placeRangeHandles = useCallback(() => {
    const render = renderer.current?.getLastRender();
    const range = latestRange.current;
    for (const [node, frame] of [
      [rangeFrom.current, range?.fromColumn],
      [rangeTo.current, range?.toColumn],
    ] as const) {
      if (!node) continue;
      const placement = render && frame !== undefined ? placeCursor(render, frame) : undefined;
      if (!placement) {
        node.style.display = "none";
        continue;
      }
      node.style.display = "block";
      node.style.left = `${(placement.x - GRAB_WIDTH / 2).toFixed(2)}px`;
      node.style.top = `${placement.topY.toFixed(2)}px`;
      node.style.height = `${placement.height.toFixed(2)}px`;
    }
  }, []);

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
    // A tresillo the reader has renamed is not a tresillo any more. Naming a figure by hand says
    // "draw it as this", and a 3 left over the group says the opposite — that the notes are not what
    // they are written as. So the mark goes with the change, and it goes for the whole group: a
    // bracket over two of three notes reads worse than no bracket at all. This is what makes
    // standardising a mixed passage onto one figure come out looking like one figure.
    const named = new Set(Object.keys(overrides ?? {}));
    const renamed = new Set<number>();
    for (const note of score.notes) {
      const staff = staffOf(note);
      if (!staff || note.tupletId === null || note.tupletId === undefined) continue;
      if (named.has(`${staff}:${note.startFrame}`)) renamed.add(note.tupletId);
    }

    const tuplets = new Map<string, { count: number; id: number }>();
    if (showTuplets) {
      for (const note of score.notes) {
        const staff = staffOf(note);
        if (!staff) continue;
        if (note.tuplet && note.tupletId !== null && note.tupletId !== undefined) {
          if (renamed.has(note.tupletId)) continue;
          tuplets.set(`${staff}:${note.startFrame}`, { count: note.tuplet, id: note.tupletId });
        }
      }
    }

    // One annotation per numbered notehead. They are grouped by hand and onset when they are drawn,
    // so a chord's numbers come out as one column without being asked to.
    const fingerAnnotations: FingerAnnotation[] = Object.entries(
      showFingers ? (fingers ?? {}) : {},
    ).map(
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
      // A step past the last column draws no interior dashed line, which is how the overlay
      // turns the guides off without a second drawing mode in the package.
      frameMeasure: showGuides ? score.layout.frameMeasure : score.envelope.frameCount + 1,
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
      interactive: readOnly ? false : Boolean(onSelectNote ?? onSelectNotes),
      onSelectionChange: (keys) => {
        if (readOnly) return;
        onSelectNote?.(keys[0] ?? null);
        onSelectNotes?.(keys);
      },
      onFrameRangeSelect: readOnly ? undefined : (range) => onSelectRange?.(range),
      rangeMarkers: !readOnly,
      onRangeMarkerSelect: readOnly
        ? undefined
        : (marker) =>
            onSelectMarkedRange?.({
              kind: marker.kind,
              label: marker.label,
              fromColumn: marker.fromColumn,
              toColumn: marker.toColumn,
            }),
    });

    renderer.current = drawn;
    reportRenderer.current?.(drawn);
    if (latestRange.current) drawn.setSelectedRange(latestRange.current);
    placeRangeHandles();

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

    // No bracket is proposed here. `suggestOttavas` is still exported by the drawing package and
    // still tested there, but nothing in this app calls it: since P8.6 charged the hand split for
    // the ledger lines it forces onto the page, a passage stranded far outside its own staff is
    // rare enough that an automatic bracket is more often wrong than right, and a bracket the
    // reader did not ask for is one they have to notice and clear. The Octave pill in the frame
    // toolbox is how one gets added.

    return () => {
      renderer.current = null;
      reportRenderer.current?.(null);
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
    onSelectNote,
    onSelectNotes,
    onSelectRange,
    onSelectMarkedRange,
    availableWidth,
    placeRangeHandles,
    readOnly,
    showGuides,
    showTuplets,
    showFingers,
  ]);

  useEffect(() => {
    latestRange.current = selectedRange;
    if (selectedRange) renderer.current?.setSelectedRange(selectedRange);
    placeRangeHandles();
  }, [placeRangeHandles, selectedRange]);

  useEffect(() => {
    if (clearSelectionsAt === undefined) return;
    latestRange.current = null;
    renderer.current?.setSelectedRange(undefined);
    renderer.current?.clearSelection();
    placeRangeHandles();
  }, [clearSelectionsAt, placeRangeHandles]);

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

    // Only while it is playing, and then only when the music moves to another line. Scrolling on
    // every tick would fight the reader; scrolling while they are scrubbing takes the bar away from
    // under their pointer. The index is still recorded when not following, so resuming does not
    // jump on the first tick for a line the reader is already looking at.
    const moved = placement.systemIndex !== system.current;
    system.current = placement.systemIndex;
    if (moved && followPlayhead) {
      marker.scrollIntoView?.({ block: "nearest", inline: "nearest" });
    }
  }, [followPlayhead, playheadSeconds, score.envelope.frameMs]);

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

  /** Which frame a pointer is over, as a whole column. */
  const frameAt = useCallback((event: React.PointerEvent<HTMLDivElement>): number | undefined => {
    const render = renderer.current?.getLastRender();
    const box = stage.current?.getBoundingClientRect();
    if (!render || !box) return undefined;
    const frames = frameAtPoint(render, event.clientX - box.left, event.clientY - box.top);
    return frames === undefined ? undefined : Math.round(frames);
  }, []);

  /**
   * Move one end of the marked stretch to the frame under the pointer.
   *
   * The ends are clamped apart rather than allowed to cross. A range that inverted would read as
   * empty everywhere downstream — no key change, no octave bracket, nothing to apply — and the
   * reader would have no way of telling that from a bug.
   */
  const dragEdge = (event: React.PointerEvent<HTMLDivElement>, edge: "from" | "to") => {
    const range = latestRange.current;
    if (!range || !onSelectRange) return;
    const frame = frameAt(event);
    if (frame === undefined) return;
    const next =
      edge === "from"
        ? { fromColumn: Math.min(Math.max(0, frame), range.toColumn - 1), toColumn: range.toColumn }
        : {
            fromColumn: range.fromColumn,
            toColumn: Math.max(range.fromColumn + 1, Math.min(frame, score.envelope.frameCount)),
          };
    if (next.fromColumn === range.fromColumn && next.toColumn === range.toColumn) return;
    onSelectRange(next);
  };

  const startEdgeDrag = (event: React.PointerEvent<HTMLDivElement>, edge: "from" | "to") => {
    if (!onSelectRange || event.button !== 0) return;
    event.preventDefault();
    event.stopPropagation();
    event.currentTarget.setPointerCapture?.(event.pointerId);
    setDraggingEdge(edge);
  };

  const continueEdgeDrag = (event: React.PointerEvent<HTMLDivElement>, edge: "from" | "to") => {
    if (draggingEdge !== edge) return;
    event.preventDefault();
    dragEdge(event, edge);
  };

  const endEdgeDrag = (event: React.PointerEvent<HTMLDivElement>) => {
    if (!draggingEdge) return;
    event.currentTarget.releasePointerCapture?.(event.pointerId);
    setDraggingEdge(null);
  };

  /**
   * Double-click a blank part of the page and the recording goes there.
   *
   * Almost every pixel of a stave already means something — a notehead picks a note, a group cell
   * picks a stretch of columns, the two range handles and the playhead are grabbed — and one
   * gesture cannot mean two things. What is left over is the strip above the top stave, the gaps
   * between systems and the margins, which is where a reader points when they mean "here" and
   * nothing else. So the seek is the *second* click on ground that is otherwise inert: a single
   * click there can go on meaning nothing, and no existing gesture changes.
   *
   * The page does not scroll afterwards. The reader is looking at the place they just pointed at;
   * moving them to it would only take that place away.
   */
  const seekOnDoubleClick = (event: React.MouseEvent<HTMLDivElement>) => {
    if (!onScrub) return;
    const target = event.target as Element | null;
    if (target?.closest?.(INERT_TO_SEEK)) return;
    const render = renderer.current?.getLastRender();
    const box = stage.current?.getBoundingClientRect();
    if (!render || !box) return;
    const frames = frameAtPoint(render, event.clientX - box.left, event.clientY - box.top);
    if (frames === undefined) return;
    onScrub((frames * score.envelope.frameMs) / 1000);
  };

  return (
    <Box sx={{ width: "100%", overflowX: "auto" }}>
      <Box
        ref={stage}
        onDoubleClick={seekOnDoubleClick}
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
        <Box ref={host} sx={readOnly ? { pointerEvents: "none" } : undefined} />

        {/*
          The two ends of the marked stretch, as things you can take hold of.
          A range is made by clicking groups, and a group is about a second — far coarser than the
          note a reader is usually aiming at. These let each end be pulled to any frame afterwards,
          so "up to that redonda and no further" is expressible. They are drawn over the sheet
          rather than inside it because only this component knows where a frame is on the page.
        */}
        {([
          ["from", rangeFrom, "Drag to move where the marked stretch starts"],
          ["to", rangeTo, "Drag to move where the marked stretch ends"],
        ] as const).map(([edge, nodeRef, title]) => (
          <Box
            key={edge}
            ref={nodeRef}
            data-range-edge={edge}
            onPointerDown={(event) => startEdgeDrag(event, edge)}
            onPointerMove={(event) => continueEdgeDrag(event, edge)}
            onPointerUp={endEdgeDrag}
            onPointerCancel={endEdgeDrag}
            title={onSelectRange ? title : undefined}
            sx={{
              position: "absolute",
              display: "none",
              width: `${GRAB_WIDTH}px`,
              zIndex: 2,
              pointerEvents: onSelectRange ? "auto" : "none",
              cursor: onSelectRange ? (draggingEdge === edge ? "ew-resize" : "col-resize") : "default",
              touchAction: "none",
              "&:hover .aitu-range-edge, & .aitu-range-edge[data-dragging='true']": {
                opacity: 1,
                width: "3px",
              },
              "&:hover .aitu-range-grip, & .aitu-range-grip[data-dragging='true']": {
                opacity: 1,
                transform: "scale(1.25)",
              },
            }}
          >
            <Box
              className="aitu-range-edge"
              data-dragging={draggingEdge === edge ? "true" : "false"}
              sx={{
                position: "absolute",
                top: 0,
                bottom: 0,
                left: `${GRAB_WIDTH / 2 - 1}px`,
                width: "2px",
                backgroundColor: palette.dark.Lavender,
                opacity: 0.85,
                transition: "opacity 120ms, width 120ms",
              }}
            />
            {/*
              A square, not a circle: the playhead's grip is round, and the two are often within a
              few pixels of each other. The shape is what says which one you are about to grab.
            */}
            <Box
              className="aitu-range-grip"
              data-dragging={draggingEdge === edge ? "true" : "false"}
              sx={{
                position: "absolute",
                top: "-5px",
                left: `${GRAB_WIDTH / 2 - 5}px`,
                width: "10px",
                height: "10px",
                borderRadius: "2px",
                backgroundColor: palette.dark.Lavender,
                border: 1,
                borderColor: surface.panel,
                opacity: 0.85,
                transition: "opacity 120ms, transform 120ms",
              }}
            />
          </Box>
        ))}

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
 * Everything on the page that already answers to a click, and so must not also seek.
 *
 * Listed rather than inferred: a double-click lands on whatever is under the pointer, and the
 * honest test for "is this blank" is "is it none of the things that mean something".
 */
const INERT_TO_SEEK = [
  ".grid-frame-range",
  ".grid-note-target",
  ".grid-notehead",
  ".grid-range-marker-hit",
  ".grid-range-marker-arm",
  ".grid-frame-timestamp",
  "[data-staff-gap-handle]",
  "[data-range-edge]",
].join(", ");

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
