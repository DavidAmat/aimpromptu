/**
 * The frame of every page (plan section 6.2): the sidebar on the left, the page on the right, no
 * top bar. The page scrolls; the sidebar stays.
 *
 * The page area has no padding of its own: a page with a list keeps a comfortable width
 * (`PageBody`), a page with a piano sheet or a piano roll takes the whole width it is given.
 */

import type { ReactNode } from "react";
import Box from "@mui/material/Box";

export interface AppShellProps {
  sidebar: ReactNode;
  children: ReactNode;
}

export function AppShell({ sidebar, children }: AppShellProps) {
  return (
    <Box sx={{ display: "flex", minHeight: "100vh", backgroundColor: "background.default" }}>
      {sidebar}
      <Box component="main" sx={{ flex: 1, minWidth: 0 }}>
        {children}
      </Box>
    </Box>
  );
}

/**
 * The body of a page: the side gutters and, unless `wide`, a width that keeps a list readable on a
 * wide screen (a row of a list should not be two metres long).
 */
export function PageBody({ wide, children }: { wide?: boolean; children: ReactNode }) {
  return (
    <Box sx={{ px: { xs: 2, md: 4 }, pt: 1.5, pb: 6, maxWidth: wide ? "none" : 960, mx: wide ? 0 : "auto" }}>
      {children}
    </Box>
  );
}

export default AppShell;
