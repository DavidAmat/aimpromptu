/**
 * What the reader changed about the *page*, applied to the matrix on its way to the drawing.
 *
 * Two of these — dropping a note and sending one to the other staff — are the sort of thing that
 * looks like an edit to the recording and must not be one. The transcription is evidence: it says
 * which keys went down and when, and no amount of disagreement with it makes that untrue. What is
 * open to disagreement is the *reading*: a note the transcriber invented out of a pedal blur has no
 * business on the page, and the hand split is a guess that a player can simply see is wrong.
 *
 * So neither writes to the matrix. Both are kept as a small set of keys beside the score and folded
 * into a copy of it here, one frame before it is drawn. Undoing one restores the original because
 * the original was never gone.
 *
 * A note is addressed as `startFrame:row`, without a hand. Right and left can never hold the same
 * onset — the package refuses a matrix where they do — so the pair is already unique, and leaving
 * the hand out is what lets a moved note keep its identity across the move.
 */

import type { SparseMatrix } from "@aimpromptu/grid-notation";

/** Which staff a printed note is on. */
export type PrintedHand = "right" | "left";

/** A note as the reader points at it: `startFrame:row`, no hand. */
export type NoteRef = string;

/** The renderer hands back `hand:startFrame:row`. This is the rest of it. */
export function noteRefOf(noteKey: string): NoteRef {
  const [, frame, row] = noteKey.split(":");
  return `${frame}:${row}`;
}

/** The hand half of `hand:startFrame:row`. */
export function handOf(noteKey: string): PrintedHand {
  return noteKey.startsWith("left:") ? "left" : "right";
}

/** The frame half of `hand:startFrame:row`. */
export function frameOf(noteKey: string): number {
  return Number(noteKey.split(":")[1]);
}

/** The row half of `hand:startFrame:row`. */
export function rowOf(noteKey: string): number {
  return Number(noteKey.split(":")[2]);
}

/** `hand:startFrame`, which is what an override, a beam break and a tuplet are all keyed by. */
export function groupKeyOf(noteKey: string): string {
  const [hand, frame] = noteKey.split(":");
  return `${hand}:${frame}`;
}

export interface RenderOverrides {
  /** Notes the reader took off the page, as `startFrame:row`. */
  hidden: ReadonlySet<NoteRef>;
  /** Notes the reader moved, as `startFrame:row` to the staff they belong on. */
  hands: ReadonlyMap<NoteRef, PrintedHand>;
}

export const NO_RENDER_OVERRIDES: RenderOverrides = {
  hidden: new Set<NoteRef>(),
  hands: new Map<NoteRef, PrintedHand>(),
};

export function hasRenderOverrides(overrides: RenderOverrides): boolean {
  return overrides.hidden.size > 0 || overrides.hands.size > 0;
}

/** One cell of a sparse matrix, with the onset it belongs to worked out. */
interface OwnedCell {
  row: number;
  col: number;
  /** True for the struck cell, false for the sustain that follows it. */
  onset: boolean;
  /** The frame of the onset this cell belongs to — itself, for an onset. */
  ownerFrame: number;
}

/**
 * Which onset each cell belongs to.
 *
 * A sustain has no identity of its own: it is the tail of the last onset in its row, and it has to
 * travel with it or a moved note would leave its sound behind on the old staff. The run breaks at a
 * gap in the columns as well as at the next onset, because two separate notes in one row with
 * silence between them are two notes.
 */
function ownCells(matrix: SparseMatrix): OwnedCell[] {
  const byRow = new Map<number, { col: number; onset: boolean }[]>();
  for (let index = 0; index < matrix.rows.length; index += 1) {
    const row = matrix.rows[index]!;
    const col = matrix.cols[index]!;
    const onset = matrix.onset[index] === row;
    const cells = byRow.get(row);
    if (cells) cells.push({ col, onset });
    else byRow.set(row, [{ col, onset }]);
  }

  const owned: OwnedCell[] = [];
  for (const [row, cells] of byRow) {
    cells.sort((left, right) => left.col - right.col);
    let ownerFrame: number | null = null;
    let previousCol: number | null = null;
    for (const cell of cells) {
      const broken = previousCol !== null && cell.col !== previousCol + 1;
      if (cell.onset || ownerFrame === null || broken) ownerFrame = cell.col;
      owned.push({ row, col: cell.col, onset: cell.onset, ownerFrame });
      previousCol = cell.col;
    }
  }
  return owned;
}

function toSparse(cells: OwnedCell[], frameCount: number): SparseMatrix {
  const ordered = [...cells].sort((left, right) =>
    left.col === right.col ? left.row - right.row : left.col - right.col,
  );
  return {
    format: "binary-coo",
    shape: [88, frameCount],
    rows: ordered.map((cell) => cell.row),
    cols: ordered.map((cell) => cell.col),
    onset: ordered.map((cell) => (cell.onset ? cell.row : -1)),
  };
}

export interface AppliedOverrides {
  rMatrix: SparseMatrix;
  lMatrix: SparseMatrix;
  /**
   * Where every surviving note ended up, as `startFrame:row` to the staff it is drawn on.
   *
   * The figures, the tuplet marks and the beam breaks are all keyed by hand, and after a move the
   * hand in the key is the one the note is *drawn* on. This is the map that re-keys them, so the
   * page cannot end up with a note on one staff and its figure on the other.
   */
  handOf: ReadonlyMap<NoteRef, PrintedHand>;
  /** Moves that could not be made because the far staff already holds that key at that moment. */
  refused: NoteRef[];
}

/**
 * Fold the reader's page edits into a copy of the two matrices.
 *
 * A move that would land on an onset the other hand already has is refused rather than merged: the
 * package rejects a matrix where both hands strike the same key in the same frame, and silently
 * dropping one of the two would lose a note the recording says was played.
 */
export function applyRenderOverrides(
  rMatrix: SparseMatrix,
  lMatrix: SparseMatrix,
  overrides: RenderOverrides,
): AppliedOverrides {
  const frameCount = rMatrix.shape[1];
  const right = ownCells(rMatrix);
  const left = ownCells(lMatrix);

  const kept: Record<PrintedHand, OwnedCell[]> = { right: [], left: [] };
  const placed: Record<PrintedHand, Set<string>> = { right: new Set(), left: new Set() };
  const landing = new Map<NoteRef, PrintedHand>();
  const refused: NoteRef[] = [];

  // Notes that stay where they are go down first, so a move can see what is already there and step
  // aside. Without the two passes, whether a move worked would depend on the order of the arrays.
  const moving: { cell: OwnedCell; from: PrintedHand; to: PrintedHand }[] = [];
  const walk = (cells: OwnedCell[], from: PrintedHand) => {
    for (const cell of cells) {
      const ref: NoteRef = `${cell.ownerFrame}:${cell.row}`;
      if (overrides.hidden.has(ref)) continue;
      const to = overrides.hands.get(ref) ?? from;
      if (to === from) {
        kept[from].push(cell);
        placed[from].add(`${cell.col}:${cell.row}`);
        landing.set(ref, from);
      } else {
        moving.push({ cell, from, to });
      }
    }
  };
  walk(right, "right");
  walk(left, "left");

  // A move is all-or-nothing: the onset and every cell of its sustain go together, or none do.
  const blocked = new Set<NoteRef>();
  for (const move of moving) {
    const ref: NoteRef = `${move.cell.ownerFrame}:${move.cell.row}`;
    if (placed[move.to].has(`${move.cell.col}:${move.cell.row}`)) blocked.add(ref);
  }

  for (const move of moving) {
    const ref: NoteRef = `${move.cell.ownerFrame}:${move.cell.row}`;
    const hand = blocked.has(ref) ? move.from : move.to;
    kept[hand].push(move.cell);
    placed[hand].add(`${move.cell.col}:${move.cell.row}`);
    landing.set(ref, hand);
    if (blocked.has(ref) && !refused.includes(ref)) refused.push(ref);
  }

  return {
    rMatrix: toSparse(kept.right, frameCount),
    lMatrix: toSparse(kept.left, frameCount),
    handOf: landing,
    refused,
  };
}
