/**
 * The whole journey of the app, timed (implementation 02, Phase 15, plan section 20), walked in
 * three headless Chromium windows through the running app (`make up`):
 *
 * - **the author**, a temporary user the check makes (`journey-a-<time>`);
 * - **the master user**, who reviews;
 * - **the reader**, a second temporary user (`journey-b-<time>`).
 *
 * Nothing of a real library changes: the project comes from a YouTube link, the song and the artist
 * it proposes are new (named with the time), and at the end `aitu_backend.library.public_fixture`
 * removes the two users with everything they made, then the public song and artist.
 *
 * 1. The author: **New project**, a YouTube link, **Download the audio**; **Transcribe**, followed
 *    live; **Predict hands**, Save; the Sheet step, Save; **Save to library**.
 * 2. The author: **Publish** the version, **Propose this song** (a new song, a new artist).
 * 3. The master user: **Review**, every item accepted.
 * 4. The reader: the song on Public songs, **Add to my library**; **Play** in Play mode, playing.
 * 5. The reader: **From other projects** with the pulled version, **Save as song**.
 *
 * Each step is timed from the press of its button to its result on screen.
 *
 *     npm run check:journey
 *     npm run check:journey -- --youtube <url> --out /tmp/journey --json /tmp/journey.json
 */

import { execFileSync } from 'node:child_process';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseArgs } from 'node:util';
import { chromium } from 'playwright';
import { signIn, useSession } from './session.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const repository = path.join(here, '..', '..');
const { values } = parseArgs({
  options: {
    out: { type: 'string', default: path.join(repository, '.run', 'screenshots', 'journey') },
    json: { type: 'string' },
    base: { type: 'string', default: 'http://localhost:5173' },
    // Yann Tiersen, "Comptine d'un autre été, l'après-midi", 2:21, solo piano (as `time:flow`).
    youtube: { type: 'string', default: 'https://www.youtube.com/watch?v=znfYwABeSZ0' },
  },
});
const base = values.base;
const api = `${base}/api`;
const rawFetch = globalThis.fetch;
await signIn(base);
const out = path.resolve(values.out);
mkdirSync(out, { recursive: true });

const results = [];
const check = (label, ok, extra = '') => {
  results.push(`${ok ? '  ok  ' : '  FAIL'} ${label}${extra ? ` (${extra})` : ''}`);
};
const timings = [];
/** Time one step, from now until `done` resolves; `what` says what was waited for. */
const timed = async (step, what, done) => {
  const started = Date.now();
  const value = await done();
  timings.push({ step, what, ms: Date.now() - started });
  return value;
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

const stamp = Date.now().toString(36);
const songTitle = `Comptine (journey ${stamp})`;
const artistName = `Yann Tiersen (journey ${stamp})`;
const people = {
  author: { username: `journey-a-${stamp}`, password: `journey-a-${stamp}-password`, cookie: null },
  reader: { username: `journey-b-${stamp}`, password: `journey-b-${stamp}-password`, cookie: null },
};
/** The API as one of the temporary users, on its own cookie. */
const as = async (who, pathname, init = {}) => {
  const headers = new Headers(init.headers);
  headers.set('Cookie', `aitu_session=${people[who].cookie}`);
  if (init.body) headers.set('Content-Type', 'application/json');
  const answer = await rawFetch(`${api}${pathname}`, { ...init, headers });
  return { status: answer.status, body: answer.status === 204 ? null : await answer.json().catch(() => null) };
};

const made = { users: [], songs: new Set(), artists: new Set() };
const browser = await chromium.launch({ args: ['--autoplay-policy=no-user-gesture-required'] });
useSession(browser);
const problems = [];
const watch = (page, who) => {
  page.on('console', (m) => { if (m.type() === 'error') problems.push(`${who} console: ${m.text()}`); });
  page.on('pageerror', (e) => problems.push(`${who} page error: ${e.message}`));
  page.on('response', (r) => { if (r.status() >= 400) problems.push(`${who} ${r.status()} ${r.url()}`); });
};
const pages = {};
const shot = async (page, name) => {
  await page.waitForTimeout(400);
  await page.screenshot({ path: path.join(out, `${name}.png`) });
};
const until = async (page, test, ms = 15000) => {
  const end = Date.now() + ms;
  while (Date.now() < end) {
    if (await test()) return true;
    await page.waitForTimeout(100);
  }
  return false;
};
const saved = (page) =>
  page.waitForFunction(() => document.querySelector('[data-unsaved]')?.getAttribute('data-unsaved') === '', null, { timeout: 60000 });

/** Make a temporary user, sign it in, and open its window. */
async function makeUser(who) {
  const person = people[who];
  await send('POST', `${api}/admin/users`, { username: person.username, password: person.password });
  made.users.push(person.username);
  const login = await rawFetch(`${api}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: person.username, password: person.password }),
  });
  person.cookie = /aitu_session=([^;]+)/.exec(login.headers.get('set-cookie') ?? '')?.[1] ?? null;
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  await context.addCookies([{ name: 'aitu_session', value: person.cookie, url: base, httpOnly: true, sameSite: 'Lax' }]);
  pages[who] = await context.newPage();
  watch(pages[who], who);
  return login.ok && person.cookie !== null;
}

let projectId = null;
let publicSongId = null;
try {
  const engine = await json(`${api}/matrix/engine`);
  check('two temporary users are made and signed in', (await makeUser('author')) && (await makeUser('reader')), `${people.author.username}, ${people.reader.username}`);
  const master = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  pages.master = master;
  watch(master, 'master');
  const { author, reader } = pages;

  // 1. The author: a YouTube link to a piano sheet, saved to the library.
  await author.goto(`${base}/projects/new`);
  await author.getByLabel('Paste a YouTube link').fill(values.youtube);
  await shot(author, '01-source');
  await timed('Download the audio', 'the Audio step of the new project', async () => {
    await author.getByRole('button', { name: 'Download the audio', exact: true }).click();
    await author.waitForURL(/\/projects\/[0-9a-f-]{36}\/audio$/, { timeout: 300000 });
  });
  projectId = author.url().split('/').at(-2);
  const audio = (await as('author', `/audio/${projectId}`)).body;
  const seconds = Math.round(audio?.durationSeconds ?? audio?.duration_seconds ?? 0);
  check('the YouTube audio is a project of the author', (await as('author', `/projects/${projectId}`)).status === 200, `${seconds} s of audio`);
  check('the master user cannot open the author\'s project', (await fetch(`${api}/projects/${projectId}`)).status === 404);

  await author.getByRole('button', { name: /^Transcribe/ }).waitFor();
  await author.waitForSelector('canvas');
  await author.waitForTimeout(1500);
  const pressed = Date.now();
  await author.getByRole('button', { name: /^Transcribe/ }).click();
  await author.waitForURL('**/notes');
  let firstNote = null;
  while (firstNote === null && Date.now() - pressed < 120000) {
    const details = (await author.locator('[data-bar=details]').textContent({ timeout: 1000 }).catch(() => '')) ?? '';
    if (/^[1-9]\d* notes/.test(details)) firstNote = Date.now() - pressed;
    else await author.waitForTimeout(20);
  }
  timings.push({ step: 'Transcribe', what: 'the first note in the live view', ms: firstNote });
  await author.waitForTimeout(Math.max(0, 6000 - (Date.now() - pressed)));
  await shot(author, '02-live-notes');
  await author.getByRole('button', { name: 'Play from the playhead', exact: true }).waitFor({ timeout: 600000 });
  timings.push({ step: 'Transcribe', what: 'every note saved, on screen', ms: Date.now() - pressed });
  const notes = (await as('author', `/pieces/${projectId}/notes`)).body;
  check('the transcription gives notes', notes?.id?.length > 100, `${notes?.id?.length} notes, ${engine.engine ?? JSON.stringify(engine)}`);

  await author.getByRole('tab', { name: 'Hands', exact: true }).click();
  await author.waitForURL('**/hands');
  await author.getByRole('button', { name: 'Predict hands', exact: true }).waitFor();
  await timed('Predict hands', 'the hands on screen', async () => {
    await author.getByRole('button', { name: 'Predict hands', exact: true }).click();
    await author.waitForSelector('[data-predicted]', { timeout: 120000 });
  });
  await shot(author, '03-hands');
  await timed('Save the hands', 'saved', async () => {
    await author.getByRole('button', { name: 'Save', exact: true }).first().click();
    await saved(author);
  });

  await author.waitForFunction(() => {
    const tab = document.querySelector('[role=tab][data-step=sheet]');
    return tab && tab.getAttribute('aria-disabled') !== 'true';
  }, null, { timeout: 15000 });
  await timed('The Sheet step', 'the first notehead drawn', async () => {
    await author.getByRole('tab', { name: 'Sheet', exact: true }).click();
    await author.waitForSelector('.grid-notehead', { timeout: 120000 });
  });
  await shot(author, '04-sheet');
  await timed('Save the sheet', 'saved', async () => {
    await author.getByRole('button', { name: 'Save', exact: true }).click();
    await saved(author);
  });
  const status = (await as('author', `/pieces/${projectId}/status`)).body;
  check('every step of the project is ready', status.steps.every((one) => one.state === 'ready'), status.steps.map((one) => one.state).join(' '));

  const saveButton = author.getByRole('button', { name: 'Save to library' });
  await saveButton.waitFor({ timeout: 60000 });
  await saveButton.click();
  const saveDialog = author.getByRole('dialog', { name: 'Save to library' });
  await saveDialog.getByLabel('Artist').fill(artistName);
  await saveDialog.getByLabel('Song').fill(songTitle);
  await shot(author, '05-save-to-library');
  await timed('Save to library', 'the song with its version', async () => {
    await saveDialog.getByRole('button', { name: 'Save to library' }).click();
    await author.waitForURL('**/library/songs/*', { timeout: 120000 });
    await author.locator('[data-testid^=version-]').first().waitFor();
  });
  const ownSongId = Number(/library\/songs\/(\d+)/.exec(author.url())?.[1]);
  const ownSong = (await as('author', `/library/songs/${ownSongId}`)).body;
  check('the song is in the author\'s library with its version', ownSong?.title === songTitle && ownSong.versions.length === 1, ownSong?.versions[0]?.name);
  await shot(author, '06-my-song');

  // 2. The author publishes it, proposing the song and its artist.
  const ownVersion = ownSong.versions[0];
  await author.getByTestId(`version-${ownVersion.id}`).getByRole('button', { name: 'More actions' }).click();
  await author.getByRole('menuitem', { name: 'Publish' }).click();
  const publish = author.getByRole('dialog');
  await publish.getByTestId('propose-song').click();
  check('Propose this song starts from the song and its artist', (await publish.getByLabel('Title').inputValue()) === songTitle && (await publish.getByText('A new artist').count()) > 0);
  await publish.getByLabel('Year').fill('2001');
  await shot(author, '07-publish');
  await timed('Publish', 'the request sent', async () => {
    await publish.getByTestId('send-request').click();
    await author.getByText('Request sent to the master user').waitFor();
  });
  const requestId = (await as('author', '/requests')).body.find((one) => one.title === songTitle)?.id;
  check('the request is in the author\'s Requests', Boolean(requestId));

  // 3. The master user reviews it and accepts every item.
  await master.goto(`${base}/admin/requests`);
  check('Review lists the request', await until(master, async () => (await master.getByRole('cell', { name: songTitle }).count()) > 0));
  await master.getByRole('cell', { name: songTitle }).first().click();
  await master.waitForURL(`**/admin/requests/${requestId}`);
  await master.getByTestId('request-status').waitFor();
  await shot(master, '08-request');
  await master.goto(`${base}/admin/requests/${requestId}/sheet`);
  await timed('The request\'s Sheet tab', 'the proposed sheet drawn', async () => {
    await until(master, async () => (await master.getByTestId('request-sheet-proposed').locator('.grid-notehead').count()) > 0, 120000);
  });
  await shot(master, '09-request-sheet');
  const items = (await json(`${api}/requests/${requestId}`)).itemList;
  check('the request has a new artist, a new song and a piano sheet', ['newArtist', 'newSong', 'project'].every((kind) => items.some((one) => one.kind === kind)), items.map((one) => one.kind).join(', '));
  await master.getByTestId('review').click();
  await master.getByRole('dialog').getByText('Finish your review').waitFor();
  for (const item of items) await master.getByTestId(`decide-${item.id}`).getByRole('button', { name: 'Accept' }).click();
  await shot(master, '10-review');
  await timed('Send decision', 'Accepted, written to the Public Library', async () => {
    await master.getByTestId('send-decision').click();
    await until(master, async () => (await master.getByTestId('request-status').innerText()) === 'Accepted', 60000);
  });
  const decided = (await json(`${api}/requests/${requestId}`)).itemList;
  publicSongId = decided.find((one) => one.kind === 'newSong')?.payload.made?.songId ?? null;
  const publicArtistId = decided.find((one) => one.kind === 'newArtist')?.payload.made?.artistId ?? null;
  if (publicSongId) made.songs.add(publicSongId);
  if (publicArtistId) made.artists.add(publicArtistId);
  const publicSong = publicSongId ? await json(`${api}/public/songs/${publicSongId}`) : null;
  const authorGroup = publicSong?.others.find((group) => group.username === people.author.username);
  check('the public song has the author\'s version, credited to the author', authorGroup?.versions.length === 1 && publicSong.artists[0]?.name === artistName);
  await shot(master, '11-accepted');

  // 4. The reader finds it, adds it to their library, and plays it.
  await reader.goto(`${base}/public/songs`);
  await reader.getByTestId('public-search').fill(`journey ${stamp}`);
  check('Public songs finds the song', await until(reader, async () => (await reader.getByRole('cell', { name: songTitle }).count()) > 0));
  await reader.getByRole('cell', { name: songTitle }).first().click();
  await reader.waitForURL(`**/public/songs/${publicSongId}`);
  await reader.getByTestId('add-to-library').click();
  await shot(reader, '12-add-to-my-library');
  await timed('Add to my library', 'the song in the reader\'s library', async () => {
    await reader.getByTestId('add-confirm').click();
    await reader.getByTestId('open-mine').waitFor({ timeout: 30000 });
  });
  await reader.getByTestId('open-mine').click();
  await reader.waitForURL('**/library/songs/*');
  const readerSongId = Number(/library\/songs\/(\d+)/.exec(reader.url())?.[1]);
  const readerSong = (await as('reader', `/library/songs/${readerSongId}`)).body;
  const pulled = readerSong?.versions[0];
  check('the reader\'s song has the version, named after its author', pulled?.name === `original (${people.author.username})`, pulled?.name);
  await shot(reader, '13-reader-song');

  await timed('Play', 'Play mode, the first notehead drawn', async () => {
    await reader.getByTestId('song-play').click();
    await reader.waitForURL('**/play/**');
    await reader.locator('[data-play-page] .grid-notehead').first().waitFor({ timeout: 120000 });
  });
  await timed('Play and Pause', 'the recording playing', async () => {
    await reader.getByTestId('play-toggle').click();
    await until(reader, async () => (await reader.getByTestId('play-toggle').getAttribute('data-playing')) === 'true', 60000);
  });
  check('Play mode plays the pulled version', (await reader.getByTestId('play-toggle').getAttribute('data-playing')) === 'true');
  await reader.waitForTimeout(3000);
  await shot(reader, '14-play-mode');
  // While it plays the page shows the sheet alone, so the keys pause and close it.
  await reader.keyboard.press('Space');
  check('Space pauses', await until(reader, async () => (await reader.getByTestId('play-toggle').getAttribute('data-playing')) === 'false'));
  await reader.keyboard.press('Escape');
  await reader.waitForURL(`**/library/songs/${readerSongId}`);

  // 5. The reader makes a project from it: From other projects, Save as song.
  const pulledProject = (await as('reader', `/projects/${pulled.projectId}`)).body;
  const pulledNotes = (await as('reader', `/pieces/${pulled.parts?.[0] ?? pulled.projectId}/notes`)).body;
  await reader.goto(`${base}/projects`);
  await reader.evaluate(() => localStorage.removeItem('aitu.compose.draft'));
  await reader.getByRole('button', { name: 'New project' }).click();
  await reader.getByRole('menuitem', { name: /From other projects/ }).click();
  await reader.waitForURL('**/projects/compose');
  await reader.locator('[data-compose-picker] [role=listitem]').first().waitFor({ timeout: 20000 });
  await reader.getByLabel('Filter').fill(pulledProject.title);
  await timed('From other projects', 'the chosen version\'s sheet drawn', async () => {
    await reader.locator('[data-compose-picker] [role=listitem]').first().getByRole('button').first().click();
    await reader.waitForSelector('[data-compose-source] .grid-notehead', { timeout: 120000 });
  });
  await reader.getByTestId('compose-add-whole').click();
  await reader.locator('[data-compose-passage]').first().waitFor();
  await shot(reader, '15-compose');
  await reader.getByRole('button', { name: 'Save as song' }).click();
  const composeDialog = reader.getByRole('dialog', { name: 'Save as song' });
  await composeDialog.getByLabel('Title').fill(`Journey medley ${stamp}`);
  await timed('Save as song', 'the new project\'s Sheet step drawn', async () => {
    await composeDialog.getByTestId('compose-save').click();
    await reader.waitForURL(/\/projects\/[0-9a-f-]+\/sheet$/, { timeout: 120000 });
    // The compose page's own sheet is gone before the new project's first notehead counts.
    await reader.locator('[data-compose-source]').waitFor({ state: 'detached', timeout: 30000 });
    await reader.waitForSelector('.grid-notehead', { timeout: 120000 });
  });
  const composed = /\/projects\/([0-9a-f-]+)\/sheet/.exec(reader.url())[1];
  const composedNotes = (await as('reader', `/pieces/${composed}/notes`)).body;
  check('the new project holds every note of the pulled version', composedNotes?.id?.length === pulledNotes?.id?.length, `${composedNotes?.id?.length} of ${pulledNotes?.id?.length}`);
  check('the new project is the reader\'s, in Projects', (await as('reader', '/projects')).body.some((row) => row.id === composed));
  await shot(reader, '16-composed');

  // The rights along the way.
  check('the author cannot open the reader\'s new project', (await as('author', `/projects/${composed}`)).status === 404);
  check('the reader cannot open the author\'s library version', (await as('reader', `/projects/${projectId}`)).status === 404);
  check('the reader cannot open Review', (await as('reader', '/admin/requests')).status === 403);
} catch (error) {
  check('the journey finished', false, error instanceof Error ? error.message.split('\n')[0] : String(error));
  for (const [who, page] of Object.entries(pages)) await shot(page, `error-${who}`).catch(() => undefined);
} finally {
  for (const username of made.users) {
    try { fixture('remove-user', '--username', username); } catch (error) { check(`removing ${username}`, false, String(error)); }
  }
  for (const id of made.songs) fixture('remove-song', '--id', String(id));
  for (const id of made.artists) fixture('remove-artist', '--id', String(id));
  await browser.close();
}

const users = await json(`${api}/admin/users`);
const leftSongs = (await json(`${api}/public/songs?q=${encodeURIComponent(`journey ${stamp}`)}`)).total;
check('nothing left behind', !users.some((one) => one.username.includes(stamp)) && leftSongs === 0, `${leftSongs} public songs`);
// The refusals asked for on purpose, and the sheet not yet written before the Sheet step.
const expected = (line) =>
  /reader 403 .*\/admin\/requests/.test(line) ||
  /404 .*\/time\/[0-9a-f-]+\/rhythm$/.test(line) ||
  /Failed to load resource: .* (404)/.test(line);
const unexpected = problems.filter((line) => !expected(line));

const secondsOf = (ms) => (ms === null || ms === undefined ? '-' : `${(ms / 1000).toFixed(1)} s`);
console.log(results.join('\n'));
console.log('\nstep | waited for | time');
for (const one of timings) console.log(`${one.step} | ${one.what} | ${secondsOf(one.ms)}`);
if (unexpected.length) console.log(`\nproblems:\n  ${unexpected.slice(0, 30).join('\n  ')}`);
console.log(`\nscreenshots: ${out}`);
if (values.json) writeFileSync(values.json, `${JSON.stringify({ date: new Date().toISOString(), youtube: values.youtube, timings, results }, null, 2)}\n`);
process.exit(results.some((line) => line.includes('FAIL')) || unexpected.length ? 1 : 0);
