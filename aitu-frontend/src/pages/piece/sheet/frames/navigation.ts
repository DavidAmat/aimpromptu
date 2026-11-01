import type { RunChoice, SongRun } from "../../../../api";

/** Navigation state: the edit copy of a library version opened by **Enhance with AI** starts there the run the dialog
 * chose (implementation 04, Phase 4), with its model and number of batches (2026-10-30). */
export interface EnhanceWithAi {
  enhanceWithAi: SongRun;
  choice?: RunChoice;
}

export const enhanceWithAi = (run: SongRun, choice?: RunChoice): EnhanceWithAi => ({
  enhanceWithAi: run,
  ...(choice ? { choice } : {}),
});

const RUNS: readonly SongRun[] = ["all", "simplify-left", "simplify-right", "simplify-both"];

/** The run a navigation state asks for; `null`: none. */
export function songRunOf(state: unknown): SongRun | null {
  const run = (state as Partial<EnhanceWithAi> | null)?.enhanceWithAi;
  return RUNS.find((one) => one === run) ?? null;
}

/** The model and the number of batches a navigation state asks for (none: the defaults). */
export function runChoiceOf(state: unknown): RunChoice | undefined {
  return (state as Partial<EnhanceWithAi> | null)?.choice;
}
