/**
 * Nothing here yet: one line, and the action that creates the first one (the guidelines' empty
 * state, section 7). It never explains how the feature works.
 */

import type { ReactNode } from "react";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

export interface EmptyStateProps {
  /** One short line: "No projects yet". */
  message: string;
  /** The button that creates the first one. */
  action?: ReactNode;
}

export function EmptyState({ message, action }: EmptyStateProps) {
  return (
    <Stack spacing={2} sx={{ alignItems: "center", py: 8 }}>
      <Typography color="text.secondary">{message}</Typography>
      {action}
    </Stack>
  );
}

export default EmptyState;
