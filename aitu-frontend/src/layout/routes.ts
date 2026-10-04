/**
 * Every route path in one place. Nothing hardcodes a URL string: navigation,
 * the top bar and the Playground tab strip all read from here.
 *
 * The Playground had seven tabs. Five of them drew a matrix at a chosen tempo
 * and granularity, and P4.2 removed that model from the backend, so they were
 * retired with it: Matrix, Piano Roll, Notes Falling, Notes Falling (raw) and
 * Music Notation.
 *
 * **Piano Roll and Notes Falling came back**, rebuilt on the wall clock: they read
 * `GET /matrix/{id}/events` and draw the recording in seconds, so neither of them
 * asks for a tempo or a resolution. The other three stay retired — Matrix and
 * Notes Falling (raw) were views of a grid that no longer exists, and Music
 * Notation is the Rhythm tab now.
 *
 * **The Piano Roll left again in implementation 08** (Q-4): the Notes and Hands
 * tabs of the flow page are the piano roll visualization now, with its editor.
 * `/playground/piano-roll` redirects to the piece.
 */

import type { PieceStep } from "../api/pieces";

export const ROUTES = {
  /** The flow page (implementation 08): one tab per step, from the audio to the piano sheet. */
  pieceRoot: "/piece",
  pieceNew: "/piece/new",
  /** A piece at one step, or at the step it opens on when `step` is left out. */
  piece: (uuid: string, step?: PieceStep) => (step ? `/piece/${uuid}/${step}` : `/piece/${uuid}`),
  youtube: "/youtube",
  video: "/video",
  videoPlayer: "/video/player",
  videoCalibration: "/video/calibration",
  videoDetection: "/video/detection",
  videoNotes: "/video/notes",
  videoExamples: "/video/examples",
  videoExample: (slug: string) => `/video/examples/${slug}`,
  playground: "/playground",
  playgroundInput: "/playground/input",
  playgroundRhythm: "/playground/rhythm",
  playgroundNotesFalling: "/playground/notes-falling",
  library: "/library",
  libraryPlay: (id: string) => `/library/play/${id}`,
  /** The Notes tab's performance measurements (Phase 7), in a development build only. */
  devRollBench: "/dev/roll-bench",
} as const;

/** Pattern form for `<Route path>`; `piece` is a function above. */
export const PIECE_PATTERN = "/piece/:uuid";

/** Pattern form for `<Route path>`; `libraryPlay` is a function above. */
export const LIBRARY_PLAY_PATTERN = "/library/play/:id";

/** Pattern form for `<Route path>`; `videoExample` is a function above. */
export const VIDEO_EXAMPLE_PATTERN = "/video/examples/:slug";

export const TOP_SECTIONS = [
  // First, because it is where a piece now starts: audio in, notes, hands, then the sheet.
  { label: "Piece", to: ROUTES.pieceRoot },
  { label: "YouTube to Audio", to: ROUTES.youtube },
  { label: "Video to Notes", to: ROUTES.video },
  { label: "Playground", to: ROUTES.playground },
  { label: "Piano Library", to: ROUTES.library },
];

/**
 * Tab order is the order of the work: bring a piece in, look at how it was
 * actually played, then name the figures and write the sheet. Notes Falling
 * sits between input and Rhythm because that is when it is useful — it is how
 * you check the transcription before you commit to reading it.
 */
export const PLAYGROUND_TABS = [
  { label: "Upload / Input", to: ROUTES.playgroundInput },
  { label: "Notes Falling", to: ROUTES.playgroundNotesFalling },
  { label: "Piano Sheet", to: ROUTES.playgroundRhythm },
];

/**
 * Video to Notes: the tabs are the order of the work. Bring the video in, fit the
 * piano overlay onto it, read the falling rectangles, turn them into the piece,
 * and — on the example screenshots — check what was read against what a person
 * read by hand.
 *
 * Detection and Notes are two different readings of the same video and both are
 * kept. Detection is per sampled frame: what the picture showed at one moment,
 * which is what a hand reading can be compared against. Notes is the whole video
 * stitched into one picture whose vertical axis is time (V-32), which is what
 * becomes the piece.
 *
 * Examples is last because it is the measuring tab, not a step of the work: it is
 * where a detection rule earns its place before it is trusted on a real video.
 */
export const VIDEO_TABS = [
  { label: "Video", to: ROUTES.videoPlayer },
  { label: "Calibration", to: ROUTES.videoCalibration },
  { label: "Detection", to: ROUTES.videoDetection },
  { label: "Notes", to: ROUTES.videoNotes },
  { label: "Examples", to: ROUTES.videoExamples },
];
