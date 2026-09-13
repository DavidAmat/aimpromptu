/**
 * An optional click while re-recording. Sound only: nothing about it is stored
 * or used by the splice. Interval is milliseconds, never a BPM.
 */

import { useCallback, useEffect, useRef } from "react";

export function useClickTrack() {
  const context = useRef<AudioContext | null>(null);
  const timer = useRef<number | null>(null);

  const stop = useCallback(() => {
    if (timer.current !== null) {
      window.clearInterval(timer.current);
      timer.current = null;
    }
  }, []);

  const click = useCallback(() => {
    const ctx = context.current;
    if (!ctx) return;
    const oscillator = ctx.createOscillator();
    const gain = ctx.createGain();
    oscillator.frequency.value = 1000;
    oscillator.type = "square";
    gain.gain.value = 0.08;
    oscillator.connect(gain);
    gain.connect(ctx.destination);
    oscillator.start();
    gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.04);
    oscillator.stop(ctx.currentTime + 0.05);
  }, []);

  const start = useCallback(
    (intervalMs: number) => {
      stop();
      if (intervalMs <= 0) return;
      const AudioCtx =
        window.AudioContext ||
        (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
      if (!AudioCtx) return;
      context.current ??= new AudioCtx();
      void context.current.resume();
      click();
      timer.current = window.setInterval(click, intervalMs);
    },
    [click, stop],
  );

  useEffect(() => () => stop(), [stop]);

  return { start, stop };
}
