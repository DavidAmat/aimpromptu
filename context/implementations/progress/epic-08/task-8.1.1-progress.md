# Task 8.1.1 — Piano SVG assets · progress

Status: **done with planned placeholder assets** on 2026-07-27.

## Delivered

- `public/piano/piano-base.svg` (white keys), `piano-black-keys.svg` (all normal black keys),
  `pressed-white-key.svg` and `pressed-black-key.svg`.
- Programmatic geometry for MIDI 21–108: row, EN/ES name, white/black type,
  x/y/width/height and equal-tempered frequency.
- `<Piano>` renders four ordered layers: white base, opaque pressed-white overlays, normal black
  keys, then opaque pressed-black overlays. The same component supports horizontal and
  rotated-vertical view boxes.

The files are the task's explicitly allowed programmatic placeholders. When the illustrator
delivers replacements, their view boxes must remain compatible with the coordinate table.

## Verification and manual trial

Browser verification inspected the live SVG during a sustained C4 and confirmed the DOM order
`piano-base.svg` → `pressed-white-key.svg` → `piano-black-keys.svg`; the console was clean. For the
supervisor trial, play Do#3 + Mi3 + Sol#3 and confirm all three overlays are blue, normal black keys
remain above the pressed Mi3, and pressed black keys remain topmost.
