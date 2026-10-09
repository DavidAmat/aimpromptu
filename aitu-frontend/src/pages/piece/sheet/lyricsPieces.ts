/**
 * The lyrics pieces of the Sheet step (plan section 11.5), as plain functions of the list.
 *
 * A **lyrics piece** is one line of the pasted lyrics. In the pool it is only its text; placed on
 * the sheet it is a `LyricLine`: the text, the frame it starts on (`fromColumn`), the frame after
 * its last (`toColumn`), how far it is raised or lowered (`offsetY`), its font size, and its line
 * breaks (newlines in the text). Two pieces never share a frame: one word would print over another.
 *
 * Each function returns the new list, or a sentence saying why it could not, so the page can show
 * the refusal and change nothing.
 */

import { LYRIC_FONT_SIZE, MAX_LYRIC_FONT_SIZE, MIN_LYRIC_FONT_SIZE } from "@aimpromptu/grid-notation";
import type { LyricLine } from "../../../api";

export type Outcome<T> = { ok: T } | { refused: string };

/** How long a piece is held on the sheet when it is dropped, per character of its text. */
const MS_PER_CHARACTER = 120;

const BUSY = "Another lyrics piece is already over those frames.";

/** The pasted lyrics as pieces: one per line, empty lines left out. */
export function piecesFromText(text: string): string[] {
  return text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line.length > 0);
}

function byStart(lyrics: readonly LyricLine[]): LyricLine[] {
  return [...lyrics].sort((left, right) => left.fromColumn - right.fromColumn);
}

function overlaps(
  lyrics: readonly LyricLine[],
  from: number,
  to: number,
  except: readonly number[] = [],
): boolean {
  return lyrics.some(
    (line) =>
      !except.includes(line.fromColumn) && line.fromColumn < to && line.toColumn > from,
  );
}

/**
 * A piece of the pool, dropped on a frame.
 *
 * It is held for about as long as its words take to sing (120 ms a character), and never past the
 * next piece or the end of the piece; the reader then drags its right edge to where it ends.
 */
export function placePiece(
  lyrics: readonly LyricLine[],
  text: string,
  atFrame: number,
  frameMs: number,
  frameCount: number,
): Outcome<LyricLine[]> {
  const landing = landingOf(lyrics, text, atFrame, frameMs, frameCount);
  if (!landing.free) return { refused: BUSY };
  return {
    ok: byStart([...lyrics, { fromColumn: landing.fromColumn, toColumn: landing.toColumn, text }]),
  };
}

/**
 * The frames a piece dropped on `atFrame` would cover, and whether it may land there: it starts on
 * that frame, and is free unless another piece already covers that frame. What the sheet shades
 * while a piece of the pool is dragged over it.
 */
export function landingOf(
  lyrics: readonly LyricLine[],
  text: string,
  atFrame: number,
  frameMs: number,
  frameCount: number,
): { fromColumn: number; toColumn: number; free: boolean } {
  const from = Math.max(0, Math.min(atFrame, frameCount - 1));
  const wanted = Math.max(1, Math.round((text.length * MS_PER_CHARACTER) / frameMs));
  if (overlaps(lyrics, from, from + 1)) {
    return { fromColumn: from, toColumn: Math.min(from + wanted, frameCount), free: false };
  }
  const next = byStart(lyrics).find((line) => line.fromColumn > from)?.fromColumn ?? frameCount;
  return { fromColumn: from, toColumn: Math.min(from + wanted, next, frameCount), free: true };
}

/** A piece's words with its line breaks and repeated spaces as single spaces, to compare them. */
const plain = (text: string) => text.replace(/\s+/g, " ").trim();

/**
 * Which pieces of the pool are on the sheet: the green tick of the pool. A piece is on the sheet
 * when a placed piece has its words (line breaks aside); a line the song sings twice is ticked once
 * per time it is placed, in pool order.
 */
export function placedInPool(pool: readonly string[], lyrics: readonly LyricLine[]): boolean[] {
  const left = new Map<string, number>();
  for (const line of lyrics) left.set(plain(line.text), (left.get(plain(line.text)) ?? 0) + 1);
  return pool.map((text) => {
    const count = left.get(plain(text)) ?? 0;
    if (count === 0) return false;
    left.set(plain(text), count - 1);
    return true;
  });
}

/** A placed piece moved or resized by dragging on the sheet, its edges on frames. */
export function movePiece(
  lyrics: readonly LyricLine[],
  change: {
    fromColumn: number;
    toColumn: number;
    nextFromColumn: number;
    nextToColumn: number;
    offsetY: number;
  },
): Outcome<LyricLine[]> {
  const piece = lyrics.find((line) => line.fromColumn === change.fromColumn);
  if (!piece) return { refused: "That lyrics piece is not on the sheet any more." };
  if (overlaps(lyrics, change.nextFromColumn, change.nextToColumn, [piece.fromColumn])) {
    return { refused: BUSY };
  }
  // The frames now say where it is and how far it reaches: the old pixel offset sideways and the
  // old pixel width, from before pieces snapped to frames, no longer apply.
  const moved: LyricLine = {
    fromColumn: change.nextFromColumn,
    toColumn: change.nextToColumn,
    text: piece.text,
    ...(change.offsetY === 0 ? {} : { offsetY: change.offsetY }),
    ...(piece.fontSize === undefined ? {} : { fontSize: piece.fontSize }),
  };
  return { ok: byStart(lyrics.map((line) => (line === piece ? moved : line))) };
}

/** The picked pieces, joined into one in their order, from the first frame to the last. */
export function mergePieces(
  lyrics: readonly LyricLine[],
  picked: readonly number[],
): Outcome<LyricLine[]> {
  const chosen = byStart(lyrics.filter((line) => picked.includes(line.fromColumn)));
  if (chosen.length < 2) return { refused: "Pick two or more pieces to merge." };
  const first = chosen[0]!;
  const to = Math.max(...chosen.map((line) => line.toColumn));
  if (overlaps(lyrics, first.fromColumn, to, chosen.map((line) => line.fromColumn))) {
    return { refused: "Another piece lies between them: pick it too, or move it first." };
  }
  const merged: LyricLine = {
    ...first,
    toColumn: to,
    text: chosen.map((line) => line.text).join(" "),
  };
  return {
    ok: byStart([...lyrics.filter((line) => !chosen.includes(line)), merged]),
  };
}

/**
 * One piece split in two where the cursor is: the words before it and the words after.
 *
 * The frames are shared in the same proportion as the words, so each half starts about where it
 * is sung; each keeps at least one frame.
 */
export function splitPiece(
  lyrics: readonly LyricLine[],
  fromColumn: number,
  caret: number,
): Outcome<LyricLine[]> {
  const piece = lyrics.find((line) => line.fromColumn === fromColumn);
  if (!piece) return { refused: "That lyrics piece is not on the sheet any more." };
  const before = piece.text.slice(0, caret).trim();
  const after = piece.text.slice(caret).trim();
  if (!before || !after) return { refused: "Put the cursor between two words to split." };
  const span = piece.toColumn - piece.fromColumn;
  if (span < 2) return { refused: "This piece covers one frame: make it longer to split it." };
  const middle = Math.min(
    piece.toColumn - 1,
    Math.max(piece.fromColumn + 1, piece.fromColumn + Math.round((span * caret) / piece.text.length)),
  );
  const first: LyricLine = { ...piece, toColumn: middle, text: before };
  const second: LyricLine = {
    fromColumn: middle,
    toColumn: piece.toColumn,
    text: after,
    ...(piece.offsetY === undefined ? {} : { offsetY: piece.offsetY }),
    ...(piece.fontSize === undefined ? {} : { fontSize: piece.fontSize }),
  };
  return { ok: byStart([...lyrics.filter((line) => line !== piece), first, second]) };
}

/** A line break put into a piece where the cursor is. */
export function breakLine(text: string, caret: number): string {
  return `${text.slice(0, caret).trimEnd()}\n${text.slice(caret).trimStart()}`;
}

/** The picked pieces, taken off the sheet; their words stay in (or join) the pool. */
export function backToPool(
  lyrics: readonly LyricLine[],
  pool: readonly string[],
  picked: readonly number[],
): { lyrics: LyricLine[]; pool: string[] } {
  const chosen = byStart(lyrics.filter((line) => picked.includes(line.fromColumn)));
  // The pool keeps every piece, placed or not: a piece taken off the sheet is already there (its
  // tick goes). Only words the pool does not have (a merged or split piece) are added, at the top,
  // one line each: a line break was a placement decision.
  const known = new Set(pool.map(plain));
  const added = chosen.map((line) => plain(line.text)).filter((text) => !known.has(text));
  return {
    lyrics: lyrics.filter((line) => !chosen.includes(line)),
    pool: [...added, ...pool],
  };
}

/** The font size of the picked pieces, one pixel up or down. */
export function resizePieces(
  lyrics: readonly LyricLine[],
  picked: readonly number[],
  delta: number,
): LyricLine[] {
  return lyrics.map((line) =>
    picked.includes(line.fromColumn)
      ? {
          ...line,
          fontSize: Math.min(
            MAX_LYRIC_FONT_SIZE,
            Math.max(MIN_LYRIC_FONT_SIZE, (line.fontSize ?? LYRIC_FONT_SIZE) + delta),
          ),
        }
      : line,
  );
}

/**
 * A piece of the pool, with its words edited: each line of the new words is a piece of its own, in
 * the same place in the pool, so a line break splits it and the order is kept. No words left
 * removes it.
 */
export function editPoolPiece(pool: readonly string[], index: number, text: string): string[] {
  return [...pool.slice(0, index), ...piecesFromText(text), ...pool.slice(index + 1)];
}

/**
 * Pieces of the pool joined into one, in pool order, in the place of the first: the way back from
 * a split made by mistake. Their words are joined with a space.
 */
export function mergePoolPieces(pool: readonly string[], indexes: readonly number[]): string[] {
  const chosen = [...new Set(indexes)].filter((at) => at >= 0 && at < pool.length).sort((a, b) => a - b);
  if (chosen.length < 2) return [...pool];
  const merged = chosen.map((at) => pool[at]!).join(" ");
  return pool.flatMap((text, at) =>
    at === chosen[0] ? [merged] : chosen.includes(at) ? [] : [text],
  );
}

/** The pieces that cover any frame of a stretch: what a stretch marked in Lyrics mode picks. */
export function piecesIn(
  lyrics: readonly LyricLine[],
  range: { fromColumn: number; toColumn: number },
): number[] {
  return lyrics
    .filter((line) => line.fromColumn < range.toColumn && line.toColumn > range.fromColumn)
    .map((line) => line.fromColumn);
}
