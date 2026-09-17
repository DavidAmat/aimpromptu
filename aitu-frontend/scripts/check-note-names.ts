/**
 * Does the note toolbox call a note what the sheet calls it?
 *
 * The panel names the note it is about in solfège — `Do 4`, `Do-# 3`, `Re-b 5` — and the one way it
 * can be wrong is to be a *second opinion*. The same black key sounds the same and is written two
 * ways, and which one the page prints depends on the signature sounding at that column; a name
 * worked out from the row alone would say `Do-#` under a notehead drawn as `Re-b`, and a reader
 * would have no way of telling which of the two the page meant.
 *
 * So the name comes from the same `pitchToStaffPosition` the noteheads come from, and this checks
 * the pair end to end. It needs no browser, so it is checked here rather than by clicking.
 *
 *     npm run check:note-names
 */

import { pitchToStaffPosition, type KeySignature } from "@aimpromptu/grid-notation";
import { spanishNoteName } from "../src/music/noteNames";

const passed: string[] = [];
const failed: string[] = [];

function check(name: string, got: string, want: string): void {
  if (got === want) passed.push(`${name} — ${got}`);
  else failed.push(`${name} — got ${got}, wanted ${want}`);
}

/** What the toolbox does, in one line: spell the row against the key, then say it in solfège. */
function named(row: number, keySignature: KeySignature, staffStepOffset = 0): string {
  return spanishNoteName(
    pitchToStaffPosition(row, "right", keySignature, "explicit", undefined, staffStepOffset),
  );
}

// A row is a key of the 88, and `midi = row + 21`. Middle C is midi 60, so row 39 — and it is
// called `Do 4`, the same reckoning the keyboard, the roll and every tooltip already use.
check("middle C", named(39, "C"), "Do 4");
check("the lowest key of the 88", named(0, "C"), "La 0");
check("the highest key of the 88", named(87, "C"), "Do 8");
check("an octave above middle C", named(51, "C"), "Do 5");
check("a white key that is not Do", named(43, "C"), "Mi 4");
check("the Si under middle C", named(38, "C"), "Si 3");

// The half of it that matters. The same key, under a key signature that writes sharps and under one
// that writes flats.
check("a black key in C", named(40, "C"), "Do-# 4");
check("the same black key in D", named(40, "D"), "Do-# 4");
check("the same black key in Ab", named(40, "Ab"), "Re-b 4");
check("the same black key in Eb", named(40, "Eb"), "Re-b 4");
check("a black key in Bb", named(49, "Bb"), "Si-b 4");
check("the same black key in B", named(49, "B"), "La-# 4");

// An octave bracket moves where a note is printed and not what it is. `letter` and `octave` are the
// sounding pitch, so a note under an 8va is called what it sounds, which is what a player asks.
check("a note under an 8va", named(39, "C", -7), "Do 4");
check("a note under a 15mb", named(39, "C", 14), "Do 4");

// The staff a note is drawn on is not part of its name either. A note sent to the other hand keeps
// the one it had.
const onTheRight = spanishNoteName(pitchToStaffPosition(39, "right", "C"));
const onTheLeft = spanishNoteName(pitchToStaffPosition(39, "left", "C"));
check("the same note on either staff", onTheLeft, onTheRight);

for (const name of passed) console.log(`  ✓ ${name}`);
for (const name of failed) console.error(`  ✗ ${name}`);
console.log(`\n${passed.length} passed, ${failed.length} failed`);

if (failed.length > 0) process.exit(1);
