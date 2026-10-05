/**
 * The top of a page: the title on the left and its one primary action on the right (plan section
 * 6.2). No subtitle and no paragraph: what a page is for is the title, what to do is the button.
 *
 * `back` puts a back arrow before the title, for a page inside another one (a project inside
 * Projects). `children` sits between the title and the action, for a page that needs a row of
 * its own controls there (the step tabs of a project).
 */

import type { ReactNode } from "react";
import Box from "@mui/material/Box";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import { useNavigate } from "react-router-dom";
import IconAction from "./IconAction";

export interface PageHeaderProps {
  title: string;
  /** Where the back arrow goes, and what its tooltip says. */
  back?: { to: string; label: string };
  /** The primary action, and any secondary icon actions beside it. */
  actions?: ReactNode;
  children?: ReactNode;
}

export function PageHeader({ title, back, actions, children }: PageHeaderProps) {
  const navigate = useNavigate();
  return (
    <Stack
      direction="row"
      useFlexGap
      spacing={2}
      sx={{ alignItems: "center", minHeight: 52, flexWrap: { xs: "wrap", md: "nowrap" }, rowGap: 1 }}
    >
      <Stack direction="row" spacing={0.5} sx={{ alignItems: "center", minWidth: 0, flex: { xs: "1 1 0", md: "0 1 auto" } }}>
        {back ? <IconAction title={back.label} icon={<ArrowBackIcon fontSize="small" />} onClick={() => navigate(back.to)} /> : null}
        <Typography
          variant="h1"
          noWrap
          title={title}
          sx={{ minWidth: 0, maxWidth: { xs: "none", md: 360, lg: 480 } }}
        >
          {title}
        </Typography>
      </Stack>
      {/* On a narrow screen the middle row goes under the title, and the action stays beside it. */}
      {children ? (
        <Box
          sx={{
            minWidth: 0,
            flexGrow: 1,
            display: "flex",
            justifyContent: "center",
            order: { xs: 3, md: 0 },
            flexBasis: { xs: "100%", md: "auto" },
          }}
        >
          {children}
        </Box>
      ) : null}
      {children ? null : <Box sx={{ flexGrow: 1 }} />}
      {actions ? (
        <Stack direction="row" spacing={1} sx={{ alignItems: "center", flexShrink: 0 }}>
          {actions}
        </Stack>
      ) : null}
    </Stack>
  );
}

export default PageHeader;
