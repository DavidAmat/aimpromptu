/**
 * Microphone capture with a live level meter.
 *
 * `MediaRecorder` produces the blob; a parallel WebAudio `AnalyserNode` produces
 * the bar heights, because `MediaRecorder` exposes no amplitude at all. The two
 * read the same `MediaStream`, so the bars and the recording cannot drift apart.
 *
 * Container choice: browsers disagree on what `MediaRecorder` can encode —
 * Safari and Firefox can do mp4 or wav, **Chrome only does webm/opus**. Rather
 * than polyfill an encoder in the browser, the backend accepts webm and lets
 * ffmpeg convert it, which is what recording apps generally do and costs us
 * nothing since every upload is normalized anyway. So `preferredMimeType()`
 * simply picks the best container this browser supports and `fileNameFor()`
 * maps it to the matching suffix.
 */

import { useCallback, useEffect, useRef, useState } from "react";

export type RecorderStatus = "idle" | "requesting" | "recording" | "recorded" | "error";

export interface RecorderState {
  status: RecorderStatus;
  /** Seconds elapsed in the current take. */
  elapsedSeconds: number;
  /** Recent levels in 0..1, newest last — one entry per animation frame batch. */
  levels: number[];
  /** Object URL of the finished take, for a preview `<audio>`. */
  previewUrl: string | null;
  /** The finished take, ready to upload. */
  blob: Blob | null;
  error: string | null;
  start: () => Promise<void>;
  stop: () => void;
  reset: () => void;
}

/** How many bars the live meter keeps on screen. */
export const LEVEL_HISTORY = 96;

const CANDIDATE_TYPES = [
  "audio/wav",
  "audio/mp4",
  "audio/aac",
  "audio/webm;codecs=opus",
  "audio/webm",
];

/** The first container this browser can record that we also accept. */
export function preferredMimeType(): string | undefined {
  if (typeof MediaRecorder === "undefined") return undefined;
  return CANDIDATE_TYPES.find((type) => MediaRecorder.isTypeSupported(type));
}

/**
 * Filename for the recorded blob.
 *
 * The backend keys the format off the **suffix**, so this must name the bytes
 * honestly — the stored `format` field comes from it. Every container listed in
 * `CANDIDATE_TYPES` maps to a suffix the upload endpoint accepts.
 */
export function fileNameFor(mimeType: string | undefined, stem = "recording"): string | null {
  if (!mimeType) return null;
  if (mimeType.startsWith("audio/wav")) return `${stem}.wav`;
  if (mimeType.startsWith("audio/mp4")) return `${stem}.m4a`;
  if (mimeType.startsWith("audio/aac")) return `${stem}.aac`;
  if (mimeType.startsWith("audio/mpeg")) return `${stem}.mp3`;
  if (mimeType.startsWith("audio/webm")) return `${stem}.webm`;
  if (mimeType.startsWith("audio/ogg")) return `${stem}.ogg`;
  return null;
}

export function useRecorder(): RecorderState {
  const [status, setStatus] = useState<RecorderStatus>("idle");
  const [levels, setLevels] = useState<number[]>([]);
  const [elapsedSeconds, setElapsed] = useState(0);
  const [blob, setBlob] = useState<Blob | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const contextRef = useRef<AudioContext | null>(null);
  const frameRef = useRef<number | null>(null);
  const startedAtRef = useRef(0);

  const teardown = useCallback(() => {
    if (frameRef.current !== null) cancelAnimationFrame(frameRef.current);
    frameRef.current = null;
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    void contextRef.current?.close();
    contextRef.current = null;
    recorderRef.current = null;
  }, []);

  useEffect(() => teardown, [teardown]);

  const start = useCallback(async () => {
    if (typeof MediaRecorder === "undefined") {
      setError("This browser does not support MediaRecorder.");
      setStatus("error");
      return;
    }
    const mimeType = preferredMimeType();
    if (fileNameFor(mimeType) === null) {
      setError(
        "This browser cannot record any audio format we recognize. " +
          "Record with another app and upload the file instead.",
      );
      setStatus("error");
      return;
    }

    setStatus("requesting");
    setError(null);
    setLevels([]);
    setElapsed(0);
    setBlob(null);
    setPreviewUrl((current) => {
      if (current) URL.revokeObjectURL(current);
      return null;
    });

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const context = new AudioContext();
      contextRef.current = context;
      const analyser = context.createAnalyser();
      analyser.fftSize = 1024;
      context.createMediaStreamSource(stream).connect(analyser);

      const buffer = new Float32Array(analyser.fftSize);
      const tick = () => {
        analyser.getFloatTimeDomainData(buffer);
        // RMS is a better bar height than peak: it tracks perceived loudness.
        let sum = 0;
        for (const sample of buffer) sum += sample * sample;
        const rms = Math.sqrt(sum / buffer.length);
        setLevels((previous) => [...previous, Math.min(1, rms * 3)].slice(-LEVEL_HISTORY));
        setElapsed((performance.now() - startedAtRef.current) / 1000);
        frameRef.current = requestAnimationFrame(tick);
      };

      const chunks: BlobPart[] = [];
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunks.push(event.data);
      };
      recorder.onstop = () => {
        const recorded = new Blob(chunks, { type: mimeType ?? "audio/wav" });
        setBlob(recorded);
        setPreviewUrl(URL.createObjectURL(recorded));
        setStatus("recorded");
        teardown();
      };

      recorderRef.current = recorder;
      startedAtRef.current = performance.now();
      recorder.start();
      setStatus("recording");
      frameRef.current = requestAnimationFrame(tick);
    } catch (caught) {
      teardown();
      setError(
        caught instanceof Error ? caught.message : "Could not access the microphone.",
      );
      setStatus("error");
    }
  }, [teardown]);

  const stop = useCallback(() => {
    recorderRef.current?.stop();
  }, []);

  const reset = useCallback(() => {
    teardown();
    setPreviewUrl((current) => {
      if (current) URL.revokeObjectURL(current);
      return null;
    });
    setBlob(null);
    setLevels([]);
    setElapsed(0);
    setError(null);
    setStatus("idle");
  }, [teardown]);

  return { status, elapsedSeconds, levels, previewUrl, blob, error, start, stop, reset };
}

export default useRecorder;
