/**
 * The note toolbox: everything a reader can decide about the notes picked on the sheet.
 *
 * The figure they print as, the finger, the hand, the beam, even spacing, a decoration, small
 * print, a trill, and taking them off the page. Every control is an icon action or a short label
 * with a tooltip; what each one does is said in its tooltip (the 09 guidelines, plan section 11.6).
 */

import type { Dispatch, SetStateAction } from "react";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import ButtonGroup from "@mui/material/ButtonGroup";
import CircularProgress from "@mui/material/CircularProgress";
import Divider from "@mui/material/Divider";
import Stack from "@mui/material/Stack";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import AddIcon from "@mui/icons-material/Add";
import BackspaceIcon from "@mui/icons-material/BackspaceOutlined";
import ContentCutIcon from "@mui/icons-material/ContentCutOutlined";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutlineOutlined";
import DragHandleIcon from "@mui/icons-material/DragHandle";
import LinkIcon from "@mui/icons-material/LinkOutlined";
import PianoIcon from "@mui/icons-material/PianoOutlined";
import RemoveIcon from "@mui/icons-material/Remove";
import SwapHorizIcon from "@mui/icons-material/SwapHorizOutlined";
import TextDecreaseIcon from "@mui/icons-material/TextDecreaseOutlined";
import {
  MAX_EVEN_SPACING_SCALE,
  MIN_EVEN_SPACING_SCALE,
  type FingerNumber,
} from "@aimpromptu/grid-notation";
import FigureGlyph from "../../../components/time/FigureGlyph";
import { FIGURE_SHORT, PLAIN_FIGURES } from "../../../music/figures";
import { frameOf, handOf, type PrintedHand } from "../../../music/renderOverrides";
import { IconAction, Segmented, Toolbox } from "../../../ui";
import { EVEN_SPACING_STEP, FINGERS, formatSeconds } from "./sheetConstants";
import type { FingerDraft, NoteActions } from "./useNoteActions";

/** A row of the toolbox: a short label, then its controls. */
function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <Stack direction="row" spacing={0.5} sx={{ alignItems: "center", flexWrap: "wrap", rowGap: 0.5 }}>
      <Typography variant="body2" color="text.secondary" sx={{ minWidth: 52 }}>
        {label}
      </Typography>
      {children}
    </Stack>
  );
}

/** The trill mark, as the page prints it. */
const TrillGlyph = (
  <Box
    component="span"
    sx={{ fontFamily: "serif", fontStyle: "italic", fontWeight: 700, fontSize: 17, lineHeight: 1, px: 0.25 }}
  >
    tr
  </Box>
);

export function NoteToolbox({
  open: notesToolbox,
  selectedNotes,
  notesAt,
  frameMs,
  onClose: closeNotes,
  onSelectFrames: selectRangeOfNotes,
  notes,
  fingers,
  setFingerDraft,
  movingHand,
  onMoveHand: moveSelected,
  noteNameAt,
  onOpenDecoration: setDecorationFor,
}: {
  open: boolean;
  selectedNotes: readonly string[];
  notesAt: { x: number; y: number } | undefined;
  frameMs: number;
  onClose: () => void;
  onSelectFrames: () => void;
  notes: NoteActions;
  fingers: Record<string, FingerNumber>;
  setFingerDraft: Dispatch<SetStateAction<FingerDraft | null>>;
  movingHand: boolean;
  onMoveHand: (to: PrintedHand) => Promise<void>;
  noteNameAt: (row: number) => string;
  onOpenDecoration: (noteKey: string | null) => void;
}) {
  const {
    pickedNoteName,
    selectedPrintedFigure,
    drawSelectionAs,
    selectedGroups,
    namedGroups,
    unnameSelection,
    pickedFingers,
    pressFinger,
    oneChord,
    selectionKey,
    applyFingers,
    beamable,
    joinedHere,
    joinBeams,
    selectedChords,
    brokenHere,
    toggleBeamBreak,
    selectedRun,
    evenHere,
    toggleEvenSpacing,
    nudgeEvenSpacing,
    graceHere,
    onlyNote,
    cueHere,
    toggleCueOnSelection,
    trillable,
    markTrillOnSelection,
    hideSelected,
  } = notes;

  const columns = [...new Set(selectedNotes.map(frameOf))].sort((a, z) => a - z);
  const first = columns[0];
  const last = columns[columns.length - 1];
  const at = (column: number) => formatSeconds((column * frameMs) / 1000);
  const sides = new Set(selectedNotes.map(handOf));
  const handNow = sides.size === 1 ? [...sides][0]! : "mixed";

  return (
    <Toolbox
      open={notesToolbox && selectedNotes.length > 0}
      title={
        // Which note it is, rather than the word "Note": what a reader cannot read off a stack of
        // ledger lines at a glance is which one.
        selectedNotes.length === 1 ? (pickedNoteName ?? "Note") : `${selectedNotes.length} notes`
      }
      subtitle={
        first === undefined || last === undefined
          ? undefined
          : first === last
            ? at(first)
            : `${at(first)} – ${at(last)}`
      }
      initialPosition={notesAt ?? { x: 420, y: 140 }}
      onClose={closeNotes}
      headerAction={
        <IconAction
          title="Select the frames of these notes"
          icon={<SwapHorizIcon fontSize="small" />}
          onClick={selectRangeOfNotes}
        />
      }
    >
      <Stack spacing={1.25}>
        {/*
          The figures, as the shapes they print as. One is pressed when every picked chord is drawn
          as that figure; pressing one names all of them. Nothing moves (D-18).
        */}
        <Stack direction="row" spacing={0.25} sx={{ alignItems: "center", flexWrap: "wrap", rowGap: 0.5 }}>
          {PLAIN_FIGURES.map((name) => (
            <IconAction
              key={name}
              title={`Draw ${
                selectedGroups.length === 1 ? "as a" : `all ${selectedGroups.length} chords as a`
              } ${FIGURE_SHORT[name].toLowerCase()}`}
              icon={<FigureGlyph figure={name} size={22} />}
              active={selectedPrintedFigure === name}
              onClick={() => drawSelectionAs(name)}
            />
          ))}
          <IconAction
            title="Back to the figures of the sheet"
            icon={<BackspaceIcon fontSize="small" />}
            disabled={namedGroups.length === 0}
            onClick={unnameSelection}
          />
        </Stack>

        <Divider />

        {/* One number on all of them, or one each on a single chord. */}
        <Row label="Finger">
          <ButtonGroup size="small">
            {FINGERS.map((finger) => (
              <Tooltip
                key={finger}
                title={
                  oneChord
                    ? `Finger ${finger}. Press up to ${oneChord.length} numbers, one per note, low to high`
                    : `Finger ${finger} on every note picked`
                }
              >
                <Button
                  variant={pickedFingers.includes(finger) ? "contained" : "outlined"}
                  onClick={() => pressFinger(finger)}
                  data-finger={finger}
                  sx={{ minWidth: 32, px: 0 }}
                >
                  {finger}
                </Button>
              </Tooltip>
            ))}
          </ButtonGroup>
          <IconAction
            title="Remove the finger numbers"
            icon={<BackspaceIcon fontSize="small" />}
            disabled={!selectedNotes.some((noteKey) => fingers[noteKey] !== undefined)}
            onClick={() => {
              setFingerDraft({ forSelection: selectionKey, picked: [] });
              applyFingers([], selectedNotes, oneChord);
            }}
          />
        </Row>

        {/*
          Which hand plays them. Written onto the recording, because the printed length of a note is
          the gap to the next onset in the same hand: a note that changes hands renames its
          neighbours too.
        */}
        <Row label="Hand">
          <Segmented<PrintedHand | "mixed">
            label="Which hand plays these notes"
            value={handNow}
            disabled={movingHand}
            options={[
              { value: "right", label: "Right", tooltip: "Play with the right hand" },
              { value: "left", label: "Left", tooltip: "Play with the left hand" },
            ]}
            onChange={(side) => {
              if (side !== "mixed" && side !== handNow) void moveSelected(side);
            }}
          />
          {movingHand ? <CircularProgress size={14} sx={{ ml: 1 }} /> : null}
        </Row>

        <Row label="Beam">
          <IconAction
            title="Beam these notes as one group"
            disabledTitle="Pick two or more whole chords, all a corchea or shorter"
            icon={<LinkIcon fontSize="small" />}
            active={joinedHere}
            disabled={!beamable}
            onClick={joinBeams}
          />
          <IconAction
            title={brokenHere ? "Join the beam again" : "Start a new beam here"}
            disabledTitle={
              selectedChords.partial.length > 0
                ? `Pick the whole chord at ${selectedChords.partial
                    .map((key) => at(Number(key.split(":")[1])))
                    .join(", ")}: a beam holds whole chords`
                : "Pick a note first"
            }
            icon={<ContentCutIcon fontSize="small" />}
            active={brokenHere}
            disabled={selectedChords.partial.length > 0 || selectedChords.whole.length === 0}
            onClick={toggleBeamBreak}
          />
          <Divider orientation="vertical" flexItem sx={{ mx: 0.5 }} />
          {/*
            Even spacing: a run of one hand set an equal distance apart, paid for in width. The plus
            and the minus wait until the run is even, because until then there is no one distance
            for them to be a multiple of.
          */}
          <IconAction
            title={evenHere ? "Back to the spacing the page measured" : "Set these an equal distance apart"}
            disabledTitle="Pick two or more notes of one hand"
            icon={<DragHandleIcon fontSize="small" />}
            active={Boolean(evenHere)}
            disabled={selectedRun === null}
            onClick={toggleEvenSpacing}
          />
          <IconAction
            title="More room between them"
            disabledTitle={!evenHere ? "Set them an equal distance apart first" : "As open as this run goes"}
            icon={<AddIcon fontSize="small" />}
            disabled={!evenHere || evenHere.scale >= MAX_EVEN_SPACING_SCALE}
            onClick={() => nudgeEvenSpacing(EVEN_SPACING_STEP)}
          />
          <IconAction
            title="Less room between them"
            disabledTitle={!evenHere ? "Set them an equal distance apart first" : "As close as this run goes"}
            icon={<RemoveIcon fontSize="small" />}
            disabled={!evenHere || evenHere.scale <= MIN_EVEN_SPACING_SCALE}
            onClick={() => nudgeEvenSpacing(-EVEN_SPACING_STEP)}
          />
          {evenHere && evenHere.scale !== 1 ? (
            <Typography variant="body2" color="text.secondary">
              {Math.round(evenHere.scale * 100)}%
            </Typography>
          ) : null}
        </Row>

        <Row label="Marks">
          <IconAction
            title={
              graceHere
                ? `Decoration ${noteNameAt(graceHere.row)}: change it on the keyboard`
                : "Add a decoration: a small note played just before this one"
            }
            disabledTitle="Pick one note to add a decoration"
            icon={<PianoIcon fontSize="small" />}
            active={Boolean(graceHere)}
            disabled={onlyNote === null}
            onClick={() => setDecorationFor(onlyNote)}
          />
          <IconAction
            title={cueHere ? "Print these at full size again" : "Print these smaller"}
            icon={<TextDecreaseIcon fontSize="small" />}
            active={cueHere}
            onClick={toggleCueOnSelection}
          />
          <IconAction
            title="Write these as one held note with a trill"
            disabledTitle="Pick three or more onsets in one hand"
            icon={TrillGlyph}
            disabled={!trillable}
            onClick={markTrillOnSelection}
          />
        </Row>

        <Divider />

        <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
          <IconAction
            title={`Take ${selectedNotes.length === 1 ? "this note" : `these ${selectedNotes.length} notes`} off the page`}
            shortcut="Delete"
            icon={<DeleteOutlineIcon />}
            danger
            onClick={hideSelected}
          />
          {selectedNotes.length > 1 ? (
            <Typography variant="body2" color="text.secondary">
              {oneChord ? `One chord of ${oneChord.length}` : `${selectedGroups.length} chords`}
            </Typography>
          ) : null}
        </Stack>
      </Stack>
    </Toolbox>
  );
}

export default NoteToolbox;
