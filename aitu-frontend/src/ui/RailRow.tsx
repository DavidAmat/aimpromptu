/**
 * A row of a side panel that lists things in order (implementation 02): the takes of a passage
 * (Phase 9), the passages of From other projects and the parts of a project (Phase 10). A click
 * shows that one; the row on show is shaded.
 *
 * A row can also be dragged to another place by its handle (`drag`, from `useRowDrag`), carry a
 * `⋯` menu, a bin, and something at its start (a number).
 */

import type { DragEvent, ReactNode } from "react";
import Box from "@mui/material/Box";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutlineOutlined";
import DragIndicatorIcon from "@mui/icons-material/DragIndicator";
import { IconAction } from "./IconAction";
import { RowMenu, type RowMenuItem } from "./RowMenu";
import { ui } from "./tokens";

/** The drag of one row, from `useRowDrag`. */
export interface RowDrag {
  /** On the row: where a dragged row can be dropped. */
  row: {
    onDragOver: (event: DragEvent) => void;
    onDrop: (event: DragEvent) => void;
  };
  /** On the handle. */
  handle: {
    draggable: boolean;
    onDragStart: (event: DragEvent) => void;
    onDragEnd: () => void;
  };
  /** This row is being dragged; a row dragged over it lands above or below it. */
  dragging: boolean;
  dropMark: "above" | "below" | null;
}

export interface RailRowProps {
  label: string;
  detail?: string;
  selected: boolean;
  onClick: () => void;
  onDelete?: () => void;
  menu?: readonly RowMenuItem[];
  /** Before the label: a number, an icon. */
  leading?: ReactNode;
  drag?: RowDrag;
  testId?: string;
}

export function RailRow({ label, detail, selected, onClick, onDelete, menu, leading, drag, testId }: RailRowProps) {
  return (
    <Stack
      direction="row"
      {...drag?.row}
      sx={{
        alignItems: "center",
        borderRadius: 2,
        bgcolor: selected ? "action.selected" : "transparent",
        opacity: drag?.dragging ? 0.4 : 1,
        boxShadow: drag?.dropMark ? `inset 0 ${drag.dropMark === "below" ? -2 : 2}px 0 ${ui.text}` : "none",
        "&:hover": { bgcolor: selected ? "action.selected" : "action.hover" },
      }}
      data-testid={testId}
      data-selected={selected ? "true" : "false"}
    >
      {drag ? (
        <Box
          {...drag.handle}
          title={drag.handle.draggable ? "Drag to put it in another place" : undefined}
          aria-hidden
          sx={{
            display: "flex",
            pl: 0.5,
            color: drag.handle.draggable ? "text.secondary" : "text.disabled",
            cursor: drag.handle.draggable ? "grab" : "default",
          }}
        >
          <DragIndicatorIcon fontSize="small" />
        </Box>
      ) : null}
      {leading ? (
        <Box sx={{ pl: drag ? 0.5 : 1.5, color: "text.secondary", fontVariantNumeric: "tabular-nums", fontSize: 13 }}>
          {leading}
        </Box>
      ) : null}
      <Box
        component="button"
        type="button"
        onClick={onClick}
        aria-current={selected ? "true" : undefined}
        sx={{
          all: "unset",
          cursor: "pointer",
          flex: 1,
          minWidth: 0,
          px: drag || leading ? 1 : 1.5,
          py: 1,
          "&:focus-visible": { outline: 2, outlineColor: "primary.main", borderRadius: 2 },
        }}
      >
        <Typography variant="body2" sx={{ fontWeight: selected ? 600 : 500 }} noWrap title={label}>
          {label}
        </Typography>
        {detail ? (
          <Typography variant="caption" color="text.secondary" noWrap component="div">
            {detail}
          </Typography>
        ) : null}
      </Box>
      {onDelete ? (
        <IconAction title={`Delete ${label}`} icon={<DeleteOutlineIcon fontSize="small" />} onClick={onDelete} />
      ) : null}
      {menu && menu.length > 0 ? <RowMenu title={`${label}: more actions`} items={menu} /> : null}
    </Stack>
  );
}
