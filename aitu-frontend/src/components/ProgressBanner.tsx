/** Renders a `useProgress` state as a MUI progress bar with the stage name. */

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import LinearProgress from "@mui/material/LinearProgress";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import type { ProgressState } from "../hooks/useProgress";

export interface ProgressBannerProps {
  progress: ProgressState;
  /** Shown while running if the backend has not named a stage yet. */
  fallbackLabel?: string;
}

export function ProgressBanner({ progress, fallbackLabel = "Working" }: ProgressBannerProps) {
  const { status, event, percent, error } = progress;

  if (status === "idle") return null;

  if (status === "error") {
    return <Alert severity="error">{error ?? "Progress stream failed"}</Alert>;
  }

  const label = event?.stage ?? fallbackLabel;

  return (
    <Box sx={{ width: "100%" }}>
      <Stack direction="row" sx={{ mb: 0.5, justifyContent: "space-between" }}>
        <Typography variant="body2">
          {label}
          {event?.message ? ` — ${event.message}` : ""}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {status === "done" ? "100%" : `${percent}%`}
        </Typography>
      </Stack>
      <LinearProgress variant="determinate" value={status === "done" ? 100 : percent} />
    </Box>
  );
}

export default ProgressBanner;
