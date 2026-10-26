/**
 * Print to PDF of the new sheet (implementation 03, Phase 8): choose the paper, look at the pages, take the PDF.
 *
 * The rule of the old sheet's panel stays (`context/frontend/printing.md`): the music is laid out again for the
 * paper, never shrunk. The backend draws the sheet for the paper's width at the printed size chosen here and deals
 * whole lines onto the pages (`GET /sheet/{uuid}/pages`): a line is never split across a page turn. The pages shown
 * here are the pages the PDF is written from (`print/scorePdf.ts`), with the title on page one and the page numbers.
 *
 * **A denser PDF** (Phase 8A+++, the user's request): **Size of the music** is the height of a printed staff (5 to
 * 8 mm; 6.5 mm by default, the size of many printed piano editions), and **Space between lines** is the white
 * between one line's ink and the next, in millimetres on paper (6 mm by default), whatever the space between lines on
 * the screen. Measured on the 10 viewer songs on A4: 5 to 7 lines a page (median 6), 44 pages instead of 51 with a
 * 7 mm staff and the screen's space. Both are kept in this browser.
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
import { sheetApi, type SheetPage } from "../../../../api";
import { pdfFilenameFor, saveBlob, scoreToPdf } from "../../../../print/scorePdf";
import { said } from "../../../library/shared";

/** The printed staff, in millimetres: the default and the limits (a staff space is a quarter of it). */
const STAFF_MM = 6.5;
const STAFF_MIN = 5;
const STAFF_MAX = 8;
/** The white between two lines on paper, in millimetres: the default and the limits. */
const BETWEEN_MM = 6;
const BETWEEN_MIN = 1;
const BETWEEN_MAX = 20;
/** The size and the space are kept in this browser (how this reader prints, not part of the sheet). */
const PRINT_KEY = "aitu.framesPdf.print";

function rememberedPrint(): { staff: number; between: number } {
  try {
    const kept = JSON.parse(window.localStorage.getItem(PRINT_KEY) ?? "null") as { staff?: unknown; between?: unknown } | null;
    const staff = Number(kept?.staff);
    const between = Number(kept?.between);
    return {
      staff: staff >= STAFF_MIN && staff <= STAFF_MAX ? staff : STAFF_MM,
      between: between >= BETWEEN_MIN && between <= BETWEEN_MAX ? between : BETWEEN_MM,
    };
  } catch {
    return { staff: STAFF_MM, between: BETWEEN_MM };
  }
}
/** CSS pixels per millimetre. */
const PX_PER_MM = 96 / 25.4;
/** The SVG adds this many staff spaces to the staff width (its margins). */
const SVG_MARGINS = 8;
/** The room the title takes on page one, in millimetres (with a second line: more). */
const TITLE_MM = 14;
const SUBTITLE_MM = 6;
const PREVIEW_WIDTH = 460;
/** The room around a page of the preview: its padding (12 px a side) and a scrollbar. */
const PREVIEW_ROOM = 24 + 18;
const PAPERS = { a4: [210, 297], letter: [215.9, 279.4] } as const;

export function FramesPdfDialog({
  open,
  onClose,
  audioUuid,
  pieceName,
  subtitle: firstSubtitle,
}: {
  open: boolean;
  onClose: () => void;
  audioUuid: string;
  /** The title on page one and the file's name, until the reader types another. */
  pieceName: string;
  subtitle: string;
}) {
  const [paper, setPaper] = useState<"a4" | "letter">("a4");
  const [landscape, setLandscape] = useState(false);
  const [sideMargin, setSideMargin] = useState(14);
  const [endMargin, setEndMargin] = useState(16);
  const [printing, setPrinting] = useState(rememberedPrint);
  const keep = (next: { staff: number; between: number }) => {
    setPrinting(next);
    try {
      window.localStorage.setItem(PRINT_KEY, JSON.stringify(next));
    } catch {
      // A browser that keeps nothing: the choice lasts while the page is open.
    }
  };
  const spaceMm = printing.staff / 4;
  const [title, setTitle] = useState(pieceName);
  const [subtitle, setSubtitle] = useState(firstSubtitle);
  const [pageNumbers, setPageNumbers] = useState(true);
  const [namedFor, setNamedFor] = useState<string | null>(null);
  if (open && namedFor !== `${pieceName}|${firstSubtitle}`) {
    setNamedFor(`${pieceName}|${firstSubtitle}`);
    setTitle(pieceName);
    setSubtitle(firstSubtitle);
  }

  const [width, height] = landscape ? [PAPERS[paper][1], PAPERS[paper][0]] : PAPERS[paper];
  const head = (title.trim() ? TITLE_MM : 0) + (subtitle.trim() ? SUBTITLE_MM : 0);
  const asked = useMemo(
    () => ({
      width: (width - 2 * sideMargin) / spaceMm - SVG_MARGINS,
      height: (height - 2 * endMargin) / spaceMm,
      first: (height - 2 * endMargin - head) / spaceMm,
      gap: printing.between / spaceMm,
    }),
    [width, height, sideMargin, endMargin, head, spaceMm, printing.between],
  );
  const key = JSON.stringify(asked);
  const [drawn, setDrawn] = useState<{ key: string; pages: SheetPage[] } | null>(null);
  const [failed, setFailed] = useState<string | null>(null);
  useEffect(() => {
    if (!open) return;
    const controller = new AbortController();
    // A short wait, so dragging a margin does not lay the piece out on every pixel of the drag.
    const timer = window.setTimeout(() => {
      sheetApi
        .pages(audioUuid, asked, controller.signal)
        .then((found) => {
          setDrawn({ key, pages: found.pages });
          setFailed(null);
        })
        .catch((caught: unknown) => {
          if (!controller.signal.aborted) setFailed(said(caught, "The pages could not be drawn."));
        });
    }, 220);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [open, audioUuid, asked, key]);

  const pages = drawn?.pages ?? null;
  const drawing = drawn?.key !== key;
  const pagePx = width * PX_PER_MM;
  const scale = Math.min(1, PREVIEW_WIDTH / pagePx);

  const host = useRef<HTMLDivElement | null>(null);
  const frame = useRef<HTMLDivElement | null>(null);
  const [saving, setSaving] = useState<{ done: number; total: number } | null>(null);
  const download = useCallback(async () => {
    if (!host.current) return;
    setSaving({ done: 0, total: pages?.length ?? 1 });
    setFailed(null);
    // Every position in the file is one the browser measured: the preview's shrinking comes off while the pages are
    // read, or the file would be written at preview size.
    const shrunk = frame.current?.style.transform ?? "";
    if (frame.current) frame.current.style.transform = "none";
    try {
      const blob = await scoreToPdf(host.current, {
        selector: "[data-pdf-page]",
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
  }, [pages, title, pieceName]);

  return (
    <Dialog open={open} onClose={onClose} maxWidth="lg" fullWidth data-frames-pdf>
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
                Side margins: {sideMargin} mm
              </Typography>
              <Slider size="small" min={5} max={35} value={sideMargin} onChange={(_, value) => setSideMargin(value as number)} />
              <Typography variant="caption" color="text.secondary">
                Narrower margins give each line more room, so the music breaks in fewer places. Nothing is shrunk: the
                lines are laid out again.
              </Typography>
            </Box>
            <Box>
              <Typography variant="body2" gutterBottom>
                Top and bottom: {endMargin} mm
              </Typography>
              <Slider size="small" min={5} max={35} value={endMargin} onChange={(_, value) => setEndMargin(value as number)} />
              <Typography variant="caption" color="text.secondary">
                How many lines fit down a page. A line is never split across a page turn.
              </Typography>
            </Box>
            <Box>
              <Typography variant="body2" gutterBottom>
                Size of the music: {printing.staff} mm staff
              </Typography>
              <Slider
                size="small"
                min={STAFF_MIN}
                max={STAFF_MAX}
                step={0.25}
                value={printing.staff}
                onChange={(_, value) => keep({ ...printing, staff: value as number })}
                slotProps={{ input: { "data-pdf-staff": true } as object }}
              />
            </Box>
            <Box>
              <Typography variant="body2" gutterBottom>
                Space between lines: {printing.between} mm
              </Typography>
              <Slider
                size="small"
                min={BETWEEN_MIN}
                max={BETWEEN_MAX}
                step={0.5}
                value={printing.between}
                onChange={(_, value) => keep({ ...printing, between: value as number })}
                slotProps={{ input: { "data-pdf-between": true } as object }}
              />
            </Box>
            <TextField
              size="small"
              label="Title"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              helperText="Printed on page one only. Leave it empty for none."
            />
            <TextField size="small" label="Second line" value={subtitle} onChange={(event) => setSubtitle(event.target.value)} />
            <FormControlLabel
              control={<Switch size="small" checked={pageNumbers} onChange={(event) => setPageNumbers(event.target.checked)} />}
              label="Number the pages"
            />
            {failed ? <Alert severity="error">{failed}</Alert> : null}
          </Stack>
          {/* As wide as a page of the preview, its padding and a scrollbar: both edges of the paper in view. */}
          <Box
            sx={{
              flex: "0 0 auto",
              width: { xs: "100%", md: Math.ceil(pagePx * scale) + PREVIEW_ROOM },
              maxHeight: 520,
              overflow: "auto",
              bgcolor: "grey.100",
              borderRadius: 1,
              p: 1.5,
            }}
            data-pdf-preview
          >
            <Box
              ref={frame}
              sx={{
                transform: `scale(${scale})`,
                transformOrigin: "top left",
                width: pagePx,
                opacity: drawing ? 0.4 : 1,
                transition: "opacity 120ms",
              }}
            >
              <Box ref={host}>
                {(pages ?? []).map((page, index) => (
                  <Box
                    key={`${index}:${page.first}`}
                    data-pdf-page
                    sx={{
                      position: "relative",
                      width: `${width}mm`,
                      height: `${height}mm`,
                      boxSizing: "border-box",
                      padding: `${endMargin}mm ${sideMargin}mm`,
                      bgcolor: "#fff",
                      mb: 2,
                      boxShadow: 1,
                      overflow: "hidden",
                    }}
                  >
                    {index === 0 && title.trim() ? (
                      <Box
                        sx={{
                          fontFamily: "Helvetica, Arial, sans-serif",
                          fontSize: "20px",
                          fontWeight: 600,
                          textAlign: "center",
                          color: "#000",
                          lineHeight: `${TITLE_MM * 0.75}mm`,
                        }}
                      >
                        {title.trim()}
                      </Box>
                    ) : null}
                    {index === 0 && subtitle.trim() ? (
                      <Box
                        sx={{
                          fontFamily: "Helvetica, Arial, sans-serif",
                          fontSize: "12px",
                          textAlign: "center",
                          color: "#000",
                          lineHeight: `${SUBTITLE_MM * 0.75}mm`,
                        }}
                      >
                        {subtitle.trim()}
                      </Box>
                    ) : null}
                    {index === 0 && head > 0 ? <Box sx={{ height: `${head * 0.25}mm` }} /> : null}
                    <Box
                      sx={{ "& svg": { display: "block", width: `${page.width * spaceMm}mm`, height: `${page.height * spaceMm}mm` } }}
                      dangerouslySetInnerHTML={{ __html: page.svg }}
                    />
                    {pageNumbers && pages && pages.length > 1 ? (
                      <Box
                        sx={{
                          position: "absolute",
                          bottom: `${Math.max(4, endMargin / 2 - 2)}mm`,
                          left: 0,
                          right: 0,
                          textAlign: "center",
                          fontFamily: "Helvetica, Arial, sans-serif",
                          fontSize: "10px",
                          color: "#000",
                        }}
                      >
                        {index + 1}
                      </Box>
                    ) : null}
                  </Box>
                ))}
              </Box>
            </Box>
          </Box>
        </Stack>
      </DialogContent>
      <DialogActions sx={{ justifyContent: "space-between", px: 3 }}>
        <Typography variant="body2" color="text.secondary" data-pdf-summary>
          {drawing
            ? "Laying the music out…"
            : pages && pages.length > 0
              ? `${pages.length} page${pages.length === 1 ? "" : "s"}, ${paper === "a4" ? "A4" : "US Letter"} ${
                  landscape ? "landscape" : "portrait"
                }`
              : "Nothing to print yet."}
        </Typography>
        <Stack direction="row" spacing={1}>
          <Button onClick={onClose}>Close</Button>
          <Button
            variant="contained"
            disabled={!pages || pages.length === 0 || drawing || saving !== null}
            onClick={() => void download()}
            startIcon={saving ? <CircularProgress size={16} color="inherit" /> : undefined}
            data-testid="pdf-download"
          >
            {saving ? `Writing page ${saving.done} of ${saving.total}` : "Download PDF"}
          </Button>
        </Stack>
      </DialogActions>
    </Dialog>
  );
}

export default FramesPdfDialog;
