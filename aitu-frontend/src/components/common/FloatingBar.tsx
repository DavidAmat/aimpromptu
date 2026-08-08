/**
 * A row of actions that floats over the page, is dragged where you want it, and can be put away.
 *
 * Some decisions about a piece are made at the top of the screen and paid for at the bottom of it.
 * The sheet runs for pages, and the buttons that keep or discard what you just did to it sat in one
 * fixed place, so using them meant scrolling the sheet out of sight, pressing, and scrolling back.
 * A bar that stays on screen removes the round trip entirely.
 *
 * It is deliberately not a toolbox: no title bar, no panel, nothing to read. Just the controls, a
 * grip to move them by, and a way to get them out from in front of the notes. Hiding it leaves the
 * grip behind as a small button in the same place, because a control that vanishes with no way back
 * is worse than one in the way.
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
import VisibilityOffIcon from "@mui/icons-material/VisibilityOffOutlined";
import BoltIcon from "@mui/icons-material/BoltOutlined";

export interface FloatingBarProps {
  /** Whether the bar is on the page at all. Hiding it is the reader's business, not this flag's. */
  open: boolean;
  /** What the bar is, said once — the tooltip on the grip and on the button that brings it back. */
  label: string;
  /** The controls. Buttons and icon buttons, kept short enough to read as one row. */
  children: ReactNode;
}

/** Kept on screen: a bar dragged off the edge cannot be dragged back. */
const MARGIN = 8;
/** How far in from the bottom right corner it starts, clear of the window's own edges. */
const INSET = 24;
/** Under the toolboxes (1300): the panel you are working in should never end up behind this. */
const Z = 1200;

export function FloatingBar({ open, label, children }: FloatingBarProps) {
  const [position, setPosition] = useState<{ x: number; y: number } | null>(
    null,
  );
  const [hidden, setHidden] = useState(false);
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
  // worked out before it exists. Measured and placed before the browser paints, so it is never seen
  // in the top left for a frame on the way there.
  useLayoutEffect(() => {
    if (!open || position || !node.current) return;
    const { offsetWidth: width, offsetHeight: height } = node.current;
    setPosition(
      clamp(
        window.innerWidth - width - INSET,
        window.innerHeight - height - INSET,
      ),
    );
  }, [open, position, clamp]);

  // A window made smaller must not take the bar with it off the edge.
  useEffect(() => {
    const onResize = () =>
      setPosition((at) => (at ? clamp(at.x, at.y) : at));
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, [clamp]);

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

  // Hidden, it is the same thing in the same place, small enough to see the notes under it. Coming
  // back where it was left is the point: a reader who moved it out of the way of one passage looks
  // for it there, not in whatever corner it was born in.
  if (hidden) {
    return (
      <Tooltip title={`Show ${label}`} placement="left">
        <Fab
          size="small"
          color="primary"
          aria-label={`Show ${label}`}
          onClick={() => setHidden(false)}
          sx={{
            position: "fixed",
            left: `${position?.x ?? MARGIN}px`,
            top: `${position?.y ?? MARGIN}px`,
            zIndex: Z,
          }}
        >
          <BoltIcon fontSize="small" />
        </Fab>
      </Tooltip>
    );
  }

  return (
    <Paper
      ref={node}
      elevation={8}
      sx={{
        position: "fixed",
        left: `${position?.x ?? MARGIN}px`,
        top: `${position?.y ?? MARGIN}px`,
        zIndex: Z,
        borderRadius: 6,
        border: "1px solid",
        borderColor: "divider",
        // Nothing here is text to read, and a stray double click while dragging should not select
        // the labels on the buttons.
        userSelect: "none",
      }}
    >
      <Stack
        direction="row"
        spacing={1}
        sx={{ alignItems: "center", px: 1, py: 0.75 }}
      >
        <Tooltip title={`Drag to move the ${label}`} placement="top">
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
            aria-label={`Hide the ${label}`}
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
