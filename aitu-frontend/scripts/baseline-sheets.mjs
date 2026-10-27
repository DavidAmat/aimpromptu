/**
 * Screenshots of every screen that draws a piano sheet (implementation 03, Phase 0: the baseline
 * before vexflow-v2 is replaced; Phase 10 takes them again on the new sheet, with the same numbers,
 * to compare: `--out .../screenshots/phase-10`).
 *
 * Real pieces are only opened, never clicked. Every screen that needs a click (a toolbox, a
 * dialog, the page of a passage, From other projects) works on a temporary copy of the project
 * (`POST /projects/{id}/duplicate`), deleted at the end with any passage made on it.
 *
 *     node scripts/baseline-sheets.mjs [--out DIR] [--only 04,11]
 *
 * Defaults: the sheet of Superestrella (`b99bc3ae`, a project of the Personal Vault) and the
 * version of 7 Years in My library (`1a16a836`, one of the 10 songs of the research viewer), the
 * integrated playlist `d13c185f` for Play mode. Signed in as the master user (scripts/session.mjs).
 */

import { mkdirSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseArgs } from 'node:util';
import { chromium } from 'playwright';
import { markStretch, waitForFrames, watchSheets } from './frames-page.mjs';
import { signIn, useSession } from './session.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const { values } = parseArgs({
  options: {
    out: {
      type: 'string',
      default: path.join(here, '..', '..', 'context', 'implementations', '03-apply-poc-research', 'screenshots', 'phase-0'),
    },
    base: { type: 'string', default: 'http://localhost:5173' },
    project: { type: 'string', default: 'b99bc3ae-' },
    version: { type: 'string', default: '1a16a836-' },
    playlist: { type: 'string', default: 'd13c185f-' },
    only: { type: 'string', default: '' },
  },
});
const base = values.base;
const api = `${base}/api`;
const only = new Set(values.only.split(',').filter(Boolean));
mkdirSync(values.out, { recursive: true });
await signIn(base);

const json = async (url, init) => {
  const answer = await fetch(url, init);
  if (!answer.ok) throw new Error(`${init?.method ?? 'GET'} ${url}: ${answer.status} ${await answer.text()}`);
  return answer.status === 204 ? null : answer.json();
};
const projects = await json(`${api}/projects`);
const byPrefix = (prefix) => {
  const found = projects.find((row) => row.id.startsWith(prefix));
  if (found) return found.id;
  return null;
};
const project = byPrefix(values.project);
if (!project) throw new Error(`No project of the vault starts with ${values.project}`);
// A version of My library is not a row of /projects; its id is given whole or found in the songs.
let version = values.version.length === 36 ? values.version : null;
if (!version) {
  for (const song of await json(`${api}/library/songs`)) {
    const detail = await json(`${api}/library/songs/${song.id}`);
    const found = detail.versions.find((row) => row.projectId.startsWith(values.version));
    if (found) { version = found.projectId; break; }
  }
}
if (!version) throw new Error(`No version of My library starts with ${values.version}`);
const playlist = byPrefix(values.playlist);

const browser = await chromium.launch();
useSession(browser);
const problems = [];
const made = new Set();
const passages = new Set();
const shots = [];

async function open(route, { theme = 'light', width = 1440, height = 900 } = {}) {
  const page = await browser.newPage({ viewport: { width, height } });
  await page.addInitScript((mode) => window.localStorage.setItem('mui-mode', mode), theme);
  page.on('console', (message) => { if (message.type() === 'error') problems.push(`${route}: console: ${message.text()}`); });
  page.on('pageerror', (error) => problems.push(`${route}: page error: ${error.message}`));
  page.on('response', (response) => { if (response.status() >= 400) problems.push(`${route}: ${response.status()} ${response.url()}`); });
  watchSheets(page);
  await page.goto(new URL(route, base).toString());
  return page;
}
const waitForSheet = async (page, scope = '') => {
  await waitForFrames(page, { scope });
  await page.waitForTimeout(700);
};
async function shot(page, name, what, options = {}) {
  await page.waitForTimeout(500);
  await page.screenshot({ path: path.join(values.out, `${name}.png`), fullPage: options.full ?? false });
  shots.push({ name, what });
  console.log(`${name}.png  ${what}`);
}
const want = (name) => only.size === 0 || only.has(name.slice(0, 2));

async function screen(name, what, route, prepare, options = {}) {
  if (!want(name)) return;
  const page = await open(route, options);
  try {
    await prepare(page);
    await shot(page, name, what, options);
  } catch (caught) {
    problems.push(`${name}: ${caught instanceof Error ? caught.message.split('\n')[0] : caught}`);
    await page.screenshot({ path: path.join(values.out, `${name}-failed.png`) }).catch(() => undefined);
  } finally {
    await page.close();
  }
}

/** Mark a stretch in the strip above the first line, from `from` to `to` of its columns. */
async function markLine(page, from, to) {
  await markStretch(page, api, { from, to });
  await page.locator('[role=tablist][aria-label="What this stretch carries"]').waitFor({ timeout: 10000 });
}
/** Pick the `nth` notehead with a press on it, as the reader does. */
async function pickNote(page, nth) {
  const head = page.locator('[data-frames-sheet] [data-note]').nth(nth);
  await head.scrollIntoViewIfNeeded();
  const box = await head.boundingBox();
  await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
  await page.locator('[data-frames-note-toolbox]').waitFor({ timeout: 10000 });
}
const toolbox = (page) => page.locator('[data-frames-sheet-toolbox]');
async function openTab(page, name) {
  if ((await toolbox(page).count()) === 0) await page.getByTestId('sheet-toolbox').click();
  await toolbox(page).getByRole('button', { name, exact: true }).click();
  await page.waitForTimeout(400);
}
async function moreAction(page, item) {
  await page.getByRole('button', { name: 'More sheet actions' }).first().click();
  await page.getByRole('menuitem', { name: item }).click();
  await page.waitForTimeout(800);
}

try {
  // The real pieces, opened only.
  await screen('01-projects', 'Projects: the step each project reached (four steps: no Hands step)', '/projects',
    async (page) => { await page.locator('table, [role=table], [role=list]').first().waitFor({ timeout: 20000 }); });
  await screen('02-notes-step', 'Notes step: the piano roll with no hands', `/projects/${project}/notes`,
    async (page) => { await page.locator('canvas').first().waitFor({ timeout: 30000 }); await page.waitForTimeout(1500); });
  await screen('03-hands-step', 'The old address of the Hands step: it opens the Sheet step (the step is gone)', `/projects/${project}/hands`,
    async (page) => { await page.waitForURL(/\/sheet$/, { timeout: 20000 }); await waitForSheet(page); });
  await screen('04-sheet-step', 'Sheet step of a project: the new sheet, title lines, floating bar', `/projects/${project}/sheet`,
    (page) => waitForSheet(page));
  await screen('05-sheet-step-full', 'Sheet step of a project, the whole page', `/projects/${project}/sheet`,
    (page) => waitForSheet(page), { full: true });
  await screen('06-library-version', 'A version of My library (7 Years), read only: the sheet draws, plays and prints', `/projects/${version}/sheet`,
    (page) => waitForSheet(page));
  await screen('07-library-version-dark', 'The same version in the dark theme', `/projects/${version}/sheet`,
    (page) => waitForSheet(page), { theme: 'dark' });
  await screen('08-play-sheet', 'Play mode, Sheet view (7 Years)', `/play/${version}`,
    (page) => waitForSheet(page));
  await screen('09-play-falling', 'Play mode, Notes Falling view (7 Years)', `/play/${version}?view=falling`,
    async (page) => { await page.locator('[data-play-menu]').first().waitFor({ timeout: 30000 }); await page.waitForTimeout(2500); });
  if (playlist) {
    await screen('10-play-integrated', 'Play mode of an integrated playlist: each part under its subheader', `/play/${playlist}`,
      (page) => waitForSheet(page));
  }

  // A temporary copy for everything that needs a click.
  const original = projects.find((row) => row.id === project);
  const copy = await json(`${api}/projects/${project}/duplicate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title: `baseline-sheets copy of ${original.title}` }),
  });
  made.add(copy.id);
  const part = copy.parts[0];
  const sheet = `/projects/${copy.id}/sheet`;

  await screen('11-note-toolbox', 'Note toolbox: the chord keyboard, hand, figures, fingers, beams, grace note, ornaments', sheet, async (page) => {
    await waitForSheet(page);
    await pickNote(page, 6);
    await page.waitForTimeout(800);
  });
  await screen('12-range-toolbox', 'Range toolbox (Frames): Both / Right / Left, Key, Clef, Octave; Copy, Record, New part, AI', sheet, async (page) => {
    await waitForSheet(page);
    await markLine(page, 0.3, 0.6);
  });
  await screen('13-range-octave', 'Range toolbox, Octave tab: the four lines per hand', sheet, async (page) => {
    await waitForSheet(page);
    await markLine(page, 0.3, 0.6);
    await page.locator('[role=tablist][aria-label="What this stretch carries"]').getByRole('tab', { name: /Octave/ }).click();
  });
  await screen('14-sheet-toolbox-transpose', 'Sheet toolbox, Transpose tab (Notes and Figures)', sheet, async (page) => {
    await waitForSheet(page);
    await openTab(page, 'Transpose');
  });
  await screen('15-transpose-preview', 'Transpose figures, Preview: the sheet in a dialog (negra to corchea)', sheet, async (page) => {
    await waitForSheet(page);
    await openTab(page, 'Transpose');
    await page.locator('[data-transpose-tab]').getByRole('button', { name: 'Figures' }).click();
    await page.locator('[aria-label="Transpose figures to"] button').nth(3).click(); // corchea
    await page.locator('[data-transpose-preview="figures"]').click();
    await page.locator('[data-transpose-sheet] svg').first().waitFor({ timeout: 60000 });
  });
  await screen('16-sheet-toolbox-lyrics', 'Sheet toolbox, Lyrics tab', sheet, async (page) => {
    await waitForSheet(page);
    await openTab(page, 'Lyrics');
  });
  await screen('17-sheet-toolbox-layout', 'Sheet toolbox, View tab: Zoom and Space between lines (the Layout tab before)', sheet, async (page) => {
    await waitForSheet(page);
    await openTab(page, 'View');
  });
  await screen('18-keyboard-panel', 'The keyboard panel under the playhead', sheet, async (page) => {
    await waitForSheet(page);
    await moreAction(page, 'Show the keyboard');
  });
  await screen('19-find-trills', 'The more actions menu (Find trills was dropped in Phase 8)', sheet, async (page) => {
    await waitForSheet(page);
    await page.getByRole('button', { name: 'More sheet actions' }).first().click();
    await page.getByRole('menuitem').first().waitFor({ timeout: 10000 });
  });
  await screen('20-print-pdf', 'Print to PDF: the A4 pages laid out again', sheet, async (page) => {
    await waitForSheet(page);
    await page.getByTestId('sheet-print').click();
    await page.locator('[data-pdf-page]').first().waitFor({ timeout: 30000 });
    await page.waitForTimeout(2000);
  });
  await screen('21-recording-in-sheet', 'Recording in Sheet: the page of a passage, the Current drawn', sheet, async (page) => {
    await waitForSheet(page);
    await markLine(page, 0.05, 0.95);
    await page.getByTestId('range-record').click();
    await page.waitForURL(/\/passages\/[0-9a-f-]+$/, { timeout: 20000 });
    passages.add(/\/passages\/([0-9a-f-]+)$/.exec(page.url())[1]);
    await waitForFrames(page, { scope: '[data-passage-current]' });
    await page.waitForTimeout(1200);
  });
  await screen('22-compose', 'From other projects: the sheet of the source project, to pick passages', '/projects/compose', async (page) => {
    await page.waitForSelector('[data-compose-picker] [role=listitem]', { timeout: 20000 });
    await page.getByLabel('Filter').fill('baseline-sheets copy');
    await page.locator('[data-compose-picker] [role=listitem]').first().getByRole('button').first().click();
    await page.waitForSelector('[data-compose-source]', { timeout: 20000 });
    await waitForSheet(page);
  });
  console.log(`(copy ${copy.id}, part ${part})`);
} finally {
  await browser.close();
  for (const id of passages) await fetch(`${api}/passages/${id}`, { method: 'DELETE' });
  for (const id of made) await fetch(`${api}/projects/${id}`, { method: 'DELETE' });
  const left = (await json(`${api}/projects`)).filter((row) => made.has(row.id) || /baseline-sheets/.test(row.title)).length;
  let open = 0;
  for (const id of passages) if ((await fetch(`${api}/passages/${id}`)).status !== 404) open += 1;
  console.log(`\n${shots.length} screenshots in ${values.out}`);
  console.log(`Left behind: ${left} projects, ${open} passages`);
  console.log(problems.length ? `\nProblems:\n${problems.join('\n')}` : '\nNo console error, no failed request.');
}
