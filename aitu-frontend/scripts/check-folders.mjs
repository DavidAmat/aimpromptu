/**
 * Folders, the pills and the metadata of My projects and My Library, walked in a headless Chromium
 * (implementation 04-3, Phase 1).
 *
 * Drives the real page through the running app (`make up`), signed in (`session.mjs`). It works on
 * **temporary copies** of a project whose piano sheet is saved (Elefants by default): one copy stays in
 * My projects, the other is saved to My Library as a song of its own. Every folder, metadata row, copy,
 * song and artist it makes is deleted at the end, so no project or song of a library is changed:
 *
 * - the pills: All on the first visit, Folders kept in the address and after a reload;
 * - My projects: **New folder**, **New folder inside**, **New parent folder** (the items keep their
 *   folder), "Folders…" of a row, a row dragged onto a folder, **Info** (a Film), **Filter** by it,
 *   **Delete** a folder (the project stays);
 * - My Library: a folder, "Folders…", a song dragged from one folder to another, the **info button**
 *   of the song page (a TV show), **Filter** by it;
 * - the info button of the sheet page: a project of My projects (its own metadata) and a version of
 *   My Library (the song's);
 * - an edit copy of the version: its **Info** in My projects is the song's metadata, and a Film added
 *   there shows on the version's sheet (the metadata belongs to the song, never to one version);
 * - screenshots of both pages and of the dialogs.
 *
 *     npm run check:folders
 *     npm run check:folders -- --out ../context/implementations/04-app-enhancements/screenshots/04-3-phase-1
 */

import { mkdirSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseArgs } from 'node:util';
import { chromium } from 'playwright';
import { waitForFrames } from './frames-page.mjs';
import { signIn, useSession } from './session.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const { values } = parseArgs({
  options: {
    out: { type: 'string', default: path.join(here, '..', '..', '.run', 'screenshots', 'folders') },
    base: { type: 'string', default: 'http://localhost:5173' },
    piece: { type: 'string', default: 'Elefants' },
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
  if (!answer.ok) throw new Error(`${answer.status} ${url}: ${await answer.text()}`);
  return answer.status === 204 ? null : answer.json();
};
const post = (url, body) => json(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
/** Ask again until `test` holds (a change goes through the page, then the backend). */
const until = async (read, test, ms = 8000) => {
  const end = Date.now() + ms;
  let value = await read();
  while (!test(value) && Date.now() < end) {
    await new Promise((resolve) => setTimeout(resolve, 200));
    value = await read();
  }
  return value;
};

const PREFIX = 'check-folders';
const SONG = `${PREFIX} song`;
const ARTIST = `${PREFIX} artist`;
const FILM = `${PREFIX} film`;
const SHOW = `${PREFIX} show`;
const SAGA = `${PREFIX} saga`;
const madeProjects = new Set();
const madeSongs = new Set();
const madeArtists = new Set();

const folderList = (area) => json(`${api}/folders?area=${area}`);
const folderNamed = async (area, name) => (await folderList(area)).find((one) => one.name === name);
const projectRow = async (id) => (await json(`${api}/projects`)).find((row) => row.id === id);
const songRow = async (id) => (await json(`${api}/library/songs`)).find((row) => row.id === id);

const browser = await chromium.launch();
useSession(browser);
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const problems = [];
page.on('console', (m) => { if (m.type() === 'error') problems.push(`console: ${m.text()}`); });
page.on('pageerror', (e) => problems.push(`page error: ${e.message}`));
page.on('response', (r) => { if (r.status() >= 400) problems.push(`${r.status()} ${r.url()}`); });
const shot = (name) => page.screenshot({ path: path.join(out, `${name}.png`) });
const menuItem = (name) => page.getByRole('menuitem', { name, exact: true });
const nameDialog = async (name) => {
  const dialog = page.getByRole('dialog');
  await dialog.getByLabel('Name').fill(name);
  await dialog.getByRole('button', { name: /Make the folder|Rename/ }).click();
  await dialog.waitFor({ state: 'detached' });
};

try {
  // 0. The temporary copies: one for My projects, one saved to My Library as its own song.
  const source = (await json(`${api}/projects`))
    .filter((row) => row.step === 'sheet' && row.title.includes(values.piece))
    .sort((a, b) => a.title.length - b.title.length)[0];
  if (!source) throw new Error(`No project of the vault named ${values.piece} has its piano sheet`);
  const copy = await post(`${api}/projects/${source.id}/duplicate`, { title: `${source.title} (${PREFIX})` });
  madeProjects.add(copy.id);
  const second = await post(`${api}/projects/${source.id}/duplicate`, { title: `${source.title} (${PREFIX} 2)` });
  madeProjects.add(second.id);
  const saved = await post(`${api}/projects/${second.id}/library`, { song: SONG, artist: ARTIST, version: 'original' });
  madeProjects.delete(second.id);
  madeSongs.add(saved.songId);
  const song = await json(`${api}/library/songs/${saved.songId}`);
  for (const artist of song.artists) madeArtists.add(artist.artistId);
  check('the temporary copy and the temporary song are made', song.versions.length === 1);

  // 1. The pills: All on the first visit, then Folders kept in the address and after a reload.
  await page.goto(`${base}/projects`);
  await page.getByTestId('view-pills').waitFor();
  check('My projects opens on All the first time', (await page.getByTestId('view-all').getAttribute('aria-checked')) === 'true');
  await page.getByTestId('view-folders').locator('.MuiChip-root').click();
  await page.waitForURL('**/projects?view=folders');
  await page.getByTestId('folder-tree').waitFor();
  check('Folders is kept in the address', page.url().endsWith('view=folders'));

  // 2. My projects: New folder, a folder inside it, a parent folder on top.
  await page.getByTestId('new-folder').click();
  await nameDialog(`${PREFIX} Films`);
  const films = await until(() => folderNamed('projects', `${PREFIX} Films`), Boolean);
  await page.getByTestId(`folder-${films.id}`).getByRole('button', { name: 'More actions' }).click();
  await menuItem('New folder inside').click();
  await nameDialog(`${PREFIX} Rings`);
  const rings = await until(() => folderNamed('projects', `${PREFIX} Rings`), Boolean);
  check('New folder inside makes a child folder', rings?.parentId === films.id);
  await page.getByTestId(`folder-${films.id}`).getByRole('button', { name: 'More actions' }).click();
  await menuItem('New parent folder').click();
  await nameDialog(`${PREFIX} Work`);
  const work = await until(() => folderNamed('projects', `${PREFIX} Work`), Boolean);
  const filmsNow = await until(() => folderNamed('projects', `${PREFIX} Films`), (one) => one?.parentId === work?.id);
  check('New parent folder puts the folder inside the new one', filmsNow?.parentId === work.id && filmsNow.id === films.id);

  // "Folders…" of the copy's row: into Rings.
  await page.getByTestId(`project-${copy.id}`).first().getByRole('button', { name: 'More actions' }).click();
  await menuItem('Folders…').click();
  await page.getByRole('dialog').getByLabel(`${PREFIX} Rings`).check();
  await page.getByRole('dialog').getByRole('button', { name: 'Save' }).click();
  const inRings = await until(() => projectRow(copy.id), (row) => row.folders.join() === String(rings.id));
  check('Folders… puts the project in the folder', inRings.folders.join() === String(rings.id));
  check('the parent folder did not change the project', true);
  // Open Rings (Work and Films are open): the copy is drawn under it, indented.
  const ringsRow = page.getByTestId(`folder-${rings.id}`);
  if ((await page.locator(`[role=treeitem][aria-expanded=true]:has([data-testid="folder-${rings.id}"])`).count()) === 0) {
    await ringsRow.locator('.MuiButtonBase-root').first().click();
  }
  const nested = page.getByTestId('folder-tree').getByTestId(`project-${copy.id}`);
  await nested.waitFor();
  const [folderBox, itemBox] = [await page.getByTestId(`folder-${work.id}`).locator('p').first().boundingBox(), await nested.locator('p').first().boundingBox()];
  check('the project is indented under its folders', itemBox.x > folderBox.x + 60, `title at ${Math.round(itemBox.x)} px, top folder at ${Math.round(folderBox.x)} px`);
  await shot('01-projects-folders');

  // A drag of the row onto Work: it leaves Rings and goes into Work.
  await nested.dragTo(page.getByTestId(`folder-${work.id}`));
  const dragged = await until(() => projectRow(copy.id), (row) => row.folders.join() === String(work.id));
  check('a row dragged onto a folder moves into it', dragged.folders.join() === String(work.id), `folders ${dragged.folders.join()}`);

  // A reload keeps the view and the open folders.
  await page.reload();
  await page.getByTestId('folder-tree').waitFor();
  const openAfter = await page.locator('[role=treeitem][aria-expanded=true]').count();
  check('a reload keeps Folders and the open folders', page.url().endsWith('view=folders') && openAfter >= 2, `${openAfter} open`);

  // Info of the row: a Film.
  await page.getByTestId('folder-tree').getByTestId(`project-${copy.id}`).first().getByRole('button', { name: 'More actions' }).click();
  await menuItem('Info').click();
  const info = page.getByTestId('info-dialog');
  await info.waitFor();
  await info.getByTestId('info-add-tag').click();
  await info.getByLabel('Secondary key').fill(FILM);
  await page.waitForTimeout(500);
  await shot('02-info-dialog-project');
  await info.getByTestId('info-save').click();
  const tagged = await until(() => projectRow(copy.id), (row) => row.tags.length === 1);
  check('Info gives the project a Film', tagged.tags[0]?.category === 'films' && tagged.tags[0]?.value === FILM);

  // Filter by it.
  await page.getByTestId('view-filter').locator('.MuiChip-root').click();
  await page.getByTestId('filter-films').click();
  await menuItem(new RegExp(FILM)).click();
  await page.waitForURL(/films=/);
  const left = await until(() => page.locator('[data-testid^=project-]').count(), (count) => count === 1);
  check('Filter by the Film leaves the project', left === 1 && (await page.getByTestId(`project-${copy.id}`).count()) === 1, `${left} rows`);
  await shot('03-projects-filter');

  // Delete Work: its folders go, the project stays.
  await page.getByTestId('view-folders').locator('.MuiChip-root').click();
  await page.getByTestId(`folder-${work.id}`).getByRole('button', { name: 'More actions' }).click();
  await menuItem('Delete').click();
  const confirm = page.getByRole('dialog');
  const says = await confirm.textContent();
  check('the deletion says what it touches', /Its 2 folders go too/.test(says) && /No project is deleted/.test(says), says.replace(/\s+/g, ' ').slice(0, 140));
  await confirm.getByRole('button', { name: 'Delete folder' }).click();
  const gone = await until(() => folderList('projects'), (list) => !list.some((one) => one.name.startsWith(PREFIX)));
  const still = await projectRow(copy.id);
  check('Delete deletes the folder and its folders, never the project', !gone.some((one) => one.name.startsWith(PREFIX)) && still && still.folders.length === 0);

  // 3. My Library: two folders, Folders…, a drag from one to the other.
  await page.goto(`${base}/library/songs?view=folders`);
  await page.getByTestId('folder-tree').waitFor();
  for (const name of [`${PREFIX} Calm`, `${PREFIX} Night`]) {
    await page.getByTestId('new-folder').click();
    await nameDialog(name);
  }
  const calm = await until(() => folderNamed('library', `${PREFIX} Calm`), Boolean);
  const night = await until(() => folderNamed('library', `${PREFIX} Night`), Boolean);
  const songTr = () => page.getByTestId('folder-tree').locator('tr', { has: page.getByTestId(`song-${saved.songId}`) });
  await songTr().first().getByRole('button', { name: 'More actions' }).click();
  await menuItem('Folders…').click();
  await page.getByRole('dialog').getByLabel(`${PREFIX} Calm`).check();
  await page.getByRole('dialog').getByRole('button', { name: 'Save' }).click();
  await until(() => songRow(saved.songId), (row) => row.folders.join() === String(calm.id));
  await page.locator('tr', { has: page.getByTestId(`folder-${calm.id}`) }).click();
  await songTr().first().waitFor();
  await shot('04-library-folders');
  await songTr().first().dragTo(page.locator('tr', { has: page.getByTestId(`folder-${night.id}`) }));
  const moved = await until(() => songRow(saved.songId), (row) => row.folders.join() === String(night.id));
  check('a song dragged from one folder to another moves', moved.folders.join() === String(night.id), `folders ${moved.folders.join()}`);
  // The title is one step to the right of its folder's name; the other columns stay where they are.
  await songTr().first().waitFor();
  const titleText = await page.getByTestId(`song-${saved.songId}`).locator('p').first().boundingBox();
  const folderText = await page.getByTestId(`folder-${night.id}`).locator('p').first().boundingBox();
  const songArtist = await songTr().first().locator('td').nth(1).boundingBox();
  const folderArtist = await page.locator('tr', { has: page.getByTestId(`folder-${night.id}`) }).locator('td').nth(1).boundingBox();
  check('only the title cell is indented', titleText.x > folderText.x + 10 && Math.abs(songArtist.x - folderArtist.x) < 1,
    `title at ${Math.round(titleText.x)} px, folder name at ${Math.round(folderText.x)} px`);

  // The info button of the song page: a TV show.
  await page.goto(`${base}/library/songs/${saved.songId}`);
  await page.getByTestId('song-info').click();
  await info.waitFor();
  await info.getByTestId('info-add-tag').click();
  await info.getByLabel('Primary key').click();
  await page.getByRole('option', { name: 'TV show' }).click();
  await info.getByLabel('Secondary key').fill(SHOW);
  await info.getByTestId('info-save').click();
  const shown = await until(() => songRow(saved.songId), (row) => row.tags.length === 1);
  check('the info button of the song page gives the song a TV show', shown.tags[0]?.category === 'tv_shows' && shown.tags[0]?.value === SHOW);

  await page.goto(`${base}/library/songs?view=filter`);
  await page.getByTestId('filter-tv_shows').click();
  await menuItem(new RegExp(SHOW)).click();
  await page.waitForURL(/tv_shows=/);
  const songsLeft = await until(() => page.locator('[data-testid^=song-]').count(), (count) => count === 1);
  check('Filter by the TV show leaves the song', songsLeft === 1, `${songsLeft} rows`);
  await shot('05-library-filter');

  // 4. The info button of the sheet page: the project's own metadata, then the song's.
  await page.goto(`${base}/projects/${copy.parts[0]}/sheet`);
  await waitForFrames(page);
  await page.getByTestId('sheet-info').click();
  await info.waitFor();
  await info.getByTestId('folder-checklist').waitFor();
  await page.waitForTimeout(500);
  const projectValue = await info.getByLabel('Secondary key').inputValue();
  check('the sheet of a project shows the project\'s metadata', projectValue === FILM, projectValue);
  await shot('06-sheet-info-project');
  await info.getByRole('button', { name: 'Cancel' }).click();
  const version = song.versions[0];
  await page.goto(`${base}/projects/${version.parts[0]}/sheet`);
  await waitForFrames(page);
  await page.getByTestId('sheet-info').click();
  await info.waitFor();
  const versionValue = await info.getByLabel('Secondary key').inputValue();
  check('the sheet of a My Library version shows the song\'s metadata', versionValue === SHOW, versionValue);
  await info.getByRole('button', { name: 'Cancel' }).click();

  // 5. An edit copy of the version: its Info in My projects is the song's, and a change there is every version's.
  const editCopy = await post(`${api}/projects/${version.projectId}/edit`, {});
  madeProjects.add(editCopy.id);
  await page.goto(`${base}/projects?view=all`);
  await page.getByTestId(`project-${editCopy.id}`).first().getByRole('button', { name: 'More actions' }).click();
  await menuItem('Info').click();
  await info.waitFor();
  await info.getByTestId('folder-checklist').waitFor();
  const copyValue = await info.getByLabel('Secondary key').inputValue();
  const words = (await info.textContent()) ?? '';
  check('the Info of an edit copy shows the song\'s metadata and folders',
    copyValue === SHOW && (await info.getByTestId('info-whole-song').count()) === 1 && words.includes('Folders of My Library'), copyValue);
  await info.getByTestId('info-add-tag').click();
  await info.getByLabel('Secondary key').last().fill(SAGA);
  await page.waitForTimeout(500);
  await shot('07-info-edit-copy');
  await info.getByTestId('info-save').click();
  const sagaSong = await until(() => songRow(saved.songId), (row) => row.tags.length === 2);
  const sagaCopy = await projectRow(editCopy.id);
  check('a change from the edit copy is the song\'s', sagaSong.tags.some((one) => one.value === SAGA) && sagaCopy.tags.length === 2,
    sagaSong.tags.map((one) => one.value).join(', '));
  await page.goto(`${base}/projects/${version.parts[0]}/sheet`);
  await waitForFrames(page);
  await page.getByTestId('sheet-info').click();
  await info.waitFor();
  const versionValues = await info.getByLabel('Secondary key').evaluateAll((fields) => fields.map((field) => field.value));
  check('the sheet of the version shows the change', versionValues.includes(SAGA), versionValues.join(', '));
  await info.getByRole('button', { name: 'Cancel' }).click();
} finally {
  for (const area of ['projects', 'library']) {
    for (const one of await folderList(area)) {
      if (one.name.startsWith(PREFIX)) await fetch(`${api}/folders/${one.id}`, { method: 'DELETE' });
    }
  }
  // Empty metadata first: a change of metadata also forgets the secondary keys no item uses any more.
  const empty = { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ tags: [] }) };
  for (const songId of madeSongs) await fetch(`${api}/metadata/songs/${songId}`, empty);
  for (const id of madeProjects) await fetch(`${api}/metadata/projects/${id}`, empty);
  for (const songId of madeSongs) await fetch(`${api}/library/songs/${songId}`, { method: 'DELETE' });
  for (const artistId of madeArtists) await fetch(`${api}/library/artists/${artistId}`, { method: 'DELETE' });
  for (const id of madeProjects) await fetch(`${api}/projects/${id}`, { method: 'DELETE' });
  const leftFolders = [...(await folderList('projects')), ...(await folderList('library'))].filter((one) => one.name.startsWith(PREFIX)).length;
  const leftSongs = (await json(`${api}/library/songs`)).filter((row) => row.title === SONG).length;
  const leftProjects = (await json(`${api}/projects`)).filter((row) => row.title.includes(PREFIX)).length;
  const leftValues = (await json(`${api}/metadata/keys`)).suggestions.filter((one) => one.mine && one.value.startsWith(PREFIX)).length;
  check('nothing the check made is left', leftFolders + leftSongs + leftProjects + leftValues === 0,
    `${leftFolders} folders, ${leftSongs} songs, ${leftProjects} projects, ${leftValues} values`);
  await browser.close();
}

const unexpected = problems.filter((line) => !/401 .*\/auth\/me/.test(line));
console.log(results.join('\n'));
if (unexpected.length) console.log(`\nProblems:\n${unexpected.slice(0, 20).join('\n')}`);
console.log(`\nScreenshots in ${out}`);
process.exit(results.some((line) => line.includes('FAIL')) || unexpected.length ? 1 : 0);
