import { customNoteToVexFlow, rowIndexToCustomNote } from "./notes";
import type { MatrixScore, NoteEvent, SparseMatrix, VexPiece } from "./types";

/**
 * Supported durations longest-first, including single-dotted variants
 * (a dot adds half the base length). Greedy picking prefers the longest
 * single symbol, so e.g. 1.5 beats becomes one dotted quarter (`q.`)
 * instead of a quarter tied to an eighth.
 */
const DURATIONS: { beats: number; token: string; dots: number }[] = [
  { beats: 4, token: "w", dots: 0 },
  { beats: 3, token: "h", dots: 1 },
  { beats: 2, token: "h", dots: 0 },
  { beats: 1.5, token: "q", dots: 1 },
  { beats: 1, token: "q", dots: 0 },
  { beats: 0.75, token: "8", dots: 1 },
  { beats: 0.5, token: "8", dots: 0 },
  { beats: 0.375, token: "16", dots: 1 },
  { beats: 0.25, token: "16", dots: 0 },
];

const MIN_BEATS = 0.25;
const EPSILON = 1e-6;

/** Decode the sparse COO payload into explicit (row, col, isOnset) cells. */
export function sparseToActiveCells(
  payload: SparseMatrix,
): Array<{ row: number; col: number; isOnset: boolean }> {
  const { rows, cols, onset } = payload;
  if (rows.length !== cols.length || rows.length !== onset.length) {
    throw new Error(
      `Sparse payload mismatch: rows ${rows.length}, cols ${cols.length}, onset ${onset.length}`,
    );
  }
  // onset[i] === -1 means the cell sustains a note rather than striking it.
  return rows.map((row, i) => ({ row, col: cols[i], isOnset: onset[i] !== -1 }));
}

/** Beats per single time step: timeStep * (bpm / 60). */
function beatsPerStep(tempoBpm: number, timeStepSeconds: number): number {
  return timeStepSeconds * (tempoBpm / 60);
}

/**
 * Turn cells into notes using the onset flag.
 *
 * An onset cell starts a new note; following sustain cells (`onset === -1`)
 * in the same row and consecutive columns extend that note's duration. This
 * is unambiguous: four `Re-4` onsets are four notes, while one onset + three
 * sustains is a single note four steps long. A sustain with no note to
 * continue (gap or missing onset) is treated as its own onset for safety.
 */
export function activeCellsToNoteEvents(
  payload: SparseMatrix,
  rows: string[] | undefined,
): NoteEvent[] {
  const cells = sparseToActiveCells(payload);

  // Cells per row, in column order.
  const cellsByRow = new Map<number, { col: number; isOnset: boolean }[]>();
  for (const { row, col, isOnset } of cells) {
    const list = cellsByRow.get(row);
    if (list) list.push({ col, isOnset });
    else cellsByRow.set(row, [{ col, isOnset }]);
  }

  const events: NoteEvent[] = [];
  for (const [row, rowCells] of cellsByRow) {
    const sorted = [...rowCells].sort((a, b) => a.col - b.col);
    const note = rowIndexToCustomNote(row, rows);
    const { key, accidental } = customNoteToVexFlow(note);
    // Bake the accidental into the pitch (e.g. "f/5" + "#" -> "f#/5") so
    // VexFlow knows the true pitch; the displayed accidental glyph is then
    // decided by Accidental.applyAccidentals against the key signature.
    const vexKey = accidental ? key.replace("/", `${accidental}/`) : key;

    let current: { startStep: number; lastCol: number; durationSteps: number } | null = null;
    const flush = () => {
      if (!current) return;
      events.push({
        note,
        vexKey,
        startStep: current.startStep,
        durationSteps: current.durationSteps,
      });
      current = null;
    };

    for (const { col, isOnset } of sorted) {
      const continues =
        current !== null && !isOnset && col === current.lastCol + 1;
      if (continues && current) {
        current.durationSteps += 1;
        current.lastCol = col;
      } else {
        flush();
        current = { startStep: col, lastCol: col, durationSteps: 1 };
      }
    }
    flush();
  }

  // Onset order: by start time, then pitch (row).
  return events.sort((a, b) => a.startStep - b.startStep || a.vexKey.localeCompare(b.vexKey));
}

type DurationToken = { token: string; dots: number };

/**
 * Split a span of steps into the fewest VexFlow symbols, preferring a single
 * (possibly dotted) note. Durations off the 1/16 grid are snapped + warned.
 */
function decomposeSpan(steps: number, beatPerStep: number): DurationToken[] {
  let beats = steps * beatPerStep;
  const snapped = Math.round(beats / MIN_BEATS) * MIN_BEATS;
  if (Math.abs(snapped - beats) > EPSILON) {
    console.warn(
      `Duration ${beats} beats is off the 1/16 grid; approximating to ${snapped}.`,
    );
  }
  beats = snapped;

  const tokens: DurationToken[] = [];
  while (beats >= MIN_BEATS - EPSILON) {
    const fit = DURATIONS.find((d) => d.beats <= beats + EPSILON);
    if (!fit) break;
    tokens.push({ token: fit.token, dots: fit.dots });
    beats -= fit.beats;
  }
  return tokens.length > 0 ? tokens : [{ token: "16", dots: 0 }];
}

/**
 * Build a single linear timeline of chords and rests.
 *
 * - Notes starting at the same column are merged into one chord.
 * - Simultaneous notes of different lengths are truncated to the shortest
 *   (MVP single-voice simplification) so every onset still appears.
 * - Silent gaps between notes become rests.
 */
/**
 * Restrict a sparse matrix to the column window `[start, end)` and rebase
 * its columns to start at 0. Used to wrap a long score into lines while
 * keeping both hands of a grand staff broken at the exact same time, so
 * the treble and bass systems stay vertically aligned. A note whose onset
 * fell before the window keeps sounding inside it: its leading cell has no
 * onset to continue, so the decoder promotes it to a fresh onset at the
 * line start (the same rule used everywhere else; we do not tie).
 */
export function sliceMatrixColumns(
  matrix: SparseMatrix,
  start: number,
  end: number,
): SparseMatrix {
  const rows: number[] = [];
  const cols: number[] = [];
  const onset: number[] = [];
  for (let i = 0; i < matrix.cols.length; i++) {
    const col = matrix.cols[i];
    if (col >= start && col < end) {
      rows.push(matrix.rows[i]);
      cols.push(col - start);
      onset.push(matrix.onset[i]);
    }
  }
  return { format: "binary-coo", shape: [matrix.shape[0], end - start], rows, cols, onset };
}

/**
 * Core pipeline for one sparse matrix (one clef): sparse cells -> note
 * events -> a linear timeline of chords and rests. Shared by the one-hand
 * treble path and by each hand of a two-hand grand staff (the bass clef
 * obeys the exact same notation, onset and duration rules).
 */
export function sparseToVexPieces(
  matrix: SparseMatrix,
  tempoBpm: number,
  timeStepSeconds: number,
  rows: string[] | undefined,
): VexPiece[] {
  const events = activeCellsToNoteEvents(matrix, rows);
  const totalCols = matrix.shape[1];
  const beatPerStep = beatsPerStep(tempoBpm, timeStepSeconds);

  const startsAt = new Map<number, NoteEvent[]>();
  let firstStart = totalCols;
  let lastEnd = 0;
  for (const ev of events) {
    const list = startsAt.get(ev.startStep);
    if (list) list.push(ev);
    else startsAt.set(ev.startStep, [ev]);
    firstStart = Math.min(firstStart, ev.startStep);
    lastEnd = Math.max(lastEnd, ev.startStep + ev.durationSteps);
  }

  const pieces: VexPiece[] = [];
  if (events.length === 0) return pieces;

  const emit = (startStep: number, tokens: DurationToken[], chord?: NoteEvent[]) => {
    tokens.forEach(({ token, dots }, i) => {
      const onset = i === 0 ? startStep : -1; // continuation pieces carry no lyric
      if (chord) {
        pieces.push({
          keys: chord.map((ev) => ev.vexKey),
          duration: token,
          dots,
          isRest: false,
          startStep: onset,
        });
      } else {
        pieces.push({
          keys: [],
          duration: token,
          dots,
          isRest: true,
          startStep: onset,
        });
      }
    });
  };

  let cursor = firstStart;
  while (cursor < lastEnd) {
    const here = startsAt.get(cursor);
    if (!here || here.length === 0) {
      // Silence until the next onset.
      let next = lastEnd;
      for (const s of startsAt.keys()) {
        if (s > cursor && s < next) next = s;
      }
      emit(cursor, decomposeSpan(next - cursor, beatPerStep));
      cursor = next;
      continue;
    }

    const chordSteps = Math.min(...here.map((ev) => ev.durationSteps));
    emit(cursor, decomposeSpan(chordSteps, beatPerStep), here);
    cursor += chordSteps;
  }

  return pieces;
}

/**
 * One-hand convenience: render the single treble `matrix`. Two-hand scores
 * (`r_matrix`/`l_matrix`) are sliced and rendered per clef by PianoSheet.
 */
export function noteEventsToVexPieces(score: MatrixScore): VexPiece[] {
  if (!score.matrix) return [];
  return sparseToVexPieces(score.matrix, score.tempoBpm, score.timeStepSeconds, score.rows);
}
