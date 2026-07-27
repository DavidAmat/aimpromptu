/** `/youtube` — audio downloads via yt-dlp (Epic 3, Story 3.5). */

import type { AudioItem } from "./audio";
import { request } from "./client";

export interface YoutubeDownloadRequest {
  url: string;
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

  download: (body: YoutubeDownloadRequest, signal?: AbortSignal) =>
    request<AudioItem>("/youtube/download", { method: "POST", body, signal }),

  batch: (items: YoutubeDownloadRequest[], signal?: AbortSignal) =>
    request<BatchEntry[]>("/youtube/batch", { method: "POST", body: { items }, signal }),
};
