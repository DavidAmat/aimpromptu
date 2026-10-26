/**
 * Copy and paste, and From scratch (implementation 02, Phase 8; on the new sheet since implementation 03, Phase 8B),
 * walked in a headless Chromium.
 *
 * Drives the real page through the running app (`make up`), signed in (`session.mjs`), on
 * **temporary copies** only, deleted at the end, so no project of a library is changed:
 *
 * 1. a stretch of one copy is marked and copied (**Copy** in the range toolbox);
 * 2. it is pasted into another copy at the cursor (**Paste** on the floating bar): its notes, its
 *    audio (a file of its own between the two halves of the target's) and its sheet, one step of undo;
 * 3. undo and redo give the notes and the files back exactly, and the step survives a reload;
 * 4. Command-V pastes over a marked stretch, which becomes cuts of the audio;
 * 5. **New project → From scratch** opens a blank sheet with no step tabs; **Paste** fills it and
 *    the steps appear; a stretch of a version of My library is pasted into it too (across layers);
 * 6. every join of the audio of both is checked sample by sample (`scripts/check_joins.py` in the
 *    backend container), and the browser loads the joined audio at the length of the piece.
 *
 *     npm run check:paste
 *     npm run check:paste -- --target Elefants --source SUPERESTRELLA --out /tmp/paste
 */

import { execFileSync } from 'node:child_process';
import { mkdirSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseArgs } from 'node:util';
import { chromium } from 'playwright';
import { markStretch as markOnSheet, waitForFrames, watchSheets } from './frames-page.mjs';
import { signIn, useSession } from './session.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const { values } = parseArgs({
  options: {
    out: { type: 'string', default: path.join(here, '..', '..', '.run', 'screenshots', 'paste') },
    base: { type: 'string', default: 'http://localhost:5173' },
    source: { type: 'string', default: 'SUPERESTRELLA' },
    target: { type: 'string', default: 'Elefants' },
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
const browser = await chromium.launch();
useSession(browser);
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
watchSheets(page);
const problems = [];
page.on('console', (m) => { if (m.type() === 'error') problems.push(`console: ${m.text()}`); });
page.on('pageerror', (e) => problems.push(`page error: ${e.message}`));
page.on('response', (r) => { if (r.status() >= 400) problems.push(`${r.status()} ${r.url()}`); });
/** Every address the page asked an audio file at, in order. */
const audioRequests = [];
page.on('request', (r) => { if (/\/audio\/[0-9a-f-]+\/file/.test(r.url())) audioRequests.push(r.url()); });
const shot = async (name) => {
  await page.waitForTimeout(400);
  await page.screenshot({ path: path.join(out, `${name}.png`) });
};
const waitForSheet = async () => {
  await page.waitForSelector('[data-sheet-title]', { timeout: 90000 });
  await waitForFrames(page);
  await page.waitForTimeout(300);
};
const notesOf = async (id) => (await json(`${api}/pieces/${id}/notes`)).id.length;
const filesOf = async (id) => (await json(`${api}/audio/${id}/files`)).files;
const statusOf = async (id) => json(`${api}/pieces/${id}/status`);
const stateOf = async (id, step) => (await statusOf(id)).steps.find((one) => one.step === step)?.state;
const undoButton = () => page.getByRole('button', { name: /^Undo/ }).first();
const redoButton = () => page.getByRole('button', { name: /^Redo/ }).first();
/** Wait until the notes of a part are `count`: a paste, an undo, a redo has landed. */
const notesBecome = async (id, count, label) => {
  for (let tries = 0; tries < 60; tries += 1) {
    if ((await notesOf(id)) === count) return true;
    await page.waitForTimeout(500);
  }
  check(label, false, `notes ${await notesOf(id)}, wanted ${count}`);
  return false;
};
/** Mark a stretch of the first line, from `from` to `to` of its columns: the range toolbox opens. */
const markStretch = async (from, to) => {
  await markOnSheet(page, api, { from, to });
  await page.locator('[data-frames-range-toolbox]').waitFor({ timeout: 10000 });
};
const joins = (ids) => {
  try {
    const answer = execFileSync(
      'docker',
      ['compose', 'exec', '-T', 'backend', 'python', 'scripts/check_joins.py', ...ids],
      { cwd: path.join(here, '..', '..'), encoding: 'utf8' },
    );
    return JSON.parse(answer);
  } catch (caught) {
    const text = caught.stdout ? String(caught.stdout) : '';
    try {
      return JSON.parse(text);
    } catch {
      return [{ ok: false, error: String(caught.message).slice(0, 200) }];
    }
  }
};

async function freshCopy(label, name) {
  const vault = await json(`${api}/projects`);
  const original = vault
    // The shortest title that names it: the song itself, not a playlist or a copy made of it.
    .filter((row) => row.step === 'sheet' && row.title.toUpperCase().includes(name.toUpperCase()) && !row.title.includes('(check-'))
    .sort((a, b) => a.title.length - b.title.length)[0];
  if (!original) throw new Error(`No project of the vault named ${name} has its piano sheet`);
  const copy = await send('POST', `${api}/projects/${original.id}/duplicate`, {
    title: `${original.title} (${label})`,
  });
  made.add(copy.id);
  return { id: copy.id, title: copy.title };
}

try {
  const source = await freshCopy('check-paste-source', values.source);
  const target = await freshCopy('check-paste-target', values.target);

  // 1. Copy a stretch of the source.
  await page.goto(`${base}/projects/${source.id}/sheet`);
  await waitForSheet();
  await markStretch(0.35, 0.75);
  await page.getByTestId('range-copy').hover();
  await shot('01-copy');
  await page.getByTestId('range-copy').click();
  const copied = await page.evaluate(() => JSON.parse(window.localStorage.getItem('aitu.clipboard.passage') ?? 'null'));
  check('Copy keeps a reference to the stretch, not its notes', copied?.part === source.id && copied.toMs > copied.fromMs && !('notes' in (copied ?? {})), copied ? `${copied.fromMs}–${copied.toMs} ms` : 'nothing');
  check('Copy says it copied', ((await page.getByTestId('sheet-flash').textContent().catch(() => '')) ?? '').startsWith('Copied'));
  await page.keyboard.press('Escape');

  // 2. Paste it into the target, at the cursor.
  const notesBefore = await notesOf(target.id);
  const filesBefore = await filesOf(target.id);
  const sheetBefore = await stateOf(target.id, 'sheet');
  await page.goto(`${base}/projects/${target.id}/sheet`);
  await waitForSheet();
  const scrub = await page.getByRole('slider', { name: 'Position in the piece' }).boundingBox();
  await page.mouse.click(scrub.x + scrub.width * 0.25, scrub.y + scrub.height / 2);
  await page.getByTestId('sheet-paste').hover();
  await shot('02-paste-tooltip');
  const pasteTitle = await page.getByTestId('sheet-paste').getAttribute('aria-label');
  check('Paste names what it pastes and where', /^Paste “.+” \d+:\d\d – \d+:\d\d at the cursor$/.test(pasteTitle ?? ''), pasteTitle);
  const pasting = page.waitForResponse((r) => /\/sheet\/[^/]+\/paste/.test(r.url()) && r.request().method() === 'POST');
  await page.getByTestId('sheet-paste').click();
  const pasted = await (await pasting).json();
  await waitForSheet();
  const notesAfter = await notesOf(target.id);
  // The live notes of the copied stretch (a note taken off the page travels too, still off the page).
  const sourceNotes = await json(`${api}/pieces/${source.id}/notes`);
  const [fromColumn, toColumn] = [Math.round(copied.fromMs / 40), Math.round(copied.toMs / 40)];
  const live = sourceNotes.onMs.filter((ms) => Math.round(ms / 40) >= fromColumn && Math.round(ms / 40) < toColumn).length;
  check('the passage’s notes are in the target', notesAfter === notesBefore + live && live > 0, `${live} live of ${pasted.notesIn} in, ${pasted.notesMoved} moved`);
  const filesAfter = await filesOf(target.id);
  check(
    'its audio is a file of its own between the two halves of the target’s',
    filesAfter.length === filesBefore.length + 2 && filesAfter[1].kind === 'passage',
    filesAfter.map((file) => `${file.name} (${file.frames})`).join(' | '),
  );
  check('the Sheet step keeps the state it had', (await stateOf(target.id, 'sheet')) === sheetBefore, `${sheetBefore}`);
  check('the Notes step is not made stale by the new audio', (await stateOf(target.id, 'notes')) === 'ready');
  await page.waitForTimeout(600);
  const cursorAt = Number(await page.getByRole('slider', { name: 'Position in the piece' }).getAttribute('aria-valuenow'));
  check('the cursor stays at the start of the pasted passage', Math.abs(cursorAt - pasted.atMs / 1000) < 0.05, `${cursorAt.toFixed(2)} s, pasted at ${(pasted.atMs / 1000).toFixed(2)} s`);
  const undoTitle = await undoButton().getAttribute('aria-label');
  check('one step of the history, called Paste', /^Undo: Paste \d+(\.\d)? s$/.test(undoTitle ?? ''), undoTitle);
  await shot('03-pasted');

  // The audio the sheet's player loads after the paste is the new one, as long as the piece.
  const pieceSeconds = (await json(`${api}/audio/${target.id}`)).durationSeconds;
  const playerUrl = [...audioRequests].reverse().find((url) => url.includes(target.id));
  check('the player asks for the audio at a new address after the paste', Boolean(playerUrl && /[?&]v=\d+\.[1-9]/.test(playerUrl)), playerUrl);
  const played = await page.evaluate(async (url) => {
    const audio = new Audio(url);
    await new Promise((resolve, reject) => {
      audio.addEventListener('loadedmetadata', resolve, { once: true });
      audio.addEventListener('error', reject, { once: true });
    });
    return audio.duration;
  }, playerUrl ?? `${api}/audio/${target.id}/file`);
  check('the browser loads the joined audio at the length of the piece', Math.abs(played - pieceSeconds) < 0.1, `${played.toFixed(2)} s of ${pieceSeconds.toFixed(2)} s`);

  // 3. Undo, redo.
  await undoButton().click();
  if (await notesBecome(target.id, notesBefore, 'undo gives the notes back')) {
    check('undo gives the notes back', true);
  }
  check('undo gives the files back', JSON.stringify(await filesOf(target.id)) === JSON.stringify(filesBefore));
  await waitForSheet();
  await shot('04-undone');
  await redoButton().click();
  if (await notesBecome(target.id, notesAfter, 'redo pastes again')) check('redo pastes again', true);
  check('redo gives the pasted files back', JSON.stringify(await filesOf(target.id)) === JSON.stringify(filesAfter));
  await waitForSheet();

  // 4. Command-V over a marked stretch.
  await markStretch(0.6, 0.8);
  const over = page.waitForResponse((r) => /\/sheet\/[^/]+\/paste/.test(r.url()) && r.request().method() === 'POST');
  await page.keyboard.press('ControlOrMeta+V');
  const overAnswer = await (await over).json();
  await waitForSheet();
  check('Command-V pastes over the marked stretch', overAnswer.notesRemoved > 0 && overAnswer.notesIn === pasted.notesIn, `${overAnswer.notesRemoved} notes out, ${overAnswer.notesIn} in`);
  const cutNow = (await filesOf(target.id)).reduce((sum, file) => sum + file.cutFrames, 0);
  check('the audio of the stretch pasted over becomes cuts the Audio step can restore', cutNow > 0, `${cutNow / 100} s cut`);
  await shot('05-paste-over');
  await page.reload();
  await waitForSheet();
  const afterReload = await undoButton().getAttribute('aria-label');
  check('after a reload the paste is still the step to undo', /^Undo: Paste .* over a stretch$/.test(afterReload ?? ''), afterReload);

  // 5. From scratch.
  await page.goto(`${base}/projects`);
  await page.getByRole('button', { name: 'New project' }).click();
  await page.waitForTimeout(300);
  await shot('06-new-project-menu');
  await page.getByRole('menuitem', { name: /From scratch/ }).click();
  await page.waitForURL(/\/projects\/[0-9a-f-]+\/sheet$/, { timeout: 20000 });
  const scratch = /\/projects\/([0-9a-f-]+)\/sheet$/.exec(page.url())[1];
  made.add(scratch);
  await page.getByText('Nothing to write yet.').waitFor({ timeout: 20000 });
  check('From scratch opens a blank sheet with no step tabs', (await page.locator('[aria-label="Steps"]').count()) === 0);
  check('the blank sheet offers Record and Paste', (await page.getByRole('button', { name: 'Record a passage' }).count()) === 1 && (await page.getByTestId('empty-paste').count()) === 1);
  check('the project is called Untitled project', (await page.getByRole('heading', { level: 1 }).first().textContent())?.includes('Untitled project'));
  await shot('07-scratch-blank');
  await page.getByTestId('empty-paste').click();
  await waitForSheet();
  await page.locator('[aria-label="Steps"]').waitFor({ timeout: 20000 });
  const scratchStatus = await statusOf(scratch);
  check('with a passage pasted, the steps appear', !scratchStatus.scratch && scratchStatus.steps.every((one) => one.state === 'ready'), scratchStatus.steps.map((one) => `${one.step} ${one.state}`).join(', '));
  await shot('08-scratch-pasted');

  // Across layers: a stretch of a version of My library, pasted at the end of the scratch project.
  const songs = await json(`${api}/library/songs`);
  let libraryPart = null;
  for (const song of songs) {
    const detail = await json(`${api}/library/songs/${song.id}`);
    const version = detail.versions.find((one) => one.step !== 'source' && one.step !== 'audio');
    if (version) {
      libraryPart = version.parts[0];
      break;
    }
  }
  if (libraryPart) {
    const end = (await json(`${api}/audio/${scratch}`)).durationSeconds * 1000;
    const fromLibrary = await fetch(`${api}/sheet/${scratch}/paste`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ source: { part: libraryPart, fromMs: 10000, toMs: 14000 }, atMs: Math.round(end / 40) * 40 }),
    });
    check('a stretch of a version of My library pastes into a project', fromLibrary.ok, `${fromLibrary.status}`);
    const into = await fetch(`${api}/sheet/${libraryPart}/paste`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ source: { part: scratch, fromMs: 0, toMs: 1000 }, atMs: 0 }),
    });
    check('a version of My library is never pasted into (it changes through Edit)', into.status === 403, `${into.status}`);
  } else {
    check('a version of My library to copy from', false, 'none with notes');
  }

  // 6. Every join, sample by sample.
  for (const report of joins([target.id, scratch])) {
    const worst = Math.max(0, ...(report.entriesChecked ?? []).flatMap((item) => [item.engine, item.played]));
    check(
      `every join of ${report.part === scratch ? 'the scratch project' : 'the target'} plays its own file`,
      report.ok === true,
      `${report.joins} joins, ${report.seconds} s, worst ${worst}`,
    );
  }

  // Narrow and dark.
  await page.goto(`${base}/projects/${target.id}/sheet`);
  await waitForSheet();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForTimeout(600);
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  check('390 px: no sideways scroll', overflow <= 0, `${overflow} px`);
  await shot('09-sheet-390');
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.emulateMedia({ colorScheme: 'dark' });
  await page.evaluate(() => localStorage.setItem('mui-mode', 'dark'));
  await page.goto(`${base}/projects/${target.id}/sheet`);
  await waitForSheet();
  await page.getByTestId('sheet-paste').hover();
  await shot('10-sheet-dark');
  await page.goto(`${base}/projects`);
  await page.getByRole('button', { name: 'New project' }).click();
  await page.waitForTimeout(300);
  await shot('11-new-project-dark');
  await page.keyboard.press('Escape');
  await page.evaluate(() => localStorage.removeItem('mui-mode'));
  await page.emulateMedia({ colorScheme: 'light' });
} finally {
  for (const id of made) await fetch(`${api}/projects/${id}`, { method: 'DELETE' });
  const left = (await json(`${api}/projects`)).filter(
    (row) => /check-paste/.test(row.title) || made.has(row.id),
  ).length;
  check('nothing the check made is left', left === 0, `${left} projects`);
  await browser.close();
}

// The page asks who is signed in before it is; a version of My library refuses a paste (the check asks for it).
const unexpected = problems.filter(
  (line) =>
    !/401 .*\/auth\/me/.test(line) &&
    !/403 .*\/paste(\?|$)/.test(line) &&
    !/Failed to load resource: .* (403|404)/.test(line),
);
console.log(results.join('\n'));
if (unexpected.length) console.log(`\nProblems:\n${unexpected.slice(0, 20).join('\n')}`);
console.log(`\nScreenshots in ${out}`);
process.exit(results.some((line) => line.includes('FAIL')) || unexpected.length ? 1 : 0);
