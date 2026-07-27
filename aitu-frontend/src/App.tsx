/**
 * Route table. Sections and tabs are declared in `layout/routes.ts`; every page
 * is a placeholder until its epic lands, but the chrome and the shared working
 * artifact are real from day one.
 */

import { Navigate, Route, Routes } from "react-router-dom";
import AppLayout from "./layout/AppLayout";
import PlaygroundLayout from "./layout/PlaygroundLayout";
import { LIBRARY_PLAY_PATTERN, ROUTES } from "./layout/routes";
import LibraryPage from "./pages/LibraryPage";
import NotFoundPage from "./pages/NotFoundPage";
import PerformancePage from "./pages/PerformancePage";
import YouTubePage from "./pages/YouTubePage";
import InputPage from "./pages/playground/InputPage";
import MatrixPage from "./pages/playground/MatrixPage";
import NotationPage from "./pages/playground/NotationPage";
import NotesFallingPage from "./pages/playground/NotesFallingPage";
import PianoRollPage from "./pages/playground/PianoRollPage";

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<Navigate to={ROUTES.playgroundInput} replace />} />
        <Route path={ROUTES.youtube} element={<YouTubePage />} />

        <Route path={ROUTES.playground} element={<PlaygroundLayout />}>
          <Route index element={<Navigate to={ROUTES.playgroundInput} replace />} />
          <Route path="input" element={<InputPage />} />
          <Route path="matrix" element={<MatrixPage />} />
          <Route path="piano-roll" element={<PianoRollPage />} />
          <Route path="notes-falling" element={<NotesFallingPage />} />
          <Route path="notation" element={<NotationPage />} />
        </Route>

        <Route path={ROUTES.library} element={<LibraryPage />} />
        <Route path={LIBRARY_PLAY_PATTERN} element={<PerformancePage />} />

        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
