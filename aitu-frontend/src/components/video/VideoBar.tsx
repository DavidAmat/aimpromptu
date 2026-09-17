/**
 * Which video, and how far it has got — the one line every Video to Notes tab
 * starts with.
 *
 * The work on a video is five steps in order: download it, sample its frames,
 * fit the piano on one of them, measure how fast the roll falls, read it. Each
 * tab does one part, so each tab has to say the same thing about where the video
 * is — what is done, and what the next step is. That line is this component.
 */

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import MenuItem from "@mui/material/MenuItem";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import type { ReactNode } from "react";
import type { VideoSummary } from "../../api/video";
import { formatTimeShort } from "../../audio/time";
import { palette, surface } from "../../ui";
import { steps } from "./videoSteps";

export interface VideoBarProps {
  videos: VideoSummary[] | null;
  selected: string | null;
  onSelect: (audioUuid: string) => void;
  /** Extra controls for the tab this bar is on. */
  children?: ReactNode;
}

/** Megabytes, to one decimal — the unit disk is talked about in. */
const mb = (bytes: number) => `${(bytes / 1e6).toFixed(1)} MB`;

export function VideoBar({ videos, selected, onSelect, children }: VideoBarProps) {
  const video = videos?.find((one) => one.metadata.audioUuid === selected) ?? null;

  return (
    <Stack spacing={1} sx={{ mb: 2 }}>
      <Stack direction="row" spacing={1} sx={{ alignItems: "center", flexWrap: "wrap", rowGap: 1 }}>
        <TextField
          select
          size="small"
          label="Video"
          value={videos && video ? selected : ""}
          onChange={(event) => onSelect(event.target.value)}
          disabled={!videos || videos.length === 0}
          sx={{ minWidth: 320 }}
        >
          {(videos ?? []).map((one) => (
            <MenuItem key={one.metadata.audioUuid} value={one.metadata.audioUuid}>
              {one.metadata.title || one.metadata.audioUuid}
            </MenuItem>
          ))}
        </TextField>
        {video ? (
          <Typography variant="caption" sx={{ color: surface.mutedText }}>
            {formatTimeShort(video.metadata.durationSeconds)} · {video.metadata.width}×
            {video.metadata.height} at {video.metadata.fps.toFixed(0)} fps · {mb(video.metadata.sizeBytes)}
            {video.metadata.framesBytes ? ` + ${mb(video.metadata.framesBytes)} of frames` : ""}
          </Typography>
        ) : null}
        <Box sx={{ flexGrow: 1 }} />
        {children}
      </Stack>

      {video ? (
        <Stack direction="row" spacing={0.75} sx={{ flexWrap: "wrap", rowGap: 0.75 }}>
          {steps(video).map((step) => (
            <Chip
              key={step.label}
              size="small"
              label={step.label}
              variant={step.done ? "filled" : "outlined"}
              sx={step.done ? { backgroundColor: palette.light.Green } : undefined}
            />
          ))}
        </Stack>
      ) : null}

      {videos && videos.length === 0 ? (
        <Alert severity="info" variant="outlined">
          No video yet. Paste a YouTube URL on the Video tab: the video is downloaded and the audio
          of that same video comes with it, so one URL gives one piece with both.
        </Alert>
      ) : null}
    </Stack>
  );
}

export default VideoBar;
