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

import { useCallback, useEffect, useRef, useState } from "react";
import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import PauseIcon from "@mui/icons-material/Pause";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import ReplayIcon from "@mui/icons-material/Replay";
import { API_BASE } from "../../api";
import { formatTime } from "../../audio/time";
import ProgressBar from "../../playback/ProgressBar";

export interface ScorePlayerProps {
  audioUuid: string;
  /** Space plays and pauses. Off for a second player on the same page (a passage's Current). */
  keys?: boolean;
  /** Changes when the audio of the piece changed under the page (a paste, its undo), so the new
   * file is loaded rather than the one the browser kept. */
  version?: string | number;
  /** Where the sheet ends, in seconds. The recording may run on past it. */
  scoreSeconds: number;
  /**
   * Where the recording is, reported on every animation frame while it plays.
   *
   * `timeupdate` fires about four times a second, which is enough for a clock reading and far too
   * coarse for a line moving across a page: it would jump about eight staff positions at a time. So
   * the position is read from the audio element on each frame the browser draws, and the element
   * stays the source of truth either way.
   */
  onTime?: (seconds: number | null) => void;
  /**
   * A handle on the transport, for everything that moves the recording without touching this bar.
   *
   * Dragging the cursor on the staves is the reason it exists: the sheet knows which moment the
   * pointer is over and nothing else does, while the audio element lives here and nothing else
   * should own it. A ref rather than a prop each way, because a seek is an event, not a value —
   * seeking twice to the same second has to move the recording twice.
   */
  controlsRef?: React.RefObject<ScorePlayerControls | null>;
  /**
   * Bring the cursor on screen. Called whenever the recording jumps somewhere the reader is not
   * looking: pressing space, or clicking the bar.
   */
  onScrollToCursor?: () => void;
  /**
   * Whether the recording is sounding, whenever that changes.
   *
   * `controls.toggle` is enough to start and stop it from elsewhere, but not to draw a button that
   * says which of the two it will do. A ref cannot: nothing re-renders when it changes.
   */
  onPlaying?: (playing: boolean) => void;
  /**
   * Only the scrub bar. The Sheet step plays and pauses from its floating bar, so it draws neither
   * the two buttons nor the paragraph under the bar (implementation 02, Phase 2).
   */
  compact?: boolean;
  /**
   * Nothing drawn but a refused start (Play mode, implementation 02, Phase 11): the page is the
   * sheet alone, and the recording is moved by the cursor on the staves.
   */
  headless?: boolean;
  /** Where the recording stops by itself, in seconds: the end of a stretch of a playlist. */
  stopAt?: number | null;
  /** The recording stopped by itself: at its end, or at `stopAt`. Not on a pause. */
  onEnded?: () => void;
  /**
   * How much of the file the browser loads before it is played. Play mode draws many parts on one
   * page and asks only for their length until one plays (a paused element keeps downloading).
   */
  preload?: "auto" | "metadata";
}

export interface ScorePlayerControls {
  /** Move the recording to a moment, playing or not. */
  seek: (seconds: number) => void;
  /** Start or stop, the same as the button does. */
  toggle: () => void;
}

export function ScorePlayer({
  audioUuid,
  version,
  scoreSeconds,
  onTime,
  controlsRef,
  onScrollToCursor,
  onPlaying,
  compact = false,
  keys = true,
  headless = false,
  stopAt = null,
  onEnded,
  preload = "auto",
}: ScorePlayerProps) {
  const audio = useRef<HTMLAudioElement | null>(null);
  const report = useRef(onTime);
  const ended = useRef(onEnded);
  const stopping = useRef(stopAt);
  const loading = useRef(preload);
  useEffect(() => {
    ended.current = onEnded;
    stopping.current = stopAt;
  }, [onEnded, stopAt]);
  // A new setting on the element itself: a new element would stop the recording and lose its place.
  useEffect(() => {
    loading.current = preload;
    if (audio.current) audio.current.preload = preload;
  }, [preload]);
  const [playing, setPlaying] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [error, setError] = useState<string | null>(null);

  // Held in a ref so a new callback identity does not tear the audio element down mid-play.
  useEffect(() => {
    report.current = onTime;
  }, [onTime]);

  // Said on every change rather than only on the button's own clicks: the recording also stops on
  // its own at the end, and anything drawing a play button elsewhere has to hear about that too.
  useEffect(() => {
    onPlaying?.(playing);
  }, [playing, onPlaying]);

  useEffect(() => {
    // A new address when the audio changed under the page (a paste, its undo): the browser keeps a
    // media file by its address and would play the old one.
    const element = new Audio(
      `${API_BASE}/audio/${audioUuid}/file${version !== undefined ? `?v=${encodeURIComponent(version)}` : ""}`,
    );
    element.preload = loading.current;
    audio.current = element;
    // Say where the recording is the moment there is one, not only when it moves. The line on the
    // staves is the thing a reader grabs to move the recording, so it has to be on the page before
    // anything has played — and the teardown below reports `null`, which means a remount that said
    // nothing would leave the page with no line and no way to get one back.
    report.current?.(0);
    const tick = () => setSeconds(element.currentTime);
    const stop = () => setPlaying(false);
    const finish = () => {
      setPlaying(false);
      ended.current?.();
    };
    element.addEventListener("timeupdate", tick);
    element.addEventListener("ended", finish);
    element.addEventListener("pause", stop);
    return () => {
      element.pause();
      element.removeEventListener("timeupdate", tick);
      element.removeEventListener("ended", finish);
      element.removeEventListener("pause", stop);
      // A paused element still downloads its file: without a source it stops, so a page that has
      // gone asks nothing more of a part that may be gone too (an edit copy saved, Phase 9).
      element.removeAttribute("src");
      element.load();
      audio.current = null;
      report.current?.(null);
    };
  }, [audioUuid, version]);

  // The line follows the recording, so it is read from the audio element rather than from a timer
  // of our own. A timer would drift against the sound within a minute and the page would be lying.
  useEffect(() => {
    if (!playing) return;
    let frame = 0;
    const step = () => {
      const element = audio.current;
      if (element) {
        report.current?.(element.currentTime);
        // The end of a stretch: stop there, as the end of the file would.
        const end = stopping.current;
        if (end !== null && end !== undefined && element.currentTime >= end) {
          element.pause();
          setPlaying(false);
          ended.current?.();
          return;
        }
      }
      frame = requestAnimationFrame(step);
    };
    frame = requestAnimationFrame(step);
    return () => cancelAnimationFrame(frame);
  }, [playing]);

  // `play()` returns a promise and it really can be refused: a browser blocks playback that no
  // click asked for, and a file that failed to load rejects too. Ignoring it left the button
  // reading "Pause" over a recording that was not playing, which is the worst of both.
  const toggle = useCallback(async () => {
    const element = audio.current;
    if (!element) return;
    if (!element.paused) {
      element.pause();
      return;
    }
    setError(null);
    try {
      await element.play();
      setPlaying(true);
    } catch (caught) {
      setPlaying(false);
      setError(
        caught instanceof Error
          ? `The recording did not start: ${caught.message}`
          : "The recording did not start.",
      );
    }
  }, []);

  /**
   * Move the recording to a moment. The one place that happens, whoever asked.
   *
   * Playing across the seek is deliberate: dragging the cursor while the piece plays should sound
   * like a needle being moved, not like a stop. The element keeps playing from wherever it lands.
   */
  const seekTo = useCallback(
    (target: number) => {
      const element = audio.current;
      if (!element) return;
      const bounded = Math.max(0, Math.min(target, scoreSeconds));
      element.currentTime = bounded;
      setSeconds(bounded);
      report.current?.(bounded);
    },
    [scoreSeconds],
  );

  useEffect(() => {
    if (!controlsRef) return;
    controlsRef.current = { seek: seekTo, toggle: () => void toggle() };
    return () => {
      controlsRef.current = null;
    };
  }, [controlsRef, seekTo, toggle]);

  /**
   * Space plays and pauses, and takes the reader to where the sound is before it starts.
   *
   * The scroll comes first on purpose. After dragging the cursor to a passage and scrolling away to
   * read something else, space would otherwise start playing a part of the page nobody is looking
   * at. Typing in a field or pressing a focused button keeps its own meaning of space, so those are
   * left alone — the button already toggles on space by being a button.
   */
  useEffect(() => {
    if (!keys) return undefined;
    const onKey = (event: KeyboardEvent) => {
      if (event.code !== "Space" && event.key !== " ") return;
      if (event.metaKey || event.ctrlKey || event.altKey) return;
      const target = event.target as HTMLElement | null;
      if (
        target &&
        (target.isContentEditable ||
          ["INPUT", "TEXTAREA", "SELECT", "BUTTON", "OPTION"].includes(target.tagName) ||
          target.closest('[role="combobox"], [role="textbox"], [role="button"]'))
      ) {
        return;
      }
      event.preventDefault();
      onScrollToCursor?.();
      void toggle();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onScrollToCursor, toggle, keys]);

  const restart = () => {
    seekTo(0);
    onScrollToCursor?.();
  };

  if (headless) {
    return error ? (
      <Alert severity="warning" onClose={() => setError(null)}>
        {error}
      </Alert>
    ) : null;
  }

  if (compact) {
    return (
      <Stack spacing={1}>
        {error ? (
          <Alert severity="warning" onClose={() => setError(null)}>
            {error}
          </Alert>
        ) : null}
        <ProgressBar currentSeconds={seconds} durationSeconds={scoreSeconds} onSeek={seekTo} />
      </Stack>
    );
  }

  return (
    <Stack spacing={1}>
      <Stack direction="row" spacing={1.5} sx={{ alignItems: "center" }}>
        <Button
          variant="outlined"
          size="small"
          onClick={() => void toggle()}
          startIcon={playing ? <PauseIcon /> : <PlayArrowIcon />}
        >
          {playing ? "Pause" : "Play the recording"}
        </Button>
        <Button size="small" onClick={restart} startIcon={<ReplayIcon />}>
          Back to the start
        </Button>
        <Typography variant="body2" color="text.secondary">
          of {formatTime(scoreSeconds)} written
        </Typography>
      </Stack>
      {error ? (
        <Alert severity="warning" onClose={() => setError(null)}>
          {error}
        </Alert>
      ) : null}
      {/*
        The same scrub bar the roll and the falling view carry. It was a plain
        progress meter you could click, which drew no handle — so there was
        nothing on the page that looked like it could be dragged, and scanning
        through a five-minute recording meant a series of guesses. Sharing the
        component means the reader learns one control for the whole app.
      */}
      <ProgressBar currentSeconds={seconds} durationSeconds={scoreSeconds} onSeek={seekTo} />
      <Typography variant="caption" color="text.secondary">
        What plays is the recording itself, exactly as it was performed. Nothing here is reconstructed
        from the sheet, so the two can be compared by ear. The line on the staves below shows where
        the recording is; drag that line to move it, drag the handle on the bar above, or double-click
        a blank part of the page — above the top stave, say — to send it there. The page stays where
        it is for all three. Space plays from wherever the line is standing and brings it on screen.
      </Typography>
    </Stack>
  );
}

export default ScorePlayer;
