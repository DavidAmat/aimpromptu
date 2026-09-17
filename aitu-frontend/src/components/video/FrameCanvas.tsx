/**
 * The picture, zoomed and panned, with an SVG layer drawn in its own pixels.
 *
 * The user is matching a few pixels, so the picture has to be zoomable hard and
 * pannable (Task 2.1.2). Everything drawn on top — the overlay, the upper line,
 * the runs — is given in the coordinates of the picture itself, so a component
 * that draws a key at x = 372 never has to know what the zoom is.
 *
 * One `<svg>` with a `viewBox` does all of it: the browser scales the image and
 * the overlay together, and a coordinate stays a coordinate.
 *
 * **The one number every overlay needs is the live scale**, and the canvas is the
 * only thing that knows it, so it hands it to its children: `children` may be a
 * function of it. It is how many picture pixels one screen pixel is worth right
 * now, so a handle of `9 * scale` is nine screen pixels at every zoom. Passing a
 * guess instead — the picture's width over a nominal canvas width — was wrong
 * twice over: the handles grew with the zoom until they covered the key they were
 * meant to size, and a drag converted the mouse's travel with the wrong factor,
 * so the shape slid away from the pointer.
 */

import { useCallback, useRef, useState } from "react";
import type { MouseEvent as ReactMouseEvent, ReactNode, WheelEvent as ReactWheelEvent } from "react";
import Box from "@mui/material/Box";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import Button from "@mui/material/Button";
import ButtonGroup from "@mui/material/ButtonGroup";
import useElementSize from "../../hooks/useElementSize";
import { surface } from "../../ui";

export interface Viewport {
  /** Top-left of the visible part, in picture pixels. */
  x: number;
  y: number;
  /** How many picture pixels are visible across and down. */
  width: number;
  height: number;
}

export interface FocusRect {
  x: number;
  y: number;
  width: number;
  height: number;
  /** Changing this is what asks the canvas to jump; the numbers alone do not. */
  key: string;
}

export interface FrameCanvasProps {
  imageUrl: string;
  imageWidth: number;
  imageHeight: number;
  /**
   * Drawn in picture coordinates, on top of the picture. Given as a function to
   * receive the live scale — picture pixels per screen pixel — which is what
   * keeps a handle, a stroke or a label the same size on screen at every zoom.
   */
  children?: ReactNode | ((scale: number) => ReactNode);
  /** Height of the canvas on the page, in CSS pixels. */
  height?: number;
  /** A click on the picture, in picture coordinates. Suppressed after a pan. */
  onPictureClick?: (point: { x: number; y: number }) => void;
  /**
   * Every press on the picture, in picture coordinates, before the canvas does
   * anything with it. Return `true` to take the gesture — the canvas then does
   * not pan, and whatever the caller started owns the mouse. It is how a screen
   * puts a gesture of its own on part of the picture, such as dragging a box
   * around the keys, without giving up panning everywhere else.
   */
  onPictureMouseDown?: (
    point: { x: number; y: number },
    event: ReactMouseEvent<SVGSVGElement>,
    /** Picture pixels per screen pixel, so the gesture can convert its own travel. */
    scale: number,
  ) => boolean | void;
  /** Disables panning while another gesture — dragging a handle — owns the mouse. */
  panDisabled?: boolean;
  /** When its `key` changes, the view jumps to show this part of the picture. */
  focus?: FocusRect | null;
}

/** Picture pixels across, at the deepest zoom: past this there is nothing to see. */
const MIN_VISIBLE = 24;
const ZOOM_STEP = 1.15;
const BUTTON_STEP = 1.6;

/**
 * How the browser lays the viewBox out inside the element, under `xMidYMid meet`.
 *
 * `meet` fits the whole viewBox inside the box and centres what is left over, so
 * the picture is letterboxed whenever the two shapes differ — which is almost
 * always, since the canvas has a fixed height and the pictures do not. Assuming
 * the content fills the element is what made a click land on the wrong row and a
 * vertical drag travel the wrong distance.
 */
function layout(view: Viewport, boxWidth: number, boxHeight: number) {
  const fit =
    boxWidth > 0 && boxHeight > 0
      ? Math.min(boxWidth / view.width, boxHeight / view.height)
      : 1 / Math.max(view.width, 1);
  return {
    /** Screen pixels per picture pixel. */
    fit,
    /** Picture pixels per screen pixel — what an overlay sizes itself with. */
    scale: 1 / fit,
    /** Where the picture's own top-left sits inside the element, in screen px. */
    offsetX: (boxWidth - view.width * fit) / 2,
    offsetY: (boxHeight - view.height * fit) / 2,
  };
}

export function FrameCanvas({
  imageUrl,
  imageWidth,
  imageHeight,
  children,
  height = 520,
  onPictureClick,
  onPictureMouseDown,
  panDisabled = false,
  focus = null,
}: FrameCanvasProps) {
  const svgRef = useRef<SVGSVGElement | null>(null);
  const [boxRef, box] = useElementSize<HTMLDivElement>();
  const whole = { x: 0, y: 0, width: imageWidth, height: imageHeight };
  const [view, setView] = useState<Viewport>(whole);
  const panFrom = useRef<{ x: number; y: number; view: Viewport } | null>(null);
  const moved = useRef(false);

  // Two things reset the view, and both are handled during render rather than in
  // an effect: a different picture, and a caller asking to look somewhere. What
  // was last seen is kept in state, not in a ref — React reads state during
  // render and refs it may not.
  const pictureKey = `${imageUrl}:${imageWidth}x${imageHeight}`;
  const [seen, setSeen] = useState({ picture: pictureKey, focus: focus?.key ?? null });
  if (seen.picture !== pictureKey) {
    setSeen({ picture: pictureKey, focus: focus?.key ?? null });
    setView(whole);
  } else if (focus && seen.focus !== focus.key) {
    setSeen({ picture: pictureKey, focus: focus.key });
    // Keep the picture's own aspect ratio: the viewBox is drawn with
    // `xMidYMid meet`, so a box of the wrong shape would letterbox and the
    // numbers on screen would stop matching the numbers in the calibration.
    const ratio = imageHeight / imageWidth;
    const width = Math.max(MIN_VISIBLE, Math.max(focus.width, focus.height / ratio));
    setView({
      x: focus.x + focus.width / 2 - width / 2,
      y: focus.y + focus.height / 2 - (width * ratio) / 2,
      width,
      height: width * ratio,
    });
  }

  const { scale } = layout(view, box.width, box.height);

  /** Where a mouse event is, in picture pixels. */
  const pictureAt = useCallback(
    (clientX: number, clientY: number) => {
      const svg = svgRef.current;
      if (!svg) return { x: 0, y: 0 };
      const rect = svg.getBoundingClientRect();
      const here = layout(view, rect.width, rect.height);
      return {
        x: view.x + (clientX - rect.left - here.offsetX) / here.fit,
        y: view.y + (clientY - rect.top - here.offsetY) / here.fit,
      };
    },
    [view],
  );

  const zoomAt = useCallback(
    (factor: number, anchor: { x: number; y: number }) => {
      setView((current) => {
        const width = Math.min(imageWidth, Math.max(MIN_VISIBLE, current.width / factor));
        const height = (width / current.width) * current.height;
        // Keep the point under the cursor exactly where it is.
        const kx = (anchor.x - current.x) / current.width;
        const ky = (anchor.y - current.y) / current.height;
        return { width, height, x: anchor.x - kx * width, y: anchor.y - ky * height };
      });
    },
    [imageWidth],
  );

  const onWheel = (event: ReactWheelEvent<SVGSVGElement>) => {
    zoomAt(event.deltaY < 0 ? ZOOM_STEP : 1 / ZOOM_STEP, pictureAt(event.clientX, event.clientY));
  };

  const onMouseDown = (event: ReactMouseEvent<SVGSVGElement>) => {
    if (event.button !== 0) return;
    if (onPictureMouseDown?.(pictureAt(event.clientX, event.clientY), event, scale)) return;
    if (panDisabled) return;
    moved.current = false;
    panFrom.current = { x: event.clientX, y: event.clientY, view };
  };

  const onMouseMove = (event: ReactMouseEvent<SVGSVGElement>) => {
    const from = panFrom.current;
    if (!from) return;
    // The same conversion the drag of a handle uses: screen travel times picture
    // pixels per screen pixel. The picture then keeps up with the pointer exactly,
    // at every zoom and on both axes.
    const dx = (event.clientX - from.x) * scale;
    const dy = (event.clientY - from.y) * scale;
    if (Math.abs(dx) > 1 || Math.abs(dy) > 1) moved.current = true;
    setView({ ...from.view, x: from.view.x - dx, y: from.view.y - dy });
  };

  const endPan = (event: ReactMouseEvent<SVGSVGElement>) => {
    const wasPanning = panFrom.current !== null;
    panFrom.current = null;
    if (wasPanning && !moved.current && onPictureClick) {
      onPictureClick(pictureAt(event.clientX, event.clientY));
    }
  };

  const centre = { x: view.x + view.width / 2, y: view.y + view.height / 2 };
  const zoom = imageWidth / view.width;

  return (
    <Box sx={{ position: "relative" }}>
      <Box
        ref={boxRef}
        sx={{
          border: 1,
          borderColor: "divider",
          borderRadius: 1,
          overflow: "hidden",
          backgroundColor: surface.panel,
          height,
        }}
      >
        <svg
          ref={svgRef}
          viewBox={`${view.x} ${view.y} ${view.width} ${view.height}`}
          preserveAspectRatio="xMidYMid meet"
          width="100%"
          height="100%"
          style={{
            display: "block",
            cursor: panDisabled ? "default" : "grab",
            touchAction: "none",
          }}
          onWheel={onWheel}
          onMouseDown={onMouseDown}
          onMouseMove={onMouseMove}
          onMouseUp={endPan}
          onMouseLeave={() => {
            panFrom.current = null;
          }}
        >
          <image
            href={imageUrl}
            x={0}
            y={0}
            width={imageWidth}
            height={imageHeight}
            preserveAspectRatio="none"
          />
          {/* The overlay is drawn only once the box has been measured: before
              that the scale is a guess, and a handle drawn at the wrong size for
              one frame is a handle that jumps. */}
          {box.width > 0
            ? typeof children === "function"
              ? children(scale)
              : children
            : null}
        </svg>
      </Box>
      <Stack
        direction="row"
        spacing={1}
        sx={{ position: "absolute", right: 8, bottom: 8, alignItems: "center" }}
      >
        <Typography
          variant="caption"
          sx={{ backgroundColor: surface.panel, px: 0.75, borderRadius: 0.5 }}
        >
          {zoom.toFixed(1)}x
        </Typography>
        <ButtonGroup size="small" variant="outlined" sx={{ backgroundColor: surface.panel }}>
          <Button onClick={() => zoomAt(BUTTON_STEP, centre)}>+</Button>
          <Button onClick={() => zoomAt(1 / BUTTON_STEP, centre)}>−</Button>
          <Button onClick={() => setView(whole)}>Fit</Button>
        </ButtonGroup>
      </Stack>
    </Box>
  );
}

export default FrameCanvas;
