/**
 * The sheet toolbox: everything about the whole piano sheet, in four tabs (plan section 11.4).
 *
 * **Title** (what the sheet prints above the music), **Key** (the key signature of the piece),
 * **Figures** (what the highest pile of gaps is called) and **Layout** (spacing, mark size, zoom,
 * frame numbers). Every change in it is one undo step, because every value is an edit of the
 * sheet; zoom and the frame numbers are how the page is looked at and are not saved. Phase 7 turns
 * **Figures** into **Transpose** (notes and figures) and adds **Lyrics**.
 */

import { useState, type Dispatch, type SetStateAction } from "react";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import FormControlLabel from "@mui/material/FormControlLabel";
import MenuItem from "@mui/material/MenuItem";
import Slider from "@mui/material/Slider";
import Stack from "@mui/material/Stack";
import Switch from "@mui/material/Switch";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import type { OttavaAnnotation } from "@aimpromptu/grid-notation";
import {
  KEY_LABELS,
  KEY_SIGNATURES,
  type FigureName,
  type KeySignatureName,
} from "../../../api";
import {
  DEFAULT_LINE_SPACING,
  DEFAULT_NOTE_SPACING,
  MAX_LINE_SPACING,
  MAX_NOTE_SPACING,
  MAX_ZOOM,
  MIN_LINE_SPACING,
  MIN_NOTE_SPACING,
  MIN_ZOOM,
} from "../../../components/time/TimeScoreView";
import type { EditHistory } from "../../../hooks/useEditHistory";
import { FigurePicker, Segmented, Toolbox } from "../../../ui";
import type { SheetEdits } from "./sheetEdits";

export type SheetTab = "title" | "key" | "figures" | "layout";

const TABS = [
  { value: "title" as const, label: "Title" },
  { value: "key" as const, label: "Key" },
  { value: "figures" as const, label: "Figures" },
  { value: "layout" as const, label: "Layout" },
];

/** The figures the main figure can be: the plain rungs a piano sheet is mostly written in. */
const MAIN_FIGURES: readonly FigureName[] = ["blanca", "negra", "corchea", "semicorchea"];

const WIDTH = 360;

export function SheetToolbox({
  open,
  onClose,
  tab,
  onTab,
  state,
  set,
  pieceLabel,
  keyHint,
  ottavaHint,
  onTakeOttavaHint,
  frameLabelsOn,
  setFrameLabelsOn,
  sheetZoom,
  setSheetZoom,
}: {
  open: boolean;
  onClose: () => void;
  tab: SheetTab;
  onTab: (tab: SheetTab) => void;
  state: SheetEdits;
  set: EditHistory<SheetEdits>["set"];
  /** The project's name: what the sheet prints as its title until one is written here. */
  pieceLabel: string | undefined;
  keyHint: { best: KeySignatureName; saved: number } | null;
  ottavaHint: readonly OttavaAnnotation[];
  onTakeOttavaHint: () => void;
  frameLabelsOn: boolean;
  setFrameLabelsOn: Dispatch<SetStateAction<boolean>>;
  sheetZoom: number;
  setSheetZoom: Dispatch<SetStateAction<number>>;
}) {
  return (
    <Toolbox
      open={open}
      title="Sheet"
      initialPosition={{
        x: Math.max(8, window.innerWidth - WIDTH - 24),
        y: 120,
      }}
      onClose={onClose}
      width={WIDTH}
    >
      <Stack spacing={2} data-sheet-toolbox={tab}>
        <Segmented<SheetTab> label="Sheet toolbox tab" value={tab} options={TABS} onChange={onTab} />
        {tab === "title" ? <TitleTab state={state} set={set} pieceLabel={pieceLabel} /> : null}
        {tab === "key" ? <KeyTab state={state} set={set} keyHint={keyHint} /> : null}
        {tab === "figures" ? (
          <FigurePicker
            label="Main figure"
            value={state.anchorFigure}
            figures={MAIN_FIGURES}
            onChange={(figure) => set.anchorFigure(figure)}
          />
        ) : null}
        {tab === "layout" ? (
          <LayoutTab
            state={state}
            set={set}
            ottavaHint={ottavaHint}
            onTakeOttavaHint={onTakeOttavaHint}
            frameLabelsOn={frameLabelsOn}
            setFrameLabelsOn={setFrameLabelsOn}
            sheetZoom={sheetZoom}
            setSheetZoom={setSheetZoom}
          />
        ) : null}
      </Stack>
    </Toolbox>
  );
}

type TitleField = "title" | "subtitle" | "artist";

/**
 * Three fields, each written to the sheet when the reader leaves it or presses Enter.
 *
 * Not on every key: one word typed would otherwise be one undo step per letter.
 */
function TitleTab({
  state,
  set,
  pieceLabel,
}: {
  state: SheetEdits;
  set: EditHistory<SheetEdits>["set"];
  pieceLabel: string | undefined;
}) {
  const [draft, setDraft] = useState<{ field: TitleField; text: string } | null>(null);
  const valueOf = (field: TitleField) =>
    draft?.field === field ? draft.text : (state[field] ?? "");
  const commit = (field: TitleField) => {
    if (draft?.field !== field) return;
    const text = draft.text.trim();
    const next = text.length > 0 ? text : null;
    if (next !== state[field]) set[field](next);
    setDraft(null);
  };
  const field = (name: TitleField, label: string, placeholder?: string) => (
    <TextField
      size="small"
      label={label}
      value={valueOf(name)}
      placeholder={placeholder}
      slotProps={{ htmlInput: { maxLength: 200 }, inputLabel: { shrink: true } }}
      onChange={(event) => setDraft({ field: name, text: event.target.value })}
      onBlur={() => commit(name)}
      onKeyDown={(event) => {
        if (event.key === "Enter") commit(name);
      }}
      fullWidth
    />
  );
  return (
    <Stack spacing={1.5}>
      {field("title", "Title", pieceLabel)}
      {field("subtitle", "Subtitle")}
      {field("artist", "Artist")}
    </Stack>
  );
}

function KeyTab({
  state,
  set,
  keyHint,
}: {
  state: SheetEdits;
  set: EditHistory<SheetEdits>["set"];
  keyHint: { best: KeySignatureName; saved: number } | null;
}) {
  return (
    <Stack spacing={1.5}>
      <TextField
        select
        size="small"
        label="Key signature"
        value={state.keySignature}
        onChange={(event) => set.keySignature(event.target.value as KeySignatureName)}
        fullWidth
      >
        {KEY_SIGNATURES.map((name) => (
          <MenuItem key={name} value={name}>
            {KEY_LABELS[name]}
          </MenuItem>
        ))}
      </TextField>
      {/*
        The fewest accidentals is applied when the sheet is first written (plan section 11.3); after
        the reader has chosen another key, the same answer is one press away.
      */}
      {keyHint ? (
        <Box>
          <Button size="small" onClick={() => set.keySignature(keyHint.best)}>
            Use {KEY_LABELS[keyHint.best]}
            {keyHint.saved > 0 ? ` (${keyHint.saved} fewer accidentals)` : ""}
          </Button>
        </Box>
      ) : null}
    </Stack>
  );
}

/** One labelled slider. The value shows on the thumb while it moves. */
function Setting({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <Box>
      <Typography variant="body2" color="text.secondary">
        {label}
      </Typography>
      {children}
    </Box>
  );
}

function LayoutTab({
  state,
  set,
  ottavaHint,
  onTakeOttavaHint,
  frameLabelsOn,
  setFrameLabelsOn,
  sheetZoom,
  setSheetZoom,
}: {
  state: SheetEdits;
  set: EditHistory<SheetEdits>["set"];
  ottavaHint: readonly OttavaAnnotation[];
  onTakeOttavaHint: () => void;
  frameLabelsOn: boolean;
  setFrameLabelsOn: Dispatch<SetStateAction<boolean>>;
  sheetZoom: number;
  setSheetZoom: Dispatch<SetStateAction<number>>;
}) {
  return (
    <Stack spacing={1}>
      <Setting label="Space between notes">
        <Slider
          size="small"
          min={MIN_NOTE_SPACING}
          max={MAX_NOTE_SPACING}
          step={2}
          marks={[{ value: DEFAULT_NOTE_SPACING }]}
          value={state.noteSpacing}
          onChange={(_, value) => set.noteSpacing(value as number)}
          valueLabelDisplay="auto"
          aria-label="Space between notes"
        />
      </Setting>
      <Setting label="Space between lines">
        <Slider
          size="small"
          min={MIN_LINE_SPACING}
          max={MAX_LINE_SPACING}
          step={4}
          marks={[{ value: DEFAULT_LINE_SPACING }]}
          value={state.lineSpacing}
          onChange={(_, value) => set.lineSpacing(value as number)}
          valueLabelDisplay="auto"
          aria-label="Space between lines"
        />
      </Setting>
      <Setting label="Size of marks">
        <Slider
          size="small"
          min={50}
          max={200}
          step={10}
          marks={[{ value: 100 }]}
          value={Math.round(state.annotationScale * 100)}
          onChange={(_, value) => set.annotationScale((value as number) / 100)}
          valueLabelDisplay="auto"
          valueLabelFormat={(value) => `${value}%`}
          aria-label="Size of the fingering, the words and the trill marks"
        />
      </Setting>
      <Setting label="Zoom">
        <Slider
          size="small"
          min={MIN_ZOOM * 100}
          max={MAX_ZOOM * 100}
          step={10}
          marks={[{ value: MIN_ZOOM * 100 }]}
          value={Math.round(sheetZoom * 100)}
          onChange={(_, value) => setSheetZoom((value as number) / 100)}
          valueLabelDisplay="auto"
          valueLabelFormat={(value) => `${value}%`}
          aria-label="Zoom (also Command and scroll over the sheet)"
        />
      </Setting>
      <FormControlLabel
        control={
          <Switch
            size="small"
            checked={frameLabelsOn}
            onChange={(event) => setFrameLabelsOn(event.target.checked)}
          />
        }
        label="Frame numbers"
      />
      <FormControlLabel
        control={
          <Switch
            size="small"
            checked={state.dropDecorative}
            onChange={(event) => set.dropDecorative(event.target.checked)}
          />
        }
        label="Hide decorative notes"
      />
      {ottavaHint.length > 0 ? (
        <Box>
          <Button size="small" onClick={onTakeOttavaHint}>
            Group high notes under 8va ({ottavaHint.length})
          </Button>
        </Box>
      ) : null}
    </Stack>
  );
}

export default SheetToolbox;
