/**
 * Transport plus the filters both animated views share.
 *
 * Two controls from the Epic 8 toolbar are gone: **BPM** and **Resolution**.
 * They used to re-derive the matrix the view was drawing, and there is no such
 * matrix now — the rectangles come from the recording itself. What is left is
 * only about listening and looking: what to hear, how fast, which stretch, and
 * whether to show the notes the pipeline throws away.
 *
 * Anything a single view needs and the other does not — zoom on the roll, the
 * lead time on the falling view — goes in `children` rather than a prop here.
 */

import type { ReactNode } from "react";
import Button from "@mui/material/Button";
import FormControlLabel from "@mui/material/FormControlLabel";
import MenuItem from "@mui/material/MenuItem";
import Stack from "@mui/material/Stack";
import Switch from "@mui/material/Switch";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { PlaybackTransport } from "./PlaybackTransport";
import type { PlaybackController, PlaybackSource } from "./usePlayback";

const SPEEDS = [0.25, 0.5, 0.75, 1, 1.25, 1.5, 2];

interface PlayerToolbarProps {
  playback: PlaybackController;
  source: PlaybackSource;
  onSourceChange: (source: PlaybackSource) => void;
  originalAvailable: boolean;
  speed: number;
  onSpeedChange: (speed: number) => void;
  rangeStart: number;
  rangeEnd: number;
  durationSeconds: number;
  onRangeChange: (start: number, end: number) => void;
  showArtifacts: boolean;
  onShowArtifactsChange: (show: boolean) => void;
  artifactCount: number;
  children?: ReactNode;
}

export function PlayerToolbar({
  playback,
  source,
  onSourceChange,
  originalAvailable,
  speed,
  onSpeedChange,
  rangeStart,
  rangeEnd,
  durationSeconds,
  onRangeChange,
  showArtifacts,
  onShowArtifactsChange,
  artifactCount,
  children,
}: PlayerToolbarProps) {
  // Changing what is playing while it plays leaves the clock anchored to a
  // sound that has stopped, so every one of these stops first.
  const rebuild = (work: () => void) => {
    playback.restart();
    work();
  };

  return (
    <Stack spacing={1.5}>
      <PlaybackTransport playback={playback} />
      <Stack
        direction={{ xs: "column", md: "row" }}
        spacing={1}
        sx={{ alignItems: { md: "center" }, flexWrap: "wrap", rowGap: 1 }}
      >
        <Typography variant="caption" color="text.secondary">
          Sound
        </Typography>
        <Button
          size="small"
          variant={source === "original" ? "contained" : "outlined"}
          disabled={!originalAvailable}
          onClick={() => rebuild(() => onSourceChange("original"))}
        >
          Original audio
        </Button>
        <Button
          size="small"
          variant={source === "piano" ? "contained" : "outlined"}
          onClick={() => rebuild(() => onSourceChange("piano"))}
        >
          Transcribed piano
        </Button>
        <TextField
          label="Speed"
          select
          size="small"
          value={speed}
          onChange={(event) => rebuild(() => onSpeedChange(Number(event.target.value)))}
          sx={{ width: 105 }}
        >
          {SPEEDS.map((option) => (
            <MenuItem key={option} value={option}>
              {option}×
            </MenuItem>
          ))}
        </TextField>
        <TextField
          label="From (s)"
          type="number"
          size="small"
          value={Number(rangeStart.toFixed(2))}
          onChange={(event) =>
            rebuild(() =>
              onRangeChange(
                Math.max(0, Math.min(Number(event.target.value) || 0, rangeEnd)),
                rangeEnd,
              ),
            )
          }
          sx={{ width: 105 }}
        />
        <TextField
          label="To (s)"
          type="number"
          size="small"
          value={Number(rangeEnd.toFixed(2))}
          onChange={(event) =>
            rebuild(() =>
              onRangeChange(
                rangeStart,
                Math.max(rangeStart, Math.min(Number(event.target.value) || 0, durationSeconds)),
              ),
            )
          }
          sx={{ width: 105 }}
        />
        {children}
        {artifactCount > 0 ? (
          <FormControlLabel
            sx={{ ml: { md: "auto" } }}
            control={
              <Switch
                size="small"
                checked={showArtifacts}
                onChange={(event) => onShowArtifactsChange(event.target.checked)}
              />
            }
            label={
              <Typography variant="caption">
                Show {artifactCount} filtered {artifactCount === 1 ? "note" : "notes"}
              </Typography>
            }
          />
        ) : null}
      </Stack>
    </Stack>
  );
}

export default PlayerToolbar;
