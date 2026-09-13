/**
 * Headless render check for `@aimpromptu/grid-notation`.
 *
 * Why it exists: a notation renderer fails loudly at draw time and **silently at
 * layout time**. A wrong option name throws and you see it; a score that draws
 * no noteheads, or loses a hand, or stops beaming, renders a blank-looking page
 * with no error at all. Neither typecheck nor lint can see either one.
 *
 * So this draws a real wall-clock envelope into jsdom and asserts against the
 * stable DOM contract the package documents. Plain `.mjs` on purpose: no build
 * step and no native dependency, so it runs anywhere Node does.
 *
 *     npm run check:render
 *
 * **It mirrors what the app actually does**, which is the only way it can guard
 * it. `TimeScoreView` builds a `GridNotationRenderer` from a schema 2.0 envelope
 * and hands it each note's printed figure through `printedFigureFor`; so does
 * this. Rewritten 2026-09-13: the fixture was still a 1.x `tempoBpm` /
 * `granularity` envelope built for `GridNotationEditor`, which the package has
 * refused since its 1.x reader was deleted in P6.9 — so this check had not run
 * for a month and nothing said so.
 */

import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const require = createRequire(import.meta.url);
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

const { JSDOM } = require('jsdom');

// ---------------------------------------------------------------- environment

const dom = new JSDOM('<!doctype html><html><body><div id="score"></div></body></html>', {
  pretendToBeVisual: true,
});
const { window } = dom;

globalThis.window = window;
globalThis.document = window.document;
globalThis.HTMLElement = window.HTMLElement;
globalThis.SVGElement = window.SVGElement;
globalThis.Element = window.Element;
globalThis.Node = window.Node;
globalThis.getComputedStyle = window.getComputedStyle.bind(window);
globalThis.requestAnimationFrame = (cb) => window.setTimeout(() => cb(Date.now()), 16);
globalThis.cancelAnimationFrame = (id) => window.clearTimeout(id);
// `navigator` is getter-only on newer Node globals, so it needs defining rather
// than assigning.
Object.defineProperty(globalThis, 'navigator', {
  value: window.navigator,
  configurable: true,
});
// jsdom has no layout engine and therefore no ResizeObserver. The renderer is
// built with `observeResize: false` below, but define one so nothing installing
// it defensively explodes.
class NoopResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver = NoopResizeObserver;
window.ResizeObserver = NoopResizeObserver;

const { GridNotationRenderer, extractMatrixMusic, parseMatrixEnvelope } = await import(
  path.join(root, 'node_modules/@aimpromptu/grid-notation/dist/index.js')
);

// ---------------------------------------------------------------- the fixture

/** Cells as `[column, row, isOnset]` into the COO payload the backend writes. */
function coo(cells, frames) {
  const rows = [];
  const cols = [];
  const onset = [];
  for (const [col, row, isOnset] of cells) {
    rows.push(row);
    cols.push(col);
    onset.push(isOnset ? row : -1);
  }
  return { format: 'binary-coo', shape: [88, frames], rows, cols, onset };
}

const FRAMES = 32;
const FRAME_MS = 40;

// Right hand: a C major scale in two-column notes, then a chord containing a
// second — the case that must displace a notehead rather than move the stem.
const right = [];
[39, 41, 43, 44, 46, 48, 50, 51].forEach((row, i) => {
  right.push([i * 2, row, true], [i * 2 + 1, row, false]);
});
for (const col of [16, 20, 24, 28]) {
  for (const row of [51, 52, 55]) right.push([col, row, true], [col + 1, row, false]);
}

// Left hand: triads on the same columns, held four columns. Same columns is the
// point — it is what makes the alignment assertion below meaningful.
const left = [];
[0, 4, 8, 12, 16, 20, 24, 28].forEach((col, i) => {
  const base = 27 + (i % 3) * 2;
  for (const row of [base, base + 4, base + 7]) {
    left.push([col, row, true]);
    for (let k = 1; k < 4; k += 1) left.push([col + k, row, false]);
  }
});

// Schema 2.0. One column is `frameMs` of wall clock and carries no rhythmic
// meaning, so there is no tempo here and no note-figure resolution: what each
// note is *called* arrives separately, through `printedFigureFor`.
const payload = {
  schemaVersion: '2.0',
  sparse: true,
  frameMs: FRAME_MS,
  matrixProcessingStep: 'two-hands',
  title: 'render check',
  keySignature: 'C',
  rMatrix: coo(right, FRAMES),
  lMatrix: coo(left, FRAMES),
};

// What the backend decided each note is called. The scale runs in corcheas and
// the chords are negras; a negra cannot be under a beam, so this fixture also
// pins that the grouping follows the names rather than the columns.
//
// The backend names figures in Spanish and the package in English, so the app
// maps between them (`VEXFLOW_FIGURE` in `TimeScoreView`). That map is part of
// the seam, so the check crosses it the same way rather than skipping it.
const VEXFLOW_FIGURE = { negra: 'quarter', corchea: 'eighth' };
const SCALE_FIGURE = 'corchea';
const CHORD_FIGURE = 'negra';
const chordColumns = new Set([16, 20, 24, 28]);
const backendFigureAt = (hand, onsetFrame) => {
  if (hand === 'left') return CHORD_FIGURE;
  return chordColumns.has(onsetFrame) ? CHORD_FIGURE : SCALE_FIGURE;
};
const printedFigureFor = (hand, onsetFrame) => VEXFLOW_FIGURE[backendFigureAt(hand, onsetFrame)];

// ----------------------------------------------------------------- assertions

const passed = [];
const failed = [];
const check = (name, condition, detail = '') => {
  (condition ? passed : failed).push(detail ? `${name} — ${detail}` : name);
};

const { envelope, summary, warnings } = parseMatrixEnvelope(payload);
check('the envelope parses', Boolean(envelope));
check(
  'both hands came from the payload',
  summary.onsets.right > 0 && summary.onsets.left > 0,
  `right=${summary.onsets.right} left=${summary.onsets.left}`,
);
check('the frame count survives', summary.frameCount === FRAMES, String(summary.frameCount));
check('a consistent envelope warns about nothing', warnings.length === 0, warnings.join('; '));
// The summary reports `frameMs` and no tempo, which is the schema 2.0 header in
// one assertion: a column is a length of time and says nothing about figures.
check('a column is frameMs of wall clock', summary.frameMs === FRAME_MS, String(summary.frameMs));
check(
  'the wall-clock length follows from the columns',
  Math.abs(summary.durationSeconds - (FRAMES * FRAME_MS) / 1000) < 1e-9,
  String(summary.durationSeconds),
);

const timeStepSeconds = summary.frameMs / 1000;

const music = extractMatrixMusic(envelope);
check('onset groups are extracted', music.groups.length > 0, `${music.groups.length} groups`);

const host = document.getElementById('score');
const renderer = new GridNotationRenderer(host, {
  frameCount: summary.frameCount,
  timeStepSeconds,
  matrixEnvelope: envelope,
  keySignature: 'C',
  availableWidth: 1100,
  // The wall-clock aggregation levels. Neither means anything musical.
  frameGroup: 8,
  frameMeasure: 16,
  silenceGroupPx: 6,
  printedFigureFor,
  beamGroups: true,
  rests: false,
  showTimestamps: false,
  observeResize: false,
});

const count = (selector) => host.querySelectorAll(selector).length;

check('an SVG is drawn', Boolean(host.querySelector('svg')));
check('noteheads are drawn', count('.grid-notehead') > 0, `${count('.grid-notehead')}`);
check('onset groups reach the DOM', count('.grid-onset-group') > 0, `${count('.grid-onset-group')}`);
check('notes are beamed', count('.grid-beam-group') > 0, `${count('.grid-beam-group')}`);
check('every notehead is clickable', count('.grid-note-target') === count('.grid-notehead'));
check('the frame ruler is labelled', count('.grid-frame-label') > 0, `${count('.grid-frame-label')}`);
check('the music is laid out in systems', count('[data-start-frame]') > 0);
check('no rest is drawn', count('[data-figure*="rest"]') === 0);

const hands = new Set(
  [...host.querySelectorAll('.grid-onset-group')].map((g) => g.getAttribute('data-hand')),
);
check('both hands are drawn', hands.has('right') && hands.has('left'), [...hands].join(', '));

const noteKeys = [...host.querySelectorAll('.grid-notehead')].map((n) =>
  n.getAttribute('data-note-key'),
);
check(
  'note identity is hand:onsetFrame:row',
  noteKeys.length > 0 && noteKeys.every((key) => /^(right|left|single):\d+:\d+$/.test(key)),
  noteKeys[0] ?? 'none',
);

// The whole point of the wall-clock model: the backend names every figure and
// the renderer draws what it is told. If this stops holding, the page has gone
// back to deriving a note value from how many columns it covers.
const figures = new Set(
  [...host.querySelectorAll('[data-figure]')].map((n) => n.getAttribute('data-figure')),
);
check(
  "the backend's figures are what get drawn",
  figures.has(VEXFLOW_FIGURE[SCALE_FIGURE]) && figures.has(VEXFLOW_FIGURE[CHORD_FIGURE]),
  [...figures].join(', '),
);

// The alignment guarantee, which is the whole reason this package exists: both
// hands strike at frame 0, so both must be drawn at the same x.
const at = (hand, frame) =>
  host.querySelector(`.grid-onset-group[data-hand="${hand}"][data-onset-frame="${frame}"]`);
check('both hands have an onset at frame 0', Boolean(at('right', 0) && at('left', 0)));

// Mid-piece key changes, as the Key tab of the frames toolbox writes them.
renderer.setKeySignatureForRange(16, 28, 'Eb');
check(
  'the key changes where asked',
  renderer.keySignatureAt(20) === 'Eb',
  renderer.keySignatureAt(20),
);
check(
  'the key reverts after the range',
  renderer.keySignatureAt(30) === 'C',
  renderer.keySignatureAt(30),
);
check('a key transition is drawn', count('.grid-key-change') > 0, `${count('.grid-key-change')}`);

// The reader's own marks, which are stored in `rhythm.json` and nowhere else.
renderer.attachLyric('do re mi', { fromColumn: 0, toColumn: 8 });
const annotations = renderer.getAnnotations();
check(
  'annotations round-trip',
  annotations.lyrics.length === 1 && annotations.keyChanges.length >= 1,
  `lyrics=${annotations.lyrics.length} keyChanges=${annotations.keyChanges.length}`,
);
check('the lyric is drawn under the staff', count('.grid-lyric') > 0, `${count('.grid-lyric')}`);

// The renderer releases its resize observer and leaves the host alone — clearing
// it belongs to whoever created it, which for the app is React unmounting the
// container. Only the editor removes its own root, and the app does not use one.
renderer.destroy();
check('destroy releases the renderer without throwing', true);
check('destroy leaves the drawing for its owner to clear', Boolean(host.querySelector('svg')));

// --------------------------------------------------------------------- report

for (const name of passed) console.log(`  ✓ ${name}`);
for (const name of failed) console.error(`  ✗ ${name}`);
console.log(`\n${passed.length} passed, ${failed.length} failed`);

if (failed.length > 0) process.exit(1);
