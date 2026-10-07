/** `/youtube` — audio downloads via yt-dlp (Epic 3, Story 3.5). */

import type { AudioItem } from "./audio";
import { request } from "./client";

export interface YoutubeDownloadRequest {
  url: string;
  /** A project (its part) to add the audio to, instead of making a new project. */
  appendTo?: string;
  /** Display name for the stored audio. Defaults to the video title. */
  alias?: string;
}

export interface VideoInfo {
  title: string;
  durationSeconds?: number | null;
  uploader?: string | null;
}

export interface BatchEntry {
  url: string;
  status: "done" | "error";
  detail?: string | null;
  audio?: AudioItem | null;
}

export const youtubeApi = {
  /** Title and duration without downloading — lets the UI prefill the name. */
  probe: (url: string, signal?: AbortSignal) =>
    request<VideoInfo>("/youtube/probe", { method: "POST", body: { url }, signal }),

  /**
   * Start the download as a background job and answer at once (the Source tab).
   *
   * Follow it with `matrixApi.progressUrl(jobId)`: a `download` stage in percent, a `store` stage
   * while the audio is converted, then a `done` frame whose result carries `audioUuid`.
   */
  startDownload: (body: YoutubeDownloadRequest, signal?: AbortSignal) =>
    request<{ jobId: string; status: string }>("/youtube/jobs", { method: "POST", body, signal }),

  download: (body: YoutubeDownloadRequest, signal?: AbortSignal) =>
    request<AudioItem>("/youtube/download", { method: "POST", body, signal }),

  batch: (items: YoutubeDownloadRequest[], signal?: AbortSignal) =>
    request<BatchEntry[]>("/youtube/batch", { method: "POST", body: { items }, signal }),
};
