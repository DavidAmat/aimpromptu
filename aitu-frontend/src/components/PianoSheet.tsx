import { useEffect, useId, useMemo, useRef } from "react";
import {
  Accidental,
  Beam,
  Dot,
  Formatter,
  Renderer,
  Stave,
  StaveConnector,
  StaveNote,
  Voice,
} from "vexflow";
import { noteEventsToVexPieces, sliceMatrixColumns, sparseToVexPieces } from "../music/matrixToNotation";
import { KEY_SIGNATURES } from "../music/notes";
import type { MatrixScore, VexPiece } from "../music/types";

/** vex key spec -> number of accidentals it draws (for layout room). */
const KEY_ACCIDENTAL_COUNT = new Map(
  KEY_SIGNATURES.map(({ vex, accidentals }) => [vex, accidentals.length]),
);

type PianoSheetProps = {
  score: MatrixScore;
  pxPerNote: number;
  lyricsGap: number;
  lyricsFontSize: number;
};

const LEFT_MARGIN = 16;
const RIGHT_MARGIN = 16;
const CLEF_ROOM = 70;
const ROW_BASE_HEIGHT = 120;

// Two-hand (grand staff) geometry. The left hand always sits on a bass clef
// directly below the right-hand treble, braced together.
const BRACE_ROOM = 16; // left padding so the brace has room to draw
const GRAND_STAVE_GAP = 100; // treble top -> bass top
const GRAND_ROW_HEIGHT = 240; // one full system (treble + gap + bass)

/** One VexPiece -> one StaveNote (chord or rest), with dots attached.
 *  Accidental glyphs are NOT added here — `Accidental.applyAccidentals`
 *  decides them per the key signature once the voice is built. */
function pieceToStaveNote(piece: VexPiece, clef: "treble" | "bass"): StaveNote {
  // Encode dots in the duration string ("qd", "8d") so ticks — and therefore
  // beam grouping — stay correct; the glyph itself is added via Dot below.
  const dotStr = "d".repeat(piece.dots);

  if (piece.isRest) {
    const rest = new StaveNote({ keys: ["b/4"], duration: `${piece.duration}${dotStr}r` });
    if (piece.dots > 0) Dot.buildAndAttach([rest], { all: true });
    return rest;
  }

  const note = new StaveNote({ clef, keys: piece.keys, duration: `${piece.duration}${dotStr}` });
  if (piece.dots > 0) Dot.buildAndAttach([note], { all: true });
  return note;
}

/** Base durations short enough to carry a beam (eighth and shorter). */
const BEAMABLE = new Set(["8", "16", "32"]);

/**
 * Beam every maximal run of >= 2 consecutive beamable notes, breaking at
 * any longer note or rest. VexFlow's tick-based `generateBeams` assumes
 * proper measures/beats, which our barless soft voice does not have, so
 * we group by the simple "consecutive corcheas" rule instead.
 */
function buildBeams(notes: StaveNote[]): Beam[] {
  const beams: Beam[] = [];
  let run: StaveNote[] = [];

  const flush = () => {
    if (run.length > 1) beams.push(new Beam(run));
    run = [];
  };

  for (const note of notes) {
    if (!note.isRest() && BEAMABLE.has(note.getDuration())) {
      run.push(note);
    } else {
      flush();
    }
  }
  flush();
  return beams;
}

/** Greedily split pieces into lines that fit the available width. */
function chunkIntoLines(pieces: VexPiece[], perLine: number): VexPiece[][] {
  const lines: VexPiece[][] = [];
  for (let i = 0; i < pieces.length; i += perLine) {
    lines.push(pieces.slice(i, i + perLine));
  }
  return lines.length > 0 ? lines : [[]];
}

export function PianoSheet({ score, pxPerNote, lyricsGap, lyricsFontSize }: PianoSheetProps) {
  const rawId = useId();
  const elementId = `vexflow-${rawId.replace(/:/g, "")}`;
  const containerRef = useRef<HTMLDivElement>(null);

  // Two hands: right hand on the treble, left hand on the bass clef. Otherwise
  // a single treble matrix (unchanged behaviour).
  const twoHand = Boolean(score.r_matrix && score.l_matrix);
  const pieces = useMemo(
    () => (twoHand ? [] : noteEventsToVexPieces(score)),
    [twoHand, score],
  );

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const keySig = score.keySignature;
    const keySigRoom = keySig
      ? (KEY_ACCIDENTAL_COUNT.get(keySig) ?? 0) * 12 + (keySig === "C" ? 0 : 8)
      : 0;

    /** Draw one clef's stave + soft voice + beams; returns the Stave. */
    const drawStave = (
      context: ReturnType<Renderer["getContext"]>,
      linePieces: VexPiece[],
      clef: "treble" | "bass",
      x: number,
      y: number,
      staveWidth: number,
      noteAreaWidth: number,
      withClef: boolean,
    ): { stave: Stave; notes: StaveNote[] } => {
      const stave = new Stave(x, y, staveWidth);
      if (withClef) stave.addClef(clef);
      if (keySig && keySig !== "C") stave.addKeySignature(keySig);
      stave.setContext(context).draw();

      if (linePieces.length === 0) return { stave, notes: [] };

      const notes = linePieces.map((p) => pieceToStaveNote(p, clef));
      // Beam BEFORE formatting/drawing: a beamed note hides its own flag.
      const beams = buildBeams(notes);

      // Soft (non-strict) voice: the custom notation does not fill measures.
      const voice = new Voice({ numBeats: 4, beatValue: 4 });
      voice.setStrict(false);
      voice.addTickables(notes);
      // Let VexFlow decide accidental glyphs against the key signature: a
      // note already altered by the key (e.g. F# in G major) shows none.
      Accidental.applyAccidentals([voice], keySig ?? "C");
      new Formatter().joinVoices([voice]).format([voice], noteAreaWidth);
      voice.draw(context, stave);
      beams.forEach((beam) => beam.setContext(context).draw());

      return { stave, notes };
    };

    /**
     * Lyrics are one per **time frame** and independent of the notes: a
     * syllable is drawn at its frame's horizontal position whether that
     * frame is a struck note, a sustain, or a silence. We build a
     * frame -> x map by interpolating between the rendered note heads
     * (with the stave's note start/end as the outer anchors), so a lyric
     * on a sustained or silent frame still lands at the right place.
     *
     * `colStart`..`colEnd` is this line's frame range in the same
     * coordinate as `piece.startStep` (window-relative for two hands,
     * absolute for one hand). `lyricColOffset` is added when indexing
     * `score.lyrics` (the window's absolute start for two hands, 0 for one).
     */
    const drawLyrics = (
      context: ReturnType<Renderer["getContext"]>,
      stave: Stave,
      linePieces: VexPiece[],
      notes: StaveNote[],
      yLyric: number,
      colStart: number,
      colEnd: number,
      lyricColOffset: number,
    ) => {
      if (!score.lyrics || colEnd <= colStart) return;

      // Anchor frames we know the exact x of: each piece's first note head.
      const anchors: { col: number; x: number }[] = [];
      linePieces.forEach((piece, i) => {
        if (piece.startStep >= 0) {
          anchors.push({ col: piece.startStep, x: notes[i].getAbsoluteX() });
        }
      });

      const pts: { col: number; x: number }[] = [];
      if (anchors.length === 0 || anchors[0].col > colStart) {
        pts.push({ col: colStart, x: stave.getNoteStartX() });
      }
      pts.push(...anchors);
      pts.push({ col: colEnd, x: stave.getNoteEndX() });

      const xForCol = (c: number): number => {
        if (c <= pts[0].col) return pts[0].x;
        for (let k = 0; k < pts.length - 1; k++) {
          const a = pts[k];
          const b = pts[k + 1];
          if (c >= a.col && c <= b.col) {
            if (b.col === a.col) return a.x;
            return a.x + ((b.x - a.x) * (c - a.col)) / (b.col - a.col);
          }
        }
        return pts[pts.length - 1].x;
      };

      context.save();
      context.setFont("Inter, system-ui, sans-serif", lyricsFontSize);
      context.setFillStyle("#17130d");
      for (let c = colStart; c < colEnd; c++) {
        const text = score.lyrics[c + lyricColOffset];
        if (!text) continue;
        const textWidth = context.measureText(text).width;
        context.fillText(text, xForCol(c) - textWidth / 2, yLyric);
      }
      context.restore();
    };

    const render = () => {
      const host = document.getElementById(elementId);
      if (!host) return;
      host.innerHTML = "";

      const hasLyrics = Boolean(score.lyrics);
      const lyricsRoom = hasLyrics ? lyricsGap + lyricsFontSize + 4 : 0;
      const availableWidth = Math.max(420, container.clientWidth);
      // pxPerNote drives the actual horizontal space each note gets; the
      // number of notes per line follows from how many fit at that spacing.
      const usableWidth = availableWidth - LEFT_MARGIN - RIGHT_MARGIN - CLEF_ROOM;
      const perLine = Math.max(2, Math.floor(usableWidth / pxPerNote));

      const renderer = new Renderer(host as HTMLDivElement, Renderer.Backends.SVG);
      const context = renderer.getContext();

      if (twoHand) {
        // Wrap by TIME, not by note count: both hands break at the exact
        // same column window so treble and bass stay vertically aligned.
        const rMatrix = score.r_matrix!;
        const lMatrix = score.l_matrix!;
        const totalCols = rMatrix.shape[1];
        const colsPerLine = Math.max(2, perLine);
        const lineCount = Math.max(1, Math.ceil(totalCols / colsPerLine));
        const rowHeight = GRAND_ROW_HEIGHT + lyricsRoom;
        const canvasHeight = 24 + lyricsRoom + lineCount * rowHeight;
        renderer.resize(availableWidth, canvasHeight);

        const staveX = LEFT_MARGIN + BRACE_ROOM;
        for (let line = 0; line < lineCount; line++) {
          const isFirst = line === 0;
          const start = line * colsPerLine;
          const end = Math.min(totalCols, start + colsPerLine);
          const colsThisLine = end - start;

          const treblePieces = sparseToVexPieces(
            sliceMatrixColumns(rMatrix, start, end),
            score.tempoBpm,
            score.timeStepSeconds,
            score.rows,
          );
          const bassPieces = sparseToVexPieces(
            sliceMatrixColumns(lMatrix, start, end),
            score.tempoBpm,
            score.timeStepSeconds,
            score.rows,
          );

          const clefRoom = (isFirst ? CLEF_ROOM : 12) + keySigRoom;
          const noteAreaWidth = Math.max(1, colsThisLine) * pxPerNote;
          const staveWidth = clefRoom + noteAreaWidth + 20;

          const yTop = 24 + lyricsRoom + line * rowHeight;
          const yBottom = yTop + GRAND_STAVE_GAP;

          const treble = drawStave(
            context, treblePieces, "treble",
            staveX, yTop, staveWidth, noteAreaWidth, isFirst,
          );
          const bass = drawStave(
            context, bassPieces, "bass",
            staveX, yBottom, staveWidth, noteAreaWidth, isFirst,
          );

          // Brace + left/right barlines tie the two hands into a grand staff.
          new StaveConnector(treble.stave, bass.stave)
            .setType(StaveConnector.type.BRACE)
            .setContext(context)
            .draw();
          new StaveConnector(treble.stave, bass.stave)
            .setType(StaveConnector.type.SINGLE_LEFT)
            .setContext(context)
            .draw();
          new StaveConnector(treble.stave, bass.stave)
            .setType(StaveConnector.type.SINGLE_RIGHT)
            .setContext(context)
            .draw();

          if (hasLyrics) {
            // Sliced matrices use window-relative columns [0, colsThisLine);
            // the lyrics array is absolute, so offset by `start`.
            drawLyrics(
              context, treble.stave, treblePieces, treble.notes,
              yTop - lyricsGap, 0, colsThisLine, start,
            );
          }
        }
        return;
      }

      // One hand: single treble staff (unchanged behaviour).
      const rowHeight = ROW_BASE_HEIGHT + lyricsRoom;
      const lines = chunkIntoLines(pieces, perLine);
      const canvasHeight = 24 + lyricsRoom + lines.length * rowHeight;
      renderer.resize(availableWidth, canvasHeight);

      // Contiguous frame range per line so lyrics map to time frames even
      // across sustains/silences. A line's first real frame is its first
      // piece with a start step; ranges chain so [start,end) covers 0..total.
      const totalColsSingle = score.matrix?.shape[1] ?? 0;
      const lineFirstCol = lines.map((lp) => {
        for (const p of lp) if (p.startStep >= 0) return p.startStep;
        return -1;
      });
      let prevEnd = 0;
      const lineRanges = lines.map((_, idx) => {
        const start = idx === 0 ? 0 : prevEnd;
        let end: number;
        if (idx < lines.length - 1) {
          const nextFirst = lineFirstCol[idx + 1];
          end = nextFirst >= 0 ? nextFirst : totalColsSingle;
        } else {
          end = totalColsSingle;
        }
        if (end < start) end = start;
        prevEnd = end;
        return { start, end };
      });

      lines.forEach((linePieces, lineIndex) => {
        const isFirst = lineIndex === 0;
        const y = 24 + lyricsRoom + lineIndex * rowHeight;
        // Key signature repeats at the start of every line (standard notation).
        const clefRoom = (isFirst ? CLEF_ROOM : 12) + keySigRoom;
        // Stave width tracks note count × spacing, so pxPerNote visibly
        // stretches/compresses the passage instead of always filling the row.
        const noteAreaWidth = Math.max(1, linePieces.length) * pxPerNote;
        const staveWidth = clefRoom + noteAreaWidth + 20;

        const { stave, notes } = drawStave(
          context, linePieces, "treble",
          LEFT_MARGIN, y, staveWidth, noteAreaWidth, isFirst,
        );

        if (linePieces.length === 0) return;

        if (hasLyrics) {
          const { start, end } = lineRanges[lineIndex];
          drawLyrics(
            context, stave, linePieces, notes,
            y - lyricsGap, start, end, 0,
          );
        }
      });
    };

    render();
    const ro = new ResizeObserver(render);
    ro.observe(container);

    return () => {
      ro.disconnect();
      const host = document.getElementById(elementId);
      if (host) host.innerHTML = "";
    };
  }, [elementId, twoHand, pieces, score, pxPerNote, lyricsGap, lyricsFontSize]);

  return (
    <section className="score-card" aria-label="Rendered piano notation" ref={containerRef}>
      <div id={elementId} className="vexflow-output" />
    </section>
  );
}
