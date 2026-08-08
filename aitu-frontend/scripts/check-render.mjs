/**
 * Headless render check for `@aimpromptu/grid-notation`.
 *
 * Replaces the VexFlow-era `check-render.mts`, and exists for the same reason:
 * a notation renderer fails loudly at draw time and silently at layout time. A
 * wrong option name throws and you see it; a score that draws no noteheads, or
 * loses a hand, or stops beaming, renders a blank-looking page with no error at
 * all. Neither typecheck nor lint can see either one.
 *
 * So this draws a real two-hand envelope — the exact shape
 * `/notation/{id}/matrix` returns — into jsdom and asserts against the stable
 * DOM contract the package documents. It is plain `.mjs` on purpose: no build
 * step and no native dependency, so it runs anywhere Node does, including CI.
 *
 *     npm run check:render
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
// built with `observeResize: false` below, but the editor installs one anyway.
class NoopResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver = NoopResizeObserver;
window.ResizeObserver = NoopResizeObserver;

const { GridNotationEditor, extractMatrixMusic, parseMatrixEnvelope } = await import(
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

// Right hand: a C major scale in two-frame notes, then a chord containing a
// second — the case that must displace a notehead rather than move the stem.
const right = [];
[39, 41, 43, 44, 46, 48, 50, 51].forEach((row, i) => {
  right.push([i * 2, row, true], [i * 2 + 1, row, false]);
});
for (const col of [16, 20, 24, 28]) {
  for (const row of [51, 52, 55]) right.push([col, row, true], [col + 1, row, false]);
}

// Left hand: triads on the same columns, held four frames. Same columns is the
// point — it is what makes the alignment assertion below meaningful.
const left = [];
[0, 4, 8, 12, 16, 20, 24, 28].forEach((col, i) => {
  const base = 27 + (i % 3) * 2;
  for (const row of [base, base + 4, base + 7]) {
    left.push([col, row, true]);
    for (let k = 1; k < 4; k += 1) left.push([col + k, row, false]);
  }
});

// tempoBpm and timeStepSeconds must agree: the backend derives the latter as
// `beats_per_column * 60 / tempo_bpm` and the loader checks it. A semicorchea
// at 60 BPM is 0.25s.
const payload = {
  sparse: true,
  tempoBpm: 60,
  timeStepSeconds: 0.25,
  granularity: 'semicorchea',
  matrixProcessingStep: 'two-hands',
  title: 'render check',
  keySignature: 'C',
  rMatrix: coo(right, FRAMES),
  lMatrix: coo(left, FRAMES),
};

// ----------------------------------------------------------------- assertions

const passed = [];
const failed = [];
const check = (name, condition, detail = '') => {
  (condition ? passed : failed).push(detail ? `${name} — ${detail}` : name);
};

const { envelope, summary, warnings } = parseMatrixEnvelope(payload);
check('the envelope parses', Boolean(envelope));
check('both hands came from the payload', summary.handSplit === 'two-hand-payload', summary.handSplit);
check('the frame count survives', summary.frameCount === FRAMES, String(summary.frameCount));
check('a consistent envelope warns about nothing', warnings.length === 0, warnings.join('; '));

const music = extractMatrixMusic(envelope);
check('onset groups are extracted', music.groups.length > 0, `${music.groups.length} groups`);

const host = document.getElementById('score');
const editor = new GridNotationEditor(host, {
  frameCount: summary.frameCount,
  timeStepSeconds: summary.timeStepSeconds,
  matrixEnvelope: envelope,
  keySignature: 'C',
  availableWidth: 1100,
  player: false,
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

// The alignment guarantee, which is the whole reason this package exists: both
// hands strike at frame 0, so both must be drawn at the same x.
const at = (hand, frame) =>
  host.querySelector(`.grid-onset-group[data-hand="${hand}"][data-onset-frame="${frame}"]`);
const rightAt0 = at('right', 0);
const leftAt0 = at('left', 0);
check('both hands have an onset at frame 0', Boolean(rightAt0 && leftAt0));

// Mid-piece key changes, as the Key toolbox tab writes them.
editor.renderer.setKeySignatureForRange(16, 28, 'Eb');
check('the key changes where asked', editor.renderer.keySignatureAt(20) === 'Eb', editor.renderer.keySignatureAt(20));
check('the key reverts after the range', editor.renderer.keySignatureAt(30) === 'C', editor.renderer.keySignatureAt(30));
check('a key transition is drawn', count('.grid-key-change') > 0, `${count('.grid-key-change')}`);

// The annotation envelope is what `/notation/{id}/grid-state` stores verbatim.
editor.renderer.attachLyric('do re mi', { fromColumn: 0, toColumn: 8 });
const annotations = editor.renderer.getAnnotations();
check(
  'annotations round-trip',
  annotations.lyrics.length === 1 && annotations.keyChanges.length >= 1,
  `lyrics=${annotations.lyrics.length} keyChanges=${annotations.keyChanges.length}`,
);

editor.destroy();
check('destroy empties the host', host.querySelectorAll('svg').length === 0);

// --------------------------------------------------------------------- report

for (const name of passed) console.log(`  ✓ ${name}`);
for (const name of failed) console.error(`  ✗ ${name}`);
console.log(`\n${passed.length} passed, ${failed.length} failed`);

if (failed.length > 0) process.exit(1);
