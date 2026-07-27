/**
 * `/playground/input` — the five ways a piece enters the Playground.
 *
 * Three of them are audio (upload, record, library) and share the range
 * selector and the transcription settings below. Two of them produce matrices
 * directly (text notation, matrix JSON) and skip the engine entirely — so the
 * settings panel is hidden for those, because BPM and granularity are already
 * baked into what they carry.
 *
 * Every mode ends the same way: the working artifact is populated.
 */

import { useEffect, useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Grid from "@mui/material/Grid";
import Stack from "@mui/material/Stack";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import ContentCutIcon from "@mui/icons-material/ContentCut";
import { audioApi, type AudioItem, type ImportedMatrix, type MatrixScore } from "../../api";
import { formatTime } from "../../audio/time";
import AudioLibraryList from "../../components/audio/AudioLibraryList";
import AudioRecorder from "../../components/audio/AudioRecorder";
import AudioUpload from "../../components/audio/AudioUpload";
import WaveformRangeSelector, {
  type AudioRange,
} from "../../components/audio/WaveformRangeSelector";
import MatrixJsonInput from "../../components/input/MatrixJsonInput";
import TextNotationInput from "../../components/input/TextNotationInput";
import TranscriptionSettings from "../../components/input/TranscriptionSettings";
import { GRANULARITY_BEATS } from "../../music/types";
import { useWorkingArtifact } from "../../state/useWorkingArtifact";
import { PageContainer, SectionCard } from "../../ui";

type Source = "upload" | "record" | "library" | "notation" | "json";

const SOURCES: { value: Source; label: string; audio: boolean }[] = [
  { value: "upload", label: "Upload audio", audio: true },
  { value: "record", label: "Record", audio: true },
  { value: "library", label: "Audio library", audio: true },
  { value: "notation", label: "Text notation", audio: false },
  { value: "json", label: "Matrix JSON", audio: false },
];

export function InputPage() {
  const { artifact, update, hasArtifact } = useWorkingArtifact();
  const [source, setSource] = useState<Source>("library");
  const [selected, setSelected] = useState<AudioItem | null>(null);
  const [reloadToken, setReloadToken] = useState(0);
  const [note, setNote] = useState<string | null>(null);
  const [pendingRange, setPendingRange] = useState<AudioRange | null>(null);
  const [segmentName, setSegmentName] = useState("");
  const [trimBusy, setTrimBusy] = useState(false);
  const [trimError, setTrimError] = useState<string | null>(null);

  const isAudioSource = SOURCES.find((item) => item.value === source)?.audio ?? true;
  const activeUuid = selected?.uuid ?? artifact.audioUuid ?? null;
  const selectionIsPartial = Boolean(
    selected?.durationSeconds &&
      pendingRange &&
      (pendingRange.startSeconds > 0.001 ||
        pendingRange.endSeconds < selected.durationSeconds - 0.001),
  );

  const chooseAudio = (audio: AudioItem) => {
    setSelected(audio);
    setNote(null);
    setTrimError(null);
    setPendingRange(null);
    setSegmentName("");
    update({
      audioUuid: audio.uuid,
      artifactId: undefined,
      label: audio.alias,
    });
  };

  useEffect(() => {
    const audioUuid = artifact.audioUuid;
    if (!audioUuid || selected?.uuid === audioUuid) return;
    const controller = new AbortController();
    audioApi
      .get(audioUuid, controller.signal)
      .then((audio) => setSelected(audio))
      .catch(() => {
        // Matrix JSON imports intentionally have no playable audio metadata.
      });
    return () => controller.abort();
  }, [artifact.audioUuid, selected?.uuid]);

  const audioArrived = (audio: AudioItem) => {
    setReloadToken((token) => token + 1);
    chooseAudio(audio);
  };

  const setRange = (range: AudioRange) => {
    setPendingRange(range);
    if (selected) {
      setSegmentName(
        `${selected.alias} — segment ${formatTime(range.startSeconds)}–${formatTime(
          range.endSeconds,
        )}`,
      );
    }
  };

  const createSegment = async () => {
    if (!selected || !pendingRange) return;
    setTrimBusy(true);
    setTrimError(null);
    try {
      const segment = await audioApi.trim(selected.uuid, {
        ...pendingRange,
        alias: segmentName.trim() || undefined,
      });
      setReloadToken((token) => token + 1);
      chooseAudio(segment);
      setNote(
        `Created "${segment.alias}". Its waveform, playback and matrix now use only the saved ` +
          `${formatTime(segment.durationSeconds ?? 0)} segment.`,
      );
    } catch (caught) {
      setTrimError(caught instanceof Error ? caught.message : "Could not create the segment.");
    } finally {
      setTrimBusy(false);
    }
  };

  const returnToOriginal = async () => {
    if (!selected?.sourceAudioUuid) return;
    setTrimBusy(true);
    setTrimError(null);
    try {
      chooseAudio(await audioApi.get(selected.sourceAudioUuid));
    } catch (caught) {
      setTrimError(caught instanceof Error ? caught.message : "Could not load the original audio.");
    } finally {
      setTrimBusy(false);
    }
  };

  const notationParsed = (score: MatrixScore, frames: number) => {
    // The score's time step implies a granularity in beats; keep the artifact
    // consistent with what was actually parsed.
    setSelected(null);
    setPendingRange(null);
    update({
      audioUuid: undefined,
      label: score.title || "Text notation",
      tempoBpm: score.tempoBpm,
      matrixProcessingStep: "clean",
    });
    setNote(`Parsed ${frames} frame(s) from text notation.`);
  };

  const jsonImported = (imported: ImportedMatrix, label: string) => {
    // The backend stored it under a uuid, so the Matrix tab reads it exactly
    // like a transcription — that is the handoff.
    setSelected(null);
    setPendingRange(null);
    update({
      audioUuid: imported.audioUuid,
      label,
      granularity: imported.granularity,
      matrixProcessingStep: imported.matrixProcessingStep,
    });
    setNote(
      `Imported "${label}" — ${imported.frameCount} frames at ${imported.granularity}. ` +
        "Open the Matrix tab to see it.",
    );
  };

  return (
    <PageContainer
      title="Upload / Input"
      subtitle="Where a piece enters the Playground: upload, record, pick from the library, write text notation, or load a matrix JSON."
      wide
    >
      <Tabs
        value={source}
        onChange={(_, value: Source) => setSource(value)}
        variant="scrollable"
        scrollButtons="auto"
        sx={{ mb: 2, borderBottom: 1, borderColor: "divider" }}
      >
        {SOURCES.map((item) => (
          <Tab key={item.value} value={item.value} label={item.label} />
        ))}
      </Tabs>

      {note ? (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setNote(null)}>
          {note}
        </Alert>
      ) : null}

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, md: isAudioSource ? 5 : 12 }}>
          {source === "upload" ? (
            <SectionCard title="Upload" description="mp3, aac, m4a or wav.">
              <AudioUpload onUploaded={audioArrived} />
            </SectionCard>
          ) : null}

          {source === "record" ? <AudioRecorder onSaved={audioArrived} /> : null}

          {source === "library" ? (
            <SectionCard
              title="Audio library"
              description="Uploads, recordings and YouTube downloads."
            >
              <AudioLibraryList
                selectedUuid={activeUuid}
                onSelect={chooseAudio}
                reloadToken={reloadToken}
              />
            </SectionCard>
          ) : null}

          {source === "notation" ? (
            <SectionCard
              title="Text notation"
              description="Produces a matrix directly — no transcription engine involved."
            >
              <TextNotationInput
                tempoBpm={artifact.tempoBpm}
                timeStepSeconds={
                  GRANULARITY_BEATS[artifact.granularity] * (60 / artifact.tempoBpm)
                }
                onParsed={notationParsed}
              />
            </SectionCard>
          ) : null}

          {source === "json" ? (
            <SectionCard
              title="Matrix JSON"
              description="A file exported from the Matrix tab, dense or sparse."
            >
              <MatrixJsonInput onImported={jsonImported} />
            </SectionCard>
          ) : null}
        </Grid>

        {isAudioSource ? (
          <Grid size={{ xs: 12, md: 7 }}>
            <SectionCard
              title={selected?.sourceTimeRange ? "Saved segment" : "Create a segment"}
              description={
                selected?.sourceTimeRange
                  ? "This waveform is the physically trimmed audio used by every Playground view."
                  : "Choose a range, name it, and create a trimmed audio before transcription."
              }
            >
              {trimError ? <Alert severity="error" sx={{ mb: 2 }}>{trimError}</Alert> : null}
              {selected?.sourceTimeRange ? (
                <Alert
                  severity="info"
                  sx={{ mb: 2 }}
                  action={
                    <Button
                      size="small"
                      startIcon={trimBusy ? <CircularProgress size={14} /> : <ArrowBackIcon />}
                      onClick={() => void returnToOriginal()}
                      disabled={trimBusy}
                    >
                      Back to original
                    </Button>
                  }
                >
                  Fragment of the original audio from{" "}
                  <strong>
                    {formatTime(selected.sourceTimeRange.startSeconds)}–{" "}
                    {formatTime(selected.sourceTimeRange.endSeconds)}
                  </strong>
                  . Its local timeline starts at 00:00.00.
                </Alert>
              ) : null}
              {activeUuid ? (
                <WaveformRangeSelector
                  key={activeUuid}
                  audioUuid={activeUuid}
                  durationSeconds={selected?.durationSeconds ?? undefined}
                  onRangeChange={setRange}
                  readOnly={Boolean(selected?.sourceTimeRange)}
                />
              ) : (
                <Typography variant="body2" color="text.secondary">
                  Pick, upload or record an audio to see its waveform.
                </Typography>
              )}
              {selected && !selected.sourceTimeRange ? (
                <Stack
                  direction={{ xs: "column", sm: "row" }}
                  spacing={1.5}
                  sx={{ mt: 2, alignItems: { sm: "center" } }}
                >
                  <TextField
                    label="Segment name"
                    size="small"
                    value={segmentName}
                    onChange={(event) => setSegmentName(event.target.value)}
                    placeholder={`${selected.alias} — segment`}
                    fullWidth
                  />
                  <Button
                    variant="contained"
                    startIcon={trimBusy ? <CircularProgress size={16} /> : <ContentCutIcon />}
                    disabled={
                      trimBusy ||
                      !selectionIsPartial
                    }
                    onClick={() => void createSegment()}
                    sx={{ whiteSpace: "nowrap" }}
                  >
                    Create segment
                  </Button>
                </Stack>
              ) : null}
            </SectionCard>

            <SectionCard
              title="Transcription settings"
              description="The raw matrix is always built at fusa, then collapsed to the resolution you pick."
            >
              <TranscriptionSettings
                audioUuid={activeUuid}
                audio={selected}
                requiresSegmentCreation={selectionIsPartial}
              />
            </SectionCard>
          </Grid>
        ) : (
          <Grid size={12}>
            <Box sx={{ mt: 1 }}>
              <Typography variant="body2" color="text.secondary">
                {hasArtifact
                  ? "Loaded. Switch to the Matrix tab to see it."
                  : "This source produces a matrix directly — no BPM or granularity to choose."}
              </Typography>
            </Box>
          </Grid>
        )}
      </Grid>
    </PageContainer>
  );
}

export default InputPage;
