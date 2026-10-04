/**
 * The save bar of the flow page: what is unsaved, **Discard** and **Save**.
 *
 * Nothing on the Audio, Notes and Hands tabs is written before the reader presses Save (plan
 * section 7.3). The bar appears as soon as something is unsaved and goes away once it is saved or
 * discarded. It is the same floating bar the piano sheet uses, so it can be dragged out of the way.
 */

import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Typography from "@mui/material/Typography";
import SaveIcon from "@mui/icons-material/Save";
import FloatingBar from "../common/FloatingBar";

export interface SaveBarProps {
  /** What is unsaved, in words; `null` hides the bar. */
  summary: string | null;
  saving: boolean;
  onSave: () => void;
  onDiscard: () => void;
}

export function SaveBar({ summary, saving, onSave, onDiscard }: SaveBarProps) {
  return (
    <FloatingBar open={summary !== null} label="save bar">
      <Typography variant="body2" sx={{ fontWeight: 600, whiteSpace: "nowrap", px: 0.5 }}>
        {summary}
      </Typography>
      <Button size="small" onClick={onDiscard} disabled={saving}>
        Discard
      </Button>
      <Button
        size="small"
        variant="contained"
        startIcon={saving ? <CircularProgress size={14} color="inherit" /> : <SaveIcon />}
        onClick={onSave}
        disabled={saving}
      >
        Save
      </Button>
    </FloatingBar>
  );
}

export default SaveBar;
