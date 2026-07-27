/**
 * Audacity-like range picker over an audio's waveform.
 *
 * Used wherever a sub-range must be chosen: the Input tab (transcribe only this
 * passage), the editing epic's staged re-recording, and range playback.
 *
 * Playback is done with a plain `<audio>` element seeking within the already
 * downloaded file — no round trip per range, and the cursor is just
 * `currentTime`. The element stops itself at the range end.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import StopIcon from "@mui/icons-material/Stop";
import { audioApi, type WaveformPeaks } from "../../api";
import { clamp, formatTime, formatTimeShort, parseTime } from "../../audio/time";
import { semantic } from "../../ui";
import WaveformView from "./WaveformView";

export interface AudioRange {
  startSeconds: number;
  endSeconds: number;
}

export interface WaveformRangeSelectorProps {
  audioUuid: string;
  /** Known duration; otherwise taken from the waveform payload. */
  durationSeconds?: number;
  /** Emitted whenever the range changes. */
  onRangeChange?: (range: AudioRange) => void;
  points?: number;
  height?: number;
}

type Handle = "start" | "end" | null;

/** Peaks tagged with the request they belong to, so nothing stale leaks through. */
interface PeaksState {
  key: string;
  peaks: WaveformPeaks | null;
  error: string | null;
}

export function WaveformRangeSelector({
  audioUuid,
  durationSeconds,
  onRangeChange,
  points = 1000,
  height = 120,
}: WaveformRangeSelectorProps) {
  const requestKey = `${audioUuid}:${points}`;
  const [loaded, setLoaded] = useState<PeaksState>({ key: "", peaks: null, error: null });
  const [range, setRange] = useState<AudioRange>({ startSeconds: 0, endSeconds: 0 });
  const [startText, setStartText] = useState("00:00.000");
  const [endText, setEndText] = useState("00:00.000");
  const [dragging, setDragging] = useState<Handle>(null);
  const [cursor, setCursor] = useState<number | null>(null);
  const [playing, setPlaying] = useState(false);

  const trackRef = useRef<HTMLDivElement | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const frameRef = useRef<number | null>(null);

  // Derived, not assigned in an effect: a new key means "loading", full stop.
  const current =
    loaded.key === requestKey ? loaded : { key: requestKey, peaks: null, error: null };
  const peaks = current.peaks;
  const loadError = current.error;
  const duration = peaks?.durationSeconds ?? durationSeconds ?? 0;

  // ---------------------------------------------------------------- loading

  useEffect(() => {
    const controller = new AbortController();

    audioApi
      .waveform(audioUuid, points, controller.signal)
      .then((fetched) => {
        setLoaded({ key: requestKey, peaks: fetched, error: null });
        setRange({ startSeconds: 0, endSeconds: fetched.durationSeconds });
        setStartText(formatTime(0));
        setEndText(formatTime(fetched.durationSeconds));
      })
      .catch((caught: unknown) => {
        if (controller.signal.aborted) return;
        setLoaded({
          key: requestKey,
          peaks: null,
          error: caught instanceof Error ? caught.message : "Could not load the waveform.",
        });
      });

    return () => controller.abort();
  }, [audioUuid, points, requestKey]);

  const applyRange = useCallback(
    (next: AudioRange) => {
      setRange(next);
      setStartText(formatTime(next.startSeconds));
      setEndText(formatTime(next.endSeconds));
      onRangeChange?.(next);
    },
    [onRangeChange],
  );

  // --------------------------------------------------------------- dragging

  const secondsAtClientX = useCallback(
    (clientX: number) => {
      const element = trackRef.current;
      if (!element || duration === 0) return 0;
      const bounds = element.getBoundingClientRect();
      const fraction = clamp((clientX - bounds.left) / bounds.width, 0, 1);
      return fraction * duration;
    },
    [duration],
  );

  useEffect(() => {
    if (dragging === null) return;

    const move = (event: PointerEvent) => {
      const seconds = secondsAtClientX(event.clientX);
      setRange((current) => {
        // Handles cannot cross: each is clamped by the other.
        const next =
          dragging === "start"
            ? { ...current, startSeconds: clamp(seconds, 0, current.endSeconds) }
            : { ...current, endSeconds: clamp(seconds, current.startSeconds, duration) };
        setStartText(formatTime(next.startSeconds));
        setEndText(formatTime(next.endSeconds));
        return next;
      });
    };

    // Emit once, at pointer-up, so the parent is not spammed on every frame.
    const up = () => {
      setDragging(null);
      setRange((current) => {
        onRangeChange?.(current);
        return current;
      });
    };

    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
    return () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
    };
  }, [dragging, duration, secondsAtClientX, onRangeChange]);

  // -------------------------------------------------------------- text input

  const commitStart = () => {
    const parsed = parseTime(startText);
    if (parsed === null) {
      setStartText(formatTime(range.startSeconds));
      return;
    }
    applyRange({ ...range, startSeconds: clamp(parsed, 0, range.endSeconds) });
  };

  const commitEnd = () => {
    const parsed = parseTime(endText);
    if (parsed === null) {
      setEndText(formatTime(range.endSeconds));
      return;
    }
    applyRange({ ...range, endSeconds: clamp(parsed, range.startSeconds, duration) });
  };

  // --------------------------------------------------------------- playback

  const stop = useCallback(() => {
    const element = audioRef.current;
    if (element) {
      element.pause();
      element.currentTime = range.startSeconds;
    }
    if (frameRef.current !== null) cancelAnimationFrame(frameRef.current);
    frameRef.current = null;
    setPlaying(false);
    setCursor(null);
  }, [range.startSeconds]);

  useEffect(() => stop, [stop]);

  const play = (whole: boolean) => {
    const element = audioRef.current;
    if (!element) return;

    const from = whole ? 0 : range.startSeconds;
    const to = whole ? duration : range.endSeconds;

    element.currentTime = from;
    void element.play();
    setPlaying(true);

    const follow = () => {
      const at = element.currentTime;
      setCursor(at);
      if (at >= to - 0.01) {
        element.pause();
        setPlaying(false);
        setCursor(to);
        frameRef.current = null;
        return;
      }
      frameRef.current = requestAnimationFrame(follow);
    };
    frameRef.current = requestAnimationFrame(follow);
  };

  // ----------------------------------------------------------------- render

  if (loadError) return <Alert severity="error">{loadError}</Alert>;
  if (!peaks) {
    return (
      <Stack direction="row" spacing={1} sx={{ alignItems: "center", py: 2 }}>
        <CircularProgress size={18} />
        <Typography variant="body2" color="text.secondary">
          Loading waveform…
        </Typography>
      </Stack>
    );
  }

  const percent = (seconds: number) => `${duration ? (seconds / duration) * 100 : 0}%`;

  return (
    <Stack spacing={1.5}>
      <Box
        ref={trackRef}
        sx={{ position: "relative", userSelect: "none", touchAction: "none", cursor: "text" }}
      >
        <WaveformView
          peaks={peaks}
          height={height}
          selection={range}
          cursorSeconds={cursor}
        />

        {(["start", "end"] as const).map((which) => {
          const seconds = which === "start" ? range.startSeconds : range.endSeconds;
          return (
            <Tooltip
              key={which}
              open={dragging === which}
              title={formatTime(seconds)}
              placement="top"
              arrow
            >
              <Box
                role="slider"
                aria-label={`${which} of range`}
                aria-valuenow={seconds}
                tabIndex={0}
                onPointerDown={() => setDragging(which)}
                sx={{
                  position: "absolute",
                  top: 0,
                  left: percent(seconds),
                  height: "100%",
                  width: 12,
                  ml: "-6px",
                  cursor: "ew-resize",
                  "&::before": {
                    content: '""',
                    position: "absolute",
                    left: 5,
                    top: 0,
                    bottom: 0,
                    width: 2,
                    backgroundColor: semantic.waveform.selection,
                  },
                }}
              />
            </Tooltip>
          );
        })}
      </Box>

      <Stack direction="row" sx={{ justifyContent: "space-between" }}>
        <Typography variant="caption" color="text.secondary">
          0:00
        </Typography>
        <Typography variant="caption" color="text.secondary">
          {formatTimeShort(duration)}
        </Typography>
      </Stack>

      <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} sx={{ alignItems: "center" }}>
        <TextField
          label="Start"
          size="small"
          value={startText}
          onChange={(event) => setStartText(event.target.value)}
          onBlur={commitStart}
          onKeyDown={(event) => event.key === "Enter" && commitStart()}
          placeholder="mm:ss.mmm"
          sx={{ width: 140 }}
        />
        <TextField
          label="End"
          size="small"
          value={endText}
          onChange={(event) => setEndText(event.target.value)}
          onBlur={commitEnd}
          onKeyDown={(event) => event.key === "Enter" && commitEnd()}
          placeholder="mm:ss.mmm"
          sx={{ width: 140 }}
        />
        <Typography variant="body2" color="text.secondary">
          {formatTime(range.endSeconds - range.startSeconds)} selected
        </Typography>

        <Box sx={{ flexGrow: 1 }} />

        {playing ? (
          <Button size="small" startIcon={<StopIcon />} onClick={stop}>
            Stop
          </Button>
        ) : (
          <>
            <Button size="small" startIcon={<PlayArrowIcon />} onClick={() => play(false)}>
              Play range
            </Button>
            <Button size="small" onClick={() => play(true)}>
              Play all
            </Button>
          </>
        )}
      </Stack>

      <Box component="audio" ref={audioRef} src={audioApi.fileUrl(audioUuid)} preload="auto" hidden />
    </Stack>
  );
}

export default WaveformRangeSelector;
