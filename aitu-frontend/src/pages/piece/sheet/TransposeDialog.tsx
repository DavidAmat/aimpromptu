/**
 * The one dialog both transpositions use (plan section 11.4): the piano sheet as it would be, the
 * counts of what the change removes, and **Transpose** or **Cancel**. Nothing is written until
 * **Transpose** is pressed, so a result the reader does not like costs nothing.
 */

import type { ComponentProps } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import TimeScoreView from "../../../components/time/TimeScoreView";
import { PillButton } from "../../../ui";

export type PreviewSheet = Omit<ComponentProps<typeof TimeScoreView>, "readOnly">;

export function TransposeDialog({
  open,
  title,
  facts,
  sheet,
  loading,
  error,
  confirming,
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title: string;
  /** One short line each: what moves, and what is removed. */
  facts: readonly string[];
  /** The sheet as it would be, or `null` while it is being written. */
  sheet: PreviewSheet | null;
  loading: boolean;
  error: string | null;
  confirming: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <Dialog
      open={open}
      onClose={confirming ? undefined : onCancel}
      maxWidth="lg"
      fullWidth
      data-transpose-dialog
    >
      <DialogTitle>{title}</DialogTitle>
      <DialogContent>
        <Stack spacing={1.5}>
          {facts.map((fact) => (
            <Typography key={fact} variant="body2" data-transpose-fact>
              {fact}
            </Typography>
          ))}
          {error ? <Alert severity="error">{error}</Alert> : null}
          {/* The space of the sheet is kept while it is written, so nothing jumps when it comes. */}
          <Box
            sx={{
              height: "55vh",
              overflow: "auto",
              border: 1,
              borderColor: "divider",
              borderRadius: 1,
              bgcolor: "#fff",
            }}
            data-transpose-sheet
          >
            {loading || !sheet ? (
              <Box sx={{ display: "grid", placeItems: "center", height: "100%" }}>
                {loading ? <CircularProgress size={22} /> : null}
              </Box>
            ) : (
              <TimeScoreView {...sheet} readOnly showFrameLabels={false} />
            )}
          </Box>
        </Stack>
      </DialogContent>
      <DialogActions>
        <PillButton kind="quiet" onClick={onCancel} disabled={confirming}>
          Cancel
        </PillButton>
        <PillButton
          kind="primary"
          onClick={onConfirm}
          busy={confirming}
          disabled={loading || !sheet}
          data-transpose-confirm
        >
          Transpose
        </PillButton>
      </DialogActions>
    </Dialog>
  );
}

export default TransposeDialog;
