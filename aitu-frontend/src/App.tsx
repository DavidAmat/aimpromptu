/**
 * The route table (implementation 02, plan section 6.3). Every path is declared in
 * `layout/routes.ts`; the router itself is created in `main.tsx`, which renders this table inside it.
 */

import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import AppLayout from "./layout/AppLayout";
import LabLayout from "./layout/LabLayout";
import LegacyRedirect from "./layout/LegacyRedirect";
import { LAB_EXAMPLE_PATTERN, LEGACY_REDIRECTS, PROJECT_PATTERN, ROUTES } from "./layout/routes";
import NotFoundPage from "./pages/NotFoundPage";
import ProjectsPage from "./pages/ProjectsPage";
import AudioTab from "./pages/piece/AudioTab";
import HandsTab from "./pages/piece/HandsTab";
import NotesFallingPage from "./pages/piece/NotesFallingPage";
import NotesTab from "./pages/piece/NotesTab";
import PiecePage from "./pages/piece/PiecePage";
import PieceResume from "./pages/piece/PieceResume";
import SheetTab from "./pages/piece/SheetTab";
import SourceTab from "./pages/piece/SourceTab";
import ExamplesPage from "./pages/video/ExamplesPage";
import VideoCalibrationPage from "./pages/video/VideoCalibrationPage";
import VideoDetectionPage from "./pages/video/VideoDetectionPage";
import VideoNotesPage from "./pages/video/VideoNotesPage";
import VideoPlayerPage from "./pages/video/VideoPlayerPage";

/** The Notes tab's measurements (implementation 08, Phase 7); only in a development build. */
const RollBenchPage = import.meta.env.DEV ? lazy(() => import("./pages/dev/RollBenchPage")) : null;
/** Every shared component on one page (implementation 02, Phase 1); only in a development build. */
const UiGalleryPage = import.meta.env.DEV ? lazy(() => import("./pages/dev/UiGalleryPage")) : null;

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
        <Route index element={<Navigate to={ROUTES.projects} replace />} />
        {UiGalleryPage ? (
          <Route
            path={ROUTES.devUi}
            element={
              <Suspense fallback={null}>
                <UiGalleryPage />
              </Suspense>
            }
          />
        ) : null}
        <Route path={ROUTES.projects} element={<ProjectsPage />} />

        {/*
          A project, step by step (plan section 10.2). `/projects/new` has only the Source step;
          `/projects/:id` opens a project on the step it reached, and every other step is one path
          segment after it. A step that cannot be opened yet sends the reader to the step reached.
        */}
        <Route path={ROUTES.projectNew} element={<PiecePage />}>
          <Route index element={<SourceTab />} />
        </Route>
        <Route path={PROJECT_PATTERN} element={<PiecePage />}>
          <Route index element={<PieceResume />} />
          <Route path="source" element={<SourceTab />} />
          <Route path="audio" element={<AudioTab />} />
          <Route path="notes" element={<NotesTab />} />
          <Route path="hands" element={<HandsTab />} />
          <Route path="sheet" element={<SheetTab />} />
          <Route path="notes-falling" element={<NotesFallingPage />} />
        </Route>

        <Route path={ROUTES.lab} element={<LabLayout />}>
          <Route index element={<Navigate to={ROUTES.labVideo} replace />} />
          <Route path="video" element={<VideoPlayerPage />} />
          <Route path="calibration" element={<VideoCalibrationPage />} />
          <Route path="detection" element={<VideoDetectionPage />} />
          <Route path="notes" element={<VideoNotesPage />} />
          <Route path="examples" element={<ExamplesPage />} />
          <Route path={LAB_EXAMPLE_PATTERN.replace(`${ROUTES.lab}/`, "")} element={<ExamplesPage />} />
        </Route>

        {LEGACY_REDIRECTS.map(([from, to]) => (
          <Route key={from} path={from} element={<LegacyRedirect to={to} />} />
        ))}

        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
