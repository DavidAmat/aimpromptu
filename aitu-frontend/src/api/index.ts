/**
 * The whole backend surface, one module per backend router.
 * Import from here: `import { matrixApi } from "../api";`
 */

import { request } from "./client";

export { API_BASE, ApiError, buildUrl, request, upload } from "./client";
export type { RequestOptions } from "./client";

export { scoresApi } from "./scores";
export type { SequenceRequest } from "./scores";

// Music contracts, re-exported so components have one import path for the API
// surface and the shapes it carries.
export type {
  Granularity as MatrixGranularity,
  KeyLabel,
  MatrixScore,
  SparseMatrix,
} from "../music/types";

export { audioApi, SUPPORTED_AUDIO_SUFFIXES } from "./audio";
export type { AudioItem, AudioSource, AudioTimeRange, WaveformPeaks } from "./audio";

export { timeScoreApi, FIGURE_LABELS } from "./timeScore";
export type {
  FigureLadder,
  FigureName,
  HandChoice,
  LabelledPeak,
  LadderPreview,
  LayoutHints,
  Passage,
  Peak,
  PeaksResponse,
  PrintedHand,
  PrintedNote,
  SavedRhythm,
  SpeedChange,
  TimeMatrixEnvelope,
  TimeScorePayload,
} from "./timeScore";

export { matrixApi } from "./matrix";
export type {
  JobHandle,
  JobStatus,
  RawEvents,
  RawNoteEvent,
  TranscribeRequest,
} from "./matrix";

export { libraryApi } from "./library";
export type {
  LibraryTrack,
  PlaygroundTrack,
  PromoteRequest,
  Promotion,
  PromotionSuggestion,
  SaveVersionRequest,
  SavedVersion,
  VersionHistoryEntry,
} from "./library";

export { youtubeApi } from "./youtube";
export type { BatchEntry, VideoInfo, YoutubeDownloadRequest } from "./youtube";

/** Liveness check used by the app bar indicator. */
export const health = (signal?: AbortSignal) =>
  request<{ status: string }>("/health", { signal });
