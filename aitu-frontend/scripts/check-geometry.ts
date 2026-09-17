/**
 * Do the two services build the same piano overlay?
 *
 * One module owns the geometry and the backend and the frontend agree on its
 * shape. They cannot literally share the code: the calibration UI redraws the
 * overlay on every drag of a handle, and a round trip per drag is not a UI. So
 * `src/video/overlayGeometry.ts` is a twin of
 * `aitu-backend/src/aitu_backend/video/geometry.py`, and twins drift.
 *
 * Neither typecheck nor lint can see that drift, and neither can the app: a key
 * border a pixel to the left of where the detector looks for it produces a
 * calibration that looks right on screen and reads the wrong lane. So both
 * sides assert against one fixture, and this is the frontend half. The fixture
 * holds two cases since implementation 05: a straight whole piano, and a
 * rectangle at an angle whose white keys widen from left to right.
 *
 *     npm run check:geometry
 *
 * Regenerate the fixture from the backend when the geometry changes on purpose:
 * `cd aitu-backend && uv run python scripts/build_geometry_fixture.py`.
 */

import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import type { Calibration, KeyLane, PianoKey } from "../src/api/frameExamples";
import { buildKeys, buildLanes } from "../src/video/overlayGeometry";

const here = path.dirname(fileURLToPath(import.meta.url));
const FIXTURE = path.resolve(
  here,
  "../../aitu-backend/tests/fixtures/video/geometry-fixture.json",
);

interface Case {
  name: string;
  calibration: Calibration;
  margin: number;
  keys: PianoKey[];
  lanes: KeyLane[];
}

interface Fixture {
  cases: Case[];
}

/** Pixels. The two languages round a float the same way; this is for the printer. */
const TOLERANCE = 1e-9;

function fail(message: string): never {
  console.error(`✗ ${message}`);
  process.exit(1);
}

function compareNumbers(what: string, mine: number, theirs: number): void {
  if (Math.abs(mine - theirs) > TOLERANCE) {
    fail(`${what}: the frontend says ${mine}, the backend says ${theirs}`);
  }
}

const fixture = JSON.parse(readFileSync(FIXTURE, "utf8")) as Fixture;
if (!fixture.cases?.length) fail("the fixture holds no cases");

for (const one of fixture.cases) {
  const keys = buildKeys(one.calibration);
  const lanes = buildLanes(one.calibration, one.margin);
  const tag = `[${one.name}]`;

  if (keys.length !== one.keys.length) {
    fail(`${tag} the frontend built ${keys.length} keys and the backend built ${one.keys.length}`);
  }
  if (lanes.length !== one.lanes.length) {
    fail(`${tag} the frontend built ${lanes.length} lanes and the backend built ${one.lanes.length}`);
  }

  one.keys.forEach((theirs, index) => {
    const mine = keys[index];
    if (mine.midi !== theirs.midi) fail(`${tag} key ${index}: midi ${mine.midi} against ${theirs.midi}`);
    if (mine.kind !== theirs.kind) fail(`${tag} key ${theirs.midi}: ${mine.kind} against ${theirs.kind}`);
    if (mine.nameEn !== theirs.nameEn) {
      fail(`${tag} key ${theirs.midi}: named ${mine.nameEn} against ${theirs.nameEn}`);
    }
    if (mine.nameEs !== theirs.nameEs) {
      fail(`${tag} key ${theirs.midi}: named ${mine.nameEs} against ${theirs.nameEs}`);
    }
    compareNumbers(`${tag} key ${theirs.midi} left`, mine.left, theirs.left);
    compareNumbers(`${tag} key ${theirs.midi} right`, mine.right, theirs.right);
    compareNumbers(`${tag} key ${theirs.midi} mid`, mine.mid, theirs.mid);
  });

  one.lanes.forEach((theirs, index) => {
    const mine = lanes[index];
    if (mine.midi !== theirs.midi) fail(`${tag} lane ${index}: midi ${mine.midi} against ${theirs.midi}`);
    compareNumbers(`${tag} lane ${theirs.midi} x0`, mine.x0, theirs.x0);
    compareNumbers(`${tag} lane ${theirs.midi} x1`, mine.x1, theirs.x1);
  });

  console.log(
    `✓ ${tag} the two services build the same overlay: ${keys.length} keys, ` +
      `${keys[0].nameEn} to ${keys[keys.length - 1].nameEn}, ` +
      `and ${lanes.length} lanes at a margin of ${one.margin} white key widths`,
  );
}
