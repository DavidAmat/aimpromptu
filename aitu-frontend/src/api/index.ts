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

export { timeScoreApi, FIGURE_LABELS, KEY_LABELS, KEY_SIGNATURES } from "./timeScore";
export type {
  CueRange,
  FigureLadder,
  FigureName,
  GraceNote,
  HandChoice,
  KeySignatureName,
  LabelledPeak,
  LadderPreview,
  LayoutHints,
  LyricLine,
  Passage,
  Peak,
  PeaksResponse,
  PrintedHand,
  PrintedNote,
  SavedRhythm,
  SpeedChange,
  TimeMatrixEnvelope,
  TimeScorePayload,
  Trill,
  TrillSuggestion,
  TrillsResponse,
} from "./timeScore";

export { matrixApi } from "./matrix";
export type {
  JobHandle,
  JobStatus,
  RawEvents,
  RawNoteEvent,
  RemovalResult,
  RemovedNote,
  TranscribeRequest,
} from "./matrix";

export { libraryApi } from "./library";
export type {
  LibraryTrack,
  PlaygroundTrack,
  Playlist,
  PlaylistItem,
  PromoteRequest,
  Promotion,
  PromotionSuggestion,
  SaveVersionRequest,
  SavedVersion,
  VersionHistoryEntry,
} from "./library";

export { editingApi } from "./editing";
export type {
  AcceptResult,
  Confirmation,
  DroppedMarks,
  EditPreview,
  EditSession,
  MovedMarks,
  Placement,
  SlowdownChoice,
  StartEditBody,
} from "./editing";

export { videoApi } from "./video";
export type {
  DetectionReport,
  FrameLine,
  ScrollSpeed,
  VideoJobHandle,
  VideoMeasurement,
  VideoMetadata,
  VideoSummary,
} from "./video";

export { youtubeApi } from "./youtube";
export type { BatchEntry, VideoInfo, YoutubeDownloadRequest } from "./youtube";

export { frameExamplesApi } from "./frameExamples";
export type {
  Annotation,
  BlackBorder,
  Calibration,
  DetectedRun,
  Detection,
  Disagreement,
  ExampleSummary,
  FindRequest,
  Found,
  FrameExample,
  Geometry,
  KeyLane,
  KeyState,
  MomentumVerdict,
  PianoKey,
  PianoRect,
  ScoreBoard,
  ScoreLine,
} from "./frameExamples";

/** Liveness check used by the app bar indicator. */
export const health = (signal?: AbortSignal) =>
  request<{ status: string }>("/health", { signal });
