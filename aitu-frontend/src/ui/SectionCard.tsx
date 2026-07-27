/** Bordered surface grouping one block of controls or content. */

import type { ReactNode } from "react";
import Box from "@mui/material/Box";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

export interface SectionCardProps {
  title?: string;
  description?: string;
  actions?: ReactNode;
  /** Removes the inner padding — for grids and canvases that manage their own. */
  flush?: boolean;
  children?: ReactNode;
}

export function SectionCard({ title, description, actions, flush, children }: SectionCardProps) {
  return (
    <Paper variant="outlined" sx={{ mb: 2, overflow: "hidden" }}>
      {title || actions ? (
        <Stack
          direction="row"
          spacing={1}
          sx={{
            px: 2,
            py: 1.5,
            borderBottom: 1,
            borderColor: "divider",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <Box>
            {title ? <Typography variant="h3">{title}</Typography> : null}
            {description ? (
              <Typography variant="body2" color="text.secondary">
                {description}
              </Typography>
            ) : null}
          </Box>
          {actions ? <Stack direction="row" spacing={1}>{actions}</Stack> : null}
        </Stack>
      ) : null}
      <Box sx={{ p: flush ? 0 : 2 }}>{children}</Box>
    </Paper>
  );
}

export default SectionCard;
