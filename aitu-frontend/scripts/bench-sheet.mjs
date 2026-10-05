/**
 * A hand move on the piano sheet, timed part by part in a headless Chromium (implementation 08,
 * Phase 8, Task 8.2.3; plan section 9.7, target under 300 ms for a 3.5-minute piece).
 *
 * For each piece it makes a temporary copy in the data folder (a new uuid, deleted at the end, so
 * the library is never changed), opens it on the Sheet step of the project and makes it current
 * the way a reader does: a stale reading shows its banner and waits for **Write the sheet** and
 * **Save**; a piece with no reading is drawn on arrival from the defaults and saved. Then it moves notes
 * to the other hand the way a reader does (a click on the notehead, then **L** or **R** in the
 * panel) and times each part:
 *
 * - `hands`: the `PUT /time/{uuid}/hands` request, from the press to its answer;
 * - `build`: the sheet request, from sent to the first byte of the answer (the backend builds it);
 * - `transfer`: the first byte to the last byte of the sheet answer, and its size as sent;
 * - `draw`: the last byte to the moved note in the page (parse, React, the drawing package);
 * - `paint`: to the next frame on screen;
 * - `total`: from the press to that frame.
 *
 * The first move of an old piece (no saved hands) also saves every hand and is reported apart.
 *
 *     npm run bench:sheet
 *     npm run bench:sheet -- --piece <uuid> --piece <uuid> --moves 6 --out result.json
 *
 * It needs `make up`. Headless Chromium on this machine draws without a GPU, and the requests do
 * not cross the SSH tunnel, so `transfer` is the time on this machine only.
 */

import { cpSync, mkdirSync, readdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { randomUUID } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { parseArgs } from 'node:util';
import { chromium } from 'playwright';

const here = path.dirname(fileURLToPath(import.meta.url));
const dataDir = path.join(here, '..', '..', 'aitu-backend', 'data', 'audio');
const { values } = parseArgs({
  options: {
    piece: {
      type: 'string',
      multiple: true,
      default: [
        '6594364e', // Elefants, 3:53, MuScriptor, saved hands, a stale sheet
        'b99bc3ae', // Superestrella tutorial, 3:10, ByteDance, no saved hands
        'ddd8bce8', // The Other Side, 4:33, the most notes of the library, no sheet
      ],
    },
    moves: { type: 'string', default: '6' },
    // Record a CPU profile of the first timed move and print where the main thread spent it.
    profile: { type: 'boolean', default: false },
    base: { type: 'string', default: 'http://localhost:5173' },
    out: { type: 'string' },
    shots: { type: 'string', default: path.join(here, '..', '..', '.run', 'screenshots', 'sheet') },
  },
});
const base = values.base;
const api = `${base}/api`;
const moves = Number(values.moves);
mkdirSync(values.shots, { recursive: true });

/** A piece named by its uuid or the first 8 characters of it. */
function resolvePiece(prefix) {
  const found = readdirSync(dataDir).find((name) => name.startsWith(prefix.slice(0, 8)));
  if (!found) throw new Error(`No piece starts with ${prefix}`);
  return found;
}

/** A copy of the piece under a new uuid, without its history, staging and video folders. */
function copyPiece(source) {
  const copy = randomUUID();
  const from = path.join(dataDir, source);
  const to = path.join(dataDir, copy);
  const skip = new Set(['history', 'staging', 'video']);
  cpSync(from, to, {
    recursive: true,
    filter: (file) => !skip.has(path.relative(from, file).split(path.sep)[0]),
  });
  const metadataPath = path.join(to, 'metadata.json');
  const metadata = JSON.parse(readFileSync(metadataPath, 'utf8'));
  metadata.uuid = copy;
  metadata.alias = `bench:sheet copy of ${metadata.alias}`;
  writeFileSync(metadataPath, JSON.stringify(metadata));
  return { copy, alias: metadata.alias.replace('bench:sheet copy of ', '') };
}

const median = (list) => {
  if (list.length === 0) return null;
  const sorted = [...list].sort((a, b) => a - b);
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2;
};
const round = (value) => (value === null || value === undefined ? null : Math.round(value * 10) / 10);

/**
 * Where a CPU profile spent its time: the functions with the most time of their own, and the most
 * time including what they call (a recursive function counted once).
 */
function summarise(profile) {
  const byId = new Map(profile.nodes.map((node) => [node.id, node]));
  const interval = profile.timeDeltas.reduce((a, b) => a + b, 0) / profile.samples.length / 1000;
  const name = (node) => {
    const frame = node.callFrame;
    const file = frame.url ? frame.url.split('/').pop().split('?')[0] : '';
    return `${frame.functionName || '(anonymous)'} ${file}:${frame.lineNumber + 1}`;
  };
  const own = new Map();
  const inclusive = new Map();
  const walk = (id, seen) => {
    const node = byId.get(id);
    const key = name(node);
    let total = (node.hitCount ?? 0) * interval;
    own.set(key, (own.get(key) ?? 0) + total);
    const inner = new Set(seen).add(key);
    for (const child of node.children ?? []) total += walk(child, inner);
    if (!seen.has(key)) inclusive.set(key, (inclusive.get(key) ?? 0) + total);
    return total;
  };
  walk(profile.nodes[0].id, new Set());
  const top = (map, n) => [...map.entries()].sort((a, b) => b[1] - a[1]).slice(0, n).map(([k, v]) => `${v.toFixed(1)} ms  ${k}`);
  return { own: top(own, 15), inclusive: top(inclusive, 30) };
}

const browser = await chromium.launch();
const report = { date: new Date().toISOString(), base, moves, pieces: [] };
const problems = [];

for (const source of values.piece.map(resolvePiece)) {
  const { copy, alias } = copyPiece(source);
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  page.on('pageerror', (e) => problems.push(`${alias}: page error: ${e.message} (${(e.stack ?? '').split('\n').slice(1, 4).map((l) => l.trim()).join(' < ')})`));
  // A 404 on `/rhythm` is how the page asks whether a reading exists; the browser logs it too.
  const expected = (url) => /\/time\/[^/]+\/rhythm$/.test(url);
  page.on('console', (m) => { if (m.type() === 'error' && !/status of 404/.test(m.text())) problems.push(`${alias}: console: ${m.text()}`); });
  page.on('response', (r) => { if (r.status() >= 400 && !(r.status() === 404 && expected(r.url()))) problems.push(`${alias}: ${r.status()} ${r.url()}`); });
  const status = async () => (await (await fetch(`${api}/pieces/${copy}/status`)).json()).steps[4];
  const piece = { source, alias, flow: {}, first: null, moves: [] };
  try {
    const notes = await (await fetch(`${api}/pieces/${copy}/notes`)).json();
    piece.notes = notes.id.length;
    piece.durationS = round(notes.durationMs / 1000);
    piece.flow.before = (await status()).state;

    // 0. A piece whose hands were never saved and that has no sheet cannot open its Sheet tab:
    //    predict and save its hands first, as the Hands tab does.
    if (!(await status()).enabled) {
      const predicted = await (await fetch(`${api}/pieces/${copy}/hands/predict`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ baseRevision: notes.revision }),
      })).json();
      const ids = (hand) => predicted.id.filter((_, i) => predicted.hand[i] === hand);
      const saved = await fetch(`${api}/pieces/${copy}/notes`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          baseRevision: notes.revision,
          baseHandsRevision: notes.handsRevision,
          ops: [{ op: 'hand', ids: ids('r'), hand: 'r' }, { op: 'hand', ids: ids('l'), hand: 'l' }],
        }),
      });
      if (!saved.ok) throw new Error(`Saving the predicted hands failed: ${saved.status} ${(await saved.text()).slice(0, 300)}`);
      piece.flow.handsPredicted = true;
    }

    // 1. The Sheet tab, made current the way a reader does it.
    await page.goto(`${base}/projects/${copy}/sheet`);
    await page.waitForSelector('[data-sheet-page]');
    // Every sheet but a stale one is drawn on arrival (implementation 02, Phase 2).
    if (piece.flow.before !== 'stale') await page.waitForSelector('.grid-notehead', { timeout: 60000 });
    const writeButton = page.getByRole('button', { name: 'Write the sheet', exact: true });
    if (piece.flow.before === 'stale') {
      await page.waitForSelector('[data-sheet-banner=stale]');
      await page.waitForTimeout(3000);
      piece.flow.staleDrawsNothing = (await page.locator('.grid-notehead').count()) === 0;
      await page.screenshot({ path: path.join(values.shots, `${source.slice(0, 8)}-stale.png`) });
    }
    if (piece.flow.before === 'missing') {
      await page.getByRole('button', { name: 'Save', exact: true }).click();
      await page.waitForFunction(() => document.querySelector('[data-unsaved]')?.getAttribute('data-unsaved') === '', null, { timeout: 15000 });
    }
    if ((await page.locator('.grid-notehead').count()) === 0) {
      await writeButton.waitFor();
      await page.waitForFunction(() => {
        const button = [...document.querySelectorAll('button')].find((b) => b.textContent === 'Write the sheet');
        return button && !button.disabled;
      }, null, { timeout: 30000 });
      const pressed = Date.now();
      await writeButton.click();
      await page.waitForSelector('.grid-notehead', { timeout: 60000 });
      piece.flow.writeMs = Date.now() - pressed;
      if (piece.flow.before === 'stale') {
        piece.flow.bannerAfterWrite = (await page.locator('[data-sheet-banner]').textContent()) ?? '';
      }
      await page.getByRole('button', { name: 'Save', exact: true }).click();
      await page.waitForFunction(() => document.querySelector('[data-sheet-banner]') === null, null, { timeout: 15000 });
    }
    piece.flow.after = (await status()).state;
    await page.waitForTimeout(300);
    piece.flow.tabTicked = (await page.locator('[role=tab][data-step=sheet]').getAttribute('data-state')) === 'ready';
    await page.waitForTimeout(1500);

    // 2. The hand moves: a right-hand note to the left hand, then a left-hand note to the right
    //    hand, each time another note, spread over the piece. (A click on a note also moves the
    //    playhead line onto it, and the line then takes the next click on that same note.)
    await page.evaluate(() => {
      window.__long = [];
      new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) window.__long.push({ start: entry.startTime, duration: entry.duration });
      }).observe({ type: 'longtask', buffered: false });
    });
    const targetsOf = (hand) => page.locator(`.grid-note-target[data-hand=${hand}]`).evaluateAll((nodes) =>
      nodes.map((node) => ({ frame: node.dataset.onsetFrame, row: node.dataset.row })));
    const pool = { right: await targetsOf('right'), left: await targetsOf('left') };
    const pick = (hand, i) => pool[hand][Math.min(pool[hand].length - 1, 40 + i * Math.floor((pool[hand].length - 40) / (moves + 2)))];

    const moveOnce = async (from, to, note, profile = false) => {
      const selector = `.grid-note-target[data-note-key="${from}:${note.frame}:${note.row}"]`;
      const target = page.locator(selector).first();
      // In the middle of the window: the floating toolbar covers the bottom right corner.
      await target.evaluate((node) => node.scrollIntoView({ block: 'center', inline: 'center' }));
      await page.waitForTimeout(200);
      const box = await target.boundingBox();
      await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
      const button = page.getByRole('button', { name: to === 'left' ? 'Left' : 'Right', exact: true });
      await button.waitFor();
      await page.waitForTimeout(200);
      // Armed in the page, so every time is read on the page's own clock.
      await page.evaluate(({ key }) => {
        performance.clearResourceTimings();
        window.__move = { key, pressed: null, drawn: null, painted: null, redraws: [] };
        // The sheet's full redraw starts by emptying its container: count them, with their times.
        if (!window.__patched) {
          window.__patched = true;
          const original = Element.prototype.replaceChildren;
          Element.prototype.replaceChildren = function replaceChildren(...nodes) {
            if (nodes.length === 0 && window.__move) {
              window.__move.redraws.push(performance.now());
              if (window.__debugRedraws) {
                const stack = (new Error().stack ?? '').split('\n').slice(2, 7).map((line) => line.trim().replace(/\(?https?:\/\/[^/]+\//, '').replace(/\?[^:]*/, '')).join(' < ');
                window.__debugRedraws.push(`${(performance.now() - (window.__move.pressed ?? 0)).toFixed(0)} ms ${this.tagName}.${this.getAttribute('class') ?? ''} ${stack}`);
              }
            }
            return original.apply(this, nodes);
          };
        }
        const watch = new MutationObserver(() => {
          if (window.__move.drawn !== null) return;
          if (!document.querySelector(`.grid-note-target[data-note-key="${key}"]`)) return;
          window.__move.drawn = performance.now();
          watch.disconnect();
          requestAnimationFrame(() => setTimeout(() => { window.__move.painted = performance.now(); }, 0));
        });
        watch.observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ['data-note-key'] });
        document.addEventListener('pointerup', () => { window.__move.pressed = performance.now(); }, { capture: true, once: true });
      }, { key: `${to}:${note.frame}:${note.row}` });
      const cdp = profile ? await page.context().newCDPSession(page) : null;
      if (cdp) {
        await cdp.send('Profiler.enable');
        await cdp.send('Profiler.setSamplingInterval', { interval: 250 });
        await cdp.send('Profiler.start');
      }
      await button.click();
      await page.waitForFunction(() => window.__move.painted !== null, null, { timeout: 30000 });
      if (cdp) {
        const { profile: recorded } = await cdp.send('Profiler.stop');
        piece.profile = summarise(recorded);
        await cdp.detach();
      }
      await page.waitForTimeout(300);
      return page.evaluate(() => {
        const move = window.__move;
        const entries = performance.getEntriesByType('resource');
        const find = (part) => entries.filter((e) => e.name.includes(part) && e.startTime >= move.pressed - 5).pop();
        const hands = find('/hands');
        const score = find('/score');
        const ladder = find('/ladder-preview');
        const long = window.__long.filter((t) => t.start >= move.pressed && t.start <= move.painted);
        return {
          hands: hands ? hands.responseEnd - move.pressed : null,
          build: score ? score.responseStart - score.requestStart : null,
          transfer: score ? score.responseEnd - score.responseStart : null,
          sentKB: score ? score.encodedBodySize / 1024 : null,
          rawKB: score ? score.decodedBodySize / 1024 : null,
          ladder: ladder ? ladder.responseEnd - ladder.startTime : null,
          waitBeforeSheet: hands && score ? score.startTime - hands.responseEnd : null,
          draw: score ? move.drawn - score.responseEnd : null,
          paint: move.painted - move.drawn,
          total: move.painted - move.pressed,
          longestTask: long.length ? Math.max(...long.map((t) => t.duration)) : 0,
          redraws: move.redraws.filter((t) => t >= move.pressed).length,
          timeline: {
            handsAnswered: hands ? hands.responseEnd - move.pressed : null,
            sheetAsked: score ? score.startTime - move.pressed : null,
            sheetAnswered: score ? score.responseEnd - move.pressed : null,
            redrawsAt: move.redraws.filter((t) => t >= move.pressed).map((t) => t - move.pressed),
            drawn: move.drawn - move.pressed,
          },
        };
      });
    };

    for (let count = 0; count <= moves; count += 1) {
      const [from, to] = count % 2 === 0 ? ['right', 'left'] : ['left', 'right'];
      const timing = await moveOnce(from, to, pick(from, count), values.profile && count === 1);
      if (count === 0) {
        piece.first = timing;
        await page.screenshot({ path: path.join(values.shots, `${source.slice(0, 8)}-moved.png`) });
      } else piece.moves.push(timing);
    }
    piece.flow.afterMoves = (await status()).state;
    const parts = ['hands', 'build', 'transfer', 'draw', 'paint', 'total', 'longestTask', 'redraws', 'sentKB', 'rawKB', 'ladder', 'waitBeforeSheet'];
    piece.median = Object.fromEntries(parts.map((part) => [part, round(median(piece.moves.map((m) => m[part]).filter((v) => v !== null)))]));
    const tidy = (value) => (Array.isArray(value) ? value.map(tidy)
      : value && typeof value === 'object' ? Object.fromEntries(Object.entries(value).map(([k, v]) => [k, tidy(v)]))
        : typeof value === 'number' ? round(value) : value);
    piece.first = tidy(piece.first);
    piece.moves = tidy(piece.moves);
  } catch (caught) {
    piece.error = caught instanceof Error ? caught.message.split('\n')[0] : String(caught);
    await page.screenshot({ path: path.join(values.shots, `${source.slice(0, 8)}-failed.png`) }).catch(() => {});
  } finally {
    await page.close();
    rmSync(path.join(dataDir, copy), { recursive: true, force: true });
  }
  report.pieces.push(piece);
  console.log(JSON.stringify({ alias: piece.alias, notes: piece.notes, durationS: piece.durationS, flow: piece.flow, first: piece.first, median: piece.median, profile: piece.profile, error: piece.error }, null, 1));
}
await browser.close();

if (values.out) writeFileSync(values.out, `${JSON.stringify(report, null, 2)}\n`);
console.log(problems.length ? `\nProblems:\n${problems.join('\n')}` : '\nNo console error, no failed request.');
process.exit(report.pieces.some((p) => p.error) ? 1 : 0);
