/**
 * Every route path in one place. Nothing hardcodes a URL string: navigation,
 * the top bar and the Playground tab strip all read from here.
 *
 * The Playground had seven tabs. Five of them drew a matrix at a chosen tempo
 * and granularity, and P4.2 removed that model from the backend, so they were
 * retired with it: Matrix, Piano Roll, Notes Falling, Notes Falling (raw) and
 * Music Notation. What they showed is either gone by design (a beats-based
 * score) or waiting to be rebuilt on the wall clock.
 */

export const ROUTES = {
  youtube: "/youtube",
  playground: "/playground",
  playgroundInput: "/playground/input",
  playgroundRhythm: "/playground/rhythm",
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
  { label: "Rhythm", to: ROUTES.playgroundRhythm },
];
