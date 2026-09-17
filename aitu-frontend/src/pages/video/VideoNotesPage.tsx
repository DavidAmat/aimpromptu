/**
 * Notes — the whole video stitched into one picture, and then the piece.
 *
 * Story 4.1 and Story 4.3. The scroll speed is constant over a piece, so the top
 * `scrollSpeed x sampleMs` rows of each sampled frame are the strip of the roll
 * nobody has seen yet; piling them up rebuilds the whole video as one tall
 * picture whose vertical axis is time, and a note is one shape in it whose top
 * and bottom rows convert straight to seconds (V-32, V-05).
 *
 * That reading is **not** the piece yet. It is what will be written, shown first
 * so it can be looked at and corrected (Task 4.3.1), and only then written
 * through the writer that already exists (V-02). Writing is the step that
 * changes the piece, so it advances the music version and the screen says so
 * before it does it.
 *
 * Why the reading is drawn back onto the video rather than on a roll of its own:
 * the question this screen answers is whether the notes are the rectangles, and
 * the only way to answer it is to put them on the rectangles.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { MouseEvent as ReactMouseEvent } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import LinearProgress from "@mui/material/LinearProgress";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { Link } from "react-router-dom";
import { audioApi } from "../../api/audio";
import type { PianoKey } from "../../api/frameExamples";
import {
  videoApi,
  type NoteCorrections,
  type VideoNote,
  type VideoNotes,
  type VideoSummary,
  type WriteResult,
} from "../../api/video";
import FramePlayer from "../../components/video/FramePlayer";
import NotesOnFrame from "../../components/video/NotesOnFrame";
import PianoOverlay from "../../components/video/PianoOverlay";
import TimeFrameLines from "../../components/video/TimeFrameLines";
import VideoBar from "../../components/video/VideoBar";
import useProgress from "../../hooks/useProgress";
import { ROUTES } from "../../layout/routes";
import { noteName } from "../../music/noteNames";
import { formatTime } from "../../audio/time";
import { PageContainer, SectionCard, surface } from "../../ui";
import { buildKeys } from "../../video/overlayGeometry";
import { noteId, place } from "../../video/notePlacement";
import { readSelectedVideo, writeSelectedVideo } from "../../video/selectedVideo";
import { useWorkingArtifact } from "../../state/useWorkingArtifact";

/** A drag shorter than this is a click, not a band. The Piano Roll's number. */
const BAND_THRESHOLD = 3;

interface Band {
  x0: number;
  y0: number;
  x1: number;
  y1: number;
  additive: boolean;
}

interface Drawing {
  key: PianoKey;
  yTop: number;
  yBottom: number;
}

export function VideoNotesPage() {
  const [videos, setVideos] = useState<VideoSummary[] | null>(null);
  const [selected, setSelected] = useState<string | null>(readSelectedVideo);
  const [jobId, setJobId] = useState<string | null>(null);
  const [read, setRead] = useState<VideoNotes | null>(null);
  const [corrections, setCorrections] = useState<NoteCorrections>({ removed: [], added: [] });
  const [picked, setPicked] = useState<ReadonlySet<string>>(() => new Set());
  const [index, setIndex] = useState(0);
  const [band, setBand] = useState<Band | null>(null);
  const [drawing, setDrawing] = useState<Drawing | null>(null);
  const [written, setWritten] = useState<WriteResult | null>(null);
  const { update: updateWorkingArtifact } = useWorkingArtifact();
  const [error, setError] = useState<string | null>(null);
  const gesture = useRef(false);

  const progress = useProgress(jobId ? videoApi.progressUrl(jobId) : null);

  const refresh = useCallback(
    () =>
      videoApi
        .list()
        .then(setVideos)
        .catch((caught: unknown) =>
          setError(caught instanceof Error ? caught.message : String(caught)),
        ),
    [],
  );

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const video = videos?.find((one) => one.metadata.audioUuid === selected) ?? null;
  const calibration = video?.calibration ?? null;
  const pxPerSecond = video?.measurement?.scrollSpeed.pxPerSecond ?? 0;

  const [seenVideo, setSeenVideo] = useState<string | null>(selected);
  if (seenVideo !== selected) {
    setSeenVideo(selected);
    setIndex(0);
    setRead(null);
    setWritten(null);
    setPicked(new Set());
  }

  // The reading and the corrections are both files on disk, so they are asked
  // for when the video changes and again when a job ends.
  useEffect(() => {
    if (!selected) return;
    const controller = new AbortController();
    videoApi.notes(selected, controller.signal).then(setRead).catch(() => setRead(null));
    videoApi
      .corrections(selected, controller.signal)
      .then(setCorrections)
      .catch(() => setCorrections({ removed: [], added: [] }));
    return () => controller.abort();
  }, [selected, video?.noteCount]);

  const [seenJob, setSeenJob] = useState<string | null>(null);
  if (progress.status === "done" && jobId && seenJob !== jobId) {
    setSeenJob(jobId);
    void refresh();
    if (selected) void videoApi.notes(selected).then(setRead).catch(() => undefined);
  }

  const keys = useMemo(() => (calibration ? buildKeys(calibration) : []), [calibration]);

  /** What will be written: the reading, less the removals, plus the additions. */
  const notes: VideoNote[] = useMemo(() => {
    const base = read?.notes ?? [];
    const added: VideoNote[] = corrections.added.map((one) => ({
      midi: one.midi,
      start: one.start,
      end: one.end ?? one.start + 0.1,
      rowTop: 0,
      rowBottom: 0,
      widthKeys: 0,
      keyDistance: 0,
      startsBefore: false,
      endsAfter: false,
    }));
    return [...base, ...added].sort((a, b) => a.start - b.start || a.midi - b.midi);
  }, [read, corrections.added]);

  const removedIds = useMemo(
    () => new Set(corrections.removed.map((one) => `${one.midi}:${one.start.toFixed(4)}`)),
    [corrections.removed],
  );

  const seconds = ((video?.metadata.sampleMs ?? 100) * index) / 1000;

  const pick = (id: string, additive: boolean) =>
    setPicked((current) => {
      if (!additive) return new Set([id]);
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  const save = (next: NoteCorrections) => {
    setCorrections(next);
    if (!selected) return;
    videoApi
      .putCorrections(selected, next)
      .catch((caught: unknown) =>
        setError(caught instanceof Error ? caught.message : String(caught)),
      );
  };

  /** Take the picked notes off, or put them back if they were already off. */
  const toggleRemoved = () => {
    const chosen = notes.filter((note) => picked.has(noteId(note)));
    if (!chosen.length) return;
    const allOff = chosen.every((note) => removedIds.has(noteId(note)));
    const ids = new Set(chosen.map(noteId));
    const kept = corrections.removed.filter(
      (one) => !ids.has(`${one.midi}:${one.start.toFixed(4)}`),
    );
    save({
      removed: allOff
        ? kept
        : [...kept, ...chosen.map((note) => ({ midi: note.midi, start: note.start }))],
      // An added note that is taken off again is simply not added: there is no
      // reason to keep a correction that cancels another one.
      added: allOff
        ? corrections.added
        : corrections.added.filter((one) => !ids.has(`${one.midi}:${one.start.toFixed(4)}`)),
    });
    setPicked(new Set());
  };

  /**
   * The gestures on the picture. A plain press on empty picture drags a band; a
   * press with shift draws a note the reading missed, on the key under it.
   */
  const onPictureMouseDown = (
    point: { x: number; y: number },
    event: ReactMouseEvent<SVGSVGElement>,
  ) => {
    if (!calibration || pxPerSecond <= 0) return false;
    if (event.shiftKey) {
      const key = keys.find((one) => point.x >= one.left && point.x <= one.right);
      if (!key) return false;
      gesture.current = true;
      setDrawing({ key, yTop: point.y, yBottom: point.y });
      return true;
    }
    gesture.current = true;
    setBand({
      x0: point.x,
      y0: point.y,
      x1: point.x,
      y1: point.y,
      additive: event.metaKey || event.ctrlKey,
    });
    return true;
  };

  // The band and the drawn note follow the mouse on the window, not on the
  // canvas, so a drag that leaves the picture still ends where the user let go.
  useEffect(() => {
    if (!band && !drawing) return;
    const svg = document.querySelector<SVGSVGElement>("[data-video-notes] svg");
    const at = (event: MouseEvent) => {
      if (!svg) return null;
      const box = svg.getBoundingClientRect();
      const view = svg.viewBox.baseVal;
      const fit = Math.min(box.width / view.width, box.height / view.height);
      const offsetX = (box.width - view.width * fit) / 2;
      const offsetY = (box.height - view.height * fit) / 2;
      return {
        x: view.x + (event.clientX - box.left - offsetX) / fit,
        y: view.y + (event.clientY - box.top - offsetY) / fit,
      };
    };
    const move = (event: MouseEvent) => {
      const point = at(event);
      if (!point) return;
      if (band) setBand({ ...band, x1: point.x, y1: point.y });
      if (drawing) setDrawing({ ...drawing, yBottom: point.y });
    };
    const up = () => {
      if (band) {
        const small =
          Math.abs(band.x1 - band.x0) < BAND_THRESHOLD &&
          Math.abs(band.y1 - band.y0) < BAND_THRESHOLD;
        if (small) {
          if (!band.additive) setPicked(new Set());
        } else if (calibration) {
          const inside = place(notes, keys, calibration, seconds, pxPerSecond)
            .filter(
              (one) =>
                one.key.right >= Math.min(band.x0, band.x1) &&
                one.key.left <= Math.max(band.x0, band.x1) &&
                one.yBottom >= Math.min(band.y0, band.y1) &&
                one.yTop <= Math.max(band.y0, band.y1),
            )
            .map((one) => one.id);
          setPicked((current) =>
            band.additive ? new Set([...current, ...inside]) : new Set(inside),
          );
        }
        setBand(null);
      }
      if (drawing && calibration) {
        const top = Math.min(drawing.yTop, drawing.yBottom);
        const bottom = Math.max(drawing.yTop, drawing.yBottom);
        if (bottom - top >= BAND_THRESHOLD) {
          const start = seconds + (calibration.upperLine - bottom) / pxPerSecond;
          const end = seconds + (calibration.upperLine - top) / pxPerSecond;
          save({
            removed: corrections.removed,
            added: [
              ...corrections.added,
              { midi: drawing.key.midi, start: Math.max(0, start), end: Math.max(0.001, end) },
            ],
          });
        }
        setDrawing(null);
      }
      gesture.current = false;
    };
    window.addEventListener("mousemove", move);
    window.addEventListener("mouseup", up);
    return () => {
      window.removeEventListener("mousemove", move);
      window.removeEventListener("mouseup", up);
    };
  });

  const pickVideo = (audioUuid: string) => {
    setSelected(audioUuid);
    writeSelectedVideo(audioUuid);
  };

  const runRead = () => {
    if (!video) return;
    setError(null);
    setWritten(null);
    videoApi
      .readNotes(video.metadata.audioUuid)
      .then((job) => setJobId(job.jobId))
      .catch((caught: unknown) =>
        setError(caught instanceof Error ? caught.message : String(caught)),
      );
  };

  const [writing, setWriting] = useState(false);
  const writePiece = () => {
    if (!video) return;
    setError(null);
    setWriting(true);
    videoApi
      .writeEvents(video.metadata.audioUuid)
      .then((result) => {
        setWritten(result);
        // The piece the Playground tabs share is now this one, so the Piano
        // Roll and the sheet open on it without a second picker.
        updateWorkingArtifact({ audioUuid: result.audioUuid, label: result.title });
        void refresh();
      })
      .catch((caught: unknown) =>
        setError(caught instanceof Error ? caught.message : String(caught)),
      )
      .finally(() => setWriting(false));
  };

  const running = jobId !== null && progress.status === "running";
  const ready = Boolean(calibration && video?.measurement?.scrollSpeed.stable);
  const report = read?.report ?? null;
  const willWrite = notes.filter((note) => !removedIds.has(noteId(note))).length;
  const chosen = notes.filter((note) => picked.has(noteId(note)));

  return (
    <PageContainer
      title="Notes"
      subtitle="The whole video as one picture whose vertical axis is time, the notes read off it, and then the piece."
      wide
    >
      {error ? (
        <Alert severity="error" onClose={() => setError(null)} sx={{ mb: 2 }}>
          {error}
        </Alert>
      ) : null}

      <SectionCard
        title="Read the video into notes"
        description="The fresh strip of every sampled frame, piled up into one tall picture: a note is one shape in it, and its bottom row is the onset and its top row the release. This does not write the piece — it is what will be written."
        actions={
          <Button variant="contained" size="small" onClick={runRead} disabled={!ready || running}>
            {running ? "Reading…" : read ? "Read it again" : "Read it"}
          </Button>
        }
      >
        <VideoBar videos={videos} selected={selected} onSelect={pickVideo} />

        {video && !ready ? (
          <Alert severity="info" variant="outlined" sx={{ mb: 2 }}>
            {!calibration
              ? "This video has no piano overlay yet. Fit it on the Calibration tab first."
              : "The scroll speed is not measured, or it is not stable. A row of the stitched roll is a distance, and a distance is only a time while the speed holds, so this is refused rather than guessed at."}
          </Alert>
        ) : null}

        {running ? (
          <Box sx={{ mb: 2 }}>
            <LinearProgress
              variant={progress.event?.total ? "determinate" : "indeterminate"}
              value={progress.event ? progress.event.fraction * 100 : 0}
            />
            <Typography variant="caption" sx={{ color: surface.mutedText }}>
              {progress.event?.stage} · {progress.event?.current} of {progress.event?.total}
            </Typography>
          </Box>
        ) : null}
        {progress.status === "error" ? (
          <Alert severity="error" sx={{ mb: 2 }}>
            {progress.error}
          </Alert>
        ) : null}

        {report ? (
          <Stack spacing={0.5}>
            <Typography variant="body2">
              <strong>{report.notes} notes</strong> over {report.frameCount} sampled frames ·{" "}
              {report.notesPerSecond.toFixed(2)} a second · median {report.medianLengthMs.toFixed(0)}{" "}
              ms long and {report.medianWidthKeys.toFixed(2)} white keys wide
            </Typography>
            <Typography variant="caption" sx={{ color: surface.mutedText }}>
              the picture is {report.rows.toLocaleString()} rows by {report.width}, which is{" "}
              {report.megabytes.toFixed(1)} MB · strip of {report.stripHeight} rows from row{" "}
              {report.stripTop}, with a head of {report.headRows} · stitched and read in{" "}
              {report.elapsedSeconds.toFixed(1)} s
            </Typography>
            <Typography variant="caption" sx={{ color: surface.mutedText }}>
              furthest from a key midpoint {report.worstKeyDistance.toFixed(3)} white key widths, and
              V-14 has a measured margin of 0.33 · plain connected shapes on the same picture find{" "}
              {report.connectedShapes} ·{" "}
              {Object.entries(report.rejected).length
                ? Object.entries(report.rejected)
                    .map(([reason, count]) => `${count} ${reason}`)
                    .join(", ")
                : "nothing"}{" "}
              thrown out by a gate
            </Typography>
            {report.busyKeys?.length ? (
              <Typography variant="body2" color="warning.main">
                {report.busyKeys.length === 1 ? "One key is" : `${report.busyKeys.length} keys are`}{" "}
                foreground more than six tenths of the time (MIDI {report.busyKeys.join(", ")}). The
                background plate cannot tell a key held for most of the piece from the roll behind it,
                so look at those lanes before writing the piece.
              </Typography>
            ) : null}
            {report.notesStartingBefore || report.notesEndingAfter || report.notesPastTheEnd ? (
              <Typography variant="caption" sx={{ color: surface.mutedText }}>
                {report.notesStartingBefore} already sounding when the video started ·{" "}
                {report.notesEndingAfter} still falling when it ended · {report.notesPastTheEnd} that
                never reached the piano and were dropped
              </Typography>
            ) : null}
          </Stack>
        ) : null}
      </SectionCard>

      {read && video && calibration && video.metadata.frameCount > 0 ? (
        <SectionCard
          title="What will be written"
          description="Every note put back where its rectangle is at this moment: if the reading is right, every box lands on a rectangle. Click a note to pick it, ⌘-click to add one, drag a band over the picture to pick several, and shift-drag on a key to draw a note the reading missed."
          actions={
            <Stack direction="row" spacing={1}>
              <Button size="small" onClick={toggleRemoved} disabled={!chosen.length}>
                {chosen.length && chosen.every((note) => removedIds.has(noteId(note)))
                  ? `Put ${chosen.length} back`
                  : `Take ${chosen.length || ""} off`}
              </Button>
              <Button
                variant="contained"
                size="small"
                onClick={writePiece}
                disabled={writing || !willWrite}
              >
                {writing ? "Writing…" : "Write the piece"}
              </Button>
            </Stack>
          }
        >
          {written ? (
            <Alert
              severity="success"
              onClose={() => setWritten(null)}
              sx={{ mb: 2 }}
              action={
                <Stack direction="row" spacing={1}>
                  <Button color="inherit" size="small" component={Link} to={ROUTES.playgroundPianoRoll}>
                    Open the Piano Roll
                  </Button>
                  <Button color="inherit" size="small" component={Link} to={ROUTES.playgroundRhythm}>
                    Open the sheet
                  </Button>
                </Stack>
              }
            >
              <strong>{written.notes} notes written</strong> into the piece «{written.title}», music
              version {written.musicVersion}
              {written.removed ? ` · ${written.removed} taken off by hand` : ""}
              {written.added ? ` · ${written.added} put on by hand` : ""}
              {written.unmatched
                ? ` · ${written.unmatched} corrections named a note the reading no longer holds`
                : ""}
              . The Playground now opens on this piece.
            </Alert>
          ) : null}
          <Stack direction="row" spacing={1} sx={{ mb: 1, alignItems: "center", flexWrap: "wrap" }}>
            <Chip size="small" label={`${willWrite} notes will be written`} />
            {corrections.removed.length ? (
              <Chip size="small" label={`${corrections.removed.length} taken off`} />
            ) : null}
            {corrections.added.length ? (
              <Chip size="small" label={`${corrections.added.length} put on by hand`} />
            ) : null}
            <Box sx={{ flexGrow: 1 }} />
            {chosen.length === 1 ? (
              <Typography variant="caption" sx={{ color: surface.mutedText }}>
                {noteName(chosen[0]!.midi)} at {formatTime(chosen[0]!.start)},{" "}
                {((chosen[0]!.end - chosen[0]!.start) * 1000).toFixed(0)} ms long
              </Typography>
            ) : chosen.length ? (
              <Typography variant="caption" sx={{ color: surface.mutedText }}>
                {chosen.length} notes picked · backspace or the button takes them off
              </Typography>
            ) : null}
          </Stack>

          <Box
            data-video-notes
            onKeyDown={(event) => {
              if (event.key === "Backspace" || event.key === "Delete") {
                event.preventDefault();
                toggleRemoved();
              }
            }}
          >
            <FramePlayer
              frameUrl={(at) => videoApi.frameUrl(video.metadata.audioUuid, at)}
              audioUrl={audioApi.fileUrl(video.metadata.audioUuid)}
              frameCount={video.metadata.frameCount}
              sampleMs={video.metadata.sampleMs}
              frameWidth={video.metadata.frameWidth}
              frameHeight={video.metadata.frameHeight}
              index={Math.min(index, video.metadata.frameCount - 1)}
              onIndexChange={setIndex}
              onPictureMouseDown={onPictureMouseDown}
              panDisabled={band !== null || drawing !== null}
              height={560}
            >
              {(scale) => (
                <>
                  <TimeFrameLines
                    upperLine={calibration.upperLine}
                    offsetPx={video.measurement?.offsetPx ?? 0}
                    imageWidth={video.metadata.frameWidth}
                    count={1}
                    rollTop={calibration.rollTop}
                    guardBand={calibration.guardBand}
                    scale={scale}
                  />
                  <NotesOnFrame
                    notes={notes}
                    keys={keys}
                    calibration={calibration}
                    seconds={seconds}
                    pxPerSecond={pxPerSecond}
                    scale={scale}
                    selected={picked}
                    removed={removedIds}
                    onPick={pick}
                    band={band}
                    drawing={drawing}
                  />
                  <PianoOverlay calibration={calibration} keys={keys} scale={scale} />
                </>
              )}
            </FramePlayer>
          </Box>
        </SectionCard>
      ) : null}

      {written ? (
        <Alert severity="success" sx={{ mt: 2 }}>
          <strong>{written.notes} notes</strong> written into the piece “{written.title}”, which is
          now at music version {written.musicVersion}
          {written.removed || written.added
            ? ` · ${written.removed} taken off and ${written.added} put on by hand`
            : ""}
          {written.unmatched
            ? ` · ${written.unmatched} corrections named a note the reading no longer holds`
            : ""}
          . It is an ordinary piece now:{" "}
          <Link to={ROUTES.playgroundPianoRoll}>open it on the Piano Roll</Link>.
        </Alert>
      ) : null}
    </PageContainer>
  );
}

export default VideoNotesPage;
