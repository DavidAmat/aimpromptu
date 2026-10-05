/**
 * `/dev/ui`: every shared component of `src/ui/` on one page, in development builds only
 * (implementation 02, Phase 1). It is where a component with no page yet (the table, the mini
 * piano, the figure picker) is seen working before a phase uses it, and where a change to the
 * tokens is looked at once for every component.
 */

import { useState } from "react";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import AddIcon from "@mui/icons-material/Add";
import UndoIcon from "@mui/icons-material/Undo";
import type { FigureName } from "../../api";
import { spanishNoteShort } from "../../music/noteNames";
import {
  ConfirmDialog,
  DataTable,
  EmptyState,
  FigurePicker,
  IconAction,
  ListRow,
  MiniPiano,
  PageBody,
  PageHeader,
  PillButton,
  Section,
  Segmented,
} from "../../ui";

interface Row {
  id: string;
  title: string;
  notes: number | null;
}

const ROWS: Row[] = Array.from({ length: 40 }, (_, index) => ({
  id: `row-${index}`,
  title: index === 3 ? "A title long enough to be truncated in its column, with the full value on hover" : `Song ${index + 1}`,
  notes: index % 7 === 0 ? null : (index * 37) % 900,
}));

export function UiGalleryPage() {
  const [key, setKey] = useState<number | null>(60);
  const [figure, setFigure] = useState<FigureName>("negra");
  const [kind, setKind] = useState<"audio" | "video">("audio");
  const [confirm, setConfirm] = useState(false);
  return (
    <PageBody>
      <PageHeader title="Shared components" actions={<PillButton kind="primary" startIcon={<AddIcon />}>Primary</PillButton>} />
      <Section title="Buttons">
        <Stack direction="row" spacing={1} sx={{ alignItems: "center", flexWrap: "wrap", rowGap: 1 }}>
          <PillButton kind="primary">Primary</PillButton>
          <PillButton>Secondary</PillButton>
          <PillButton kind="quiet">Quiet</PillButton>
          <PillButton busy>Busy</PillButton>
          <PillButton kind="danger" onClick={() => setConfirm(true)}>Delete</PillButton>
          <IconAction title="Undo" shortcut="⌘Z" icon={<UndoIcon fontSize="small" />} />
          <IconAction title="Undo" disabled disabledTitle="Nothing to undo" icon={<UndoIcon fontSize="small" />} />
          <Segmented label="Kind" value={kind} onChange={setKind} options={[{ value: "audio", label: "Audio" }, { value: "video", label: "Video" }]} />
        </Stack>
      </Section>
      <Section title="Mini piano">
        <MiniPiano label="Pick a key" value={key} onChange={setKey} />
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
          {key === null ? "–" : spanishNoteShort(key)}
        </Typography>
      </Section>
      <Section title="Figure picker">
        <FigurePicker label="Pick a figure" value={figure} onChange={setFigure} />
      </Section>
      <Section title="List">
        {ROWS.slice(0, 4).map((row) => (
          <ListRow key={row.id} title={row.title} status="Notes" meta="2 h ago" menu={[{ label: "Open", onClick: () => undefined }]} />
        ))}
      </Section>
      <Section title="Table">
        <DataTable
          rows={ROWS}
          rowKey={(row) => row.id}
          initialSort={{ key: "notes", direction: "desc" }}
          rowsPerPageOptions={[10, 25]}
          columns={[
            { key: "title", label: "Title", render: (row) => row.title, sortValue: (row) => row.title, width: 320 },
            { key: "notes", label: "Notes", align: "right", render: (row) => row.notes ?? "–", sortValue: (row) => row.notes },
          ]}
        />
      </Section>
      <Section title="Empty state">
        <EmptyState message="No projects yet" action={<PillButton kind="primary">New project</PillButton>} />
      </Section>
      <ConfirmDialog
        open={confirm}
        title="Delete 3 projects?"
        message="This cannot be undone."
        confirmLabel="Delete 3 projects"
        danger
        onConfirm={() => setConfirm(false)}
        onCancel={() => setConfirm(false)}
      />
    </PageBody>
  );
}

export default UiGalleryPage;
