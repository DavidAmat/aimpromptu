/**
 * From other projects, the parts of a project, and the songs playlists (implementation 02, Phase
 * 10), walked in a headless Chromium.
 *
 * Drives the real page through the running app (`make up`), signed in (`session.mjs`), on
 * **temporary copies** only, deleted at the end, so no project of a library is changed:
 *
 * 1. **New project → From other projects**: a project is chosen, a stretch of its read-only sheet
 *    is marked and added, a second project is added whole, a third passage starts a **Subheader**;
 *    a passage is moved; **Save as integrated playlist** makes the project, which opens on its
 *    Sheet step with its parts beside it;
 * 2. the parts: rename, move, join, and **Start a new part here** in the range toolbox;
 * 3. a copy saved to My library (through the API): **Make a playlist** from a selection on Songs,
 *    **Add to a playlist** from a version's menu, a song removed from the playlist, the playlist
 *    deleted;
 * 4. 390 px and dark.
 *
 *     npm run check:compose
 *     npm run check:compose -- --first Elefants --second SUPERESTRELLA --out /tmp/compose
 */

import { mkdirSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseArgs } from 'node:util';
import { chromium } from 'playwright';
import { oldSheet, signIn, useSession } from './session.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const { values } = parseArgs({
  options: {
    out: { type: 'string', default: path.join(here, '..', '..', '.run', 'screenshots', 'compose') },
    base: { type: 'string', default: 'http://localhost:5173' },
    first: { type: 'string', default: 'Elefants' },
    second: { type: 'string', default: 'SUPERESTRELLA' },
  },
});
const base = values.base;
const api = `${base}/api`;
await signIn(base);
const out = path.resolve(values.out);
mkdirSync(out, { recursive: true });

const results = [];
const check = (label, ok, extra = '') => {
  results.push(`${ok ? '  ok  ' : '  FAIL'} ${label}${extra ? ` (${extra})` : ''}`);
};
const json = async (url, init) => {
  const answer = await fetch(url, init);
  if (!answer.ok) throw new Error(`${init?.method ?? 'GET'} ${url}: ${answer.status} ${await answer.text()}`);
  return answer.status === 204 ? null : answer.json();
};
const send = (method, url, body) =>
  json(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body ?? {}) });

const made = new Set();
const songs = new Set();
const playlists = new Set();
const browser = await chromium.launch();
useSession(browser);
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const problems = [];
page.on('console', (m) => { if (m.type() === 'error') problems.push(`console: ${m.text()}`); });
page.on('pageerror', (e) => problems.push(`page error: ${e.message}`));
page.on('response', (r) => { if (r.status() >= 400) problems.push(`${r.status()} ${r.url()}`); });
const shot = async (name) => {
  await page.waitForTimeout(400);
  await page.screenshot({ path: path.join(out, `${name}.png`) });
};
const waitForSheet = async () => {
  await oldSheet(page, { drawn: false });
  await page.waitForSelector('.grid-note-target', { timeout: 90000 });
  await page.waitForTimeout(800);
};
const notesOf = async (id) => (await json(`${api}/pieces/${id}/notes`)).id.length;
const partsOf = async (id) => (await json(`${api}/projects/${id}/parts`)).parts;
/** Mark a stretch on the first line's frame ruler, from `from` to `to` of its width. */
const markStretch = async (from, to) => {
  await page.locator('.grid-frame-ruler').first().scrollIntoViewIfNeeded();
  await page.waitForTimeout(300);
  const box = await page.locator('.grid-frame-ruler').first().boundingBox();
  await page.mouse.click(box.x + box.width * from, box.y + box.height / 2);
  await page.waitForTimeout(300);
  await page.keyboard.down('Shift');
  await page.mouse.click(box.x + box.width * to, box.y + box.height / 2);
  await page.keyboard.up('Shift');
  await page.waitForTimeout(400);
};
const rowMenu = async (row, item) => {
  await row.getByRole('button', { name: /more actions/i }).click();
  await page.getByRole('menuitem', { name: item }).click();
  await page.waitForTimeout(300);
};

async function freshCopy(label, name) {
  const vault = await json(`${api}/projects`);
  const original = vault
    // The shortest title that names it: the song itself, not a playlist or a copy made of it.
    .filter((row) => row.step === 'sheet' && row.title.toUpperCase().includes(name.toUpperCase()) && !row.title.includes('(check-'))
    .sort((a, b) => a.title.length - b.title.length)[0];
  if (!original) throw new Error(`No project of the vault named ${name} has its piano sheet`);
  const copy = await send('POST', `${api}/projects/${original.id}/duplicate`, { title: `${original.title} (${label})` });
  made.add(copy.id);
  return { id: copy.id, title: copy.title };
}

/** Open a project of the picker by its title, and wait for its sheet. */
async function pick(title) {
  await page.getByLabel('Filter').fill(title);
  await page.locator('[data-compose-picker] [role=listitem]').first().getByRole('button').first().click();
  await page.waitForSelector('[data-compose-source]', { timeout: 20000 });
  await waitForSheet();
}

try {
  const first = await freshCopy('check-compose-a', values.first);
  const second = await freshCopy('check-compose-b', values.second);
  const firstNotes = await notesOf(first.id);
  const secondNotes = await notesOf(second.id);

  // 1. From other projects.
  await page.goto(`${base}/projects`);
  await page.evaluate(() => localStorage.removeItem('aitu.compose.draft'));
  await page.getByRole('button', { name: 'New project' }).click();
  await page.getByRole('menuitem', { name: /From other projects/ }).click();
  await page.waitForURL('**/projects/compose');
  await page.waitForSelector('[data-compose-picker] [role=listitem]', { timeout: 20000 });
  check('New project → From other projects opens the picker', true);
  await shot('01-picker');

  await pick('check-compose-a');
  await markStretch(0.15, 0.6);
  const add = page.getByTestId('readonly-stretch-action');
  await add.waitFor({ timeout: 10000 });
  check('a stretch marked on the read-only sheet offers Add this stretch', (await add.textContent()) === 'Add this stretch');
  await shot('02-mark-a-stretch');
  await add.click();
  await page.locator('[data-compose-passage]').first().waitFor();

  await page.getByTestId('compose-add').click();
  await pick('check-compose-b');
  await page.getByTestId('compose-add-whole').click();
  await page.getByTestId('compose-add').click();
  await pick('check-compose-a');
  await page.getByTestId('compose-add-whole').click();
  const rows = page.locator('[data-compose-passage]');
  check('three passages listed', (await rows.count()) === 3);
  // The third starts a part of its own, under a title.
  const third = rows.nth(2);
  await third.getByRole('button', { name: 'Subheader' }).click();
  await third.getByRole('textbox', { name: 'Title' }).fill('Coda');
  // Moved up and back down by its menu.
  await rowMenu(third, 'Move up');
  check('Move up puts the passage in the place before', (await rows.nth(1).getByText(first.title).count()) > 0);
  await rowMenu(rows.nth(1), 'Move down');
  await shot('03-passages');
  const draft = await page.evaluate(() => JSON.parse(localStorage.getItem('aitu.compose.draft') ?? '[]'));
  check(
    'the list survives in the browser: a stretch, a whole sheet, a subheader',
    draft.length === 3 && draft[0].fromMs !== null && draft[1].fromMs === null && draft[2].join === 'subheader' && draft[2].subheader === 'Coda',
  );
  await page.reload();
  await page.locator('[data-compose-passage]').nth(2).waitFor();
  check('a reload keeps the passages', (await page.locator('[data-compose-passage]').count()) === 3);

  await page.getByRole('button', { name: 'Save as integrated playlist' }).click();
  const dialog = page.getByRole('dialog', { name: 'Save as integrated playlist' });
  await dialog.getByLabel('Title').fill('Medley (check-compose)');
  await shot('04-save');
  await dialog.getByTestId('compose-save').click();
  await page.waitForURL(/\/projects\/[0-9a-f-]+\/sheet$/, { timeout: 120000 });
  const project = /\/projects\/([0-9a-f-]+)\/sheet/.exec(page.url())[1];
  made.add(project);
  await waitForSheet();
  await page.locator('[data-parts-panel]').waitFor({ timeout: 20000 });
  const row = await json(`${api}/projects/${project}`);
  const parts = await partsOf(project);
  check('Save makes an integrated playlist of two parts', row.kind === 'integratedPlaylist' && parts.length === 2, `${parts.length} parts`);
  check('the parts are titled after the source and the subheader', parts[1].subheader === 'Coda' && parts[0].subheader === draft[0].title, parts.map((p) => p.subheader).join(', '));
  const inFirst = await notesOf(parts[0].id);
  const inSecond = await notesOf(parts[1].id);
  check(
    'the first part holds the stretch and the whole second project',
    inFirst > secondNotes && inFirst < secondNotes + firstNotes,
    `${inFirst} notes`,
  );
  check('the second part holds the whole first project', inSecond === firstNotes, `${inSecond} of ${firstNotes}`);
  const statuses = await Promise.all(parts.map((part) => json(`${api}/pieces/${part.id}/status`)));
  check('every part opens on a ready Sheet step', statuses.every((s) => s.steps.find((one) => one.step === 'sheet').state === 'ready'));
  check('the list was emptied once saved', (await page.evaluate(() => localStorage.getItem('aitu.compose.draft'))) === null);
  check('the sources did not change', (await notesOf(first.id)) === firstNotes && (await notesOf(second.id)) === secondNotes);
  await shot('05-integrated-playlist');

  // 2. The parts.
  const panel = page.locator('[data-parts-panel]');
  await rowMenu(panel.getByTestId('part-1'), 'Rename');
  const rename = page.getByRole('dialog', { name: 'Rename the part' });
  await rename.getByLabel('Title').fill('Ending');
  await rename.getByRole('button', { name: 'Rename' }).click();
  await panel.getByText('Ending').waitFor();
  check('a part is renamed', (await partsOf(project))[1].subheader === 'Ending');
  await rowMenu(panel.getByTestId('part-1'), 'Move up');
  await page.waitForTimeout(800);
  check('a part is moved', (await partsOf(project))[0].subheader === 'Ending');
  await panel.getByTestId('part-1').getByRole('button').first().click();
  await page.waitForURL(`**/projects/${parts[0].id}/sheet`);
  await waitForSheet();
  const joinDone = page.waitForResponse((r) => r.url().endsWith('/join') && r.request().method() === 'POST', { timeout: 120000 });
  await rowMenu(panel.getByTestId('part-1'), /^Join with/);
  await joinDone;
  const joined = await partsOf(project);
  check('two parts are joined into one', joined.length === 1 && (await notesOf(joined[0].id)) === inFirst + inSecond, `${joined.length} parts`);
  await page.waitForURL(`**/projects/${joined[0].id}/sheet`);
  await waitForSheet();
  await markStretch(0.5, 0.6);
  const split = page.getByTestId('range-split');
  await split.waitFor({ timeout: 10000 });
  await shot('06-start-a-new-part-here');
  const splitDone = page.waitForResponse((r) => r.url().endsWith('/split') && r.request().method() === 'POST', { timeout: 120000 });
  await split.click();
  await splitDone;
  const halves = await partsOf(project);
  const halfNotes = await Promise.all(halves.map((part) => notesOf(part.id)));
  check('Start a new part here splits the part', halves.length === 2 && halfNotes[0] + halfNotes[1] === inFirst + inSecond, halfNotes.join(' + '));
  await page.locator('[data-parts-panel] [data-testid=part-1]').waitFor({ timeout: 20000 });
  await waitForSheet();
  await shot('07-split');

  // 3. Songs playlists, on a copy saved to My library.
  const kept = await freshCopy('check-compose-song', values.first);
  const saved = await send('POST', `${api}/projects/${kept.id}/library`, {
    song: 'check-compose song',
    artist: 'check-compose artist',
    version: 'original',
  });
  songs.add(saved.songId);
  await page.goto(`${base}/library/songs`);
  await page.getByLabel('Filter').fill('check-compose');
  await page.getByRole('checkbox', { name: 'Select this row' }).first().check();
  await page.getByTestId('make-playlist').click();
  const makeDialog = page.getByRole('dialog', { name: 'Make a playlist' });
  await makeDialog.getByLabel('Title').fill('check-compose playlist');
  await shot('08-make-a-playlist');
  await makeDialog.getByRole('button', { name: 'Make the playlist' }).click();
  await page.waitForURL('**/library/playlists/*');
  const playlistId = Number(/\/library\/playlists\/(\d+)/.exec(page.url())[1]);
  playlists.add(playlistId);
  await page.locator('[data-playlist-item]').first().waitFor();
  check('Make a playlist opens it with the song on its version', (await json(`${api}/playlists/${playlistId}`)).items[0]?.versionName === 'original');

  await page.goto(`${base}/library/songs/${saved.songId}`);
  await page.locator(`[data-testid="version-${saved.versionId}"]`).getByRole('button', { name: /more actions/i }).click();
  await page.getByRole('menuitem', { name: 'Add to a playlist' }).click();
  const addDialog = page.getByRole('dialog', { name: 'Add to a playlist' });
  await addDialog.getByRole('button', { name: /check-compose playlist/ }).click();
  await addDialog.getByText(/Added to/).waitFor();
  await addDialog.getByRole('button', { name: 'Open the playlist' }).click();
  await page.waitForURL(`**/library/playlists/${playlistId}`);
  await page.locator('[data-playlist-item="1"]').waitFor();
  check('Add to a playlist puts the version at the end', (await json(`${api}/playlists/${playlistId}`)).items.length === 2);
  await shot('09-playlist');
  await rowMenu(page.locator('[data-playlist-item="1"]'), 'Remove from the playlist');
  await page.waitForTimeout(600);
  check('a song is removed from the playlist', (await json(`${api}/playlists/${playlistId}`)).items.length === 1);
  await page.goto(`${base}/library/playlists`);
  await page.getByText('check-compose playlist').waitFor();
  await shot('10-playlists');
  await page.goto(`${base}/library/playlists/${playlistId}`);
  await page.getByRole('button', { name: 'Playlist actions' }).click();
  await page.getByRole('menuitem', { name: 'Delete playlist' }).click();
  await page.getByRole('dialog').getByRole('button', { name: 'Delete playlist' }).click();
  await page.waitForURL('**/library/playlists');
  playlists.delete(playlistId);
  check('the playlist is deleted, its song kept', (await fetch(`${api}/playlists/${playlistId}`)).status === 404 && (await json(`${api}/library/songs/${saved.songId}`)).versions.length === 1);

  // 4. Narrow and dark.
  await page.goto(`${base}/projects/compose`);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForSelector('[data-compose-picker] [role=listitem]', { timeout: 20000 });
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  check('390 px: no sideways scroll on the picker', overflow <= 0, `${overflow} px`);
  await shot('11-picker-390');
  await page.goto(`${base}/projects/${halves[0].id}/sheet`);
  await waitForSheet();
  const overflowSheet = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  check('390 px: no sideways scroll with the parts', overflowSheet <= 0, `${overflowSheet} px`);
  await shot('12-parts-390');
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.emulateMedia({ colorScheme: 'dark' });
  await page.evaluate(() => localStorage.setItem('mui-mode', 'dark'));
  await page.goto(`${base}/projects/${halves[0].id}/sheet`);
  await waitForSheet();
  await shot('13-parts-dark');
  await page.evaluate(() => localStorage.removeItem('mui-mode'));
  await page.emulateMedia({ colorScheme: 'light' });
} finally {
  for (const id of playlists) await fetch(`${api}/playlists/${id}`, { method: 'DELETE' });
  for (const id of songs) await fetch(`${api}/library/songs/${id}`, { method: 'DELETE' });
  for (const id of made) await fetch(`${api}/projects/${id}`, { method: 'DELETE' });
  await page.evaluate(() => localStorage.removeItem('aitu.compose.draft')).catch(() => undefined);
  const left = (await json(`${api}/projects?layer=vault&layer=private`)).filter(
    (row) => /check-compose/.test(row.title) || made.has(row.id),
  ).length;
  const leftSongs = (await json(`${api}/library/songs`)).filter((row) => /check-compose/.test(row.title)).length;
  check('nothing the check made is left', left === 0 && leftSongs === 0, `${left} projects, ${leftSongs} songs`);
  await browser.close();
}

const unexpected = problems.filter(
  (line) =>
    !/401 .*\/auth\/me/.test(line) &&
    !/404 .*\/time\/[0-9a-f-]+\/rhythm$/.test(line) &&
    !/404 .*\/playlists\/\d+$/.test(line) &&
    !/Failed to load resource: .* (404)/.test(line),
);
console.log(results.join('\n'));
if (unexpected.length) console.log(`\nProblems:\n${unexpected.slice(0, 20).join('\n')}`);
console.log(`\nScreenshots in ${out}`);
process.exit(results.some((line) => line.includes('FAIL')) || unexpected.length ? 1 : 0);
