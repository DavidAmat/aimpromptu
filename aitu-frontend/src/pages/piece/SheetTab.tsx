/**
 * Step 5 (**Sheet**): the piano sheet of the Playground, inside the flow page (plan section 9.7).
 *
 * The page is `RhythmPage` as it is, with every tool it has. The flow page gives it the piece and
 * the state of the Sheet step, so it can open a stale reading with its banner (plan section 8.3),
 * and asks the backend again after a save or **Remove all**, so the tick of the tab follows.
 */

import { useMemo } from "react";
import RhythmPage, { type SheetStep } from "../playground/RhythmPage";
import { stepStatus, usePiece } from "./pieceContext";

export function SheetTab() {
  const { uuid, audio, status, refresh } = usePiece();
  const here = stepStatus(status, "sheet");
  const state = here?.state ?? null;
  const reason = here?.reason ?? null;
  const label = audio?.alias;

  const step = useMemo<SheetStep | null>(
    () =>
      uuid && state
        ? { audioUuid: uuid, label, state, reason, onChanged: () => void refresh() }
        : null,
    [uuid, label, state, reason, refresh],
  );

  if (!step) return null;
  // Keyed by the piece, so nothing of one piece's sheet is shown over the next one.
  return <RhythmPage key={step.audioUuid} step={step} />;
}

export default SheetTab;
