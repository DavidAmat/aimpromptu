/**
 * `/playground/input` — the three ways a piece enters the Playground.
 *
 * All three are a recording: upload one, record one, or pick one from the audio
 * library. They share the range selector and the transcription settings below,
 * and they all end the same way, with the working artifact populated and the
 * recorded notes stored.
 *
 * A recording is now the only entry point, because the page is drawn from the
 * onsets the engine heard. The two modes that produced a matrix directly, text
 * notation and matrix JSON, had no recording behind them and therefore nothing
 * to draw; they were removed in P4.2.
 */

import { useEffect, useState } from "react";
import Alert from "@mui/material/Alert";
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
import { audioApi, type AudioItem } from "../../api";
import { formatTime } from "../../audio/time";
import AudioLibraryList from "../../components/audio/AudioLibraryList";
import AudioRecorder from "../../components/audio/AudioRecorder";
import AudioUpload from "../../components/audio/AudioUpload";
import WaveformRangeSelector, {
  type AudioRange,
} from "../../components/audio/WaveformRangeSelector";
import TranscriptionSettings from "../../components/input/TranscriptionSettings";
import { useWorkingArtifact } from "../../state/useWorkingArtifact";
import { PageContainer, SectionCard } from "../../ui";

type Source = "upload" | "record" | "library";

//: Every way a piece enters the Playground, and they are all a recording.
//:
//: "Text notation" and "Matrix JSON" used to be here too. Both produced a matrix
//: with no recording behind it, and under the wall-clock model there is nothing
//: to show for that: a page is drawn from the recorded onsets in `events.json`,
//: which a hand-written matrix does not have. They were removed in P4.2 rather
//: than left as buttons that lead nowhere.
const SOURCES: { value: Source; label: string; audio: boolean }[] = [
  { value: "upload", label: "Upload audio", audio: true },
  { value: "record", label: "Record", audio: true },
  { value: "library", label: "Audio library", audio: true },
];

export function InputPage() {
  const { artifact, update } = useWorkingArtifact();
  const [source, setSource] = useState<Source>("library");
  const [selected, setSelected] = useState<AudioItem | null>(null);
  const [reloadToken, setReloadToken] = useState(0);
  const [note, setNote] = useState<string | null>(null);
  const [pendingRange, setPendingRange] = useState<AudioRange | null>(null);
  const [segmentName, setSegmentName] = useState("");
  const [trimBusy, setTrimBusy] = useState(false);
  const [trimError, setTrimError] = useState<string | null>(null);

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

  return (
    <PageContainer
      title="Upload / Input"
      subtitle="Where a piece enters the Playground: upload a recording, record one, or pick one from the audio library."
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
        <Grid size={{ xs: 12, md: 5 }}>
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
        </Grid>

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
              description="The notes are recorded exactly as played. The rhythm is named afterwards, on the Rhythm step."
            >
              <TranscriptionSettings
                audioUuid={activeUuid}
                audio={selected}
                requiresSegmentCreation={selectionIsPartial}
              />
            </SectionCard>
        </Grid>
      </Grid>
    </PageContainer>
  );
}

export default InputPage;
