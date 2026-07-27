/**
 * Every route path in one place. Nothing hardcodes a URL string: navigation,
 * the top bar and the Playground tab strip all read from here.
 */

export const ROUTES = {
  youtube: "/youtube",
  playground: "/playground",
  playgroundInput: "/playground/input",
  playgroundMatrix: "/playground/matrix",
  playgroundPianoRoll: "/playground/piano-roll",
  playgroundNotesFalling: "/playground/notes-falling",
  playgroundNotation: "/playground/notation",
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

export const PLAYGROUND_TABS = [
  { label: "Upload / Input", to: ROUTES.playgroundInput },
  { label: "Matrix", to: ROUTES.playgroundMatrix },
  { label: "Piano Roll", to: ROUTES.playgroundPianoRoll },
  { label: "Notes Falling", to: ROUTES.playgroundNotesFalling },
  { label: "Music Notation", to: ROUTES.playgroundNotation },
];
