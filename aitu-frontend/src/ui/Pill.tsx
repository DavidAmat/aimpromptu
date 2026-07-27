/**
 * Small selectable chip. Used for the matrix processing-step pills (Epic 7)
 * and any other one-of-N toggle, so those never restyle a raw MUI Chip.
 */

import Chip from "@mui/material/Chip";
import { alpha } from "@mui/material/styles";

export interface PillProps {
  label: string;
  selected?: boolean;
  /** Accent color; falls back to the theme primary. Pass a `palette.ts` value. */
  color?: string;
  disabled?: boolean;
  title?: string;
  onClick?: () => void;
}

export function Pill({ label, selected, color, disabled, title, onClick }: PillProps) {
  return (
    <Chip
      label={label}
      title={title}
      size="small"
      disabled={disabled}
      onClick={onClick}
      variant={selected ? "filled" : "outlined"}
      sx={(t) => {
        const accent = color ?? t.palette.primary.main;
        return {
          fontWeight: 600,
          borderColor: accent,
          color: selected ? t.palette.getContrastText(accent) : accent,
          backgroundColor: selected ? accent : "transparent",
          "&:hover": {
            backgroundColor: selected ? accent : alpha(accent, 0.14),
          },
        };
      }}
    />
  );
}

export default Pill;
