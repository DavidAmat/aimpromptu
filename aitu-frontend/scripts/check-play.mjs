/**
 * Play mode (implementation 02, plan section 17, Phase 11), walked in a headless Chromium.
 *
 * Drives the real page through the running app (`make up`), signed in (`session.mjs`), on
 * **temporary copies** only, deleted at the end, so no project of a library is changed:
 *
 * 1. a copy of a project with two lyrics pieces put on its saved sheet: **Play** from its `⋯` on
 *    Projects; the page has the sheet and nothing else (no sidebar, Close and Play, no Next);
 *    Space plays; the buttons fade while it plays and the pointer rests, and come back; the page
 *    keeps the cursor in the middle of the window; the lyrics piece of the frames sounding is shown
 *    and the other faint; Notes Falling as a view; the old Notes Falling address; Escape closes;
 * 2. an integrated playlist of two short parts (`POST /projects/compose`): both drawn with their
 *    subheaders, the second plays on from the first;
 * 3. two copies saved to My library as two songs, a songs playlist of them (the second a stretch):
 *    **Play** on the song page and on a version, **Play** on the playlist, **Next**, the stretch
 *    stops by itself, **All songs**, Close back to the playlist with its song shaded;
 * 4. 390 px and dark.
 *
 *     npm run check:play
 *     npm run check:play -- --name Elefants --out /tmp/play
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
    out: { type: 'string', default: path.join(here, '..', '..', '.run', 'screenshots', 'play') },
    base: { type: 'string', default: 'http://localhost:5173' },
    name: { type: 'string', default: 'Elefants' },
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
const waitForSheet = async () => {
  await page.waitForSelector('[data-play-page] .grid-note-target', { timeout: 90000 });
  await page.waitForTimeout(800);
};
const playing = () => page.getByTestId('play-toggle').getAttribute('data-playing');
/** Wait until `test` holds, polling, up to `ms`. */
const until = async (test, ms = 10000) => {
  const end = Date.now() + ms;
  while (Date.now() < end) {
    if (await test()) return true;
    await page.waitForTimeout(150);
  }
  return false;
};
const rowMenu = async (row, item) => {
  await row.getByRole('button', { name: /more actions/i }).click();
  await page.getByRole('menuitem', { name: item }).click();
  await page.waitForTimeout(300);
};

async function freshCopy(label) {
  const vault = await json(`${api}/projects`);
  // The shortest title that names it: "Elefants - Oques Grasses", not a playlist or a copy of it.
  const original = vault
    .filter((row) => row.step === 'sheet' && row.title.toUpperCase().includes(values.name.toUpperCase()) && !row.title.includes('(check-'))
    .sort((a, b) => a.title.length - b.title.length)[0];
  if (!original) throw new Error(`No project of the vault named ${values.name} has its piano sheet`);
  const copy = await send('POST', `${api}/projects/${original.id}/duplicate`, { title: `${original.title} (${label})` });
  made.add(copy.id);
  return copy;
}

try {
  // 1. One project.
  const copy = await freshCopy('check-play');
  const sheet = await json(`${api}/time/${copy.id}/rhythm`);
  await send('PUT', `${api}/time/${copy.id}/rhythm`, {
    ...sheet,
    lyrics: [
      { fromColumn: 25, toColumn: 100, text: 'check words one' },
      { fromColumn: 400, toColumn: 450, text: 'check words two' },
    ],
  });

  await page.goto(`${base}/projects`);
  await page.getByText(copy.title).first().waitFor({ timeout: 20000 });
  const projectRow = page.locator('[role=listitem]', { hasText: copy.title }).first();
  await rowMenu(projectRow, 'Play');
  await page.waitForURL(`**/play/${copy.id}`);
  await waitForSheet();
  check('Projects → ⋯ → Play opens Play mode', true);
  check('the page has no sidebar', (await page.locator('nav').count()) === 0);
  check('Close and Play are on the page, Next is not', (await page.getByTestId('play-close').isVisible()) && (await page.getByTestId('play-toggle').isVisible()) && (await page.getByTestId('play-next').count()) === 0);
  check('nothing on the sheet opens a toolbox', (await page.locator('[data-sheet-page] [data-testid=sheet-floating-bar], [role=toolbar]').count()) === 0);
  check('the lyrics are drawn', (await page.locator('.grid-lyric').count()) === 2);
  await shot('01-play-mode');

  await page.mouse.move(700, 450);
  await page.keyboard.press('Space');
  check('Space plays', await until(async () => (await playing()) === 'true', 8000));
  const lit = await until(
    async () =>
      page.evaluate(() => {
        const one = document.querySelector('.grid-lyric[data-from-column="25"]');
        const two = document.querySelector('.grid-lyric[data-from-column="400"]');
        const ink = one?.querySelector('.grid-lyric-text');
        return Boolean(
          one && two && ink &&
            getComputedStyle(one).opacity === '1' &&
            getComputedStyle(ink).fill === 'rgb(0, 0, 0)' &&
            Number(getComputedStyle(two).opacity) < 0.5,
        );
      }),
    8000,
  );
  check('the lyrics piece of the frames sounding is shown in black, the other faint', lit);
  await shot('02-lyrics-by-frames');
  const faded = await until(
    async () => (await page.locator('[data-play-menu]').evaluate((node) => getComputedStyle(node).opacity)) === '0',
    6000,
  );
  check('while it plays, the buttons fade when the pointer rests', faded);
  await shot('03-playing-clean');
  await page.mouse.move(720, 470);
  check('a move of the pointer brings them back', await until(async () => (await page.locator('[data-play-menu]').evaluate((node) => getComputedStyle(node).opacity)) === '1', 2000));
  const scrolled = await until(async () => (await page.evaluate(() => window.scrollY)) > 0, 40000);
  await page.waitForTimeout(1200);
  const place = await page.evaluate(() => {
    const line = document.querySelector('[data-play-active="true"] [data-playhead]');
    const box = line?.getBoundingClientRect();
    return box ? (box.top + box.height / 2) / window.innerHeight : -1;
  });
  check('the page follows the music, the cursor in the middle of the window', scrolled && place > 0.25 && place < 0.75, `at ${(place * 100).toFixed(0)} % of the height`);
  await shot('04-cursor-in-the-middle');
  await page.keyboard.press('Space');
  check('Space pauses', await until(async () => (await playing()) === 'false', 4000));
  const before = await page.evaluate(() => window.scrollY);
  await page.keyboard.press('ArrowDown');
  await page.waitForTimeout(700);
  check('the arrows scroll', (await page.evaluate(() => window.scrollY)) > before);
  const cursorAt = () =>
    page.evaluate(() => {
      const box = document.querySelector('[data-play-active="true"] [data-playhead]')?.getBoundingClientRect();
      return box ? Math.round(box.top + window.scrollY) : null;
    });
  const firstLine = await cursorAt();
  // A line further down: below the cursor's own line, by more than a line's height.
  const line = await page.locator('[data-play-active="true"] [data-playhead]').boundingBox();
  if (line) await page.mouse.dblclick(720, Math.min(860, line.y + line.height + 220));
  check('a double-click on the sheet moves the cursor there', await until(async () => (await cursorAt()) !== firstLine, 3000));

  await page.getByRole('button', { name: 'Notes Falling' }).click();
  await page.waitForSelector('[data-play-falling] [data-note-id]', { timeout: 20000 });
  check('Notes Falling is a view of Play mode', page.url().includes('view=falling'));
  await shot('05-notes-falling');
  await page.getByRole('button', { name: 'Sheet' }).click();
  await page.waitForTimeout(400);
  check('back to the sheet', (await page.locator('[data-play-falling]').count()) === 0);

  await page.goto(`${base}/projects/${copy.id}/notes-falling`);
  await page.waitForURL(`**/play/${copy.id}?view=falling`);
  check('the old Notes Falling address opens Play mode on Notes Falling', true);
  await page.goto(`${base}/play/${copy.id}`);
  await waitForSheet();
  await page.keyboard.press('Escape');
  await page.waitForURL(`**/projects/${copy.id}**`);
  check('Escape closes Play mode', true);

  // The Sheet step lights the words being sung too, and fades nothing.
  await page.goto(`${base}/projects/${copy.id}/sheet`);
  await page.waitForSelector('[data-sheet-page] .grid-note-target', { timeout: 90000 });
  await page.waitForTimeout(800);
  await page.mouse.move(700, 450);
  await page.keyboard.press('Space');
  const litOnSheet = await until(
    async () =>
      page.evaluate(() => {
        const one = document.querySelector('.grid-lyric[data-from-column="25"]');
        const two = document.querySelector('.grid-lyric[data-from-column="400"]');
        const ink = one?.querySelector('.grid-lyric-text');
        return Boolean(
          one && two && ink &&
            getComputedStyle(ink).fill === 'rgb(0, 0, 0)' &&
            Number(getComputedStyle(ink).fontWeight) >= 700 &&
            getComputedStyle(two).opacity === '1',
        );
      }),
    8000,
  );
  check('on the Sheet step the words being sung turn black and bold, the others stay', litOnSheet);
  await shot('12-sheet-step-lyrics');
  await page.keyboard.press('Space');

  // A piece placed and not saved lights up too: the page's own lyrics, not the saved ones.
  await page.waitForTimeout(400);
  await page.getByRole('button', { name: 'Sheet toolbox' }).click();
  const toolbox = page.locator('[data-sheet-toolbox]');
  await toolbox.getByRole('button', { name: 'Lyrics', exact: true }).click();
  await page.locator('[data-lyrics-paste]').fill('words not saved');
  await toolbox.locator('[data-lyrics-add]').click();
  const target = await page.evaluate(() => {
    const ruler = document.querySelector('.grid-frame-ruler')?.getBoundingClientRect();
    for (const note of document.querySelectorAll('.grid-note-target[data-hand="right"]')) {
      const box = note.getBoundingClientRect();
      if (ruler && box.top > ruler.y && box.top < ruler.y + 220 && box.left > ruler.x + ruler.width * 0.4) {
        return { x: box.left + box.width / 2, y: ruler.y + ruler.height + 40 };
      }
    }
    return null;
  });
  const dropBox = await page.locator('[data-sheet-drop]').boundingBox();
  if (target && dropBox) {
    await toolbox.locator('[data-lyrics-piece]').last().dragTo(page.locator('[data-sheet-drop]'), {
      targetPosition: { x: target.x - dropBox.x, y: target.y - dropBox.y },
    });
  }
  await page.waitForTimeout(1200);
  const pool = await toolbox.locator('[data-lyrics-piece]').count();
  const placed = await page.evaluate(() => {
    for (const group of document.querySelectorAll('.grid-lyric')) {
      if (group.textContent?.includes('words not saved')) {
        return { from: Number(group.getAttribute('data-from-column')), to: Number(group.getAttribute('data-to-column')) };
      }
    }
    return null;
  });
  const savedNow = await json(`${api}/time/${copy.id}/rhythm`);
  const notSaved = placed !== null && !savedNow.lyrics.some((line) => line.text === 'words not saved');
  let litUnsaved = false;
  if (placed) {
    await page.getByRole('button', { name: 'Close' }).first().click().catch(() => undefined);
    // Move the recording to the middle of the piece with the scrub bar's keys, then play.
    const bar = page.getByRole('slider', { name: 'Position in the piece' });
    const want = (((placed.from + placed.to) / 2) * 40) / 1000;
    await bar.evaluate((node) => node.focus());
    for (let tries = 0; tries < 400; tries++) {
      const now = Number(await bar.getAttribute('aria-valuenow'));
      if (now >= want - 0.3) break;
      await page.keyboard.press('ArrowRight');
    }
    await page.mouse.click(5, 5);
    await page.keyboard.press('Space');
    litUnsaved = await until(
      async () =>
        page.evaluate((from) => {
          const ink = document.querySelector(`.grid-lyric[data-from-column="${from}"] .grid-lyric-text`);
          return Boolean(ink && getComputedStyle(ink).fill === 'rgb(0, 0, 0)' && Number(getComputedStyle(ink).fontWeight) >= 700);
        }, placed.from),
      8000,
    );
    // At once: the piece is lit only while the cursor is over it.
    await page.screenshot({ path: path.join(out, '13-sheet-step-lyrics-not-saved.png') });
    await page.keyboard.press('Space');
  }
  check('a lyrics piece placed and not saved lights up too', notSaved && litUnsaved, placed ? `f${placed.from}–f${placed.to}` : `not placed: target ${JSON.stringify(target)}, ${pool} in the pool`);

  // 2. An integrated playlist: two parts, played on.
  const composed = await send('POST', `${api}/projects/compose`, {
    title: 'check-play integrated',
    kind: 'integratedPlaylist',
    passages: [
      { part: copy.id, fromMs: 20000, toMs: 22500, join: 'sequential' },
      { part: copy.id, fromMs: 40000, toMs: 46000, join: 'subheader', subheader: 'Coda' },
    ],
  });
  made.add(composed.id);
  await page.goto(`${base}/play/${composed.id}`);
  await waitForSheet();
  await page.locator('[data-play-part="0:1"] .grid-note-target').first().waitFor({ timeout: 60000 });
  check('an integrated playlist draws its parts one after the other, with their subheaders', (await page.locator('[data-play-part]').count()) === 2 && (await page.getByRole('heading', { name: 'Coda' }).count()) === 1);
  await shot('06-integrated-playlist');
  await page.keyboard.press('Space');
  const onward = await until(
    async () =>
      (await page.locator('[data-play-part="0:1"]').getAttribute('data-play-active')) === 'true' && (await playing()) === 'true',
    12000,
  );
  check('the second part plays on from the first', onward);
  await page.keyboard.press('Space');

  // 3. Songs: two copies saved to My library, a playlist of them.
  const one = await freshCopy('check-play-one');
  const savedOne = await send('POST', `${api}/projects/${one.id}/library`, { song: 'check-play one', artist: 'check-play artist', version: 'original' });
  songs.add(savedOne.songId);
  const two = await freshCopy('check-play-two');
  const savedTwo = await send('POST', `${api}/projects/${two.id}/library`, { song: 'check-play two', artist: 'check-play artist', version: 'original' });
  songs.add(savedTwo.songId);

  await page.goto(`${base}/library/songs/${savedOne.songId}`);
  await page.getByTestId('song-play').click();
  await page.waitForURL(`**/play/${savedOne.projectId}`);
  await waitForSheet();
  check('Song → Play opens its version in Play mode', (await page.getByRole('heading', { name: 'check-play one' }).count()) === 1);
  await page.goto(`${base}/projects/${savedOne.projectId}/sheet`);
  await page.getByTestId('version-play').click();
  await page.waitForURL(`**/play/${savedOne.projectId}`);
  check('a version, read only, has Play', true);

  const playlist = await send('POST', `${api}/playlists`, {
    title: 'check-play playlist',
    items: [{ songId: savedOne.songId }, { songId: savedTwo.songId, fromMs: 30000, toMs: 32000 }],
  });
  playlists.add(playlist.id);
  await page.goto(`${base}/library/playlists/${playlist.id}`);
  await page.getByTestId('playlist-play').click();
  await page.waitForURL(`**/play/playlist/${playlist.id}**`);
  await waitForSheet();
  check('Playlist → Play opens its first song', (await page.getByRole('heading', { name: 'check-play one' }).count()) === 1 && (await page.locator('[data-play-song]').count()) === 1);
  check('a songs playlist has Next', await page.getByTestId('play-next').isVisible());
  await shot('07-playlist-first-song');
  await page.getByTestId('play-next').click();
  await page.getByRole('heading', { name: 'check-play two' }).waitFor({ timeout: 20000 });
  await waitForSheet();
  check('Next opens the next song', page.url().includes('at=1'));
  check('no Next on the last song', (await page.getByTestId('play-next').count()) === 0);
  await page.waitForTimeout(800);
  await page.keyboard.press('Space');
  await until(async () => (await playing()) === 'true', 8000);
  const stopped = await until(async () => (await playing()) === 'false', 8000);
  check('a stretch starts where it was chosen and stops by itself at its end', stopped);
  await page.getByRole('button', { name: 'All songs' }).click();
  await page.waitForTimeout(800);
  check('All songs draws every song on one page', (await page.locator('[data-play-song]').count()) === 2);
  await shot('08-all-songs');
  await page.getByRole('button', { name: 'One song' }).click();
  await page.getByTestId('play-close').click();
  await page.waitForURL(`**/library/playlists/${playlist.id}?at=1`);
  check('Close goes back to the playlist on the song it was on', true);
  await shot('09-playlist-after-close');

  // 4. Narrow and dark.
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`${base}/play/${copy.id}`);
  await waitForSheet();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  check('390 px: no sideways scroll', overflow <= 0, `${overflow} px`);
  await shot('10-play-390');
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.emulateMedia({ colorScheme: 'dark' });
  await page.evaluate(() => localStorage.setItem('mui-mode', 'dark'));
  await page.goto(`${base}/play/${composed.id}`);
  await waitForSheet();
  await shot('11-play-dark');
  await page.evaluate(() => localStorage.removeItem('mui-mode'));
  await page.emulateMedia({ colorScheme: 'light' });
} finally {
  for (const id of playlists) await fetch(`${api}/playlists/${id}`, { method: 'DELETE' });
  for (const id of songs) await fetch(`${api}/library/songs/${id}`, { method: 'DELETE' });
  for (const id of made) await fetch(`${api}/projects/${id}`, { method: 'DELETE' });
  await page.evaluate(() => localStorage.removeItem('aitu.play.allSongs')).catch(() => undefined);
  const left = (await json(`${api}/projects?layer=vault&layer=private`)).filter(
    (row) => /check-play/.test(row.title) || made.has(row.id),
  ).length;
  const leftSongs = (await json(`${api}/library/songs`)).filter((row) => /check-play/.test(row.title)).length;
  check('nothing the check made is left', left === 0 && leftSongs === 0, `${left} projects, ${leftSongs} songs`);
  await browser.close();
}

const unexpected = problems.filter(
  (line) =>
    !/401 .*\/auth\/me/.test(line) &&
    !/404 .*\/time\/[0-9a-f-]+\/rhythm$/.test(line) &&
    !/Failed to load resource: .* (404)/.test(line),
);
console.log(results.join('\n'));
if (unexpected.length) console.log(`\nProblems:\n${unexpected.slice(0, 20).join('\n')}`);
console.log(`\nScreenshots in ${out}`);
process.exit(results.some((line) => line.includes('FAIL')) || unexpected.length ? 1 : 0);
