/**
 * What you can do with the notes you have picked.
 *
 * A floating `ToolboxDialog`, the same panel the sheet opens on a selected note,
 * for the same reason: the reader is looking at the notes it is about, so it must
 * not cover them and must not block the page behind it.
 *
 * There is one action and it has two directions. Taking a note off the recording
 * is not a view filter — it is written onto the note event, so the gap plot and
 * the sheet stop counting it too — and that is worth saying on the panel, because
 * it is a bigger thing than "hide" would suggest. Putting it back is the same
 * button pointing the other way, which is why a mixed selection offers both.
 */

import Alert from "@mui/material/Alert";
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
  busy: boolean;
  error: string | null;
  onRemove: () => void;
  onRestore: () => void;
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
  busy,
  error,
  onRemove,
  onRestore,
  onClose,
}: NoteSelectionToolboxProps) {
  const open = selected.length > 0;
  const present = selected.filter((note) => !note.removed);
  const absent = selected.filter((note) => note.removed);

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
          Taking a note off the recording removes it from the sheet and from the gaps the
          rhythm is measured from, not just from this view. It can be put back.
        </Typography>

        {error ? <Alert severity="error">{error}</Alert> : null}

        <Stack direction="row" spacing={1}>
          <Button
            variant="contained"
            color="error"
            size="small"
            startIcon={<DeleteOutlinedIcon />}
            disabled={busy || present.length === 0}
            onClick={onRemove}
          >
            Delete {present.length > 1 ? `${present.length} notes` : "note"}
          </Button>
          {absent.length > 0 ? (
            <Button
              variant="outlined"
              size="small"
              startIcon={<RestoreIcon />}
              disabled={busy}
              onClick={onRestore}
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
