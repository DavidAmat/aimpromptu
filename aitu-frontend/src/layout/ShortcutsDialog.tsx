/** The keyboard shortcuts of the app, from the user menu. */

import Box from "@mui/material/Box";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Typography from "@mui/material/Typography";
import CloseIcon from "@mui/icons-material/Close";
import { IconAction } from "../ui";

const SHORTCUTS: readonly (readonly [string, string])[] = [
  ["⌘K", "Search"],
  ["Space", "Play or pause"],
  ["⌘Z", "Undo"],
  ["⇧⌘Z", "Redo"],
  ["Delete", "Delete the selection"],
  ["R / L", "Give the selected notes to the right or the left hand"],
  ["Arrows", "Move the selected notes"],
  ["Esc", "Clear the selection"],
];

export function ShortcutsDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  return (
    <Dialog open={open} onClose={onClose} maxWidth="xs" fullWidth>
      <DialogTitle sx={{ display: "flex", alignItems: "center", pr: 1.5 }}>
        <Box sx={{ flex: 1 }}>Keyboard shortcuts</Box>
        <IconAction title="Close" icon={<CloseIcon fontSize="small" />} onClick={onClose} />
      </DialogTitle>
      <DialogContent>
        <Box component="dl" sx={{ display: "grid", gridTemplateColumns: "88px 1fr", rowGap: 1.25, columnGap: 2, m: 0 }}>
          {SHORTCUTS.map(([keys, action]) => (
            <Box key={keys} sx={{ display: "contents" }}>
              <Typography component="dt" sx={{ fontWeight: 600, fontVariantNumeric: "tabular-nums" }}>
                {keys}
              </Typography>
              <Typography component="dd" sx={{ m: 0 }} color="text.secondary">
                {action}
              </Typography>
            </Box>
          ))}
        </Box>
        <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 2 }}>
          On Windows and Linux, Ctrl in place of ⌘.
        </Typography>
      </DialogContent>
    </Dialog>
  );
}

export default ShortcutsDialog;
