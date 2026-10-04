/**
 * Do the Audio tab's cuts follow the backend's rules, and does the player jump where it should?
 *
 * The page edits the cuts before they are saved, so it must keep them in the exact form the backend
 * stores (`normalize_cuts` in `aitu_backend/audio/frames.py`). If the two disagreed, a list the page
 * thinks is unsaved would save as "no change", or the reverse. The same cases as the backend tests
 * are checked here, plus the jumps the player makes over a cut.
 *
 *     npm run check:cuts
 */

import type { Cut } from "../src/api";
import {
  addCut,
  cutAt,
  cutFrames,
  firstKeptFrom,
  jumpTarget,
  keptRanges,
  normalizeCuts,
  overlapsCut,
  restoreRange,
  sameCuts,
} from "../src/audio/cuts";

let failed = 0;
function check(label: string, ok: boolean): void {
  console.log(`${ok ? "  ok  " : "  FAIL"} ${label}`);
  if (!ok) failed += 1;
}
const same = (a: unknown, b: unknown) => JSON.stringify(a) === JSON.stringify(b);

console.log("The backend's normalization");
{
  const cuts: Cut[] = [[50, 60], [10, 20], [15, 30], [30, 35], [90, 200], [5, 5]];
  check("sorted, merged when overlapping or touching, clipped", same(normalizeCuts(cuts, 100), [[10, 35], [50, 60], [90, 100]]));
  check("a range before zero is clipped at zero", same(normalizeCuts([[-5, 3]]), [[0, 3]]));
  check("saving the same cuts twice compares equal", sameCuts(normalizeCuts(cuts, 100), normalizeCuts([...cuts].reverse(), 100)));
}

console.log("\nDelete and Restore");
{
  const one = addCut([], 100, 300, 1000);
  const two = addCut(one, 500, 550, 1000);
  check("Delete adds a cut", same(two, [[100, 300], [500, 550]]));
  check("Delete over the end of a cut joins them", same(addCut(two, 290, 310, 1000), [[100, 310], [500, 550]]));
  check("Restore of a whole cut removes it", same(restoreRange(two, 100, 300), [[500, 550]]));
  check("Restore of the middle of a cut splits it", same(restoreRange(two, 150, 200), [[100, 150], [200, 300], [500, 550]]));
  check("Restore across two cuts trims both", same(restoreRange(two, 250, 520), [[100, 250], [520, 550]]));
  check("Restore where there is no cut changes nothing", same(restoreRange(two, 0, 50), two));
  check("frames removed are counted", cutFrames(two) === 250);
  check("a selection over a cut is seen", overlapsCut(two, 290, 400) && !overlapsCut(two, 300, 500));
  check("the cut under a frame is found", same(cutAt(two, 520), [500, 550]) && cutAt(two, 550) === null);
}

console.log("\nThe frame table, as GET /audio/{uuid}/cuts answers it");
{
  const rows = keptRanges([[100, 310], [500, 550]], 1000);
  check("one row per kept range", rows.length === 3);
  check("the second row is the backend's", same(rows[1], { pieceStart: 100, originalStart: 310, length: 190 }));
  check("no cut is one row, the whole audio", same(keptRanges([], 400), [{ pieceStart: 0, originalStart: 0, length: 400 }]));
  check("a cut at the start leaves the first row at its end", keptRanges([[0, 10]], 100)[0]!.originalStart === 10);
}

console.log("\nWhere the player jumps");
{
  const cuts: Cut[] = [[100, 300], [500, 550]];
  check("inside a cut, it goes to the cut's end", jumpTarget(cuts, 150) === 300);
  check("before a cut, it keeps playing", jumpTarget(cuts, 90) === null);
  check("just before a cut, the lookahead jumps early", jumpTarget(cuts, 99, 2) === 300);
  check("after the last cut, it keeps playing", jumpTarget(cuts, 600, 2) === null);
  check("starting inside a cut starts at its end", firstKeptFrom(cuts, 120, 1000) === 300);
  check("starting in a cut that runs to the end has nowhere to go", firstKeptFrom([[900, 1000]], 950, 1000) === null);
}

console.log(failed === 0 ? "\nEvery check passed.\n" : `\n${failed} check${failed === 1 ? "" : "s"} failed.\n`);
process.exit(failed === 0 ? 0 : 1);
