/**
 * What every tab of the flow page shares: the piece, its status, and the guard for unsaved edits.
 *
 * Context and types only (no components), so React Fast Refresh stays happy, as in
 * `state/workingArtifactContext.ts`.
 */

import { createContext, useContext, useEffect } from "react";
import type { AudioItem, PieceStatus, PieceStep, StepStatus } from "../../api";

/** What a tab with unsaved edits does when the reader leaves it and chooses Save or Discard. */
export interface UnsavedHandlers {
  /** Save the edits. `false` when the save failed, so the reader stays on the tab. */
  save: () => Promise<boolean>;
  discard: () => void;
}

export interface PieceContextValue {
  /** `null` on `/piece/new`. */
  uuid: string | null;
  audio: AudioItem | null;
  status: PieceStatus | null;
  /** Ask the backend again, after anything that may change a step. Resolves to the new status. */
  refresh: () => Promise<PieceStatus | null>;
  /** Called by the tab on each render with its current handlers. */
  registerUnsaved: (handlers: UnsavedHandlers | null) => void;
  /** What is unsaved, in words for the dialog and the save bar; `null` when nothing is. */
  setUnsavedSummary: (summary: string | null) => void;
}

export const PieceContext = createContext<PieceContextValue | null>(null);

export function usePiece(): PieceContextValue {
  const value = useContext(PieceContext);
  if (value === null) throw new Error("usePiece must be used inside the flow page");
  return value;
}

/** The status of one step, once the status has arrived. */
export function stepStatus(status: PieceStatus | null, step: PieceStep): StepStatus | null {
  return status?.steps.find((item) => item.step === step) ?? null;
}

/**
 * Tell the flow page that this tab holds unsaved edits.
 *
 * With a summary, leaving the tab (another tab, a link of the top bar, the browser's back button)
 * first asks the reader to save or discard, and closing the browser tab shows the browser's own
 * warning. `null` means nothing is unsaved.
 */
export function useUnsavedChanges(summary: string | null, handlers: UnsavedHandlers): void {
  const { registerUnsaved, setUnsavedSummary } = usePiece();
  // The handlers are new functions on every render; handing them over costs nothing and never
  // re-renders the page. Only the summary, a string, is state up there.
  useEffect(() => {
    registerUnsaved(handlers);
  });
  useEffect(() => {
    setUnsavedSummary(summary);
  }, [summary, setUnsavedSummary]);
  useEffect(
    () => () => {
      registerUnsaved(null);
      setUnsavedSummary(null);
    },
    [registerUnsaved, setUnsavedSummary],
  );
}

/** Navigation state that says "already saved": the guard lets it through. */
export const SAVED_NAVIGATION = { savedBeforeLeaving: true } as const;
