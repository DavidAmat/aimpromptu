import { useState } from "react";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import MenuItem from "@mui/material/MenuItem";
import TextField from "@mui/material/TextField";
import type { FolderRow } from "../../api";
import { PillButton } from "../../ui";
import { inside, pathOf } from "./folderTree";

/** **Move to…**: the top, or any folder that is not this one or inside it. */
export function MoveFolderDialog({
  folder,
  folders,
  busy,
  error,
  onCancel,
  onMove,
}: {
  folder: FolderRow;
  folders: FolderRow[];
  busy: boolean;
  error: string | null;
  onCancel: () => void;
  onMove: (parentId: number | null) => void;
}) {
  const blocked = inside(folders, folder.id);
  const targets = folders
    .filter((one) => !blocked.has(one.id))
    .map((one) => ({ id: one.id, path: pathOf(folders, one.id) }))
    .sort((a, b) => a.path.localeCompare(b.path, undefined, { sensitivity: "base" }));
  const [target, setTarget] = useState<string>(folder.parentId === null ? "top" : String(folder.parentId));
  const chosen = target === "top" ? null : Number(target);
  return (
    <Dialog open onClose={busy ? undefined : onCancel} maxWidth="xs" fullWidth>
      <DialogTitle>Move “{folder.name}”</DialogTitle>
      <DialogContent>
        <TextField
          select
          fullWidth
          label="To"
          value={target}
          onChange={(event) => setTarget(event.target.value)}
          error={error !== null}
          helperText={error ?? undefined}
          sx={{ mt: 1 }}
          data-testid="move-folder-to"
        >
          <MenuItem value="top">The top</MenuItem>
          {targets.map((one) => (
            <MenuItem key={one.id} value={String(one.id)}>
              {one.path}
            </MenuItem>
          ))}
        </TextField>
      </DialogContent>
      <DialogActions>
        <PillButton kind="quiet" onClick={onCancel} disabled={busy}>
          Cancel
        </PillButton>
        <PillButton kind="primary" onClick={() => onMove(chosen)} disabled={chosen === folder.parentId} busy={busy}>
          Move
        </PillButton>
      </DialogActions>
    </Dialog>
  );
}
