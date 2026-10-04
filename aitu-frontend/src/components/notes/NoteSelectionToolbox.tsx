/**
 * What you can do with the notes you have picked on Notes Falling.
 *
 * A floating `ToolboxDialog`, the same panel the sheet opens on a selected note,
 * for the same reason: the reader is looking at the notes it is about, so it must
 * not cover them and must not block the page behind it.
 *
 * Its title names the note in Spanish (`Do - 5`), or counts the notes. The panel
 * holds only buttons: **Delete** marks the notes to take off the recording, and
 * **Put back** marks them to return. Neither writes: the floating **Save** bar
 * commits, because a note taken off renames its neighbour's printed length.
 *
 * The hand buttons and the walk through the notes without a hand lived here for
 * the old Piano Roll; they moved to the Hands tab of the flow page with it
 * (implementation 08, Q-4).
 */

import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import DeleteOutlinedIcon from "@mui/icons-material/DeleteOutlined";
import RestoreIcon from "@mui/icons-material/Restore";
import { ToolboxDialog } from "../common/ToolboxDialog";
import { spanishKeyName } from "../../music/noteNames";
import type { PlayedNote } from "../../playback/playedNotes";

interface NoteSelectionToolboxProps {
  selected: PlayedNote[];
  /** How each selected note currently reads, staged decisions included. */
  isRemoved: (note: PlayedNote) => boolean;
  onStageRemove: () => void;
  onStageRestore: () => void;
  onClose: () => void;
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
  const single = selected.length === 1;

  return (
    <ToolboxDialog
      open={open}
      title={single ? spanishKeyName(selected[0]!.midiNote) : `${selected.length} notes`}
      // Top right, clear of the tabs and the transport — both of which a reader
      // still needs while a selection is up. It can be dragged anywhere from there.
      initialPosition={{ x: Math.max(8, window.innerWidth - 392), y: 88 }}
      onClose={onClose}
    >
      <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap", rowGap: 1 }}>
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
          <Button variant="outlined" size="small" startIcon={<RestoreIcon />} onClick={onStageRestore}>
            Put {absent.length > 1 ? `${absent.length} back` : "it back"}
          </Button>
        ) : null}
      </Stack>
    </ToolboxDialog>
  );
}

export default NoteSelectionToolbox;
