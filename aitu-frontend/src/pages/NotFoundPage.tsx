/** A path that matches no page: say so, and offer the way back to Projects. */

import { useNavigate } from "react-router-dom";
import { ROUTES } from "../layout/routes";
import { EmptyState, PageBody, PageHeader, PillButton } from "../ui";

export function NotFoundPage() {
  const navigate = useNavigate();
  return (
    <PageBody>
      <PageHeader title="Page not found" />
      <EmptyState
        message="There is no page at this address."
        action={
          <PillButton kind="primary" onClick={() => navigate(ROUTES.projects)}>
            Open Projects
          </PillButton>
        }
      />
    </PageBody>
  );
}

export default NotFoundPage;
