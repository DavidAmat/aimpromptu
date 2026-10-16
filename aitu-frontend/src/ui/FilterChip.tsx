/**
 * A filter of a list as one chip (implementation 02, Phase 13: the Public Library's decade, region,
 * genre and tag). The chip names the filter ("Decade"); a click opens its values, each with how
 * many rows it would leave, and the first entry takes the filter off. Chosen, the chip is filled
 * and says the value ("80s"), with a cross to take it off.
 *
 * A filter with no value to offer is not drawn by the page: an empty menu helps no one.
 */

import { useState } from "react";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import ListSubheader from "@mui/material/ListSubheader";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";

export interface FilterChipOption {
  value: string;
  label: string;
  count: number;
  /** A heading the option sits under in the menu (a tag's category). */
  group?: string | null;
}

export interface FilterChipProps {
  /** The filter's name: "Decade". */
  label: string;
  /** The first entry of the menu, which takes the filter off: "Any decade". */
  anyLabel: string;
  options: readonly FilterChipOption[];
  /** The chosen value, or `null`. */
  value: string | null;
  onChange: (value: string | null) => void;
  "data-testid"?: string;
}

export function FilterChip({ label, anyLabel, options, value, onChange, "data-testid": testId }: FilterChipProps) {
  const [anchor, setAnchor] = useState<HTMLElement | null>(null);
  const chosen = value === null ? null : options.find((one) => one.value === value);
  const pick = (next: string | null) => {
    setAnchor(null);
    onChange(next);
  };
  return (
    <>
      <Chip
        data-testid={testId}
        label={
          value !== null ? (
            (chosen?.label ?? value)
          ) : (
            <Box component="span" sx={{ display: "inline-flex", alignItems: "center", gap: 0.25 }}>
              {label}
              <ExpandMoreIcon sx={{ fontSize: 18, mr: -0.5 }} />
            </Box>
          )
        }
        aria-label={chosen ? `${label}: ${chosen.label}` : label}
        aria-haspopup="menu"
        variant={value !== null ? "filled" : "outlined"}
        color={value !== null ? "primary" : "default"}
        onClick={(event) => setAnchor(event.currentTarget)}
        onDelete={value !== null ? () => onChange(null) : undefined}
        sx={{ fontWeight: 500 }}
      />
      <Menu anchorEl={anchor} open={anchor !== null} onClose={() => setAnchor(null)} slotProps={{ paper: { sx: { maxHeight: 420 } } }}>
        <MenuItem selected={value === null} onClick={() => pick(null)}>
          {anyLabel}
        </MenuItem>
        {options.flatMap((option, index) => {
          const heading =
            option.group && option.group !== options[index - 1]?.group ? (
              <ListSubheader key={`group-${option.group}`} sx={{ lineHeight: "32px" }}>
                {option.group}
              </ListSubheader>
            ) : null;
          const item = (
            <MenuItem key={option.value} selected={option.value === value} onClick={() => pick(option.value)}>
              <Box component="span" sx={{ flex: 1, pr: 3 }}>
                {option.label}
              </Box>
              <Box component="span" sx={{ color: "text.secondary", fontVariantNumeric: "tabular-nums", fontSize: 13 }}>
                {option.count.toLocaleString("en")}
              </Box>
            </MenuItem>
          );
          return heading ? [heading, item] : [item];
        })}
      </Menu>
    </>
  );
}

export default FilterChip;
