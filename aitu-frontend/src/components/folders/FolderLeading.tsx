/** Before a folder's name in the Folders view: the disclosure triangle (open or closed) and the folder icon. */

import Box from "@mui/material/Box";
import ArrowDropDownIcon from "@mui/icons-material/ArrowDropDown";
import ArrowRightIcon from "@mui/icons-material/ArrowRight";
import FolderIcon from "@mui/icons-material/FolderOutlined";
import FolderOpenIcon from "@mui/icons-material/FolderOpenOutlined";

export function FolderLeading({ open }: { open: boolean }) {
  const Triangle = open ? ArrowDropDownIcon : ArrowRightIcon;
  const Icon = open ? FolderOpenIcon : FolderIcon;
  return (
    <Box component="span" sx={{ display: "inline-flex", alignItems: "center", flexShrink: 0, color: "text.secondary", ml: -0.75 }}>
      <Triangle fontSize="small" />
      <Icon sx={{ fontSize: 18 }} />
    </Box>
  );
}

/**
 * Before an item's mark in the Folders view: the room of a folder's triangle, left empty, so the item's mark is
 * under its sibling folders' icons, as in the Finder's list view.
 */
export function TriangleRoom() {
  return <Box component="span" aria-hidden sx={{ width: 14, flexShrink: 0 }} />;
}
