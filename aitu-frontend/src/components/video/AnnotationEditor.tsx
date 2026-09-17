/**
 * Mark, by hand, which keys are onset and which are sustained in one window.
 *
 * Task 2.2.2. One picture, the piano that was accepted on the step before, and
 * one line to drag. Press a key to cycle it: nothing → onset → sustain → cannot
 * say → nothing. Released is the default and is never written down (V-19), and
 * "cannot say" is the third answer Phase 1 found it needed — a rectangle
 * entirely past the upper line with the strike light over what is left cannot be
 * answered for, and guessing it would poison the score in both directions.
 *
 * The offset line is dragged, not typed. The entry saved is the triple (example,
 * offset line position, the keys marked), so the same example marked with the
 * line in three places is three entries — which is the point: it tests whether
 * the detector follows the window and not a fixed guess.
 *
 * The frame window rule (V-18, Task 2.2.3) is on the page, folded away. It has to
 * be here, because the person annotating applies the rule the detector applies
 * and a disagreement must be about what was seen and never about what the words
 * mean — but it is four lines of algebra that are read once and known after that,
 * so it does not sit open on top of the picture.
 */

import { useMemo, useState } from "react";
import Accordion from "@mui/material/Accordion";
import AccordionDetails from "@mui/material/AccordionDetails";
import AccordionSummary from "@mui/material/AccordionSummary";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import type { Annotation, Calibration, PianoKey } from "../../api/frameExamples";
import { buildKeys } from "../../video/overlayGeometry";
import { surface } from "../../ui";
import FrameCanvas from "./FrameCanvas";
import OffsetLine from "./OffsetLine";
import PianoOverlay from "./PianoOverlay";
import { markColours, type MarkState } from "./overlayColours";

export interface AnnotationEditorProps {
  imageUrl: string;
  imageWidth: number;
  imageHeight: number;
  calibration: Calibration;
  annotations: Annotation[];
  onSave: (annotation: Annotation) => void;
  onDelete: (offsetPx: number) => void;
  saving?: boolean;
}

const CYCLE: MarkState[] = ["released", "onset", "sustain", "skip"];

const RULE: [string, string][] = [
  ["onset in this window", "U − d ≤ yBottom < U"],
  ["sustain in this window", "yBottom ≥ U and yTop < U − d"],
  ["released in this window", "yTop ≥ U − d"],
  ["anything else", "released, and nothing is written"],
];

export function AnnotationEditor({
  imageUrl,
  imageWidth,
  imageHeight,
  calibration,
  annotations,
  onSave,
  onDelete,
  saving = false,
}: AnnotationEditorProps) {
  const keys = useMemo(() => buildKeys(calibration), [calibration]);
  // Two white keys to begin with. Opening on the narrowest window already saved
  // would be honest and useless: on one example that window is six pixels tall.
  const [offsetPx, setOffsetPx] = useState(() => Math.round(calibration.whiteWidth * 2));
  const [marks, setMarks] = useState<Record<number, MarkState>>({});
  const [dragging, setDragging] = useState(false);
  const [hovered, setHovered] = useState<number | null>(null);

  // A different picture is a different piano and a different reading.
  const [seen, setSeen] = useState(imageUrl);
  if (seen !== imageUrl) {
    setSeen(imageUrl);
    setMarks({});
    setOffsetPx(Math.round(calibration.whiteWidth * 2));
  }

  const cycle = (key: PianoKey) =>
    setMarks((current) => {
      const next = CYCLE[(CYCLE.indexOf(current[key.midi] ?? "released") + 1) % CYCLE.length];
      const copy = { ...current };
      if (next === "released") delete copy[key.midi];
      else copy[key.midi] = next;
      return copy;
    });

  const pick = (state: MarkState) =>
    Object.entries(marks)
      .filter(([, value]) => value === state)
      .map(([midi]) => Number(midi))
      .sort((a, b) => a - b);

  const load = (annotation: Annotation) => {
    const next: Record<number, MarkState> = {};
    annotation.onsets.forEach((midi) => (next[midi] = "onset"));
    annotation.sustains.forEach((midi) => (next[midi] = "sustain"));
    annotation.skip.forEach((midi) => (next[midi] = "skip"));
    setMarks(next);
    setOffsetPx(annotation.offsetPx);
  };

  const counts = { onset: pick("onset").length, sustain: pick("sustain").length, skip: pick("skip").length };

  return (
    <Stack spacing={1.5}>
      <Stack direction="row" spacing={1} sx={{ alignItems: "center", flexWrap: "wrap", rowGap: 1 }}>
        <Chip
          size="small"
          label={`${counts.onset} onset`}
          sx={{ backgroundColor: markColours.onset, color: surface.panel }}
        />
        <Chip size="small" label={`${counts.sustain} sustain`} sx={{ backgroundColor: markColours.sustain }} />
        <Chip
          size="small"
          label={`${counts.skip} cannot say`}
          sx={{ backgroundColor: markColours.skip, color: surface.panel }}
        />
        <Box sx={{ flexGrow: 1 }} />
        {annotations.map((annotation) => (
          <Chip
            key={annotation.offsetPx}
            size="small"
            variant="outlined"
            label={`${annotation.offsetPx.toFixed(0)} px`}
            onClick={() => load(annotation)}
            onDelete={() => onDelete(annotation.offsetPx)}
          />
        ))}
        <Button size="small" onClick={() => setMarks({})}>
          Clear
        </Button>
        <Button
          variant="contained"
          size="small"
          disabled={saving}
          onClick={() =>
            onSave({
              offsetPx,
              onsets: pick("onset"),
              sustains: pick("sustain"),
              skip: pick("skip"),
              note: "",
            })
          }
        >
          {saving ? "Saving…" : "Save this reading"}
        </Button>
      </Stack>

      <Typography variant="caption" color="text.secondary">
        Drag the yellow line to set the window. Press a key to cycle it: nothing → onset → sustain →
        cannot say.
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
              onChange={setOffsetPx}
              onGesture={setDragging}
            />
            <PianoOverlay
              calibration={calibration}
              keys={keys}
              scale={scale}
              marks={marks}
              onKeyClick={cycle}
              hoveredMidi={hovered}
              onHover={setHovered}
            />
          </>
        )}
      </FrameCanvas>

      <Accordion variant="outlined" disableGutters>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography variant="body2" color="text.secondary">
            The rule this reading and the detector both apply
          </Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Typography variant="body2" sx={{ mb: 1 }}>
            Given an upper line <b>U</b>, an offset line <b>d</b> pixels above it, and a rectangle
            whose last tip is at <b>yTop</b> and whose tip is at <b>yBottom</b> — with y growing
            downward:
          </Typography>
          {RULE.map(([what, rule]) => (
            <Stack key={what} direction="row" spacing={1}>
              <Typography variant="body2" sx={{ minWidth: 190, color: surface.mutedText }}>
                {what}
              </Typography>
              <Typography variant="body2" sx={{ fontFamily: "monospace" }}>
                {rule}
              </Typography>
            </Stack>
          ))}
          <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 1 }}>
            Mark a key <b>cannot say</b> when the picture itself cannot answer — those keys come out
            of the score on both sides rather than being guessed.
          </Typography>
        </AccordionDetails>
      </Accordion>
    </Stack>
  );
}

export default AnnotationEditor;
