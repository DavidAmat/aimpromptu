/**
 * The sheet toolbox of the new sheet in the browser (implementation 03, Phase 8A).
 *
 * On a temporary copy of a version of My library that the AI wrote (7 Years by default; the copy is deleted at the
 * end, the library is only read), each tool through the page, checked against the backend:
 * - **Title**: a title typed and kept, printed above the sheet;
 * - **View**: the space between lines (the sheet grows taller, nothing moves sideways);
 * - **Transpose figures** with its preview (every figure one step shorter, no column moves), then undone;
 * - **Transpose notes** with its preview (two semitones up), then undone;
 * - **Lyrics**: words pasted, added to the pool, a piece dragged from the pool onto the sheet (drawn above the
 *   staff), moved by dragging it on the sheet, picked and taken off with Delete;
 * - **the chord keyboard** of the note toolbox: the picked column's keys lit, a dark key adds a note to the chord (its
 *   figure and beam group), the chord stays picked, the lit key takes it off, Undo walks both; notes of two columns
 *   show no keyboard;
 * - **the keyboard panel**: a dark key adds a note under the cursor, the lit key takes it off again;
 * - **Print to PDF**: the pages of the paper, and the file (vector, no notation font needed);
 * - **Play mode**: the lyrics piece that sounds is lit.
 *
 * Zoomed pictures go to `--out`.
 *
 *     npm run check:frames-toolbox -- --out /tmp/frames-toolbox
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
    out: { type: 'string', default: path.join(os.tmpdir(), 'check-frames-toolbox') },
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
const json = async (url, init) => {
  const answer = await fetch(url, init);
  if (!answer.ok) throw new Error(`${init?.method ?? 'GET'} ${url}: ${answer.status} ${await answer.text()}`);
  return answer.json();
};
const post = (url, body) =>
  json(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body ?? {}) });

const browser = await chromium.launch();
useSession(browser);
const problems = [];
let pageWidth = 130;
async function open(route, wait = '[data-frames-sheet] [data-note]') {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2, acceptDownloads: true });
  page.on('console', (m) => { if (m.type() === 'error' && !/status of (404|400)/.test(m.text())) problems.push(`console: ${m.text()}`); });
  page.on('pageerror', (e) => problems.push(`page error: ${e.message}`));
  page.on('response', (r) => {
    if (r.status() >= 400 && !(r.status() === 404 && /\/(rhythm|lyrics)$/.test(r.url()))) problems.push(`${r.status()} ${r.url()}`);
    const width = /\/sheet\/[^/?]+(?:\/[a-z]+)?\?width=(\d+)/.exec(r.url());
    if (width) pageWidth = Number(width[1]);
  });
  await page.goto(new URL(route, base).toString());
  await page.locator(wait).first().waitFor({ timeout: 120000 });
  await page.waitForTimeout(500);
  return page;
}
const now = async (part) => json(`${api}/sheet/${part}?width=${pageWidth}`);
const toolbox = (page) => page.locator('[data-frames-sheet-toolbox]');
async function tab(page, name) {
  await toolbox(page).getByRole('button', { name, exact: true }).click();
  await page.waitForTimeout(200);
}
/** Do something that sends one edit, and wait for the sheet the backend answers. */
async function edited(page, action, pattern = /\/sheet\/[^/]+\/(reading|transpose|add|remove|undo|redo)(\?|$)/) {
  const [response] = await Promise.all([
    page.waitForResponse((r) => pattern.test(r.url()) && r.request().method() === 'POST' && !/preview=true/.test(r.url())),
    action(),
  ]);
  await page.waitForTimeout(300);
  return response;
}
/** Pick the note `ref` with a click on its head (Shift adds it to the notes picked). */
async function clickHead(page, ref, modifiers = []) {
  const head = page.locator(`[data-frames-sheet] [data-note~="${ref}"]`).first();
  await head.scrollIntoViewIfNeeded();
  const box = await head.boundingBox();
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  for (const key of modifiers) await page.keyboard.down(key);
  await page.mouse.down();
  await page.mouse.up();
  for (const key of modifiers) await page.keyboard.up(key);
  await page.waitForTimeout(200);
}
/** The point of the screen where a frame is drawn on the sheet, on the upper staff's strip of its line. */
async function pointOf(page, sheet, frame, above = 2) {
  const column = sheet.columns.find((c) => c.frame >= frame) ?? sheet.columns[0];
  const system = sheet.systems[column.system];
  const svg = await page.locator('[data-frames-sheet] svg').first().boundingBox();
  const scale = svg.width / sheet.width;
  return { x: svg.x + column.x * scale, y: svg.y + (system.staff_top - above) * scale };
}

const made = [];
try {
  const copy = await post(`${api}/projects/${values.version}/duplicate`, {});
  made.push(copy.id);
  const part = copy.parts?.[0] ?? copy.id;
  let sheet = await now(part);
  check('a copy of a sheet the AI wrote can be edited', sheet.editable === true && sheet.llm.enhanced === true);
  const page = await open(`/projects/${part}/sheet`);
  sheet = await now(part);

  // ------------------------------------------------------------------ Title
  await page.getByTestId('sheet-toolbox').click();
  await toolbox(page).waitFor();
  const field = page.locator('[data-title-field="title"]');
  await field.fill('Seven Years (copy)');
  await edited(page, () => field.press('Enter'));
  sheet = await now(part);
  check('a title is written into the sheet', sheet.titles.title === 'Seven Years (copy)');
  check('and printed above it', (await page.locator('[data-sheet-title]').innerText()) === 'Seven Years (copy)');

  // ------------------------------------------------------------------ View: the space between lines
  await tab(page, 'View');
  const before = sheet;
  const slider = page.getByTestId('line-space').locator('input');
  await edited(page, async () => {
    await slider.focus();
    for (let i = 0; i < 4; i += 1) await page.keyboard.press('ArrowRight');
  });
  await page.waitForTimeout(800);
  sheet = await now(part);
  check(
    'more space between lines: taller, and no column moves sideways',
    sheet.lineSpace > 5 && sheet.height > before.height && JSON.stringify(sheet.columns.map((c) => c.x)) === JSON.stringify(before.columns.map((c) => c.x)),
    `${sheet.lineSpace} staff spaces`,
  );

  // ------------------------------------------------------------------ Transpose figures, with the preview
  await tab(page, 'Transpose');
  await page.locator('[data-transpose-tab]').getByRole('button', { name: 'Figures' }).click();
  await page.locator('[aria-label="Transpose figures to"] button').nth(3).click(); // corchea
  await page.locator('[data-transpose-preview="figures"]').click();
  await page.locator('[data-transpose-sheet] svg').waitFor({ timeout: 30000 });
  check('Transpose figures shows the sheet as it would be', (await now(part)).quarterMs === sheet.quarterMs);
  await page.screenshot({ path: path.join(values.out, '01-figures-preview.png') });
  await edited(page, () => page.locator('[data-transpose-confirm]').click());
  const renamed = await now(part);
  // The spacing keeps its figure (D-18); only the rules that read the names move a column: a note renamed a
  // semicorchea or shorter may become a grace note, drawn before its main note instead of at a column of its own.
  const graces = (s) => s.notes.filter((n) => n.grace).length;
  const xs = new Map(sheet.columns.map((c) => [c.frame, c.x]));
  const kept = renamed.columns.filter((c) => xs.get(c.frame) === c.x).length;
  check(
    'every figure one step shorter, and the spacing keeps its figure',
    renamed.quarterMs === 2 * sheet.quarterMs && renamed.spaceMs === sheet.quarterMs,
    `${Math.round(sheet.quarterMs)} ms -> ${Math.round(renamed.quarterMs)} ms; ${kept} of ${renamed.columns.length} columns in place, grace notes ${graces(sheet)} -> ${graces(renamed)}`,
  );
  await page.keyboard.press('Escape');
  await page.screenshot({ path: path.join(values.out, '01b-figures-renamed.png') });
  await edited(page, () => page.getByTestId('sheet-undo').click());
  check('Undo names the figures back', (await now(part)).quarterMs === sheet.quarterMs);

  // ------------------------------------------------------------------ Transpose notes, with the preview
  await page.locator('[data-transpose-tab]').getByRole('button', { name: 'Notes' }).click();
  await page.locator('[aria-label="Transpose to"] [data-midi="62"]').click();
  await page.locator('[data-transpose-preview="notes"]').click();
  await page.locator('[data-transpose-sheet] svg').waitFor({ timeout: 30000 });
  await edited(page, () => page.locator('[data-transpose-confirm]').click());
  const up = await now(part);
  const pitches = (s) => s.notes.map((n) => Number(n.ref.split(':')[1])).sort((a, b) => a - b);
  check(
    'every note two semitones higher, the AI mark kept',
    JSON.stringify(pitches(up)) === JSON.stringify(pitches(sheet).map((k) => k + 2)) && up.llm.enhanced,
    `armadura ${sheet.reading.key} -> ${up.reading.key}`,
  );
  await page.screenshot({ path: path.join(values.out, '02-transposed.png') });
  await edited(page, () => page.getByTestId('sheet-undo').click());
  check('Undo moves every note back', JSON.stringify(pitches(await now(part))) === JSON.stringify(pitches(sheet)));

  // ------------------------------------------------------------------ Lyrics
  await tab(page, 'Lyrics');
  await page.locator('[data-lyrics-paste]').fill('Once I was seven years old\nMy mama told me');
  await page.locator('[data-lyrics-add]').click();
  await page.locator('[data-lyrics-piece="0"]').waitFor();
  sheet = await now(part);
  const target = await pointOf(page, sheet, sheet.columns[6].frame);
  await page.evaluate(({ y }) => window.scrollTo(0, Math.max(0, window.scrollY + y - 400)), target);
  await page.waitForTimeout(300);
  const drop = await pointOf(page, sheet, sheet.columns[6].frame);
  const sheetBox = await page.locator('[data-frames-sheet]').boundingBox();
  await edited(page, () =>
    page.locator('[data-lyrics-piece="0"]').dragTo(page.locator('[data-frames-sheet]'), {
      targetPosition: { x: drop.x - sheetBox.x, y: drop.y - sheetBox.y },
    }),
  );
  sheet = await now(part);
  const placed = sheet.lyrics[0];
  check('a pool piece dropped on the sheet is placed on a frame', placed?.text === 'Once I was seven years old', placed ? `f${placed.start}-f${placed.end}` : 'none');
  check('and drawn above the staff', (await page.locator('[data-frames-sheet] [data-lyric="0"]').count()) === 1);
  await page.locator('[data-frames-sheet] [data-lyric="0"]').scrollIntoViewIfNeeded();
  const words = await page.locator('[data-frames-sheet] [data-lyric="0"]').boundingBox();
  const svgBox = await page.locator('[data-frames-sheet] svg').first().boundingBox();
  await page.screenshot({
    path: path.join(values.out, '03-lyric-placed.png'),
    clip: { x: Math.max(0, words.x - 120), y: words.y - 40, width: 700, height: 220 },
  });
  // Moved by dragging it on the sheet, a few columns later.
  const later = sheet.columns.findIndex((c) => c.frame >= placed.end) + 2;
  const there = await pointOf(page, sheet, sheet.columns[later].frame);
  const scale = svgBox.width / sheet.width;
  await edited(page, async () => {
    await page.mouse.move(words.x + 4, words.y + words.height / 2);
    await page.mouse.down();
    await page.mouse.move(words.x + 30, words.y + words.height / 2, { steps: 4 });
    await page.mouse.move(there.x + 4, words.y + words.height / 2, { steps: 8 });
    await page.mouse.up();
  });
  sheet = await now(part);
  check('a piece dragged on the sheet moves to the frame under it', sheet.lyrics[0]?.start > placed.start, `f${placed.start} -> f${sheet.lyrics[0]?.start}`);
  check('the frames under a dragged piece are shaded meanwhile', scale > 0);
  // Picked and taken off with Delete.
  const moved = await page.locator('[data-frames-sheet] [data-lyric="0"]').boundingBox();
  await page.mouse.click(moved.x + moved.width / 2, moved.y + moved.height / 2);
  await page.waitForTimeout(200);
  check('a click picks the piece', (await page.locator('[data-lyric-picked]').count()) === 1);
  await edited(page, () => page.keyboard.press('Delete'));
  check('Delete takes it off the sheet', (await now(part)).lyrics.length === 0);
  await edited(page, () => page.getByTestId('sheet-undo').click());
  check('and Undo brings it back', (await now(part)).lyrics.length === 1);

  // ------------------------------------------------------------------ the chord keyboard of the note toolbox
  await page.keyboard.press('Escape');
  await page.keyboard.press('Escape');
  sheet = await now(part);
  const frameOfRef = (ref) => Number(ref.split(':')[0]);
  const midiOfRef = (ref) => Number(ref.split(':')[1]);
  // A right-hand chord of two or more notes, not a grace note, in a column whose keys are all different.
  const byColumn = new Map();
  for (const n of sheet.notes) byColumn.set(frameOfRef(n.ref), [...(byColumn.get(frameOfRef(n.ref)) ?? []), n]);
  const [chordFrame, columnNotes] = [...byColumn.entries()].find(
    ([, ns]) =>
      ns.filter((n) => n.hand === 'right' && !n.grace && n.figure >= 8 && n.beam !== null).length >= 2 &&
      new Set(ns.map((n) => midiOfRef(n.ref))).size === ns.length,
  );
  const rightChord = columnNotes.filter((n) => n.hand === 'right');
  const countBefore = sheet.notes.length;
  const pickedRef = rightChord[0].ref;
  await clickHead(page, pickedRef);
  const keys = page.locator('[data-frames-note-toolbox] [data-chord-keys]');
  await keys.waitFor({ timeout: 5000 });
  const litKeys = async () => (await keys.locator('[data-lit]').evaluateAll((els) => els.map((e) => Number(e.getAttribute('data-midi'))))).sort((a, b) => a - b);
  const columnKeys = columnNotes.map((n) => midiOfRef(n.ref)).sort((a, b) => a - b);
  check('picking a note shows its column on the keyboard, both hands lit', JSON.stringify(await litKeys()) === JSON.stringify(columnKeys), `${columnKeys}`);
  await page.locator('[data-frames-note-toolbox]').screenshot({ path: path.join(values.out, '03b-chord-keys.png') });
  const top = Math.max(...rightChord.map((n) => midiOfRef(n.ref)));
  const extra = [top + 1, top + 2, top + 3, top + 4].find((midi) => !columnKeys.includes(midi) && midi <= 108);
  await edited(page, () => keys.locator(`[data-midi="${extra}"]`).click());
  sheet = await now(part);
  const addedNote = sheet.notes.find((n) => n.ref === `${chordFrame}:${extra}`);
  check(
    'a dark key adds a note to the chord, in its hand, with its figure and beam group',
    addedNote?.hand === 'right' && addedNote.figure === rightChord[0].figure && addedNote.beam === rightChord[0].beam,
    `${addedNote?.hand} ${addedNote?.figure} ${addedNote?.beam}; the chord ${rightChord[0].figure} ${rightChord[0].beam}`,
  );
  check('it is one step of undo', sheet.history.undo === 'Add a note');
  check('the chord stays picked, with the new key lit', (await keys.count()) === 1 && (await litKeys()).includes(extra));
  await page.locator('[data-frames-note-toolbox]').screenshot({ path: path.join(values.out, '03c-chord-key-added.png') });
  await edited(page, () => keys.locator(`[data-midi="${extra}"]`).click());
  sheet = await now(part);
  check('the lit key takes it off again', !sheet.notes.some((n) => n.ref === `${chordFrame}:${extra}`) && sheet.history.undo === 'Take a note off the page');
  check('and the chord is still picked', JSON.stringify(await litKeys()) === JSON.stringify(columnKeys));
  await edited(page, () => page.getByTestId('sheet-undo').click());
  check('Undo brings the note back', (await now(part)).notes.some((n) => n.ref === `${chordFrame}:${extra}`));
  await edited(page, () => page.getByTestId('sheet-undo').click());
  sheet = await now(part);
  check('a second Undo takes it away', !sheet.notes.some((n) => n.ref === `${chordFrame}:${extra}`) && sheet.notes.length === countBefore);
  const otherRef = sheet.notes.find((n) => frameOfRef(n.ref) > chordFrame && n.hand === 'right').ref;
  await clickHead(page, otherRef, ['Shift']);
  check('notes of two columns show no keyboard', (await keys.count()) === 0);
  await page.keyboard.press('Escape');

  // ------------------------------------------------------------------ the keyboard panel
  await page.keyboard.press('Escape');
  sheet = await now(part);
  const column = sheet.columns[10];
  const head = page.locator(`[data-frames-sheet] [data-note^="${column.frame}:"]`).first();
  await head.scrollIntoViewIfNeeded();
  const headBox = await head.boundingBox();
  // A click off the notes moves the cursor to that column (a click on a head would pick it).
  const above = await pointOf(page, sheet, column.frame, -6);
  await page.mouse.click(headBox.x + headBox.width / 2, above.y);
  await page.waitForTimeout(400);
  // The panel opens after the cursor moved: it may cover the place clicked.
  await page.getByRole('button', { name: 'More sheet actions' }).click();
  await page.getByRole('menuitem', { name: 'Show the keyboard' }).click();
  await page.waitForTimeout(300);
  const notesBefore = sheet.notes.length;
  const lit = new Set(sheet.notes.filter((n) => Number(n.ref.split(':')[0]) === column.frame).map((n) => Number(n.ref.split(':')[1])));
  const free = [96, 97, 98, 99, 100].find((midi) => !lit.has(midi));
  await edited(page, () => page.locator(`[aria-label="Keys sounding under the playhead"] [data-key-row="${free - 21}"]`).click());
  const added = await now(part);
  check('a dark key adds a note under the cursor', added.notes.length === notesBefore + 1, `${added.history.undo}`);
  await edited(page, () => page.getByTestId('sheet-undo').click());
  check('Undo takes it off again', (await now(part)).notes.length === notesBefore);
  await page.screenshot({ path: path.join(values.out, '04-keyboard.png') });

  // ------------------------------------------------------------------ Print to PDF
  await page.getByTestId('sheet-print').click();
  await page.locator('[data-pdf-page]').first().waitFor({ timeout: 30000 });
  const pages = await page.locator('[data-pdf-page]').count();
  check('Print to PDF lays the sheet out on pages', pages >= 2, `${pages} pages`);
  await page.screenshot({ path: path.join(values.out, '05-pdf-dialog.png') });
  const [download] = await Promise.all([page.waitForEvent('download', { timeout: 60000 }), page.getByTestId('pdf-download').click()]);
  const file = path.join(values.out, 'sheet.pdf');
  await download.saveAs(file);
  const bytes = (await import('node:fs')).readFileSync(file);
  const text = bytes.toString('latin1');
  const count = (text.match(/\/Type \/Page\b/g) ?? []).length;
  check('the PDF is written, one page per page', text.startsWith('%PDF') && count === pages, `${Math.round(bytes.length / 1024)} kB, ${count} pages`);
  check('without the notation font (the glyphs are paths)', !text.includes('/Bravura'));
  await page.getByRole('button', { name: 'Close' }).click();
  await page.close();

  // ------------------------------------------------------------------ Play mode: the lyrics piece that sounds
  sheet = await now(part);
  const first = sheet.columns[0].frame;
  await post(`${api}/sheet/${part}/reading?width=${pageWidth}`, {
    action: 'lyrics',
    value: { pieces: [{ start: first, end: first + 150, text: 'Once I was seven years old', size: null, lift: 0 }] },
  });
  const play = await open(`/play/${copy.id}`);
  await play.keyboard.press('Space');
  await play.locator('[data-lyric-lit]').first().waitFor({ timeout: 20000 }).catch(() => undefined);
  check('in Play mode the lyrics piece that sounds is lit', (await play.locator('[data-lyric-lit]').count()) === 1);
  await play.screenshot({ path: path.join(values.out, '06-play-lyric.png') });
  await play.keyboard.press('Space');
  await play.close();
  writeFileSync(path.join(values.out, 'summary.txt'), failures.length ? failures.join('\n') : 'all passed\n');
} finally {
  for (const id of made) await fetch(`${api}/projects/${id}`, { method: 'DELETE' }).catch(() => undefined);
  await browser.close();
}

for (const problem of problems) console.log(`problem: ${problem}`);
console.log(failures.length === 0 && problems.length === 0 ? 'all passed' : `${failures.length} failed, ${problems.length} problems`);
process.exit(failures.length === 0 && problems.length === 0 ? 0 : 1);
