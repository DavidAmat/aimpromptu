/**
 * The note toolbox: everything a reader can decide about the notes picked on the sheet.
 *
 * Split out of `RhythmPage.tsx` (implementation 02, Phase 2) with no change.
 */

import Button from "@mui/material/Button";
import ButtonGroup from "@mui/material/ButtonGroup";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Divider from "@mui/material/Divider";
import IconButton from "@mui/material/IconButton";
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
import type { Dispatch, SetStateAction } from "react";
import {
  MAX_EVEN_SPACING_SCALE,
  MIN_EVEN_SPACING_SCALE,
  type FingerNumber,
} from "@aimpromptu/grid-notation";
import FigureGlyph from "../../../components/time/FigureGlyph";
import { FIGURE_SHORT, PLAIN_FIGURES } from "../../../music/figures";
import { frameOf, handOf, type PrintedHand } from "../../../music/renderOverrides";
import { Toolbox } from "../../../ui";
import { EVEN_SPACING_STEP, FINGERS } from "./sheetConstants";
import type { FingerDraft, NoteActions } from "./useNoteActions";

export function NoteToolbox({
  open: notesToolbox,
  selectedNotes,
  notesAt,
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
    clearGrace,
    cueHere,
    toggleCueOnSelection,
    trillable,
    markTrillOnSelection,
    hideSelected,
  } = notes;
  return (
    <Toolbox
      open={notesToolbox && selectedNotes.length > 0}
      title={
        // Which note it is, rather than the word "Note" — a reader who has just clicked a
        // notehead already knows it is a note, and what they cannot read off a stack of ledger
        // lines at a glance is which one.
        selectedNotes.length === 1
          ? (pickedNoteName ?? "Note")
          : `${selectedNotes.length} notes`
      }
      subtitle={
        // The columns, each said once. A chord is three notes at one moment, and printing that
        // moment three times reads as three moments.
        selectedNotes.length > 0
          ? (() => {
              const columns = [...new Set(selectedNotes.map(frameOf))].sort(
                (a, z) => a - z,
              );
              return (
                columns
                  .slice(0, 4)
                  .map((column) => `f${column}`)
                  .join(", ") + (columns.length > 4 ? ", \u2026" : "")
              );
            })()
          : undefined
      }
      initialPosition={notesAt ?? { x: 420, y: 140 }}
      onClose={closeNotes}
      headerAction={
        /*
          From the notes to the columns they stand in, so the stretch is exactly the music that is
          picked rather than an aim at the ruler.
        */
        <Tooltip title="Mark the stretch from the first picked note to the last, and open the frames toolbox on it">
          <span>
            <Button
              size="small"
              color="inherit"
              startIcon={<SwapHorizIcon fontSize="small" />}
              onClick={selectRangeOfNotes}
              sx={{ textTransform: "none", whiteSpace: "nowrap" }}
            >
              Select frames
            </Button>
          </span>
        </Tooltip>
      }
    >
      <Stack spacing={1.25}>
        {/*
          Everything a reader can decide about a note, as controls rather than as prose.

          This panel used to explain each of its sections in a paragraph — what an acciaccatura
          was, how fingering numbers were read against a chord, what happened to a note taken off
          the page. All of it was true and none of it was being read: a reader who has already
          picked three noteheads wants a row of things to press. What is left is the shapes, the
          numbers and two letters, with the sentences moved into the tooltips where they are
          reachable and out of the way.
        */}

        {/*
          The figures, as the shapes they print as.

          A pill is filled when every picked chord is drawn as that figure already; pressing one
          names all of them, which is how a passage written as a mix of corcheas, semicorcheas and
          tresillos becomes one figure. Nothing moves — not a column, not a timing (D-18) — and a
          tresillo renamed here loses its 3, because it is now written as what it says it is.
        */}
        <Stack
          direction="row"
          spacing={0.5}
          sx={{ alignItems: "center", flexWrap: "wrap", rowGap: 0.5 }}
        >
          {PLAIN_FIGURES.map((name) => {
            const chosen = selectedPrintedFigure === name;
            return (
              <IconButton
                key={name}
                size="small"
                onClick={() => drawSelectionAs(name)}
                title={`Draw ${
                  selectedGroups.length === 1
                    ? "this chord"
                    : `all ${selectedGroups.length} chords`
                } as a ${FIGURE_SHORT[name].toLowerCase()}`}
                aria-label={`Draw as a ${FIGURE_SHORT[name]}`}
                aria-pressed={chosen}
                sx={{
                  borderRadius: 1,
                  border: 1,
                  borderColor: chosen ? "secondary.main" : "divider",
                  bgcolor: chosen ? "secondary.main" : "transparent",
                  color: chosen ? "secondary.contrastText" : "text.primary",
                  px: 0.5,
                  py: 0.25,
                }}
              >
                <FigureGlyph figure={name} size={24} />
              </IconButton>
            );
          })}
          <Tooltip title="Back to whatever the score called them">
            <span>
              <IconButton
                size="small"
                disabled={namedGroups.length === 0}
                onClick={unnameSelection}
                aria-label="Back to the score's own figures"
              >
                <BackspaceIcon fontSize="small" />
              </IconButton>
            </span>
          </Tooltip>
        </Stack>

        <Divider />

        {/* Which finger plays them. One number on all of them, or one each on a single chord. */}
        <Stack
          direction="row"
          spacing={1}
          sx={{ alignItems: "center", flexWrap: "wrap", rowGap: 0.5 }}
        >
          <Typography variant="caption" color="text.secondary" sx={{ minWidth: 48 }}>
            Finger
          </Typography>
          <ButtonGroup size="small">
            {FINGERS.map((finger) => (
              <Button
                key={finger}
                variant={
                  pickedFingers.includes(finger) ? "contained" : "outlined"
                }
                onClick={() => pressFinger(finger)}
                data-finger={finger}
                title={
                  oneChord
                    ? `Press one number for the whole chord, or ${oneChord.length} of them to give each notehead its own`
                    : "One number, on every note picked"
                }
              >
                {finger}
              </Button>
            ))}
          </ButtonGroup>
          <Tooltip title="Take the numbers off">
            <span>
              <IconButton
                size="small"
                disabled={
                  !selectedNotes.some((noteKey) => fingers[noteKey] !== undefined)
                }
                onClick={() => {
                  setFingerDraft({ forSelection: selectionKey, picked: [] });
                  applyFingers([], selectedNotes, oneChord);
                }}
                aria-label="Clear the fingering"
              >
                <BackspaceIcon fontSize="small" />
              </IconButton>
            </span>
          </Tooltip>
        </Stack>

        {/*
          Which hand plays them.

          Written onto the recording rather than onto the drawing, because the printed length of a
          note is the gap to the next onset in the same hand — so a note that changes hands renames
          its old neighbour, its new neighbour and itself. The button is two letters; the tooltip
          is where that sentence lives now.
        */}
        <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
          <Typography variant="caption" color="text.secondary" sx={{ minWidth: 48 }}>
            Hand
          </Typography>
          <ButtonGroup size="small">
            {(["right", "left"] as const).map((side) => {
              const on = selectedNotes.every(
                (noteKey) => handOf(noteKey) === side,
              );
              return (
                <Button
                  key={side}
                  variant={on ? "contained" : "outlined"}
                  disabled={movingHand || on}
                  onClick={() => void moveSelected(side)}
                  sx={{ minWidth: 34 }}
                  title={`Play with the ${side} hand \u2014 written onto the recording, so the figures around it are named again`}
                >
                  {side === "right" ? "R" : "L"}
                </Button>
              );
            })}
          </ButtonGroup>
          {movingHand ? <CircularProgress size={14} /> : null}
        </Stack>

        {/* How they are grouped, and how far apart they stand. Five things, so it may wrap. */}
        <Stack
          direction="row"
          spacing={0.5}
          sx={{ alignItems: "center", flexWrap: "wrap", rowGap: 0.5 }}
        >
          <Typography variant="caption" color="text.secondary" sx={{ minWidth: 48 }}>
            Beam
          </Typography>
          <Tooltip
            title={
              beamable
                ? "Beam all of these as one group, whatever the page would do with them"
                : "Pick two or more whole chords, all of them a corchea or shorter: a negra has no beam to share"
            }
          >
            <span>
              <IconButton
                size="small"
                color={joinedHere ? "secondary" : "default"}
                disabled={!beamable}
                onClick={joinBeams}
                aria-label="Beam these notes as one group"
              >
                <LinkIcon fontSize="small" />
              </IconButton>
            </span>
          </Tooltip>
          <Tooltip
            title={
              selectedChords.partial.length > 0
                ? `A beam holds a whole chord, so it can only be cut in front of all of it. Pick the rest of the notes at ${selectedChords.partial
                    .map((key) => `f${key.split(":")[1]}`)
                    .join(", ")} as well.`
                : brokenHere
                  ? "Join the beam again"
                  : "Cut the beam in front of these, so a new group runs on from them"
            }
          >
            <span>
              <IconButton
                size="small"
                color={brokenHere ? "secondary" : "default"}
                disabled={
                  selectedChords.partial.length > 0 ||
                  selectedChords.whole.length === 0
                }
                onClick={toggleBeamBreak}
                aria-label="Start a new beam here"
              >
                <ContentCutIcon fontSize="small" />
              </IconButton>
            </span>
          </Tooltip>
          <Divider orientation="vertical" flexItem sx={{ mx: 0.5 }} />
          {/*
            Set the run an equal distance apart, then open it or close it.

            A column belongs to the whole system, so a run of even corcheas in one hand is drawn
            unevenly wherever the other hand needs room at one of those moments. The page is not
            wrong when that happens — the space really is being used — but a beam of equal notes
            that is not equally spaced reads as an uneven performance, which is a worse lie than
            the width. This is the reader choosing evenness and paying for it in width, and the
            other hand moves with it.

            The plus and the minus stand down until the run is even, because until then there is
            no one distance for them to be a multiple of. And the minus stops at even rather than
            going below it: every gap is the sum of the widths its columns asked for, so closing
            one further would print one note over another. The minimums are the page's and only
            the maximum is the reader's.
          */}
          <Tooltip
            title={
              selectedRun === null
                ? "Pick two or more notes of one hand to set them an equal distance apart"
                : evenHere
                  ? "Back to the spacing the page measured"
                  : "Set these an equal distance apart, whatever the other hand needs at those moments"
            }
          >
            <span>
              <IconButton
                size="small"
                color={evenHere ? "secondary" : "default"}
                disabled={selectedRun === null}
                onClick={toggleEvenSpacing}
                aria-label="Set these notes an equal distance apart"
                aria-pressed={Boolean(evenHere)}
              >
                <DragHandleIcon fontSize="small" />
              </IconButton>
            </span>
          </Tooltip>
          <Tooltip
            title={
              !evenHere
                ? "Set them even first"
                : evenHere.scale >= MAX_EVEN_SPACING_SCALE
                  ? "As open as this run goes"
                  : "More room between them"
            }
          >
            <span>
              <IconButton
                size="small"
                disabled={!evenHere || evenHere.scale >= MAX_EVEN_SPACING_SCALE}
                onClick={() => nudgeEvenSpacing(EVEN_SPACING_STEP)}
                aria-label="More room between these notes"
              >
                <AddIcon fontSize="small" />
              </IconButton>
            </span>
          </Tooltip>
          <Tooltip
            title={
              !evenHere
                ? "Set them even first"
                : evenHere.scale <= MIN_EVEN_SPACING_SCALE
                  ? "As close as this run goes"
                  : "Less room between them"
            }
          >
            <span>
              <IconButton
                size="small"
                disabled={!evenHere || evenHere.scale <= MIN_EVEN_SPACING_SCALE}
                onClick={() => nudgeEvenSpacing(-EVEN_SPACING_STEP)}
                aria-label="Less room between these notes"
              >
                <RemoveIcon fontSize="small" />
              </IconButton>
            </span>
          </Tooltip>
          {evenHere && evenHere.scale !== 1 ? (
            <Typography variant="caption" color="text.secondary">
              {Math.round(evenHere.scale * 100)}%
            </Typography>
          ) : null}
        </Stack>

        <Divider />

        {/* The three marks that hang off a note rather than off a column. */}
        <Stack
          direction="row"
          spacing={1}
          sx={{ alignItems: "center", flexWrap: "wrap", rowGap: 0.75 }}
        >
          <Typography variant="caption" color="text.secondary" sx={{ minWidth: 48 }}>
            Marks
          </Typography>
          <Chip
            size="small"
            icon={<PianoIcon />}
            label={
              graceHere ? `Decoration ${noteNameAt(graceHere.row)}` : "Decoration"
            }
            color={graceHere ? "secondary" : "default"}
            variant={graceHere ? "filled" : "outlined"}
            disabled={onlyNote === null}
            title={
              onlyNote === null
                ? "Pick one notehead to lean a small note on it"
                : "A small note played just before this one. Pick its pitch on the keyboard."
            }
            onClick={() => setDecorationFor(onlyNote)}
            {...(graceHere ? { onDelete: clearGrace } : {})}
          />
          <Chip
            size="small"
            label="Small"
            color={cueHere ? "secondary" : "default"}
            variant={cueHere ? "filled" : "outlined"}
            title="Print these smaller than the rest of the page, so a florid run reads as decoration and takes less width"
            onClick={toggleCueOnSelection}
          />
          <Chip
            size="small"
            label="Trill"
            variant="outlined"
            disabled={!trillable}
            title={
              trillable
                ? "Write these as one held note with tr and a wavy line over it. Every alternation stays in the recording and still plays."
                : "Pick three or more onsets in one hand \u2014 the notes taking turns"
            }
            onClick={markTrillOnSelection}
          />
        </Stack>

        <Divider />

        <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
          <Tooltip title="Take them off the page — or press Delete. Command-Z brings them back, the recording keeps every one of them, and Remove all puts them back.">
            <IconButton
              size="small"
              color="error"
              onClick={hideSelected}
              aria-label={`Take ${
                selectedNotes.length === 1
                  ? "this note"
                  : `these ${selectedNotes.length} notes`
              } off the page`}
            >
              <DeleteOutlineIcon />
            </IconButton>
          </Tooltip>
          <Typography variant="caption" color="text.secondary">
            {selectedNotes.length === 1
              ? "Hold Command and click more noteheads to build a set."
              : oneChord
                ? `One chord of ${oneChord.length}.`
                : `${selectedGroups.length} chords.`}
          </Typography>
        </Stack>
      </Stack>
    </Toolbox>
  );
}

export default NoteToolbox;
