/**
 * Examples: the example screenshots, the manual annotation, and the score board.
 *
 * Stories 2.2 and 2.3. This is the measuring tab: a detection rule ships with its
 * measured score over these pictures, or it does not ship (V-20). The work on one
 * example goes left to right — fit the piano overlay, read the picture by hand,
 * then run the detector and look at where the two disagree.
 */

import { useCallback, useEffect, useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import FormControlLabel from "@mui/material/FormControlLabel";
import MenuItem from "@mui/material/MenuItem";
import Stack from "@mui/material/Stack";
import Switch from "@mui/material/Switch";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import TextField from "@mui/material/TextField";
import { useNavigate, useParams } from "react-router-dom";
import {
  frameExamplesApi,
  type Annotation,
  type Calibration,
  type Detection,
  type ExampleSummary,
  type FindRequest,
  type FrameExample,
  type ScoreBoard,
} from "../../api/frameExamples";
import { ROUTES } from "../../layout/routes";
import { PageContainer, SectionCard, palette } from "../../ui";
import AnnotationEditor from "../../components/video/AnnotationEditor";
import CalibrationEditor from "../../components/video/CalibrationEditor";
import DetectionView from "../../components/video/DetectionView";
import ScoreBoardTable from "../../components/video/ScoreBoardTable";

type Step = "calibrate" | "annotate" | "detect";

/** Every request on this page fails the same way: say what went wrong, in words. */
const report = (setError: (message: string) => void) => (caught: unknown) => {
  setError(caught instanceof Error ? caught.message : String(caught));
};

export function ExamplesPage() {
  const { slug } = useParams<{ slug: string }>();
  const navigate = useNavigate();

  const [list, setList] = useState<ExampleSummary[] | null>(null);
  const [record, setRecord] = useState<FrameExample | null>(null);
  const [board, setBoard] = useState<ScoreBoard | null>(null);
  const [detection, setDetection] = useState<Detection | null>(null);
  const [step, setStep] = useState<Step>("calibrate");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [channel, setChannel] = useState("plate");
  const [colourCheck, setColourCheck] = useState(false);
  const [detectOffset, setDetectOffset] = useState<number | null>(null);

  // Which example these values describe. Switching example clears them during
  // render rather than in an effect, so the page never shows one example's
  // reading over another one's picture for a frame.
  const [shown, setShown] = useState<string | undefined>(slug);
  if (shown !== slug) {
    setShown(slug);
    setRecord(null);
    setDetection(null);
    setDetectOffset(null);
    setStep("calibrate");
  }

  const refreshList = useCallback(
    () => frameExamplesApi.list().then(setList).catch(report(setError)),
    [],
  );

  const refreshBoard = useCallback(
    () =>
      frameExamplesApi
        .score({ channel, colourCheck })
        .then(setBoard)
        .catch(report(setError)),
    [channel, colourCheck],
  );

  const refreshRecord = useCallback(
    (loaded: FrameExample) => {
      setRecord(loaded);
      return Promise.all([refreshList(), refreshBoard()]);
    },
    [refreshList, refreshBoard],
  );

  useEffect(() => {
    void refreshList();
  }, [refreshList]);

  useEffect(() => {
    void refreshBoard();
  }, [refreshBoard]);

  useEffect(() => {
    if (!slug) return;
    const controller = new AbortController();
    frameExamplesApi
      .get(slug, controller.signal)
      .then((loaded) => {
        setRecord(loaded);
        // Always the first step. Jumping an example that already has a
        // calibration straight to reading it was meant to save a click and
        // instead hid where the work starts: the piano is the first thing to
        // check on a picture you have not seen before.
        setStep("calibrate");
        // Two white keys to begin with, always. Opening on the narrowest window
        // already read would be honest and useless: on `derulo` that window is
        // six pixels tall and the right answer in it is nothing at all.
        setDetectOffset((loaded.calibration?.whiteWidth ?? 12) * 2);
      })
      .catch((caught: unknown) => {
        if (!controller.signal.aborted) setError(String(caught));
      });
    return () => controller.abort();
  }, [slug]);

  /** The one rectangle in, the overlay found inside it out (V-37). Nothing saved. */
  const findOverlay = useCallback(
    (body: FindRequest) => {
      if (!slug) return Promise.reject(new Error("no example"));
      return frameExamplesApi.find(slug, body);
    },
    [slug],
  );

  const saveCalibration = (calibration: Calibration) => {
    if (!slug) return;
    setBusy(true);
    frameExamplesApi
      .putCalibration(slug, calibration)
      .then((loaded) => {
        setStep("annotate");
        return refreshRecord(loaded);
      })
      .catch(report(setError))
      .finally(() => setBusy(false));
  };

  const saveAnnotation = (annotation: Annotation) => {
    if (!slug) return;
    setBusy(true);
    frameExamplesApi
      .putAnnotation(slug, annotation)
      .then((loaded) => {
        setDetectOffset(annotation.offsetPx);
        return refreshRecord(loaded);
      })
      .catch(report(setError))
      .finally(() => setBusy(false));
  };

  const removeAnnotation = (offsetPx: number) => {
    if (!slug) return;
    frameExamplesApi
      .deleteAnnotation(slug, offsetPx)
      .then(refreshRecord)
      .catch(report(setError));
  };

  /**
   * The detector reads the window the user is looking at, and re-reads it when
   * they move the line. There is no button: the answer is what the screen is
   * about, so waiting to be asked for it would be a step with no decision in it.
   * The offset line settles before it runs, because dragging a line is dozens of
   * values and every one of them would otherwise be a request.
   */
  useEffect(() => {
    if (!slug || !record?.calibration || step !== "detect") return;
    const offset = detectOffset ?? record.calibration.whiteWidth * 2;
    const controller = new AbortController();
    const handle = window.setTimeout(() => {
      frameExamplesApi
        .detect(slug, offset, { channel, colourCheck }, controller.signal)
        .then(setDetection)
        .catch((caught: unknown) => {
          if (!controller.signal.aborted) setError(String(caught));
        });
    }, 150);
    return () => {
      controller.abort();
      window.clearTimeout(handle);
    };
  }, [slug, record?.calibration, step, detectOffset, channel, colourCheck]);

  const toggleNoRoll = () => {
    if (!slug || !record) return;
    frameExamplesApi
      .setNoRoll(slug, !record.noRoll)
      .then(refreshRecord)
      .catch(report(setError));
  };

  const imageUrl = slug ? frameExamplesApi.imageUrl(slug) : "";

  return (
    <PageContainer
      title="Examples"
      subtitle="Every rendering these videos use, read by hand and read by the detector, side by side."
      wide
      actions={
        slug ? (
          <Button size="small" onClick={() => navigate(ROUTES.videoExamples)}>
            All examples
          </Button>
        ) : null
      }
    >
      {error ? (
        <Alert severity="error" onClose={() => setError(null)} sx={{ mb: 2 }}>
          {error}
        </Alert>
      ) : null}

      {!slug ? (
        <>
          <SectionCard
            title="The example set"
            description="One screenshot per rendering. Every example needs its own calibration, because every example is a different piano."
          >
            {list === null ? (
              <CircularProgress size={20} />
            ) : (
              <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap", rowGap: 1 }}>
                {list.map((row) => (
                  <Chip
                    key={row.slug}
                    label={label(row)}
                    variant={row.annotationCount ? "filled" : "outlined"}
                    onClick={() => navigate(ROUTES.videoExample(row.slug))}
                    sx={
                      row.noRoll
                        ? { opacity: 0.55 }
                        : row.annotationCount
                          ? { backgroundColor: palette.light.Green }
                          : undefined
                    }
                  />
                ))}
              </Stack>
            )}
          </SectionCard>

          <SectionCard
            title="The score board"
            description="Every annotated example at every annotated offset line position. This is the number a change has to quote."
            actions={
              <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
                <TextField
                  select
                  size="small"
                  label="Channel"
                  value={channel}
                  onChange={(event) => setChannel(event.target.value)}
                  sx={{ minWidth: 120 }}
                >
                  <MenuItem value="plate">plate</MenuItem>
                  <MenuItem value="edges">edges</MenuItem>
                  <MenuItem value="both">both</MenuItem>
                </TextField>
                <FormControlLabel
                  control={
                    <Switch
                      size="small"
                      checked={colourCheck}
                      onChange={(event) => setColourCheck(event.target.checked)}
                    />
                  }
                  label="Colour check"
                />
                <Button size="small" onClick={() => void refreshBoard()}>
                  Run again
                </Button>
              </Stack>
            }
          >
            {board ? (
              <ScoreBoardTable
                board={board}
                onPickExample={(picked) => navigate(ROUTES.videoExample(picked))}
              />
            ) : (
              <CircularProgress size={20} />
            )}
          </SectionCard>
        </>
      ) : null}

      {slug && record ? (
        <SectionCard
          title={slug}
          description={`${record.imageWidth} × ${record.imageHeight} · ${record.annotations.length} reading${record.annotations.length === 1 ? "" : "s"} saved`}
          actions={
            <FormControlLabel
              control={<Switch size="small" checked={record.noRoll} onChange={toggleNoRoll} />}
              label="No roll to read"
            />
          }
        >
          {record.noRoll ? (
            <Alert severity="warning" variant="outlined" sx={{ mb: 2 }}>
              This example is marked as having no roll to read, so it is left out of the score board
              rather than counted as a failure.
            </Alert>
          ) : null}

          <Tabs value={step} onChange={(_, value) => setStep(value as Step)} sx={{ mb: 2 }}>
            <Tab value="calibrate" label="1 · Fit the piano" />
            <Tab value="annotate" label="2 · Read it by hand" disabled={!record.calibration} />
            <Tab value="detect" label="3 · What the detector saw" disabled={!record.calibration} />
          </Tabs>

          {step === "calibrate" ? (
            <CalibrationEditor
              imageUrl={imageUrl}
              imageWidth={record.imageWidth}
              imageHeight={record.imageHeight}
              calibration={record.calibration}
              onFind={findOverlay}
              onSave={saveCalibration}
              saving={busy}
            />
          ) : null}

          {step === "annotate" && record.calibration ? (
            <AnnotationEditor
              imageUrl={imageUrl}
              imageWidth={record.imageWidth}
              imageHeight={record.imageHeight}
              calibration={record.calibration}
              annotations={record.annotations}
              onSave={saveAnnotation}
              onDelete={removeAnnotation}
              saving={busy}
            />
          ) : null}

          {step === "detect" && record.calibration ? (
            <DetectionView
              imageUrl={imageUrl}
              imageWidth={record.imageWidth}
              imageHeight={record.imageHeight}
              calibration={record.calibration}
              detection={detection}
              offsetPx={detectOffset ?? record.calibration.whiteWidth * 2}
              onOffsetChange={setDetectOffset}
              onSave={saveAnnotation}
              saving={busy}
              saved={record.annotations.find(
                (one) => Math.round(one.offsetPx) === Math.round(detectOffset ?? -1),
              )}
            />
          ) : null}
        </SectionCard>
      ) : null}

      {slug && !record ? (
        <Box sx={{ py: 4, textAlign: "center" }}>
          <CircularProgress size={24} />
        </Box>
      ) : null}
    </PageContainer>
  );
}

function label(row: ExampleSummary): string {
  if (row.noRoll) return `${row.slug} · no roll`;
  if (!row.hasCalibration) return `${row.slug} · not calibrated`;
  if (!row.annotationCount) return `${row.slug} · not read yet`;
  return `${row.slug} · ${row.annotationCount} reading${row.annotationCount === 1 ? "" : "s"}`;
}

export default ExamplesPage;
