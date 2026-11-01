/** The patterns of the catalog of Enhance with AI (implementation 04-3, Phase 4): their hand, names and drawings. */

import { API_BASE, type CatalogPattern, type LevelName } from "../../../../api";

export type CatalogHand = "left" | "right";

/** The drawing of a pattern's example, by the app's engine. */
export function drawingUrl(pattern: Pick<CatalogPattern, "hand" | "level" | "number">): string {
  return `${API_BASE}/sheet/levels/catalog/${pattern.hand}/${pattern.level.replace(" ", "-")}/${pattern.number}.svg`;
}

/** `medium 2`: a pattern as the user names it in the words. */
export const shortRef = (ref: string): string => ref.split(" ").slice(1).join(" ");

/** "Easy, left hand · easy 1 (Strict)". */
export function runTitle(run: {
  level: LevelName | Record<"right" | "left", LevelName> | null;
  hand: string | null;
  patterns: string[];
  strict: string[];
}): string {
  const level =
    run.level === null
      ? "A level"
      : typeof run.level === "string"
        ? run.level[0].toUpperCase() + run.level.slice(1)
        : `Right ${run.level.right}, left ${run.level.left}`;
  const hand = run.hand === "both" || run.hand === null ? "" : `, ${run.hand} hand`;
  const patterns = run.patterns.map((ref) => `${shortRef(ref)}${run.strict.includes(ref) ? " (Strict)" : ""}`);
  return `${level}${hand}${patterns.length ? ` · ${patterns.join(", ")}` : ""}`;
}
