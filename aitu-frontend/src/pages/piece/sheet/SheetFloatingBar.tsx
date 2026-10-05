/**
 * The floating bar of the Sheet step, and the message of a refused save that sits with it.
 *
 * Split out of `RhythmPage.tsx` (implementation 02, Phase 2) with no change.
 */

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Divider from "@mui/material/Divider";
import IconButton from "@mui/material/IconButton";
import Snackbar from "@mui/material/Snackbar";
import Tooltip from "@mui/material/Tooltip";
import DeleteSweepIcon from "@mui/icons-material/DeleteSweepOutlined";
import PauseIcon from "@mui/icons-material/Pause";
import PictureAsPdfIcon from "@mui/icons-material/PictureAsPdfOutlined";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import SaveIcon from "@mui/icons-material/SaveOutlined";
import { FloatingBar } from "../../../ui";

export function SheetFloatingBar({
  playing,
  onTogglePlay,
  canSave,
  saving,
  clearing,
  saveProblem,
  onCloseProblem,
  flash,
  armed,
  onSave,
  onRemoveAll,
  canPrint,
  onPrint,
}: {
  playing: boolean;
  onTogglePlay: () => void;
  canSave: boolean;
  saving: boolean;
  clearing: boolean;
  saveProblem: string | null;
  onCloseProblem: () => void;
  flash: "saved" | "removed" | null;
  armed: boolean;
  onSave: () => void;
  onRemoveAll: () => void;
  canPrint: boolean;
  onPrint: () => void;
}) {
  return (
    <>
        {/*
          A refused save, where the reader is.

          It stays until it is closed rather than fading: this is the one message on the page
          that a reader must not miss, and a save is pressed and then looked away from. The
          backend's own words, so a bound it refused names the field it refused.
        */}
        <Snackbar
          open={saveProblem !== null}
          anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
          onClose={onCloseProblem}
          sx={{ zIndex: 1250 }}
        >
          <Alert
            severity="error"
            variant="filled"
            onClose={onCloseProblem}
            sx={{ maxWidth: 560 }}
          >
            {saveProblem}
          </Alert>
        </Snackbar>
        <FloatingBar open label="sheet buttons">
          <Tooltip
            title={playing ? "Pause the recording" : "Play the recording"}
          >
            <IconButton
              size="small"
              color="primary"
              aria-label={playing ? "Pause" : "Play"}
              onClick={onTogglePlay}
            >
              {playing ? <PauseIcon /> : <PlayArrowIcon />}
            </IconButton>
          </Tooltip>
          <Divider orientation="vertical" flexItem />
          {/*
            A greyed Save used to say nothing about why. It is disabled until a pile of gaps is
            named, because the name is half of what a reading *is* — and a reader looking at a
            drawn sheet has no way of guessing that the plot above it is what the button is
            waiting for. A failed save is the other half: it turns red and says so, because the
            only Save there is lives up here on the bar.
          */}
          <Tooltip
            title={
              !canSave
                ? "Name a pile of gaps on the plot above first: that is what a reading is saved as"
                : saveProblem
                  ? saveProblem
                  : "Keep this reading with the piece"
            }
          >
            <span>
              <Button
                size="small"
                variant="contained"
                color={
                  flash === "saved"
                    ? "success"
                    : saveProblem
                      ? "error"
                      : "primary"
                }
                disabled={!canSave || saving || clearing}
                // Pressing anything else on the bar is an answer to "sure?", and the answer is no.
                onClick={onSave}
                startIcon={
                  saving ? <CircularProgress size={14} /> : <SaveIcon />
                }
              >
                {flash === "saved"
                  ? "Saved"
                  : saveProblem
                    ? "Save failed"
                    : "Save"}
              </Button>
            </span>
          </Tooltip>
          <Tooltip title="Throws away every decision about this piece, on screen and on disk, and puts back the notes taken off the recording. Command-Z cannot take it back.">
          <Button
            size="small"
            color={flash === "removed" ? "success" : "error"}
            variant={armed ? "contained" : "outlined"}
            disabled={saving || clearing}
            onClick={onRemoveAll}
            startIcon={
              clearing ? (
                <CircularProgress size={14} />
              ) : (
                <DeleteSweepIcon />
              )
            }
          >
            {flash === "removed"
              ? "Removed"
              : armed
                ? "Sure? Remove all"
                : "Remove all"}
          </Button>
          </Tooltip>
          <Divider orientation="vertical" flexItem />
          {/*
            The way off the screen. A window is whatever width it happens to be; paper is 210
            millimetres, so the music has to be laid out again before it can be printed, and
            the panel is where that is looked at before it is committed to a file.
          */}
          <Tooltip title="Lay the sheet out on paper and download it">
            <span>
              <Button
                size="small"
                variant="outlined"
                disabled={!canPrint}
                onClick={onPrint}
                startIcon={<PictureAsPdfIcon />}
              >
                PDF
              </Button>
            </span>
          </Tooltip>
        </FloatingBar>
    </>
  );
}

export default SheetFloatingBar;
