/**
 * Consume a backend SSE progress stream.
 *
 * The backend's `ProgressReporter` (see `aitu_backend/progress.py`) emits one
 * JSON frame per tick with exactly these fields. Pass `null` to stay idle;
 * pass a URL to open the stream. The connection closes on unmount, on the
 * terminal `done` event, or on error.
 *
 * Note on shape: everything lives in one state object tagged with the URL it
 * belongs to, and `status` is *derived* rather than assigned. That keeps the
 * effect free of synchronous `setState` calls (which cascade renders) while
 * still resetting cleanly when the URL changes.
 */

import { useCallback, useEffect, useState } from "react";

export interface ProgressEvent {
  stage: string;
  current: number;
  total: number;
  /** 0..1 — already rounded by the backend. */
  fraction: number;
  message: string;
  timestamp: number;
}

export type ProgressStatus = "idle" | "running" | "done" | "error";

export interface ProgressState {
  status: ProgressStatus;
  /** Latest event, or `null` before the first tick. */
  event: ProgressEvent | null;
  /** 0..100, ready for MUI's `LinearProgress value`. */
  percent: number;
  error: string | null;
  /** Every stage seen so far, in order — useful for a multi-step pipeline UI. */
  stages: string[];
  /** Drop what was received and reopen the stream. */
  reset: () => void;
}

interface StreamState {
  /** The URL these values describe; anything else is stale. */
  url: string | null;
  event: ProgressEvent | null;
  outcome: "running" | "done" | "error";
  error: string | null;
  stages: string[];
  /** Monotonic whole-pipeline percentage; stage fractions reset at each stage. */
  percent: number;
}

const EMPTY: StreamState = {
  url: null,
  event: null,
  outcome: "running",
  error: null,
  stages: [],
  percent: 0,
};

const PIPELINE_RANGES: Record<string, readonly [number, number]> = {
  "download model": [0, 5],
  transcribe: [5, 80],
  events: [80, 88],
  collapse: [88, 94],
  clean: [94, 99],
  "two-hands": [99, 100],
};

function wholePipelinePercent(event: ProgressEvent): number {
  const range = PIPELINE_RANGES[event.stage];
  if (!range) return Math.round(event.fraction * 100);
  return Math.round(range[0] + (range[1] - range[0]) * event.fraction);
}

function isProgressEvent(value: unknown): value is ProgressEvent {
  if (typeof value !== "object" || value === null) return false;
  const candidate = value as Partial<ProgressEvent>;
  return typeof candidate.stage === "string" && typeof candidate.fraction === "number";
}

export function useProgress(url: string | null): ProgressState {
  const [state, setState] = useState<StreamState>(EMPTY);
  const [generation, setGeneration] = useState(0);

  // Values from a previous URL must not leak into the current one.
  const fresh = state.url === url ? state : { ...EMPTY, url };

  const reset = useCallback(() => {
    setState(EMPTY);
    setGeneration((n) => n + 1);
  }, []);

  useEffect(() => {
    if (url === null) return;

    const source = new EventSource(url);

    source.onmessage = (message: MessageEvent<string>) => {
      let parsed: unknown;
      try {
        parsed = JSON.parse(message.data);
      } catch {
        return; // Ignore keep-alive comments and malformed frames.
      }
      if (!isProgressEvent(parsed)) return;
      const event = parsed;
      setState((previous) => {
        const base = previous.url === url ? previous : { ...EMPTY, url };
        const stages =
          base.stages[base.stages.length - 1] === event.stage
            ? base.stages
            : [...base.stages, event.stage];
        return {
          ...base,
          url,
          event,
          stages,
          percent: Math.max(base.percent, wholePipelinePercent(event)),
        };
      });
    };

    // The backend closes the stream with a named `done` event when finished.
    source.addEventListener("done", (rawEvent) => {
      const message = rawEvent as MessageEvent<string>;
      let payload: { status?: string; error?: string | null } = {};
      try {
        payload = JSON.parse(message.data) as typeof payload;
      } catch {
        // A malformed terminal frame is still a terminal frame.
      }
      setState((previous) => {
        const base = previous.url === url ? previous : { ...EMPTY, url };
        return payload.status === "error"
          ? {
              ...base,
              url,
              outcome: "error",
              error: payload.error || "Transcription failed",
            }
          : { ...base, url, outcome: "done", percent: 100 };
      });
      source.close();
    });

    source.onerror = () => {
      // EventSource fires `error` on a clean server close too, so a stream that
      // already reached `done` must not be downgraded to an error.
      setState((previous) => {
        if (previous.url === url && previous.outcome === "done") return previous;
        return {
          ...(previous.url === url ? previous : { ...EMPTY, url }),
          url,
          outcome: "error",
          error: "Progress stream interrupted",
        };
      });
      source.close();
    };

    return () => source.close();
  }, [url, generation]);

  const status: ProgressStatus = url === null ? "idle" : fresh.outcome;

  return {
    status,
    event: fresh.event,
    percent: fresh.percent,
    error: fresh.error,
    stages: fresh.stages,
    reset,
  };
}

export default useProgress;
