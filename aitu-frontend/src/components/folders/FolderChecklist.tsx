/**
 * The folders of one tree with a checkbox each, indented under their parent (implementation 04-3, Phase 1): an item
 * can be in several folders, so each folder is ticked on its own. Used by the "Folders…" dialog of a row and by the
 * info dialog.
 */

import { useState } from "react";
import Box from "@mui/material/Box";
import Checkbox from "@mui/material/Checkbox";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import FormControlLabel from "@mui/material/FormControlLabel";
import Typography from "@mui/material/Typography";
import type { FolderRow } from "../../api";
import { PillButton } from "../../ui";
import { childrenOf } from "./folderTree";

export function FolderChecklist({
  folders,
  value,
  onChange,
  disabled,
}: {
  folders: readonly FolderRow[];
  value: ReadonlySet<number>;
  onChange: (next: Set<number>) => void;
  disabled?: boolean;
}) {
  if (folders.length === 0) {
    return (
      <Typography color="text.secondary" sx={{ fontSize: 14 }} data-testid="folder-checklist">
        No folders yet
      </Typography>
    );
  }
  const children = childrenOf(folders);
  const lines: { folder: FolderRow; depth: number }[] = [];
  const walk = (parent: number | null, depth: number) => {
    for (const folder of children.get(parent) ?? []) {
      lines.push({ folder, depth });
      walk(folder.id, depth + 1);
    }
  };
  walk(null, 0);
  return (
    <Box role="group" aria-label="Folders" data-testid="folder-checklist">
      {lines.map(({ folder, depth }) => (
        <Box key={folder.id} sx={{ pl: depth * 3 }}>
          <FormControlLabel
            disabled={disabled}
            control={
              <Checkbox
                size="small"
                checked={value.has(folder.id)}
                onChange={() => {
                  const next = new Set(value);
                  if (next.has(folder.id)) next.delete(folder.id);
                  else next.add(folder.id);
                  onChange(next);
                }}
              />
            }
            label={folder.name}
            slotProps={{ typography: { sx: { fontSize: 14 } } }}
          />
        </Box>
      ))}
    </Box>
  );
}

/** "Folders…" of a row's `⋯` menu: the folders the item is in. */
export function FoldersDialog({
  title,
  folders,
  initial,
  busy,
  error,
  onCancel,
  onSave,
}: {
  title: string;
  folders: readonly FolderRow[];
  initial: readonly number[];
  busy: boolean;
  error: string | null;
  onCancel: () => void;
  onSave: (folders: number[]) => void;
}) {
  const [value, setValue] = useState<Set<number>>(() => new Set(initial));
  const changed = value.size !== initial.length || initial.some((one) => !value.has(one));
  return (
    <Dialog open onClose={busy ? undefined : onCancel} maxWidth="xs" fullWidth>
      <DialogTitle sx={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{title}</DialogTitle>
      <DialogContent>
        <FolderChecklist folders={folders} value={value} onChange={setValue} disabled={busy} />
        {error ? (
          <Typography color="error" sx={{ mt: 1, fontSize: 14 }}>
            {error}
          </Typography>
        ) : null}
      </DialogContent>
      <DialogActions>
        <PillButton kind="quiet" onClick={onCancel} disabled={busy}>
          Cancel
        </PillButton>
        <PillButton kind="primary" onClick={() => onSave([...value])} disabled={!changed} busy={busy}>
          Save
        </PillButton>
      </DialogActions>
    </Dialog>
  );
}
