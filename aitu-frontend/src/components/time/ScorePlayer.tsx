/**
 * Play the recording under the sheet, with a marker showing where in the piece it is.
 *
 * What plays is the original audio, never anything reconstructed from the grid. A sheet is a
 * reading of a performance and the performance is the recording, so the only honest thing to hear
 * is the thing that was played. It also makes the sheet checkable by ear: if the notes on the page
 * and the sound drift apart, the page is wrong.
 *
 * The marker is placed by time, not by column. A column is a slice of wall clock, so where the
 * playing is at a given second is arithmetic, not a lookup.
 */

import { useEffect, useRef, useState } from "react";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import LinearProgress from "@mui/material/LinearProgress";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import PauseIcon from "@mui/icons-material/Pause";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import ReplayIcon from "@mui/icons-material/Replay";
import { API_BASE } from "../../api";
import { formatTime } from "../../audio/time";

export interface ScorePlayerProps {
  audioUuid: string;
  /** Where the sheet ends, in seconds. The recording may run on past it. */
  scoreSeconds: number;
}

export function ScorePlayer({ audioUuid, scoreSeconds }: ScorePlayerProps) {
  const audio = useRef<HTMLAudioElement | null>(null);
  const [playing, setPlaying] = useState(false);
  const [seconds, setSeconds] = useState(0);

  useEffect(() => {
    const element = new Audio(`${API_BASE}/audio/${audioUuid}/file`);
    audio.current = element;
    const tick = () => setSeconds(element.currentTime);
    const stop = () => setPlaying(false);
    element.addEventListener("timeupdate", tick);
    element.addEventListener("ended", stop);
    element.addEventListener("pause", stop);
    return () => {
      element.pause();
      element.removeEventListener("timeupdate", tick);
      element.removeEventListener("ended", stop);
      element.removeEventListener("pause", stop);
      audio.current = null;
    };
  }, [audioUuid]);

  const toggle = () => {
    const element = audio.current;
    if (!element) return;
    if (element.paused) {
      void element.play();
      setPlaying(true);
    } else {
      element.pause();
    }
  };

  const restart = () => {
    const element = audio.current;
    if (!element) return;
    element.currentTime = 0;
    setSeconds(0);
  };

  const throughScore = scoreSeconds > 0 ? Math.min(100, (seconds / scoreSeconds) * 100) : 0;

  return (
    <Stack spacing={1}>
      <Stack direction="row" spacing={1.5} sx={{ alignItems: "center" }}>
        <Button
          variant="outlined"
          size="small"
          onClick={toggle}
          startIcon={playing ? <PauseIcon /> : <PlayArrowIcon />}
        >
          {playing ? "Pause" : "Play the recording"}
        </Button>
        <Button size="small" onClick={restart} startIcon={<ReplayIcon />}>
          Back to the start
        </Button>
        <Typography variant="body2" color="text.secondary">
          {formatTime(seconds)} of {formatTime(scoreSeconds)} written
        </Typography>
      </Stack>
      <Box>
        <LinearProgress variant="determinate" value={throughScore} />
      </Box>
      <Typography variant="caption" color="text.secondary">
        What plays is the recording itself, exactly as it was performed. Nothing here is reconstructed
        from the sheet, so the two can be compared by ear.
      </Typography>
    </Stack>
  );
}

export default ScorePlayer;
