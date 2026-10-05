/**
 * The two keyboards of the Sheet step: what is sounding under the playhead, and the decoration of
 * one picked note.
 *
 * Split out of `RhythmPage.tsx` (implementation 02, Phase 2).
 */

import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutlineOutlined";
import type { GraceNote } from "../../../api";
import { rowOf, type PrintedHand } from "../../../music/renderOverrides";
import { Piano } from "../../../piano/Piano";
import { IconAction, Segmented, Toolbox } from "../../../ui";
import {
  DECORATION_COLOUR,
  formatSeconds,
  KEY_LEGEND,
  PRINCIPAL_COLOUR,
  type SoundingNote,
} from "./sheetConstants";

export function PianoToolbox({
  open: pianoOpen,
  onClose,
  playheadFrame,
  frameMs,
  addHand,
  setAddHand,
  addingNote,
  soundingColours,
  soundingNow,
  onKeyPress: pressKeyboardKey,
  noteNameAt,
}: {
  open: boolean;
  onClose: () => void;
  playheadFrame: number | null;
  frameMs: number;
  addHand: PrintedHand;
  setAddHand: (hand: PrintedHand) => void;
  addingNote: boolean;
  soundingColours: Record<number, string>;
  soundingNow: readonly SoundingNote[];
  onKeyPress: (row: number) => void;
  noteNameAt: (row: number) => string;
}) {
  return (
    <Toolbox
      open={pianoOpen}
      title="Piano"
      subtitle={
        playheadFrame === null ? undefined : formatSeconds((playheadFrame * frameMs) / 1000)
      }
      initialPosition={{ x: 24, y: Math.max(80, window.innerHeight - 300) }}
      onClose={onClose}
      width={760}
    >
      <Stack spacing={1}>
        {/*
          The keyboard as a way of editing a chord, which is the shortest route there is to
          "this chord has a note in it that was never played" and to "this chord is missing one".
          On the staves those are a notehead among five others; here they are a key that is lit
          when it should be dark, or dark when it should be lit.
        */}
        <Stack
          direction="row"
          spacing={1.5}
          sx={{ alignItems: "center", flexWrap: "wrap", rowGap: 1 }}
        >
          <Typography variant="body2" color="text.secondary">
            Add to
          </Typography>
          <Segmented<PrintedHand>
            label="Which hand a key you add goes to"
            value={addHand}
            onChange={setAddHand}
            options={[
              { value: "right", label: "Right", tooltip: "A dark key you click is added to the right hand" },
              { value: "left", label: "Left", tooltip: "A dark key you click is added to the left hand" },
            ]}
          />
          {/*
            The legend, and the only explanation the panel needs.

            Four colours and four names. It replaces a paragraph under the keyboard that said the
            same thing in prose — and a reader looking at a lit key wants to look *across* at a
            swatch of the same colour, not down at a sentence about it. `onset` and `sustain` are
            the words the roll and the matrix already use for struck and still-sounding, so this
            is one vocabulary rather than a second one invented for this panel.
          */}
          {KEY_LEGEND.map((entry) => (
            <Stack
              key={entry.label}
              direction="row"
              spacing={0.5}
              sx={{ alignItems: "center" }}
            >
              <Box
                sx={{
                  width: 12,
                  height: 12,
                  borderRadius: 0.5,
                  bgcolor: entry.colour,
                }}
              />
              <Typography variant="caption" color="text.secondary">
                {entry.label}
              </Typography>
            </Stack>
          ))}
          {addingNote ? <CircularProgress size={14} /> : null}
        </Stack>
        <Piano
          width="100%"
          height="auto"
          keyColours={soundingColours}
          onKeyPress={pressKeyboardKey}
          keyTitle={(row) => {
            const sounding = soundingNow.find((note) => note.row === row);
            if (!sounding) {
              return `${noteNameAt(row)} \u2014 click to add it to the ${
                addHand === "left" ? "left" : "right"
              } hand here.`;
            }
            const hand = sounding.hand === "left" ? "left" : "right";
            // A held key is about a notehead somewhere else on the page, and the tooltip is the
            // only place that can say so before the reader presses it.
            return sounding.onsetFrame === playheadFrame
              ? `${noteNameAt(row)} \u2014 ${hand} hand, struck here. Click to take it off the page.`
              : `${noteNameAt(row)} \u2014 ${hand} hand, still sounding from ${formatSeconds((sounding.onsetFrame * frameMs) / 1000)}. Click to take that note off the page.`;
          }}
          ariaLabel="Keys sounding under the playhead"
        />
      </Stack>
    </Toolbox>
  );
}

export function DecorationToolbox({
  open,
  onlyNote,
  onClose,
  graceHere,
  clearGrace,
  putGrace,
  noteNameAt,
}: {
  open: boolean;
  onlyNote: string | null;
  onClose: () => void;
  graceHere: GraceNote | null;
  clearGrace: () => void;
  putGrace: (noteKey: string, row: number) => void;
  noteNameAt: (row: number) => string;
}) {
  return (
    <Toolbox
      open={open}
      title="Piano Edit"
      subtitle={
        onlyNote
          ? `The decoration played just before ${noteNameAt(rowOf(onlyNote))}`
          : undefined
      }
      initialPosition={{ x: 24, y: Math.max(80, window.innerHeight - 300) }}
      onClose={onClose}
      width={760}
    >
      {onlyNote ? (
        <Stack spacing={1}>
          <Stack
            direction="row"
            spacing={1.5}
            sx={{ alignItems: "center", flexWrap: "wrap", rowGap: 1 }}
          >
            <Stack direction="row" spacing={0.5} sx={{ alignItems: "center" }}>
              <Box
                sx={{
                  width: 12,
                  height: 12,
                  borderRadius: 0.5,
                  bgcolor: PRINCIPAL_COLOUR,
                }}
              />
              <Typography variant="caption" color="text.secondary">
                {noteNameAt(rowOf(onlyNote))} — the note it leans on
              </Typography>
            </Stack>
            <Stack direction="row" spacing={0.5} sx={{ alignItems: "center" }}>
              <Box
                sx={{
                  width: 12,
                  height: 12,
                  borderRadius: 0.5,
                  bgcolor: DECORATION_COLOUR,
                }}
              />
              <Typography variant="caption" color="text.secondary">
                {graceHere
                  ? `${noteNameAt(graceHere.row)} — the decoration`
                  : "Click a key to choose the decoration"}
              </Typography>
            </Stack>
            {graceHere ? (
              <IconAction
                title="Remove the decoration"
                icon={<DeleteOutlineIcon fontSize="small" />}
                danger
                onClick={clearGrace}
              />
            ) : null}
          </Stack>
          <Piano
            width="100%"
            height="auto"
            keyColours={{
              [rowOf(onlyNote)]: PRINCIPAL_COLOUR,
              ...(graceHere ? { [graceHere.row]: DECORATION_COLOUR } : {}),
            }}
            onKeyPress={(row) => putGrace(onlyNote, row)}
            keyTitle={(row) => `${noteNameAt(row)} as the decoration`}
            ariaLabel="Choose the decoration note"
          />
        </Stack>
      ) : null}
    </Toolbox>
  );
}
