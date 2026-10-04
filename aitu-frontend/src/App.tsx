/**
 * Route table. Sections and tabs are declared in `layout/routes.ts`. The router
 * itself is created in `main.tsx`, which renders this table inside it.
 */

import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import AppLayout from "./layout/AppLayout";
import PlaygroundLayout from "./layout/PlaygroundLayout";
import VideoLayout from "./layout/VideoLayout";
import { LIBRARY_PLAY_PATTERN, PIECE_PATTERN, ROUTES, VIDEO_EXAMPLE_PATTERN } from "./layout/routes";
import LibraryPage from "./pages/LibraryPage";
import NotFoundPage from "./pages/NotFoundPage";
import PerformancePage from "./pages/PerformancePage";
import YouTubePage from "./pages/YouTubePage";
import AudioTab from "./pages/piece/AudioTab";
import SheetTab from "./pages/piece/SheetTab";
import HandsTab from "./pages/piece/HandsTab";
import NotesTab from "./pages/piece/NotesTab";
import PieceIndex from "./pages/piece/PieceIndex";
import PiecePage from "./pages/piece/PiecePage";
import PieceResume from "./pages/piece/PieceResume";
import SourceTab from "./pages/piece/SourceTab";
import InputPage from "./pages/playground/InputPage";
import NotesFallingPage from "./pages/playground/NotesFallingPage";
import RhythmPage from "./pages/playground/RhythmPage";
import ExamplesPage from "./pages/video/ExamplesPage";
import VideoCalibrationPage from "./pages/video/VideoCalibrationPage";
import VideoDetectionPage from "./pages/video/VideoDetectionPage";
import VideoNotesPage from "./pages/video/VideoNotesPage";
import VideoPlayerPage from "./pages/video/VideoPlayerPage";

/** The Notes tab's measurements (Phase 7); only in a development build. */
const RollBenchPage = import.meta.env.DEV ? lazy(() => import("./pages/dev/RollBenchPage")) : null;

export default function App() {
  return (
    <Routes>
      {RollBenchPage ? (
        <Route
          path={ROUTES.devRollBench}
          element={
            <Suspense fallback={null}>
              <RollBenchPage />
            </Suspense>
          }
        />
      ) : null}
      <Route element={<AppLayout />}>
        <Route index element={<Navigate to={ROUTES.pieceNew} replace />} />

        {/*
          The flow page (implementation 08, plan section 7). `/piece/new` has only the Source tab;
          `/piece/:uuid` opens a piece on the step it reached, and every other tab is one path
          segment after it. A tab that is not enabled yet sends the reader back to that step.
        */}
        <Route path={ROUTES.pieceRoot} element={<PieceIndex />} />
        <Route path={ROUTES.pieceNew} element={<PiecePage />}>
          <Route index element={<SourceTab />} />
        </Route>
        <Route path={PIECE_PATTERN} element={<PiecePage />}>
          <Route index element={<PieceResume />} />
          <Route path="source" element={<SourceTab />} />
          <Route path="audio" element={<AudioTab />} />
          <Route path="notes" element={<NotesTab />} />
          <Route path="hands" element={<HandsTab />} />
          <Route path="sheet" element={<SheetTab />} />
        </Route>

        <Route path={ROUTES.youtube} element={<YouTubePage />} />

        <Route path={ROUTES.video} element={<VideoLayout />}>
          <Route index element={<Navigate to={ROUTES.videoExamples} replace />} />
          <Route path="player" element={<VideoPlayerPage />} />
          <Route path="calibration" element={<VideoCalibrationPage />} />
          <Route path="detection" element={<VideoDetectionPage />} />
          <Route path="notes" element={<VideoNotesPage />} />
          <Route path="examples" element={<ExamplesPage />} />
          <Route path={VIDEO_EXAMPLE_PATTERN.replace("/video/", "")} element={<ExamplesPage />} />
        </Route>

        <Route path={ROUTES.playground} element={<PlaygroundLayout />}>
          <Route index element={<Navigate to={ROUTES.playgroundInput} replace />} />
          <Route path="input" element={<InputPage />} />
          {/* The old Piano Roll (Q-4): its place is the Notes tab of the piece. */}
          <Route path="piano-roll" element={<Navigate to={ROUTES.pieceRoot} replace />} />
          <Route path="notes-falling" element={<NotesFallingPage />} />
          <Route path="rhythm" element={<RhythmPage />} />
        </Route>

        <Route path={ROUTES.library} element={<LibraryPage />} />
        <Route path={LIBRARY_PLAY_PATTERN} element={<PerformancePage />} />

        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
