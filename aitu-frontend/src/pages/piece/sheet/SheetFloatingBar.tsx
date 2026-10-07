/**
 * The floating bar of the Sheet step (plan section 11.2), and the two messages that sit with it.
 *
 * Play or pause, undo, redo, the sheet toolbox, Record, Print, **Save**, and a `⋯` with the rest.
 * Save stays a visible button: nothing is written before it, and a dot on it says there are
 * changes it would keep. The bar is draggable and can be hidden (the shared `FloatingBar`).
 *
 * A refused save and a refused hand move appear here rather than under the sheet, because the
 * reader is looking at the bar when they press it and the sheet can be pages long.
 */

import Alert from "@mui/material/Alert";
import Badge from "@mui/material/Badge";
import Divider from "@mui/material/Divider";
import Snackbar from "@mui/material/Snackbar";
import Tooltip from "@mui/material/Tooltip";
import CheckIcon from "@mui/icons-material/Check";
import DeleteSweepIcon from "@mui/icons-material/DeleteSweepOutlined";
import FiberManualRecordIcon from "@mui/icons-material/FiberManualRecordOutlined";
import GraphicEqIcon from "@mui/icons-material/GraphicEqOutlined";
import PauseIcon from "@mui/icons-material/Pause";
import PianoIcon from "@mui/icons-material/PianoOutlined";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import PrintIcon from "@mui/icons-material/PrintOutlined";
import RedoIcon from "@mui/icons-material/RedoOutlined";
import RestoreIcon from "@mui/icons-material/RestoreOutlined";
import TuneIcon from "@mui/icons-material/TuneOutlined";
import UndoIcon from "@mui/icons-material/UndoOutlined";
import { FloatingBar, IconAction, PillButton, RowMenu, type RowMenuItem } from "../../../ui";

export function SheetFloatingBar({
  readOnly = false,
  playing,
  onTogglePlay,
  undo,
  redo,
  toolboxOpen,
  onToolbox,
  onRecord,
  canPrint,
  onPrint,
  canSave,
  unsaved,
  saving,
  flash,
  onSave,
  pianoOpen,
  onPiano,
  onFindTrills,
  hiddenCount,
  onBringBack,
  clearing,
  onRemoveAll,
  saveProblem,
  onCloseProblem,
  refused,
  onCloseRefused,
}: {
  /** A version of the library: Play and Print only (Phase 6). */
  readOnly?: boolean;
  playing: boolean;
  onTogglePlay: () => void;
  undo: { can: boolean; label: string | null; busy: boolean; run: () => void };
  redo: { can: boolean; label: string | null; busy: boolean; run: () => void };
  toolboxOpen: boolean;
  onToolbox: () => void;
  onRecord: () => void;
  canPrint: boolean;
  onPrint: () => void;
  canSave: boolean;
  /** There are changes that Save would keep. */
  unsaved: boolean;
  saving: boolean;
  flash: "saved" | "removed" | null;
  onSave: () => void;
  pianoOpen: boolean;
  onPiano: () => void;
  onFindTrills: () => void;
  /** How many notes are taken off the page, for the item that brings them back. */
  hiddenCount: number;
  onBringBack: () => void;
  clearing: boolean;
  onRemoveAll: () => void;
  saveProblem: string | null;
  onCloseProblem: () => void;
  refused: string | null;
  onCloseRefused: () => void;
}) {
  const more: RowMenuItem[] = [
    {
      label: pianoOpen ? "Hide the keyboard" : "Show the keyboard",
      icon: <PianoIcon fontSize="small" />,
      onClick: onPiano,
    },
    { label: "Find trills", icon: <GraphicEqIcon fontSize="small" />, onClick: onFindTrills },
    ...(hiddenCount > 0
      ? [
          {
            label: `Bring back ${hiddenCount} note${hiddenCount === 1 ? "" : "s"} taken off`,
            icon: <RestoreIcon fontSize="small" />,
            onClick: onBringBack,
          },
        ]
      : []),
    {
      label: "Remove all",
      icon: <DeleteSweepIcon fontSize="small" />,
      onClick: onRemoveAll,
      danger: true,
      disabled: saving || clearing,
    },
  ];
  if (readOnly) {
    return (
      <FloatingBar open label="sheet buttons">
        <IconAction
          title={playing ? "Pause" : "Play"}
          shortcut="Space"
          icon={playing ? <PauseIcon /> : <PlayArrowIcon />}
          onClick={onTogglePlay}
          placement="top"
        />
        <IconAction title="Print to PDF" icon={<PrintIcon />} onClick={onPrint} disabled={!canPrint} placement="top" />
      </FloatingBar>
    );
  }
  return (
    <>
      {/*
        A refused save, where the reader is. It stays until it is closed: a save is pressed and then
        looked away from, and a reading that the reader believes is saved and is not is the worst
        thing this page can do.
      */}
      <Snackbar
        open={saveProblem !== null}
        anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
        onClose={onCloseProblem}
        sx={{ zIndex: 1250 }}
      >
        <Alert severity="error" variant="filled" onClose={onCloseProblem} sx={{ maxWidth: 560 }}>
          {saveProblem}
        </Alert>
      </Snackbar>
      <Snackbar
        open={refused !== null && saveProblem === null}
        anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
        onClose={(_event, reason) => {
          if (reason !== "clickaway") onCloseRefused();
        }}
        sx={{ zIndex: 1250 }}
      >
        <Alert severity="warning" onClose={onCloseRefused} sx={{ maxWidth: 560 }}>
          {refused}
        </Alert>
      </Snackbar>
      <FloatingBar open label="sheet buttons">
        <IconAction
          title={playing ? "Pause" : "Play"}
          shortcut="Space"
          icon={playing ? <PauseIcon /> : <PlayArrowIcon />}
          onClick={onTogglePlay}
          placement="top"
        />
        <IconAction
          title={undo.label ? `Undo: ${undo.label}` : "Undo"}
          shortcut="⌘Z"
          icon={<UndoIcon />}
          onClick={undo.run}
          disabled={!undo.can || undo.busy}
          disabledTitle="Nothing to undo"
          placement="top"
        />
        <IconAction
          title={redo.label ? `Redo: ${redo.label}` : "Redo"}
          shortcut="⇧⌘Z"
          icon={<RedoIcon />}
          onClick={redo.run}
          disabled={!redo.can || redo.busy}
          disabledTitle="Nothing to redo"
          placement="top"
        />
        <Divider orientation="vertical" flexItem />
        <IconAction
          title="Sheet toolbox"
          icon={<TuneIcon />}
          onClick={onToolbox}
          active={toolboxOpen}
          placement="top"
        />
        <IconAction
          title="Record a passage"
          icon={<FiberManualRecordIcon />}
          onClick={onRecord}
          placement="top"
        />
        <IconAction
          title="Print to PDF"
          icon={<PrintIcon />}
          onClick={onPrint}
          disabled={!canPrint}
          placement="top"
        />
        <Divider orientation="vertical" flexItem />
        <Tooltip
          title={
            !canSave
              ? "Nothing to save until the sheet is written"
              : saveProblem
                ? saveProblem
                : unsaved
                  ? "Keep these changes"
                  : "Everything is saved"
          }
          placement="top"
        >
          <span>
            <Badge
              color="warning"
              variant="dot"
              overlap="rectangular"
              invisible={!unsaved || flash === "saved"}
              data-unsaved={unsaved ? "unsaved" : ""}
            >
              <PillButton
                kind="primary"
                size="small"
                busy={saving}
                disabled={!canSave || clearing}
                onClick={onSave}
                startIcon={flash === "saved" ? <CheckIcon /> : undefined}
              >
                {flash === "saved" ? "Saved" : saveProblem ? "Save failed" : "Save"}
              </PillButton>
            </Badge>
          </span>
        </Tooltip>
        <RowMenu items={more} title="More sheet actions" />
      </FloatingBar>
    </>
  );
}

export default SheetFloatingBar;
