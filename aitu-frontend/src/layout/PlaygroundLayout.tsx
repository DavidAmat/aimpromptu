/**
 * Playground chrome: the five tabs plus a banner naming the current working
 * artifact. The artifact lives in context, so switching tabs keeps the piece.
 */

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Container from "@mui/material/Container";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { Outlet } from "react-router-dom";
import { Pill, TabBar } from "../ui";
import { useWorkingArtifact } from "../state/useWorkingArtifact";
import { PLAYGROUND_TABS } from "./routes";

export function PlaygroundLayout() {
  const { artifact, hasArtifact, clear } = useWorkingArtifact();

  return (
    <Box>
      <Container maxWidth={false} sx={{ pt: 1 }}>
        <TabBar items={PLAYGROUND_TABS} />
        <Stack
          direction="row"
          spacing={1.5}
          sx={{ py: 1.25, flexWrap: "wrap", rowGap: 1, alignItems: "center" }}
        >
          <Typography variant="body2" color="text.secondary">
            Working piece:
          </Typography>
          <Typography variant="body2" sx={{ fontWeight: 600 }}>
            {hasArtifact
              ? (artifact.label ?? artifact.artifactId ?? artifact.audioUuid)
              : "none loaded"}
          </Typography>
          <Pill label={`${artifact.tempoBpm} BPM`} />
          <Pill label={artifact.granularity} />
          <Pill label={artifact.matrixProcessingStep} />
          {hasArtifact ? (
            <Button size="small" onClick={clear}>
              Clear
            </Button>
          ) : null}
        </Stack>
      </Container>
      <Outlet />
    </Box>
  );
}

export default PlaygroundLayout;
