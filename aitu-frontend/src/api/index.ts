/**
 * The whole backend surface, one module per backend router.
 * Import from here: `import { matrixApi } from "../api";`
 */

import { request } from "./client";

export { API_BASE, ApiError, buildUrl, request, SIGNED_OUT_EVENT, upload } from "./client";
export type { RequestOptions } from "./client";

export { authApi } from "./auth";
export type { Me } from "./auth";
export { adminApi } from "./admin";
export type { AdminUser } from "./admin";

export { audioApi, SUPPORTED_AUDIO_SUFFIXES } from "./audio";
export type {
  AudioItem,
  AudioSource,
  AudioTimeRange,
  Cut,
  AudioFiles,
  AxisFile,
  CutsState,
  FramePeaks,
  KeptRange,
  WaveformPeaks,
} from "./audio";

export { projectsApi } from "./projects";
export type {
  DuplicatedProject,
  LibraryLink,
  ProjectLayer,
  ProjectRow,
  SavedToLibrary,
  SaveToLibrary,
} from "./projects";
export { libraryApi } from "./library";
export type {
  ArtistDetail,
  ArtistNameRow,
  ArtistRow,
  Credit,
  EarlierState,
  SongDetail,
  SongRow,
  VersionRow,
} from "./library";
export { piecesApi, PIECE_STEPS } from "./pieces";
export type {
  NotesOperation,
  NotesPatchResult,
  PieceNotes,
  PieceStatus,
  PredictResult,
  PieceStep,
  StepState,
  StepStatus,
} from "./pieces";

export { timeScoreApi, FIGURE_LABELS, KEY_LABELS, KEY_SIGNATURES } from "./timeScore";
export type {
  CueRange,
  DefaultReading,
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
