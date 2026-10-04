/**
 * The Audio tab's player: the original audio file, played over the cuts the page holds.
 *
 * The audio file is never changed (plan section 9.2), so the deleted parts are still in it. **Play
 * all** plays the selected region, the frames that are not in a cut, by jumping the original audio
 * over each cut when the playhead reaches it. **Play selection** plays exactly the frames selected,
 * cut or not, because that is how a reader listens to a part before deleting or restoring it.
 *
 * The cuts it jumps over are the page's current ones, saved or not: the reader hears the result of
 * a Delete before deciding to keep it.
 *
 * The position is checked once per screen refresh (about every 16 ms). A jump is made up to
 * {@link LOOKAHEAD_FRAMES} early, so at most a few milliseconds of a cut are heard. A browser stops
 * the screen refreshes of a tab in the background, so the audio element's own `timeupdate` event
 * (about four times a second, also in the background) checks too: there a jump can be up to a
 * quarter of a second late, but the cut is never played through. React is not
 * re-rendered during playback: the waveform reads {@link CutPlayer.position} on its own animation
 * frame, and `cursor` changes only when playback stops or the reader seeks.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import type { Cut } from "../api";
import { firstKeptFrom, jumpTarget } from "./cuts";

/** One time frame, in seconds. */
const FRAME_SECONDS = 0.01;
/** Two frames (20 ms): a little more than one screen refresh. */
const LOOKAHEAD_FRAMES = 2;

export type PlayMode = "all" | "selection";

export interface CutPlayer {
  /** What is playing, or `null`. */
  playing: PlayMode | null;
  /** Where the playhead rests while nothing plays, in frames of the original audio. */
  cursor: number;
  /** The live position in frames, read on each animation frame while playing. */
  position: () => number;
  /** Play the kept frames from the cursor, jumping over every cut. */
  playAll: () => void;
  /** Play `[start, end)` exactly, then come back to its start. */
  playSelection: (selection: Cut) => void;
  /** Play all, or pause where it is. For Space. */
  toggle: () => void;
  pause: () => void;
  /** Move the playhead. Playback goes on from there when it was playing. */
  seek: (frame: number) => void;
  /** The audio could not be loaded or played, in words. */
  error: string | null;
}

export function useCutPlayer(url: string | null, cuts: readonly Cut[], totalFrames: number): CutPlayer {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const loopRef = useRef<number | null>(null);
  /** The check of the playing run, also called by `timeupdate`; removed when playback stops. */
  const checkRef = useRef<(() => void) | null>(null);
  // The latest cuts and total, for the loop that runs between renders.
  const cutsRef = useRef<readonly Cut[]>(cuts);
  const totalRef = useRef(totalFrames);
  const [playing, setPlaying] = useState<PlayMode | null>(null);
  const [cursor, setCursor] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    cutsRef.current = cuts;
    totalRef.current = totalFrames;
  }, [cuts, totalFrames]);

  const stopLoop = useCallback(() => {
    if (loopRef.current !== null) cancelAnimationFrame(loopRef.current);
    loopRef.current = null;
    if (checkRef.current) audioRef.current?.removeEventListener("timeupdate", checkRef.current);
    checkRef.current = null;
  }, []);

  useEffect(() => {
    if (!url) return;
    const audio = new Audio(url);
    audio.preload = "auto";
    audioRef.current = audio;
    const onEnded = () => {
      stopLoop();
      setPlaying(null);
      setCursor(totalRef.current);
    };
    audio.addEventListener("ended", onEnded);
    return () => {
      stopLoop();
      audio.pause();
      audio.removeEventListener("ended", onEnded);
      audio.removeAttribute("src");
      audio.load();
      audioRef.current = null;
    };
  }, [url, stopLoop]);

  const position = useCallback(() => {
    const audio = audioRef.current;
    return audio ? audio.currentTime / FRAME_SECONDS : 0;
  }, []);

  const pause = useCallback(() => {
    stopLoop();
    const audio = audioRef.current;
    if (audio) {
      audio.pause();
      setCursor(Math.round(audio.currentTime / FRAME_SECONDS));
    }
    setPlaying(null);
  }, [stopLoop]);

  const start = useCallback(
    (from: number, mode: PlayMode, until: number | null) => {
      const audio = audioRef.current;
      if (!audio) return;
      stopLoop();
      audio.currentTime = from * FRAME_SECONDS;
      setError(null);
      audio.play().catch((caught: unknown) => {
        stopLoop();
        setPlaying(null);
        setError(caught instanceof Error ? caught.message : "The audio could not be played.");
      });
      setPlaying(mode);
      setCursor(from);

      /** Stop where the run ends, or jump over a cut. `false` once playback has stopped. */
      const check = (): boolean => {
        const frame = audio.currentTime / FRAME_SECONDS;
        if (until !== null && frame >= until) {
          // The end of the selection: stop, and come back to its start to play it again.
          audio.pause();
          stopLoop();
          setPlaying(null);
          setCursor(from);
          return false;
        }
        if (mode === "all") {
          const target = jumpTarget(cutsRef.current, frame, LOOKAHEAD_FRAMES);
          if (target !== null) {
            if (target >= totalRef.current) {
              audio.pause();
              stopLoop();
              setPlaying(null);
              setCursor(totalRef.current);
              return false;
            }
            audio.currentTime = target * FRAME_SECONDS;
          }
        }
        return true;
      };
      const follow = () => {
        if (check()) loopRef.current = requestAnimationFrame(follow);
      };
      const onTimeUpdate = () => void check();
      checkRef.current = onTimeUpdate;
      audio.addEventListener("timeupdate", onTimeUpdate);
      loopRef.current = requestAnimationFrame(follow);
    },
    [stopLoop],
  );

  const playAll = useCallback(() => {
    const total = totalRef.current;
    const from = cursor >= total - 1 ? 0 : cursor;
    const kept = firstKeptFrom(cutsRef.current, from, total) ?? firstKeptFrom(cutsRef.current, 0, total);
    if (kept === null) return;
    start(kept, "all", null);
  }, [cursor, start]);

  const playSelection = useCallback(
    (selection: Cut) => start(selection[0], "selection", selection[1]),
    [start],
  );

  const toggle = useCallback(() => {
    if (playing) pause();
    else playAll();
  }, [playing, pause, playAll]);

  const seek = useCallback(
    (frame: number) => {
      const at = Math.max(0, Math.min(totalRef.current, Math.round(frame)));
      setCursor(at);
      const audio = audioRef.current;
      if (audio && playing) audio.currentTime = at * FRAME_SECONDS;
    },
    [playing],
  );

  return { playing, cursor, position, playAll, playSelection, toggle, pause, seek, error };
}

export default useCutPlayer;
