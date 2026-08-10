/**
 * The transport the animated views share: an AudioContext clock over the played
 * notes, with the original recording or a synthesised piano as the sound.
 *
 * Adapted from Epic 8's `useMatrixPlayback`. The clock is unchanged — it was
 * already reading seconds off the audio context rather than counting frames, and
 * that is the part worth keeping. What went is everything that translated between
 * seconds and matrix columns: there is no `timeStepSeconds` and no `currentFrame`,
 * because a position in this app is a wall-clock time and nothing else.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { pianoKeyByRow } from "../piano/keyPositions";
import { soundingRows, type PlayedNote } from "./playedNotes";

export type PlaybackSource = "original" | "piano";

interface UsePlaybackOptions {
  notes: PlayedNote[];
  durationSeconds: number;
  selectionStart?: number;
  selectionEnd?: number;
  speed?: number;
  source?: PlaybackSource;
  originalAudioUrl?: string | null;
  originalAudioOffset?: number;
}

interface ClockAnchor {
  contextSeconds: number;
  pieceSeconds: number;
}

/** How far ahead of the clock a note is allowed to be triggered, in seconds. */
const TRIGGER_LOOKAHEAD = 0.04;
/** Repaint interval in milliseconds — 30 ms is smooth and costs one render. */
const PAINT_INTERVAL = 30;

async function startOriginalAudio(
  audio: HTMLAudioElement,
  seconds: number,
  speed: number,
): Promise<void> {
  audio.currentTime = seconds;
  audio.playbackRate = speed;
  await audio.play();
}

export function usePlayback({
  notes,
  durationSeconds,
  selectionStart = 0,
  selectionEnd = durationSeconds,
  speed = 1,
  source = "piano",
  originalAudioUrl,
  originalAudioOffset = 0,
}: UsePlaybackOptions) {
  const safeEnd = Math.max(selectionStart, Math.min(durationSeconds, selectionEnd));
  const [currentSeconds, setCurrentSeconds] = useState(selectionStart);
  const [playing, setPlaying] = useState(false);
  const contextRef = useRef<AudioContext | null>(null);
  const anchorRef = useRef<ClockAnchor | null>(null);
  const frameRequestRef = useRef<number | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const oscillatorsRef = useRef<OscillatorNode[]>([]);
  const triggeredRef = useRef<Set<string>>(new Set());
  const playingRef = useRef(false);
  const currentRef = useRef(selectionStart);
  const lastPaintRef = useRef(0);

  const ensureContext = useCallback(async () => {
    const AudioContextConstructor =
      window.AudioContext ??
      (window as typeof window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!AudioContextConstructor) throw new Error("Web Audio is not available in this browser.");
    const context = contextRef.current ?? new AudioContextConstructor();
    contextRef.current = context;
    if (context.state === "suspended") await context.resume();
    return context;
  }, []);

  const stopVoices = useCallback(() => {
    for (const oscillator of oscillatorsRef.current) {
      try {
        oscillator.stop();
      } catch {
        // It already ended naturally.
      }
    }
    oscillatorsRef.current = [];
  }, []);

  const pause = useCallback(() => {
    playingRef.current = false;
    setPlaying(false);
    if (frameRequestRef.current !== null) cancelAnimationFrame(frameRequestRef.current);
    frameRequestRef.current = null;
    audioRef.current?.pause();
    stopVoices();
  }, [stopVoices]);

  const seek = useCallback(
    (seconds: number) => {
      const next = Math.max(selectionStart, Math.min(safeEnd, seconds));
      currentRef.current = next;
      setCurrentSeconds(next);
      triggeredRef.current.clear();
      if (audioRef.current) audioRef.current.currentTime = originalAudioOffset + next;
      if (playingRef.current && contextRef.current) {
        anchorRef.current = {
          contextSeconds: contextRef.current.currentTime,
          pieceSeconds: next,
        };
        stopVoices();
      }
    },
    [originalAudioOffset, safeEnd, selectionStart, stopVoices],
  );

  const soundNote = useCallback(
    (context: AudioContext, note: PlayedNote, now: number) => {
      const key = pianoKeyByRow.get(note.row);
      if (!key) return;
      const oscillator = context.createOscillator();
      const gain = context.createGain();
      const remaining = Math.max(0.025, (note.endSeconds - now) / speed);
      // Velocity is what the engine reported, so a quiet accompaniment stays
      // quiet under a melody instead of every note arriving at one loudness.
      const peak = 0.04 + (Math.min(127, Math.max(1, note.velocity)) / 127) * 0.11;
      oscillator.type = "triangle";
      oscillator.frequency.value = key.frequency;
      gain.gain.setValueAtTime(0.0001, context.currentTime);
      gain.gain.exponentialRampToValueAtTime(peak, context.currentTime + 0.012);
      gain.gain.exponentialRampToValueAtTime(0.0001, context.currentTime + remaining);
      oscillator.connect(gain).connect(context.destination);
      oscillator.start();
      oscillator.stop(context.currentTime + remaining + 0.02);
      oscillatorsRef.current.push(oscillator);
      oscillator.addEventListener("ended", () => {
        oscillatorsRef.current = oscillatorsRef.current.filter((voice) => voice !== oscillator);
      });
    },
    [speed],
  );

  const play = useCallback(async () => {
    const context = await ensureContext();
    const start = currentRef.current >= safeEnd ? selectionStart : currentRef.current;
    currentRef.current = start;
    setCurrentSeconds(start);
    triggeredRef.current.clear();
    stopVoices();

    if (source === "original" && originalAudioUrl) {
      const audio =
        audioRef.current?.src === originalAudioUrl
          ? audioRef.current
          : new window.Audio(originalAudioUrl);
      audioRef.current = audio;
      await startOriginalAudio(audio, originalAudioOffset + start, speed);
    } else {
      audioRef.current?.pause();
    }

    anchorRef.current = { contextSeconds: context.currentTime, pieceSeconds: start };
    playingRef.current = true;
    setPlaying(true);

    const tick = (paintTime: number) => {
      if (!playingRef.current || !anchorRef.current) return;
      const now =
        anchorRef.current.pieceSeconds +
        (context.currentTime - anchorRef.current.contextSeconds) * speed;
      currentRef.current = now;

      if (source === "piano") {
        for (const note of notes) {
          if (note.endSeconds <= now || note.startSeconds > now + TRIGGER_LOOKAHEAD) continue;
          if (!triggeredRef.current.has(note.id)) {
            triggeredRef.current.add(note.id);
            soundNote(context, note, now);
          }
        }
      }

      if (paintTime - lastPaintRef.current >= PAINT_INTERVAL) {
        lastPaintRef.current = paintTime;
        setCurrentSeconds(Math.min(now, safeEnd));
      }

      if (now >= safeEnd) {
        playingRef.current = false;
        setPlaying(false);
        setCurrentSeconds(safeEnd);
        audioRef.current?.pause();
        stopVoices();
        frameRequestRef.current = null;
        return;
      }
      frameRequestRef.current = requestAnimationFrame(tick);
    };
    frameRequestRef.current = requestAnimationFrame(tick);
  }, [
    ensureContext,
    notes,
    originalAudioOffset,
    originalAudioUrl,
    safeEnd,
    selectionStart,
    soundNote,
    source,
    speed,
    stopVoices,
  ]);

  const restart = useCallback(() => {
    pause();
    seek(selectionStart);
  }, [pause, seek, selectionStart]);

  const pressedKeys = useMemo(
    () => soundingRows(notes, currentSeconds),
    [currentSeconds, notes],
  );

  useEffect(
    () => () => {
      playingRef.current = false;
      if (frameRequestRef.current !== null) cancelAnimationFrame(frameRequestRef.current);
      audioRef.current?.pause();
      stopVoices();
    },
    [stopVoices],
  );

  return { currentSeconds, playing, pressedKeys, play, pause, restart, seek };
}

export type PlaybackController = ReturnType<typeof usePlayback>;
