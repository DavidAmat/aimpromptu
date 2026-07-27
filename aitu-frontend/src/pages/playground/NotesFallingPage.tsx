/** `/playground/notes-falling` — Synthesia-style falling view (Epic 8, Story 8.4). */

import { PageContainer, Placeholder, SectionCard } from "../../ui";

export function NotesFallingPage() {
  return (
    <PageContainer
      title="Notes Falling"
      subtitle="Rectangles falling onto a horizontal keyboard, swallowed as each note is struck."
      wide
    >
      <SectionCard>
        <Placeholder
          epic="Epic 8 (Piano roll), Story 8.4"
          what="Calibrated falling rectangles whose velocity comes from the visible window, BPM and granularity, with the swallow effect at Y=0."
        />
      </SectionCard>
    </PageContainer>
  );
}

export default NotesFallingPage;
