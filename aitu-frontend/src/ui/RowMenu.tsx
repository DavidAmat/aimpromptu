/**
 * The `⋯` menu of a row or a page: the secondary actions, out of the way until asked for
 * (plan section 6.2).
 */

import { useState } from "react";
import ListItemIcon from "@mui/material/ListItemIcon";
import ListItemText from "@mui/material/ListItemText";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import MoreHorizIcon from "@mui/icons-material/MoreHoriz";
import type { ReactNode } from "react";
import IconAction from "./IconAction";

export interface RowMenuItem {
  label: string;
  icon?: ReactNode;
  onClick: () => void;
  danger?: boolean;
  disabled?: boolean;
}

export interface RowMenuProps {
  items: readonly RowMenuItem[];
  /** The tooltip of the `⋯` button. */
  title?: string;
  /**
   * Give the focus back to the `⋯` button when the menu closes (the default). Off for a menu whose
   * item opens a field in place (Rename), which must keep the focus.
   */
  restoreFocus?: boolean;
}

export function RowMenu({ items, title = "More actions", restoreFocus = true }: RowMenuProps) {
  const [anchor, setAnchor] = useState<HTMLElement | null>(null);
  return (
    <>
      <IconAction
        title={title}
        icon={<MoreHorizIcon fontSize="small" />}
        onClick={(event) => {
          event.stopPropagation();
          setAnchor(event.currentTarget);
        }}
      />
      <Menu
        anchorEl={anchor}
        open={anchor !== null}
        onClose={() => setAnchor(null)}
        onClick={(event) => event.stopPropagation()}
        disableRestoreFocus={!restoreFocus}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
        transformOrigin={{ vertical: "top", horizontal: "right" }}
      >
        {items.map((item) => (
          <MenuItem
            key={item.label}
            disabled={item.disabled}
            onClick={() => {
              setAnchor(null);
              item.onClick();
            }}
            sx={item.danger ? { color: "error.main" } : undefined}
          >
            {item.icon ? <ListItemIcon sx={item.danger ? { color: "error.main" } : undefined}>{item.icon}</ListItemIcon> : null}
            <ListItemText>{item.label}</ListItemText>
          </MenuItem>
        ))}
      </Menu>
    </>
  );
}

export default RowMenu;
