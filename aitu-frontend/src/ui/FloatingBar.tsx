/**
 * A row of actions that floats over the page, is dragged where you want it, and can be put away
 * (plan section 7.4): a white pill with the one shadow of floating things.
 *
 * Some decisions about a piece are made at the top of the screen and paid for at the bottom of it.
 * The sheet runs for pages, and the buttons that keep or discard what you just did to it sat in one
 * fixed place, so using them meant scrolling the sheet out of sight, pressing, and scrolling back.
 * A bar that stays on screen removes the round trip entirely.
 *
 * It is deliberately not a toolbox: no title bar, no panel, nothing to read. Just the controls, a
 * grip to move them by, and a way to get them out from in front of the notes. Hiding it leaves a
 * small round button with an eye where the hide button was (under the pointer that hid it), because
 * a control that vanishes with no way back is worse than one in the way. Implementation 04, Phase 1:
 * that button sat at the bar's left end, white on the notes, with a lightning icon, and the user
 * found no way back; a page may also hold the hidden state itself (`hidden`, `onHiddenChange`) to
 * bring the bar back from a button of its own.
 */

import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import Fab from "@mui/material/Fab";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import Tooltip from "@mui/material/Tooltip";
import DragIndicatorIcon from "@mui/icons-material/DragIndicator";
import VisibilityIcon from "@mui/icons-material/VisibilityOutlined";
import VisibilityOffIcon from "@mui/icons-material/VisibilityOffOutlined";
import { shadow } from "./tokens";

export interface FloatingBarProps {
  /** Whether the bar is on the page at all. Hiding it is the reader's business, not this flag's. */
  open: boolean;
  /** What the bar is, said once — the tooltip on the grip and on the button that brings it back. */
  label: string;
  /** The controls. Buttons and icon buttons, kept short enough to read as one row. */
  children: ReactNode;
  /** Put away, when the page holds that state (it then also shows it again); else the bar holds it. */
  hidden?: boolean;
  onHiddenChange?: (hidden: boolean) => void;
}

/** Kept on screen: a bar dragged off the edge cannot be dragged back. */
const MARGIN = 8;
/** How far in from the bottom right corner it starts, clear of the window's own edges. */
const INSET = 24;
/** Under the toolboxes (1300): the panel you are working in should never end up behind this. */
const Z = 1200;
/** The small round button left behind (MUI's small Fab). */
const FAB = 40;

export function FloatingBar({
  open,
  label,
  children,
  hidden: heldHidden,
  onHiddenChange,
}: FloatingBarProps) {
  const [position, setPosition] = useState<{ x: number; y: number } | null>(
    null,
  );
  const [ownHidden, setOwnHidden] = useState(false);
  const hidden = heldHidden ?? ownHidden;
  const setHidden = (next: boolean) => {
    setOwnHidden(next);
    onHiddenChange?.(next);
  };
  // The bar's size when it was last drawn: the button left behind goes to its right end.
  const [drawn, setDrawn] = useState<{ width: number; height: number }>({
    width: 320,
    height: 48,
  });
  const node = useRef<HTMLDivElement | null>(null);

  /** Where it may sit, measured from what is actually drawn rather than from a guessed width. */
  const clamp = useCallback((x: number, y: number) => {
    const width = node.current?.offsetWidth ?? 320;
    const height = node.current?.offsetHeight ?? 48;
    const maxX = Math.max(MARGIN, window.innerWidth - width - MARGIN);
    const maxY = Math.max(MARGIN, window.innerHeight - height - MARGIN);
    return {
      x: Math.min(Math.max(MARGIN, x), maxX),
      y: Math.min(Math.max(MARGIN, y), maxY),
    };
  }, []);

  // The first place it sits is the bottom right corner, which needs its drawn size and so cannot be
  // worked out before it exists (a bar hidden from the start is placed when it is first shown).
  // Measured and placed before the browser paints, so it is never seen in the top left for a frame
  // on the way there.
  useLayoutEffect(() => {
    if (!open || hidden || position || !node.current) return;
    const { offsetWidth: width, offsetHeight: height } = node.current;
    setPosition(
      clamp(
        window.innerWidth - width - INSET,
        window.innerHeight - height - INSET,
      ),
    );
  }, [open, hidden, position, clamp]);

  // A window made smaller must not take the bar with it off the edge, and neither must a bar that
  // grows: its words change ("1 note moved" becomes "1 note moved, 1 deleted, 1 added"), and the
  // part pushed past the edge is the Save button.
  useEffect(() => {
    const onResize = () => {
      const bar = node.current;
      if (bar) {
        setDrawn((was) =>
          was.width === bar.offsetWidth && was.height === bar.offsetHeight
            ? was
            : { width: bar.offsetWidth, height: bar.offsetHeight },
        );
      }
      setPosition((at) => {
        if (!at) return at;
        const next = clamp(at.x, at.y);
        return next.x === at.x && next.y === at.y ? at : next;
      });
    };
    onResize();
    window.addEventListener("resize", onResize);
    const bar = node.current;
    const observer = bar ? new ResizeObserver(onResize) : null;
    if (bar) observer?.observe(bar);
    return () => {
      window.removeEventListener("resize", onResize);
      observer?.disconnect();
    };
  }, [clamp, open, hidden]);

  /**
   * Start a drag, listening on the window rather than on the grip.
   *
   * The pointer leaves the grip as soon as it moves faster than the bar follows, and a listener on
   * the grip itself would stop hearing about it there. Both pointer and mouse events are taken,
   * because not every way of driving a page sends the first kind.
   */
  const beginDrag = useCallback(
    (clientX: number, clientY: number) => {
      const at = position ?? { x: 0, y: 0 };
      const grab = { dx: clientX - at.x, dy: clientY - at.y };
      const move = (event: PointerEvent | MouseEvent) => {
        setPosition(clamp(event.clientX - grab.dx, event.clientY - grab.dy));
      };
      const drop = () => {
        window.removeEventListener("pointermove", move);
        window.removeEventListener("mousemove", move);
        window.removeEventListener("pointerup", drop);
        window.removeEventListener("mouseup", drop);
      };
      window.addEventListener("pointermove", move);
      window.addEventListener("mousemove", move);
      window.addEventListener("pointerup", drop);
      window.addEventListener("mouseup", drop);
    },
    [position, clamp],
  );

  if (!open) return null;

  // Hidden, it is the same thing in the same place, small enough to see the notes under it: at the
  // bar's right end, where its hide button was, so the pointer that hid it is already on it. Coming
  // back where it was left is the point: a reader who moved it out of the way of one passage looks
  // for it there, not in whatever corner it was born in.
  if (hidden) {
    // Never shown yet: in the bottom right corner, where the bar will be born.
    const at = position ?? {
      x: window.innerWidth - drawn.width - INSET,
      y: window.innerHeight - drawn.height - INSET,
    };
    const left = Math.min(
      Math.max(MARGIN, at.x + drawn.width - FAB),
      window.innerWidth - FAB - MARGIN,
    );
    const top = Math.min(
      Math.max(MARGIN, at.y + (drawn.height - FAB) / 2),
      window.innerHeight - FAB - MARGIN,
    );
    return (
      <Tooltip title={`Show ${label}`} placement="left">
        <Fab
          size="small"
          aria-label={`Show ${label}`}
          onClick={() => setHidden(false)}
          data-floating-show
          sx={{
            position: "fixed",
            left: `${left}px`,
            top: `${top}px`,
            zIndex: Z,
            color: "text.secondary",
            backgroundColor: "background.paper",
            border: "1px solid",
            borderColor: "divider",
            boxShadow: shadow.float,
          }}
        >
          <VisibilityIcon fontSize="small" />
        </Fab>
      </Tooltip>
    );
  }

  return (
    <Paper
      ref={node}
      elevation={0}
      sx={{
        position: "fixed",
        left: `${position?.x ?? MARGIN}px`,
        top: `${position?.y ?? MARGIN}px`,
        zIndex: Z,
        borderRadius: "24px",
        boxShadow: shadow.float,
        // On a narrow screen the row wraps rather than run off the edge.
        maxWidth: `calc(100vw - ${2 * MARGIN}px)`,
        border: "1px solid",
        borderColor: "divider",
        // Nothing here is text to read, and a stray double click while dragging should not select
        // the labels on the buttons.
        userSelect: "none",
      }}
    >
      <Stack
        direction="row"
        sx={{ alignItems: "center", px: 1, py: 0.75, gap: 1, flexWrap: "wrap" }}
      >
        <Tooltip title={`Drag to move ${label}`} placement="top">
          <DragIndicatorIcon
            fontSize="small"
            onPointerDown={(event) => beginDrag(event.clientX, event.clientY)}
            onMouseDown={(event) => beginDrag(event.clientX, event.clientY)}
            sx={{
              color: "text.disabled",
              cursor: "grab",
              "&:active": { cursor: "grabbing" },
            }}
          />
        </Tooltip>
        {children}
        <Tooltip title="Hide these buttons" placement="top">
          <VisibilityOffIcon
            fontSize="small"
            role="button"
            aria-label={`Hide ${label}`}
            data-floating-hide
            tabIndex={0}
            onClick={() => setHidden(true)}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") setHidden(true);
            }}
            sx={{ color: "text.disabled", cursor: "pointer" }}
          />
        </Tooltip>
      </Stack>
    </Paper>
  );
}

export default FloatingBar;
