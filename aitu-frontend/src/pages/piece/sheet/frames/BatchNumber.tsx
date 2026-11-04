/** The number of a batch in its colour, as the sheet draws it: in the dialog's list and the panels of a run. */

import Box from "@mui/material/Box";
import type { ReactNode } from "react";

export function BatchNumber({ colour, size = 26, children }: { colour: string; size?: number; children: ReactNode }) {
  return (
    <Box
      sx={{
        width: size,
        height: size,
        borderRadius: 1,
        border: `2px solid ${colour}`,
        bgcolor: `${colour}1f`,
        color: colour,
        fontWeight: 700,
        fontSize: size / 2,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        flexShrink: 0,
      }}
    >
      {children}
    </Box>
  );
}

export default BatchNumber;
