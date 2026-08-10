/**
 * Every route path in one place. Nothing hardcodes a URL string: navigation,
 * the top bar and the Playground tab strip all read from here.
 *
 * The Playground had seven tabs. Five of them drew a matrix at a chosen tempo
 * and granularity, and P4.2 removed that model from the backend, so they were
 * retired with it: Matrix, Piano Roll, Notes Falling, Notes Falling (raw) and
 * Music Notation.
 *
 * **Piano Roll and Notes Falling are back**, rebuilt on the wall clock: they read
 * `GET /matrix/{id}/events` and draw the recording in seconds, so neither of them
 * asks for a tempo or a resolution. The other three stay retired — Matrix and
 * Notes Falling (raw) were views of a grid that no longer exists, and Music
 * Notation is the Rhythm tab now.
 */

export const ROUTES = {
  youtube: "/youtube",
  playground: "/playground",
  playgroundInput: "/playground/input",
  playgroundRhythm: "/playground/rhythm",
  playgroundPianoRoll: "/playground/piano-roll",
  playgroundNotesFalling: "/playground/notes-falling",
  library: "/library",
  libraryPlay: (id: string) => `/library/play/${id}`,
} as const;

/** Pattern form for `<Route path>`; `libraryPlay` is a function above. */
export const LIBRARY_PLAY_PATTERN = "/library/play/:id";

export const TOP_SECTIONS = [
  { label: "YouTube to Audio", to: ROUTES.youtube },
  { label: "Playground", to: ROUTES.playground },
  { label: "Piano Library", to: ROUTES.library },
];

/**
 * Tab order is the order of the work: bring a piece in, look at how it was
 * actually played, then name the figures and write the sheet. The two visual
 * views sit between input and Rhythm because that is when they are useful —
 * they are how you check the transcription before you commit to reading it.
 */
export const PLAYGROUND_TABS = [
  { label: "Upload / Input", to: ROUTES.playgroundInput },
  { label: "Piano Roll", to: ROUTES.playgroundPianoRoll },
  { label: "Notes Falling", to: ROUTES.playgroundNotesFalling },
  { label: "Rhythm", to: ROUTES.playgroundRhythm },
];
