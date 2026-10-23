/**
 * Screenshots of passages of today's sheet (vexflow-v2) for the Phase 3 gallery of implementation 03
 * (`aitu-backend/scripts/frames_gallery.py` writes the cases: a library version and its columns [first, end)).
 *
 * Each case opens the Sheet step of a version of My library and only reads it (no click). vexflow-v2 draws the
 * whole part as one SVG and marks each onset group with `data-onset-frame`; the script takes the groups of the
 * passage line by line (one `.grid-music-layer` per line of the sheet), and clips each line from the first to the
 * last group of the passage, over the height of its two staves. Lines are scaled to 10 px per staff space (the
 * new engine's drawing size) and stacked into one PNG per case, at twice that resolution.
 *
 *     node scripts/vexflow-passages.mjs --cases DIR/cases.json --out DIR/vexflow
 */

import { mkdirSync, readFileSync } from 'node:fs';
import { parseArgs } from 'node:util';
import { chromium } from 'playwright';
import { signIn, useSession } from './session.mjs';

const { values } = parseArgs({
  options: {
    cases: { type: 'string' },
    out: { type: 'string' },
    base: { type: 'string', default: 'http://localhost:5173' },
    only: { type: 'string', default: '' },
  },
});
const cases = JSON.parse(readFileSync(values.cases, 'utf8'));
const only = new Set(values.only.split(',').filter(Boolean).map(Number));
mkdirSync(values.out, { recursive: true });
await signIn(values.base);
const browser = await chromium.launch();
useSession(browser);

const SCALE = 2;
const pages = new Map();
async function sheetOf(part) {
  if (pages.has(part)) return pages.get(part);
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: SCALE });
  await page.addInitScript(() => window.localStorage.setItem('mui-mode', 'light'));
  await page.goto(`${values.base}/projects/${part}/sheet`);
  await page.locator('.grid-note-target').first().waitFor({ timeout: 90000 });
  await page.waitForTimeout(1500);
  pages.set(part, page);
  return page;
}

for (const c of cases) {
  if (only.size && !only.has(c.case)) continue;
  const page = await sheetOf(c.part);
  // every onset group with its box in page coordinates, and the line it belongs to (groups whose tops are close)
  // the lines (music layers) that hold onset groups of the passage
  const layers = await page.evaluate(({ first, end }) => {
    const all = [...document.querySelectorAll('.grid-music-layer')];
    return all
      .map((layer, k) => ({ k, n: [...layer.querySelectorAll('.grid-onset-group[data-onset-frame]')]
        .filter((g) => { const f = Number(g.getAttribute('data-onset-frame')); return f >= first && f < end; }).length }))
      .filter((row) => row.n > 0)
      .map((row) => row.k);
  }, c);
  if (!layers.length) { console.log(`case ${c.case}: no onset group in f${c.first}..f${c.end - 1}`); continue; }
  const shots = [];
  for (const k of layers) {
    // the page scrolls inside a container: bring the line into view, then clip in viewport coordinates
    const l = await page.evaluate(({ k, first, end }) => {
      const layer = document.querySelectorAll('.grid-music-layer')[k];
      layer.scrollIntoView({ block: 'center' });
      const box = (e) => e.getBoundingClientRect();
      const inside = [...layer.querySelectorAll('.grid-onset-group[data-onset-frame]')]
        .filter((g) => { const f = Number(g.getAttribute('data-onset-frame')); return f >= first && f < end; })
        .map(box);
      const top = Math.min(...inside.map((g) => g.top));
      const bottom = Math.max(...inside.map((g) => g.bottom));
      // the two staves that the most onset groups of the passage cover
      const covered = (st) => { const r = box(st); const mid = (r.top + r.bottom) / 2; return inside.filter((g) => g.top < mid && g.bottom > mid).length; };
      const own = [...document.querySelectorAll('.grid-staff')]
        .filter((st) => { const r = box(st); return (r.top + r.bottom) / 2 > top && (r.top + r.bottom) / 2 < bottom; })
        .sort((x, y) => covered(y) - covered(x)).slice(0, 2);
      // the staff space: the distance between the horizontal lines of a staff
      const ys = [...new Set([...own[0].querySelectorAll('*')].map(box)
        .filter((r) => r.height < 3 && r.width > 100).map((r) => Math.round((r.top + r.bottom) * 5) / 10))].sort((x, y) => x - y);
      const steps = ys.slice(1).map((y, i) => y - ys[i]).filter((d) => d > 2).sort((x, y) => x - y);
      const space = steps[Math.floor(steps.length / 2)] || 7.5;
      const lines = own.flatMap((st) => [...st.querySelectorAll('*')].map(box).filter((r) => r.height < 3 && r.width > 100));
      return {
        space,
        x0: Math.min(...inside.map((g) => g.left)) - 24,
        x1: Math.max(...inside.map((g) => g.right)) + 16,
        y0: Math.min(...lines.map((r) => r.top)) - 5 * space,
        y1: Math.max(...lines.map((r) => r.bottom)) + 5 * space,
      };
    }, { k, first: c.first, end: c.end });
    await page.waitForTimeout(300);
    const clip = { x: Math.max(0, l.x0), y: Math.max(0, l.y0), width: Math.min(1440, l.x1) - Math.max(0, l.x0), height: Math.min(900, l.y1) - Math.max(0, l.y0) };
    // shown at 10 px per staff space, the new engine's drawing size, so that the spacing compares directly
    const zoom = 10 / l.space;
    shots.push({ data: (await page.screenshot({ clip })).toString('base64'), w: clip.width * zoom, h: clip.height * zoom });
  }
  // stack the lines of the passage into one picture
  const sheet = await browser.newPage({ deviceScaleFactor: SCALE, viewport: { width: Math.ceil(Math.max(...shots.map((s) => s.w))), height: 10 } });
  await sheet.setContent(`<body style="margin:0;background:#fff">${shots.map((s) => `<img style="display:block;width:${s.w}px;height:${s.h}px" src="data:image/png;base64,${s.data}">`).join('')}</body>`);
  await sheet.locator('img').last().waitFor();
  await sheet.screenshot({ path: `${values.out}/case-${c.case}.png`, fullPage: true });
  await sheet.close();
  console.log(`case ${c.case}: ${layers.length} line(s)`);
}
await browser.close();
