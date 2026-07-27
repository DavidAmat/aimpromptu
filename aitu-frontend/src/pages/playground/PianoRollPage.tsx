/** `/playground/piano-roll` — horizontal roll over the piano SVG (Epic 8). */

import { PageContainer, Placeholder, SectionCard } from "../../ui";

export function PianoRollPage() {
  return (
    <PageContainer
      title="Piano Roll"
      subtitle="Vertical piano on the left, note rectangles running right across time."
      wide
    >
      <SectionCard title="Roll view">
        <Placeholder
          epic="Epic 8 (Piano roll), Stories 8.1 and 8.2"
          what="Piano SVG with pressed-key overlays, note rectangles, dashed numbered guides, full-height fit and the waveform watermark."
        />
      </SectionCard>
      <SectionCard title="Player">
        <Placeholder
          epic="Epic 8 (Piano roll), Story 8.3"
          what="Transport with key highlighting, original audio vs sampled piano, and speed / BPM / granularity / range filters."
        />
      </SectionCard>
    </PageContainer>
  );
}

export default PianoRollPage;
