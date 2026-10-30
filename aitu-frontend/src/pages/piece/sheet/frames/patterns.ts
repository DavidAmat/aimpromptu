/** The patterns of the catalog of Enhance with AI (implementation 04-3, Phase 4): their hand, names and drawings. */

import { API_BASE, type CatalogPattern } from "../../../../api";

export type CatalogHand = "left" | "right";

/** The drawing of a pattern's example, by the app's engine. */
export function drawingUrl(pattern: Pick<CatalogPattern, "hand" | "level" | "number">): string {
  return `${API_BASE}/sheet/levels/catalog/${pattern.hand}/${pattern.level.replace(" ", "-")}/${pattern.number}.svg`;
}

/** `medium 2`: a pattern as the user names it in the words. */
export const shortRef = (ref: string): string => ref.split(" ").slice(1).join(" ");
