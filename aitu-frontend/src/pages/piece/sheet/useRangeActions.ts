/**
 * What the range toolbox knows about the marked stretch of frames, and the edits it makes there.
 *
 * Split out of `RhythmPage.tsx` (implementation 02, Phase 2).
 */

import { useMemo } from "react";
import type { KeySignatureName } from "../../../api";
import {
  clefAtFrame,
  keySignatureAtFrame,
  ottavaAtFrame,
  type KeySignature,
} from "@aimpromptu/grid-notation";
import { frameOf, rowOf, type PrintedHand } from "../../../music/renderOverrides";
import type { EditHistory } from "../../../hooks/useEditHistory";
import { DEFAULT_CLEF, type FrameTab, type RangeHand } from "./sheetConstants";
import type { SheetEdits } from "./sheetEdits";

export interface FrameRange {
  fromColumn: number;
  toColumn: number;
}

export function useRangeActions({
  range,
  rangeHand,
  chords,
  state,
  set,
  lyricDraft,
  passageDraft,
}: {
  range: FrameRange | null;
  rangeHand: RangeHand;
  chords: ReadonlyMap<string, number[]>;
  state: SheetEdits;
  set: EditHistory<SheetEdits>["set"];
  lyricDraft: { forRange: string; text: string } | null;
  passageDraft: { forRange: string; value: KeySignatureName } | null;
}) {
  const { keySignature, keyChanges, clefChanges, ottavas, lyrics, spacings, stretches } = state;
  const { spacings: setSpacings } = set;

  // Which stretch the toolbox is about, and what it will write. The signature offered is whatever
  // is already sounding at the start of the stretch, until the reader picks another.
  const rangeKey = range ? `${range.fromColumn}:${range.toColumn}` : "";

  /** The scale the selected stretch is set at: the stretch that covers its first column, or 1. */
  const spacingHere = range
    ? (spacings.find(
        (stretch) =>
          stretch.fromColumn <= range.fromColumn && stretch.toColumn > range.fromColumn,
      )?.scale ?? 1)
    : 1;
  /**
   * Set the marked stretch to take `scale` times the room the page measured for it.
   *
   * A handle rather than the two step buttons it replaces. Those moved by a fixed factor each
   * press, so finding the spot a crowded run actually reads at meant pressing *Wider* five times
   * and *Narrower* twice while watching the page jump — and the number the reader was after is a
   * look, not an arithmetic sequence. The sheet redraws as the handle moves, so the spot is found
   * by seeing it.
   *
   * A scale of exactly one is stored as nothing, so a stretch put back where it started leaves no
   * mark on the page and none in the file.
   */
  const setRangeSpacing = (scale: number) => {
    if (!range) return;
    const next = Math.round(Math.min(4, Math.max(0.25, scale)) * 100) / 100;
    setSpacings((current) => [
      ...current.filter(
        (stretch) =>
          !(stretch.fromColumn < range.toColumn && stretch.toColumn > range.fromColumn),
      ),
      ...(next === 1
        ? []
        : [{ fromColumn: range.fromColumn, toColumn: range.toColumn, scale: next }]),
    ]);
  };
  const clearSpacingRange = () => {
    if (!range) return;
    setSpacings((current) =>
      current.filter(
        (stretch) =>
          !(stretch.fromColumn < range.toColumn && stretch.toColumn > range.fromColumn),
      ),
    );
  };

  /**
   * The staves the frame pills act on: the one the reader narrowed to, or both.
   *
   * A clef and an octave bracket belong to one hand, so narrowing is the whole point of the pills.
   * A key signature is drawn on both clefs whatever is chosen, and a line of words is sung over the
   * piece — those two read the scope and ignore it, which the panel says.
   */
  const handsInScope: PrintedHand[] =
    rangeHand === "both" ? ["right", "left"] : [rangeHand];

  const editedHere: Record<FrameTab, boolean> = {
    key: range
      ? keySignatureAtFrame(
          range.fromColumn,
          keySignature as KeySignature,
          keyChanges,
        ) !== keySignature ||
        keyChanges.some(
          (change) =>
            change.fromColumn > range.fromColumn &&
            change.fromColumn < range.toColumn,
        )
      : false,
    clef: range
      ? handsInScope.some(
          (side) => clefAtFrame(range.fromColumn, side, clefChanges) !== DEFAULT_CLEF[side],
        ) ||
        clefChanges.some(
          (change) =>
            change.fromColumn > range.fromColumn && change.fromColumn < range.toColumn,
        )
      : false,
    octave: range
      ? handsInScope.some(
          (side) => ottavaAtFrame(ottavas, side, range.fromColumn) !== undefined,
        )
      : false,
    lyrics: range
      ? lyrics.some(
          (line) =>
            line.fromColumn < range.toColumn && line.toColumn > range.fromColumn,
        )
      : false,
    spacing: range
      ? spacings.some(
          (stretch) =>
            stretch.fromColumn < range.toColumn && stretch.toColumn > range.fromColumn,
        )
      : false,
    speed: range
      ? stretches.some(
          (stretch) =>
            stretch.startFrame >= range.fromColumn && stretch.startFrame < range.toColumn,
        )
      : false,
    rerecord: false,
  };

  /**
   * What the lyric tab needs to know about the stretch now open.
   *
   * Read from the marks themselves rather than kept in state: a panel that could disagree with
   * what is on the page is worse than a panel that has to look it up.
   */
  const lyricHere = range
    ? (lyrics.find(
        (line) =>
          line.fromColumn < range.toColumn && line.toColumn > range.fromColumn,
      ) ?? null)
    : null;
  const lyricText =
    lyricDraft?.forRange === rangeKey ? lyricDraft.text : (lyricHere?.text ?? "");

  const passageKey: KeySignatureName =
    passageDraft?.forRange === rangeKey
      ? passageDraft.value
      : (keySignatureAtFrame(
          range?.fromColumn ?? 0,
          keySignature as KeySignature,
          keyChanges,
        ) as KeySignatureName);

  /**
   * The noteheads a marked stretch covers, on the staves the hand pills name.
   *
   * By the column a note **begins** in, which is the column it is addressed by everywhere else on
   * this page — a note struck before the stretch and still sounding through it is not in it, the
   * same way it is not in the stretch's beam and does not take its figure from it. `toColumn` is
   * exclusive, as it is in every range this page holds.
   */
  const notesUnderRange = useMemo<readonly string[]>(() => {
    if (!range) return [];
    const hands: PrintedHand[] = rangeHand === "both" ? ["right", "left"] : [rangeHand];
    const keys: string[] = [];
    for (const [groupKey, rows] of chords) {
      const [staffName, frameText] = groupKey.split(":");
      const staff: PrintedHand = staffName === "left" ? "left" : "right";
      const frame = Number(frameText);
      if (!hands.includes(staff)) continue;
      if (frame < range.fromColumn || frame >= range.toColumn) continue;
      for (const row of rows) keys.push(`${staff}:${frame}:${row}`);
    }
    return keys.sort((left, right) =>
      frameOf(left) === frameOf(right)
        ? rowOf(left) - rowOf(right)
        : frameOf(left) - frameOf(right),
    );
  }, [range, rangeHand, chords]);

  return {
    rangeKey,
    spacingHere,
    setRangeSpacing,
    clearSpacingRange,
    handsInScope,
    editedHere,
    lyricHere,
    lyricText,
    passageKey,
    notesUnderRange,
  };
}

export type RangeActions = ReturnType<typeof useRangeActions>;
