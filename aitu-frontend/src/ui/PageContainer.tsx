/** Standard page frame: title, optional subtitle and actions, then content. */

import type { ReactNode } from "react";
import Box from "@mui/material/Box";
import Container from "@mui/material/Container";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

export interface PageContainerProps {
  title: string;
  subtitle?: string;
  /** Buttons or controls rendered to the right of the title. */
  actions?: ReactNode;
  /** `false` (default) keeps a comfortable max width; `true` fills the viewport. */
  wide?: boolean;
  children?: ReactNode;
}

export function PageContainer({ title, subtitle, actions, wide, children }: PageContainerProps) {
  return (
    <Container maxWidth={wide ? false : "lg"} sx={{ py: 3 }}>
      <Stack
        direction={{ xs: "column", sm: "row" }}
        spacing={1.5}
        sx={{
          mb: 2.5,
          justifyContent: "space-between",
          alignItems: { xs: "flex-start", sm: "center" },
        }}
      >
        <Box>
          <Typography variant="h1">{title}</Typography>
          {subtitle ? (
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
              {subtitle}
            </Typography>
          ) : null}
        </Box>
        {actions ? <Stack direction="row" spacing={1}>{actions}</Stack> : null}
      </Stack>
      {children}
    </Container>
  );
}

export default PageContainer;
