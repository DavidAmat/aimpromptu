/**
 * Fit the piano overlay onto a picture: step 1 of the work on one example.
 *
 * One rectangle, and the overlay found from it (V-37). The user drags the
 * rectangle over the piano area — resizable and rotatable, so it can take
 * whatever shape the picture needs — and when it settles the app finds every
 * key inside it; there is no button for that, because the answer is what the
 * screen is about. Every button of the old flow — place the white key, place
 * the black key, render one octave, render the piano, move the piano — is gone.
 *
 * What the user still decides, and the app only defaults: where the rectangle
 * is, the upper line (V-11, dragged), and the octave of the leftmost key (V-10,
 * one dropdown). When the found overlay misses, any white key border can be
 * taken and dragged along the top edge; a dragged border is marked as the
 * user's and never mistaken for the finder's own answer.
 *
 * A picture that already has an overlay opens showing it, at the rectangle it
 * was found with, and nothing is found again until the rectangle moves — so a
 * border corrected by hand is not thrown away by opening the page.
 */

import { useEffect, useMemo, useState } from "react";
import type { MouseEvent as ReactMouseEvent } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import MenuItem from "@mui/material/MenuItem";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import type { Calibration, FindRequest, PianoRect as Rect } from "../../api/frameExamples";
import { buildKeys, medianWhiteWidth } from "../../video/overlayGeometry";
import { palette, surface } from "../../ui";
import FrameCanvas from "./FrameCanvas";
import { rectColours } from "./overlayColours";
import PianoOverlay from "./PianoOverlay";
import PianoRect from "./PianoRect";

export interface CalibrationEditorProps {
  imageUrl: string;
  imageWidth: number;
  imageHeight: number;
  calibration: Calibration | null;
  /** Find the overlay inside a rectangle. The page knows which picture; this does not. */
  onFind: (body: FindRequest) => Promise<Calibration>;
  onSave: (calibration: Calibration) => void;
  saving?: boolean;
}

/** How tall the grab strip of the upper line is, in screen pixels. */
const GRAB_SCREEN_PX = 11;
/** How long the rectangle has to stay still before the finder reads it. */
const SETTLE_MS = 350;

/** Where the rectangle starts on a picture nobody has fitted: the bottom third. */
function startingRect(imageWidth: number, imageHeight: number): Rect {
  return { x: 0, y: imageHeight * 0.6, width: imageWidth, height: imageHeight * 0.4, angle: 0 };
}

export function CalibrationEditor({
  imageUrl,
  imageWidth,
  imageHeight,
  calibration,
  onFind,
  onSave,
  saving = false,
}: CalibrationEditorProps) {
  const [rect, setRect] = useState<Rect>(
    () => calibration?.pianoRect ?? startingRect(imageWidth, imageHeight),
  );
  const [draft, setDraft] = useState<Calibration | null>(calibration);
  /** The rectangle moved since the overlay was last found or opened. */
  const [moved, setMoved] = useState(false);
  const [finding, setFinding] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const [hovered, setHovered] = useState<number | null>(null);
  /** The user dragged the upper line since the last find, so the finder must not move it. */
  const [upperLineTouched, setUpperLineTouched] = useState(false);

  // A different picture is a different piano. What was last seen is state rather
  // than a ref, because React reads state during render.
  const pictureKey = `${imageUrl}:${imageWidth}`;
  const [seen, setSeen] = useState(pictureKey);
  if (seen !== pictureKey) {
    setSeen(pictureKey);
    setRect(calibration?.pianoRect ?? startingRect(imageWidth, imageHeight));
    setDraft(calibration);
    setMoved(false);
    setProblem(null);
    setUpperLineTouched(false);
  }

  const keys = useMemo(() => (draft ? buildKeys(draft) : []), [draft]);
  const edit = (change: Partial<Calibration>) =>
    setDraft((current) => (current ? { ...current, ...change } : current));

  /**
   * The finder runs when the rectangle has stopped moving for a moment, the way
   * the detector re-reads when the offset line moves. Dragging a rectangle is
   * dozens of values and every one of them would otherwise be a request.
   */
  useEffect(() => {
    if (!moved || dragging) return;
    const controller = new AbortController();
    const handle = window.setTimeout(() => {
      setFinding(true);
      onFind({
        pianoRect: rect,
        upperLine: upperLineTouched && draft ? draft.upperLine : null,
        firstWhiteOctave: draft ? draft.firstWhiteOctave : null,
      })
        .then((found) => {
          if (controller.signal.aborted) return;
          setDraft(found);
          setProblem(null);
          setMoved(false);
        })
        .catch((caught: unknown) => {
          if (controller.signal.aborted) return;
          setProblem(caught instanceof Error ? caught.message : String(caught));
        })
        .finally(() => {
          if (!controller.signal.aborted) setFinding(false);
        });
    }, SETTLE_MS);
    return () => {
      controller.abort();
      window.clearTimeout(handle);
    };
    // The draft's upper line and octave are read when the finder runs, and
    // changing either must not run it again: they are the user's, not its.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [moved, dragging, rect, onFind]);

  const changeRect = (next: Rect) => {
    setRect(next);
    setMoved(true);
  };

  /** The upper line is dragged up and down the picture, never typed (V-11). */
  const startUpperLine = (scale: number) => (event: ReactMouseEvent) => {
    if (!draft) return;
    event.stopPropagation();
    const origin = { y: event.clientY, upperLine: draft.upperLine };
    setDragging(true);
    setUpperLineTouched(true);
    const move = (native: MouseEvent) => {
      const next = origin.upperLine + (native.clientY - origin.y) * scale;
      edit({ upperLine: Math.min(imageHeight - 1, Math.max(1, next)) });
    };
    const stop = () => {
      setDragging(false);
      window.removeEventListener("mousemove", move);
      window.removeEventListener("mouseup", stop);
    };
    window.addEventListener("mousemove", move);
    window.addEventListener("mouseup", stop);
  };

  /**
   * One white key border, dragged by hand along the top edge.
   *
   * The fallback for a found overlay that misses (the user's decision): the
   * border moves between its two neighbours, the keys on both sides follow, the
   * black key between them keeps its own found borders, and the index goes
   * into `found.corrected` so the hand's answer is never taken for the finder's.
   */
  const dragBorder = (index: number, u: number) =>
    setDraft((current) => {
      if (!current) return current;
      const borders = [...current.whiteBorders];
      const low = index > 0 ? borders[index - 1] + 2 : -Infinity;
      const high = index < borders.length - 1 ? borders[index + 1] - 2 : Infinity;
      borders[index] = Math.min(high, Math.max(low, u));
      const found = current.found ?? {
        route: "hand",
        confidence: 0,
        extrapolated: [],
        confirmed: [],
        corrected: [],
      };
      const corrected = found.corrected.includes(index)
        ? found.corrected
        : [...found.corrected, index].sort((a, b) => a - b);
      const next = { ...current, whiteBorders: borders, found: { ...found, corrected } };
      return { ...next, whiteWidth: medianWhiteWidth(next) };
    });

  const found = draft?.found ?? null;
  const summary = draft
    ? [
        `${keys.length} keys · ${keys[0]?.nameEn ?? "?"} to ${keys[keys.length - 1]?.nameEn ?? "?"}`,
        `white key ${draft.whiteWidth.toFixed(1)} px at the median`,
        found && found.route !== "hand"
          ? `found by route ${found.route} · confidence ${found.confidence.toFixed(2)}`
          : null,
        found && found.extrapolated.length
          ? `${found.extrapolated.length} black key${found.extrapolated.length === 1 ? "" : "s"} placed through a hand, ${found.confirmed.length} confirmed by the pixels`
          : null,
        found && found.corrected.length
          ? `${found.corrected.length} border${found.corrected.length === 1 ? "" : "s"} corrected by hand`
          : null,
      ]
        .filter(Boolean)
        .join(" · ")
    : null;

  return (
    <Stack spacing={1.5}>
      <Stack direction="row" spacing={1} sx={{ alignItems: "center", flexWrap: "wrap", rowGap: 1 }}>
        {draft ? (
          <TextField
            select
            size="small"
            label="Octave of the leftmost key"
            value={draft.firstWhiteOctave}
            onChange={(event) => edit({ firstWhiteOctave: Number(event.target.value) })}
            sx={{ minWidth: 200 }}
          >
            {[0, 1, 2, 3, 4].map((octave) => (
              <MenuItem key={octave} value={octave}>
                {octave}
              </MenuItem>
            ))}
          </TextField>
        ) : null}
        {finding ? <CircularProgress size={18} /> : null}
        {summary ? (
          <Typography variant="caption" sx={{ color: surface.mutedText }}>
            {summary}
          </Typography>
        ) : null}
        <Box sx={{ flexGrow: 1 }} />
        <Button
          variant="contained"
          size="small"
          disabled={!draft || saving || finding || moved}
          onClick={() => draft && onSave(draft)}
        >
          {saving ? "Saving…" : "Save"}
        </Button>
      </Stack>

      <Typography variant="caption" color="text.secondary">
        Drag the rectangle over the piano area; every key inside it is found when it settles. Then
        drag the red line onto the top of the keys, choose the octave, and save. A border the finder
        got wrong can be dragged along the top of the keys; the names of the keys are on the next
        step, under the pointer.
      </Typography>

      {problem ? (
        <Alert severity="warning" variant="outlined" onClose={() => setProblem(null)}>
          {problem}
        </Alert>
      ) : null}

      <FrameCanvas
        imageUrl={imageUrl}
        imageWidth={imageWidth}
        imageHeight={imageHeight}
        panDisabled={dragging}
        height={560}
      >
        {(scale) => (
          <>
            {/* The rectangle first, under the overlay: it is dragged by its body,
                and the keys drawn over it let the pointer through. */}
            <PianoRect
              rect={rect}
              onChange={changeRect}
              onGesture={setDragging}
              colour={rectColours.white}
              scale={scale}
              bounds={{ width: imageWidth, height: imageHeight }}
            />
            {draft ? (
              <>
                <PianoOverlay
                  calibration={draft}
                  keys={keys}
                  scale={scale}
                  hoveredMidi={hovered}
                  onHover={setHovered}
                  dashedMidis={found?.extrapolated}
                  dottedMidis={found?.confirmed}
                  correctedBorders={found?.corrected}
                  onBorderDrag={dragBorder}
                  onGesture={setDragging}
                />
                {/* The upper line: a rectangle tip crossing it is an onset (V-11). */}
                <line
                  x1={0}
                  x2={imageWidth}
                  y1={draft.upperLine}
                  y2={draft.upperLine}
                  stroke={palette.dark.Red}
                  strokeWidth={1.5 * scale}
                  style={{ pointerEvents: "none" }}
                />
                <rect
                  x={0}
                  y={draft.upperLine - (GRAB_SCREEN_PX * scale) / 2}
                  width={imageWidth}
                  height={GRAB_SCREEN_PX * scale}
                  fill="transparent"
                  style={{ cursor: "ns-resize" }}
                  onMouseDown={startUpperLine(scale)}
                />
              </>
            ) : null}
          </>
        )}
      </FrameCanvas>

      {!draft && !moved ? (
        <Alert severity="info" variant="outlined">
          Zoom with the wheel, drag the picture to move it. Move the rectangle onto the piano to
          find the keys.
        </Alert>
      ) : null}
    </Stack>
  );
}

export default CalibrationEditor;
