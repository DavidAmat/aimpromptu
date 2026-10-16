/**
 * Requests, the review and sharing (implementation 02, Phase 14, plan sections 15.4 and 16), walked
 * in two headless Chromium windows through the running app (`make up`): the master user, and a
 * **temporary user** the check makes (`check-<time>`) and removes at the end with everything it made.
 *
 * Nothing of a real library changes: the temporary user gets its version by **Add to my library**
 * from the master user's library shared with it (a copy), and everything public the check accepts
 * (a user version and a fixed version of the public "7 Years", a new song and a new artist) is
 * removed by `aitu_backend.library.public_fixture` at the end.
 *
 * 1. Sharing: **Share my library** from the user menu; the user's **Shared**, the song, **Add to my
 *    library**; the shared version opens read only.
 * 2. **Publish** a version: the dialog, the public song chosen, the request page (side by side).
 * 3. **Propose a song** with a new artist; the master user's **Review** (the count, oldest first);
 *    the artist accepted, a change asked on the song; the user's count; **Change and send again**;
 *    accepted.
 * 4. The version request: the two sheets, Play, accepted; the version on the public song by the user.
 * 5. **Ask for a fixed version** (Hard), accepted; **Suggest a change**, withdrawn.
 * 6. Rights: the user cannot open Review; sharing stopped, the shared song is gone.
 * 7. 390 px and dark.
 *
 *     npm run check:requests
 *     npm run check:requests -- --out /tmp/requests
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
    out: { type: 'string', default: path.join(repository, '.run', 'screenshots', 'requests') },
    base: { type: 'string', default: 'http://localhost:5173' },
    name: { type: 'string', default: '7 Years' },
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

// The temporary user, signed in on its own cookie.
const stamp = Date.now().toString(36);
const reader = { username: `check-${stamp}`, password: `check-${stamp}-password` };
let readerCookie = null;
const asReader = async (pathname, init = {}) => {
  const headers = new Headers(init.headers);
  headers.set('Cookie', `aitu_session=${readerCookie}`);
  if (init.body) headers.set('Content-Type', 'application/json');
  const answer = await rawFetch(`${api}${pathname}`, { ...init, headers });
  return { status: answer.status, body: answer.status === 204 ? null : await answer.json().catch(() => null) };
};

const made = { user: false, songs: new Set(), artists: new Set(), sharing: false };

const browser = await chromium.launch({ args: ['--autoplay-policy=no-user-gesture-required'] });
useSession(browser);
const problems = [];
const watch = (page, who) => {
  page.on('console', (m) => { if (m.type() === 'error') problems.push(`${who} console: ${m.text()}`); });
  page.on('pageerror', (e) => problems.push(`${who} page error: ${e.message}`));
  page.on('response', (r) => { if (r.status() >= 400) problems.push(`${who} ${r.status()} ${r.url()}`); });
};
const master = await browser.newPage({ viewport: { width: 1440, height: 900 } });
watch(master, 'master');
let user = null;
const shot = async (page, name) => {
  await page.waitForTimeout(400);
  await page.screenshot({ path: path.join(out, `${name}.png`) });
};
const until = async (page, test, ms = 15000) => {
  const end = Date.now() + ms;
  while (Date.now() < end) {
    if (await test()) return true;
    await page.waitForTimeout(150);
  }
  return false;
};
const sidebarCount = async (page, label) => {
  const text = await page.getByRole('navigation', { name: 'Sections' }).getByRole('link', { name: new RegExp(`^${label}`) }).innerText();
  return Number(text.replace(/[^0-9]/g, '') || 0);
};
/** Decide one item on the review page: a decision, and a comment when it is not an acceptance. */
const decideItem = async (itemId, decision, comment) => {
  const box = master.getByTestId(`decide-${itemId}`);
  await box.getByRole('button', { name: decision }).click();
  if (comment) await box.getByRole('textbox').last().fill(comment);
};

try {
  // The song the check publishes to, and the master user's version it copies.
  const target = (await json(`${api}/public/suggest?q=${encodeURIComponent(values.name)}`)).songs.find((one) => one.title === values.name);
  if (!target) throw new Error(`The Public Library has no ${values.name}`);
  const before = await json(`${api}/public/songs/${target.id}`);
  if (before.fixed.length || before.others.length) throw new Error(`${values.name} already has public versions: the check would change them`);
  const mine = await json(`${api}/library/songs`);
  const source = mine.find((song) => song.title === values.name);
  if (!source) throw new Error(`My library has no song named ${values.name}`);

  await send('POST', `${api}/admin/users`, reader);
  made.user = true;
  const login = await rawFetch(`${api}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(reader),
  });
  readerCookie = /aitu_session=([^;]+)/.exec(login.headers.get('set-cookie') ?? '')?.[1] ?? null;
  check('a temporary user is made and signed in', login.ok && readerCookie !== null, reader.username);
  const readerContext = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  await readerContext.addCookies([{ name: 'aitu_session', value: readerCookie, url: base, httpOnly: true, sameSite: 'Lax' }]);
  user = await readerContext.newPage();
  watch(user, 'user');

  // 1. Sharing.
  await master.goto(`${base}/projects`);
  await master.getByRole('button', { name: /^Account:/ }).click();
  await master.getByRole('menuitem', { name: 'Share my library' }).click();
  const share = master.getByRole('dialog');
  await share.getByRole('switch', { name: `Share with ${reader.username}` }).click();
  made.sharing = true;
  check('Share my library lists the user, switched on', await until(master, async () => (await share.getByRole('switch', { name: `Share with ${reader.username}` }).isChecked())));
  await shot(master, '01-share-my-library');
  await share.getByRole('button', { name: 'Done' }).click();

  await user.goto(`${base}/library/shared`);
  check('Shared lists the master user\'s songs', await until(user, async () => (await user.getByRole('cell', { name: values.name, exact: true }).count()) > 0));
  await shot(user, '02-shared');
  await user.getByRole('cell', { name: values.name, exact: true }).click();
  await user.getByTestId('shared-add').click();
  check('Add to my library copies the shared version', await until(user, async () => (await user.getByText('1 version added to My library').count()) > 0));
  await shot(user, '03-shared-song-added');
  const sharedSong = (await asReader(`/shared/songs/${source.id}`)).body;
  const sharedVersion = sharedSong.versions[0];
  check('the shared version is read only for the user', (await asReader(`/projects/${sharedVersion.projectId}`, { method: 'PATCH', body: JSON.stringify({ title: 'x' }) })).status === 403);
  await user.goto(`${base}/projects/${sharedVersion.parts[0]}/sheet`);
  check('the shared version opens with Play and without Edit', await until(user, async () => (await user.getByTestId('version-play').count()) > 0 && (await user.getByRole('button', { name: 'Edit' }).count()) === 0, 60000));

  // 2. Publish the copied version.
  const ownSongId = sharedSong.inLibrary ?? (await asReader('/library/songs')).body[0].id;
  await user.goto(`${base}/library/songs/${ownSongId}`);
  const ownVersion = (await asReader(`/library/songs/${ownSongId}`)).body.versions[0];
  await user.getByTestId(`version-${ownVersion.id}`).getByRole('button', { name: 'More actions' }).click();
  await user.getByRole('menuitem', { name: 'Publish' }).click();
  const publish = user.getByRole('dialog');
  await publish.getByLabel('Public song').click();
  await publish.getByLabel('Public song').fill(values.name);
  check('the dialog suggests the public song', await until(user, async () => (await user.getByRole('option', { name: new RegExp(values.name) }).count()) > 0));
  await user.getByRole('option', { name: new RegExp(values.name) }).first().click();
  check('the version name is offered in its simple form', /^[a-z0-9-]+$/.test(await publish.getByLabel('Version name').inputValue()));
  await publish.getByLabel('Version name').fill('check');
  await shot(user, '04-publish-dialog');
  await publish.getByTestId('send-request').click();
  await user.getByText('Request sent to the master user').waitFor();
  await user.getByRole('button', { name: 'Open' }).click();
  await user.getByTestId('request-status').waitFor();
  check('the request waits for review', (await user.getByTestId('request-status').innerText()) === 'Waiting for review');
  check('the request shows the proposal beside an empty side', await until(user, async () => (await user.getByTestId('compare-proposed').locator('svg').count()) > 0, 60000));
  await shot(user, '05-request-sent');
  const versionRequest = Number(user.url().split('/').pop());

  // 3. Propose a song with a new artist.
  await user.goto(`${base}/public/songs`);
  await user.getByTestId('propose-a-song').click();
  const propose = user.getByRole('dialog');
  const songTitle = `Check song ${stamp}`;
  const artistName = `Check artist ${stamp}`;
  await propose.getByLabel('Title').fill(songTitle);
  await propose.getByLabel('Artist').fill(artistName);
  check('a name with no public artist is a new artist', await until(user, async () => (await propose.getByText('A new artist').count()) > 0));
  await propose.getByLabel('Genres').click();
  await user.getByRole('option', { name: 'pop', exact: true }).click();
  await shot(user, '06-propose-a-song');
  await propose.getByTestId('send-request').click();
  await user.getByText('Request sent to the master user').waitFor();
  const songRequest = (await asReader('/requests')).body.find((one) => one.title === songTitle)?.id;

  await master.goto(`${base}/admin/requests`);
  check('Review counts the two requests', await until(master, async () => (await sidebarCount(master, 'Review')) === 2));
  const reviewRows = await master.locator('tbody tr').allInnerTexts();
  check('Review lists them oldest first', reviewRows[0]?.includes(values.name) && reviewRows[1]?.includes(songTitle));
  await shot(master, '07-review');
  await master.goto(`${base}/admin/requests/${songRequest}`);
  const songItems = (await json(`${api}/requests/${songRequest}`)).itemList;
  await master.getByTestId(`decide-${songItems[0].id}`).waitFor();
  await decideItem(songItems[0].id, 'Accept');
  await decideItem(songItems[1].id, 'Ask for a change', 'Add its year, please');
  await shot(master, '08-review-decisions');
  await master.getByTestId('send-decision').click();
  check('changes asked, the artist accepted', await until(master, async () => (await master.getByTestId('request-status').innerText()) === 'Changes asked'));
  const afterFirst = await json(`${api}/requests/${songRequest}`);
  const newArtist = afterFirst.itemList[0].payload.made?.artistId;
  if (newArtist) made.artists.add(newArtist);
  check('the new artist is in the Public library', Boolean(newArtist) && (await json(`${api}/public/artists/${newArtist}`)).name === artistName);

  await user.goto(`${base}/requests`);
  check('Requests counts the request with changes asked', await until(user, async () => (await sidebarCount(user, 'Requests')) === 1));
  await shot(user, '09-my-requests');
  await user.goto(`${base}/requests/${songRequest}`);
  await user.getByTestId('resend').click();
  const again = user.getByRole('dialog');
  await again.getByLabel('Year').waitFor();
  check('the dialog opens as it was sent, the artist now public', (await again.getByLabel('Title').inputValue()) === songTitle && (await again.getByText('From the Public Library').count()) > 0);
  await again.getByLabel('Year').fill('2026');
  await shot(user, '10-change-and-send-again');
  await again.getByTestId('send-request').click();
  check('sent again, it waits for review', await until(user, async () => (await user.getByTestId('request-status').innerText()) === 'Waiting for review'));

  await master.goto(`${base}/admin/requests/${songRequest}`);
  const songItemsAgain = (await json(`${api}/requests/${songRequest}`)).itemList.filter((one) => one.decision === null);
  await master.getByTestId(`decide-${songItemsAgain[0].id}`).waitFor();
  await decideItem(songItemsAgain[0].id, 'Accept');
  await master.getByTestId('send-decision').click();
  check('the song is accepted', await until(master, async () => (await master.getByTestId('request-status').innerText()) === 'Accepted'));
  const newSong = (await json(`${api}/requests/${songRequest}`)).itemList.find((one) => one.kind === 'newSong')?.payload.made?.songId;
  if (newSong) made.songs.add(newSong);
  const publicSong = newSong ? await json(`${api}/public/songs/${newSong}`) : null;
  check('the new song is in the Public library with its year and artist', publicSong?.year === 2026 && publicSong.artists[0]?.name === artistName && publicSong.genres[0] === 'pop');

  // 4. The version request, side by side.
  await master.goto(`${base}/admin/requests/${versionRequest}`);
  check('the review draws the proposed sheet', await until(master, async () => (await master.getByTestId('compare-proposed').locator('svg').count()) > 0, 60000));
  check('the current side says it is a new version', (await master.getByTestId('compare-current').innerText()).includes('new version'));
  await master.getByTestId('compare-play-proposed').click();
  // Play answers once the browser has enough of the recording: slower while the machine is busy.
  check('the proposal plays', await until(master, async () => (await master.getByRole('button', { name: 'Pause' }).count()) > 0, 60000));
  await shot(master, '11-side-by-side');
  await master.getByRole('button', { name: 'Pause' }).click();
  const versionItem = (await json(`${api}/requests/${versionRequest}`)).itemList[0];
  await decideItem(versionItem.id, 'Accept');
  await master.getByTestId('send-decision').click();
  check('the version is accepted', await until(master, async () => (await master.getByTestId('request-status').innerText()) === 'Accepted', 30000));
  const published = await json(`${api}/public/songs/${target.id}`);
  const userVersion = published.others.find((group) => group.username === reader.username)?.versions[0];
  check('the public song has the user\'s version, by the user', userVersion?.name === 'check');

  // 5. A fixed version; a change withdrawn.
  await user.goto(`${base}/public/songs/${target.id}`);
  await user.getByTestId('public-version').last().getByRole('button', { name: 'Version actions' }).click();
  await user.getByRole('menuitem', { name: 'Ask for a fixed version' }).click();
  await shot(user, '12-ask-fixed-version');
  await user.getByRole('dialog').getByTestId('send-request').click();
  await user.getByText('Request sent to the master user').waitFor();
  const fixedRequest = (await asReader('/requests')).body.find((one) => one.kind === 'fixedVersion')?.id;
  await master.goto(`${base}/admin/requests/${fixedRequest}`);
  const fixedItem = (await json(`${api}/requests/${fixedRequest}`)).itemList[0];
  await master.getByTestId(`decide-${fixedItem.id}`).waitFor();
  await decideItem(fixedItem.id, 'Accept');
  await master.getByTestId('send-decision').click();
  check('the fixed version is accepted', await until(master, async () => (await master.getByTestId('request-status').innerText()) === 'Accepted', 30000));
  const fixed = (await json(`${api}/public/songs/${target.id}`)).fixed;
  check('Hard is the user\'s version, by the user', fixed[0]?.name === 'hard' && fixed[0].creator === reader.username && fixed[0].projectId === userVersion?.projectId);
  await master.goto(`${base}/public/songs/${target.id}`);
  await master.getByTestId('public-play').waitFor();
  await shot(master, '13-public-song-with-versions');

  await user.goto(`${base}/public/songs/${newSong}`);
  await user.getByRole('button', { name: 'Song actions' }).click();
  await user.getByRole('menuitem', { name: 'Suggest a change' }).click();
  const change = user.getByRole('dialog');
  await change.getByLabel('Genres').click();
  await user.getByRole('option', { name: 'rock', exact: true }).click();
  await change.getByTestId('send-request').click();
  await user.getByText('Request sent to the master user').waitFor();
  await user.getByRole('button', { name: 'Open' }).click();
  await user.getByTestId('withdraw').click();
  await user.getByRole('dialog').getByRole('button', { name: 'Withdraw request' }).click();
  check('a waiting request is withdrawn', await until(user, async () => (await user.getByTestId('request-status').innerText()) === 'Withdrawn'));
  await shot(user, '14-withdrawn');

  // 6. Rights.
  check('the user cannot open Review', (await asReader('/admin/requests')).status === 403);
  check('the user does not see Admin', (await user.getByRole('link', { name: /^Review/ }).count()) === 0);
  await send('DELETE', `${api}/shares/${(await json(`${api}/shares`)).people.find((one) => one.username === reader.username).id}`);
  made.sharing = false;
  check('sharing stopped, the shared song is gone', (await asReader(`/shared/songs/${source.id}`)).status === 404);

  // 7. 390 px and dark.
  await master.setViewportSize({ width: 390, height: 844 });
  await master.goto(`${base}/admin/requests/${versionRequest}`);
  await master.getByTestId('request-status').waitFor();
  await until(master, async () => (await master.getByTestId('compare-proposed').locator('svg').count()) > 0, 60000);
  check('390 px: no sideways scroll on a request', await master.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1));
  await shot(master, '15-narrow-request');
  await master.goto(`${base}/admin/requests`);
  await master.getByRole('heading', { name: 'Review' }).waitFor();
  await master.getByRole('button', { name: 'All' }).click();
  await master.locator('tbody tr').first().waitFor();
  check('390 px: no sideways scroll on Review', await master.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1));
  await shot(master, '16-narrow-review');
  await master.setViewportSize({ width: 1440, height: 900 });
  await master.emulateMedia({ colorScheme: 'dark' });
  await master.evaluate(() => localStorage.setItem('mui-mode', 'dark'));
  await master.goto(`${base}/admin/requests/${songRequest}`);
  await master.getByTestId('request-status').waitFor();
  await shot(master, '17-dark-request');
  await master.evaluate(() => localStorage.removeItem('mui-mode'));
  check('the counts are back to none', (await json(`${api}/requests/counts`)).review === 0);
} catch (error) {
  check('the walk finished', false, error instanceof Error ? error.message : String(error));
  await shot(master, 'error-master').catch(() => undefined);
  if (user) await shot(user, 'error-user').catch(() => undefined);
} finally {
  if (made.sharing) {
    const found = (await json(`${api}/shares`)).people.find((one) => one.username === reader.username);
    if (found) await fetch(`${api}/shares/${found.id}`, { method: 'DELETE' });
  }
  if (made.user) fixture('remove-user', '--username', reader.username);
  for (const id of made.songs) fixture('remove-song', '--id', String(id));
  for (const id of made.artists) fixture('remove-artist', '--id', String(id));
  await browser.close();
}

const target = (await json(`${api}/public/suggest?q=${encodeURIComponent(values.name)}`)).songs.find((one) => one.title === values.name);
const after = await json(`${api}/public/songs/${target.id}`);
const users = await json(`${api}/admin/users`);
const leftSongs = (await json(`${api}/public/songs?q=${encodeURIComponent(`check song ${stamp}`)}`)).total;
check(
  'nothing left behind',
  after.fixed.length === 0 && after.others.length === 0 && !users.some((one) => one.username === reader.username) && leftSongs === 0,
);
// The refusals the walk asks for on purpose: the user's 403 on Review, and the 404 once sharing stopped.
const expected = (line) => /user 40[34] .*\/(admin\/requests|shared\/songs)/.test(line);
const unexpected = problems.filter((line) => !expected(line));
console.log(results.join('\n'));
if (unexpected.length) console.log(`\nproblems:\n  ${unexpected.join('\n  ')}`);
console.log(`\nscreenshots: ${out}`);
process.exit(results.some((line) => line.includes('FAIL')) || unexpected.length ? 1 : 0);
