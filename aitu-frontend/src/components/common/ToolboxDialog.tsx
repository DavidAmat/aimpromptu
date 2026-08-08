/**
 * A small floating panel that can be moved out of the way.
 *
 * The sheet is the whole screen on the Rhythm tab, so anything that opens over it hides the very
 * notes it is about. A modal dialog would be worse: it blocks the page behind it, and the reason
 * this panel is open is that the reader wants to look at that page while they use it.
 *
 * So it floats, it never blocks, and it is dragged by its title bar. The position is remembered
 * while it stays open, and it starts again at its default corner each time it opens, which is
 * where a reader looks for it.
 */
import { useCallback, useState, type ReactNode } from "react";
import Box from "@mui/material/Box";
import IconButton from "@mui/material/IconButton";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import CloseIcon from "@mui/icons-material/Close";
import DragIndicatorIcon from "@mui/icons-material/DragIndicator";

export interface ToolboxDialogProps {
  open: boolean;
  title: string;
  /** One line under the title saying what the panel is about, for example the range selected. */
  subtitle?: string;
  /** Where it appears when it opens, in pixels from the top left of the window. */
  initialPosition?: { x: number; y: number };
  onClose: () => void;
  children: ReactNode;
}

const WIDTH = 360;
/** Kept on screen: a panel dragged off the edge cannot be dragged back. */
const MARGIN = 8;

export function ToolboxDialog({
  open,
  title,
  subtitle,
  initialPosition,
  onClose,
  children,
}: ToolboxDialogProps) {
  const [position, setPosition] = useState<{ x: number; y: number } | null>(null);
  const [wasOpen, setWasOpen] = useState(open);

  // Back to the default corner each time it opens. A panel that reappears where it was three
  // selections ago reads as lost rather than as remembered. Compared while rendering rather than in
  // an effect, so it never appears for one frame in the place it was dragged to last time.
  if (wasOpen !== open) {
    setWasOpen(open);
    if (!open) setPosition(null);
  }

  const clamp = useCallback((x: number, y: number) => {
    const maxX = Math.max(MARGIN, window.innerWidth - WIDTH - MARGIN);
    const maxY = Math.max(MARGIN, window.innerHeight - 80);
    return { x: Math.min(Math.max(MARGIN, x), maxX), y: Math.min(Math.max(MARGIN, y), maxY) };
  }, []);

  const at = position ?? initialPosition ?? { x: 24, y: 120 };

  /**
   * Start a drag, listening on the window rather than on the title bar.
   *
   * The pointer leaves the bar as soon as it moves faster than the panel follows, and a listener on
   * the bar itself would stop hearing about it there. Both pointer and mouse events are taken,
   * because not every way of driving a page sends the first kind.
   */
  const beginDrag = useCallback(
    (clientX: number, clientY: number) => {
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
    [at.x, at.y, clamp],
  );

  if (!open) return null;

  return (
    <Paper
      elevation={12}
      sx={{
        position: "fixed",
        left: `${at.x}px`,
        top: `${at.y}px`,
        width: WIDTH,
        zIndex: 1300,
        borderRadius: 2,
        overflow: "hidden",
        border: "1px solid",
        borderColor: "divider",
      }}
    >
      <Stack
        direction="row"
        spacing={1}
        onPointerDown={(event) => beginDrag(event.clientX, event.clientY)}
        onMouseDown={(event) => beginDrag(event.clientX, event.clientY)}
        sx={{
          alignItems: "center",
          px: 1,
          py: 0.75,
          cursor: "grab",
          bgcolor: "primary.main",
          color: "primary.contrastText",
          userSelect: "none",
          "&:active": { cursor: "grabbing" },
        }}
      >
        <DragIndicatorIcon fontSize="small" sx={{ opacity: 0.8 }} />
        <Box sx={{ flexGrow: 1, minWidth: 0 }}>
          <Typography variant="subtitle2" noWrap sx={{ fontWeight: 700 }}>
            {title}
          </Typography>
          {subtitle ? (
            <Typography variant="caption" noWrap sx={{ display: "block", opacity: 0.85 }}>
              {subtitle}
            </Typography>
          ) : null}
        </Box>
        <IconButton
          size="small"
          onClick={onClose}
          aria-label="Close the toolbox"
          sx={{ color: "inherit" }}
        >
          <CloseIcon fontSize="small" />
        </IconButton>
      </Stack>
      <Box sx={{ p: 2 }}>{children}</Box>
    </Paper>
  );
}

export default ToolboxDialog;
