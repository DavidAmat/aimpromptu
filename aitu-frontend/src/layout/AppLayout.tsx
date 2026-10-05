/**
 * The app's frame: the sidebar and the routed page (implementation 02, plan section 6.2).
 *
 * The sidebar shows the sections that exist: **Projects**, and **Lab** for the video reader. The
 * other sections of the plan (the libraries, Requests, Admin) appear in the phases that build them.
 * It is open on the list pages and closed inside a project, where the piano roll and the piano
 * sheet need the width; the reader's own choice holds until they move between the two kinds of page.
 *
 * `⌘K` (`Ctrl+K`) opens **Search** from anywhere.
 */

import { useEffect, useState } from "react";
import Box from "@mui/material/Box";
import ButtonBase from "@mui/material/ButtonBase";
import ListItemIcon from "@mui/material/ListItemIcon";
import ListItemText from "@mui/material/ListItemText";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import Typography from "@mui/material/Typography";
import useMediaQuery from "@mui/material/useMediaQuery";
import FolderIcon from "@mui/icons-material/FolderOutlined";
import KeyboardIcon from "@mui/icons-material/KeyboardOutlined";
import PersonIcon from "@mui/icons-material/PersonOutlined";
import ScienceIcon from "@mui/icons-material/ScienceOutlined";
import { Outlet, useLocation } from "react-router-dom";
import { AppShell, radius, Sidebar, type SidebarGroup } from "../ui";
import { ROUTES } from "./routes";
import SearchDialog from "./SearchDialog";
import ShortcutsDialog from "./ShortcutsDialog";

/** A project page (its steps, Notes Falling), where the sidebar starts closed. */
function areaOf(pathname: string): "project" | "list" {
  return /^\/projects\/(?!$)/.test(pathname) ? "project" : "list";
}

function UserMenu({ open }: { open: boolean }) {
  const [anchor, setAnchor] = useState<HTMLElement | null>(null);
  const [shortcuts, setShortcuts] = useState(false);
  return (
    <>
      <ButtonBase
        onClick={(event) => setAnchor(event.currentTarget)}
        aria-label="Account"
        sx={(theme) => ({
          width: "100%",
          height: 40,
          px: 1,
          gap: 1.25,
          justifyContent: open ? "flex-start" : "center",
          borderRadius: `${radius.row}px`,
          "&:hover": { backgroundColor: (theme.vars ?? theme).palette.action.hover },
        })}
      >
        <Box
          sx={{
            width: 26,
            height: 26,
            borderRadius: "50%",
            backgroundColor: "text.primary",
            color: "background.paper",
            display: "grid",
            placeItems: "center",
            flexShrink: 0,
          }}
        >
          <PersonIcon sx={{ fontSize: 16 }} />
        </Box>
        {open ? (
          <Typography noWrap sx={{ fontSize: 14 }}>
            Local user
          </Typography>
        ) : null}
      </ButtonBase>
      <Menu
        anchorEl={anchor}
        open={anchor !== null}
        onClose={() => setAnchor(null)}
        anchorOrigin={{ vertical: "top", horizontal: "left" }}
        transformOrigin={{ vertical: "bottom", horizontal: "left" }}
      >
        <MenuItem
          onClick={() => {
            setAnchor(null);
            setShortcuts(true);
          }}
        >
          <ListItemIcon>
            <KeyboardIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>Keyboard shortcuts</ListItemText>
        </MenuItem>
      </Menu>
      <ShortcutsDialog open={shortcuts} onClose={() => setShortcuts(false)} />
    </>
  );
}

export function AppLayout() {
  const { pathname } = useLocation();
  const area = areaOf(pathname);
  const narrow = useMediaQuery("(max-width:899px)");
  const [choice, setChoice] = useState<{ area: string; open: boolean } | null>(null);
  const [searching, setSearching] = useState(false);
  const open = !narrow && (choice?.area === area ? choice.open : area === "list");

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setSearching(true);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  const under = (prefix: string) => pathname === prefix || pathname.startsWith(`${prefix}/`);
  const groups: SidebarGroup[] = [
    { items: [{ label: "Projects", to: ROUTES.projects, icon: <FolderIcon />, active: under(ROUTES.projects) }] },
    { heading: "Admin", items: [{ label: "Lab", to: ROUTES.lab, icon: <ScienceIcon />, active: under(ROUTES.lab) }] },
  ];

  return (
    <AppShell
      sidebar={
        <Sidebar
          open={open}
          onToggle={() => setChoice({ area, open: !open })}
          onSearch={() => setSearching(true)}
          groups={groups}
          home={ROUTES.projects}
          footer={<UserMenu open={open} />}
        />
      }
    >
      <Outlet />
      <SearchDialog open={searching} onClose={() => setSearching(false)} />
    </AppShell>
  );
}

export default AppLayout;
