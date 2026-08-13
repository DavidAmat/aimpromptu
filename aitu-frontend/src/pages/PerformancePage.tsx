/** `/library/play/:id` — read-only performance view (Epic 10, Story 10.2). */

import { useEffect, useState } from "react";
import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { libraryApi, type LibraryTrack, type Promotion } from "../api";
import { ROUTES } from "../layout/routes";
import { activePromotions, parseLibraryPlayId } from "../library/playId";
import { PageContainer, Placeholder, SectionCard } from "../ui";

export function PerformancePage() {
  const { id } = useParams<{ id: string }>();
  const [params] = useSearchParams();
  const ref = parseLibraryPlayId(id);
  const wantedName = params.get("promotion") ?? undefined;

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

  return <LoadedPerformance artistSlug={ref.artistSlug} trackSlug={ref.trackSlug} wantedName={wantedName} />;
}

function LoadedPerformance({
  artistSlug,
  trackSlug,
  wantedName,
}: {
  artistSlug: string;
  trackSlug: string;
  wantedName?: string;
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
  const title = promotion?.promotionName ?? track?.trackName ?? "Performance view";

  return (
    <PageContainer
      title={title}
      subtitle={track ? `${track.trackName} — ${track.artistName}` : `${artistSlug}/${trackSlug}`}
    >
      {error ? (
        <SectionCard>
          <Alert severity="error">{error}</Alert>
          <Button component={Link} to={ROUTES.library} sx={{ mt: 2 }}>
            Back to the library
          </Button>
        </SectionCard>
      ) : !track ? (
        <SectionCard>
          <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
            <CircularProgress size={16} />
            <Typography variant="body2" color="text.secondary">
              Loading…
            </Typography>
          </Stack>
        </SectionCard>
      ) : blocked ? (
        <SectionCard>
          <Alert severity="warning">
            This piece cannot be opened in the performance view. {blocked}
          </Alert>
          <Button component={Link} to={ROUTES.library} sx={{ mt: 2 }}>
            Back to the library
          </Button>
        </SectionCard>
      ) : (
        <SectionCard>
          <Placeholder
            epic="Epic 10 (Piano Library), Story 10.2"
            what="Clean read-only score page with overlay toggles (lyrics, fingering, beat guides) and scroll/zoom tuned for playing from the screen."
          />
        </SectionCard>
      )}
    </PageContainer>
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
