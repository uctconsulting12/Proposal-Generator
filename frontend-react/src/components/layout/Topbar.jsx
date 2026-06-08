import {
  AppBar,
  Toolbar,
  Box,
  IconButton,
  InputBase,
  Avatar,
  Tooltip,
  Menu,
  MenuItem,
  ListItemIcon,
  Divider,
  Typography,
  alpha,
  useTheme,
} from "@mui/material";
import MenuIcon from "@mui/icons-material/Menu";
import SearchIcon from "@mui/icons-material/Search";
import LightModeOutlinedIcon from "@mui/icons-material/LightModeOutlined";
import DarkModeOutlinedIcon from "@mui/icons-material/DarkModeOutlined";
import LogoutIcon from "@mui/icons-material/Logout";
import BusinessOutlinedIcon from "@mui/icons-material/BusinessOutlined";
import { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import BrandMark from "./BrandMark.jsx";
import { useThemeMode } from "../../contexts/ThemeModeContext.jsx";
import { useAuth } from "../../contexts/AuthContext.jsx";
import { useProfile } from "../../contexts/ProfileContext.jsx";

const NAV_LINKS = [
  { label: "Workspace", path: "/workspace" },
  { label: "Dashboard", path: "/dashboard" },
  { label: "Client Database", path: "/client-database" },
];

export default function Topbar({
  topbarHeight,
  searchTerm,
  onSearchChange,
  onMenuClick,
  isMobile,
}) {
  const theme = useTheme();
  const navigate = useNavigate();
  const location = useLocation();
  const { mode, toggleMode } = useThemeMode();
  const { user, logout } = useAuth();
  const { profile, logoUrl } = useProfile();
  const [anchorEl, setAnchorEl] = useState(null);
  const menuOpen = Boolean(anchorEl);
  const closeMenu = () => setAnchorEl(null);

  const goProfile = () => {
    closeMenu();
    navigate("/profile");
  };
  const doLogout = () => {
    closeMenu();
    logout();
  };

  const initial = (profile.company_name || user?.email || "?")
    .trim()
    .slice(0, 1)
    .toUpperCase();

  const isActive = (path) =>
    path === "/workspace"
      ? location.pathname === "/" || location.pathname === path
      : location.pathname === path;

  return (
    <AppBar
      position="fixed"
      elevation={0}
      sx={{
        height: topbarHeight,
        bgcolor: "background.paper",
        color: "text.primary",
        borderBottom: 1,
        borderColor: "divider",
        zIndex: theme.zIndex.drawer + 1,
      }}
    >
      <Toolbar sx={{ height: topbarHeight, gap: 2 }}>
        {isMobile && (
          <IconButton edge="start" onClick={onMenuClick} sx={{ mr: 0.5 }}>
            <MenuIcon />
          </IconButton>
        )}

        <BrandMark />

        {!isMobile && (
          <Box sx={{ display: "flex", alignItems: "center", gap: 0.5, ml: 3 }}>
            {NAV_LINKS.map((link) => (
              <Box
                key={link.path}
                onClick={() => navigate(link.path)}
                sx={{
                  cursor: "pointer",
                  px: 1.5,
                  py: 1,
                  fontWeight: 600,
                  fontSize: "0.9rem",
                  color: isActive(link.path) ? "primary.main" : "text.secondary",
                  borderBottom: 2,
                  borderColor: isActive(link.path)
                    ? "primary.main"
                    : "transparent",
                  transition: "color .15s ease, border-color .15s ease",
                  "&:hover": { color: "primary.main" },
                }}
              >
                {link.label}
              </Box>
            ))}
          </Box>
        )}

        <Box sx={{ flex: 1 }} />

        {!isMobile && (
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              gap: 1,
              px: 1.5,
              py: 0.5,
              bgcolor: (t) =>
                t.palette.mode === "dark"
                  ? alpha(t.palette.common.white, 0.04)
                  : alpha(t.palette.common.black, 0.04),
              border: 1,
              borderColor: "divider",
              borderRadius: 2,
              width: 280,
            }}
          >
            <SearchIcon fontSize="small" sx={{ color: "text.secondary" }} />
            <InputBase
              fullWidth
              value={searchTerm}
              onChange={(e) => onSearchChange(e.target.value)}
              placeholder="Search proposals..."
              sx={{ fontSize: "0.9rem" }}
            />
          </Box>
        )}

        <Tooltip title={mode === "dark" ? "Light mode" : "Dark mode"}>
          <IconButton onClick={toggleMode}>
            {mode === "dark" ? (
              <LightModeOutlinedIcon />
            ) : (
              <DarkModeOutlinedIcon />
            )}
          </IconButton>
        </Tooltip>

        <Tooltip title={profile.company_name || user?.email || "Account"}>
          <IconButton
            onClick={(e) => setAnchorEl(e.currentTarget)}
            sx={{ p: 0.25 }}
            aria-label="Open account menu"
          >
            <Avatar
              src={logoUrl || undefined}
              sx={{
                width: 36,
                height: 36,
                background:
                  "linear-gradient(135deg, #0d4f4a 0%, #14b8a6 100%)",
                fontWeight: 700,
                border: 2,
                borderColor: "background.paper",
                boxShadow: (t) =>
                  `0 0 0 1px ${alpha(t.palette.primary.main, 0.25)}`,
              }}
            >
              {initial}
            </Avatar>
          </IconButton>
        </Tooltip>

        <Menu
          anchorEl={anchorEl}
          open={menuOpen}
          onClose={closeMenu}
          anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
          transformOrigin={{ vertical: "top", horizontal: "right" }}
          slotProps={{
            paper: {
              elevation: 4,
              sx: {
                mt: 1,
                minWidth: 240,
                borderRadius: 2,
                border: 1,
                borderColor: "divider",
                overflow: "visible",
              },
            },
          }}
        >
          <Box sx={{ px: 2, py: 1.25 }}>
            <Typography sx={{ fontWeight: 700, lineHeight: 1.2 }} noWrap>
              {profile.company_name || "Your workspace"}
            </Typography>
            <Typography variant="caption" color="text.secondary" noWrap>
              {user?.email}
            </Typography>
          </Box>
          <Divider />
          <MenuItem onClick={goProfile}>
            <ListItemIcon>
              <BusinessOutlinedIcon fontSize="small" />
            </ListItemIcon>
            Company profile
          </MenuItem>
          <Divider />
          <MenuItem onClick={doLogout}>
            <ListItemIcon>
              <LogoutIcon fontSize="small" />
            </ListItemIcon>
            Sign out
          </MenuItem>
        </Menu>
      </Toolbar>
    </AppBar>
  );
}
