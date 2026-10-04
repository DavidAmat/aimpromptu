/**
 * The five tabs of the flow page, in the order of the work, each with the state of its step.
 *
 * A tab whose step cannot be opened yet is greyed and does nothing when pressed; hovering it says
 * what is missing ("Predict hands first."). It is not a disabled MUI tab, because a disabled
 * element receives no pointer events and its tooltip would never show.
 */

import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import Tooltip from "@mui/material/Tooltip";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import EditIcon from "@mui/icons-material/EditOutlined";
import RadioButtonUncheckedIcon from "@mui/icons-material/RadioButtonUnchecked";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import type { PieceStep, StepStatus } from "../../api";
import { STEP_LABELS } from "./stepLabels";

const STATE_WORDS: Record<StepStatus["state"], string> = {
  ready: "Ready.",
  running: "Running.",
  stale: "Out of date.",
  missing: "Not done yet.",
};

function StateIcon({ step, unsaved }: { step: StepStatus; unsaved: boolean }) {
  if (step.state === "running") return <CircularProgress size={14} />;
  // Changes not saved yet: the step is not done until Save, whatever the backend says.
  if (unsaved) return <EditIcon fontSize="small" color="warning" />;
  if (step.state === "ready") return <CheckCircleIcon fontSize="small" color="success" />;
  if (step.state === "stale") return <WarningAmberIcon fontSize="small" color="warning" />;
  return <RadioButtonUncheckedIcon fontSize="small" color="disabled" />;
}

export interface StepTabsProps {
  steps: StepStatus[];
  current: PieceStep | null;
  onSelect: (step: PieceStep) => void;
  /** A step with unsaved changes: its tick is replaced by a pencil until they are saved. */
  unsaved?: PieceStep | null;
}

export function StepTabs({ steps, current, onSelect, unsaved = null }: StepTabsProps) {
  return (
    <Tabs
      value={current ?? false}
      onChange={(_, value: PieceStep) => {
        if (steps.find((step) => step.step === value)?.enabled) onSelect(value);
      }}
      variant="scrollable"
      scrollButtons="auto"
      sx={{ borderBottom: 1, borderColor: "divider", minHeight: 48 }}
    >
      {steps.map((step, index) => {
        const pending = unsaved === step.step;
        const tip = pending ? "Unsaved changes: press Save to complete this step." : (step.reason ?? STATE_WORDS[step.state]);
        return (
          <Tab
            key={step.step}
            value={step.step}
            aria-disabled={!step.enabled}
            disableRipple={!step.enabled}
            iconPosition="start"
            icon={<StateIcon step={step} unsaved={pending} />}
            label={
              <Tooltip title={tip} placement="bottom" arrow describeChild>
                <Box component="span">{`${index + 1}. ${STEP_LABELS[step.step]}`}</Box>
              </Tooltip>
            }
            sx={{
              minHeight: 48,
              gap: 0.75,
              ...(step.enabled ? {} : { opacity: 0.45, cursor: "not-allowed" }),
            }}
          />
        );
      })}
    </Tabs>
  );
}

export default StepTabs;
