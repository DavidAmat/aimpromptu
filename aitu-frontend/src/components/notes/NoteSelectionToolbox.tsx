/**
 * What you can do with the notes you have picked.
 *
 * A floating `ToolboxDialog`, the same panel the sheet opens on a selected note,
 * for the same reason: the reader is looking at the notes it is about, so it must
 * not cover them and must not block the page behind it.
 *
 * There is one action and it has two directions. Neither writes anything. Taking a
 * note off the recording removes it from the matrix the piece is drawn from — the
 * printed length of a note is the gap to the next onset, so the note's neighbour
 * is renamed by it — and a change of that size is staged and reviewed, not applied
 * on a click. The panel marks; the floating **Save** bar commits.
 */

import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import DeleteOutlinedIcon from "@mui/icons-material/DeleteOutlined";
import RestoreIcon from "@mui/icons-material/Restore";
import { ToolboxDialog } from "../common/ToolboxDialog";
import { formatTime } from "../../audio/time";
import { noteName } from "../../music/noteNames";
import type { PlayedNote } from "../../playback/playedNotes";

interface NoteSelectionToolboxProps {
  selected: PlayedNote[];
  /** How each selected note currently reads, staged decisions included. */
  isRemoved: (note: PlayedNote) => boolean;
  onStageRemove: () => void;
  onStageRestore: () => void;
  onClose: () => void;
}

function describe(selected: PlayedNote[]): string {
  if (selected.length === 1) {
    const note = selected[0]!;
    return `${noteName(note.midiNote)} at ${formatTime(note.startSeconds)}, ${(
      (note.endSeconds - note.startSeconds) *
      1000
    ).toFixed(0)} ms long`;
  }
  const from = Math.min(...selected.map((note) => note.startSeconds));
  const to = Math.max(...selected.map((note) => note.endSeconds));
  return `${selected.length} notes, ${formatTime(from)} to ${formatTime(to)}`;
}

export function NoteSelectionToolbox({
  selected,
  isRemoved,
  onStageRemove,
  onStageRestore,
  onClose,
}: NoteSelectionToolboxProps) {
  const open = selected.length > 0;
  const present = selected.filter((note) => !isRemoved(note));
  const absent = selected.filter((note) => isRemoved(note));

  return (
    <ToolboxDialog
      open={open}
      title={selected.length === 1 ? "This note" : `${selected.length} notes`}
      subtitle={open ? describe(selected) : undefined}
      // Top right, clear of the tabs and the transport — both of which a reader
      // still needs while a selection is up. It can be dragged anywhere from there.
      initialPosition={{ x: Math.max(8, window.innerWidth - 392), y: 88 }}
      onClose={onClose}
    >
      <Stack spacing={1.5}>
        <Typography variant="body2" color="text.secondary">
          Taking a note off removes it from the piano matrix this piece is drawn from, so it
          leaves the sheet and the gaps the rhythm is measured from as well. Marked here, kept
          by <strong>Save</strong> on the floating bar, and reversible either way.
        </Typography>

        <Stack direction="row" spacing={1}>
          <Button
            variant="contained"
            color="error"
            size="small"
            startIcon={<DeleteOutlinedIcon />}
            disabled={present.length === 0}
            onClick={onStageRemove}
          >
            Delete {present.length > 1 ? `${present.length} notes` : "note"}
          </Button>
          {absent.length > 0 ? (
            <Button
              variant="outlined"
              size="small"
              startIcon={<RestoreIcon />}
              onClick={onStageRestore}
            >
              Put {absent.length > 1 ? `${absent.length} back` : "it back"}
            </Button>
          ) : null}
        </Stack>

        <Typography variant="caption" color="text.secondary">
          Click a note to pick it, ⌘-click to add one, or drag a band over several.
        </Typography>
      </Stack>
    </ToolboxDialog>
  );
}

export default NoteSelectionToolbox;
