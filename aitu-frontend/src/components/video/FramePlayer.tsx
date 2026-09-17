/**
 * The player: the sampled frames, stepped and played (Task 3.3.1).
 *
 * **It draws the sampled frames, not the video element**, so what the user sees
 * is exactly what the detector sees — the same JPEG, at the same width, with the
 * same coordinates (V-35). A video element would play more smoothly and would
 * show a picture nothing else in this section ever reads.
 *
 * Spacebar plays and pauses, the left and right arrows step one sampled frame,
 * and the progress bar shows mm:ss and can be dragged.
 *
 * **It plays the original audio, and the audio is the clock** (changed after
 * Phase 4, at the user's direction; Task 3.3.1 first said this player shows the
 * picture only). The audio was taken out of this very video file with ffmpeg on
 * the same download (V-03), so its t = 0 *is* the video's t = 0 and there is
 * nothing to align: the frame on screen is `currentTime / sampleMs`, read off the
 * audio element every animation frame. Driving it the other way — a timer that
 * counts frames and an audio element told to keep up — is what drifts, because a
 * `setInterval` of 100 ms is not 100 ms and an audio clock is.
 *
 * Without an audio URL, or with the sound turned off, playing falls back to that
 * timer, which is what Phase 3 had. The next few frames are fetched ahead of the
 * one on screen either way, so the browser has them before the clock asks.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import Box from "@mui/material/Box";
import IconButton from "@mui/material/IconButton";
import Slider from "@mui/material/Slider";
import Stack from "@mui/material/Stack";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { formatTime } from "../../audio/time";
import { surface } from "../../ui";
import FrameCanvas, { type FrameCanvasProps } from "./FrameCanvas";

export interface FramePlayerProps {
  /** The URL of one sampled frame by its index, counted from zero. */
  frameUrl: (index: number) => string;
  frameCount: number;
  /** How often we look at the video, in milliseconds. Never `frameMs` (V-04). */
  sampleMs: number;
  frameWidth: number;
  frameHeight: number;
  index: number;
  onIndexChange: (index: number) => void;
  /** Drawn on the picture, in its own coordinates, with the live scale. */
  children?: (scale: number) => ReactNode;
  height?: number;
  /**
   * The original audio of this same video. Given, the player plays it and takes
   * its clock from it; left out, there is no speaker button and playing is the
   * timer it always was.
   */
  audioUrl?: string;
  /**
   * Passed straight through to the canvas, so a screen can put a gesture of its
   * own on the picture — picking a note, or drawing one the reading missed —
   * without the player knowing what the gesture is (Task 4.3.1).
   */
  onPictureMouseDown?: FrameCanvasProps["onPictureMouseDown"];
  onPictureClick?: FrameCanvasProps["onPictureClick"];
  panDisabled?: boolean;
}

/** How many frames ahead are fetched, so the clock never waits on the network. */
const PRELOAD = 6;

export function FramePlayer({
  frameUrl,
  frameCount,
  sampleMs,
  frameWidth,
  frameHeight,
  index,
  onIndexChange,
  children,
  height = 520,
  audioUrl,
  onPictureMouseDown,
  onPictureClick,
  panDisabled = false,
}: FramePlayerProps) {
  const [playing, setPlaying] = useState(false);
  const [sound, setSound] = useState(true);
  const surfaceRef = useRef<HTMLDivElement | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const last = Math.max(0, frameCount - 1);
  const clamp = useCallback(
    (value: number) => Math.max(0, Math.min(last, Math.round(value))),
    [last],
  );

  // Where the bar is, readable from inside the play loop without making the loop
  // depend on it. The loop sets the index dozens of times a second, so an effect
  // that watched it would tear itself down and build itself up just as often.
  const indexRef = useRef(index);
  useEffect(() => {
    indexRef.current = index;
  }, [index]);

  const audioFor = useCallback(() => {
    if (!audioUrl) return null;
    const current = audioRef.current;
    if (!current || current.getAttribute("src") !== audioUrl) {
      current?.pause();
      const next = new Audio();
      next.setAttribute("src", audioUrl);
      next.preload = "auto";
      audioRef.current = next;
    }
    return audioRef.current;
  }, [audioUrl]);

  /** Move the bar, and move the audio with it: one position, two surfaces. */
  const seek = useCallback(
    (value: number) => {
      const next = clamp(value);
      onIndexChange(next);
      if (audioRef.current) audioRef.current.currentTime = (next * sampleMs) / 1000;
    },
    [clamp, onIndexChange, sampleMs],
  );

  // Playing. With the audio it is the audio's clock, read every animation frame;
  // without it, a timer. Either way it stops at the end rather than wrapping: a
  // video that starts again by itself is one you cannot look at the last frame of.
  useEffect(() => {
    if (!playing) {
      audioRef.current?.pause();
      return;
    }
    const audio = sound ? audioFor() : null;
    if (audio) {
      audio.currentTime = (indexRef.current * sampleMs) / 1000;
      void audio.play().catch(() => setSound(false));
      let frame = 0;
      const tick = () => {
        const at = clamp((audio.currentTime * 1000) / sampleMs);
        onIndexChange(at);
        if (audio.ended || at >= last) {
          setPlaying(false);
          return;
        }
        frame = window.requestAnimationFrame(tick);
      };
      frame = window.requestAnimationFrame(tick);
      return () => {
        window.cancelAnimationFrame(frame);
        audio.pause();
      };
    }
    const handle = window.setInterval(() => {
      const next = indexRef.current + 1;
      onIndexChange(next > last ? last : next);
      if (next >= last) setPlaying(false);
    }, sampleMs);
    return () => window.clearInterval(handle);
  }, [playing, sound, audioFor, clamp, last, sampleMs, onIndexChange]);

  // The audio element outlives a render but not the page. Nothing else stops it,
  // so a tab left while it plays would keep playing from nowhere.
  useEffect(
    () => () => {
      audioRef.current?.pause();
      audioRef.current = null;
    },
    [],
  );

  // The next few frames, fetched into the browser's cache before they are shown.
  useEffect(() => {
    for (let ahead = 1; ahead <= PRELOAD; ahead += 1) {
      const next = index + ahead;
      if (next <= last) new Image().src = frameUrl(next);
    }
  }, [index, last, frameUrl]);

  /**
   * Spacebar and the arrows, while this player has the keyboard. They are caught
   * on the player's own element and not on the window, so typing a URL into a
   * field on the same page never steps the video.
   */
  const onKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === " ") {
      event.preventDefault();
      setPlaying((was) => !was);
    } else if (event.key === "ArrowLeft") {
      event.preventDefault();
      setPlaying(false);
      seek(index - (event.shiftKey ? 10 : 1));
    } else if (event.key === "ArrowRight") {
      event.preventDefault();
      setPlaying(false);
      seek(index + (event.shiftKey ? 10 : 1));
    }
  };

  const seconds = (index * sampleMs) / 1000;
  const total = (last * sampleMs) / 1000;

  return (
    <Stack
      spacing={1}
      ref={surfaceRef}
      tabIndex={0}
      onKeyDown={onKeyDown}
      sx={{ outline: "none" }}
    >
      <FrameCanvas
        imageUrl={frameUrl(index)}
        imageWidth={frameWidth}
        imageHeight={frameHeight}
        height={height}
        onPictureMouseDown={onPictureMouseDown}
        onPictureClick={onPictureClick}
        panDisabled={panDisabled}
      >
        {children}
      </FrameCanvas>

      <Stack direction="row" spacing={1.5} sx={{ alignItems: "center" }}>
        <IconButton size="small" onClick={() => setPlaying((was) => !was)} aria-label="play">
          <Box component="span" sx={{ fontSize: 18, lineHeight: 1 }}>
            {playing ? "❚❚" : "▶"}
          </Box>
        </IconButton>
        {audioUrl ? (
          <Tooltip title={sound ? "Sound on — the audio is the clock" : "Sound off"}>
            <IconButton
              size="small"
              onClick={() => setSound((was) => !was)}
              aria-label={sound ? "sound on" : "sound off"}
            >
              <Box component="span" sx={{ fontSize: 16, lineHeight: 1 }}>
                {sound ? "🔊" : "🔇"}
              </Box>
            </IconButton>
          </Tooltip>
        ) : null}
        <Typography variant="caption" sx={{ whiteSpace: "nowrap", minWidth: 68 }}>
          {formatTime(seconds)}
        </Typography>
        <Slider
          size="small"
          min={0}
          max={last}
          value={index}
          onChange={(_, value) => seek(value as number)}
          sx={{ flexGrow: 1 }}
        />
        <Typography variant="caption" sx={{ whiteSpace: "nowrap", minWidth: 68 }}>
          {formatTime(total)}
        </Typography>
      </Stack>

      <Typography variant="caption" sx={{ color: surface.mutedText }}>
        Frame {index + 1} of {frameCount} · click the picture, then spacebar plays and pauses, the
        arrows step one sampled frame and shift with an arrow steps ten. Drag the bar to move
        {audioUrl
          ? " — it moves the audio with it, and the audio of this same video is what the playing follows."
          : "."}
      </Typography>
    </Stack>
  );
}

export default FramePlayer;
