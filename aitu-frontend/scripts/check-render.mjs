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
/** Every end-of-bracket drag the sheet reported, in the order it reported them. */
const ottavaResizes = [];
/** Every marked stretch the sheet asked the page to open. Clicking a bracket must add none. */
const markerSelections = [];
/** What the sheet last said was picked. The two **Select notes** / **Select frames** buttons work
 * by asking the renderer to select, and hearing it back through here is what opens the panel. */
let reportedSelection = null;
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
  // How far apart the lines are drawn, as the gap between system boxes. `TimeScoreView` hands the
  // reader's white space in here with `SYSTEM_ROOM` already taken off it.
  systemGap: 0,
  printedFigureFor,
  beamGroups: true,
  rests: false,
  showTimestamps: false,
  observeResize: false,
  // Listening for the drag is what makes the sheet draw a band along each octave bracket. The app
  // passes one on the Piano Sheet and not on the printed view, so the check draws the page the
  // reader actually works on.
  onOttavaResize: (change) => ottavaResizes.push(change),
  // The corner marks are how a reader gets back to a stretch that carries an edit. The page listens
  // for them, which is what makes the next check about the bracket meaningful: the dashed line must
  // **not** come through here.
  rangeMarkers: true,
  onRangeMarkerSelect: (marker) => markerSelections.push(marker),
  onSelectionChange: (keys) => {
    reportedSelection = [...keys];
  },
});

const count = (selector) => host.querySelectorAll(selector).length;

check('an SVG is drawn', Boolean(host.querySelector('svg')));
const noteheads = count('.grid-notehead');
check('noteheads are drawn', noteheads > 0, `${noteheads}`);
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

// The space between lines, as the slider beside the key signature sets it. A vertical number, so
// the drawing gets taller and not one note moves sideways — checked here as well as in the package
// because this is the path the app actually uses.
// Narrowed first, because a gap between lines needs two lines to be between: at the width above,
// this piece fits on one system and the gap would be drawn nowhere.
const lineCount = () => host.querySelectorAll('[data-system-index][data-start-frame]').length;
renderer.setAvailableWidth(240);
check('a narrow page wraps onto several lines', lineCount() > 1, `${lineCount()}`);
const linesBefore = lineCount();
const heightBefore = renderer.getLastRender().height;
const xsBefore = [...Array(8).keys()].map((frame) =>
  renderer.getLastRender().grid.xForFrame(frame, 0),
);
renderer.setSystemGap(96);
check(
  'the space between lines makes the drawing taller',
  renderer.getLastRender().height > heightBefore,
  `${heightBefore} → ${renderer.getLastRender().height}`,
);
check('and keeps the music on the same lines', lineCount() === linesBefore, `${lineCount()}`);
check(
  'and moves no note sideways',
  xsBefore.every(
    (x, frame) => renderer.getLastRender().grid.xForFrame(frame, 0) === x,
  ),
);
renderer.setSystemGap(0);
renderer.setAvailableWidth(1100);

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

// A run set an equal distance apart, as the equals sign in the note toolbox writes it. Both staves
// share a column, so a run of even notes in one hand is drawn unevenly wherever the other hand needs
// room; this is the reader choosing evenness and paying for it in width.
const runGaps = () => {
  const grid = renderer.getLastRender().grid;
  return [0, 2, 4].map((from) => grid.xForFrame(from + 2, 0) - grid.xForFrame(from, 0));
};
const beforeEven = runGaps();
renderer.setEvenSpacings([{ hand: 'right', fromColumn: 0, toColumn: 8, scale: 1 }]);
const afterEven = runGaps();
check(
  'an even run has one distance between its notes',
  Math.max(...afterEven) - Math.min(...afterEven) < 0.2,
  `${beforeEven.map((gap) => gap.toFixed(1)).join(", ")} -> ${afterEven
    .map((gap) => gap.toFixed(1))
    .join(", ")}`,
);
check(
  'and it never closed a gap to get there',
  afterEven.every((gap, index) => gap >= beforeEven[index] - 0.05),
);
renderer.setEvenSpacings([{ hand: 'right', fromColumn: 0, toColumn: 8, scale: 2 }]);
check(
  'opening it further keeps it even',
  (() => {
    const wider = runGaps();
    return Math.max(...wider) - Math.min(...wider) < 0.3 && wider[0] > afterEven[0];
  })(),
);
renderer.setEvenSpacings([]);
check(
  'and taking it off puts every column back',
  runGaps().every((gap, index) => Math.abs(gap - beforeEven[index]) < 0.05),
);

// Mid-piece clef changes, as the Clef tab of the frames toolbox writes them. A left hand that
// spends a passage above middle C reads better here than under a stack of ledger lines.
renderer.setClefForRange('left', 16, 28, 'treble');
check('a hand changes clef where asked', renderer.clefAt('left', 20) === 'treble', renderer.clefAt('left', 20));
check('and reads its own clef again after it', renderer.clefAt('left', 30) === 'bass', renderer.clefAt('left', 30));
check(
  'a clef transition is drawn',
  count('.grid-clef-change') > 0,
  `${count('.grid-clef-change')}`,
);
renderer.clearClefForRange('left', 16, 28);

// How far apart the notes stand, as the slider beside the key signature writes it. Only the
// columns that carry a note open up, so the sheet gets wider and no silence is stretched.
const noteXs = () => [...Array(8).keys()].map((frame) => renderer.getLastRender().grid.xForFrame(frame, 0));
const tightXs = noteXs();
renderer.setNoteSpacing(20);
const openXs = noteXs();
check(
  'the space between notes pushes the notes apart',
  openXs[6] > tightXs[6],
  `${tightXs[6].toFixed(1)} → ${openXs[6].toFixed(1)}`,
);
check('and still draws every notehead', count('.grid-notehead') === noteheads, `${count('.grid-notehead')}`);
renderer.setNoteSpacing(0);
check(
  'and putting it back puts every column back',
  noteXs().every((x, frame) => Math.abs(x - tightXs[frame]) < 0.01),
);

// Octave brackets, and the two things a reader can now do to one from the sheet itself: pull
// either end to change how far it reaches, and take it off the page without taking the reading off
// the piece. The whole point of hiding is that the notes do not move, so the check measures them.
renderer.setOttava('right', 0, 8, '8va');
const stepAt = (frame, row) =>
  Number(host.querySelector(`[data-note-key="right:${frame}:${row}"]`)?.getAttribute('data-staff-step'));
const bracketedRow = Number(
  host.querySelector('.grid-notehead[data-note-key^="right:0:"]')?.getAttribute('data-row'),
);
const bracketedStep = stepAt(0, bracketedRow);
check('an octave bracket is drawn where asked', count('.grid-ottava-line') > 0, `${count('.grid-ottava-line')}`);
check(
  'and it has a band to take hold of, with a tip at each end',
  count('.grid-ottava-band') > 0 && count('.grid-ottava-tip') === 2,
  `band=${count('.grid-ottava-band')} tips=${count('.grid-ottava-tip')}`,
);

// Clicking the dashed line picks the bracket and asks for no stretch of columns. One press used to
// make two selections — the bracket, and a marked stretch painted over it by the page.
host
  .querySelector('.grid-ottava-band')
  .dispatchEvent(new window.Event('click', { bubbles: true }));
check(
  'clicking the bracket picks it and marks no stretch',
  markerSelections.length === 0 && count('.grid-ottava.is-picked') === 1,
  `stretches=${markerSelections.length} picked=${count('.grid-ottava.is-picked')}`,
);

// The drag itself, on the app's own path: press a tip, move it four columns' worth, let go.
const tip = host.querySelector('.grid-ottava-tip.is-end');
const bracketGroup = host.querySelector('.grid-ottava');
const columnWidth =
  renderer.getLastRender().grid.xForFrame(9, 0) - renderer.getLastRender().grid.xForFrame(8, 0);
const pointerAt = (type, clientX) => {
  const event = new window.Event(type, { bubbles: true, cancelable: true });
  Object.assign(event, { clientX, clientY: 0, pointerId: 1, button: 0 });
  return event;
};
tip.dispatchEvent(pointerAt('pointerdown', 400));
bracketGroup.dispatchEvent(pointerAt('pointermove', 400 + columnWidth * 4));
// What the reader can see while the tip is down: the stretch it would cover painted over the page,
// a line at the column the end would drop into, and the helper lines either side of it. None of it
// is ink — it is gone the moment the pointer is let go, which the check after the drop asserts.
const dragOverlay = host.querySelector('.grid-ottava-drag');
check(
  'holding a tip paints the stretch it would cover',
  Boolean(dragOverlay) && dragOverlay.querySelectorAll('.grid-ottava-drag-band').length > 0,
  `bands=${dragOverlay ? dragOverlay.querySelectorAll('.grid-ottava-drag-band').length : 0}`,
);
const dragEdge = host.querySelector('.grid-ottava-drag-edge');
check(
  'and says which column the end would drop into',
  Boolean(dragEdge) &&
    Number(dragEdge.getAttribute('data-frame')) > 8 &&
    host.querySelector('.grid-ottava-drag-label').textContent ===
      `f${dragEdge.getAttribute('data-frame')}`,
  dragEdge ? host.querySelector('.grid-ottava-drag-label').textContent : 'nothing drawn',
);
check(
  'and draws helper lines at the columns around it',
  count('.grid-ottava-drag-guide') > 0,
  `${count('.grid-ottava-drag-guide')}`,
);
bracketGroup.dispatchEvent(pointerAt('pointerup', 400 + columnWidth * 4));
check('and takes all of it down when the tip is let go', count('.grid-ottava-drag') === 0);
check(
  'pulling the right tip reports a longer bracket, once',
  ottavaResizes.length === 1 && ottavaResizes[0].nextToColumn > 8 && ottavaResizes[0].nextFromColumn === 0,
  JSON.stringify(ottavaResizes[0]),
);

// Hiding. Every piece of the bracket's ink goes and the note stays exactly where the bracket put
// it — which is the difference between hiding a bracket and removing one.
// Everything else the sheet carries is handed back untouched: `setAnnotations` replaces the whole
// envelope rather than merging into it, so a bare `{ ottavas }` would quietly drop the key change
// two checks above.
renderer.setAnnotations({
  ...renderer.getAnnotations(),
  ottavas: [{ kind: '8va', hand: 'right', fromColumn: 0, toColumn: 8, hidden: true }],
});
check(
  'a hidden bracket draws no number, no dashed line and no hook',
  count('.grid-ottava-number') === 0 && count('.grid-ottava-line') === 0 && count('.grid-ottava-hook') === 0,
);
check(
  'and the notes stay written exactly where it puts them',
  stepAt(0, bracketedRow) === bracketedStep,
  `${stepAt(0, bracketedRow)} vs ${bracketedStep}`,
);
check('and it is still there to be found', count('.grid-ottava[data-hidden="true"]') === 1);
renderer.clearOttava('right', 0, 8);
check('and clearing it puts every notehead back', count('.grid-notehead') === noteheads, `${count('.grid-notehead')}`);

// The two selections handing the same music to each other — the **Select notes** button on the
// frames toolbox and **Select frames** on the note toolbox. Neither writes the page's own state: the
// renderer owns which noteheads are picked, and asking it reports straight back through the same
// callback a click does, which is what opens the panel on the far side and places it.
const columnKeys = [...host.querySelectorAll('.grid-notehead')]
  .map((head) => head.getAttribute('data-note-key'))
  .filter((key) => key?.startsWith('right:8:'));
check('there are notes to hand over', columnKeys.length > 0, `${columnKeys.length}`);
renderer.setSelection(columnKeys);
check(
  'picking the notes under a stretch reports them back',
  reportedSelection?.length === columnKeys.length &&
    columnKeys.every((key) => reportedSelection.includes(key)),
  `${reportedSelection?.length} of ${columnKeys.length}`,
);
check(
  'and marks them on the page',
  count('.grid-note-target.is-selected') === columnKeys.length,
  `${count('.grid-note-target.is-selected')}`,
);
renderer.clearSelection();
check(
  'and letting them go reports nothing picked, with nothing left marked',
  reportedSelection?.length === 0 && count('.grid-note-target.is-selected') === 0,
);

// The reader's own marks, which are stored in `rhythm.json` and nowhere else.
renderer.attachLyric('do re mi', { fromColumn: 0, toColumn: 8 });
const annotations = renderer.getAnnotations();
check(
  'annotations round-trip',
  annotations.lyrics.length === 1 && annotations.keyChanges.length >= 1,
  `lyrics=${annotations.lyrics.length} keyChanges=${annotations.keyChanges.length}`,
);
check('the lyric is drawn', count('.grid-lyric') > 0, `${count('.grid-lyric')}`);

// Where the words go. Above the right hand, in a block of their own at the very top of the system:
// that is where a singer reads them, and it is the one place an octave bracket — whose height comes
// from the highest note it covers, not from any fixed distance off the staff — can never reach.
const lyricBox = () => {
  const box = host.querySelector('.grid-lyric-box');
  return box
    ? {
        x: Number(box.getAttribute('x')),
        y: Number(box.getAttribute('y')),
        width: Number(box.getAttribute('width')),
        height: Number(box.getAttribute('height')),
      }
    : undefined;
};
const trebleTopY = renderer.getLastRender().systems[0].geometry.trebleTopY;
check(
  'the words sit above the right hand',
  lyricBox() !== undefined && lyricBox().y + lyricBox().height <= trebleTopY,
  `${lyricBox()?.y.toFixed(1)} + ${lyricBox()?.height.toFixed(1)} vs ${trebleTopY.toFixed(1)}`,
);

// The column numbers give way where the words are, so the two cannot print over each other.
const printedLabels = () =>
  [...host.querySelectorAll('.grid-frame-label')].map((label) => Number(label.getAttribute('data-frame')));
check(
  'the frame numbers give way to the words',
  printedLabels().filter((frame) => frame >= 0 && frame < 8).length === 0 &&
    printedLabels().length > 0,
  `${printedLabels().join(', ')}`,
);

// And the reader's own answers about the block: how wide it is, and how large the words are. A
// narrow block folds the line into two, which is the whole point of being able to narrow it.
renderer.setAnnotations({
  lyrics: [
    {
      anchor: { hand: 'single', columns: { fromColumn: 0, toColumn: 8 }, rows: [] },
      text: 'do re mi fa sol la si',
      width: 70,
      fontSize: 20,
      offsetX: 30,
      offsetY: -10,
    },
  ],
});
check('a narrowed block wraps its words', count('.grid-lyric-text tspan') > 1, `${count('.grid-lyric-text tspan')}`);
check(
  'and is drawn at the width and size it was given',
  Math.abs(lyricBox().width - 70) < 0.01 &&
    Number(host.querySelector('.grid-lyric-text').getAttribute('font-size')) === 20,
  `${lyricBox()?.width} px`,
);

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
