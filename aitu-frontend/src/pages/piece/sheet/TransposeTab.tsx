/**
 * The **Transpose** tab of the sheet toolbox (plan section 11.4): **Notes** and **Figures**.
 *
 * Notes: two keyboards, **From** and **To**; the interval between the two keys moves every note.
 * Figures: two rows of figure icons, **From** (the last **To**, or negra the first time) and
 * **To**; the step between them renames every figure. Neither applies anything here: **Preview**
 * opens the dialog that shows the result and asks for **Transpose**.
 */

import { useState } from "react";
import Box from "@mui/material/Box";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import type { FigureName } from "../../../api";
import { spanishNoteShort } from "../../../music/noteNames";
import { figureSteps, intervalWords, shiftFigure } from "../../../music/transpose";
import { FigurePicker, MiniPiano, PillButton, Segmented } from "../../../ui";

type Mode = "notes" | "figures";

const MODES = [
  { value: "notes" as const, label: "Notes" },
  { value: "figures" as const, label: "Figures" },
];

/** The figures a figures transposition goes from and to: the plain rungs. */
const FIGURES: readonly FigureName[] = [
  "redonda",
  "blanca",
  "negra",
  "corchea",
  "semicorchea",
  "fusa",
];

/** Do 4, middle C: where both keyboards start. */
const MIDDLE_C = 60;

export function TransposeTab({
  figuresFrom,
  anchorFigure,
  busy,
  onPreviewNotes,
  onPreviewFigures,
}: {
  /** Where the next figures transposition starts: the last **To**, or negra the first time. */
  figuresFrom: FigureName | null;
  /** What the highest pile of gaps is called now, which the figures transposition moves. */
  anchorFigure: FigureName;
  busy: boolean;
  onPreviewNotes: (semitones: number, from: number, to: number) => void;
  onPreviewFigures: (from: FigureName, to: FigureName) => void;
}) {
  const [mode, setMode] = useState<Mode>("notes");
  const [fromKey, setFromKey] = useState(MIDDLE_C);
  const [toKey, setToKey] = useState(MIDDLE_C);
  const start = figuresFrom ?? "negra";
  const [fromFigure, setFromFigure] = useState<FigureName>(start);
  const [toFigure, setToFigure] = useState<FigureName>(start);

  const semitones = toKey - fromKey;
  const steps = figureSteps(fromFigure, toFigure);
  // The ladder has seven rungs: a step that would take the main figure off either end is refused.
  const fits = steps === 0 || shiftFigure(anchorFigure, steps) !== null;

  return (
    <Stack spacing={1.5} data-transpose-tab={mode}>
      <Segmented<Mode> label="What to transpose" value={mode} options={MODES} onChange={setMode} />
      {mode === "notes" ? (
        <>
          <Box>
            <Typography variant="body2" color="text.secondary">
              From {spanishNoteShort(fromKey)}
            </Typography>
            <MiniPiano label="Transpose from" value={fromKey} onChange={setFromKey} />
          </Box>
          <Box>
            <Typography variant="body2" color="text.secondary">
              To {spanishNoteShort(toKey)}
            </Typography>
            <MiniPiano label="Transpose to" value={toKey} onChange={setToKey} />
          </Box>
          <Stack direction="row" spacing={1.5} sx={{ alignItems: "center" }}>
            <PillButton
              kind="primary"
              size="small"
              disabled={semitones === 0}
              busy={busy}
              onClick={() => onPreviewNotes(semitones, fromKey, toKey)}
              data-transpose-preview="notes"
            >
              Preview
            </PillButton>
            <Typography variant="body2" color="text.secondary" data-transpose-interval>
              {intervalWords(semitones)}
            </Typography>
          </Stack>
        </>
      ) : (
        <>
          <Box>
            <Typography variant="body2" color="text.secondary">
              From
            </Typography>
            <FigurePicker
              label="Transpose figures from"
              value={fromFigure}
              figures={FIGURES}
              onChange={setFromFigure}
            />
          </Box>
          <Box>
            <Typography variant="body2" color="text.secondary">
              To
            </Typography>
            <FigurePicker
              label="Transpose figures to"
              value={toFigure}
              figures={FIGURES}
              onChange={setToFigure}
            />
          </Box>
          <Stack direction="row" spacing={1.5} sx={{ alignItems: "center" }}>
            <PillButton
              kind="primary"
              size="small"
              disabled={steps === 0 || !fits}
              busy={busy}
              onClick={() => onPreviewFigures(fromFigure, toFigure)}
              data-transpose-preview="figures"
            >
              Preview
            </PillButton>
            {!fits ? (
              <Typography variant="body2" color="text.secondary">
                No shorter or longer figure left
              </Typography>
            ) : null}
          </Stack>
        </>
      )}
    </Stack>
  );
}

export default TransposeTab;
