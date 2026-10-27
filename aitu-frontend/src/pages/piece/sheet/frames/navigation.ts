import type { SongRun } from "../../../../api";

/** Navigation state: the edit copy of a library version opened by **Enhance with AI** starts there the run the dialog
 * chose (implementation 04, Phase 4). */
export interface EnhanceWithAi {
  enhanceWithAi: SongRun;
}

export const enhanceWithAi = (run: SongRun): EnhanceWithAi => ({ enhanceWithAi: run });

const RUNS: readonly SongRun[] = ["all", "simplify-left", "simplify-right", "simplify-both"];

/** The run a navigation state asks for; `null`: none. */
export function songRunOf(state: unknown): SongRun | null {
  const run = (state as Partial<EnhanceWithAi> | null)?.enhanceWithAi;
  return RUNS.find((one) => one === run) ?? null;
}
