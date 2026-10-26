/**
 * The whole backend surface, one module per backend router.
 * Import from here: `import { matrixApi } from "../api";`
 */

import { request } from "./client";

export { API_BASE, ApiError, buildUrl, postForm, request, SIGNED_OUT_EVENT, upload } from "./client";
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

export { sheetApi } from "./sheet";
export type {
  FramesSheet,
  ReadingEdit,
  SheetColumn,
  SheetEdited,
  SheetHistory,
  SheetLlm,
  SheetLyric,
  SheetNote,
  SheetPage,
  SheetPreview,
  SheetReading,
  SheetSegment,
  SheetSystem,
  SheetTitles,
  StretchKeys,
  StretchRequest,
} from "./sheet";
export { projectsApi } from "./projects";
export type {
  ChosenPassage,
  DuplicatedProject,
  LibraryLink,
  PartRow,
  PartsAnswer,
  ProjectLayer,
  ProjectRow,
  SavedToLibrary,
  SaveToLibrary,
} from "./projects";
export { playlistsApi } from "./playlists";
export type { NewPlaylistItem, PlaylistDetail, PlaylistItem, PlaylistRow } from "./playlists";
export { passagesApi } from "./passages";
export type {
  OpenPassage,
  PassageTake,
  PlayedNote,
  Promoted,
  PromotionAudio,
  PromotionFacts,
  PromotionMode,
} from "./passages";
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
export { publicApi } from "./publicLibrary";
export type {
  ArtistSort,
  FacetValue,
  Facets,
  PublicArtistDetail,
  PublicArtistRow,
  PublicChart,
  PublicRegionPopularity,
  PublicCredit,
  PublicLists,
  PublicPlaylistDetail,
  PublicPlaylistItem,
  PublicPlaylistRow,
  PublicSongDetail,
  PublicSongPage,
  PublicSongRow,
  PublicUserVersions,
  PublicVersion,
  Pulled,
  SongQuery,
  SongSort,
  SortDirection,
  Suggestions,
} from "./publicLibrary";
export { requestsApi } from "./requests";
export type {
  ArtistInRequest,
  ArtistRef,
  CommentInput,
  ItemDecision,
  ItemDecisionValue,
  ItemKind,
  Made,
  PlaylistInfo,
  ProjectSide,
  Proposal,
  PublishInfo,
  RequestComment,
  RequestDetail,
  RequestItem,
  RequestKind,
  RequestStatus,
  RequestSummary,
  ReviewDetails,
  SongFields,
  SongState,
  StretchDetails,
} from "./requests";
export { sharesApi } from "./shares";
export type { Person, SharedLibrary, SharedSong, Shares } from "./shares";
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
  PassageRef,
  PasteResult,
  Peak,
  PeaksResponse,
  PrintedHand,
  PrintedNote,
  RestoreResult,
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
