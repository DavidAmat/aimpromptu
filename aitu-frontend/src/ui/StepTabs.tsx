/**
 * The steps of a project, in the order of the work, each with a small dot for its state (plan
 * section 10.2): filled when ready, a spinner while running, amber when out of date or unsaved,
 * an empty ring when not done yet.
 *
 * A step that cannot be opened yet is grey and does nothing when pressed; its tooltip says what is
 * missing ("Predict hands first."). It is not a disabled tab, because a disabled element receives
 * no pointer events and its tooltip would never show.
 */

import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import Tooltip from "@mui/material/Tooltip";
import { palette } from "./palette";
import { useScheme } from "./schemeContext";
import { ui } from "./tokens";

export type StepState = "ready" | "running" | "stale" | "missing";

export interface StepItem<K extends string> {
  key: K;
  label: string;
  state: StepState;
  enabled: boolean;
  /** Why the step cannot be opened, or what is wrong with it. */
  reason?: string | null;
}

const STATE_WORDS: Record<StepState, string> = {
  ready: "Done",
  running: "Running",
  stale: "Out of date",
  missing: "Not done yet",
};

function Dot({ state, unsaved }: { state: StepState; unsaved: boolean }) {
  useScheme();
  if (state === "running") return <CircularProgress size={9} thickness={6} sx={{ color: ui.text2 }} />;
  const amber = unsaved || state === "stale";
  const filled = unsaved || state !== "missing";
  return (
    <Box
      component="span"
      aria-hidden
      sx={{
        width: 7,
        height: 7,
        borderRadius: "50%",
        flexShrink: 0,
        border: `1.5px solid ${amber ? palette.dark.Orange : filled ? ui.text : ui.text3}`,
        backgroundColor: filled ? (amber ? palette.dark.Orange : ui.text) : "transparent",
      }}
    />
  );
}

export interface StepTabsProps<K extends string> {
  steps: readonly StepItem<K>[];
  current: K | null;
  onSelect: (step: K) => void;
  /** A step with unsaved changes: its dot is amber until they are saved. */
  unsaved?: K | null;
}

export function StepTabs<K extends string>({ steps, current, onSelect, unsaved = null }: StepTabsProps<K>) {
  return (
    <Tabs
      value={current ?? false}
      onChange={(_event, value: K) => {
        if (steps.find((step) => step.key === value)?.enabled) onSelect(value);
      }}
      variant="scrollable"
      scrollButtons={false}
      aria-label="Steps"
      sx={{ minHeight: 40, "& .MuiTabs-indicator": { height: 2 } }}
    >
      {steps.map((step) => {
        const pending = unsaved === step.key;
        const tip = pending ? "Unsaved changes" : (step.reason ?? STATE_WORDS[step.state]);
        return (
          <Tab
            key={step.key}
            value={step.key}
            aria-disabled={!step.enabled}
            disableRipple={!step.enabled}
            data-step={step.key}
            data-state={pending ? "unsaved" : step.state}
            label={
              <Tooltip title={tip} placement="bottom" describeChild>
                <Box component="span" sx={{ display: "inline-flex", alignItems: "center", gap: 0.75 }}>
                  <Dot state={step.state} unsaved={pending} />
                  {step.label}
                </Box>
              </Tooltip>
            }
            sx={step.enabled ? undefined : { color: "text.disabled", cursor: "not-allowed", "&.Mui-selected": { color: "text.disabled" } }}
          />
        );
      })}
    </Tabs>
  );
}

export default StepTabs;
