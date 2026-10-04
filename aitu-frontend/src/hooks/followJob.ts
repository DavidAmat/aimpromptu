/**
 * Follow one backend job to its end, from an event handler: `await` its result.
 *
 * `useProgress` suits a page that shows a job it did not start (the transcription the Notes tab
 * follows). A button that starts a short job and then does something with its answer (**Predict
 * hands**) reads better as one async flow: start, follow, use the answer. This opens the progress
 * stream, calls `onProgress` with each progress frame, and resolves with the payload of the `done`
 * frame. `close()` stops following (the page left).
 */

export interface JobFrame {
  stage: string;
  current: number;
  total: number;
  fraction: number;
  message: string;
}

export interface FollowedJob {
  result: Promise<Record<string, unknown>>;
  close: () => void;
}

export function followJob(url: string, onProgress: (frame: JobFrame) => void): FollowedJob {
  const source = new EventSource(url);
  const result = new Promise<Record<string, unknown>>((resolve, reject) => {
    source.onmessage = (message: MessageEvent<string>) => {
      try {
        const frame = JSON.parse(message.data) as Partial<JobFrame>;
        if (typeof frame.stage === "string" && typeof frame.fraction === "number") onProgress(frame as JobFrame);
      } catch {
        // A keep-alive comment or a malformed frame: nothing to show.
      }
    };
    source.addEventListener("done", (frame) => {
      source.close();
      let payload: Record<string, unknown> = {};
      try {
        payload = JSON.parse((frame as MessageEvent<string>).data) as Record<string, unknown>;
      } catch {
        // A terminal frame is still terminal.
      }
      if (payload.status === "error") reject(new Error(typeof payload.error === "string" ? payload.error : "The job failed."));
      else resolve(payload);
    });
    source.onerror = () => {
      if (source.readyState === EventSource.CLOSED) reject(new Error("The progress of the job could not be followed."));
    };
  });
  return { result, close: () => source.close() };
}

export default followJob;
