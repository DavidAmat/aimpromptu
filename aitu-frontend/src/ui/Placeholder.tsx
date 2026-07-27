/**
 * Marker for a page whose real content arrives in a later epic. Keeps the
 * navigation shell honest: every route renders something that says who owns it.
 */

import Alert from "@mui/material/Alert";
import AlertTitle from "@mui/material/AlertTitle";
import Typography from "@mui/material/Typography";

export interface PlaceholderProps {
  /** e.g. "Epic 7 (Matrix tab)". */
  epic: string;
  /** One line on what this page will do. */
  what: string;
}

export function Placeholder({ epic, what }: PlaceholderProps) {
  return (
    <Alert severity="info" variant="outlined">
      <AlertTitle>Coming in {epic}</AlertTitle>
      <Typography variant="body2">{what}</Typography>
    </Alert>
  );
}

export default Placeholder;
