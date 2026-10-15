/**
 * The route table (implementation 02, plan section 6.3). Every path is declared in
 * `layout/routes.ts`; the router itself is created in `main.tsx`, which renders this table inside it.
 *
 * `/login` and Play mode (`/play/...`, Phase 11) are outside the shell. My library (`/library/...`, Phase 6; its playlists, Phase 10) is the
 * Private Library. Every other page needs a user signed in (`RequireUser`), and the
 * Admin pages, Users and Lab, the master user (`RequireMaster`; Phase 4).
 */

import { lazy, Suspense } from "react";
import { Navigate, Route, Routes, useParams } from "react-router-dom";
import AppLayout from "./layout/AppLayout";
import LabLayout from "./layout/LabLayout";
import LegacyRedirect from "./layout/LegacyRedirect";
import { RequireMaster, RequireUser } from "./layout/RequireUser";
import {
  LAB_EXAMPLE_PATTERN,
  LEGACY_REDIRECTS,
  LIBRARY_ARTIST_PATTERN,
  LIBRARY_PLAYLIST_PATTERN,
  LIBRARY_SONG_PATTERN,
  PASSAGE_PATTERN,
  PLAY_PATTERN,
  PLAY_PLAYLIST_PATTERN,
  PROJECT_PATTERN,
  ROUTES,
} from "./layout/routes";
import UsersPage from "./pages/admin/UsersPage";
import ArtistPage from "./pages/library/ArtistPage";
import ArtistsPage from "./pages/library/ArtistsPage";
import PlaylistPage from "./pages/library/PlaylistPage";
import PlaylistsPage from "./pages/library/PlaylistsPage";
import SongPage from "./pages/library/SongPage";
import SongsPage from "./pages/library/SongsPage";
import LoginPage from "./pages/LoginPage";
import NotFoundPage from "./pages/NotFoundPage";
import ComposePage from "./pages/compose/ComposePage";
import ProjectsPage from "./pages/ProjectsPage";
import AudioTab from "./pages/piece/AudioTab";
import HandsTab from "./pages/piece/HandsTab";
import NotesTab from "./pages/piece/NotesTab";
import PassagePage from "./pages/piece/passage/PassagePage";
import PiecePage from "./pages/piece/PiecePage";
import PlayPage from "./pages/play/PlayPage";
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

/** Play mode, drawn again from the start for another project or playlist. */
function PlayRoute() {
  const { projectId, playlistId } = useParams();
  return <PlayPage key={playlistId ? `playlist:${playlistId}` : `project:${projectId}`} />;
}

export default function App() {
  return (
    <Routes>
      <Route path={ROUTES.login} element={<LoginPage />} />
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
      {/*
        Play mode (Phase 11): the sheet alone, outside the shell. Keyed by the address's id, so
        nothing of one song or playlist is left on the next.
      */}
      <Route
        path={PLAY_PATTERN}
        element={
          <RequireUser>
            <PlayRoute />
          </RequireUser>
        }
      />
      <Route
        path={PLAY_PLAYLIST_PATTERN}
        element={
          <RequireUser>
            <PlayRoute />
          </RequireUser>
        }
      />
      <Route
        element={
          <RequireUser>
            <AppLayout />
          </RequireUser>
        }
      >
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
        {/* Recording in Sheet (Phase 9): a passage of a project, its Current and its Proposal. */}
        <Route path={ROUTES.projectCompose} element={<ComposePage />} />
        <Route path={PASSAGE_PATTERN} element={<PassagePage />} />
        <Route path={PROJECT_PATTERN} element={<PiecePage />}>
          <Route index element={<PieceResume />} />
          <Route path="source" element={<SourceTab />} />
          <Route path="audio" element={<AudioTab />} />
          <Route path="notes" element={<NotesTab />} />
          <Route path="hands" element={<HandsTab />} />
          <Route path="sheet" element={<SheetTab />} />
        </Route>

        {/* My library: the Private Library (Phase 6). */}
        <Route path={ROUTES.librarySongs} element={<SongsPage />} />
        <Route path={LIBRARY_SONG_PATTERN} element={<SongPage />} />
        <Route path={ROUTES.libraryArtists} element={<ArtistsPage />} />
        <Route path={LIBRARY_ARTIST_PATTERN} element={<ArtistPage />} />
        <Route path={ROUTES.libraryPlaylists} element={<PlaylistsPage />} />
        <Route path={LIBRARY_PLAYLIST_PATTERN} element={<PlaylistPage />} />

        <Route
          path={ROUTES.adminUsers}
          element={
            <RequireMaster>
              <UsersPage />
            </RequireMaster>
          }
        />
        <Route
          path={ROUTES.lab}
          element={
            <RequireMaster>
              <LabLayout />
            </RequireMaster>
          }
        >
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
