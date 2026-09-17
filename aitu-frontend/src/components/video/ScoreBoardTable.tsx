/**
 * The score board: found, invented and missed, per example and in total.
 *
 * Task 2.3.3. It is what says whether a change helped, and every change from here
 * on quotes it (V-20). The examples that could not be scored are listed with the
 * reason rather than left out quietly — an honest failure list is a result, a
 * rounded up number is not.
 */

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Stack from "@mui/material/Stack";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import type { ScoreBoard, ScoreLine } from "../../api/frameExamples";
import { palette, surface } from "../../ui";

export interface ScoreBoardTableProps {
  board: ScoreBoard;
  onPickExample?: (slug: string) => void;
}

function bad(value: number) {
  return value > 0 ? { color: palette.dark.Red, fontWeight: 600 } : undefined;
}

function Row({
  line,
  total,
  onPick,
}: {
  line: ScoreLine;
  total?: boolean;
  onPick?: () => void;
}) {
  return (
    <TableRow
      hover={!total}
      onClick={onPick}
      sx={{
        cursor: onPick ? "pointer" : "default",
        "& td": total ? { fontWeight: 700, borderTop: 2, borderColor: surface.strongLine } : undefined,
      }}
    >
      <TableCell>{total ? "total" : line.slug}</TableCell>
      <TableCell align="right">{total ? "" : line.offsetPx.toFixed(1)}</TableCell>
      <TableCell align="right">{line.onsetsFound}</TableCell>
      <TableCell align="right" sx={bad(line.onsetsInvented)}>
        {line.onsetsInvented}
      </TableCell>
      <TableCell align="right" sx={bad(line.onsetsMissed)}>
        {line.onsetsMissed}
      </TableCell>
      <TableCell align="right">{line.sustainsFound}</TableCell>
      <TableCell align="right" sx={bad(line.sustainsInvented)}>
        {line.sustainsInvented}
      </TableCell>
      <TableCell align="right" sx={bad(line.sustainsMissed)}>
        {line.sustainsMissed}
      </TableCell>
      <TableCell>
        <Typography variant="caption" color="text.secondary">
          {line.disagreements
            .map((one) => `${one.nameEn}: ${one.truth}→${one.detected}`)
            .join(", ")}
        </Typography>
      </TableCell>
    </TableRow>
  );
}

export function ScoreBoardTable({ board, onPickExample }: ScoreBoardTableProps) {
  const skipped = Object.entries(board.skipped);

  return (
    <Stack spacing={1.5}>
      {board.lines.length ? (
        <Box sx={{ overflowX: "auto" }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>example</TableCell>
                <TableCell align="right">d px</TableCell>
                <TableCell align="right">onsets found</TableCell>
                <TableCell align="right">invented</TableCell>
                <TableCell align="right">missed</TableCell>
                <TableCell align="right">sustains found</TableCell>
                <TableCell align="right">invented</TableCell>
                <TableCell align="right">missed</TableCell>
                <TableCell>keys that disagree</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              <Row line={board.total} total />
              {board.lines.map((line) => (
                <Row
                  key={`${line.slug}-${line.offsetPx}`}
                  line={line}
                  onPick={onPickExample ? () => onPickExample(line.slug) : undefined}
                />
              ))}
            </TableBody>
          </Table>
        </Box>
      ) : (
        <Alert severity="info" variant="outlined">
          Nothing to score yet. An example is scored once it has a calibration and at least one
          reading made by hand.
        </Alert>
      )}

      {skipped.length ? (
        <Box>
          <Typography variant="caption" color="text.secondary">
            Not scored, and why
          </Typography>
          <Stack spacing={0.25} sx={{ mt: 0.5 }}>
            {skipped.map(([slug, reason]) => (
              <Typography key={slug} variant="caption" color="text.secondary">
                <b>{slug}</b> — {reason}
              </Typography>
            ))}
          </Stack>
        </Box>
      ) : null}
    </Stack>
  );
}

export default ScoreBoardTable;
