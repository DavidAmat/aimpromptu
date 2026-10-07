/**
 * The Private Library, walked in a headless Chromium (implementation 02, Phase 6).
 *
 * Drives the real page through the running app (`make up`), signed in (`session.mjs`). It works on
 * a **temporary copy** of a project whose piano sheet is saved (Elefants by default), saved under a
 * song and an artist of its own, and deletes all of it at the end, so no project or song of a
 * library is changed:
 *
 * - the project page of the copy: **Save to library** (artist, song, version name), which opens the
 *   song; the copy left Projects, and its audio was written again with only the ranges in use;
 * - the version opened **read only**: **Edit** is the one action, no Save, no toolbox;
 * - **Edit**: a copy in Projects that says Editing; **Save to library → Replace** the version (one
 *   earlier state in its history); **History → Restore**; Edit again and **Save as a new version**;
 * - Songs (the filter), Artists, one artist: **Add a name**, **Make default**;
 * - screenshots at 1440 px, at 390 px and in the dark scheme.
 *
 *     npm run check:library
 *     npm run check:library -- --piece Superestrella --out /tmp/library
 */

import { mkdirSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseArgs } from 'node:util';
import { chromium } from 'playwright';
import { signIn, useSession } from './session.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const { values } = parseArgs({
  options: {
    out: { type: 'string', default: path.join(here, '..', '..', '.run', 'screenshots', 'library') },
    base: { type: 'string', default: 'http://localhost:5173' },
    piece: { type: 'string', default: 'Elefants' },
  },
});
const base = values.base;
const api = `${base}/api`;
await signIn(base);
const out = path.resolve(values.out);
mkdirSync(out, { recursive: true });

const SONG = 'check-library song';
const ARTIST = 'check-library artist';

const results = [];
const check = (label, ok, extra = '') => {
  results.push(`${ok ? '  ok  ' : '  FAIL'} ${label}${extra ? ` (${extra})` : ''}`);
};
const json = async (url, init) => {
  const answer = await fetch(url, init);
  if (!answer.ok) throw new Error(`${init?.method ?? 'GET'} ${url}: ${answer.status} ${await answer.text()}`);
  return answer.status === 204 ? null : answer.json();
};
const post = (url, body) =>
  json(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body ?? {}) });

/** Every project and song this script made, deleted at the end whatever happens. */
const madeProjects = new Set();
const madeSongs = new Set();
const madeArtists = new Set();

const browser = await chromium.launch();
useSession(browser);
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const problems = [];
page.on('console', (m) => { if (m.type() === 'error') problems.push(`console: ${m.text()}`); });
page.on('pageerror', (e) => problems.push(`page error: ${e.message}`));
page.on('response', (r) => { if (r.status() >= 400) problems.push(`${r.status()} ${r.url()}`); });
// A short wait first: a dialog or a menu fades in and out in about 225 ms.
const shot = async (name) => {
  await page.waitForTimeout(350);
  await page.screenshot({ path: path.join(out, `${name}.png`) });
};
const idFromUrl = (url) => /\/projects\/([0-9a-f-]{36})/.exec(url)?.[1] ?? null;
const songFromUrl = (url) => Number(/\/library\/songs\/(\d+)/.exec(url)?.[1] ?? NaN);
const versionRows = () => page.locator('[data-testid^=version-]');
const versionMenu = async (index) => {
  await versionRows().nth(index).getByRole('button', { name: 'More actions' }).click();
};
const saveDialog = () => page.getByRole('dialog', { name: 'Save to library' });

try {
  // 0. The temporary copy.
  const vault = await json(`${api}/projects`);
  const source = vault.find((row) => row.step === 'sheet' && row.title.includes(values.piece));
  if (!source) throw new Error(`No project of the vault named ${values.piece} has its piano sheet`);
  const copy = await post(`${api}/projects/${source.id}/duplicate`, { title: `${source.title} (check-library)` });
  madeProjects.add(copy.id);
  const status = await json(`${api}/pieces/${copy.id}/status`);
  check('the temporary copy has its piano sheet ready', status.steps.find((step) => step.step === 'sheet').state === 'ready');
  const cutsBefore = await json(`${api}/audio/${copy.id}/cuts`);
  const notesBefore = await json(`${api}/pieces/${copy.id}/notes`);

  // 1. Save to library from the project page.
  await page.goto(`${base}/projects/${copy.id}/sheet`);
  const saveButton = page.getByRole('button', { name: 'Save to library' });
  await saveButton.waitFor({ timeout: 60000 });
  await page.waitForSelector('[data-sheet-title]', { timeout: 60000 });
  check('a project with its sheet ready offers Save to library', true);
  await saveButton.click();
  await saveDialog().waitFor();
  await saveDialog().getByLabel('Artist').fill(ARTIST);
  await saveDialog().getByLabel('Song').fill(SONG);
  const versionField = saveDialog().getByLabel('Version name');
  check('the version name starts as “original”', (await versionField.inputValue()) === 'original');
  await shot('01-save-to-library');
  await saveDialog().getByRole('button', { name: 'Save to library' }).click();
  await page.waitForURL('**/library/songs/*', { timeout: 120000 });
  const songId = songFromUrl(page.url());
  madeSongs.add(songId);
  madeProjects.delete(copy.id); // it is the song's version now; the song is deleted at the end
  await versionRows().first().waitFor();
  await shot('02-song');
  const song = await json(`${api}/library/songs/${songId}`);
  check('Save to library opens the song with its version', song.title === SONG && song.versions.length === 1 && song.versions[0].name === 'original');
  check('the song has its artist', song.artists.map((artist) => artist.name).join() === ARTIST);
  for (const artist of song.artists) madeArtists.add(artist.artistId);
  const saved = await json(`${api}/projects/${copy.id}`);
  check('the project moved into the library', saved.layer === 'private' && saved.library?.versionName === 'original');
  const inVault = (await json(`${api}/projects`)).some((row) => row.id === copy.id);
  check('and left Projects', !inVault);
  const cutsAfter = await json(`${api}/audio/${copy.id}/cuts`);
  const kept = (cuts) => cuts.totalFrames - cuts.cuts.reduce((sum, [a, b]) => sum + b - a, 0);
  check('the audio is written again with only the ranges in use', cutsAfter.cuts.length === 0 && kept(cutsAfter) === kept(cutsBefore),
    `${cutsBefore.cuts.length} cuts before, ${kept(cutsBefore)} kept frames; ${kept(cutsAfter)} frames after`);
  const notesAfter = await json(`${api}/pieces/${copy.id}/notes`);
  check('and the notes did not move', JSON.stringify(notesAfter.onMs) === JSON.stringify(notesBefore.onMs));
  const sourceStill = await json(`${api}/audio/${source.id}/cuts`);
  check('the project it was copied from keeps its audio and its cuts', JSON.stringify(sourceStill.cuts) === JSON.stringify(cutsBefore.cuts));

  // 2. The version, read only.
  await versionRows().first().locator('button').first().click();
  await page.waitForURL(`**/projects/${copy.id}**`);
  await page.waitForSelector('[data-sheet-title]', { timeout: 60000 });
  await page.waitForTimeout(500);
  await shot('03-version-read-only');
  check('a version opens read only, with Edit as its action', (await page.getByRole('button', { name: 'Edit', exact: true }).count()) === 1);
  check('the sheet has no Save and no toolbox', (await page.locator('[data-unsaved]').count()) === 0
    && (await page.getByRole('button', { name: 'Sheet toolbox' }).count()) === 0);
  check('the header goes back to the song', (await page.getByRole('button', { name: `Back to ${SONG}` }).count()) === 1);
  await page.getByRole('tab', { name: 'Audio', exact: true }).click();
  await page.waitForSelector('[data-audio]');
  check('the Audio step has no cut and no Transcribe', (await page.getByRole('button', { name: 'Cut the selection' }).count()) === 0
    && (await page.getByRole('button', { name: /Transcribe/ }).count()) === 0);
  await page.getByRole('tab', { name: 'Hands', exact: true }).click();
  await page.waitForTimeout(800);
  check('the Hands step has no Predict hands and no Save', (await page.getByRole('button', { name: 'Predict hands' }).count()) === 0
    && (await page.locator('[data-unsaved]').count()) === 0);
  await shot('04-version-hands-read-only');

  // 3. Edit: a copy in Projects.
  await page.getByRole('button', { name: 'Edit', exact: true }).click();
  await page.waitForURL((url) => idFromUrl(url.toString()) !== copy.id, { timeout: 30000 });
  const editId = idFromUrl(page.url());
  madeProjects.add(editId);
  const edit = await json(`${api}/projects/${editId}`);
  check('Edit opens a copy in Projects that edits the version', edit.layer === 'vault' && edit.basedOn === copy.id && edit.editing?.versionName === 'original');
  await page.goto(`${base}/projects`);
  await page.getByTestId(`project-${editId}`).waitFor();
  check('Projects says Editing', (await page.getByTestId(`project-${editId}`).getByText('Editing').count()) === 1);
  await shot('05-projects-editing');
  await page.goto(`${base}/library/songs/${songId}`);
  await versionRows().first().waitFor();
  check('the version says Editing', (await versionRows().first().getByText('Editing').count()) === 1);

  // 4. Replace the version.
  await page.goto(`${base}/projects/${editId}/sheet`);
  await page.waitForSelector('[data-sheet-title]', { timeout: 60000 });
  await page.getByRole('button', { name: 'Save to library' }).click();
  await saveDialog().waitFor();
  check('a copy opens the dialog on Replace', (await saveDialog().getByRole('button', { name: 'Replace the version' }).count()) === 1);
  await shot('06-replace');
  await saveDialog().getByRole('button', { name: 'Replace the version' }).click();
  await page.waitForURL(`**/library/songs/${songId}`, { timeout: 120000 });
  madeProjects.delete(editId);
  const replaced = await json(`${api}/library/songs/${songId}`);
  check('Replace keeps one version, with one earlier state', replaced.versions.length === 1 && replaced.versions[0].history === 1 && replaced.versions[0].editCopy === null);
  const gone = await fetch(`${api}/projects/${editId}`);
  check('and the copy is gone', gone.status === 404);

  // 5. History and Restore.
  await versionRows().first().waitFor();
  await versionMenu(0);
  await page.getByRole('menuitem', { name: 'History' }).click();
  const history = page.getByRole('dialog', { name: /History of/ });
  await history.waitFor();
  await history.getByRole('button', { name: 'Restore' }).first().waitFor();
  await shot('07-history');
  await history.getByRole('button', { name: 'Restore' }).first().click();
  await page.getByRole('dialog', { name: /Restore the state/ }).getByRole('button', { name: 'Restore' }).click();
  await page.getByRole('status').filter({ hasText: 'restored' }).waitFor({ timeout: 30000 });
  const restored = await json(`${api}/library/songs/${songId}`);
  check('Restore keeps the state it replaces too', restored.versions[0].history === 2);

  // 6. Edit again, and Save as a new version.
  await versionMenu(0);
  await page.getByRole('menuitem', { name: 'Edit', exact: true }).click();
  await page.waitForURL('**/projects/**');
  const secondEdit = idFromUrl(page.url());
  madeProjects.add(secondEdit);
  await page.goto(`${base}/projects/${secondEdit}/sheet`);
  await page.waitForSelector('[data-sheet-title]', { timeout: 60000 });
  await page.getByRole('button', { name: 'Save to library' }).click();
  await saveDialog().waitFor();
  await saveDialog().getByRole('button', { name: 'New version' }).click();
  await saveDialog().getByLabel('Version name').fill('check easy');
  await saveDialog().getByRole('button', { name: 'Save to library' }).click();
  await page.waitForURL(`**/library/songs/${songId}`, { timeout: 120000 });
  madeProjects.delete(secondEdit);
  await versionRows().nth(1).waitFor();
  const two = await json(`${api}/library/songs/${songId}`);
  check('Save as a new version adds a second version', two.versions.map((v) => v.name).join() === 'original,check easy');
  await shot('08-song-two-versions');

  // 7. Songs, Artists, one artist.
  await page.goto(`${base}/library/songs`);
  await page.getByRole('table').waitFor();
  await page.getByLabel('Filter').fill('check-library');
  await page.waitForTimeout(200);
  const songRows = await page.locator('tbody tr').count();
  check('Songs filters by title and artist', songRows === 1, `${songRows} rows`);
  await shot('09-songs');
  await page.getByLabel('Filter').fill('');
  await shot('09b-songs-all');
  const artistId = [...madeArtists][0];
  await page.goto(`${base}/library/artists`);
  await page.getByRole('table').waitFor();
  await shot('10-artists');
  await page.goto(`${base}/library/artists/${artistId}`);
  await page.getByRole('button', { name: 'Add a name' }).click();
  const nameDialog = page.getByRole('dialog');
  await nameDialog.getByLabel('Name').fill('check-library other name');
  await nameDialog.getByRole('button', { name: 'Add name' }).click();
  await page.getByText('check-library other name').waitFor();
  const otherRow = page.getByRole('listitem').filter({ hasText: 'check-library other name' });
  await otherRow.getByRole('button', { name: 'More actions' }).click();
  await page.getByRole('menuitem', { name: 'Make default' }).click();
  await page.getByRole('heading', { name: 'check-library other name' }).waitFor();
  const artist = await json(`${api}/library/artists/${artistId}`);
  check('an artist takes another name and makes it its default', artist.name === 'check-library other name' && artist.names.length === 2);
  await shot('11-artist');

  // 8. Narrow and dark.
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`${base}/library/songs`);
  await page.getByRole('table').waitFor();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  check('Songs at 390 px has no sideways scroll', overflow <= 0, `${overflow} px`);
  await shot('12-songs-390');
  await page.goto(`${base}/library/songs/${songId}`);
  await versionRows().first().waitFor();
  await shot('13-song-390');
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.emulateMedia({ colorScheme: 'dark' });
  await page.evaluate(() => localStorage.setItem('mui-mode', 'dark'));
  await page.reload();
  await versionRows().first().waitFor();
  await shot('14-song-dark');
  await page.evaluate(() => localStorage.removeItem('mui-mode'));
} catch (error) {
  check('the walk ended', false, error instanceof Error ? error.message : String(error));
  await shot('zz-failure').catch(() => undefined);
} finally {
  for (const songId of madeSongs) await fetch(`${api}/library/songs/${songId}`, { method: 'DELETE' });
  for (const artistId of madeArtists) await fetch(`${api}/library/artists/${artistId}`, { method: 'DELETE' });
  for (const id of madeProjects) await fetch(`${api}/projects/${id}`, { method: 'DELETE' });
  const leftSongs = (await json(`${api}/library/songs`)).filter((row) => row.title === SONG).length;
  const leftArtists = (await json(`${api}/library/artists`)).filter((row) => row.names.some((name) => name.name.startsWith('check-library'))).length;
  check('nothing the check made is left', leftSongs === 0 && leftArtists === 0, `${leftSongs} songs, ${leftArtists} artists`);
  await browser.close();
}

// The answers this walk expects: an edit of a read-only version is refused nowhere because it is
// never sent, so any 4xx here is a real problem.
const unexpected = problems.filter((line) => !/401 .*\/auth\/me/.test(line));
console.log(results.join('\n'));
if (unexpected.length) console.log(`\nProblems:\n${unexpected.slice(0, 20).join('\n')}`);
console.log(`\nScreenshots in ${out}`);
process.exit(results.some((line) => line.includes('FAIL')) || unexpected.length ? 1 : 0);
