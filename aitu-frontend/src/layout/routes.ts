/**
 * Every route path in one place (implementation 02, plan section 6.3). Nothing hardcodes a URL
 * string: navigation, the sidebar, the step tabs and the redirects all read from here.
 *
 * A project's id is the id of its first part, the uuid of the backend's routes (plan P-6).
 * `/projects/new` opens the Source step of a new project (**New project → From source** on the
 * Projects page; From scratch and From other projects come in Phases 8 and 10).
 *
 * **Lab** holds the video reader's development pages: the video, its calibration, the detection,
 * its notes and the examples it is measured on. A video project fits its piano and reads its notes
 * on its own Video step (`/projects/:id/audio`, Phase 5); Lab opens the same video for the master
 * user's measurements.
 *
 * `/login` is the one page outside the shell; every other page needs a user signed in, and the
 * Admin pages (Users, Lab) the master user (Phase 4).
 *
 * The old paths (`/piece/...`, `/playground/...`, `/youtube`, `/video/...`, `/library...`) redirect
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
  /** A project at one step, or at the step it opens on when `step` is left out. */
  project: (id: string, step?: PieceStep) => (step ? `/projects/${id}/${step}` : `/projects/${id}`),
  /** Notes Falling of a project, until Play mode makes it a view of its own (Phase 11). */
  projectNotesFalling: (id: string) => `/projects/${id}/notes-falling`,
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
  ["/library", ROUTES.projects],
  ["/library/*", ROUTES.projects],
];
