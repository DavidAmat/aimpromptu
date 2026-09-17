/**
 * What the detector saw, and whether it was right.
 *
 * Task 2.3.2, and the other half of Task 2.2.2. The detector's answer is drawn on
 * the pixels it came from and the user judges it in place:
 *
 * - a **rectangle it found** is a box on the picture. Press it to say it is not a
 *   note — a false positive — and the key it stood for stops being called;
 * - a **key it missed** is a key with nothing on it. Press the key to say what it
 *   should have been: onset, then sustain, then cannot say, then nothing again.
 *
 * What comes out is the hand reading for that window, so the fastest way to read
 * an example is to let the detector read it first and correct what it got wrong.
 * That is only sound because the reading is judged against the picture, never
 * against the detector: every box is drawn on the rectangle it claims to be, so
 * accepting one is looking at it, not trusting it.
 *
 * The offset line is dragged here too, and the detector is re-run as it moves —
 * the window is the thing being judged, so it has to be the thing you can change.
 */

import { useMemo, useState } from "react";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import type {
  Annotation,
  Calibration,
  DetectedRun,
  Detection,
  PianoKey,
} from "../../api/frameExamples";
import { buildKeys } from "../../video/overlayGeometry";
import { palette, surface } from "../../ui";
import FrameCanvas from "./FrameCanvas";
import OffsetLine from "./OffsetLine";
import PianoOverlay from "./PianoOverlay";
import { markColours, runColours, type MarkState } from "./overlayColours";

export interface DetectionViewProps {
  imageUrl: string;
  imageWidth: number;
  imageHeight: number;
  calibration: Calibration;
  /** What the detector answered for the window below. Null while it is reading. */
  detection: Detection | null;
  offsetPx: number;
  onOffsetChange: (offsetPx: number) => void;
  /** Save what the user made of it, as the hand reading for this window. */
  onSave: (annotation: Annotation) => void;
  saving?: boolean;
  /** A reading already saved at this window, if there is one. */
  saved?: Annotation;
}

const CYCLE: MarkState[] = ["released", "onset", "sustain", "skip"];

const runId = (run: DetectedRun) => `${run.midi}:${run.yTop}:${run.yBottom}`;

export function DetectionView({
  imageUrl,
  imageWidth,
  imageHeight,
  calibration,
  detection,
  offsetPx,
  onOffsetChange,
  onSave,
  saving = false,
  saved,
}: DetectionViewProps) {
  const keys = useMemo(() => buildKeys(calibration), [calibration]);
  const [dragging, setDragging] = useState(false);
  const [hovered, setHovered] = useState<number | null>(null);
  /** Keys the user corrected by hand, over what the detector said. */
  const [edited, setEdited] = useState<Record<number, MarkState>>({});
  /** Rectangles the user threw out. */
  const [rejected, setRejected] = useState<string[]>([]);

  // A new answer from the detector is a new thing to judge, so the corrections
  // made against the old one are let go. Derived during render, not in an effect.
  const answerKey = detection ? `${detection.slug}:${detection.offsetPx}:${detection.runs.length}` : "";
  const [seen, setSeen] = useState(answerKey);
  if (seen !== answerKey) {
    setSeen(answerKey);
    setEdited({});
    setRejected([]);
  }

  /** What the detector says, corrected by what the user said about it. */
  const marks: Record<number, MarkState> = {};
  if (detection) {
    const thrownOut = new Set(rejected);
    for (const run of detection.runs) {
      if (run.verdict === "released" || thrownOut.has(runId(run))) continue;
      if (run.verdict === "onset" || marks[run.midi] !== "onset") marks[run.midi] = run.verdict;
    }
  }
  for (const [midi, state] of Object.entries(edited)) {
    if (state === "released") delete marks[Number(midi)];
    else marks[Number(midi)] = state;
  }

  const cycleKey = (key: PianoKey) =>
    setEdited((current) => {
      const now = current[key.midi] ?? marks[key.midi] ?? "released";
      return { ...current, [key.midi]: CYCLE[(CYCLE.indexOf(now) + 1) % CYCLE.length] };
    });

  const throwOut = (run: DetectedRun) =>
    setRejected((current) =>
      current.includes(runId(run))
        ? current.filter((one) => one !== runId(run))
        : [...current, runId(run)],
    );

  const pick = (state: MarkState) =>
    Object.entries(marks)
      .filter(([, value]) => value === state)
      .map(([midi]) => Number(midi))
      .sort((a, b) => a - b);

  const corrections = Object.keys(edited).length + rejected.length;
  const thrownOut = new Set(rejected);

  const drawRun = (run: DetectedRun, scale: number) => {
    const out = thrownOut.has(runId(run));
    const colour = out ? palette.dark.Gray : runColours[run.verdict];
    return (
      <g key={runId(run)}>
        <rect
          x={run.x0}
          y={run.yTop}
          width={Math.max(0.5, run.x1 - run.x0)}
          height={Math.max(0.5, run.yBottom - run.yTop)}
          fill={colour}
          fillOpacity={out ? 0.05 : 0.16}
          stroke={colour}
          strokeWidth={1.3 * scale}
          strokeDasharray={out ? `${4 * scale} ${3 * scale}` : undefined}
          style={{ cursor: "pointer" }}
          onMouseDown={(event) => {
            event.stopPropagation();
            throwOut(run);
          }}
        >
          <title>
            {`${keys.find((key) => key.midi === run.midi)?.nameEn ?? run.midi} · ${run.verdict}` +
              ` · ${run.yBottom - run.yTop + 1} px tall · ${run.widthKeys.toFixed(2)} keys wide` +
              (out ? " · thrown out" : " — press to throw it out")}
          </title>
        </rect>
        {/* The rectangle tip: the side that reaches the piano first. */}
        <line
          x1={run.x0}
          x2={run.x1}
          y1={run.yBottom}
          y2={run.yBottom}
          stroke={colour}
          strokeWidth={2.2 * scale}
          style={{ pointerEvents: "none" }}
        />
      </g>
    );
  };

  return (
    <Stack spacing={1.5}>
      <Stack direction="row" spacing={1} sx={{ alignItems: "center", flexWrap: "wrap", rowGap: 1 }}>
        <Chip
          size="small"
          label={`${pick("onset").length} onset`}
          sx={{ backgroundColor: markColours.onset, color: surface.panel }}
        />
        <Chip
          size="small"
          label={`${pick("sustain").length} sustain`}
          sx={{ backgroundColor: markColours.sustain }}
        />
        {corrections ? (
          <Chip
            size="small"
            label={`${corrections} correction${corrections === 1 ? "" : "s"}`}
            sx={{ backgroundColor: palette.dark.Orange, color: surface.panel }}
          />
        ) : null}
        {saved ? (
          <Typography variant="caption" color="text.secondary">
            already read by hand at this window
          </Typography>
        ) : null}
        <Box sx={{ flexGrow: 1 }} />
        <Typography variant="caption" color="text.secondary">
          {detection ? `${detection.runs.length} rectangles · ${detection.elapsedMs.toFixed(0)} ms` : "reading…"}
        </Typography>
        <Button
          variant="contained"
          size="small"
          disabled={saving || !detection}
          onClick={() =>
            onSave({
              offsetPx,
              onsets: pick("onset"),
              sustains: pick("sustain"),
              skip: pick("skip"),
              note: corrections ? `${corrections} corrected by hand over the detector` : "accepted as the detector read it",
            })
          }
        >
          {saving ? "Saving…" : "Save as the reading"}
        </Button>
      </Stack>

      <Typography variant="caption" color="text.secondary">
        Drag the yellow line to move the window. Press a rectangle to throw it out, press a key to
        say what it should have been.
      </Typography>

      <FrameCanvas
        imageUrl={imageUrl}
        imageWidth={imageWidth}
        imageHeight={imageHeight}
        panDisabled={dragging}
        height={560}
      >
        {(scale) => (
          <>
            <OffsetLine
              upperLine={calibration.upperLine}
              offsetPx={offsetPx}
              imageWidth={imageWidth}
              whiteWidth={calibration.whiteWidth}
              scale={scale}
              onChange={onOffsetChange}
              onGesture={setDragging}
            />
            {detection?.runs.map((run) => drawRun(run, scale))}
            <PianoOverlay
              calibration={calibration}
              keys={keys}
              scale={scale}
              marks={marks}
              onKeyClick={cycleKey}
              hoveredMidi={hovered}
              onHover={setHovered}
            />
          </>
        )}
      </FrameCanvas>
    </Stack>
  );
}

export default DetectionView;
