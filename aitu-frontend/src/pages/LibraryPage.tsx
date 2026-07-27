/** `/library` — browse tracks and playlists (Epic 10). */

import { PageContainer, Placeholder, SectionCard } from "../ui";

export function LibraryPage() {
  return (
    <PageContainer
      title="Piano Library"
      subtitle="Consolidated pieces ready to play, with tags, filters and playlists."
    >
      <SectionCard title="Tracks">
        <Placeholder
          epic="Epic 10 (Piano Library), Story 10.1"
          what="Track list with tags, filters and free-text search, plus management of playground pieces promoted here."
        />
      </SectionCard>
      <SectionCard title="Playlists">
        <Placeholder
          epic="Epic 10 (Piano Library), Story 10.3"
          what="Spotify-like playlists: CRUD, ordering, version-by-name selection and a playing mode with Next."
        />
      </SectionCard>
    </PageContainer>
  );
}

export default LibraryPage;
