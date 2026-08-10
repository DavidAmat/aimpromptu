/**
 * The floating bar that keeps or throws away staged note removals.
 *
 * Same `FloatingBar` the sheet carries its **Save** on, in the same place and with
 * the same manners, because it is the same decision: this view runs wider than the
 * window, and a button pinned under it would mean scrolling away from the notes
 * you are deciding about in order to keep the decision.
 *
 * It appears only when something is staged, and the count is on the button rather
 * than in a sentence beside it — the bar is controls, not prose.
 */

import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import SaveIcon from "@mui/icons-material/SaveOutlined";
import UndoIcon from "@mui/icons-material/UndoOutlined";
import FloatingBar from "../common/FloatingBar";
import { semantic } from "../../ui";

interface PendingRemovalsBarProps {
  removing: number;
  restoring: number;
  saving: boolean;
  /** Flashes on the Save button for a moment after a successful write. */
  saved: boolean;
  onSave: () => void;
  onDiscard: () => void;
}

function summary(removing: number, restoring: number): string {
  const parts: string[] = [];
  if (removing) parts.push(`${removing} off`);
  if (restoring) parts.push(`${restoring} back`);
  return parts.join(" · ");
}

export function PendingRemovalsBar({
  removing,
  restoring,
  saving,
  saved,
  onSave,
  onDiscard,
}: PendingRemovalsBarProps) {
  const total = removing + restoring;
  // The bar stays up for the moment the Save button spends saying "Saved", so the
  // confirmation is not yanked away in the same frame it appears.
  if (total === 0 && !saved) return null;

  return (
    <FloatingBar open label="staged note changes">
      <Typography variant="caption" sx={{ px: 0.5, color: semantic.status.warning }}>
        {summary(removing, restoring)}
      </Typography>
      <Button
        size="small"
        variant="contained"
        color={saved ? "success" : "primary"}
        disabled={saving || total === 0}
        startIcon={saving ? <CircularProgress size={14} /> : <SaveIcon />}
        onClick={onSave}
      >
        {saved ? "Saved" : "Save"}
      </Button>
      <Tooltip title="Put every staged note back the way it was">
        <span>
          <Button size="small" disabled={saving || total === 0} startIcon={<UndoIcon />} onClick={onDiscard}>
            Discard
          </Button>
        </span>
      </Tooltip>
    </FloatingBar>
  );
}

export default PendingRemovalsBar;
