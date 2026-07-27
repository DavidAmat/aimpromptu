/** `/playground/notation` — VexFlow sheet music (Epic 9). */

import { PageContainer, Placeholder, SectionCard } from "../../ui";

export function NotationPage() {
  return (
    <PageContainer
      title="Music Notation"
      subtitle="The matrix engraved as sheet music, rendered by VexFlow from a backend-built score document."
      wide
    >
      <SectionCard title="Score">
        <Placeholder
          epic="Epic 9 (Music notation), Stories 9.1 and 9.2"
          what="Artifact picker, grand staff or single hand, responsive wrapping, annotation saving and the promote button. The existing renderer in src/music/ and src/components/PianoSheet.tsx is reused here."
        />
      </SectionCard>
      <SectionCard title="Engraving rules">
        <Placeholder
          epic="Epic 9 (Music notation), Stories 9.3 to 9.6"
          what="Stem direction, beam runs, tie policy, key signatures and naturals, transposition, octave displacement and clef switching, beat guides and cut-measure."
        />
      </SectionCard>
    </PageContainer>
  );
}

export default NotationPage;
