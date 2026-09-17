/**
 * The staff, drawn from a wall-clock score.
 *
 * The figures come from the backend, note by note, and this view passes them straight through. It
 * does not work out what a note should be called from how many columns it covers, because a column
 * is a slice of time and says nothing about note values. That is the whole point of the change: the
 * position and the figure are two separate numbers now.
 */

import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import Box from "@mui/material/Box";
import {
  frameAtPoint,
  GridNotationRenderer,
  placeCursor,
  suggestKeySignature,
  suggestOttavas,
  GRAND_STAFF_TOP_PADDING,
  GRAND_STAFF_TOP_PADDING_BARE,
  SYSTEM_ROOM,
  type SpacingAnnotation,
  type StaffGapOverride,
  type ClefChangeAnnotation,
  type EvenSpacingAnnotation,
  type FingerAnnotation,
  type FingerNumber,
  type KeyChangeAnnotation,
  type GraceNoteAnnotation,
  type LyricAnnotation,
  type OttavaAnnotation,
  type OttavaResizeChange,
  type PassageAnnotation,
  type LyricLayoutChange,
  type SparseMatrix,
  type TrillAnnotation,
} from "@aimpromptu/grid-notation";
import type {
  CueRange,
  FigureName,
  GraceNote,
  KeySignatureName,
  LyricLine,
  TimeScorePayload,
  Trill,
} from "../../api";
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
   * Notes the reader asked to keep inside the beam they are in, keyed `hand:startFrame`.
   *
   * The other half of `beamBreaks`. The page cuts a beam where a run turns over at its lowest note,
   * which is right for an arpeggio and wrong for a scale that happens to dip; this is the reader
   * saying so. It stands down only that one rule — a beam still never crosses a key change, a clef
   * change or a tuplet boundary, because those are not guesses.
   */
  beamJoins?: ReadonlySet<string>;
  /**
   * Where the piece leaves the main signature and what it changes to, keyed by column.
   *
   * A transition rather than a range, so two edits can never disagree about what is sounding at a
   * given column. Giving a passage its own key writes two of them: one where it starts and one
   * where the piece goes back to what it was.
   */
  keyChanges?: readonly KeyChangeAnnotation[];
  /**
   * Where one hand starts printing a different clef, keyed by column.
   *
   * A transition rather than a range, for the same reason the key changes are: at any column each
   * hand prints exactly one clef, so two edits cannot disagree about what is on the page.
   *
   * It is the honest answer to a hand that spends a passage far outside its own staff, and a better
   * one than an octave bracket where the passage is long: under a bracket the notes are written an
   * octave from where they sound and the reader has to keep the bracket in mind, while on the other
   * clef they are written exactly where they sound.
   */
  clefChanges?: readonly ClefChangeAnnotation[];
  /**
   * Where a hand is written an octave or two from where it sounds, and how far.
   *
   * A passage far outside its own staff prints as a stack of ledger lines that nobody counts
   * accurately; under a bracket it prints inside the staff and the bracket says how to read it. The
   * spans are held by the page, not worked out here, so the reader can clear or change any of them.
   */
  ottavas?: readonly OttavaAnnotation[];
  /**
   * The reader pulled one end of an octave bracket and let go.
   *
   * Reported once, when the pointer is up, so the sheet is rebuilt once per gesture rather than
   * once per pixel of it — the same rule the lyric blocks and the two range handles follow. Leave
   * it out and a bracket is drawn with nothing to take hold of, which is what a printed view wants.
   */
  onOttavaResize?: (change: OttavaResizeChange) => void;
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
  selectedRange?: {
    fromColumn: number;
    toColumn: number;
    /** The one staff the stretch is about, when the reader has narrowed it to a hand. */
    hand?: "right" | "left";
  } | null;
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
  /**
   * A stretch of the piece was selected on the ruler above the staves.
   *
   * `adjusting` is set when the reader is dragging one end of a stretch that is already marked,
   * rather than starting a new one. The two look identical from here and are not the same thing to
   * a host: a new stretch is a place to open a panel beside, and an adjustment is a panel that is
   * already open and must stay where the reader put it.
   */
  onSelectRange?: (
    range: { fromColumn: number; toColumn: number },
    options?: { adjusting?: boolean },
  ) => void;
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
    /** `single` for a key change or a line of words, which belong to the piece and not to a staff. */
    hand: string;
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
  /**
   * The octave brackets the notes themselves ask for: a run of three or more chords written three
   * ledger lines or more outside its staff, grouped under one bracket rather than one per note.
   *
   * Reported rather than applied, like the key. The page decides when to take them.
   */
  onOttavaSuggestion?: (spans: OttavaAnnotation[]) => void;
  /** Stretches the reader set wider or narrower than the page would set them. */
  spacings?: readonly SpacingAnnotation[];
  /**
   * Runs of one hand's notes the reader asked to have set an equal distance apart.
   *
   * A column belongs to the whole system, so a run of even corcheas in one hand is drawn unevenly
   * whenever the other hand needs room at some of those moments. That is truthful and reads as a
   * mistake in the playing. This is the reader choosing evenness and paying for it in width.
   *
   * Driven through a setter, like the two spacings above: the plus and minus beside the equals sign
   * are pressed repeatedly while the reader watches the page.
   */
  evenSpacings?: readonly EvenSpacingAnnotation[];
  /**
   * How much white space there is between the staves of one line and the staves of the next, in
   * pixels. Nought puts them directly under each other.
   *
   * **This is not the package's `systemGap`, and the difference is the whole point.** A system is
   * not its staves: over them is a strip that holds the frame numbers, under them room for a lyric
   * and its extender, and a band at each end for the corner marks. `systemGap` is the distance
   * between two of those boxes, so at `systemGap: 0` the lines are still `SYSTEM_ROOM` — some 160
   * pixels — apart, which is more white than the staves are tall. A reader asked for a number and
   * got a number that did nothing they could see.
   *
   * So the number here is the white space itself, and the room is taken off before it is handed
   * over. Room a lyric or an octave bracket needs is added back by the drawing, because the words
   * live in it.
   *
   * Driven through the renderer's own setter rather than through the build below, because the
   * sheet is rebuilt whenever anything the build depends on changes, and dragging a slider would
   * otherwise rebuild every note on every pixel of the drag.
   */
  lineSpacing?: number;
  /**
   * Extra pixels between one note and the next, everywhere on the page.
   *
   * The twin of `lineSpacing`, one axis over, and driven through a setter for the same reason: the
   * sheet is rebuilt whenever anything the build depends on changes, and dragging a slider must not
   * rebuild every note on every pixel of the drag.
   *
   * It is charged to the columns that carry a note and to no others, so the notes open up while the
   * silences keep exactly the width the wall clock gives them. Scaling every column instead would
   * be a zoom, and would stretch the one thing this page already says well.
   */
  noteSpacing?: number;
  /**
   * Lines the reader has spread wider or narrower than the rest, keyed by a column inside each.
   *
   * The handle between the two staves of a line writes one of these. It used to set one number for
   * the whole page, so opening out a line to fit a wide chord opened out every line on the score.
   *
   * Held by the page rather than by the renderer, and for the usual reason: the renderer is rebuilt
   * whenever the music or an annotation changes, and anything it alone remembered would be lost on
   * the reader's next edit.
   */
  staffGaps?: readonly StaffGapOverride[];
  /** Told when the reader drags a line's handle, so the page can keep the answer and save it. */
  onStaffGapsChange?: (staffGaps: StaffGapOverride[]) => void;
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
  /**
   * The column number over each guide — `f0`, `f100`.
   *
   * An address rather than notation. It is what every mark on this page is keyed by and it is how
   * a reader says where something is, so it has to be reachable; it is also fifty-two of the sixty
   * pixels above every staff, spent on numbers that mean nothing musically. Off is the better
   * resting state and the page has a switch for it.
   *
   * The dashed guides and the cells a reader clicks to mark a stretch are unaffected.
   */
  showFrameLabels?: boolean;
  /** Tresillo (and similar) marks. On unless the performance overlay turns them off. */
  showTuplets?: boolean;
  /** Finger numbers. On unless the performance overlay turns them off. */
  showFingers?: boolean;
  /**
   * Stretches printed as one held note with `tr` over them.
   *
   * The alternations are already off the page by the time the score arrives — they are taken out
   * on the backend, before any figure is named, because the printed length of a note is the gap to
   * the next onset in the same hand. All that is left to do here is print the mark.
   */
  trills?: readonly Trill[];
  /**
   * Lines of words over a stretch of columns, drawn above the right hand.
   *
   * Each one carries where the reader put it and how wide and how large it is drawn, because those
   * are decisions about the piece: a line of three words over eight seconds and a whole sentence
   * over one need different answers, and no rule has them.
   */
  lyrics?: readonly LyricLine[];
  /**
   * The reader dragged a lyric's block somewhere, or pulled its right edge in.
   *
   * Reported once, when the pointer is let go, so the sheet is rebuilt once per gesture rather
   * than once per pixel of it. Leave it out and the blocks are drawn where they are stored and
   * cannot be moved, which is what a printed view wants.
   */
  onLyricLayoutChange?: (change: LyricLayoutChange) => void;
  /** Stretches printed smaller than the rest of the page. */
  cueRanges?: readonly CueRange[];
  /**
   * Small notes leaning on a note of the music.
   *
   * Drawn in the annotation layer and not in the music, because a grace note takes no column:
   * nothing about the spacing of the page is measured from it, and adding one moves no note.
   */
  graceNotes?: readonly GraceNote[];
  /** Words under the staff. On unless the performance overlay turns them off. */
  showLyrics?: boolean;
  /**
   * How large the marks over and under the staff are drawn, as a multiple of their normal size.
   *
   * One piece can be dense enough that fingering crowds it and another airy enough that the same
   * numbers are hard to read, so the size belongs to the piece rather than to the app.
   */
  annotationScale?: number;
  /**
   * How large the whole sheet is drawn, as a multiple of its natural size. 1 is the natural size.
   *
   * A magnifier and **not** a change to the music: the drawing is scaled on screen, so no column
   * is re-measured, the page does not re-wrap, and not one note moves relative to another. It is
   * for working on a crowded passage — picking one notehead out of a chord, putting the end of a
   * stretch on the right column — where the page at its natural size is smaller than a pointer is
   * accurate.
   *
   * One is the floor, because the natural size is already the page laid out for the window: there
   * is nothing to see by drawing it smaller than the layout it was measured for.
   */
  zoom?: number;
  /**
   * The reader zoomed with Command and the wheel. Leave it out and the wheel does nothing.
   *
   * The number is held by the page rather than here, so the page can show it and put it back.
   */
  onZoomChange?: (zoom: number) => void;
}

export function TimeScoreView({
  score,
  overrides,
  beamBreaks,
  beamJoins,
  keySignature = "C",
  keyChanges,
  clefChanges,
  ottavas,
  onOttavaResize,
  renderOverrides = NO_RENDER_OVERRIDES,
  fingers,
  onMovesRefused,
  selectedRange,
  clearSelectionsAt,
  onKeySuggestion,
  onOttavaSuggestion,
  spacings,
  evenSpacings,
  lineSpacing = DEFAULT_LINE_SPACING,
  noteSpacing = DEFAULT_NOTE_SPACING,
  staffGaps,
  onStaffGapsChange,
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
  showFrameLabels = true,
  showTuplets = true,
  showFingers = true,
  trills,
  lyrics,
  cueRanges,
  graceNotes,
  showLyrics = true,
  annotationScale = 1,
  onLyricLayoutChange,
  zoom = MIN_ZOOM,
  onZoomChange,
}: TimeScoreViewProps) {
  const host = useRef<HTMLDivElement | null>(null);
  // The box the sheet scrolls inside. The wheel is listened for here and the horizontal scroll is
  // put back here, so the point under the pointer stays under it while the page grows.
  const scroller = useRef<HTMLDivElement | null>(null);
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
  /**
   * How large the sheet is drawn, held where the drag handlers can read it without being rebuilt.
   *
   * Every measurement taken from the page — which second a pointer is over, which column, where a
   * lyric was dropped — is in the drawing's own units, and a magnified page reports screen pixels.
   * Dividing by this is the whole of the correction.
   */
  const heldZoom = useRef(zoom);
  useEffect(() => {
    heldZoom.current = zoom;
  }, [zoom]);
  // What the drawing measures at its natural size, so the box it scrolls in can be made as large
  // as the magnified drawing actually is. Read off the layout, which a transform does not change.
  const [naturalSize, setNaturalSize] = useState<{ width: number; height: number } | null>(null);
  // Where the pointer was when the reader last turned the wheel, so the page can be scrolled back
  // under it once the new size is laid out.
  const zoomAnchor = useRef<{ u: number; v: number; clientX: number; clientY: number } | null>(
    null,
  );
  // Held in a ref for the same reason `onRendererChange` is: a page passing an inline function
  // would otherwise tear down and rebuild every note on each of its own renders.
  const reportLyricLayout = useRef(onLyricLayoutChange);
  useEffect(() => {
    reportLyricLayout.current = onLyricLayoutChange;
  }, [onLyricLayoutChange]);
  // Held in a ref rather than listed as a dependency: a page that passes an inline function would
  // otherwise rebuild every note on every one of its own renders.
  const reportRenderer = useRef(onRendererChange);
  useEffect(() => {
    reportRenderer.current = onRendererChange;
  }, [onRendererChange]);
  const reportStaffGaps = useRef(onStaffGapsChange);
  useEffect(() => {
    reportStaffGaps.current = onStaffGapsChange;
  }, [onStaffGapsChange]);
  // And once more for the octave brackets. Held in a ref for the same reason as the three above:
  // the sheet is rebuilt whenever anything the build depends on changes, and an inline handler
  // would make every one of the page's own renders a rebuild of every note.
  const reportOttavaResize = useRef(onOttavaResize);
  useEffect(() => {
    reportOttavaResize.current = onOttavaResize;
  }, [onOttavaResize]);
  const system = useRef<number | null>(null);
  // The gap the sheet should be drawn with, readable from the build effect without being a
  // dependency of it. The effect below is what applies a change to it.
  const gapNow = useRef(lineSpacing);
  // The same again for the lines the reader has spread: read by the build, driven by the effect
  // below, and never a dependency of the build itself.
  const spreadNow = useRef(staffGaps);
  // And once more for how far apart the notes stand, and for the stretches the reader has opened
  // out. Same shape, same reason: a handle being dragged must not rebuild the page it is moving.
  const noteRoomNow = useRef(noteSpacing);
  const rangeRoomNow = useRef(spacings);
  const evenRoomNow = useRef(evenSpacings);

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

    // `tr` over the note that was left standing where the alternations were, and a wavy line
    // running to where the shake stops. The note itself is already one held note by the time the
    // score arrives; this is the mark above it, and the wave is the half of it that says how long.
    const trillMarks: TrillAnnotation[] = (trills ?? []).map((trill) => ({
      anchor: {
        hand: trill.hand,
        columns: { fromColumn: trill.startFrame, toColumn: trill.endFrame },
        rows: [trill.row],
      },
    }));

    // Words belong to the piece rather than to a staff, so they are anchored `single`. They are
    // drawn above the right hand, in a block of their own at the top of the system: that is where
    // a singer reads them, and it is the one place on the page that an octave bracket — whose
    // height comes from the highest note it covers — can never reach.
    const lyricAnnotations: LyricAnnotation[] = (showLyrics ? (lyrics ?? []) : []).map((line) => ({
      anchor: {
        hand: "single",
        columns: { fromColumn: line.fromColumn, toColumn: line.toColumn },
        rows: [],
      },
      text: line.text,
      // Where the reader put the block, how wide they left it and how large the words are. All
      // three are left out where nobody has said, which is the drawing package's own default.
      ...(line.offsetX === undefined ? {} : { offsetX: line.offsetX }),
      ...(line.offsetY === undefined ? {} : { offsetY: line.offsetY }),
      ...(line.width === undefined ? {} : { width: line.width }),
      ...(line.fontSize === undefined ? {} : { fontSize: line.fontSize }),
    }));

    const cuePassages: PassageAnnotation[] = (cueRanges ?? []).map((cue) => ({
      kind: "cue-size",
      anchor: {
        hand: cue.hand === "left" ? "left" : cue.hand === "right" ? "right" : "single",
        columns: { fromColumn: cue.fromColumn, toColumn: cue.toColumn },
        rows: [],
      },
      options: {},
    }));

    const graceAnnotations: GraceNoteAnnotation[] = (graceNotes ?? []).map((grace) => ({
      anchor: {
        hand: grace.hand,
        columns: { fromColumn: grace.startFrame, toColumn: grace.startFrame + 1 },
        rows: [grace.targetRow],
      },
      row: grace.row,
      kind: grace.kind,
    }));

    const drawn = new GridNotationRenderer(container, {
      frameCount: score.envelope.frameCount,
      // A column is `frameMs` of wall clock. The renderer only uses this to turn a column into a
      // moment for the timestamps; nothing about the music is derived from it.
      timeStepSeconds: score.envelope.frameMs / 1000,
      availableWidth: availableWidth ?? container.clientWidth ?? 900,
      // Read from a ref rather than listed below, so a change to it never rebuilds the sheet.
      systemGap: systemGapFor(gapNow.current, showFrameLabels),
      staffGaps: spreadNow.current,
      // Read from a ref for the same reason the gap above is.
      noteSpacingPx: noteRoomNow.current,
      onStaffGapsChange: (changed) => reportStaffGaps.current?.(changed),
      // No fixed column width on purpose. Left to itself the renderer makes each column as wide as
      // what is drawn in it, so a column where nothing starts collapses to a sliver and a long
      // silence takes a short space. Distance on the page then reads as how much is happening,
      // which is what a wall-clock grid is for. Setting `pixelsPerFrame` turns that off.
      keySignature,
      // Where the piece leaves that signature. The package draws the whole transition: naturals
      // cancelling the outgoing sharps or flats, both clefs again, then the incoming signature.
      annotations: {
        keyChanges: [...(keyChanges ?? [])],
        // Where a hand leaves the clef it normally reads. The package draws the whole transition:
        // a thin barline, then the incoming clef on that staff alone.
        clefChanges: [...(clefChanges ?? [])],
        // Octave brackets, which take a passage out of the ledger lines and into the staff.
        ottavas: [...(ottavas ?? [])],
        fingers: fingerAnnotations,
        // The shakes, the words under the staff, and the stretches printed small.
        trills: trillMarks,
        lyrics: lyricAnnotations,
        passages: cuePassages,
        graceNotes: graceAnnotations,
        // Read from a ref, like the two spacings above it, so dragging the Spacing handle moves the
        // page instead of rebuilding it.
        spacings: [...(rangeRoomNow.current ?? [])],
        evenSpacings: [...(evenRoomNow.current ?? [])],
      },
      // How large every mark over and under the staff is drawn. One number rather than one per
      // kind: a reader crowding a dense passage wants all of them smaller, not the numbers only.
      annotationScale,
      staves: score.layout.hideLeftHand || score.layout.hideRightHand ? "single" : "grand",
      // The two wall-clock levels above the column. A dashed line every `frameMeasure` columns
      // says where the page is in time; a selection snaps to `frameGroup` columns, which is the
      // unit a passage is drawn in. Neither means anything musical.
      frameGroup: score.layout.frameGroup,
      // A step past the last column draws no interior dashed line, which is how the overlay
      // turns the guides off without a second drawing mode in the package.
      frameMeasure: showGuides ? score.layout.frameMeasure : score.envelope.frameCount + 1,
      frameLabels: showFrameLabels,
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
      beamJoinAt: (hand: string, onsetFrame: number) =>
        beamJoins?.has(`${hand}:${onsetFrame}`) ?? false,
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
      // A range now starts where the reader pointed and runs for one group, so the last group of
      // the piece can name a column past the end. Held here, where the piece's length is known.
      onFrameRangeSelect: readOnly
        ? undefined
        : (range) =>
            onSelectRange?.({
              ...range,
              toColumn: Math.min(range.toColumn, score.envelope.frameCount),
            }),
      // The corners stay: a pair per marked stretch, in its own colour, is how a reader sees which
      // stretches carry an edit without selecting any of them, and the way back to one.
      rangeMarkers: !readOnly,
      // They no longer outline the stretch they belong to when one of them is hovered — that is
      // gone from the package, not switched off here, so nothing can bring it back by accident.
      // A lyric's block is dragged in the drawing itself and reported here once, when the pointer
      // is let go — so a reader moving one is not rebuilding the page on every pixel of it.
      onLyricLayout: readOnly
        ? undefined
        : (change) => reportLyricLayout.current?.(change),
      onRangeMarkerSelect: readOnly
        ? undefined
        : (marker) =>
            onSelectMarkedRange?.({
              kind: marker.kind,
              label: marker.label,
              hand: String(marker.hand),
              fromColumn: marker.fromColumn,
              toColumn: marker.toColumn,
            }),
      // Either end of an octave bracket can be pulled to bring more columns under it or fewer.
      // Reported once, when the pointer is let go; the band and the dashed line follow the pointer
      // in the drawing itself in the meantime.
      onOttavaResize: readOnly
        ? undefined
        : (change) => reportOttavaResize.current?.(change),
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

    // The brackets the notes ask for, reported and not applied. Three ledger lines is where a
    // reader starts counting instead of reading, and a run of three or more chords up there is a
    // passage worth one bracket; a single stray note is read faster as a note. The page takes the
    // proposal when the reader has never decided about brackets, or when asked to.
    if (music && onOttavaSuggestion) {
      onOttavaSuggestion(
        suggestOttavas(music, { keySignature, minLedgerLines: 3, minRunLength: 3 }),
      );
    }

    return () => {
      renderer.current = null;
      reportRenderer.current?.(null);
      drawn.destroy?.();
    };
  }, [
    score,
    overrides,
    beamBreaks,
    beamJoins,
    drawnMatrix,
    fingers,
    keySignature,
    keyChanges,
    clefChanges,
    ottavas,
    onKeySuggestion,
    onOttavaSuggestion,
    onSelectNote,
    onSelectNotes,
    onSelectRange,
    onSelectMarkedRange,
    availableWidth,
    placeRangeHandles,
    readOnly,
    showGuides,
    showFrameLabels,
    trills,
    lyrics,
    cueRanges,
    graceNotes,
    showLyrics,
    annotationScale,
    showTuplets,
    showFingers,
  ]);

  /**
   * The space between lines, applied to the drawing that is already there.
   *
   * The sheet is laid out again, so the two range handles have to be put back where they belong —
   * they are placed against the last render rather than from React state, and that render has just
   * been replaced. The playhead is the same, and the effect below this one does it, because it
   * lists the spacing too and effects run in the order they are written.
   */
  useEffect(() => {
    gapNow.current = lineSpacing;
    const drawn = renderer.current;
    if (!drawn) return;
    drawn.setSystemGap(systemGapFor(lineSpacing, showFrameLabels));
    placeRangeHandles();
  }, [lineSpacing, showFrameLabels, placeRangeHandles]);

  /**
   * The lines the reader has spread, applied to the drawing that is already there.
   *
   * Through the renderer's own setter for the same reason the spacing above is: a line the reader
   * drags open must not tear down and rebuild every note on the page to show it. Taking one back
   * with Command-Z comes through here too.
   */
  /**
   * How far apart the notes stand, applied to the drawing that is already there.
   *
   * Through the renderer's own setter, like the space between lines — but this one is horizontal,
   * so the columns are measured again and the page may wrap somewhere else. The handles and the
   * playhead are placed against the last render, which has just been replaced, so both are put back.
   */
  useEffect(() => {
    noteRoomNow.current = noteSpacing;
    const drawn = renderer.current;
    if (!drawn) return;
    drawn.setNoteSpacing(noteSpacing);
    placeRangeHandles();
  }, [noteSpacing, placeRangeHandles]);

  /**
   * The stretches the reader has opened out or closed up, applied to the drawing already there.
   *
   * Through the renderer's own setter, like the two spacings above. It is horizontal, so the
   * columns are measured again and the page may wrap somewhere else — which is why the handles go
   * back where they belong afterwards.
   */
  useEffect(() => {
    rangeRoomNow.current = spacings;
    const drawn = renderer.current;
    if (!drawn) return;
    drawn.setSpacings(spacings ?? []);
    placeRangeHandles();
  }, [spacings, placeRangeHandles]);

  /** The runs set an equal distance apart, applied to the drawing already there. */
  useEffect(() => {
    evenRoomNow.current = evenSpacings;
    const drawn = renderer.current;
    if (!drawn) return;
    drawn.setEvenSpacings(evenSpacings ?? []);
    placeRangeHandles();
  }, [evenSpacings, placeRangeHandles]);

  useEffect(() => {
    spreadNow.current = staffGaps;
    const drawn = renderer.current;
    if (!drawn) return;
    drawn.setStaffGaps(staffGaps ?? []);
    placeRangeHandles();
  }, [staffGaps, placeRangeHandles]);

  /**
   * The stretch the host has marked, kept on the drawing that is already there.
   *
   * Cleared as well as set. Dropping the stretch used to leave its band painted until something
   * raised `clearSelectionsAt`, which drops *every* selection — and that is one half too much for a
   * host handing the stretch over to the noteheads under it, which is exactly what the two
   * **Select notes** / **Select frames** buttons do. A host that asks for no stretch gets none.
   */
  useEffect(() => {
    latestRange.current = selectedRange;
    renderer.current?.setSelectedRange(selectedRange ?? undefined);
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
  }, [
    followPlayhead,
    playheadSeconds,
    score.envelope.frameMs,
    lineSpacing,
    noteSpacing,
    spacings,
    evenSpacings,
    staffGaps,
  ]);

  /**
   * Command and the wheel magnifies the sheet, around whatever the pointer is over.
   *
   * A native listener rather than React's `onWheel`, because the browser's own page zoom is on the
   * same gesture and only a listener registered as non-passive is allowed to call `preventDefault`
   * and take it. Control is accepted as well as Command: that is what a trackpad pinch sends, and
   * it is the same gesture on a mouse in Windows.
   *
   * Nothing about the score changes. The drawing is scaled, so no column is measured again, the
   * page does not wrap somewhere else, and every mark stays exactly over the note it is about.
   */
  useEffect(() => {
    const box = scroller.current;
    if (!box || !onZoomChange) return;
    const onWheel = (event: WheelEvent): void => {
      if (!event.metaKey && !event.ctrlKey) return;
      event.preventDefault();
      const stageBox = stage.current?.getBoundingClientRect();
      const now = heldZoom.current || 1;
      // Exponential, so one notch of the wheel is the same proportion of the page whatever size it
      // is already at — which is what makes a long zoom feel even instead of racing at the top.
      const next = clampZoom(now * Math.exp(-event.deltaY * ZOOM_PER_WHEEL_PIXEL));
      if (next === now) return;
      if (stageBox) {
        zoomAnchor.current = {
          u: (event.clientX - stageBox.left) / now,
          v: (event.clientY - stageBox.top) / now,
          clientX: event.clientX,
          clientY: event.clientY,
        };
      }
      onZoomChange(next);
    };
    box.addEventListener("wheel", onWheel, { passive: false });
    return () => box.removeEventListener("wheel", onWheel);
  }, [onZoomChange]);

  /**
   * Put the page back under the pointer after a zoom.
   *
   * Without it the sheet grows from its top-left corner, so the passage the reader was looking at
   * slides away from them and the gesture is useless for the one thing it is for — working on a
   * crowded stretch. The horizontal scroll belongs to the box the sheet is in and the vertical one
   * to the document, so both are moved by however far the anchor point drifted.
   */
  useLayoutEffect(() => {
    const want = zoomAnchor.current;
    zoomAnchor.current = null;
    const stageBox = stage.current?.getBoundingClientRect();
    const box = scroller.current;
    if (!want || !stageBox || !box) return;
    box.scrollLeft += stageBox.left + want.u * zoom - want.clientX;
    const page = document.scrollingElement ?? document.documentElement;
    page.scrollTop += stageBox.top + want.v * zoom - want.clientY;
  }, [zoom]);

  /**
   * How large the drawing is at its natural size, so the box it scrolls in can hold the magnified
   * one. `offsetWidth` and `offsetHeight` are layout, which a transform does not change — which is
   * exactly why they are the right numbers to multiply.
   */
  useEffect(() => {
    const node = host.current;
    if (!node || typeof ResizeObserver === "undefined") return;
    const measure = (): void =>
      setNaturalSize((current) =>
        current?.width === node.offsetWidth && current?.height === node.offsetHeight
          ? current
          : { width: node.offsetWidth, height: node.offsetHeight },
      );
    const observer = new ResizeObserver(measure);
    observer.observe(node);
    measure();
    return () => observer.disconnect();
  }, []);

  // Bring the cursor on screen because the page asked — space, or a click on the progress bar. The
  // recording may be four minutes down a page that wraps a hundred times, and playing something the
  // reader cannot see is the same as not playing it.
  useEffect(() => {
    if (scrollCursorAt === undefined) return;
    const marker = playhead.current;
    if (!marker || marker.style.display === "none") return;
    marker.scrollIntoView?.({ block: "center", inline: "center", behavior: "smooth" });
  }, [scrollCursorAt]);

  /**
   * A point on the screen, in the drawing's own units.
   *
   * The stage is what carries the magnification, so its box on screen is the magnified one: a
   * distance measured inside it is that many screen pixels and this many drawing units. Every
   * measurement taken from a pointer goes through here, which is the whole of what makes a
   * magnified page click in the right place.
   */
  const drawingPoint = useCallback(
    (clientX: number, clientY: number): { x: number; y: number } | undefined => {
      const box = stage.current?.getBoundingClientRect();
      if (!box) return undefined;
      const scale = heldZoom.current || 1;
      return { x: (clientX - box.left) / scale, y: (clientY - box.top) / scale };
    },
    [],
  );

  /** Where a pointer is, as a moment in the recording. */
  const secondsAt = useCallback(
    (event: React.PointerEvent<HTMLDivElement>): number | undefined => {
      const point = drawingPoint(event.clientX, event.clientY);
      const render = renderer.current?.getLastRender();
      if (!render || !point) return undefined;
      const frames = frameAtPoint(render, point.x, point.y);
      return frames === undefined ? undefined : (frames * score.envelope.frameMs) / 1000;
    },
    [drawingPoint, score.envelope.frameMs],
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
  const frameAt = useCallback(
    (event: React.PointerEvent<HTMLDivElement>): number | undefined => {
      const point = drawingPoint(event.clientX, event.clientY);
      const render = renderer.current?.getLastRender();
      if (!render || !point) return undefined;
      const frames = frameAtPoint(render, point.x, point.y);
      return frames === undefined ? undefined : Math.round(frames);
    },
    [drawingPoint],
  );

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
    // The stretch already exists and the reader is pulling one of its ends. Said so explicitly, or
    // the host cannot tell this apart from a fresh selection — and it moved its panel on every
    // pixel of the drag, into the very stretch being dragged out.
    onSelectRange(next, { adjusting: true });
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
    const point = drawingPoint(event.clientX, event.clientY);
    if (!render || !point) return;
    const frames = frameAtPoint(render, point.x, point.y);
    if (frames === undefined) return;
    onScrub((frames * score.envelope.frameMs) / 1000);
  };

  // The magnified drawing takes more room than its layout does, because a transform is not layout.
  // This is the box that claims it, so the page below the sheet is pushed down instead of being
  // drawn over and the sheet can be scrolled sideways to its far end.
  const magnified =
    zoom === MIN_ZOOM || !naturalSize
      ? undefined
      : {
          width: `${(naturalSize.width * zoom).toFixed(0)}px`,
          height: `${(naturalSize.height * zoom).toFixed(0)}px`,
        };

  return (
    <Box ref={scroller} sx={{ width: "100%", overflowX: "auto" }}>
      <Box sx={magnified}>
        <Box
          ref={stage}
          onDoubleClick={seekOnDoubleClick}
          sx={{
            position: "relative",
            display: "inline-block",
            minWidth: magnified ? 0 : "100%",
            // The magnifier. Everything inside scales together — the staves, the playhead and the two
            // range handles — so a handle stays exactly on the column it marks and nothing has to be
            // placed twice. From the top-left corner, so the scroll arithmetic above has one origin.
            ...(magnified
              ? { transform: `scale(${zoom})`, transformOrigin: "top left" }
              : {}),
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
    </Box>
  );
}

/** How wide the invisible strip around the cursor is, in pixels. Two is a line; this is a target. */
const GRAB_WIDTH = 14;

/**
 * The two ends of the magnifier, and how fast the wheel moves it.
 *
 * One is the floor because the natural size is already the page laid out for this window: drawing
 * it smaller would show no more music, only a smaller version of the same lines. Four is as far up
 * as a page stays worth scrolling.
 */
export const MIN_ZOOM = 1;
export const MAX_ZOOM = 4;
const ZOOM_PER_WHEEL_PIXEL = 0.0025;

function clampZoom(zoom: number): number {
  if (!Number.isFinite(zoom)) return MIN_ZOOM;
  return Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, zoom));
}

/**
 * White space between the staves of one line and the staves of the next, before anybody asks.
 *
 * Rather less than the package's own, which leaves the lines further apart than the staves are
 * tall. Exported so the page's slider and this view cannot disagree about where the middle of the
 * range is.
 */
export const DEFAULT_LINE_SPACING = 72;
export const MIN_LINE_SPACING = 0;
export const MAX_LINE_SPACING = 240;

/**
 * Extra room between one note and the next, before anybody asks.
 *
 * Nought: the page's own measurement is a reasonable answer, and it is the one every sheet drawn
 * before this control existed was set at. Exported so the page's slider and this view cannot
 * disagree about where the ends of the range are.
 */
export const DEFAULT_NOTE_SPACING = 0;
export const MIN_NOTE_SPACING = 0;
export const MAX_NOTE_SPACING = 48;

/**
 * The white space a reader asked for, as the gap between system boxes that the package draws with.
 *
 * Two things at once. It takes off the room every system keeps outside its staves, so the number
 * the reader set is the white they actually see. And it holds the result inside what the package
 * accepts — which refuses anything outside its range by throwing, right for a mistake in code and
 * wrong for a number arriving from a saved reading: a file written by hand would otherwise take
 * the whole page down rather than drawing with a sensible gap.
 */
function systemGapFor(whiteSpace: number, frameLabels: boolean): number {
  const asked = Number.isFinite(whiteSpace) ? whiteSpace : DEFAULT_LINE_SPACING;
  const held = Math.min(MAX_LINE_SPACING, Math.max(MIN_LINE_SPACING, asked));
  // A page with its column numbers off keeps less room above each staff, so less has to be taken
  // off to leave the reader the white they asked for. Without this the same number on the slider
  // meant two different gaps depending on a switch that has nothing to do with it.
  const room = frameLabels
    ? SYSTEM_ROOM
    : SYSTEM_ROOM - (GRAND_STAFF_TOP_PADDING - GRAND_STAFF_TOP_PADDING_BARE);
  return held - room;
}

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
