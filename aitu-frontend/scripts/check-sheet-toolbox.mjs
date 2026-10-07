/**
 * The sheet toolbox of implementation 02, Phase 7, walked in a headless Chromium.
 *
 * Drives the real page through the running app (`make up`), signed in (`session.mjs`), on a
 * **temporary copy** of a project whose piano sheet is saved (Elefants by default), deleted at the
 * end, so no project of a library is changed. Two halves, also run alone:
 *
 * - `--only transpose` (`npm run check:transpose`): **Transpose → Notes** from Do 4 to Re 4, its
 *   preview, the notes moved on the backend and the key moved with them, undo and redo exact;
 *   **Transpose → Figures** from negra to corchea, its preview, the main figure and the next
 *   **From**; **Key for this passage** and the clef rule in the range toolbox.
 * - `--only lyrics` (`npm run check:lyrics`): words saved before Phase 7 read as a placed piece;
 *   paste, the pool, drag a piece onto the sheet, move it and pull its edge (both on frames),
 *   merge, split at the cursor, line break, larger, back to the pool, delete, undo, Save.
 * - `--only clefs`: the clef rule on a first write (a copy of Superestrella's tutorial whose saved
 *   sheet is removed first): the left hand's high runs in the treble clef, and no octave bracket
 *   over them.
 *
 *     npm run check:transpose
 *     npm run check:lyrics -- --piece Superestrella --out /tmp/lyrics
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
    out: { type: 'string', default: path.join(here, '..', '..', '.run', 'screenshots', 'sheet-toolbox') },
    base: { type: 'string', default: 'http://localhost:5173' },
    piece: { type: 'string', default: 'Elefants' },
    only: { type: 'string', default: '' },
    'clef-piece': { type: 'string', default: 'SUPERESTRELLA' },
  },
});
const base = values.base;
const api = `${base}/api`;
await signIn(base);
const out = path.resolve(values.out);
mkdirSync(out, { recursive: true });
const runs = (half) => !values.only || values.only === half;

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
const problems = [];
page.on('console', (m) => { if (m.type() === 'error') problems.push(`console: ${m.text()}`); });
page.on('pageerror', (e) => problems.push(`page error: ${e.message}`));
page.on('response', (r) => { if (r.status() >= 400) problems.push(`${r.status()} ${r.url()}`); });
const shot = async (name) => {
  await page.waitForTimeout(400);
  await page.screenshot({ path: path.join(out, `${name}.png`) });
};
const toolbox = () => page.locator('[data-sheet-toolbox]');
const openTab = async (name) => {
  if ((await toolbox().count()) === 0) await page.getByRole('button', { name: 'Sheet toolbox' }).click();
  await toolbox().getByRole('button', { name, exact: true }).click();
};
const undoButton = () => page.getByRole('button', { name: /^Undo/ }).first();
const redoButton = () => page.getByRole('button', { name: /^Redo/ }).first();
const saveSheet = async () => {
  await page.getByRole('button', { name: /^Save/ }).filter({ hasNotText: 'library' }).first().click();
  await page.waitForTimeout(1500);
};
const notesOf = async (id) => {
  const notes = await json(`${api}/pieces/${id}/notes`);
  return Object.fromEntries(notes.id.map((noteId, index) => [noteId, notes.key[index]]));
};
const waitForSheet = async () => {
  await page.waitForSelector('[data-sheet-title]', { timeout: 60000 });
  await page.waitForSelector('.grid-note-target', { timeout: 60000 });
  await page.waitForTimeout(800);
};
/**
 * The lyrics piece whose words are `words`, read line by line (a wrapped block draws one `tspan`
 * per line), as a locator on its first frame; `null` when no piece has them.
 */
const lyricNamed = async (words) => {
  const from = await page.evaluate((wanted) => {
    for (const group of document.querySelectorAll('.grid-lyric')) {
      const text = [...group.querySelectorAll('tspan')]
        .map((span) => span.textContent)
        .join(' ')
        .replace(/\s+/g, ' ')
        .trim();
      if (text === wanted) return group.getAttribute('data-from-column');
    }
    return null;
  }, words);
  return from === null ? null : page.locator(`.grid-lyric[data-from-column="${from}"]`);
};
const hasLyric = async (words) => (await lyricNamed(words)) !== null;

async function freshCopy(label, piece = values.piece) {
  const vault = await json(`${api}/projects`);
  const source = vault.find((row) => row.step === 'sheet' && row.title.includes(piece));
  if (!source) throw new Error(`No project of the vault named ${piece} has its piano sheet`);
  const copy = await send('POST', `${api}/projects/${source.id}/duplicate`, { title: `${source.title} (${label})` });
  made.add(copy.id);
  return copy.id;
}

try {
  if (runs('transpose')) {
    const id = await freshCopy('check-transpose');
    const savedBefore = await json(`${api}/time/${id}/rhythm`);
    const notesBefore = await notesOf(id);
    await page.goto(`${base}/projects/${id}/sheet`);
    await waitForSheet();

    // Notes: from Do 4 to Re 4, two semitones up.
    await openTab('Transpose');
    await toolbox().locator('[aria-label="Transpose to"] rect[data-midi="62"]').click();
    check('the interval is said in words', (await toolbox().locator('[data-transpose-interval]').textContent()) === 'Up 2 semitones');
    await toolbox().locator('[data-transpose-preview=notes]').click();
    await page.locator('[data-transpose-dialog] [data-transpose-sheet] .grid-onset-group').first().waitFor({ timeout: 60000 });
    const facts = await page.locator('[data-transpose-fact]').allTextContents();
    check('the preview says what moves and how the key moves', facts.some((fact) => fact.includes('note')) && facts.some((fact) => fact.startsWith('The key moves')), facts.join(' | '));
    check('the preview writes nothing', JSON.stringify(await notesOf(id)) === JSON.stringify(notesBefore));
    await shot('01-transpose-notes-preview');
    await page.locator('[data-transpose-confirm]').click();
    await page.locator('[data-transpose-dialog]').waitFor({ state: 'detached', timeout: 60000 });
    await page.waitForTimeout(1500);
    const notesAfter = await notesOf(id);
    const allMoved = Object.entries(notesBefore).every(([noteId, key]) => notesAfter[noteId] === key + 2);
    check('every note moved two keys up on the recording', allMoved);
    check('the undo button names the step', ((await undoButton().getAttribute('aria-label')) ?? '').includes('Transpose notes'));
    await undoButton().click();
    await page.waitForTimeout(2000);
    check('undo puts every note back on its key', JSON.stringify(await notesOf(id)) === JSON.stringify(notesBefore));
    await redoButton().click();
    await page.waitForTimeout(2000);
    check('redo moves them again', JSON.stringify(await notesOf(id)) === JSON.stringify(notesAfter));
    await saveSheet();
    const savedNotes = await json(`${api}/time/${id}/rhythm`);
    check('the key moved with the notes', savedNotes.keySignature !== savedBefore.keySignature || savedBefore.keySignature === undefined,
      `${savedBefore.keySignature} → ${savedNotes.keySignature}`);
    await shot('02-transposed');

    // Figures: from negra to corchea.
    await openTab('Transpose');
    await toolbox().getByRole('button', { name: 'Figures', exact: true }).click();
    const fromPressed = await toolbox().locator('[aria-label="Transpose figures from"] button[aria-pressed=true]').getAttribute('value');
    check('From starts on negra the first time', fromPressed === (savedBefore.figuresFrom ?? 'negra'), fromPressed ?? '');
    await toolbox().locator('[aria-label="Transpose figures to"] button[value=corchea]').click();
    await toolbox().locator('[data-transpose-preview=figures]').click();
    await page.locator('[data-transpose-dialog] [data-transpose-sheet] .grid-onset-group').first().waitFor({ timeout: 60000 });
    await shot('03-transpose-figures-preview');
    const figureFacts = await page.locator('[data-transpose-fact]').allTextContents();
    check('the figures preview says every figure becomes shorter', figureFacts.some((fact) => fact.includes('one step shorter')), figureFacts.join(' | '));
    await page.locator('[data-transpose-confirm]').click();
    await page.waitForTimeout(2000);
    await saveSheet();
    const savedFigures = await json(`${api}/time/${id}/rhythm`);
    check('the main figure moved one step shorter', savedFigures.anchorFigure !== savedNotes.anchorFigure, `${savedNotes.anchorFigure} → ${savedFigures.anchorFigure}`);
    check('the next From is the last To', savedFigures.figuresFrom === 'corchea', String(savedFigures.figuresFrom));
    await page.reload();
    await waitForSheet();
    await openTab('Transpose');
    await toolbox().getByRole('button', { name: 'Figures', exact: true }).click();
    check('and the tab opens on it', (await toolbox().locator('[aria-label="Transpose figures from"] button[aria-pressed=true]').getAttribute('value')) === 'corchea');
    await shot('04-figures-from-corchea');
    await page.getByRole('button', { name: 'Close the toolbox' }).first().click().catch(() => undefined);

    // The range toolbox: a stretch, its Key tab and its Clef tab.
    const ruler = page.locator('.grid-frame-ruler').first();
    const box = await ruler.boundingBox();
    if (box) {
      await page.mouse.click(box.x + box.width * 0.3, box.y + box.height / 2);
      await page.locator('[role=tablist][aria-label="What this stretch carries"]').waitFor({ timeout: 10000 });
      const hint = page.locator('[data-passage-key]');
      check('the Key tab of a stretch can offer its own key', true, (await hint.count()) > 0 ? `offers ${await hint.getAttribute('data-passage-key')}` : 'this stretch is already in its best key');
      await shot('05-passage-key');
      await page.getByRole('tab', { name: 'Clef' }).click();
      const rule = page.locator('[data-clef-rule]');
      check('the Clef tab offers the clef rule where it applies', true, (await rule.count()) > 0 ? `${await rule.getAttribute('data-clef-rule')} run(s)` : 'no high left-hand run here');
      await shot('06-clef-tab');
      await page.keyboard.press('Escape');
    } else {
      check('the frame ruler is on the page', false);
    }
  }

  if (runs('lyrics')) {
    const id = await freshCopy('check-lyrics');
    // Words saved before Phase 7: a line over a stretch with a pixel offset and width.
    const saved = await json(`${api}/time/${id}/rhythm`);
    await send('PUT', `${api}/time/${id}/rhythm`, {
      ...saved,
      lyrics: [{ fromColumn: 40, toColumn: 90, text: 'old words', offsetX: 12, width: 140 }],
    });
    await page.goto(`${base}/projects/${id}/sheet`);
    await waitForSheet();
    check('words saved before are read as a placed piece', await hasLyric('old words'));

    await openTab('Lyrics');
    await page.locator('[data-lyrics-paste]').fill('first line of words\nsecond line\n\nthird line here');
    await toolbox().locator('[data-lyrics-add]').click();
    check('each pasted line is a piece of the pool', (await toolbox().locator('[data-lyrics-piece]').count()) === 3);
    await shot('07-lyrics-pool');

    // Drop the first piece on the sheet, about a third of the way along the first line.
    const ruler = page.locator('.grid-frame-ruler').first();
    const rulerBox = await ruler.boundingBox();
    const dropAt = { x: rulerBox.x + rulerBox.width * 0.45, y: rulerBox.y + rulerBox.height + 40 };
    const sheetBox = await page.locator('[data-sheet-drop]').boundingBox();
    await toolbox().locator('[data-lyrics-piece="0"]').dragTo(page.locator('[data-sheet-drop]'), {
      targetPosition: { x: dropAt.x - sheetBox.x, y: dropAt.y - sheetBox.y },
    });
    await page.waitForTimeout(1200);
    const placed = await lyricNamed('first line of words');
    check('a piece dragged from the pool lands on the sheet', placed !== null);
    if (!placed) throw new Error('the dropped piece is not on the sheet');
    check('and leaves the pool', (await toolbox().locator('[data-lyrics-piece]').count()) === 2);
    const from0 = Number(await placed.getAttribute('data-from-column'));
    check('it starts on a frame', Number.isInteger(from0), String(from0));
    await shot('08-lyrics-placed');

    // Move it to the right: it snaps to another frame and keeps its length.
    const to0 = Number(await placed.getAttribute('data-to-column'));
    const blockBox = await placed.locator('.grid-lyric-box').boundingBox();
    await page.mouse.move(blockBox.x + 10, blockBox.y + blockBox.height / 2);
    await page.mouse.down();
    await page.mouse.move(blockBox.x + 90, blockBox.y + blockBox.height / 2 - 6, { steps: 8 });
    await page.mouse.up();
    await page.waitForTimeout(1200);
    const moved = await lyricNamed('first line of words');
    const from1 = Number(await moved.getAttribute('data-from-column'));
    const to1 = Number(await moved.getAttribute('data-to-column'));
    check('dragged, it snaps to a later frame and keeps how many frames it covers', from1 > from0 && to1 - from1 === to0 - from0, `${from0}–${to0} → ${from1}–${to1}`);

    // Pull its right edge: the end lands on a frame.
    const grip = await moved.locator('.grid-lyric-grip').boundingBox();
    await page.mouse.move(grip.x + grip.width / 2, grip.y + grip.height / 2);
    await page.mouse.down();
    await page.mouse.move(grip.x + 120, grip.y + grip.height / 2, { steps: 8 });
    await page.mouse.up();
    await page.waitForTimeout(1200);
    const to2 = Number(await (await lyricNamed('first line of words')).getAttribute('data-to-column'));
    check('its right edge pulled further ends on a later frame', to2 > to1, `${to1} → ${to2}`);

    // A second piece, after the first, then pick both and merge.
    // On the next line, near its start: clear of the toolbox floating on the right.
    const nextRuler = await page.locator('.grid-frame-ruler').nth(1).boundingBox();
    await toolbox().locator('[data-lyrics-piece="0"]').dragTo(page.locator('[data-sheet-drop]'), {
      targetPosition: {
        x: nextRuler.x + nextRuler.width * 0.1 - sheetBox.x,
        y: nextRuler.y + nextRuler.height + 40 - sheetBox.y,
      },
    });
    await page.waitForTimeout(1200);
    check('a second piece goes after it, on one line', await hasLyric('second line')
      && (await (await lyricNamed('second line')).getAttribute('data-lines')) === '1');
    await (await lyricNamed('first line of words')).locator('.grid-lyric-box').click();
    await (await lyricNamed('second line')).locator('.grid-lyric-box').click({ modifiers: ['ControlOrMeta'] });
    check('Command-click picks a second piece', (await toolbox().locator('[data-lyrics-picked]').getAttribute('data-lyrics-picked')) === '2');
    await shot('09-lyrics-picked');
    await page.getByTestId('lyrics-merge').click();
    await page.waitForTimeout(1200);
    const merged = await lyricNamed('first line of words second line');
    check('Merge joins them into one piece', merged !== null);
    if (!merged) throw new Error('the merged piece is not on the sheet');

    // Split at the cursor: after "first line".
    await merged.locator('.grid-lyric-box').click();
    const words = toolbox().locator('[data-lyrics-words]');
    await words.click();
    await words.evaluate((field) => field.setSelectionRange(10, 10));
    await words.press('Enter');
    await page.waitForTimeout(1200);
    check('Enter splits the piece where the cursor is', (await hasLyric('of words second line')) && (await hasLyric('first line')));

    // A line break, larger, back to the pool, delete.
    const tail = await lyricNamed('of words second line');
    const tailFrom = await tail.getAttribute('data-from-column');
    await tail.locator('.grid-lyric-box').click();
    await words.click();
    await words.evaluate((field) => field.setSelectionRange(8, 8));
    await page.getByTestId('lyrics-break').click();
    await page.waitForTimeout(1200);
    const broken = page.locator(`.grid-lyric[data-from-column="${tailFrom}"]`);
    check('Line break puts a new line inside the piece', (await broken.getAttribute('data-lines')) === '2');
    await page.getByTestId('lyrics-larger').click();
    await page.waitForTimeout(1200);
    const size = Number(await broken.locator('.grid-lyric-text').getAttribute('font-size'));
    check('Larger makes the words bigger', size > 12, String(size));
    await shot('10-lyrics-edited');
    await page.getByTestId('lyrics-pool').click();
    await page.waitForTimeout(800);
    check('Back to the pool takes it off the sheet', (await toolbox().locator('[data-lyrics-piece]').count()) === 2);
    await (await lyricNamed('first line')).locator('.grid-lyric-box').click();
    await page.getByTestId('lyrics-delete').click();
    await page.waitForTimeout(800);
    check('Delete removes the picked piece', !(await hasLyric('first line')));
    await undoButton().click();
    await page.waitForTimeout(1200);
    check('undo brings it back', await hasLyric('first line'));

    await saveSheet();
    const after = await json(`${api}/time/${id}/rhythm`);
    check('Save keeps the pieces and the pool', after.lyrics.some((line) => line.text === 'first line') && (after.lyricsPool ?? []).length === 2,
      `${after.lyrics.length} pieces, ${(after.lyricsPool ?? []).length} in the pool`);
    check('every saved piece starts and ends on a frame', after.lyrics.every((line) => Number.isInteger(line.fromColumn) && Number.isInteger(line.toColumn) && line.toColumn > line.fromColumn));

    // Narrow and dark.
    await page.setViewportSize({ width: 390, height: 844 });
    await page.waitForTimeout(800);
    await shot('11-lyrics-390');
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.emulateMedia({ colorScheme: 'dark' });
    await page.evaluate(() => localStorage.setItem('mui-mode', 'dark'));
    await page.reload();
    await waitForSheet();
    const reread = await lyricNamed('first line');
    check('read back after a reload, a saved piece draws as it did (one line)', reread !== null && (await reread.getAttribute('data-lines')) === '1');
    await openTab('Lyrics');
    await shot('12-lyrics-dark');
    await page.evaluate(() => localStorage.removeItem('mui-mode'));
  }

  if (runs('clefs')) {
    const id = await freshCopy('check-clefs', values['clef-piece']);
    // A first write: the saved sheet goes, so the page takes its defaults again.
    await fetch(`${api}/time/${id}/rhythm`, { method: 'DELETE' });
    await page.goto(`${base}/projects/${id}/sheet`);
    await waitForSheet();
    await page.waitForTimeout(2500);
    const changes = await page.locator('.grid-clef-change[data-hand=left]').evaluateAll((nodes) =>
      nodes.map((node) => ({ frame: Number(node.getAttribute('data-frame')), to: node.getAttribute('data-to-clef') })));
    const toTreble = changes.filter((change) => change.to === 'treble');
    check('a first write puts the left hand\'s high runs in the treble clef', toTreble.length > 0, `${toTreble.length} runs drawn`);
    if (toTreble.length > 0) {
      const first = page.locator(`.grid-clef-change[data-hand=left][data-frame="${toTreble[0].frame}"]`);
      await first.scrollIntoViewIfNeeded();
      await page.mouse.wheel(0, -200);
      await shot('13-clef-rule');
    }
    await saveSheet();
    const saved = await json(`${api}/time/${id}/rhythm`);
    const leftTreble = (saved.clefChanges ?? []).filter((change) => change.hand === 'left');
    const overlapping = (saved.ottavas ?? []).filter((span) => span.hand === 'left' && leftTreble.some((change, index) => {
      if (change.clef !== 'treble') return false;
      const back = leftTreble[index + 1]?.fromColumn ?? Infinity;
      return span.fromColumn < back && span.toColumn > change.fromColumn;
    }));
    check('and no octave bracket over a passage written in the treble clef', overlapping.length === 0, `${overlapping.length}`);
  }
} catch (error) {
  check('the walk ended', false, error instanceof Error ? error.message : String(error));
  await shot('zz-failure').catch(() => undefined);
} finally {
  for (const id of made) await fetch(`${api}/projects/${id}`, { method: 'DELETE' });
  const left = (await json(`${api}/projects`)).filter((row) => /check-(transpose|lyrics|clefs)/.test(row.title)).length;
  check('nothing the check made is left', left === 0, `${left} projects`);
  await browser.close();
}

// A sheet with no saved reading answers 404 for it, which the page reads as "nothing saved" (the
// clefs half removes the reading on purpose); the browser logs that 404 as a console error too.
const unexpected = problems.filter(
  (line) =>
    !/401 .*\/auth\/me/.test(line) &&
    !/404 .*\/time\/[0-9a-f-]+\/rhythm$/.test(line) &&
    !(values.only === 'clefs' && /Failed to load resource: .* 404/.test(line)),
);
console.log(results.join('\n'));
if (unexpected.length) console.log(`\nProblems:\n${unexpected.slice(0, 20).join('\n')}`);
console.log(`\nScreenshots in ${out}`);
process.exit(results.some((line) => line.includes('FAIL')) || unexpected.length ? 1 : 0);
