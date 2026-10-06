/** The colour scheme in use (`scheme.tsx` fills it). */

import { createContext, useContext } from "react";
import type { SchemeName } from "./tokens";

export const SchemeContext = createContext<SchemeName>("light");

/** The scheme in use. Call it in a component that draws with `ui`, so it re-renders on a change. */
export function useScheme(): SchemeName {
  return useContext(SchemeContext);
}
