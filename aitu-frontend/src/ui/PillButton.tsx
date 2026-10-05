/**
 * A button of the app: fully rounded, 36 px high (32 in toolboxes), plan section 7.3.
 *
 * `primary` is the one black button of a screen, `secondary` is white with a grey border, `quiet`
 * has no border. The text is a verb or a destination ("Transcribe", "New project"), never "OK".
 */

import type { ReactNode } from "react";
import Button, { type ButtonProps } from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";

export interface PillButtonProps extends Omit<ButtonProps, "variant" | "color"> {
  kind?: "primary" | "secondary" | "quiet" | "danger";
  /** Shows a small spinner in place of the start icon, and disables the button. */
  busy?: boolean;
  startIcon?: ReactNode;
}

const VARIANT = { primary: "contained", secondary: "outlined", quiet: "text", danger: "contained" } as const;

export function PillButton({ kind = "secondary", busy, startIcon, disabled, children, ...rest }: PillButtonProps) {
  return (
    <Button
      {...rest}
      variant={VARIANT[kind]}
      color={kind === "danger" ? "error" : "primary"}
      disabled={disabled || busy}
      startIcon={busy ? <CircularProgress size={14} color="inherit" /> : startIcon}
    >
      {children}
    </Button>
  );
}

export default PillButton;
