/**
 * Follow a running transcription: its progress stream, into a {@link LiveFeed}.
 *
 * The stream (`GET /matrix/progress/{jobId}`) carries three kinds of frames:
 *
 * - unnamed progress frames (`stage`, `message`, `timestamp`): "waiting", then one per chunk, then
 *   "timing" (the lag). The page shows the stage in words; the timestamps measure the time taken;
 * - `event: chunk`: the live notes (Phase 4 report, section 2.3), put in the feed's queue and drawn
 *   by the canvas on its next animation frame, with no React update;
 * - `event: done`: the end, with `status`, `revision` and `noteCount`.
 *
 * React state changes only when the stage changes and at the end, so a fast stream costs no
 * renders. A page that connects late receives every frame of the job from the start. When the
 * connection drops, the browser reconnects by itself and the backend resumes after the last frame
 * received (`Last-Event-ID`).
 */

import { useEffect, useState } from "react";
import { isChunkMessage, type LiveFeed } from "./liveFeed";

export type LiveStatus = "idle" | "running" | "done" | "error";

export interface LiveTranscription {
  status: LiveStatus;
  /** The backend's stage (`waiting`, `transcribe`, `timing`), and its words. */
  stage: string | null;
  message: string | null;
  error: string | null;
  /** The payload of the `done` frame, with `elapsedSeconds`: how long the transcription took. */
  result: Record<string, unknown> | null;
}

interface Tagged extends Omit<LiveTranscription, "status"> {
  url: string | null;
  outcome: "running" | "done" | "error";
}

const EMPTY: Tagged = { url: null, outcome: "running", stage: null, message: null, error: null, result: null };

export function useLiveTranscription(url: string | null, feed: LiveFeed): LiveTranscription {
  const [state, setState] = useState<Tagged>(EMPTY);
  const current = state.url === url ? state : { ...EMPTY, url };

  useEffect(() => {
    if (url === null) return;
    feed.reset();
    const source = new EventSource(url);
    const update = (change: Partial<Tagged>) =>
      setState((previous) => ({ ...(previous.url === url ? previous : { ...EMPTY, url }), ...change }));

    let stage: string | null = null;
    let message: string | null = null;
    source.onmessage = (frame: MessageEvent<string>) => {
      let parsed: { stage?: unknown; message?: unknown; timestamp?: unknown };
      try {
        parsed = JSON.parse(frame.data) as typeof parsed;
      } catch {
        return;
      }
      if (typeof parsed.timestamp === "number") feed.stamp(parsed.timestamp);
      const nextStage = typeof parsed.stage === "string" ? parsed.stage : null;
      // One chunk's words ("chunk 12/38") would re-render the page once per chunk: the canvas
      // already says how far it is, so the words are kept only when the stage changes.
      const nextMessage = typeof parsed.message === "string" ? parsed.message : null;
      if (nextStage !== stage || (nextStage === "waiting" && nextMessage !== message)) {
        stage = nextStage;
        message = nextMessage;
        update({ stage, message });
      }
    };

    source.addEventListener("chunk", (frame) => {
      try {
        const parsed: unknown = JSON.parse((frame as MessageEvent<string>).data);
        if (isChunkMessage(parsed)) feed.push(parsed);
      } catch {
        // A malformed frame is skipped; the saved notes are read at the end anyway.
      }
    });

    source.addEventListener("done", (frame) => {
      let payload: Record<string, unknown> = {};
      try {
        payload = JSON.parse((frame as MessageEvent<string>).data) as Record<string, unknown>;
      } catch {
        // A terminal frame is still terminal.
      }
      source.close();
      feed.finish();
      // The time the transcription took, on the backend's clock, for the page to keep saying it.
      payload.elapsedSeconds = feed.elapsedSeconds();
      if (payload.status === "error") {
        update({ outcome: "error", error: typeof payload.error === "string" ? payload.error : "The transcription failed." });
      } else {
        update({ outcome: "done", result: payload });
      }
    });

    source.onerror = () => {
      // `CONNECTING`: the browser is reconnecting by itself, and the backend resumes after the last
      // frame received. `CLOSED`: the backend refused (an unknown job), which is final.
      if (source.readyState === EventSource.CLOSED) {
        update({ outcome: "error", error: "The progress of the transcription could not be followed." });
      }
    };

    return () => source.close();
  }, [url, feed]);

  return {
    status: url === null ? "idle" : current.outcome,
    stage: current.stage,
    message: current.message,
    error: current.error,
    result: current.result,
  };
}

export default useLiveTranscription;
