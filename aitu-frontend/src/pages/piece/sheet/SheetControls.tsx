/**
 * The controls of the whole piano sheet: the key signature, the space between lines and notes,
 * the suggestions, and how the page is looked at.
 *
 * Split out of `RhythmPage.tsx` (implementation 02, Phase 2) with no change.
 */

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import MenuItem from "@mui/material/MenuItem";
import Slider from "@mui/material/Slider";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import type { Dispatch, SetStateAction } from "react";
import type { OttavaAnnotation } from "@aimpromptu/grid-notation";
import {
  KEY_LABELS,
  KEY_SIGNATURES,
  type KeySignatureName,
  type TimeScorePayload,
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

export function SheetControls({
  score,
  keySignature,
  setKeySignature,
  lineSpacing,
  setLineSpacing,
  noteSpacing,
  setNoteSpacing,
  keyHint,
  ottavaHint,
  onTakeOttavaHint,
  frameLabelsOn,
  setFrameLabelsOn,
  sheetZoom,
  setSheetZoom,
  dropDecorative,
  setDropDecorative,
  pianoOpen,
  setPianoOpen,
}: {
  score: TimeScorePayload | null;
  keySignature: KeySignatureName;
  setKeySignature: Dispatch<SetStateAction<KeySignatureName>>;
  lineSpacing: number;
  setLineSpacing: Dispatch<SetStateAction<number>>;
  noteSpacing: number;
  setNoteSpacing: Dispatch<SetStateAction<number>>;
  keyHint: { best: KeySignatureName; saved: number } | null;
  ottavaHint: readonly OttavaAnnotation[];
  onTakeOttavaHint: () => void;
  frameLabelsOn: boolean;
  setFrameLabelsOn: Dispatch<SetStateAction<boolean>>;
  sheetZoom: number;
  setSheetZoom: Dispatch<SetStateAction<number>>;
  dropDecorative: boolean;
  setDropDecorative: Dispatch<SetStateAction<boolean>>;
  pianoOpen: boolean;
  setPianoOpen: Dispatch<SetStateAction<boolean>>;
}) {
  return (
    <>
        {/*
          The key signature belongs beside the sheet rather than beside the plot, because it is
          read off the sheet: you change it and look at how many sharps and flats disappear.
        */}
        <Stack
          direction="row"
          spacing={2}
          sx={{ alignItems: "center", flexWrap: "wrap" }}
        >
          <TextField
            select
            size="small"
            label="Key signature"
            value={keySignature}
            onChange={(event) =>
              setKeySignature(event.target.value as KeySignatureName)
            }
            sx={{ minWidth: 200 }}
            helperText="Written on both clefs. It changes spelling only: no note moves."
          >
            {KEY_SIGNATURES.map((name) => (
              <MenuItem key={name} value={name}>
                {KEY_LABELS[name]}
              </MenuItem>
            ))}
          </TextField>
          {/*
            How far apart the lines of the piece are drawn.

            A line here is one pair of pentagrams under a curly bracket, and a long piece wraps
            onto many of them. One fixed gap cannot be right for every piece: most sheets are
            mostly white space at it, and on a sheet with high notes a low note of the left hand
            and a high note of the next line's right hand reach towards each other through it
            until the two runs of ledger lines meet. So the reader sets it, and it is saved with
            the piece — it belongs to this piece the same way the mark size does.

            Beside the key signature because that is where a reader is already standing when
            they look at how the page reads, and because both change the page and neither moves
            a note or touches the recording.
          */}
          <Box sx={{ minWidth: 190 }}>
            <Typography variant="caption" color="text.secondary">
              Space between lines — {Math.round(lineSpacing)} px
            </Typography>
            <Slider
              size="small"
              min={MIN_LINE_SPACING}
              max={MAX_LINE_SPACING}
              step={4}
              marks={[{ value: DEFAULT_LINE_SPACING }]}
              value={lineSpacing}
              onChange={(_, value) => setLineSpacing(value as number)}
              valueLabelDisplay="auto"
              aria-label="Space between the staves of one line and the next"
            />
            <Typography variant="caption" color="text.secondary">
              The white between one pair of staves and the next. At nought
              they sit directly under each other.
            </Typography>
          </Box>
          {/*
            How far apart the notes stand, which is the same question one axis over.

            Each column is as wide as what is drawn in it, so a page of even corcheas comes out
            as tight as the noteheads allow — right for reading a texture, and tighter than a
            player wants when the next thing to happen is a blanca. This opens every note up by
            the same amount and leaves the silences alone: a column where nothing starts is
            already exactly as wide as the time it holds, and widening it would say time had
            passed that did not. A stretch that needs more than the page does is still the
            Spacing pill's job.
          */}
          <Box sx={{ minWidth: 190 }}>
            <Typography variant="caption" color="text.secondary">
              Space between notes — {Math.round(noteSpacing)} px
            </Typography>
            <Slider
              size="small"
              min={MIN_NOTE_SPACING}
              max={MAX_NOTE_SPACING}
              step={2}
              marks={[{ value: DEFAULT_NOTE_SPACING }]}
              value={noteSpacing}
              onChange={(_, value) => setNoteSpacing(value as number)}
              valueLabelDisplay="auto"
              aria-label="Extra space between one note and the next"
            />
            <Typography variant="caption" color="text.secondary">
              Added to every note, and to no silence. Nothing is renamed and
              the recording is untouched.
            </Typography>
          </Box>
          {keyHint ? (
            <Button
              size="small"
              onClick={() => setKeySignature(keyHint.best)}
            >
              Try {KEY_LABELS[keyHint.best]}
              {keyHint.saved > 0
                ? ` (${keyHint.saved} fewer accidentals)`
                : ""}
            </Button>
          ) : (
            <Typography variant="body2" color="text.secondary">
              No other signature would print fewer accidentals than this
              one.
            </Typography>
          )}
          <Chip
            size="small"
            label={`Group high notes under 8va${
              ottavaHint.length ? ` (${ottavaHint.length})` : ""
            }`}
            title="One bracket over every run of three or more chords written three ledger lines or more outside its staff, in either hand. Replaces the brackets on the page; the Octave pill of a stretch edits them."
            variant="outlined"
            disabled={!score || ottavaHint.length === 0}
            onClick={onTakeOttavaHint}
          />
          <Chip
            size="small"
            label="Show frame numbers"
            title="The column numbers over the guides — f0, f100. They are how a mark on this page is addressed; the dashed lines and the stretches you can select stay either way."
            color={frameLabelsOn ? "secondary" : "default"}
            variant={frameLabelsOn ? "filled" : "outlined"}
            onClick={() => setFrameLabelsOn((current) => !current)}
          />
          <Chip
            size="small"
            label={
              sheetZoom === MIN_ZOOM
                ? "Zoom: Command and scroll"
                : `Zoom ${Math.round(sheetZoom * 100)}% — back to normal`
            }
            title={`Hold Command (Control on Windows) and scroll over the sheet to draw it larger, up to ${
              MAX_ZOOM * 100
            }%. It magnifies the page and changes nothing about the music: no column is measured again and the lines wrap exactly where they did.`}
            color={sheetZoom === MIN_ZOOM ? "default" : "secondary"}
            variant={sheetZoom === MIN_ZOOM ? "outlined" : "filled"}
            onClick={() => setSheetZoom(MIN_ZOOM)}
          />
          <Chip
            size="small"
            label="Remove decorative notes"
            title="A sixteenth or shorter right before an eighth or longer is an ornament. Off the page, and the note before it runs on; nothing is written in its place."
            color={dropDecorative ? "secondary" : "default"}
            variant={dropDecorative ? "filled" : "outlined"}
            onClick={() => setDropDecorative((current) => !current)}
          />
          {dropDecorative && score?.decorativeDropped ? (
            <Typography variant="caption" color="text.secondary">
              {score.decorativeDropped} left off
            </Typography>
          ) : null}
          <Chip
            size="small"
            label={pianoOpen ? "Hide piano" : "Show piano"}
            title="A keyboard with the keys sounding under the playhead coloured in."
            color={pianoOpen ? "secondary" : "default"}
            variant={pianoOpen ? "filled" : "outlined"}
            onClick={() => setPianoOpen((current) => !current)}
          />
        </Stack>
    </>
  );
}

export default SheetControls;
