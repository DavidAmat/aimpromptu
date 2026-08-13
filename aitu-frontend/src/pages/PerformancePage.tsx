/** `/library/play/:id` — read-only performance view (Epic 10, Story 10.2). */

import { useCallback, useEffect, useRef, useState } from "react";
import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Stack from "@mui/material/Stack";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import type { GridNotationRenderer } from "@aimpromptu/grid-notation";
import { libraryApi, type LibraryTrack, type PlaylistItem, type Promotion } from "../api";
import ScorePdfDialog from "../components/time/ScorePdfDialog";
import ScorePlayer, { type ScorePlayerControls } from "../components/time/ScorePlayer";
import TimeScoreView from "../components/time/TimeScoreView";
import { ROUTES } from "../layout/routes";
import { loadPerformanceScore, type PerformanceReading } from "../library/loadPerformanceScore";
import { activePromotions, libraryPlayId, parseLibraryPlayId } from "../library/playId";
import { PageContainer, Pill, SectionCard } from "../ui";

export function PerformancePage() {
  const { id } = useParams<{ id: string }>();
  const [params] = useSearchParams();
  const ref = parseLibraryPlayId(id);
  const wantedName = params.get("promotion") ?? undefined;
  const playlistSlug = params.get("playlist") ?? undefined;
  const playlistIndex = Number(params.get("index") ?? "0");

  if (!ref) {
    return (
      <PageContainer title="Performance view" subtitle={`Piece: ${id ?? "unknown"}`}>
        <SectionCard>
          <Alert severity="error">That is not a library piece.</Alert>
          <Button component={Link} to={ROUTES.library} sx={{ mt: 2 }}>
            Back to the library
          </Button>
        </SectionCard>
      </PageContainer>
    );
  }

  return (
    <LoadedPerformance
      artistSlug={ref.artistSlug}
      trackSlug={ref.trackSlug}
      wantedName={wantedName}
      playlistSlug={playlistSlug}
      playlistIndex={Number.isFinite(playlistIndex) ? playlistIndex : 0}
    />
  );
}

function LoadedPerformance({
  artistSlug,
  trackSlug,
  wantedName,
  playlistSlug,
  playlistIndex,
}: {
  artistSlug: string;
  trackSlug: string;
  wantedName?: string;
  playlistSlug?: string;
  playlistIndex: number;
}) {
  const [track, setTrack] = useState<LibraryTrack | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    libraryApi
      .getTrack(artistSlug, trackSlug, controller.signal)
      .then((loaded) => {
        setTrack(loaded);
        setError(null);
      })
      .catch((caught: unknown) => {
        if (controller.signal.aborted) return;
        setTrack(null);
        setError(caught instanceof Error ? caught.message : "Could not load that piece.");
      });
    return () => controller.abort();
  }, [artistSlug, trackSlug]);

  const promotion = track ? pickPromotion(track, wantedName) : null;
  const blocked = promotion?.needsRederivation ?? null;
  const audioUuid = promotion?.audioUuid ?? null;
  const title = promotion?.promotionName ?? track?.trackName ?? "Performance view";
  const subtitle = track ? `${track.trackName} — ${track.artistName}` : `${artistSlug}/${trackSlug}`;

  return (
    <PageContainer
      wide
      title={title}
      subtitle={subtitle}
      actions={
        <Stack direction="row" spacing={1}>
          <Button component={Link} to={ROUTES.library} variant="outlined" size="small">
            Back to the library
          </Button>
          {playlistSlug ? <PlaylistNext playlistSlug={playlistSlug} playlistIndex={playlistIndex} /> : null}
        </Stack>
      }
    >
      {error ? (
        <SectionCard>
          <Alert severity="error">{error}</Alert>
        </SectionCard>
      ) : !track ? (
        <LoadingCard />
      ) : blocked ? (
        <SectionCard>
          <Alert severity="warning">
            This piece cannot be opened in the performance view. {blocked}
          </Alert>
        </SectionCard>
      ) : !audioUuid ? (
        <SectionCard>
          <Alert severity="info">This promotion has no linked audio, so there is nothing to draw.</Alert>
        </SectionCard>
      ) : (
        <PerformanceStand audioUuid={audioUuid} title={title} />
      )}
    </PageContainer>
  );
}

function PlaylistNext({
  playlistSlug,
  playlistIndex,
}: {
  playlistSlug: string;
  playlistIndex: number;
}) {
  const navigate = useNavigate();
  const [nextItem, setNextItem] = useState<PlaylistItem | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    libraryApi
      .getPlaylist(playlistSlug, controller.signal)
      .then((playlist) => setNextItem(playlist.items[playlistIndex + 1] ?? null))
      .catch(() => setNextItem(null));
    return () => controller.abort();
  }, [playlistSlug, playlistIndex]);

  if (!nextItem) return null;
  const path = ROUTES.libraryPlay(libraryPlayId(nextItem.artistSlug, nextItem.trackSlug));
  const query = new URLSearchParams({
    promotion: nextItem.promotionName,
    playlist: playlistSlug,
    index: String(playlistIndex + 1),
  });
  return (
    <Button variant="contained" size="small" onClick={() => navigate(`${path}?${query.toString()}`)}>
      Next
    </Button>
  );
}

function PerformanceStand({ audioUuid, title }: { audioUuid: string; title: string }) {
  const [reading, setReading] = useState<PerformanceReading | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sheetRenderer, setSheetRenderer] = useState<GridNotationRenderer | null>(null);
  const [pdfOpen, setPdfOpen] = useState(false);
  const [playheadSeconds, setPlayheadSeconds] = useState<number | null>(0);
  const [playing, setPlaying] = useState(false);
  const [scrollCursorAt, setScrollCursorAt] = useState(0);
  const player = useRef<ScorePlayerControls | null>(null);
  const [showFingers, setShowFingers] = useState(true);
  const [showMarks, setShowMarks] = useState(true);
  const [showGuides, setShowGuides] = useState(true);

  useEffect(() => {
    const controller = new AbortController();
    loadPerformanceScore(audioUuid, controller.signal)
      .then((loaded) => {
        if (controller.signal.aborted) return;
        setReading(loaded);
        setError(null);
      })
      .catch((caught: unknown) => {
        if (controller.signal.aborted) return;
        setReading(null);
        setError(caught instanceof Error ? caught.message : "Could not draw that piece.");
      });
    return () => controller.abort();
  }, [audioUuid]);

  const scrub = useCallback((seconds: number) => {
    player.current?.seek(seconds);
  }, []);

  if (error) {
    return (
      <SectionCard>
        <Alert severity="error">{error}</Alert>
      </SectionCard>
    );
  }
  if (!reading) return <LoadingCard />;

  return (
    <Stack spacing={2}>
      {reading.unnamed ? (
        <Alert severity="info">
          No rhythm is saved for this piece yet. Figures are unnamed until someone names a gap on
          the Rhythm tab.
        </Alert>
      ) : null}

      <Stack direction="row" spacing={1} useFlexGap sx={{ flexWrap: "wrap", alignItems: "center" }}>
        <Typography variant="caption" color="text.secondary">
          Overlays
        </Typography>
        <Pill label="Fingering" selected={showFingers} onClick={() => setShowFingers((value) => !value)} />
        <Tooltip title="Lyrics arrive in Epic 12">
          <span>
            <Pill label="Lyrics" disabled />
          </span>
        </Tooltip>
        <Pill
          label="Tuplet & trill marks"
          selected={showMarks}
          onClick={() => setShowMarks((value) => !value)}
        />
        <Pill label="Guides" selected={showGuides} onClick={() => setShowGuides((value) => !value)} />
        <Button size="small" variant="outlined" disabled={!sheetRenderer} onClick={() => setPdfOpen(true)}>
          PDF
        </Button>
      </Stack>

      <ScorePlayer
        audioUuid={audioUuid}
        scoreSeconds={(reading.score.envelope.frameCount * reading.score.envelope.frameMs) / 1000}
        onTime={setPlayheadSeconds}
        controlsRef={player}
        onScrollToCursor={() => setScrollCursorAt((value) => value + 1)}
        onPlaying={setPlaying}
      />

      <TimeScoreView
        score={reading.score}
        overrides={reading.overrides}
        beamBreaks={reading.beamBreaks}
        keySignature={reading.keySignature}
        keyChanges={reading.keyChanges}
        ottavas={reading.ottavas}
        fingers={reading.fingers}
        playheadSeconds={playheadSeconds}
        followPlayhead={playing}
        onScrub={scrub}
        scrollCursorAt={scrollCursorAt}
        onRendererChange={setSheetRenderer}
        readOnly
        showFingers={showFingers}
        showTuplets={showMarks}
        showGuides={showGuides}
      />

      <ScorePdfDialog
        open={pdfOpen}
        onClose={() => setPdfOpen(false)}
        renderer={sheetRenderer}
        pieceName={title}
      />
    </Stack>
  );
}

function LoadingCard() {
  return (
    <SectionCard>
      <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
        <CircularProgress size={16} />
        <Typography variant="body2" color="text.secondary">
          Loading…
        </Typography>
      </Stack>
    </SectionCard>
  );
}

function pickPromotion(track: LibraryTrack, name?: string): Promotion | null {
  if (name) {
    const named = [...track.promotions].reverse().find((item) => item.promotionName === name);
    if (named) return named;
  }
  const live = activePromotions(track.promotions);
  return live[0] ?? track.promotions.at(-1) ?? null;
}

export default PerformancePage;
