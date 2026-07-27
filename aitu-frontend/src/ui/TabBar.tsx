/**
 * Router-aware tab strip. Given a list of `{ label, to }`, it highlights the
 * tab whose path prefixes the current location and navigates on click.
 * Used for the Playground tabs and any future sub-navigation.
 */

import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import { useLocation, useNavigate } from "react-router-dom";

export interface TabItem {
  label: string;
  /** Absolute route path, e.g. `/playground/matrix`. */
  to: string;
  disabled?: boolean;
}

export interface TabBarProps {
  items: TabItem[];
}

export function TabBar({ items }: TabBarProps) {
  const navigate = useNavigate();
  const { pathname } = useLocation();

  // Longest matching prefix wins, so `/library/play/x` selects `/library`.
  const active = items
    .filter((item) => pathname === item.to || pathname.startsWith(`${item.to}/`))
    .sort((a, b) => b.to.length - a.to.length)[0];

  return (
    <Tabs
      value={active?.to ?? false}
      onChange={(_, value: string) => navigate(value)}
      variant="scrollable"
      scrollButtons="auto"
      sx={{ borderBottom: 1, borderColor: "divider", minHeight: 44 }}
    >
      {items.map((item) => (
        <Tab key={item.to} label={item.label} value={item.to} disabled={item.disabled} />
      ))}
    </Tabs>
  );
}

export default TabBar;
