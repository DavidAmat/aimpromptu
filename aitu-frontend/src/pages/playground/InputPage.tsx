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

import { useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Grid from "@mui/material/Grid";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import Typography from "@mui/material/Typography";
import type { AudioItem, ImportedMatrix, MatrixScore } from "../../api";
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

  const isAudioSource = SOURCES.find((item) => item.value === source)?.audio ?? true;
  const activeUuid = selected?.uuid ?? artifact.audioUuid ?? null;

  const chooseAudio = (audio: AudioItem) => {
    setSelected(audio);
    setNote(null);
    update({
      audioUuid: audio.uuid,
      artifactId: undefined,
      label: audio.alias,
      rangeStartSeconds: undefined,
      rangeEndSeconds: undefined,
    });
  };

  const audioArrived = (audio: AudioItem) => {
    setReloadToken((token) => token + 1);
    chooseAudio(audio);
  };

  const setRange = (range: AudioRange) => {
    update({ rangeStartSeconds: range.startSeconds, rangeEndSeconds: range.endSeconds });
  };

  const notationParsed = (score: MatrixScore, frames: number) => {
    // The score's time step implies a granularity in beats; keep the artifact
    // consistent with what was actually parsed.
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
    update({
      audioUuid: imported.audioUuid,
      label,
      granularity: imported.granularity,
      matrixProcessingStep: imported.matrixProcessingStep,
      rangeStartSeconds: undefined,
      rangeEndSeconds: undefined,
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
              title="Range"
              description="Drag the handles or type mm:ss.mmm. Only the selected range is transcribed."
            >
              {activeUuid ? (
                <WaveformRangeSelector
                  key={activeUuid}
                  audioUuid={activeUuid}
                  durationSeconds={selected?.durationSeconds ?? undefined}
                  onRangeChange={setRange}
                />
              ) : (
                <Typography variant="body2" color="text.secondary">
                  Pick, upload or record an audio to see its waveform.
                </Typography>
              )}
            </SectionCard>

            <SectionCard
              title="Transcription settings"
              description="The raw matrix is always built at fusa, then collapsed to the resolution you pick."
            >
              <TranscriptionSettings
                audioUuid={activeUuid}
                durationSeconds={selected?.durationSeconds ?? undefined}
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
