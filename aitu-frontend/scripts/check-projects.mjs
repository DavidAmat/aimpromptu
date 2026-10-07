/**
 * The projects of the Personal Vault, walked in a headless Chromium (implementation 02, Phase 5).
 *
 * Drives the real page through the running app (`make up`), signed in (`session.mjs`), and works
 * only on projects it makes itself from small files it writes with ffmpeg, all deleted at the end,
 * so no project of a library is changed:
 *
 * - Projects: the list, **New project** with its three choices (two not built yet) and Import;
 * - From source with an audio file, then **Add audio** on the Audio step (two files end to end, the
 *   join drawn), and the Source step listing the added file;
 * - the row menu: Duplicate, Export (a `.aitu` zip with both audio files), Rename, Delete;
 * - **Import** of that `.aitu` from the New project menu, which opens the new project;
 * - From source with a video file: the project opens on its **Video** step.
 *
 *     npm run check:projects
 *     npm run check:projects -- --out /tmp/projects
 */

import { execFileSync } from 'node:child_process';
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseArgs } from 'node:util';
import { chromium } from 'playwright';
import { signIn, useSession } from './session.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const { values } = parseArgs({
  options: {
    out: { type: 'string', default: path.join(here, '..', '..', '.run', 'screenshots', 'projects') },
    base: { type: 'string', default: 'http://localhost:5173' },
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

// Small files of our own: two tones and a two-second video with sound.
const work = mkdtempSync(path.join(os.tmpdir(), 'aitu-check-projects-'));
const ffmpeg = (...args) => execFileSync('ffmpeg', ['-nostdin', '-v', 'error', '-y', ...args]);
const first = path.join(work, 'check-projects first.wav');
const second = path.join(work, 'check-projects second.wav');
const third = path.join(work, 'check-projects third.wav');
const video = path.join(work, 'check-projects video.mp4');
ffmpeg('-f', 'lavfi', '-i', 'sine=frequency=440:duration=3', first);
ffmpeg('-f', 'lavfi', '-i', 'sine=frequency=660:duration=2', second);
ffmpeg('-f', 'lavfi', '-i', 'sine=frequency=550:duration=1', third);
ffmpeg('-f', 'lavfi', '-i', 'testsrc=size=640x360:rate=10', '-f', 'lavfi', '-i', 'sine=frequency=330', '-t', '2', '-shortest', video);

/** Every project this script made, deleted at the end whatever happens. */
const made = new Set();
const idFromUrl = (url) => /\/projects\/([0-9a-f-]{36})/.exec(url)?.[1] ?? null;
const listed = async () => (await fetch(`${api}/projects`)).json();

const browser = await chromium.launch();
useSession(browser);
const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, acceptDownloads: true });
const problems = [];
page.on('console', (m) => { if (m.type() === 'error') problems.push(`console: ${m.text()}`); });
page.on('pageerror', (e) => problems.push(`page error: ${e.message}`));
page.on('response', (r) => { if (r.status() >= 400) problems.push(`${r.status()} ${r.url()}`); });
const shot = (name) => page.screenshot({ path: path.join(out, `${name}.png`) });
const rowOf = (id) => page.getByTestId(`project-${id}`);
const menuOf = async (id) => {
  await rowOf(id).getByRole('button', { name: 'More actions' }).click();
};

try {
  // 1. The list and the New project menu.
  const before = await listed();
  await page.goto(`${base}/projects`);
  await page.waitForSelector('[role=list]');
  const rows = await page.locator('[data-testid^=project-]').count();
  check('Projects lists every project of the vault', rows === before.length, `${rows} rows, ${before.length} projects`);
  await page.getByRole('button', { name: 'New project' }).click();
  const fromSource = page.getByRole('menuitem', { name: /From source/ });
  await fromSource.waitFor();
  const scratchDisabled = await page.getByRole('menuitem', { name: /From scratch/ }).getAttribute('aria-disabled');
  const otherDisabled = await page.getByRole('menuitem', { name: /From other projects/ }).getAttribute('aria-disabled');
  check('New project offers From source, and From scratch and From other projects not yet', scratchDisabled === 'true' && otherDisabled === 'true');
  check('New project offers Import', (await page.getByRole('menuitem', { name: /Import/ }).count()) === 1);
  await shot('01-new-project-menu');
  await fromSource.click();
  await page.waitForURL('**/projects/new');
  await page.waitForSelector('text=Drop an audio or video file');
  check('From source opens the Source step', true);

  // 2. From source with an audio file, then Add audio.
  await page.locator('input[aria-label="Choose an audio or video file"]').setInputFiles(first);
  await page.waitForURL('**/audio', { timeout: 60000 });
  const audioId = idFromUrl(page.url());
  made.add(audioId);
  await page.waitForSelector('[data-audio][data-files="1"]');
  const one = await (await fetch(`${api}/audio/${audioId}/cuts`)).json();
  check('an uploaded file opens on the Audio step', one.totalFrames === 300, `${one.totalFrames} frames`);
  await page.locator('input[aria-label="Choose an audio file to add"]').setInputFiles(second);
  await page.waitForSelector('[data-audio][data-files="2"]', { timeout: 60000 });
  await page.waitForTimeout(400);
  await shot('02-audio-two-files');
  const two = await (await fetch(`${api}/audio/${audioId}/cuts`)).json();
  check('Add audio puts the second file at the end', two.totalFrames === 500 && two.files.length === 2 && two.files[1].startFrame === 300,
    `${two.totalFrames} frames, files at ${two.files.map((file) => file.startFrame).join(', ')}`);
  check('and the audio revision went up', two.audioRevision === one.audioRevision + 1);
  const original = await fetch(`${api}/audio/${audioId}/file?original=true`);
  check('the Audio step plays both files joined', original.ok && original.headers.get('content-type') === 'audio/flac');
  // 2b. The Source step: the files by name, rename, add, drag to a new place, remove.
  const namesNow = async () => (await (await fetch(`${api}/audio/${audioId}/files`)).json()).files.map((file) => file.name);
  await page.getByRole('tab', { name: 'Source', exact: true }).click();
  await page.waitForSelector('[data-source-files="2"]');
  check('the Source step lists the two files by name', JSON.stringify(await namesNow()) === JSON.stringify(['check-projects first', 'check-projects second']));
  await shot('03-source-two-files');
  await page.locator('[data-file-row="1"]').getByRole('button', { name: 'File actions' }).click();
  await page.getByRole('menuitem', { name: 'Rename' }).click();
  await page.getByLabel('Name').fill('Chorus');
  await page.keyboard.press('Enter');
  await page.waitForSelector('text=Chorus');
  check('Rename gives a file a name', (await namesNow())[1] === 'Chorus');
  await page.locator('input[aria-label="Choose audio files to add"]').setInputFiles(third);
  await page.waitForSelector('[data-source-files="3"]', { timeout: 60000 });
  check('Choose files adds a file at the end', (await namesNow())[2] === 'check-projects third');
  await page.locator('[data-file-row="2"] [draggable="true"]').dragTo(page.locator('[data-file-row="0"]'));
  await page.waitForFunction(async () => document.querySelector('[data-file-row="0"]')?.textContent?.includes('third'), null, { timeout: 15000 }).catch(() => null);
  const dragged = await namesNow();
  check('a file dragged to the top plays first', JSON.stringify(dragged) === JSON.stringify(['check-projects third', 'check-projects first', 'Chorus']), dragged.join(', '));
  await shot('03b-source-three-files');
  await page.locator('[data-file-row="0"]').getByRole('button', { name: 'File actions' }).click();
  await page.getByRole('menuitem', { name: 'Remove' }).click();
  await page.getByRole('button', { name: 'Remove the file' }).click();
  await page.waitForSelector('[data-source-files="2"]', { timeout: 15000 });
  check('Remove takes a file out', JSON.stringify(await namesNow()) === JSON.stringify(['check-projects first', 'Chorus']));
  check('and the notes would have to be made again (the audio changed)', (await (await fetch(`${api}/audio/${audioId}/cuts`)).json()).audioRevision > two.audioRevision);

  // 2c. The Audio step: the panel of files selects one file's part.
  await page.getByRole('tab', { name: 'Audio', exact: true }).click();
  await page.waitForSelector('[data-file-panel]');
  await page.locator('[data-file="1"]').click();
  const picked = await page.locator('[data-audio]').getAttribute('data-selection');
  check('a file of the panel selects its part of the waveform', picked === '300-500', picked ?? '');
  await page.waitForTimeout(400);
  await shot('03c-audio-panel');

  // 3. The row menu: Duplicate, Export, Rename.
  await page.goto(`${base}/projects`);
  await rowOf(audioId).waitFor();
  check('the new project is in the list, at its step', ((await rowOf(audioId).textContent()) ?? '').includes('Audio'));
  await menuOf(audioId);
  await shot('04-row-menu');
  await page.getByRole('menuitem', { name: 'Duplicate' }).click();
  await page.waitForSelector('text=(copy)” added');
  const copy = (await listed()).find((row) => row.title === 'check-projects first (copy)');
  if (copy) made.add(copy.id);
  check('Duplicate adds a copy with the same audio files', Boolean(copy));
  await shot('05-duplicated');

  await menuOf(audioId);
  const downloading = page.waitForEvent('download');
  await page.getByRole('menuitem', { name: 'Export' }).click();
  const download = await downloading;
  const exported = path.join(work, download.suggestedFilename());
  await download.saveAs(exported);
  const zipList = execFileSync('python3', ['-c', 'import sys, zipfile; print("\\n".join(zipfile.ZipFile(sys.argv[1]).namelist()))', exported]).toString();
  const audioFiles = zipList.split('\n').filter((name) => name.startsWith('audio/')).length;
  check('Export saves a .aitu with the project and its two audio files',
    download.suggestedFilename() === 'check-projects first.aitu' && zipList.includes('project.json') && audioFiles === 2,
    `${download.suggestedFilename()}, ${audioFiles} audio files`);

  await menuOf(audioId);
  await page.getByRole('menuitem', { name: 'Rename' }).click();
  await page.getByLabel('Title').fill('check-projects renamed');
  await page.getByRole('button', { name: 'Rename', exact: true }).click();
  await page.waitForSelector('text=check-projects renamed');
  check('Rename changes the title', ((await rowOf(audioId).textContent()) ?? '').includes('check-projects renamed'));

  // 4. Import the exported file.
  await page.getByRole('button', { name: 'New project' }).click();
  await page.getByRole('menuitem', { name: /Import/ }).waitFor();
  await page.keyboard.press('Escape');
  await page.locator('input[aria-label="Choose a .aitu file"]').setInputFiles(exported);
  await page.waitForURL(/\/projects\/[0-9a-f-]{36}\/(audio|source)/, { timeout: 60000 });
  const importedId = idFromUrl(page.url());
  if (importedId) made.add(importedId);
  check('Import opens the new project', importedId !== null && importedId !== audioId);
  const imported = await (await fetch(`${api}/audio/${importedId}/cuts`)).json();
  check('and it has both files', imported.totalFrames === 500 && imported.files.length === 2);

  // 5. Delete, from the row menu.
  await page.goto(`${base}/projects`);
  await rowOf(importedId).waitFor();
  await menuOf(importedId);
  await page.getByRole('menuitem', { name: 'Delete' }).click();
  await shot('06-delete-confirm');
  await page.getByRole('button', { name: 'Delete project' }).click();
  await rowOf(importedId).waitFor({ state: 'detached' });
  const gone = await fetch(`${api}/projects/${importedId}`);
  check('Delete removes the project', gone.status === 404);
  if (gone.status === 404) made.delete(importedId);

  // 6. From source with a video file: the Video step.
  await page.goto(`${base}/projects/new`);
  await page.locator('input[aria-label="Choose an audio or video file"]').setInputFiles(video);
  await page.waitForURL('**/audio', { timeout: 120000 });
  const videoId = idFromUrl(page.url());
  made.add(videoId);
  const videoTab = await page.getByRole('tab', { name: 'Video', exact: true }).waitFor({ timeout: 30000 }).then(() => true, () => false);
  check('a video file opens on the Video step', videoTab);
  await page.waitForSelector('text=Drag the rectangle onto the piano keys', { timeout: 60000 });
  check('its frames are taken out and the piano can be fitted', true);
  await page.waitForTimeout(800);
  await shot('07-video-fit');
  const row = await (await fetch(`${api}/projects/${videoId}`)).json();
  check('the project says it has a video', row.hasVideo === true);
} catch (caught) {
  check('the walk finished', false, caught instanceof Error ? caught.message.split('\n')[0] : String(caught));
} finally {
  await browser.close();
  for (const id of made) {
    if (id) await fetch(`${api}/projects/${id}`, { method: 'DELETE' });
  }
  rmSync(work, { recursive: true, force: true });
}

const after = await listed();
check('nothing this script made is left', after.every((row) => !made.has(row.id) && !row.title.startsWith('check-projects')));

console.log(results.join('\n'));
console.log(problems.length ? `\nProblems:\n${problems.join('\n')}` : '\nNo console error, no failed request.');
const failed = results.filter((line) => line.includes('FAIL')).length;
console.log(failed === 0 ? '\nEvery check passed.\n' : `\n${failed} check${failed === 1 ? '' : 's'} failed.\n`);
process.exit(failed === 0 ? 0 : 1);
