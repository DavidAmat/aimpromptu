/** Filters plus transport shared by Piano Roll and Notes Falling. */

import Button from "@mui/material/Button";
import MenuItem from "@mui/material/MenuItem";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import type { Granularity } from "../api";
import { TRANSCRIPTION_GRANULARITIES } from "../music/granularities";
import { PlaybackTransport } from "./PlaybackTransport";
import type {
  MatrixPlaybackController,
  PlaybackSource,
} from "./useMatrixPlayback";

interface PlayerToolbarProps {
  playback: MatrixPlaybackController;
  source: PlaybackSource;
  onSourceChange: (source: PlaybackSource) => void;
  originalAvailable: boolean;
  speed: number;
  onSpeedChange: (speed: number) => void;
  tempoBpm: number;
  onTempoChange: (tempoBpm: number) => void;
  granularity: Granularity;
  onGranularityChange: (granularity: Granularity) => void;
  rangeStart: number;
  rangeEnd: number;
  durationSeconds: number;
  onRangeChange: (start: number, end: number) => void;
}

export function PlayerToolbar({
  playback,
  source,
  onSourceChange,
  originalAvailable,
  speed,
  onSpeedChange,
  tempoBpm,
  onTempoChange,
  granularity,
  onGranularityChange,
  rangeStart,
  rangeEnd,
  durationSeconds,
  onRangeChange,
}: PlayerToolbarProps) {
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
        sx={{ alignItems: { md: "center" }, flexWrap: "wrap" }}
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
          {[0.5, 0.75, 1, 1.25, 1.5, 2].map((option) => (
            <MenuItem key={option} value={option}>
              {option}×
            </MenuItem>
          ))}
        </TextField>
        <TextField
          label="BPM"
          type="number"
          size="small"
          value={tempoBpm}
          onChange={(event) =>
            rebuild(() => onTempoChange(Math.max(20, Number(event.target.value) || 60)))
          }
          slotProps={{ htmlInput: { min: 20, max: 300 } }}
          sx={{ width: 95 }}
        />
        <TextField
          label="Resolution"
          select
          size="small"
          value={granularity}
          onChange={(event) =>
            rebuild(() => onGranularityChange(event.target.value as Granularity))
          }
          sx={{ minWidth: 180 }}
        >
          {TRANSCRIPTION_GRANULARITIES.map((option) => (
            <MenuItem key={option.value} value={option.value}>
              {option.label}
            </MenuItem>
          ))}
        </TextField>
        <TextField
          label="From (s)"
          type="number"
          size="small"
          value={rangeStart}
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
          value={rangeEnd}
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
      </Stack>
    </Stack>
  );
}
