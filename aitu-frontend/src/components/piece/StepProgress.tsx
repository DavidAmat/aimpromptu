/**
 * A short job of the flow page in progress: what it is doing, how far it is, how long it has
 * taken. It stands on its own, so it takes the shared width of a progress bar, not the page's.
 */

import Box from "@mui/material/Box";
import LinearProgress from "@mui/material/LinearProgress";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { progressSx, timestampSx } from "../../ui";

export interface StepProgressProps {
  /** What the job is doing now, in words. */
  label: string;
  /** 0 to 100, or `null` while it is not known yet. */
  percent: number | null;
  /** Seconds since the job started. */
  elapsedSeconds: number;
}

export function StepProgress({ label, percent, elapsedSeconds }: StepProgressProps) {
  return (
    <Box sx={progressSx} role="status" aria-live="polite">
      <Stack direction="row" spacing={2} sx={{ mb: 0.5, justifyContent: "space-between" }}>
        <Typography variant="body2">{label}</Typography>
        <Typography variant="body2" color="text.secondary" sx={timestampSx}>
          {`${percent === null ? "" : `${Math.round(percent)}% · `}${elapsedSeconds.toFixed(1)} s`}
        </Typography>
      </Stack>
      <LinearProgress variant={percent === null ? "indeterminate" : "determinate"} value={percent ?? 0} />
    </Box>
  );
}

export default StepProgress;
