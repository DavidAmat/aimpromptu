/**
 * The sheet toolbox of the new sheet (implementation 03, Phase 8): what the reader says about the whole sheet, in
 * five tabs, each change written at once as one step of undo (the edit model of Phase 6).
 *
 * - **Info** (named Title until 2026-10-30): the title, subtitle and artist printed above the sheet (and on the PDF);
 *   each is written when the field is left or Enter is pressed, so a word is one step, not one per letter. They stay
 *   editable while the AI writes the sheet (the user, 2026-10-30): they touch no note, and the run keeps them.
 * - **Key**: the armadura of the piece, on both clefs (the armaduras of passages stay); when another one prints fewer
 *   signs over the whole piece, a button names it.
 * - **Transpose**: **Notes** (every note moved, the sheet with them) and **Figures** (every figure renamed by the same
 *   number of steps; nothing moves on the page), each with **Preview**, as on the old sheet.
 * - **Lyrics**: the old sheet's tab as it was: the pasted words, the pool, the edit toolbar of the picked pieces.
 * - **View**: **Zoom** (how big the page draws, not saved with the sheet) and **Space between lines** (saved). The
 *   user dropped the rest of the old Layout tab (Phase 8): the spacing is measured, the marks have one size, there
 *   are no frame numbers, grace notes replace the hidden decorative notes, and **Clefs by the rule** of a stretch
 *   replaces grouping high notes under 8va.
 */

import { useEffect, useState, type Dispatch, type SetStateAction } from "react";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import MenuItem from "@mui/material/MenuItem";
import Slider from "@mui/material/Slider";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { sheetApi, type FigureName, type FramesSheet, type LyricLine, type ReadingEdit, type SheetTitles } from "../../../../api";
import { figureSteps } from "../../../../music/transpose";
import { Segmented, Toolbox } from "../../../../ui";
import { LyricsTab } from "../LyricsTab";
import { TransposeTab } from "../TransposeTab";
import { ARMADURAS, keyName } from "./readingTools";

export type FramesSheetTab = "title" | "key" | "transpose" | "lyrics" | "view";

const TABS = [
  { value: "title" as const, label: "Info" },
  { value: "key" as const, label: "Key" },
  { value: "transpose" as const, label: "Transpose" },
  { value: "lyrics" as const, label: "Lyrics" },
  { value: "view" as const, label: "View" },
];

const WIDTH = 400;

/** The zoom of the page, and the space between lines (staff spaces; the engine's own is 5). */
export const MIN_ZOOM = 0.7;
export const MAX_ZOOM = 2;
const LINE_SPACE = { min: 2, max: 16, own: 5 };

export function FramesSheetToolbox({
  open,
  onClose,
  tab,
  onTab,
  audioUuid,
  sheet,
  pieceLabel,
  onEdit,
  busy,
  locked,
  aiRunning,
  transposing,
  onPreviewNotes,
  onPreviewFigures,
  zoom,
  setZoom,
  lyrics,
  tabs,
}: {
  open: boolean;
  onClose: () => void;
  tab: FramesSheetTab;
  onTab: (tab: FramesSheetTab) => void;
  audioUuid: string;
  sheet: FramesSheet;
  /** The project's name: the title until one is written here. */
  pieceLabel: string | undefined;
  onEdit: (change: ReadingEdit) => void;
  busy: boolean;
  /** Why nothing can be changed now (the AI writes the sheet), or `null`. */
  locked: string | null;
  /** The AI writes the sheet now: only the Info tab's fields can be changed. */
  aiRunning: boolean;
  transposing: boolean;
  onPreviewNotes: (semitones: number) => void;
  onPreviewFigures: (steps: number) => void;
  zoom: number;
  setZoom: (zoom: number) => void;
  /** What the Lyrics tab of the old sheet needs, adapted by the page. */
  lyrics: {
    lines: readonly LyricLine[];
    pool: readonly string[];
    picked: readonly number[];
    setLines: Dispatch<SetStateAction<readonly LyricLine[]>>;
    setPool: Dispatch<SetStateAction<readonly string[]>>;
    setPicked: Dispatch<SetStateAction<readonly number[]>>;
    onRefused: (why: string) => void;
    onPoolDrag: (index: number | null) => void;
    pasted: string;
    setPasted: (text: string) => void;
    savedText: string | null;
    poolUnsaved: boolean;
    saving: boolean;
    onSave: (text: string) => void;
  };
  /** The tabs shown (a take's sheet, Record in Sheet: Key, Transpose and View); all of them by default. */
  tabs?: readonly FramesSheetTab[];
}) {
  const disabled = busy || locked !== null;
  const shownTabs = tabs ? TABS.filter((one) => tabs.includes(one.value)) : TABS;
  return (
    <Toolbox
      open={open}
      title="Sheet"
      subtitle={locked ?? undefined}
      initialPosition={{ x: Math.max(8, window.innerWidth - WIDTH - 24), y: 120 }}
      onClose={onClose}
      width={WIDTH}
    >
      <Stack spacing={2} data-sheet-toolbox={tab} data-frames-sheet-toolbox>
        <Segmented<FramesSheetTab> label="Sheet toolbox tab" value={tab} options={shownTabs} onChange={onTab} />
        {tab === "title" ? (
          <TitleTab
            titles={sheet.titles}
            pieceLabel={pieceLabel}
            disabled={busy || (locked !== null && !aiRunning)}
            onEdit={onEdit}
          />
        ) : null}
        {tab === "key" ? <KeyTab audioUuid={audioUuid} sheet={sheet} disabled={disabled} onEdit={onEdit} /> : null}
        {tab === "transpose" ? (
          <Box sx={disabled ? { opacity: 0.5, pointerEvents: "none" } : undefined}>
            <TransposeTab
              figuresFrom={null}
              anchorFigure="negra"
              busy={transposing}
              onPreviewNotes={(semitones) => onPreviewNotes(semitones)}
              // The ladder of `figureSteps` runs from the shortest figure; the backend counts steps towards shorter.
              onPreviewFigures={(from: FigureName, to: FigureName) => onPreviewFigures(-figureSteps(from, to))}
            />
          </Box>
        ) : null}
        {tab === "lyrics" ? (
          <Box sx={disabled ? { opacity: 0.5, pointerEvents: "none" } : undefined}>
            <LyricsTab
              lyrics={lyrics.lines}
              pool={lyrics.pool}
              picked={lyrics.picked}
              setLyrics={lyrics.setLines}
              setPool={lyrics.setPool}
              setPicked={lyrics.setPicked}
              onRefused={lyrics.onRefused}
              onPoolDrag={lyrics.onPoolDrag}
              pasted={lyrics.pasted}
              setPasted={lyrics.setPasted}
              savedText={lyrics.savedText}
              poolUnsaved={lyrics.poolUnsaved}
              savingText={lyrics.saving}
              onSaveText={lyrics.onSave}
              pickedTools={false}
            />
          </Box>
        ) : null}
        {tab === "view" ? (
          <ViewTab lineSpace={sheet.lineSpace} disabled={disabled} onEdit={onEdit} zoom={zoom} setZoom={setZoom} />
        ) : null}
      </Stack>
    </Toolbox>
  );
}

type TitleField = keyof SheetTitles;

/** Three fields, each written when the reader leaves it or presses Enter: one word typed is one step, not one per
 * letter. */
function TitleTab({
  titles,
  pieceLabel,
  disabled,
  onEdit,
}: {
  titles: SheetTitles;
  pieceLabel: string | undefined;
  disabled: boolean;
  onEdit: (change: ReadingEdit) => void;
}) {
  const [draft, setDraft] = useState<{ field: TitleField; text: string } | null>(null);
  const valueOf = (field: TitleField) => (draft?.field === field ? draft.text : (titles[field] ?? ""));
  const commit = (field: TitleField) => {
    if (draft?.field !== field) return;
    const text = draft.text.trim();
    setDraft(null);
    if (text !== (titles[field] ?? "")) onEdit({ action: "titles", value: { [field]: text } });
  };
  const field = (name: TitleField, label: string, placeholder?: string) => (
    <TextField
      size="small"
      label={label}
      value={valueOf(name)}
      placeholder={placeholder}
      disabled={disabled}
      slotProps={{ htmlInput: { maxLength: 200, "data-title-field": name }, inputLabel: { shrink: true } }}
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

/** The armadura of the piece, and the one with the fewest signs over the whole piece. */
function KeyTab({
  audioUuid,
  sheet,
  disabled,
  onEdit,
}: {
  audioUuid: string;
  sheet: FramesSheet;
  disabled: boolean;
  onEdit: (change: ReadingEdit) => void;
}) {
  const key = sheet.reading.key;
  const last = sheet.columns.length > 0 ? sheet.columns[sheet.columns.length - 1].frame + 1 : 1;
  const [hint, setHint] = useState<{ for: string; fewest: number; saved: number } | null>(null);
  const asked = `${audioUuid}:${key}:${last}`;
  useEffect(() => {
    const controller = new AbortController();
    sheetApi
      .stretchKeys(audioUuid, 0, last, controller.signal)
      .then((found) => setHint({ for: asked, fewest: found.fewest, saved: found.signs - found.fewestSigns }))
      .catch(() => undefined);
    return () => controller.abort();
  }, [audioUuid, last, asked]);
  const offer = hint && hint.for === asked && hint.fewest !== key && hint.saved > 0 ? hint : null;
  return (
    <Stack spacing={1.5}>
      <TextField
        select
        size="small"
        label="Armadura of the piece"
        value={key}
        disabled={disabled}
        onChange={(event) => onEdit({ action: "piece-key", value: Number(event.target.value) })}
        fullWidth
        slotProps={{ htmlInput: { "data-testid": "piece-key" } }}
      >
        {ARMADURAS.map((one) => (
          <MenuItem key={one.fifths} value={one.fifths}>
            {one.label}
          </MenuItem>
        ))}
      </TextField>
      {offer ? (
        <Box>
          <Button size="small" disabled={disabled} onClick={() => onEdit({ action: "piece-key", value: offer.fewest })}>
            Use {keyName(offer.fewest)} ({offer.saved} fewer {offer.saved === 1 ? "sign" : "signs"})
          </Button>
        </Box>
      ) : null}
      <Typography variant="body2" color="text.secondary">
        Spelling only: no note moves. A passage marked above the staves can take its own armadura.
      </Typography>
    </Stack>
  );
}

function ViewTab({
  lineSpace,
  disabled,
  onEdit,
  zoom,
  setZoom,
}: {
  lineSpace: number | null;
  disabled: boolean;
  onEdit: (change: ReadingEdit) => void;
  zoom: number;
  setZoom: (zoom: number) => void;
}) {
  const saved = lineSpace ?? LINE_SPACE.own;
  const [space, setSpace] = useState<{ for: number; value: number } | null>(null);
  const shown = space && space.for === saved ? space.value : saved;
  return (
    <Stack spacing={1}>
      <Box>
        <Typography variant="body2" color="text.secondary">
          Zoom
        </Typography>
        <Slider
          size="small"
          min={MIN_ZOOM * 100}
          max={MAX_ZOOM * 100}
          step={10}
          marks={[{ value: 100 }]}
          value={Math.round(zoom * 100)}
          onChange={(_, value) => setZoom((value as number) / 100)}
          valueLabelDisplay="auto"
          valueLabelFormat={(value) => `${value}%`}
          aria-label="Zoom (also Command and scroll over the sheet)"
        />
      </Box>
      <Box>
        <Typography variant="body2" color="text.secondary">
          Space between lines
        </Typography>
        <Slider
          size="small"
          min={LINE_SPACE.min}
          max={LINE_SPACE.max}
          step={0.5}
          marks={[{ value: LINE_SPACE.own }]}
          value={shown}
          disabled={disabled}
          onChange={(_, value) => setSpace({ for: saved, value: value as number })}
          onChangeCommitted={(_, value) => {
            const next = value as number;
            if (next !== saved) onEdit({ action: "line-space", value: next === LINE_SPACE.own ? null : next });
          }}
          valueLabelDisplay="auto"
          aria-label="Space between lines"
          data-testid="line-space"
        />
      </Box>
    </Stack>
  );
}

export default FramesSheetToolbox;
