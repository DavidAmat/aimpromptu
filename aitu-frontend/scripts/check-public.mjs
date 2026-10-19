/**
 * The Public Library (implementation 02, Phase 13, plan sections 15.1 to 15.3), walked in a headless
 * Chromium through the running app (`make up`), signed in as the master user (`session.mjs`).
 *
 * Public versions arrive by accepted requests (Phase 14), so the check makes its own, on **copies**
 * only: a duplicate of a version of My library (`--name`, "7 Years" by default) is placed as the
 * Hard version and as a user version of the public song "Stayin' Alive" (Bee Gees), a song the
 * master user's library does not have (`aitu_backend.library.public_fixture`, run on the host). At
 * the end everything it made is deleted: the pulled song and artist, the playlist, the public
 * versions, the copies. No song of the library is changed.
 *
 * 1. Public songs: the count, a search, the Decade chip (the popularity of that decade), a sort;
 *    the Region chip (Phase 16): spain and catalan, each with its own popularity, a Spanish song
 *    on several charts, a song known from number ones only.
 * 2. One song: byline, facts, the chart line, the versions, a like, the lyrics, Play.
 * 3. Add to my library: the dialog, the song in My library with its link back; a song with no
 *    version cannot be added.
 * 4. The artist (Add to my library adds nothing new), the artists list, a public playlist (Play,
 *    Add to my library), Search (⌘K), Save to library with a public song.
 * 5. 390 px and dark.
 *
 *     npm run check:public
 *     npm run check:public -- --name "7 Years" --out /tmp/public
 */

import { execFileSync } from 'node:child_process';
import { existsSync, mkdirSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseArgs } from 'node:util';
import { chromium } from 'playwright';
import { signIn, useSession } from './session.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const repository = path.join(here, '..', '..');
const { values } = parseArgs({
  options: {
    out: { type: 'string', default: path.join(repository, '.run', 'screenshots', 'public') },
    base: { type: 'string', default: 'http://localhost:5173' },
    name: { type: 'string', default: '7 Years' },
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

/** The fixture command, on the host, on the database of `.env`. */
function fixture(...args) {
  const env = { ...process.env };
  const dotEnv = path.join(repository, '.env');
  if (existsSync(dotEnv)) {
    const found = /^AITU_DATABASE_DIR=(.*)$/m.exec(readFileSync(dotEnv, 'utf8'));
    if (found) env.AITU_DATABASE_DIR = found[1].trim();
  }
  return execFileSync('uv', ['run', '--no-sync', 'python', '-m', 'aitu_backend.library.public_fixture', ...args], {
    cwd: path.join(repository, 'aitu-backend'),
    env,
    encoding: 'utf8',
  }).trim();
}

const copies = new Set();
const publicProjects = new Set();
const publicPlaylists = new Set();
const songs = new Set();
const playlists = new Set();
let pulledArtist = null;

const browser = await chromium.launch({ args: ['--autoplay-policy=no-user-gesture-required'] });
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
const until = async (test, ms = 10000) => {
  const end = Date.now() + ms;
  while (Date.now() < end) {
    if (await test()) return true;
    await page.waitForTimeout(150);
  }
  return false;
};
const rowTitles = () => page.locator('tbody tr td:nth-child(1)').allInnerTexts();

try {
  // The song the check works on, and that the library does not have it.
  const alive = (await json(`${api}/public/suggest?q=stayin%20alive&artist=bee%20gees`)).songs[0];
  if (!alive || alive.title !== "Stayin' Alive") throw new Error("The Public Library has no Stayin' Alive");
  const mine = await json(`${api}/library/songs`);
  if (mine.some((song) => song.title.toLowerCase().includes('stayin'))) throw new Error("My library already has Stayin' Alive: the check would change it");
  const myArtists = await json(`${api}/library/artists`);
  if (myArtists.some((artist) => artist.name.toLowerCase() === 'bee gees')) throw new Error('My library already has the Bee Gees: the check would change them');

  const source = mine.filter((song) => song.title.toLowerCase().includes(values.name.toLowerCase())).sort((a, b) => a.title.length - b.title.length)[0];
  if (!source) throw new Error(`My library has no song named ${values.name}`);
  const version = (await json(`${api}/library/songs/${source.id}`)).versions[0];
  const copy = await send('POST', `${api}/projects/${version.projectId}/duplicate`, { title: `${source.title} (check-public)` });
  copies.add(copy.id);
  const hard = fixture('place', '--project', copy.id, '--song', String(alive.id), '--name', 'hard');
  publicProjects.add(hard);
  const easy = fixture('place', '--project', copy.id, '--song', String(alive.id), '--name', 'easy', '--user-version');
  publicProjects.add(easy);
  check('two public versions placed from a copy', hard.length === 36 && easy.length === 36);

  // 1. Public songs.
  await page.goto(`${base}/public/songs`);
  await page.getByTestId('public-total').waitFor({ timeout: 20000 });
  const total = Number((await page.getByTestId('public-total').innerText()).replace(/[^0-9]/g, ''));
  check('Public songs lists the whole library', total > 9000, `${total} songs`);
  check('the first song is the most popular', (await rowTitles())[0]?.length > 0);
  check('the sidebar has Public library', await page.getByRole('link', { name: 'Songs' }).nth(1).isVisible());
  await shot('01-public-songs');

  await page.getByTestId('public-search').fill('bee gees');
  check('a search finds the artist\'s songs', await until(async () => (await rowTitles()).includes("Stayin' Alive")));
  check('the search is kept in the address', page.url().includes('q=bee+gees'));
  await page.getByTestId('filter-decade').click();
  await page.getByRole('menuitem', { name: /^70s/ }).click();
  check('the Decade chip filters, and the column is the decade\'s popularity', await until(async () => (await page.locator('thead').innerText()).replace(/\s+/g, ' ').includes('Popularity in the 70s')));
  await shot('02-search-and-decade');
  await page.getByRole('button', { name: 'Year' }).click();
  check('the Year header sorts', await until(async () => page.url().includes('sort=year')));
  await page.getByTestId('public-search').fill('');
  await page.getByRole('button', { name: /Decade: 70s/ }).locator('svg').last().click();
  check('the chip takes its filter off', await until(async () => !page.url().includes('decade')));

  // 1b. The regions (Phase 16): the Region chip, a region's popularity, a song on several charts.
  const spain = await json(`${api}/public/songs?region=spain&limit=50`);
  const regionCodes = spain.facets.regions.map((one) => one.value);
  check('the Region chip offers spain and catalan', regionCodes.includes('spain') && regionCodes.includes('catalan'), regionCodes.join(', '));
  check('spain has its songs', spain.total > 10000, `${spain.total} songs`);
  const spainValues = spain.rows.map((row) => row.popularity);
  check('spain is sorted by its own popularity', spainValues.every((v, i) => i === 0 || spainValues[i - 1] >= v) && spainValues[0] > 90);
  await page.goto(`${base}/public/songs`);
  await page.getByTestId('public-total').waitFor();
  await page.getByTestId('filter-region').click();
  await page.getByRole('menuitem', { name: /^Spain/ }).click();
  check('the column is the popularity in Spain', await until(async () => (await page.locator('thead').innerText()).replace(/\s+/g, ' ').includes('Popularity in Spain')));
  await shot('02b-region-spain');
  await page.getByTestId('filter-decade').click();
  await page.getByRole('menuitem', { name: /^70s/ }).click();
  check('Spain in the 70s', await until(async () => (await page.locator('thead').innerText()).replace(/\s+/g, ' ').includes('Popularity in Spain in the 70s')));
  await shot('02c-region-spain-70s');
  await page.goto(`${base}/public/songs?region=catalan`);
  check('the popularity in Catalan', await until(async () => (await page.locator('thead').innerText()).replace(/\s+/g, ' ').includes('Popularity in Catalan')));
  await shot('02d-region-catalan');
  const star = (await json(`${api}/public/songs?q=superestrella%20aitana`)).rows[0];
  await page.goto(`${base}/public/songs/${star.id}`);
  await page.getByTestId('public-byline').waitFor();
  check('a Spanish song shows its popularity in Spain', await until(async () => (await page.getByText('Popularity in Spain').count()) === 1));
  check('and every chart it was on, named', (await page.getByTestId('chart-history').count()) >= 2 && (await page.getByText('On the charts').count()) === 1);
  await shot('03b-spanish-song');
  const bravos = (await json(`${api}/public/songs?q=black%20is%20black%20bravos`)).rows[0];
  await page.goto(`${base}/public/songs/${bravos.id}`);
  await page.getByTestId('public-byline').waitFor();
  check('a song known from number ones only says so', await until(async () => (await page.getByText('Weeks at number 1').count()) >= 1 && (await page.getByText(/≈ \d/).count()) >= 1));
  await shot('03c-number-ones-song');
  // Phase 17: a song no chart of the region lists has a popularity inferred from YouTube views.
  const horitzo = (await json(`${api}/public/songs?q=agafant%20horitzo&region=catalan`)).rows[0];
  check('a Catalan song on no chart has an inferred popularity', horitzo !== undefined && horitzo.popularity > 0, horitzo && `${horitzo.title}: ${horitzo.popularity}`);
  if (horitzo) {
    // With no region, the song has no worldwide value ("–") and its Catalan one in its own column.
    await page.goto(`${base}/public/songs?q=agafant%20horitzo`);
    const listRow = page.locator('tbody tr').first();
    check('with no region, a song with no worldwide value shows "–" and its value by region', await until(async () => {
      const text = (await listRow.innerText()).replace(/\s+/g, ' ');
      return text.includes('–') && /Catalan ≈ \d+\.\d/.test(text);
    }), (await listRow.innerText()).replace(/\s+/g, ' '));
    check('the column says what it is', (await page.locator('thead').innerText()).replace(/\s+/g, ' ').includes('Popularity by region'));
    await shot('02e-by-region-column');
    // The whole list, with its longest titles and credits: the six columns fit at 1440 px.
    await page.goto(`${base}/public/songs?per=100`);
    await page.locator('tbody tr').nth(20).waitFor();
    check('the six columns fit the page', await page.evaluate(() => {
      const box = document.querySelector('table')?.parentElement;
      return box !== null && box !== undefined && box.scrollWidth <= box.clientWidth + 1;
    }));
    await shot('02f-by-region-wide');
    await page.goto(`${base}/public/songs/${horitzo.id}`);
    await page.getByTestId('public-byline').waitFor();
    const inferredFact = page.locator('[title^="Inferred from YouTube views"]');
    check('its page shows it with ≈ and says why on hover', await until(async () => (await inferredFact.count()) === 1 && /^≈ \d/.test((await inferredFact.innerText()).trim())));
    await shot('03d-inferred-song');
  }

  // 2. One song.
  await page.goto(`${base}/public/songs/${alive.id}`);
  await page.getByTestId('public-byline').waitFor();
  check('the song has its byline', (await page.getByTestId('public-byline').innerText()).includes('Bee Gees'));
  check('the chart line is drawn', (await page.getByTestId('chart-history').count()) >= 1);
  const versionRows = page.getByTestId('public-version');
  check('a fixed version and a user version', (await versionRows.count()) === 2);
  check('Hard is the Default, by master', (await versionRows.first().innerText()).includes('Default') && (await versionRows.first().innerText()).includes('by master'));
  await versionRows.first().getByTestId('like').click();
  check('a like counts once', await until(async () => (await versionRows.first().getByTestId('like').innerText()).trim() === '1'));
  await shot('03-public-song');
  await versionRows.first().getByTestId('like').click();
  check('the like is taken back', await until(async () => (await versionRows.first().getByTestId('like').innerText()).trim() === '0'));
  await page.getByTestId('show-lyrics').click();
  check('the lyrics show', await until(async () => (await page.getByTestId('lyrics').count()) === 1 && (await page.getByTestId('lyrics').innerText()).length > 50));
  await shot('04-public-song-lyrics');
  await page.getByTestId('public-play').click();
  await page.waitForURL('**/play/**');
  check('Play opens Play mode on the public version', await until(async () => (await page.locator('[data-play-page] .grid-note-target').count()) > 0, 90000));
  await shot('05-play-public-version');
  await page.getByTestId('play-close').click();
  await page.waitForURL(`**/public/songs/${alive.id}`);

  // 3. Add to my library.
  await page.getByTestId('add-to-library').click();
  await page.getByRole('dialog').waitFor();
  check('the dialog ticks the Default version', await page.getByRole('checkbox', { name: 'Hard' }).isChecked());
  await shot('06-add-dialog');
  await page.getByTestId('add-confirm').click();
  await page.getByTestId('open-mine').waitFor({ timeout: 20000 });
  const detail = await json(`${api}/public/songs/${alive.id}`);
  songs.add(detail.inLibrary);
  check('the song is in My library', detail.inLibrary !== null);
  await shot('07-added');
  await page.getByTestId('open-mine').click();
  await page.waitForURL(`**/library/songs/${detail.inLibrary}`);
  check('My library has the version hard', await until(async () => (await page.getByText('hard', { exact: true }).count()) > 0));
  check('My library\'s song links back', (await page.getByTestId('song-public-link').count()) === 1);
  const myArtist = (await json(`${api}/library/artists`)).find((artist) => artist.name === 'Bee Gees');
  pulledArtist = myArtist?.id ?? null;
  check('the artist came too', pulledArtist !== null);
  await shot('08-in-my-library');

  const billie = (await json(`${api}/public/suggest?q=billie%20jean&artist=michael%20jackson`)).songs[0];
  await page.goto(`${base}/public/songs/${billie.id}`);
  await page.getByTestId('public-byline').waitFor();
  check('a song with no version cannot be added', await page.getByTestId('add-to-library').isDisabled());
  check('it says no version yet', (await page.getByText('No version yet.').count()) === 1);
  await shot('09-no-version');

  // 4. The artist, the artists, a playlist, Search, Save to library.
  await page.goto(`${base}/public/artists/${alive.artists[0].artistId}`);
  await page.getByTestId('add-artist').waitFor();
  check('the artist\'s songs are listed by popularity', (await page.locator('tbody tr').count()) > 5);
  await page.getByTestId('add-artist').click();
  check('Add to my library on the artist adds nothing new', await until(async () => (await page.getByText('already in My library').count()) === 1));
  await shot('10-public-artist');
  await page.goto(`${base}/public/artists?q=jackson`);
  check('the artists list searches', await until(async () => (await rowTitles()).includes('Michael Jackson')));
  await shot('11-public-artists');

  const playlistId = Number(fixture('playlist', '--title', 'Check public playlist', '--item', `${alive.id}:${easy}`, '--item', String(billie.id)));
  publicPlaylists.add(playlistId);
  await page.goto(`${base}/public/playlists`);
  check('the public playlist is listed', await until(async () => (await page.getByText('Check public playlist').count()) === 1));
  await page.getByText('Check public playlist').click();
  check('its songs, one with no version', await until(async () => (await page.getByText('No version').count()) === 1));
  await shot('12-public-playlist');
  await page.getByRole('button', { name: 'Add to my library', exact: true }).click();
  await page.getByRole('button', { name: 'Open', exact: true }).waitFor({ timeout: 20000 });
  const myPlaylists = await json(`${api}/playlists`);
  const pulledPlaylist = myPlaylists.find((one) => one.title === 'Check public playlist');
  if (pulledPlaylist) playlists.add(pulledPlaylist.id);
  check('the playlist is in My library', pulledPlaylist !== undefined);
  await page.getByRole('button', { name: 'Play', exact: true }).click();
  await page.waitForURL('**/play/playlist/**');
  check('Play mode plays the public playlist', await until(async () => (await page.locator('[data-play-page] .grid-note-target').count()) > 0, 90000));
  await page.getByTestId('play-close').click();
  check('Close comes back to the public playlist', await until(async () => page.url().includes(`/public/playlists/${playlistId}`)));

  await page.goto(`${base}/projects`);
  await page.getByRole('heading', { name: 'Projects' }).waitFor();
  await page.keyboard.press('Control+k');
  await page.getByRole('dialog').getByRole('textbox').fill('blinding lights');
  check('Search finds a public song', await until(async () => (await page.getByRole('dialog').getByText('Public library').count()) > 0));
  await shot('13-search');
  await page.keyboard.press('Escape');

  const saveCopy = await send('POST', `${api}/projects/${version.projectId}/duplicate`, { title: `${source.title} (check-public save)` });
  copies.add(saveCopy.id);
  await page.goto(`${base}/projects/${saveCopy.parts?.[0] ?? saveCopy.id}/sheet`);
  await page.getByRole('button', { name: 'Save to library' }).click({ timeout: 60000 });
  const dialog = page.getByRole('dialog');
  await dialog.getByLabel('Artist').fill('');
  await dialog.getByLabel('Song').fill('stayin aliv');
  check('the Song field suggests the public song', await until(async () => (await page.getByRole('option', { name: /Stayin' Alive/ }).count()) > 0));
  await shot('14-save-public-suggestion');
  await page.getByRole('option', { name: /Stayin' Alive/ }).first().click();
  check('the field says it is from the Public Library', (await dialog.getByText('From the Public Library').count()) === 1);
  await dialog.getByLabel('Version name').fill('check');
  await dialog.getByRole('button', { name: 'Save to library' }).click();
  await page.waitForURL('**/library/songs/**', { timeout: 60000 });
  copies.delete(saveCopy.id);
  check('saved on the same song of My library', page.url().endsWith(`/library/songs/${detail.inLibrary}`));

  // 5. 390 px and dark.
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`${base}/public/songs/${alive.id}`);
  await page.getByTestId('public-byline').waitFor();
  check('390 px: no sideways scroll', await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1));
  await shot('15-narrow-song');
  await page.goto(`${base}/public/songs`);
  await page.getByTestId('public-total').waitFor();
  await shot('16-narrow-songs');
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.emulateMedia({ colorScheme: 'dark' });
  await page.evaluate(() => localStorage.setItem('mui-mode', 'dark'));
  await page.goto(`${base}/public/songs/${alive.id}`);
  await page.getByTestId('chart-history').first().waitFor();
  await shot('17-dark-song');
  await page.evaluate(() => localStorage.removeItem('mui-mode'));
} catch (error) {
  check('the walk finished', false, error instanceof Error ? error.message : String(error));
  await shot('error').catch(() => undefined);
} finally {
  for (const id of playlists) await fetch(`${api}/playlists/${id}`, { method: 'DELETE' });
  for (const id of songs) await fetch(`${api}/library/songs/${id}`, { method: 'DELETE' });
  if (pulledArtist !== null) await fetch(`${api}/library/artists/${pulledArtist}`, { method: 'DELETE' });
  for (const id of publicPlaylists) fixture('remove-playlist', '--id', String(id));
  for (const id of publicProjects) fixture('remove', '--project', id);
  for (const id of copies) await fetch(`${api}/projects/${id}`, { method: 'DELETE' });
  await browser.close();
}

const left = (await json(`${api}/library/songs`)).filter((song) => song.title.toLowerCase().includes('stayin'));
check('nothing left behind', left.length === 0 && (await json(`${api}/public/songs/${(await json(`${api}/public/suggest?q=stayin%20alive&artist=bee%20gees`)).songs[0].id}`)).fixed.length === 0);
const unexpected = problems.filter((line) => !line.includes('/public/songs/') || !line.startsWith('409'));
console.log(results.join('\n'));
if (unexpected.length) console.log(`\nproblems:\n  ${unexpected.join('\n  ')}`);
console.log(`\nscreenshots: ${out}`);
process.exit(results.some((line) => line.includes('FAIL')) || unexpected.length ? 1 : 0);
