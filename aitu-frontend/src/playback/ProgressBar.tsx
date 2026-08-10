/**
 * The scrub bar: where you are in the piece, and the only place the position is
 * set from.
 *
 * Both animated views used to have no way of moving through a five-minute
 * recording except typing a timestamp. This is that missing control — click
 * anywhere to jump, drag the handle to scan, and the selected range is shaded so
 * a `From`/`To` narrowing is visible rather than only numeric.
 *
 * It deliberately owns the position. On the roll, clicking the notes themselves
 * now *selects* them, so seeking needs a surface of its own; giving the two
 * gestures separate places is what lets a click mean one thing in each.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import Box from "@mui/material/Box";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { formatTime } from "../audio/time";
import { grays, semantic, surface, timestampSx } from "../ui";
import type { PlaybackController } from "./usePlayback";

const TRACK_HEIGHT = 8;
const HANDLE_RADIUS = 8;

interface ProgressBarProps {
  playback: PlaybackController;
  durationSeconds: number;
  /** The playable stretch, shaded on the track. */
  rangeStart: number;
  rangeEnd: number;
}

export function ProgressBar({
  playback,
  durationSeconds,
  rangeStart,
  rangeEnd,
}: ProgressBarProps) {
  const trackRef = useRef<HTMLDivElement | null>(null);
  const [scrubbing, setScrubbing] = useState(false);
  const total = Math.max(durationSeconds, 0.001);

  const secondsAt = useCallback(
    (clientX: number) => {
      const track = trackRef.current;
      if (!track) return 0;
      const bounds = track.getBoundingClientRect();
      const fraction = (clientX - bounds.left) / Math.max(1, bounds.width);
      return Math.min(total, Math.max(0, fraction * total));
    },
    [total],
  );

  // Listening on the window, not the track, so a drag that leaves the bar keeps
  // scrubbing and a mouse released anywhere still ends it. A pointer capture on
  // the handle would not survive the handle being re-rendered under the cursor,
  // which it is on every frame while playing.
  useEffect(() => {
    if (!scrubbing) return;
    const move = (event: PointerEvent) => playback.seek(secondsAt(event.clientX));
    const up = () => setScrubbing(false);
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
    window.addEventListener("pointercancel", up);
    return () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
      window.removeEventListener("pointercancel", up);
    };
  }, [playback, scrubbing, secondsAt]);

  const fraction = Math.min(1, Math.max(0, playback.currentSeconds / total));
  const rangeLeft = Math.min(1, Math.max(0, rangeStart / total));
  const rangeWidth = Math.min(1, Math.max(0, (rangeEnd - rangeStart) / total));

  return (
    <Stack direction="row" spacing={1.5} sx={{ alignItems: "center", width: "100%" }}>
      <Typography variant="body2" sx={{ ...timestampSx, flexShrink: 0 }}>
        {formatTime(playback.currentSeconds)}
      </Typography>

      <Box
        ref={trackRef}
        role="slider"
        tabIndex={0}
        aria-label="Position in the piece"
        aria-valuemin={0}
        aria-valuemax={total}
        aria-valuenow={playback.currentSeconds}
        aria-valuetext={formatTime(playback.currentSeconds)}
        onPointerDown={(event) => {
          event.preventDefault();
          setScrubbing(true);
          playback.seek(secondsAt(event.clientX));
        }}
        onKeyDown={(event) => {
          // Arrows nudge, shift-arrows jump. Not Space: that is Play everywhere
          // in this app, and a focused scrub bar must not shadow it.
          const step = event.shiftKey ? 10 : 1;
          if (event.key === "ArrowLeft") playback.seek(playback.currentSeconds - step);
          else if (event.key === "ArrowRight") playback.seek(playback.currentSeconds + step);
          else if (event.key === "Home") playback.seek(0);
          else if (event.key === "End") playback.seek(total);
          else return;
          event.preventDefault();
        }}
        sx={{
          position: "relative",
          flexGrow: 1,
          height: HANDLE_RADIUS * 2 + 6,
          display: "flex",
          alignItems: "center",
          cursor: "pointer",
          touchAction: "none",
          "&:focus-visible": { outline: "none" },
          "&:focus-visible .scrub-handle": {
            boxShadow: `0 0 0 3px ${semantic.status.info}55`,
          },
        }}
      >
        <Box
          sx={{
            position: "absolute",
            left: 0,
            right: 0,
            height: TRACK_HEIGHT,
            borderRadius: TRACK_HEIGHT,
            backgroundColor: surface.line,
            overflow: "hidden",
          }}
        >
          <Box
            sx={{
              position: "absolute",
              left: `${rangeLeft * 100}%`,
              width: `${rangeWidth * 100}%`,
              top: 0,
              bottom: 0,
              backgroundColor: grays.silver,
            }}
          />
          <Box
            sx={{
              position: "absolute",
              left: 0,
              width: `${fraction * 100}%`,
              top: 0,
              bottom: 0,
              backgroundColor: semantic.waveform.cursor,
            }}
          />
        </Box>
        <Box
          className="scrub-handle"
          sx={{
            position: "absolute",
            left: `${fraction * 100}%`,
            width: HANDLE_RADIUS * 2,
            height: HANDLE_RADIUS * 2,
            ml: `-${HANDLE_RADIUS}px`,
            borderRadius: "50%",
            backgroundColor: semantic.waveform.cursor,
            border: 2,
            borderColor: surface.panel,
            transition: scrubbing ? "none" : "left 60ms linear",
            pointerEvents: "none",
          }}
        />
      </Box>

      <Typography variant="body2" sx={{ ...timestampSx, flexShrink: 0, color: "text.secondary" }}>
        {formatTime(durationSeconds)}
      </Typography>
    </Stack>
  );
}

export default ProgressBar;
