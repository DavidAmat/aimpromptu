/** Fallback route. */

import Button from "@mui/material/Button";
import { Link } from "react-router-dom";
import { PageContainer, SectionCard } from "../ui";
import { ROUTES } from "../layout/routes";

export function NotFoundPage() {
  return (
    <PageContainer title="Page not found">
      <SectionCard>
        <Button component={Link} to={ROUTES.playgroundInput} variant="contained">
          Go to the Playground
        </Button>
      </SectionCard>
    </PageContainer>
  );
}

export default NotFoundPage;
