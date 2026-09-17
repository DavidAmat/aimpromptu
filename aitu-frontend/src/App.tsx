/**
 * Route table. Sections and tabs are declared in `layout/routes.ts`; every page
 * is a placeholder until its epic lands, but the chrome and the shared working
 * artifact are real from day one.
 */

import { Navigate, Route, Routes } from "react-router-dom";
import AppLayout from "./layout/AppLayout";
import PlaygroundLayout from "./layout/PlaygroundLayout";
import VideoLayout from "./layout/VideoLayout";
import { LIBRARY_PLAY_PATTERN, ROUTES, VIDEO_EXAMPLE_PATTERN } from "./layout/routes";
import LibraryPage from "./pages/LibraryPage";
import NotFoundPage from "./pages/NotFoundPage";
import PerformancePage from "./pages/PerformancePage";
import YouTubePage from "./pages/YouTubePage";
import InputPage from "./pages/playground/InputPage";
import NotesFallingPage from "./pages/playground/NotesFallingPage";
import PianoRollPage from "./pages/playground/PianoRollPage";
import RhythmPage from "./pages/playground/RhythmPage";
import ExamplesPage from "./pages/video/ExamplesPage";
import VideoCalibrationPage from "./pages/video/VideoCalibrationPage";
import VideoDetectionPage from "./pages/video/VideoDetectionPage";
import VideoNotesPage from "./pages/video/VideoNotesPage";
import VideoPlayerPage from "./pages/video/VideoPlayerPage";

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<Navigate to={ROUTES.playgroundInput} replace />} />
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
          <Route path="piano-roll" element={<PianoRollPage />} />
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
