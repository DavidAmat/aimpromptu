/** `/library/play/:id` — read-only performance view (Epic 10, Story 10.2). */

import { useParams } from "react-router-dom";
import { PageContainer, Placeholder, SectionCard } from "../ui";

export function PerformancePage() {
  const { id } = useParams<{ id: string }>();

  return (
    <PageContainer title="Performance view" subtitle={`Piece: ${id ?? "unknown"}`}>
      <SectionCard>
        <Placeholder
          epic="Epic 10 (Piano Library), Story 10.2"
          what="Clean read-only score page with overlay toggles (lyrics, fingering, beat guides) and scroll/zoom tuned for playing from the screen."
        />
      </SectionCard>
    </PageContainer>
  );
}

export default PerformancePage;
