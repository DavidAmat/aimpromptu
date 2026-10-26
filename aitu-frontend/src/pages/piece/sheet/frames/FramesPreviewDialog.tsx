/**
 * The preview of a transposition on the new sheet (implementation 03, Phase 8), as on the old sheet: the sheet as it
 * would be, a line for what the change removes, and **Transpose** or **Cancel**. Nothing is written until
 * **Transpose**: the backend drew the preview without storing it.
 */

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import type { SheetPreview } from "../../../../api";
import { PillButton } from "../../../../ui";

export function FramesPreviewDialog({
  open,
  title,
  facts,
  preview,
  error,
  confirming,
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title: string;
  facts: readonly string[];
  /** The sheet as it would be, or `null` while it is drawn. */
  preview: SheetPreview | null;
  error: string | null;
  confirming: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <Dialog open={open} onClose={confirming ? undefined : onCancel} maxWidth="lg" fullWidth data-transpose-dialog>
      <DialogTitle>{title}</DialogTitle>
      <DialogContent>
        <Stack spacing={1.5}>
          {facts.map((fact) => (
            <Typography key={fact} variant="body2" data-transpose-fact>
              {fact}
            </Typography>
          ))}
          {error ? <Alert severity="error">{error}</Alert> : null}
          {/* The space of the sheet is kept while it is drawn, so nothing jumps when it comes. */}
          <Box
            sx={{ height: "55vh", overflow: "auto", border: 1, borderColor: "divider", borderRadius: 1, bgcolor: "#fff" }}
            data-transpose-sheet
          >
            {preview ? (
              <Box
                sx={{ "& svg": { display: "block", width: "100%", height: "auto" } }}
                dangerouslySetInnerHTML={{ __html: preview.svg }}
              />
            ) : (
              <Box sx={{ display: "grid", placeItems: "center", height: "100%" }}>
                {error ? null : <CircularProgress size={22} />}
              </Box>
            )}
          </Box>
        </Stack>
      </DialogContent>
      <DialogActions>
        <PillButton kind="quiet" onClick={onCancel} disabled={confirming}>
          Cancel
        </PillButton>
        <PillButton kind="primary" onClick={onConfirm} busy={confirming} disabled={!preview} data-transpose-confirm>
          Transpose
        </PillButton>
      </DialogActions>
    </Dialog>
  );
}

export default FramesPreviewDialog;
