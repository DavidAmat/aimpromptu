/** Compact transport shared by all matrix-driven views. */

import { useState } from "react";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import PauseIcon from "@mui/icons-material/Pause";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import ReplayIcon from "@mui/icons-material/Replay";
import { formatFrameLabel, formatTime, parseTime } from "../audio/time";
import { timestampSx } from "../ui";
import type { MatrixPlaybackController } from "./useMatrixPlayback";

export function PlaybackTransport({ playback }: { playback: MatrixPlaybackController }) {
  const [seekText, setSeekText] = useState("");
  const commitSeek = () => {
    const seconds = parseTime(seekText);
    if (seconds !== null) playback.seek(seconds);
  };

  return (
    <Stack
      direction={{ xs: "column", sm: "row" }}
      spacing={1}
      sx={{ alignItems: { sm: "center" }, flexWrap: "wrap" }}
    >
      <Button
        size="small"
        variant="contained"
        startIcon={playback.playing ? <PauseIcon /> : <PlayArrowIcon />}
        onClick={playback.playing ? playback.pause : () => void playback.play()}
      >
        {playback.playing ? "Pause" : "Play"}
      </Button>
      <Button size="small" startIcon={<ReplayIcon />} onClick={playback.restart}>
        Restart
      </Button>
      <Typography variant="body2" sx={timestampSx}>
        {formatFrameLabel(playback.currentFrame, playback.currentSeconds)}
      </Typography>
      <TextField
        label="Seek"
        size="small"
        value={seekText}
        onChange={(event) => setSeekText(event.target.value)}
        onKeyDown={(event) => event.key === "Enter" && commitSeek()}
        placeholder={formatTime(playback.currentSeconds)}
        sx={{ width: 132 }}
      />
      <Button size="small" onClick={commitSeek}>
        Go
      </Button>
    </Stack>
  );
}
