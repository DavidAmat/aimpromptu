/**
 * Where a toolbox of the Sheet step opens, measured from what is drawn on the page.
 *
 * Split out of `RhythmPage.tsx` (implementation 02, Phase 2) with no change.
 */

/** How wide the floating toolbox is, and how far it stands off what it is about. */
export const TOOLBOX_WIDTH = 360;
export const TOOLBOX_GAP = 16;
/** Enough of a panel to be worth opening. It is what the bottom of the window is measured against. */
export const TOOLBOX_MIN_HEIGHT = 260;

/**
 * The box on screen that a set of drawn elements takes up, or `null` when none are drawn.
 *
 * Read from the page rather than worked out from frame numbers, because a frame's x depends on the
 * system it wrapped onto, how much is happening in it and where the reader has scrolled — three
 * things the page already knows and this file would only be guessing at.
 */
export function screenBoxOf(selector: string): DOMRect | null {
  const nodes = document.querySelectorAll(selector);
  if (nodes.length === 0) return null;
  let left = Infinity;
  let top = Infinity;
  let right = -Infinity;
  let bottom = -Infinity;
  for (const node of nodes) {
    const box = node.getBoundingClientRect();
    if (box.width === 0 && box.height === 0) continue;
    left = Math.min(left, box.left);
    top = Math.min(top, box.top);
    right = Math.max(right, box.right);
    bottom = Math.max(bottom, box.bottom);
  }
  if (!Number.isFinite(left)) return null;
  return new DOMRect(left, top, right - left, bottom - top);
}

/**
 * The box the marked stretch takes up **on the line it starts on**.
 *
 * The highlight is painted one rectangle per group, and a stretch that wraps paints them on several
 * lines — so taking all of them would union a box the height of the page and leave nowhere clear to
 * open. The reader is looking at where the stretch begins, so that is the fragment the panel is
 * kept clear of. Every rectangle on one line shares a top, which is what they are grouped by.
 */
export function firstLineBoxOf(selector: string): DOMRect | null {
  const nodes = [...document.querySelectorAll(selector)]
    .map((node) => node.getBoundingClientRect())
    .filter((box) => box.width > 0 || box.height > 0);
  const first = nodes[0];
  if (!first) return null;
  const onThatLine = nodes.filter((box) => Math.abs(box.top - first.top) < 2);
  const left = Math.min(...onThatLine.map((box) => box.left));
  const right = Math.max(...onThatLine.map((box) => box.right));
  const top = Math.min(...onThatLine.map((box) => box.top));
  const bottom = Math.max(...onThatLine.map((box) => box.bottom));
  return new DOMRect(left, top, right - left, bottom - top);
}

/**
 * Where to open a toolbox so it sits beside what it is about instead of on top of it.
 *
 * To the right when there is room, otherwise to the left; a panel that covered the notes it edits
 * would have to be dragged away before it could be used, every time. Vertically it starts level
 * with the selection and is pulled back onto the screen if that would run off the bottom.
 */
/**
 * The box a press was on: the whole frame group or notehead if it landed on one, else the point.
 *
 * A toolbox that must not cover what it is about has to know how big that thing is, and the only
 * moment the answer is on the page is the press itself — a frame group's highlight is not painted
 * until a render later.
 */
export function pressedBox(event: {
  target: EventTarget | null;
  clientX: number;
  clientY: number;
}): DOMRect {
  const on = (event.target as Element | null)?.closest?.(
    ".grid-frame-range, .grid-frame-cell, [data-note-target]",
  );
  const box = on?.getBoundingClientRect();
  if (box && (box.width > 0 || box.height > 0)) return box;
  return new DOMRect(event.clientX - 8, event.clientY - 8, 16, 16);
}

/**
 * Where to open the frames toolbox so a range that grows never ends up underneath it.
 *
 * `besideOnScreen` below puts a panel to the right of what it is about, which is right for a set of
 * noteheads: a selection of notes is the size it is. A marked stretch is not. It starts where the
 * reader clicked and they then drag its right-hand handle out to where they actually want it — so a
 * panel to the right is a panel the range grows underneath, and the reader has to drag the panel
 * away before they can finish the gesture they were in the middle of.
 *
 * To the **left** of where the range starts, then, because that is the one side it does not grow
 * towards. When there is no room there — a stretch near the left margin, or a narrow window — it
 * goes **below the staves** instead, left-aligned with the start of the range, which is clear of it
 * in the other axis.
 */
export function clearOfRange(box: DOMRect | null): { x: number; y: number } | undefined {
  if (!box) return undefined;
  // To the left first, because that is the one side a stretch does not grow towards.
  if (box.left >= TOOLBOX_WIDTH + TOOLBOX_GAP * 2) {
    return onScreen(box.left - TOOLBOX_GAP - TOOLBOX_WIDTH, box.top);
  }
  // Then the right. It is the side the stretch grows into, so it is the second choice — but a
  // panel beside the stretch is still better than one on top of it.
  if (window.innerWidth - box.right >= TOOLBOX_WIDTH + TOOLBOX_GAP * 2) {
    return onScreen(box.right + TOOLBOX_GAP, box.top);
  }
  // Neither side has room: a wide stretch, a narrow window, or a magnified page. Below it, held on
  // screen — and at a large enough zoom the stretch covers the window and there is no clear ground
  // left to open on, which is the reader's cue to zoom out or drag the panel where they want it.
  return onScreen(box.left, box.bottom + TOOLBOX_GAP);
}

export function besideOnScreen(
  box: DOMRect | null,
): { x: number; y: number } | undefined {
  if (!box) return undefined;
  const toTheRight = box.right + TOOLBOX_GAP;
  const x =
    toTheRight + TOOLBOX_WIDTH + TOOLBOX_GAP <= window.innerWidth
      ? toTheRight
      : box.left - TOOLBOX_GAP - TOOLBOX_WIDTH;
  return onScreen(x, box.top);
}

/**
 * A panel's top-left corner, held inside the window wherever it was asked for.
 *
 * Both placements above measure something drawn on the sheet, and the sheet can be **magnified**:
 * at 3× a stretch that was 200 pixels wide is 600, and a selection wider or taller than the window
 * is ordinary rather than exotic. Without this the panel was asked to open past the edge of the
 * screen and the browser simply drew it there, so it read as the panel having been lost.
 */
export function onScreen(x: number, y: number): { x: number; y: number } {
  const lastX = Math.max(TOOLBOX_GAP, window.innerWidth - TOOLBOX_WIDTH - TOOLBOX_GAP);
  const lastY = Math.max(TOOLBOX_GAP, window.innerHeight - TOOLBOX_MIN_HEIGHT);
  return {
    x: Math.round(Math.min(Math.max(TOOLBOX_GAP, x), lastX)),
    y: Math.round(Math.min(Math.max(TOOLBOX_GAP, y), lastY)),
  };
}
