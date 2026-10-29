/**
 * One row of a list: a title, its meta (a date, a count), its status, and the `⋯` menu of its
 * secondary actions (plan section 7.4). Flat, with a hover colour; the whole row opens the thing.
 *
 * The title is truncated with the full value on hover, so a 200-character title never sets the
 * height of the row (guidelines 5.3). Meta and status have fixed widths, so they line up from one
 * row to the next.
 */

import type { HTMLAttributes, ReactNode } from "react";
import Box from "@mui/material/Box";
import ButtonBase from "@mui/material/ButtonBase";
import Typography from "@mui/material/Typography";
import { radius } from "./tokens";
import RowMenu, { type RowMenuItem } from "./RowMenu";

export interface ListRowProps {
  title: string;
  /** Before the title: an icon or a small picture. */
  leading?: ReactNode;
  /** A short state ("Sheet", "Notes"), in its own column. */
  status?: ReactNode;
  /** A date or a count, right-aligned in its own column. */
  meta?: ReactNode;
  menu?: readonly RowMenuItem[];
  onOpen?: () => void;
  selected?: boolean;
  /** Steps of indentation before the row's content (the Folders view: one step per level of folder). */
  indent?: number;
  /** Props of the row's box: drag and drop in the Folders view (implementation 04-3). */
  rowProps?: HTMLAttributes<HTMLDivElement> & { "data-drop-over"?: string };
  "data-testid"?: string;
}

/** One step of indentation, in px: about the width of the disclosure triangle and the folder icon. */
export const INDENT_STEP = 28;

export function ListRow({ title, leading, status, meta, menu, onOpen, selected, indent = 0, rowProps, "data-testid": testId }: ListRowProps) {
  return (
    <Box
      {...rowProps}
      data-testid={testId}
      sx={(theme) => ({
        display: "flex",
        alignItems: "center",
        gap: 1,
        pr: 0.5,
        borderRadius: `${radius.row}px`,
        backgroundColor: selected ? (theme.vars ?? theme).palette.action.selected : "transparent",
        "&:hover": { backgroundColor: (theme.vars ?? theme).palette.action.hover },
        // A folder a dragged row is over (the Folders view).
        "&[data-drop-over]": { outline: `2px solid ${(theme.vars ?? theme).palette.primary.main}`, outlineOffset: -2 },
      })}
    >
      <ButtonBase
        onClick={onOpen}
        focusRipple
        sx={{
          flex: 1,
          minWidth: 0,
          display: "flex",
          alignItems: "center",
          gap: 1.5,
          justifyContent: "flex-start",
          textAlign: "left",
          px: { xs: 1, sm: 1.5 },
          ...(indent > 0 ? { pl: { xs: `${8 + indent * INDENT_STEP}px`, sm: `${12 + indent * INDENT_STEP}px` } } : {}),
          py: 1.25,
          borderRadius: `${radius.row}px`,
        }}
      >
        {leading}
        <Typography noWrap title={title} sx={{ flex: 1, minWidth: 0, fontWeight: 500 }}>
          {title}
        </Typography>
        <Box sx={{ width: 96, flexShrink: 0, color: "text.secondary", display: { xs: "none", sm: "block" } }}>
          {typeof status === "string" ? <Typography variant="body2" color="text.secondary">{status}</Typography> : status}
        </Box>
        <Typography
          variant="body2"
          color="text.secondary"
          noWrap
          sx={{ width: { xs: 76, sm: 112 }, flexShrink: 0, textAlign: "right", fontVariantNumeric: "tabular-nums" }}
        >
          {meta}
        </Typography>
      </ButtonBase>
      {menu && menu.length > 0 ? <RowMenu items={menu} /> : <Box sx={{ width: 34 }} />}
    </Box>
  );
}

export default ListRow;
