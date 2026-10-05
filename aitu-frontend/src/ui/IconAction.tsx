/**
 * An icon button with its tooltip: the way every icon action of the app is drawn (plan section 7.3).
 *
 * The tooltip says in a few words what the button does, and the shortcut when there is one. It is
 * also the button's accessible name, so a screen reader says the same words. A disabled button
 * still shows its tooltip (it is wrapped in a span, because a disabled element receives no pointer
 * events), so the reader can learn why it is disabled when `disabledTitle` says so.
 */

import type { MouseEvent, ReactNode } from "react";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";

export interface IconActionProps {
  /** What the button does, in a few words: the tooltip and the accessible name. */
  title: string;
  icon: ReactNode;
  onClick?: (event: MouseEvent<HTMLButtonElement>) => void;
  disabled?: boolean;
  /** The tooltip while disabled, when it can say why. */
  disabledTitle?: string;
  /** A key or a key combination, shown after the title: "Undo (⌘Z)". */
  shortcut?: string;
  /** Drawn pressed: a toggle that is on. */
  active?: boolean;
  /** Only for a destructive action. */
  danger?: boolean;
  size?: "small" | "medium";
  placement?: "top" | "bottom" | "left" | "right";
  "data-testid"?: string;
}

export function IconAction({
  title,
  icon,
  onClick,
  disabled,
  disabledTitle,
  shortcut,
  active,
  danger,
  size = "small",
  placement = "bottom",
  "data-testid": testId,
}: IconActionProps) {
  const label = shortcut ? `${title} (${shortcut})` : title;
  return (
    <Tooltip title={disabled && disabledTitle ? disabledTitle : label} placement={placement} describeChild>
      <span style={{ display: "inline-flex" }}>
        <IconButton
          size={size}
          onClick={onClick}
          disabled={disabled}
          aria-label={title}
          aria-pressed={active === undefined ? undefined : active}
          data-testid={testId}
          sx={(theme) => ({
            ...(active ? { backgroundColor: (theme.vars ?? theme).palette.action.selected, color: "text.primary" } : {}),
            ...(danger ? { color: "error.main" } : {}),
          })}
        >
          {icon}
        </IconButton>
      </span>
    </Tooltip>
  );
}

export default IconAction;
