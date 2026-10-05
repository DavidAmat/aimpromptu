/**
 * A choice of one among 2 to 4 known options, drawn as one rounded group (plan section 7.4; the
 * guidelines' "pick one of 2 to 4 known options": a segmented control, not a dropdown).
 */

import type { ReactNode } from "react";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Tooltip from "@mui/material/Tooltip";

export interface SegmentedOption<T extends string> {
  value: T;
  /** The words on the segment. With an icon and no label, `tooltip` is required. */
  label?: string;
  icon?: ReactNode;
  tooltip?: string;
  disabled?: boolean;
}

export interface SegmentedProps<T extends string> {
  value: T;
  options: readonly SegmentedOption<T>[];
  onChange: (value: T) => void;
  /** What is being chosen, for a screen reader: "Source kind". */
  label: string;
  size?: "small" | "medium";
  disabled?: boolean;
}

export function Segmented<T extends string>({ value, options, onChange, label, size = "small", disabled }: SegmentedProps<T>) {
  return (
    <ToggleButtonGroup
      exclusive
      size={size}
      value={value}
      disabled={disabled}
      aria-label={label}
      onChange={(_event, next: T | null) => {
        if (next !== null) onChange(next);
      }}
    >
      {options.map((option) => {
        const button = (
          <ToggleButton
            key={option.value}
            value={option.value}
            disabled={option.disabled}
            aria-label={option.label ?? option.tooltip}
            sx={{ px: option.label ? 1.75 : 1, py: 0.5, gap: 0.75, lineHeight: 1.6 }}
          >
            {option.icon}
            {option.label}
          </ToggleButton>
        );
        return option.tooltip ? (
          <Tooltip key={option.value} title={option.tooltip}>
            {button}
          </Tooltip>
        ) : (
          button
        );
      })}
    </ToggleButtonGroup>
  );
}

export default Segmented;
