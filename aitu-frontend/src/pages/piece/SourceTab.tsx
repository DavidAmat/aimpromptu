/**
 * Step 1, **Source**: where the audio of a piece comes from (plan section 7.1).
 *
 * Three ways, in one place: a piece already in the library, an audio file to upload, or a YouTube
 * URL. A piece from the library opens on the step it reached. A new audio opens on the Audio tab,
 * which is the next thing to do with it.
 */

import { useCallback } from "react";
import Grid from "@mui/material/Grid";
import { useNavigate } from "react-router-dom";
import AudioLibraryList from "../../components/audio/AudioLibraryList";
import AudioUpload from "../../components/audio/AudioUpload";
import YouTubeDownload from "../../components/piece/YouTubeDownload";
import { ROUTES } from "../../layout/routes";
import { SectionCard } from "../../ui";
import { usePiece } from "./pieceContext";

export function SourceTab() {
  const navigate = useNavigate();
  const { uuid } = usePiece();
  const openNew = useCallback(
    (audioUuid: string) => navigate(ROUTES.piece(audioUuid, "audio")),
    [navigate],
  );

  return (
    <Grid container spacing={2}>
      <Grid size={{ xs: 12, md: 7 }}>
        <SectionCard
          title="Audio library"
          description="Open a piece where you left it: a piece with a piano sheet opens on the Sheet tab."
        >
          <AudioLibraryList selectedUuid={uuid} onSelect={(item) => navigate(ROUTES.piece(item.uuid))} />
        </SectionCard>
      </Grid>
      <Grid size={{ xs: 12, md: 5 }}>
        <SectionCard title="YouTube" description="Download the audio of a video.">
          <YouTubeDownload onDone={openNew} />
        </SectionCard>
        <SectionCard title="Upload" description="An audio file from this computer.">
          <AudioUpload onUploaded={(audio) => openNew(audio.uuid)} />
        </SectionCard>
      </Grid>
    </Grid>
  );
}

export default SourceTab;
