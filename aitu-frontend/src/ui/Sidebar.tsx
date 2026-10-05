/**
 * The left sidebar of the shell (plan section 6.2): the logo, **Search**, the sections of the app,
 * and the user menu at the bottom.
 *
 * Open, it is 260 px with words. Closed, it is 64 px with icons only, each with its name in a
 * tooltip. The button beside the logo switches between the two. The sections are given by the
 * layout; a section appears only once it is built.
 */

import type { ReactNode } from "react";
import Box from "@mui/material/Box";
import ButtonBase from "@mui/material/ButtonBase";
import Stack from "@mui/material/Stack";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import SearchIcon from "@mui/icons-material/Search";
import ViewSidebarIcon from "@mui/icons-material/ViewSidebarOutlined";
import { Link } from "react-router-dom";
import IconAction from "./IconAction";
import { radius, size } from "./tokens";

export interface SidebarItem {
  label: string;
  to: string;
  icon: ReactNode;
  /** True when the current page is under this item. */
  active: boolean;
  /** A count of things waiting for the user, beside the label. */
  count?: number;
}

export interface SidebarGroup {
  /** A small heading over the group ("My library"); none for the first group. */
  heading?: string;
  items: SidebarItem[];
}

export interface SidebarProps {
  open: boolean;
  onToggle: () => void;
  onSearch: () => void;
  groups: SidebarGroup[];
  /** Where the logo goes. */
  home: string;
  /** The user menu, at the bottom. */
  footer: ReactNode;
}

/** One row of the sidebar: an icon, and its words when the sidebar is open. */
function Row({
  open,
  label,
  icon,
  active,
  count,
  to,
  onClick,
  shortcut,
}: {
  open: boolean;
  label: string;
  icon: ReactNode;
  active?: boolean;
  count?: number;
  to?: string;
  onClick?: () => void;
  shortcut?: string;
}) {
  const body = (
    <ButtonBase
      {...(to ? { component: Link, to } : { onClick })}
      aria-current={active ? "page" : undefined}
      aria-label={open ? undefined : label}
      sx={(theme) => ({
        width: "100%",
        height: 36,
        px: 1.25,
        gap: 1.25,
        justifyContent: open ? "flex-start" : "center",
        borderRadius: `${radius.row}px`,
        color: (theme.vars ?? theme).palette.text.primary,
        fontSize: 14,
        fontWeight: active ? 600 : 400,
        backgroundColor: active ? (theme.vars ?? theme).palette.action.selected : "transparent",
        "&:hover": { backgroundColor: (theme.vars ?? theme).palette.action.hover },
        "&.Mui-focusVisible": { outline: `2px solid ${(theme.vars ?? theme).palette.text.primary}`, outlineOffset: -2 },
        "& svg": { fontSize: size.icon, color: (theme.vars ?? theme).palette.text.secondary, flexShrink: 0 },
      })}
    >
      {icon}
      {open ? (
        <>
          <Box component="span" sx={{ flex: 1, textAlign: "left", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
            {label}
          </Box>
          {shortcut ? (
            <Box component="span" sx={{ color: "text.disabled", fontSize: 12 }}>
              {shortcut}
            </Box>
          ) : null}
          {count ? (
            <Box component="span" sx={{ color: "text.secondary", fontSize: 13, fontVariantNumeric: "tabular-nums" }}>
              {count}
            </Box>
          ) : null}
        </>
      ) : null}
    </ButtonBase>
  );
  return open ? body : <Tooltip title={shortcut ? `${label} (${shortcut})` : label} placement="right">{body}</Tooltip>;
}

export function Sidebar({ open, onToggle, onSearch, groups, home, footer }: SidebarProps) {
  return (
    <Box
      component="nav"
      aria-label="Sections"
      sx={(theme) => ({
        width: open ? size.sidebar : size.sidebarClosed,
        flexShrink: 0,
        height: "100vh",
        position: "sticky",
        top: 0,
        display: "flex",
        flexDirection: "column",
        backgroundColor: (theme.vars ?? theme).palette.background.sidebar,
        borderRight: 1,
        borderColor: "divider",
        transition: "width 160ms ease",
        "@media (prefers-reduced-motion: reduce)": { transition: "none" },
        overflow: "hidden",
      })}
    >
      <Stack
        direction={open ? "row" : "column"}
        spacing={open ? 1 : 0.5}
        sx={{ alignItems: "center", px: 1.25, pt: 1.25, pb: 1, justifyContent: "space-between" }}
      >
        <Box
          component={Link}
          to={home}
          aria-label="AImpromptu, open Projects"
          sx={{ display: "flex", alignItems: "center", gap: 1, color: "text.primary", textDecoration: "none", px: 0.5, py: 0.5, borderRadius: 1 }}
        >
          <Box component="img" src="/favicon.svg" alt="" sx={{ width: 26, height: 26, display: "block" }} />
          {open ? (
            <Typography sx={{ fontWeight: 600, fontSize: 16, letterSpacing: "-0.01em" }}>AImpromptu</Typography>
          ) : null}
        </Box>
        <IconAction
          title={open ? "Close the sidebar" : "Open the sidebar"}
          icon={<ViewSidebarIcon fontSize="small" />}
          onClick={onToggle}
          placement="right"
        />
      </Stack>

      <Box sx={{ px: 1.25, pb: 1 }}>
        <Row open={open} label="Search" icon={<SearchIcon />} onClick={onSearch} shortcut="⌘K" />
      </Box>

      <Box sx={{ flex: 1, overflowY: "auto", px: 1.25 }}>
        {groups.map((group, index) => (
          <Box key={group.heading ?? index} sx={{ mb: 2 }}>
            {group.heading && open ? (
              <Typography variant="caption" color="text.secondary" sx={{ display: "block", px: 1.25, pb: 0.5, fontWeight: 500 }}>
                {group.heading}
              </Typography>
            ) : null}
            <Stack spacing={0.25}>
              {group.items.map((item) => (
                <Row key={item.to} open={open} {...item} />
              ))}
            </Stack>
          </Box>
        ))}
      </Box>

      <Box sx={{ borderTop: 1, borderColor: "divider", p: 1.25 }}>{footer}</Box>
    </Box>
  );
}

export default Sidebar;
