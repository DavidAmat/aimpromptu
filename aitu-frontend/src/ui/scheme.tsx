/**
 * The colour scheme in use, light or dark (implementation 02, Phase 4).
 *
 * MUI keeps the user's choice (`light`, `dark` or `system`) in the browser's storage and switches
 * its CSS variables at once, so everything styled through the theme follows by itself. Drawing code
 * reads `ui` instead (`tokens.ts`). `SchemeSync` copies the scheme in use into `ui` and tells every
 * `useScheme()` reader, so a canvas or an SVG re-renders with the new colours, and nothing is
 * remounted: a sheet with unsaved changes keeps them.
 */

import type { ReactNode } from "react";
import { useColorScheme } from "@mui/material/styles";
import { SchemeContext } from "./schemeContext";
import { applyScheme, type SchemeName } from "./tokens";

export function SchemeSync({ children }: { children: ReactNode }) {
  const { mode, systemMode } = useColorScheme();
  const scheme: SchemeName = (mode === "system" ? systemMode : mode) === "dark" ? "dark" : "light";
  // Before the children render, so every one of them reads the new colours. Idempotent.
  applyScheme(scheme);
  return <SchemeContext.Provider value={scheme}>{children}</SchemeContext.Provider>;
}
