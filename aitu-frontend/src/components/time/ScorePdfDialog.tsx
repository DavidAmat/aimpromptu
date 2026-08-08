/**
 * The sheet on paper: choose the page, look at it, take the PDF.
 *
 * A window is as wide as the reader dragged it and a sheet of A4 is 210 mm, so the two can never
 * show the same line breaks. The notation package handles that the only way that keeps the music
 * readable — it re-wraps to the narrower width rather than shrinking what was on screen (D5) — and
 * the one number that decides how much room each line gets is the margin. So the margin is a
 * control here, next to a preview of the actual pages, instead of a constant somebody has to
 * rebuild the app to change.
 *
 * The preview is not a picture of the PDF. It *is* the pages the PDF is written from, which is why
 * what you approve and what you get cannot drift apart.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import FormControlLabel from "@mui/material/FormControlLabel";
import MenuItem from "@mui/material/MenuItem";
import Slider from "@mui/material/Slider";
import Stack from "@mui/material/Stack";
import Switch from "@mui/material/Switch";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import {
  installPrintStyles,
  type GridNotationRenderer,
  type PagedRenderResult,
} from "@aimpromptu/grid-notation";
import { pdfFilenameFor, saveBlob, scoreToPdf } from "../../print/scorePdf";

export interface ScorePdfDialogProps {
  open: boolean;
  onClose: () => void;
  /** The live renderer for the sheet on screen, or `null` when nothing is drawn. */
  renderer: GridNotationRenderer | null;
  /** What the piece is called, used for the title on page one and for the filename. */
  pieceName?: string;
}

/** How wide the preview column is allowed to get before the pages are scaled to fit it. */
const PREVIEW_WIDTH = 460;

export function ScorePdfDialog({ open, onClose, renderer, pieceName }: ScorePdfDialogProps) {
  /**
   * Held as state rather than as a ref, because the panel's contents are mounted a render *after*
   * it opens: a ref read in the first effect is still empty, and the pages would silently never be
   * drawn. As state, the node's arrival is itself what starts the drawing.
   */
  const [host, setHost] = useState<HTMLDivElement | null>(null);
  /** The box that carries the shrink-to-fit, kept apart from the box the pages go in. */
  const frame = useRef<HTMLDivElement | null>(null);
  const [paper, setPaper] = useState<"a4" | "letter">("a4");
  const [landscape, setLandscape] = useState(false);
  const [sideMargin, setSideMargin] = useState(14);
  const [endMargin, setEndMargin] = useState(16);
  const [title, setTitle] = useState("");
  const [subtitle, setSubtitle] = useState("");
  const [pageNumbers, setPageNumbers] = useState(true);
  // The pages, kept together with the settings they were drawn from. Whether the panel is busy is
  // then a comparison rather than a second piece of state that could disagree with the first.
  const [drawn, setDrawn] = useState<{
    result: PagedRenderResult;
    from: unknown;
  } | null>(null);
  const [saving, setSaving] = useState<{ done: number; total: number } | null>(null);
  const [failed, setFailed] = useState<string | null>(null);

  // The piece's own name, the first time the panel is opened for it. Typed over freely after that:
  // what a piece is called on paper is a decision about the printed copy, not about the recording.
  // Compared while rendering rather than in an effect, so page one never draws for one frame with
  // no title on it and then jumps.
  const [namedFor, setNamedFor] = useState<string | null>(null);
  if (open && namedFor !== (pieceName ?? "")) {
    setNamedFor(pieceName ?? "");
    if (!title) setTitle(pieceName ?? "");
  }

  const options = useMemo(
    () => ({
      pageSize: paper,
      orientation: landscape ? ("landscape" as const) : ("portrait" as const),
      marginsMm: { top: endMargin, bottom: endMargin, left: sideMargin, right: sideMargin },
      pageNumbers,
      ...(title.trim() ? { title: title.trim() } : {}),
      ...(subtitle.trim() ? { subtitle: subtitle.trim() } : {}),
    }),
    [paper, landscape, endMargin, sideMargin, pageNumbers, title, subtitle],
  );

  // Redrawn on a short delay, because dragging the margin slider would otherwise re-wrap the whole
  // piece on every pixel of the drag.
  useEffect(() => {
    if (!open || !renderer || !host) return;
    const timer = window.setTimeout(() => {
      installPrintStyles(document);
      try {
        setDrawn({ result: renderer.renderPages(host, options), from: options });
        setFailed(null);
      } catch (error) {
        setFailed(error instanceof Error ? error.message : "The pages could not be drawn.");
      }
    }, 220);
    return () => window.clearTimeout(timer);
  }, [open, renderer, options, host]);

  const layout = drawn?.result ?? null;
  const drawing = drawn?.from !== options;
  const scale = layout ? Math.min(1, PREVIEW_WIDTH / layout.pageWidth) : 1;

  const download = useCallback(async () => {
    if (!host) return;
    setSaving({ done: 0, total: layout?.pages.length ?? 1 });
    setFailed(null);
    // Every position written into the file is one the browser measured, and the preview is shrunk
    // to fit the panel. So the shrinking comes off for as long as it takes to read the pages, or
    // the whole score would be written at preview size.
    const shrunk = frame.current?.style.transform ?? "";
    if (frame.current) frame.current.style.transform = "none";
    try {
      const blob = await scoreToPdf(host, {
        ...(title.trim() ? { title: title.trim() } : {}),
        onProgress: (done, total) => setSaving({ done, total }),
      });
      saveBlob(blob, pdfFilenameFor(title.trim() || pieceName));
    } catch (error) {
      setFailed(error instanceof Error ? error.message : "The PDF could not be written.");
    } finally {
      if (frame.current) frame.current.style.transform = shrunk;
      setSaving(null);
    }
  }, [host, layout, pieceName, title]);

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>Download the sheet as a PDF</DialogTitle>
      <DialogContent dividers>
        <Stack direction={{ xs: "column", md: "row" }} spacing={3}>
          <Stack spacing={2.5} sx={{ minWidth: 280, flex: 1 }}>
            <Stack direction="row" spacing={2}>
              <TextField
                select
                size="small"
                label="Paper"
                value={paper}
                onChange={(event) => setPaper(event.target.value as "a4" | "letter")}
                sx={{ minWidth: 130 }}
              >
                <MenuItem value="a4">A4</MenuItem>
                <MenuItem value="letter">US Letter</MenuItem>
              </TextField>
              <TextField
                select
                size="small"
                label="Orientation"
                value={landscape ? "landscape" : "portrait"}
                onChange={(event) => setLandscape(event.target.value === "landscape")}
                sx={{ minWidth: 150 }}
              >
                <MenuItem value="portrait">Portrait</MenuItem>
                <MenuItem value="landscape">Landscape</MenuItem>
              </TextField>
            </Stack>

            <Box>
              <Typography variant="body2" gutterBottom>
                Side margins — {sideMargin} mm
              </Typography>
              <Slider
                size="small"
                min={5}
                max={35}
                value={sideMargin}
                onChange={(_, value) => setSideMargin(value as number)}
                valueLabelDisplay="auto"
              />
              <Typography variant="caption" color="text.secondary">
                Narrower margins give each line more room, so the music breaks in fewer places and
                the piece takes fewer pages. Nothing is shrunk: the lines re-wrap.
              </Typography>
            </Box>

            <Box>
              <Typography variant="body2" gutterBottom>
                Top and bottom — {endMargin} mm
              </Typography>
              <Slider
                size="small"
                min={5}
                max={35}
                value={endMargin}
                onChange={(_, value) => setEndMargin(value as number)}
                valueLabelDisplay="auto"
              />
              <Typography variant="caption" color="text.secondary">
                How many lines fit down a page. A line is never split across a page turn.
              </Typography>
            </Box>

            <TextField
              size="small"
              label="Title"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              helperText="Large on page one, small at the top of the rest. Leave it empty for none."
            />
            <TextField
              size="small"
              label="Second line"
              value={subtitle}
              onChange={(event) => setSubtitle(event.target.value)}
              helperText="Under the title on page one — a composer, a source, a date."
            />
            <FormControlLabel
              control={
                <Switch
                  size="small"
                  checked={pageNumbers}
                  onChange={(event) => setPageNumbers(event.target.checked)}
                />
              }
              label="Number the pages"
            />
            {failed ? <Alert severity="error">{failed}</Alert> : null}
          </Stack>

          <Box
            sx={{
              flex: 1,
              minWidth: 0,
              maxHeight: 520,
              overflowY: "auto",
              bgcolor: "grey.100",
              borderRadius: 1,
              p: 1.5,
            }}
          >
            {/*
              The pages themselves, shrunk to fit. `transform` rather than a smaller render, so the
              thing on screen and the thing written to the file are the same DOM.
            */}
            <Box
              ref={frame}
              sx={{
                transform: `scale(${scale})`,
                transformOrigin: "top left",
                width: layout ? layout.pageWidth : "100%",
                opacity: drawing ? 0.4 : 1,
                transition: "opacity 120ms",
              }}
            >
              <Box ref={setHost} />
            </Box>
          </Box>
        </Stack>
      </DialogContent>
      <DialogActions sx={{ justifyContent: "space-between", px: 3 }}>
        <Typography variant="body2" color="text.secondary">
          {drawing
            ? "Laying the music out…"
            : layout
              ? `${layout.pages.length} page${layout.pages.length === 1 ? "" : "s"}, ${
                  paper === "a4" ? "A4" : "US Letter"
                } ${landscape ? "landscape" : "portrait"}`
              : "Nothing to print yet."}
        </Typography>
        <Stack direction="row" spacing={1}>
          <Button onClick={onClose}>Close</Button>
          <Button
            variant="contained"
            disabled={!layout || drawing || saving !== null}
            onClick={() => void download()}
            startIcon={saving ? <CircularProgress size={16} color="inherit" /> : undefined}
          >
            {saving ? `Writing page ${saving.done} of ${saving.total}` : "Download PDF"}
          </Button>
        </Stack>
      </DialogActions>
    </Dialog>
  );
}

export default ScorePdfDialog;
