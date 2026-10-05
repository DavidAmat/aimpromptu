/**
 * A group of content inside a page, with an optional small title and the controls that belong to
 * it. No description and no border: a group is told apart by space, not by a box (guidelines 5.2).
 * This replaces the old `SectionCard`, whose description was the text the guidelines remove.
 */

import type { ReactNode } from "react";
import Box from "@mui/material/Box";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

export interface SectionProps {
  title?: string;
  /** Controls for this group, beside its title. */
  actions?: ReactNode;
  children?: ReactNode;
}

export function Section({ title, actions, children }: SectionProps) {
  return (
    <Box component="section" sx={{ mb: 4 }}>
      {title || actions ? (
        <Stack direction="row" spacing={1} sx={{ alignItems: "center", mb: 1.5, minHeight: 32, flexWrap: "wrap", rowGap: 1 }}>
          {title ? <Typography variant="h3">{title}</Typography> : null}
          <Box sx={{ flexGrow: 1 }} />
          {actions}
        </Stack>
      ) : null}
      {children}
    </Box>
  );
}

export default Section;
