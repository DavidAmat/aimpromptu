/**
 * Editing the new sheet in the browser (implementation 03, Phase 6): picking notes, moving them to the other hand,
 * undo and redo, and the time of one edit.
 *
 * Without credits, on a temporary copy of a version of My library that Sonnet wrote (7 Years by default; the copy
 * is deleted at the end, the library is only read):
 * - a click on a notehead picks it (`[data-selected]`) and opens the note toolbox (`[data-frames-note-toolbox]`)
 *   titled with its printed name; ⌘ (Control) adds a note; a box dragged across the staves picks every notehead in it;
 * - **Left** moves the picked note to the left hand: the sheet comes back drawn again, and the backend says the
 *   note is in the left hand now; the sheet is still **Enhanced with AI**;
 * - Control-Z takes it back, Control-Shift-Z puts it again, and so do the floating bar's arrows, whose tooltips
 *   name the step; after a reload the step is still there (the backend keeps it);
 * - `--edits N` hand moves in a row, timed from the click to the new drawing on the page: the numbers decide where
 *   the engine runs (plan Phase 6, task 4).
 *
 *     npm run check:frames-edit -- --out /tmp/frames-edit [--edits 10]
 */

import { mkdirSync, writeFileSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { parseArgs } from 'node:util';
import { chromium } from 'playwright';
import { signIn, useSession } from './session.mjs';

const { values } = parseArgs({
  options: {
    base: { type: 'string', default: 'http://localhost:5173' },
    out: { type: 'string', default: path.join(os.tmpdir(), 'check-frames-edit') },
    version: { type: 'string', default: '1a16a836-62b9-483b-af46-d89d0ab1b2d8' },
    edits: { type: 'string', default: '10' },
  },
});
const base = values.base;
const api = `${base}/api`;
mkdirSync(values.out, { recursive: true });
await signIn(base);

const failures = [];
const check = (what, ok, detail = '') => {
  console.log(`${ok ? 'ok  ' : 'FAIL'}  ${what}${detail ? `  (${detail})` : ''}`);
  if (!ok) failures.push(what);
};
const json = async (url, init) => {
  const answer = await fetch(url, init);
  if (!answer.ok) throw new Error(`${init?.method ?? 'GET'} ${url}: ${answer.status} ${await answer.text()}`);
  return answer.json();
};
const post = (url, body) =>
  json(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body ?? {}) });
const median = (xs) => [...xs].sort((a, b) => a - b)[Math.floor(xs.length / 2)];

const browser = await chromium.launch();
useSession(browser);
const problems = [];
async function open(route) {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 });
  page.on('console', (m) => { if (m.type() === 'error' && !/status of 404/.test(m.text())) problems.push(`console: ${m.text()}`); });
  page.on('pageerror', (e) => problems.push(`page error: ${e.message}`));
  page.on('response', (r) => { if (r.status() >= 400 && !(r.status() === 404 && /\/rhythm$/.test(r.url()))) problems.push(`${r.status()} ${r.url()}`); });
  await page.goto(new URL(route, base).toString());
  await page.locator('[data-frames-sheet] [data-note]').first().waitFor({ timeout: 120000 });
  await page.waitForTimeout(500);
  return page;
}
const shot = (page, name) => page.screenshot({ path: path.join(values.out, `${name}.png`) });
/** A zoomed picture of the line that holds `ref`, with the toolbox closed. */
async function lineShot(page, ref, name) {
  await page.keyboard.press('Escape');
  await page.waitForTimeout(250);
  const head = await page.locator(`[data-frames-sheet] [data-note~="${ref}"]`).first().boundingBox();
  const sheet = await page.locator('[data-frames-sheet]').boundingBox();
  const clip = { x: Math.max(sheet.x, head.x - 420), y: head.y - 150, width: 560, height: 300 };
  await page.screenshot({ path: path.join(values.out, `${name}.png`), clip });
}
const toolbox = (page) => page.locator('[data-frames-note-toolbox]');
const handButton = (page, hand) => toolbox(page).locator(`button[aria-label="${hand === 'left' ? 'Left' : 'Right'}"]`);
/** Click the centre of a notehead (the first one naming `ref`). */
async function clickHead(page, ref, modifiers = []) {
  const head = page.locator(`[data-frames-sheet] [data-note~="${ref}"]`).first();
  await head.scrollIntoViewIfNeeded();
  const box = await head.boundingBox();
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  for (const key of modifiers) await page.keyboard.down(key);
  await page.mouse.down();
  await page.mouse.up();
  for (const key of modifiers) await page.keyboard.up(key);
}
/** The hand the backend gives a ref now. */
const handOf = async (part, ref) => (await json(`${api}/sheet/${part}?width=130`)).notes.find((n) => n.ref === ref)?.hand;

const made = [];
try {
  const copy = await post(`${api}/projects/${values.version}/duplicate`, {});
  made.push(copy.id);
  const part = copy.parts?.[0] ?? copy.id;
  const first = await json(`${api}/sheet/${part}?width=130`);
  check('a copy of a sheet the AI wrote can be edited', first.editable === true && first.llm.enhanced === true);
  // A right-hand note of the melody on the second line of the page, and the note after it.
  const right = first.notes.filter((n) => n.hand === 'right');
  const column = first.columns.find((c) => c.system === 1);
  const target = right.find((n) => Number(n.ref.split(':')[0]) >= column.frame) ?? right[0];
  const next = right[right.indexOf(target) + 1];

  const page = await open(`/projects/${part}/sheet`);
  await clickHead(page, target.ref);
  await toolbox(page).waitFor();
  const title = await page.locator('[data-frames-note-toolbox]').locator('xpath=ancestor::*[contains(@class,"MuiPaper")][1]').innerText();
  check('a click on a notehead picks it', (await page.locator('[data-selected]').count()) >= 1);
  check('and opens the note toolbox with its name', /^(Do|Re|Mi|Fa|Sol|La|Si)/.test(title.trim()), title.split('\n')[0]);
  check('the toolbox says it is in the right hand', (await handButton(page, 'right').getAttribute('aria-pressed')) === 'true');
  await clickHead(page, next.ref, ['Control']);
  await page.waitForTimeout(200);
  check('Control-click adds a note', (await page.locator('[data-selected]').count()) >= 2, `${await page.locator('[data-selected]').count()} picked`);
  await clickHead(page, target.ref);
  await page.waitForTimeout(200);
  await shot(page, '01-picked');
  await lineShot(page, target.ref, '01-line-before');
  await clickHead(page, target.ref);
  await toolbox(page).waitFor();

  // Move it to the left hand.
  const before = await page.locator('[data-frames-sheet] svg').first().innerHTML();
  await handButton(page, 'left').click();
  await page.waitForFunction(
    (svg) => document.querySelector('[data-frames-sheet] svg')?.innerHTML !== svg,
    before,
    { timeout: 30000 },
  );
  await page.waitForTimeout(300);
  check('Left moves the note to the left hand', (await handOf(part, target.ref)) === 'left');
  check('the toolbox follows it', (await handButton(page, 'left').getAttribute('aria-pressed')) === 'true');
  check('the sheet stays Enhanced with AI', (await page.locator('[data-enhanced-badge]').count()) === 1);
  const undoTitle = await page.getByTestId('sheet-undo').getAttribute('aria-label');
  check('Undo names the step', /Move a note to the left hand/.test(undoTitle ?? ''), undoTitle);
  await shot(page, '02-moved');
  await lineShot(page, target.ref, '02-line-after');

  // Undo and redo, by the keys.
  await page.keyboard.press('Control+z');
  await page.waitForFunction(() => document.querySelector('[data-testid="sheet-redo"]:not([disabled])') !== null);
  check('Control-Z takes it back', (await handOf(part, target.ref)) === 'right');
  // Redo is also disabled while an edit is on its way: wait for the answer, not for the button.
  await Promise.all([
    page.waitForResponse((r) => /\/sheet\/[^/]+\/redo/.test(r.url())),
    page.keyboard.press('Control+Shift+z'),
  ]);
  check('Control-Shift-Z puts it again', (await handOf(part, target.ref)) === 'left');

  // The step is kept by the backend: still there after a reload, and the floating bar's arrow takes it back.
  await page.reload();
  await page.locator('[data-frames-sheet] [data-note]').first().waitFor();
  await page.getByTestId('sheet-undo').click();
  await page.waitForFunction(() => document.querySelector('[data-testid="sheet-redo"]:not([disabled])') !== null);
  check('after a reload, Undo still takes it back', (await handOf(part, target.ref)) === 'right');

  // A box dragged across the first line picks every notehead in it.
  const system = first.systems[0];
  const svg = await page.locator('[data-frames-sheet] svg').first().boundingBox();
  const scale = svg.width / first.width;
  await page.keyboard.press('Escape');
  // Inside the upper staff: above it is the strip that marks a stretch (Phase 7).
  await page.mouse.move(svg.x + (system.left + 4) * scale, svg.y + (system.staff_top + 0.3) * scale);
  await page.mouse.down();
  await page.mouse.move(svg.x + (system.left + 30) * scale, svg.y + (system.bottom + 1) * scale, { steps: 6 });
  await page.mouse.up();
  await page.waitForTimeout(300);
  const boxed = await page.locator('[data-selected]').count();
  const boxTitle = (await page.locator('[data-frames-note-toolbox]').locator('xpath=ancestor::*[contains(@class,"MuiPaper")][1]').innerText()).split('\n')[0];
  check('a box dragged across the staves picks the notes in it', boxed > 3 && /notes$/.test(boxTitle), `${boxed} heads, "${boxTitle}"`);
  await shot(page, '03-box');
  await page.keyboard.press('Escape');

  // The time of one edit: click Left or Right, until the new drawing is on the page; split into the backend (the
  // request sent to its first byte back), the transfer of the answer, and the page (the rest: the click, reading
  // the answer, putting the new SVG in and painting it).
  const times = [];
  const parts = [];
  await clickHead(page, target.ref);
  await toolbox(page).waitFor();
  for (let i = 0; i < Number(values.edits); i += 1) {
    const to = i % 2 === 0 ? 'left' : 'right';
    const svgNow = await page.locator('[data-frames-sheet] svg').first().innerHTML();
    const begin = await page.evaluate(() => performance.now());
    const [response] = await Promise.all([
      page.waitForResponse((r) => /\/sheet\/[^/]+\/hands/.test(r.url())),
      handButton(page, to).click(),
    ]);
    const end = await page.evaluate(
      (svg) =>
        new Promise((resolve) => {
          const tick = () => {
            const now = document.querySelector('[data-frames-sheet] svg')?.innerHTML;
            if (now && now !== svg) requestAnimationFrame(() => resolve(performance.now()));
            else requestAnimationFrame(tick);
          };
          tick();
        }),
      svgNow,
    );
    const timing = response.request().timing();
    const total = Math.round(end - begin);
    const backend = Math.round(timing.responseStart - timing.requestStart);
    const transfer = Math.round(timing.responseEnd - timing.responseStart);
    const body = (await response.body()).length;
    times.push(total);
    parts.push({ total, backend, transfer, page: total - backend - transfer, kb: Math.round(body / 1024) });
  }
  const mid = (key) => median(parts.map((p) => p[key]));
  check(
    `${times.length} hand moves timed`,
    times.length === Number(values.edits),
    `median ${median(times)} ms (${Math.min(...times)} to ${Math.max(...times)}): backend ${mid('backend')}, transfer ${mid('transfer')}, page ${mid('page')} ms; answer ${mid('kb')} KB`,
  );
  writeFileSync(path.join(values.out, 'times.json'), JSON.stringify(parts, null, 1));
  await page.close();
} finally {
  for (const id of made) await fetch(`${api}/projects/${id}`, { method: 'DELETE' }).catch(() => undefined);
  await browser.close();
}

for (const problem of problems) console.log(`problem: ${problem}`);
console.log(failures.length === 0 && problems.length === 0 ? 'all passed' : `${failures.length} failed, ${problems.length} problems`);
process.exit(failures.length === 0 && problems.length === 0 ? 0 : 1);
