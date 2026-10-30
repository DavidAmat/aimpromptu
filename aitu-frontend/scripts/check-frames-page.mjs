/**
 * The sheet page's header, zoom, floating toolbox and cursor in the browser (implementation 04, Phase 1).
 *
 * Without credits, on a temporary copy of a version of My library that the AI enhanced (7 Years by default; the copy
 * is deleted at the end, the library is only read):
 * - the AI symbol next to the title (its tooltip **Enhanced with AI**), no green badge;
 * - the header has the floating toolbox's buttons, and stays at the top of the window while the sheet scrolls;
 * - the floating toolbox hidden leaves a button where its hide button was, which brings it back; the header's own
 *   button hides and shows it too, and a hidden floating toolbox stays hidden after a reload;
 * - ⌘ and the wheel (and Control and the wheel: a trackpad pinch) over the sheet zoom it: the drawing scales at
 *   once, one drawing is asked for at the pause of the wheel, the sheet has more lines, the line under the pointer
 *   stays under it, and the browser itself does not zoom;
 * - the cursor shows `grab` under the pointer and `grabbing` while it is dragged, follows the pointer to another
 *   line, and the recording moves there when it is let go, playing on if it played; the drag picks no note; near
 *   the window's bottom edge the page scrolls;
 * - the frame marks (implementation 04-3, Phase 2b): a grey dashed line with its number and time on every 100 frames, also
 *   after the zoom and on the printed pages; a stretch marked in the strip names its first and last frames in the
 *   range toolbox's two fields, and frames typed there mark that stretch; a decoration note lights at its own onset,
 *   not with the note before it.
 *
 *     npm run check:frames-page -- --out /tmp/frames-page
 */

import { mkdirSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { parseArgs } from 'node:util';
import { chromium } from 'playwright';
import { markStretch, sheetNow, waitForFrames, watchSheets } from './frames-page.mjs';
import { signIn, useSession } from './session.mjs';

const { values } = parseArgs({
  options: {
    base: { type: 'string', default: 'http://localhost:5173' },
    out: { type: 'string', default: path.join(os.tmpdir(), 'check-frames-page') },
    version: { type: 'string', default: '1a16a836-62b9-483b-af46-d89d0ab1b2d8' },
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
const post = async (url, body) => {
  const answer = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body ?? {}) });
  if (!answer.ok) throw new Error(`POST ${url}: ${answer.status} ${await answer.text()}`);
  return answer.json();
};

const browser = await chromium.launch({ args: ['--autoplay-policy=no-user-gesture-required'] });
useSession(browser);
const problems = [];
const shot = (page, name) => page.screenshot({ path: path.join(values.out, `${name}.png`) });

/** The sheet on the screen: its svg box and pixels per staff space. */
async function screenOf(page, sheet) {
  const box = await page.locator('[data-frames-sheet] svg').first().boundingBox();
  return { box, scale: box.width / sheet.width };
}
/** The cursor's time and line (by its y on the screen, against the systems). */
async function cursorNow(page) {
  return Number(await page.locator('[data-frames-cursor]').getAttribute('data-ms'));
}
const rootCursor = (page) => page.locator('[data-frames-sheet]').evaluate((el) => getComputedStyle(el).cursor);
const scrollY = (page) => page.evaluate(() => window.scrollY);

const made = [];
try {
  const copy = await post(`${api}/projects/${values.version}/duplicate`, {});
  made.push(copy.id);
  const part = copy.parts?.[0] ?? copy.id;
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  page.on('console', (m) => { if (m.type() === 'error' && !/status of 404/.test(m.text())) problems.push(`console: ${m.text()}`); });
  page.on('pageerror', (e) => problems.push(`page error: ${e.message}`));
  watchSheets(page);
  const asked = [];
  page.on('request', (r) => {
    const found = /\/api\/sheet\/[0-9a-f-]+\?(?:[^#]*&)?width=(\d+)/.exec(r.url());
    if (found && r.method() === 'GET') asked.push(Number(found[1]));
  });
  await page.goto(`${base}/projects/${part}/sheet`);
  await waitForFrames(page);

  // ------------------------------------------------------------------ the AI symbol and the header
  check('no green badge', (await page.locator('[data-enhanced-badge]').count()) === 0);
  const mark = page.locator('[data-sheet-header] [data-ai-mark] [data-enhanced]');
  check('the AI symbol is next to the title', (await mark.count()) === 1);
  await mark.hover();
  const tip = page.getByRole('tooltip');
  await tip.first().waitFor({ timeout: 3000 }).catch(() => undefined);
  check('its tooltip says Enhanced with AI', (await tip.first().innerText().catch(() => '')).trim() === 'Enhanced with AI');
  await page.mouse.move(700, 600);
  const names = ['sheet-play', 'sheet-record', 'sheet-paste', 'sheet-print', 'sheet-undo', 'sheet-redo', 'sheet-toolbox', 'enhance-with-ai'];
  const inBoth = [];
  for (const name of names) {
    if ((await page.getByTestId(name).count()) === 1 && (await page.getByTestId(`header-${name}`).count()) === 1) inBoth.push(name);
  }
  check('the header has the floating toolbox\'s buttons', inBoth.length === names.length, `${inBoth.length} of ${names.length}`);
  check('and its ⋯', (await page.locator('[data-sheet-header] [aria-label="More sheet actions"]').count()) === 1);
  await shot(page, '01-header');

  await page.getByTestId('header-sheet-toolbox').click();
  await page.locator('[data-frames-sheet-toolbox]').waitFor({ timeout: 5000 }).catch(() => undefined);
  check('the header\'s Sheet toolbox opens it', (await page.locator('[data-frames-sheet-toolbox]').count()) === 1);
  await page.getByTestId('header-sheet-toolbox').click();
  await page.waitForTimeout(300);

  await page.getByTestId('header-sheet-play').click();
  await page.waitForTimeout(1500);
  const played = await cursorNow(page);
  await page.getByTestId('header-sheet-play').click();
  check('the header\'s Play plays', played > 500, `${played} ms`);

  await page.evaluate(() => window.scrollTo(0, 1600));
  await page.waitForTimeout(300);
  const header = await page.locator('[data-sheet-header]').boundingBox();
  check('the header stays at the top while the sheet scrolls', header && Math.abs(header.y) <= 1, header ? `y ${header.y}` : 'none');
  await shot(page, '02-header-scrolled');
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(300);

  // ------------------------------------------------------------------ hiding and showing the floating toolbox
  const hide = page.locator('[data-floating-hide]');
  const hideBox = await hide.boundingBox();
  await hide.click();
  await page.waitForTimeout(300);
  const show = page.locator('[data-floating-show]');
  check('hidden, the floating toolbox leaves a button', (await show.count()) === 1 && (await page.getByTestId('sheet-undo').count()) === 0);
  const showBox = await show.boundingBox();
  const off = showBox ? Math.hypot(showBox.x + showBox.width / 2 - (hideBox.x + hideBox.width / 2), showBox.y + showBox.height / 2 - (hideBox.y + hideBox.height / 2)) : Infinity;
  check('the button is where the hide button was', off <= 30, `${Math.round(off)} px away`);
  await shot(page, '03-floating-hidden');
  await show.click();
  await page.waitForTimeout(300);
  check('it brings the floating toolbox back', (await page.getByTestId('sheet-undo').count()) === 1);
  await hide.click();
  await page.waitForTimeout(300);
  await page.getByTestId('header-floating-toggle').click();
  await page.waitForTimeout(300);
  check('the header\'s button brings it back too', (await page.getByTestId('sheet-undo').count()) === 1);
  await page.getByTestId('header-floating-toggle').click();
  await page.reload();
  await waitForFrames(page);
  check('a hidden floating toolbox stays hidden after a reload', (await page.getByTestId('sheet-undo').count()) === 0 && (await show.count()) === 1);
  const corner = (b) => b && b.x + b.width >= 1440 - 40 && b.y + b.height >= 900 - 40;
  check('its button is in the bottom right corner', corner(await show.boundingBox()));
  await page.getByTestId('header-floating-toggle').click();
  await page.waitForTimeout(300);
  check('shown, the floating toolbox is born in the bottom right corner', corner(await page.locator('[data-floating-hide]').locator('xpath=ancestor::div[contains(@class,"MuiPaper")][1]').boundingBox()));

  // ------------------------------------------------------------------ ⌘ and the wheel
  const zoomOnce = async (modifier, deltaY, label) => {
    const sheet = await sheetNow(api, part);
    // The pointer on the middle of the third line, brought to the middle of the window.
    const system = sheet.systems[2];
    let { box, scale } = await screenOf(page, sheet);
    await page.evaluate((y) => window.scrollBy(0, y - 450), box.y + ((system.top + system.bottom) / 2) * scale);
    await page.waitForTimeout(300);
    ({ box, scale } = await screenOf(page, sheet));
    const target = { x: box.x + box.width * 0.5, y: box.y + ((system.top + system.bottom) / 2) * scale };
    await page.mouse.move(target.x, target.y);
    const pixelRatio = await page.evaluate(() => window.visualViewport?.scale ?? 1);
    const before = asked.length;
    await page.keyboard.down(modifier);
    for (let i = 0; i < 4; i += 1) {
      await page.mouse.wheel(0, deltaY);
      await page.waitForTimeout(40);
    }
    const scaled = await page.locator('[data-wheel-zoom]').count();
    await page.keyboard.up(modifier);
    await page.waitForTimeout(1500);
    const after = await sheetNow(api, part);
    const requests = asked.slice(before);
    const now = await screenOf(page, after);
    // The line under the pointer now: the one whose time was under it.
    const ms = sheet.columns.filter((c) => c.system === 2).map((c) => c.ms);
    const middle = ms[Math.floor(ms.length / 2)];
    const column = after.columns.reduce((best, c) => (Math.abs(c.ms - middle) < Math.abs(best.ms - middle) ? c : best));
    const line = after.systems[column.system];
    const lineY = now.box.y + ((line.top + line.bottom) / 2) * now.scale;
    const viewport = await page.evaluate(() => window.visualViewport?.scale ?? 1);
    check(`${label}: the drawing scales at once`, scaled === 1);
    check(`${label}: one drawing asked for at the pause`, requests.length === 1, requests.join(', '));
    check(`${label}: the sheet is laid out again`, after.systems.length !== sheet.systems.length, `${sheet.systems.length} -> ${after.systems.length} lines`);
    // Unless the page would have to scroll above its top.
    const top = (await scrollY(page)) === 0 && lineY < target.y;
    check(`${label}: the line under the pointer stays near it`, top || Math.abs(lineY - target.y) <= ((line.bottom - line.top) / 2 + 2) * now.scale,
      `${Math.round(lineY - target.y)} px${top ? ', the page at its top' : ''}`);
    check(`${label}: the browser itself does not zoom`, viewport === pixelRatio);
    return after;
  };
  await zoomOnce('Meta', -120, '⌘ and the wheel');
  await shot(page, '04-zoomed-in');
  const stored = await page.evaluate(() => Number(window.localStorage.getItem('aitu.framesSheet.zoom')));
  check('the zoom is kept in this browser', stored > 1, `${stored}`);
  await zoomOnce('Control', 120, 'a trackpad pinch (Control and the wheel)');

  // ------------------------------------------------------------------ the frame marks (04-3, Phase 2b)
  {
    const sheet = await sheetNow(api, part);
    const read = (selector) => page.locator(`[data-frames-sheet] svg ${selector}`).evaluateAll((all) =>
      all.map((el) => ({ frame: Number(el.getAttribute('data-frame')), fill: el.getAttribute('fill'), stroke: el.getAttribute('stroke'), dash: el.getAttribute('stroke-dasharray') })));
    const lines = await read('.frame-line');
    const numbers = await read('.frame-number');
    const last = sheet.columns[sheet.columns.length - 1].frame;
    const wanted = [];
    // From the first column on: nothing is drawn before the first note.
    for (let f = Math.ceil(Math.max(1, sheet.columns[0].frame) / 100) * 100; f <= last; f += 100) wanted.push(f);
    check('a dashed line on every 100 frames', JSON.stringify(lines.map((one) => one.frame)) === JSON.stringify(wanted) && lines.every((one) => one.dash), `${lines.length} lines, ${wanted.length} wanted`);
    check('each with its frame number', numbers.length >= wanted.length - 2 && numbers.every((one) => wanted.includes(one.frame)), `${numbers.length} numbers`);
    const times = await page.locator('[data-frames-sheet] svg .frame-time').evaluateAll((all) => all.map((el) => Number(el.getAttribute('data-frame'))));
    check('and the time over each number', JSON.stringify(times) === JSON.stringify(numbers.map((one) => one.frame)), `${times.length} times`);
    check('lines and numbers are grey', lines.every((one) => one.stroke === '#b4b4b4') && numbers.every((one) => one.fill === '#8a8a8a'));
    const printed = await fetch(`${api}/sheet/${part}/pages?width=130&height=180`).then((r) => r.json());
    check('the printed pages have them too', printed.pages.length > 0 && printed.pages.every((one) => one.svg.includes('class="frame-line"')));
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.waitForTimeout(300);
    const { box, scale } = await screenOf(page, sheet);
    const first = sheet.systems[0];
    await page.screenshot({ path: path.join(values.out, '07-frame-marks.png'), clip: { x: box.x, y: box.y + (first.top - 1) * scale, width: box.width, height: (first.bottom - first.top + 3) * scale } });

    // The range toolbox: the frames of the stretch in two fields; other numbers mark another stretch.
    const stretch = await markStretch(page, api, { from: 0.2, to: 0.6 });
    const inside = sheet.columns.filter((c) => c.frame >= stretch.start && c.frame < stretch.end).map((c) => c.frame);
    const fromField = page.locator('[data-frames-range-toolbox] [data-range-from]');
    const toField = page.locator('[data-frames-range-toolbox] [data-range-to]');
    check('the range toolbox names the first and last frames', (await fromField.inputValue()) === String(inside[0]) && (await toField.inputValue()) === String(inside[inside.length - 1]),
      `${await fromField.inputValue()} to ${await toField.inputValue()}`);
    await shot(page, '08-range-frames');
    const a = sheet.columns[Math.floor(sheet.columns.length * 0.4)];
    const bIndex = Math.floor(sheet.columns.length * 0.45);
    const b = sheet.columns[bIndex];
    await fromField.fill(String(a.frame + 1)); // between two columns: from the next column on
    await toField.fill(String(b.frame));
    await toField.press('Enter');
    await page.waitForTimeout(800);
    const startNow = Number(await page.locator('[data-range-band]').first().getAttribute('data-start'));
    const ends = await page.locator('[data-range-band]').evaluateAll((all) => all.map((el) => Number(el.getAttribute('data-end'))).sort((x, y) => x - y));
    const afterA = sheet.columns.find((c) => c.frame > a.frame).frame;
    const nextB = sheet.columns[bIndex + 1]?.frame ?? b.frame + 1;
    check('typed frames mark that stretch', startNow === afterA && ends[ends.length - 1] === nextB, `${startNow}-${ends[ends.length - 1]}, wanted ${afterA}-${nextB}`);
    check('and the fields show its columns', (await fromField.inputValue()) === String(afterA) && (await toField.inputValue()) === String(b.frame));
    const band = await page.locator('[data-range-band]').first().boundingBox();
    check('the stretch is brought into view', band && band.y > 0 && band.y < 900, band ? `y ${Math.round(band.y)}` : 'none');
    await shot(page, '09-range-typed');
    await page.keyboard.press('Escape');
    await page.mouse.click(5, 450);
    await page.keyboard.press('Escape');
    await page.waitForTimeout(300);

    // A decoration note lights at its own onset, not with the note before it.
    const columnFrames = new Set(sheet.columns.map((c) => c.frame));
    const grace = sheet.columns.map((c, k) => {
      const next = sheet.columns[k + 1];
      const later = sheet.notes.map((n) => Number(n.ref.split(':')[0])).filter((f) => next && f > c.frame + 1 && f < next.frame && !columnFrames.has(f));
      return later.length && next.system === c.system ? { c, next, g: Math.min(...later) } : null;
    }).find(Boolean);
    if (!grace) {
      check('a decoration note lights at its own onset (no decoration note in this sheet: not checked)', true);
    } else {
      const { c, next, g } = grace;
      const xAt = (ms) => c.x + ((next.x - c.x) * (ms - c.ms)) / (next.ms - c.ms);
      const s = sheet.systems[c.system];
      let { box: sb, scale: sc } = await screenOf(page, sheet);
      await page.evaluate((y) => window.scrollBy(0, y - 450), sb.y + s.staff_top * sc);
      await page.waitForTimeout(300);
      ({ box: sb, scale: sc } = await screenOf(page, sheet));
      const y = sb.y + ((s.staff_top + 4 + s.staff_bottom - 4) / 2) * sc;
      const graceLit = () => page.locator(`[data-frames-sheet] [data-note^="${g}:"][data-lit], [data-frames-sheet] [data-note~="${g}:"][data-lit]`).count();
      await page.mouse.click(sb.x + xAt((c.ms + g * 40) / 2) * sc, y);
      await page.waitForTimeout(500);
      const before = await graceLit();
      await page.mouse.click(sb.x + xAt((g * 40 + next.ms) / 2) * sc, y);
      await page.waitForTimeout(500);
      const after = await graceLit();
      check('a decoration note is not lit while the note before it sounds', before === 0, `frame ${g}, after column ${c.frame}`);
      check('it lights at its own onset', after > 0);
    }
  }

  // ------------------------------------------------------------------ dragging the cursor
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(300);
  const sheet = await sheetNow(api, part);
  const { box, scale } = await screenOf(page, sheet);
  const at = (system, share) => {
    const s = sheet.systems[system];
    const onLine = sheet.columns.filter((c) => c.system === system);
    const c = onLine[Math.floor(share * (onLine.length - 1))];
    // Between the two staves, clear of the noteheads.
    return { x: box.x + c.x * scale, y: box.y + ((s.staff_top + 4 + s.staff_bottom - 4) / 2) * scale, column: c };
  };
  // A click puts the cursor on the first line.
  const start = at(0, 0.3);
  await page.mouse.click(start.x, start.y);
  await page.waitForTimeout(400);
  const cursor = await page.locator('[data-frames-cursor]').boundingBox();
  const grip = { x: cursor.x + cursor.width / 2, y: start.y };
  await page.mouse.move(grip.x + 40, grip.y);
  await page.mouse.move(grip.x, grip.y, { steps: 3 });
  check('the pointer shows grab over the cursor', (await rootCursor(page)) === 'grab', await rootCursor(page));
  const picked = await page.locator('[data-selected]').count();
  await page.mouse.down();
  const end = at(1, 0.6);
  await page.mouse.move(end.x, end.y, { steps: 12 });
  check('grabbing while it is dragged', (await rootCursor(page)) === 'grabbing', await rootCursor(page));
  const dragging = await page.locator('[data-frames-cursor][data-dragging]').count();
  const line = await page.locator('[data-frames-cursor]').boundingBox();
  check('the cursor follows the pointer to the next line', dragging === 1 && Math.abs(line.x + line.width / 2 - end.x) <= 4 && line.y > cursor.y + 20,
    `x ${Math.round(line.x + line.width / 2 - end.x)} px off`);
  await shot(page, '05-cursor-dragged');
  await page.mouse.up();
  await page.waitForTimeout(400);
  const dropped = await cursorNow(page);
  check('the recording moves there on release', Math.abs(dropped - end.column.ms) <= 200, `${dropped} ms, aimed at ${end.column.ms}`);
  check('the drag picks no note and draws no box', (await page.locator('[data-selected]').count()) === picked && (await page.locator('[data-pick-box]').count()) === 0);

  // While it plays: it plays on from where it is let go.
  await page.keyboard.press('Space');
  await page.waitForTimeout(600);
  let now = await page.locator('[data-frames-cursor]').boundingBox();
  const target = at(2, 0.5);
  await page.mouse.move(now.x + now.width / 2, target.y - (at(2, 0.5).y - at(1, 0.5).y));
  await page.mouse.down();
  await page.mouse.move(target.x, target.y, { steps: 10 });
  await page.mouse.up();
  await page.waitForTimeout(800);
  const playedOn = await cursorNow(page);
  await page.keyboard.press('Space');
  check('while it plays, it plays on from the drop', playedOn > target.column.ms + 300 && playedOn < target.column.ms + 3000, `${playedOn} ms, dropped at ${target.column.ms}`);

  // Near the bottom edge the page scrolls.
  now = await page.locator('[data-frames-cursor]').boundingBox();
  await page.evaluate((y) => window.scrollBy(0, y - 400), now.y + now.height / 2);
  await page.waitForTimeout(300);
  now = await page.locator('[data-frames-cursor]').boundingBox();
  const y0 = await scrollY(page);
  await page.mouse.move(now.x + now.width / 2, now.y + now.height / 2);
  await page.mouse.down();
  await page.mouse.move(now.x + now.width / 2 + 30, 890, { steps: 10 });
  await page.waitForTimeout(1200);
  const y1 = await scrollY(page);
  await page.mouse.up();
  await page.waitForTimeout(400);
  check('near the bottom edge the page scrolls', y1 > y0 + 100, `${y0} -> ${y1}`);
  await shot(page, '06-after-edge');
  await page.close();
} finally {
  for (const id of made) await fetch(`${api}/projects/${id}`, { method: 'DELETE' }).catch(() => undefined);
  await browser.close();
}

for (const problem of problems) console.log(`problem: ${problem}`);
console.log(failures.length === 0 && problems.length === 0 ? 'all passed' : `${failures.length} failed, ${problems.length} problems`);
process.exit(failures.length === 0 && problems.length === 0 ? 0 : 1);
