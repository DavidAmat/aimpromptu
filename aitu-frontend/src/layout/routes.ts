/**
 * Every route path in one place (implementation 02, plan section 6.3). Nothing hardcodes a URL
 * string: navigation, the sidebar, the step tabs and the redirects all read from here.
 *
 * A project's id is the id of its first part, the uuid of the backend's routes (plan P-6).
 * `/projects/new` opens the Source step of a new project (**New project → From source** on the
 * Projects page); `/projects/compose` is **From other projects** (Phase 10), where passages of
 * other projects are chosen before the project is made.
 *
 * **Lab** holds the video reader's development pages: the video, its calibration, the detection,
 * its notes and the examples it is measured on. A video project fits its piano and reads its notes
 * on its own Video step (`/projects/:id/audio`, Phase 5); Lab opens the same video for the master
 * user's measurements.
 *
 * **My library** (`/library/songs`, `/library/artists`, Phase 6; `/library/playlists`, Phase 10) is
 * the Private Library: finished work, as songs with their versions, and the songs playlists.
 *
 * **Public library** (`/public/songs`, `/public/artists`, `/public/playlists`, Phase 13) is the Public
 * Library: every user's catalogue of songs, artists and playlists, with the versions published to it.
 *
 * **Shared** (`/library/shared`, Phase 14) lists the libraries other users share with the user
 * (`?from=<owner id>` picks one), and `/library/shared/songs/:id` one of their songs.
 *
 * **Requests** (`/requests`, Phase 14) are the user's requests to the Public Library; **Review**
 * (`/admin/requests`) is the master user's list of the requests to decide. One request opens at
 * `/requests/:id` for its author and at `/admin/requests/:id` for the review; `/sheet` after either
 * is its Sheet tab.
 *
 * **Play mode** (`/play/:projectId`, `/play/playlist/:id`, Phase 11) is the sheet alone, outside the
 * shell: a project or a version of the library, or a songs playlist. Notes Falling is one of its views
 * (`?view=falling`); its old address `/projects/:id/notes-falling` goes there.
 *
 * `/login` and Play mode are the pages outside the shell; every page needs a user signed in, and the
 * Admin pages (Users, Lab) the master user (Phase 4).
 *
 * The old paths (`/piece/...`, `/playground/...`, `/youtube`, `/video/...`, `/library/play/...`) redirect
 * to their new home (`LEGACY_REDIRECTS`) until Phase 15 removes them.
 */

import type { PieceStep } from "../api/pieces";

export const ROUTES = {
  home: "/",
  login: "/login",
  /** The sign-in page, coming back to `next` after. */
  signIn: (next?: string) => (next && next !== "/" ? `/login?next=${encodeURIComponent(next)}` : "/login"),
  /** Admin → Users: the master user's (Phase 4). */
  adminUsers: "/admin/users",
  projects: "/projects",
  projectNew: "/projects/new",
  /** **From other projects** (Phase 10): passages of other projects, then a new project. */
  projectCompose: "/projects/compose",
  /** A project at one step, or at the step it opens on when `step` is left out. */
  project: (id: string, step?: PieceStep) => (step ? `/projects/${id}/${step}` : `/projects/${id}`),
  /** A passage of a project being re-recorded: Current and Proposal (Record in Sheet, Phase 9). */
  passage: (projectId: string, passageId: string) => `/projects/${projectId}/passages/${passageId}`,
  /**
   * Play mode (Phase 11): a project or a version, from its first part. `falling` opens Notes Falling.
   */
  play: (projectId: string, options?: { falling?: boolean }) =>
    `/play/${projectId}${options?.falling ? "?view=falling" : ""}`,
  /** Play mode on a songs playlist, from its song `at` (0 is the first). */
  playPlaylist: (id: number, at = 0) => `/play/playlist/${id}${at > 0 ? `?at=${at}` : ""}`,
  /** Play mode on a playlist of the Public Library (Phase 13). */
  playPublicPlaylist: (id: number, at = 0) => `/play/playlist/${id}?from=public${at > 0 ? `&at=${at}` : ""}`,
  /** My library (the Private Library, Phase 6): songs with their versions, artists. */
  librarySongs: "/library/songs",
  librarySong: (id: number) => `/library/songs/${id}`,
  libraryArtists: "/library/artists",
  libraryArtist: (id: number) => `/library/artists/${id}`,
  /** The songs playlists of My library (Phase 10). */
  libraryPlaylists: "/library/playlists",
  libraryPlaylist: (id: number) => `/library/playlists/${id}`,
  /** The libraries shared with the user (Phase 14), one of them by its owner, and one song. */
  libraryShared: "/library/shared",
  librarySharedFrom: (ownerId: number) => `/library/shared?from=${ownerId}`,
  librarySharedSong: (id: number) => `/library/shared/songs/${id}`,
  /** The user's requests to the Public Library (Phase 14), and one of them. */
  requests: "/requests",
  request: (id: number) => `/requests/${id}`,
  /** Admin → Review (Phase 14): the requests to decide, and one of them. */
  adminRequests: "/admin/requests",
  adminRequest: (id: number) => `/admin/requests/${id}`,
  /** The Public Library (Phase 13): songs, artists, playlists. */
  publicSongs: "/public/songs",
  publicSong: (id: number) => `/public/songs/${id}`,
  publicArtists: "/public/artists",
  publicArtist: (id: number) => `/public/artists/${id}`,
  publicPlaylists: "/public/playlists",
  publicPlaylist: (id: number) => `/public/playlists/${id}`,
  lab: "/admin/lab",
  labVideo: "/admin/lab/video",
  labCalibration: "/admin/lab/calibration",
  labDetection: "/admin/lab/detection",
  labNotes: "/admin/lab/notes",
  labExamples: "/admin/lab/examples",
  labExample: (slug: string) => `/admin/lab/examples/${slug}`,
  /** The Notes tab's performance measurements (implementation 08, Phase 7), development builds only. */
  devRollBench: "/dev/roll-bench",
  /** Every shared component of `src/ui/` on one page, development builds only. */
  devUi: "/dev/ui",
} as const;

/** Pattern forms for `<Route path>`. */
export const PROJECT_PATTERN = "/projects/:id";
export const PASSAGE_PATTERN = "/projects/:id/passages/:passageId";
export const LIBRARY_SONG_PATTERN = "/library/songs/:id";
export const LIBRARY_ARTIST_PATTERN = "/library/artists/:id";
export const LIBRARY_PLAYLIST_PATTERN = "/library/playlists/:id";
export const LIBRARY_SHARED_SONG_PATTERN = "/library/shared/songs/:id";
export const REQUEST_PATTERN = "/requests/:id";
export const ADMIN_REQUEST_PATTERN = "/admin/requests/:id";
/** The Sheet tab of a request: its whole proposed sheet. */
export const REQUEST_SHEET_PATTERN = "/requests/:id/sheet";
export const ADMIN_REQUEST_SHEET_PATTERN = "/admin/requests/:id/sheet";
export const PUBLIC_SONG_PATTERN = "/public/songs/:id";
export const PUBLIC_ARTIST_PATTERN = "/public/artists/:id";
export const PUBLIC_PLAYLIST_PATTERN = "/public/playlists/:id";
export const PLAY_PATTERN = "/play/:projectId";
export const PLAY_PLAYLIST_PATTERN = "/play/playlist/:playlistId";
export const LAB_EXAMPLE_PATTERN = "/admin/lab/examples/:slug";

/** The Lab tabs, in the order of the work on a video; Examples last, because it is where a rule is measured. */
export const LAB_TABS = [
  { label: "Video", to: ROUTES.labVideo },
  { label: "Calibration", to: ROUTES.labCalibration },
  { label: "Detection", to: ROUTES.labDetection },
  { label: "Notes", to: ROUTES.labNotes },
  { label: "Examples", to: ROUTES.labExamples },
];

/**
 * The old paths and where they go now: `[old pattern, new path]`, where `:name` in the new path is
 * taken from the old one and `*` is the rest of the old path. The query string is kept, so a link
 * to `/video/notes?video=<uuid>` still opens that video.
 */
export const LEGACY_REDIRECTS: readonly (readonly [string, string])[] = [
  ["/piece", ROUTES.projects],
  ["/piece/new", ROUTES.projectNew],
  ["/piece/:id/*", "/projects/:id/*"],
  ["/playground/*", ROUTES.projects],
  ["/youtube", ROUTES.projectNew],
  ["/video", ROUTES.labVideo],
  ["/video/player", ROUTES.labVideo],
  ["/video/calibration", ROUTES.labCalibration],
  ["/video/detection", ROUTES.labDetection],
  ["/video/notes", ROUTES.labNotes],
  ["/video/examples", ROUTES.labExamples],
  ["/video/examples/:slug", "/admin/lab/examples/:slug"],
  ["/library", ROUTES.librarySongs],
  // The old Piano Library's performance page; My library has its songs now (Phase 6).
  ["/library/play/*", ROUTES.librarySongs],
  // Notes Falling is a view of Play mode since Phase 11.
  ["/projects/:id/notes-falling", "/play/:id?view=falling"],
];
