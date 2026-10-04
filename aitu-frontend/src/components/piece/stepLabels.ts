/** The names of the five steps of the flow page, as their tabs and buttons say them. */

import type { PieceStep } from "../../api";

export const STEP_LABELS: Record<PieceStep, string> = {
  source: "Source",
  audio: "Audio",
  notes: "Notes",
  hands: "Hands",
  sheet: "Sheet",
};
