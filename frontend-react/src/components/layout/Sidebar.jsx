import {
  Box,
  Drawer,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Collapse,
  Typography,
  Button,
  Divider,
  CircularProgress,
  alpha,
} from "@mui/material";
import DashboardOutlinedIcon from "@mui/icons-material/DashboardOutlined";
import DescriptionOutlinedIcon from "@mui/icons-material/DescriptionOutlined";
import HistoryIcon from "@mui/icons-material/History";
import StorageOutlinedIcon from "@mui/icons-material/StorageOutlined";
import BusinessOutlinedIcon from "@mui/icons-material/BusinessOutlined";
import AddIcon from "@mui/icons-material/Add";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import { useNavigate } from "react-router-dom";
import { useState } from "react";
import { useAuth } from "../../contexts/AuthContext.jsx";
import { useSession } from "../../contexts/SessionContext.jsx";

const NAV_ITEMS = [
  { key: "dashboard", label: "Dashboard", path: "/dashboard", icon: DashboardOutlinedIcon },
  { key: "workspace", label: "Active Project", path: "/workspace", icon: DescriptionOutlinedIcon },
];

function SidebarContent({ width, onNavigate, currentPath }) {
  const navigate = useNavigate();
  const { user } = useAuth();
  const {
    history,
    historyLoading,
    loadHistory,
    loadSession,
    sessionId,
    resetWorkspace,
  } = useSession();
  const [historyOpen, setHistoryOpen] = useState(false);

  const go = (path) => {
    navigate(path);
    onNavigate?.();
  };

  const isActive = (path) =>
    path === "/workspace"
      ? currentPath === "/" || currentPath === path
      : currentPath === path;

  return (
    <Box
      sx={{
        width,
        p: 1.5,
        display: "flex",
        flexDirection: "column",
        gap: 1.5,
        height: "100%",
        overflowY: "auto",
      }}
    >
      <Box
        sx={{
          p: 1.5,
          borderRadius: 2,
          border: 1,
          borderColor: "divider",
          display: "flex",
          alignItems: "center",
          gap: 1.5,
          bgcolor: (t) =>
            t.palette.mode === "dark"
              ? alpha(t.palette.common.white, 0.03)
              : alpha(t.palette.common.black, 0.025),
        }}
      >
        <Box
          sx={{
            width: 38,
            height: 38,
            borderRadius: 1.5,
            background: "linear-gradient(135deg, #0d4f4a 0%, #14b8a6 100%)",
          }}
        />
        <Box sx={{ minWidth: 0 }}>
          <Typography sx={{ fontWeight: 700, fontSize: "0.92rem" }}>
            Workspace
          </Typography>
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{ display: "block", overflow: "hidden", textOverflow: "ellipsis" }}
          >
            {user?.email}
          </Typography>
        </Box>
      </Box>

      <Button
        fullWidth
        variant="contained"
        color="primary"
        startIcon={<AddIcon />}
        onClick={() => {
          resetWorkspace();
          go("/workspace");
        }}
        sx={{ py: 1.2 }}
      >
        New Proposal
      </Button>

      <List dense disablePadding>
        {NAV_ITEMS.map(({ key, label, path, icon: Icon }) => (
          <ListItemButton
            key={key}
            onClick={() => go(path)}
            selected={isActive(path)}
            sx={{
              borderRadius: 2,
              mb: 0.5,
              "&.Mui-selected": {
                bgcolor: (t) => alpha(t.palette.primary.main, 0.1),
                color: "primary.main",
                "& .MuiListItemIcon-root": { color: "primary.main" },
              },
            }}
          >
            <ListItemIcon sx={{ minWidth: 36 }}>
              <Icon fontSize="small" />
            </ListItemIcon>
            <ListItemText
              primaryTypographyProps={{ fontWeight: 600, fontSize: "0.9rem" }}
              primary={label}
            />
          </ListItemButton>
        ))}

        <ListItemButton
          onClick={() => {
            if (!historyOpen) loadHistory();
            setHistoryOpen((o) => !o);
          }}
          sx={{ borderRadius: 2, mb: 0.5 }}
        >
          <ListItemIcon sx={{ minWidth: 36 }}>
            <HistoryIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText
            primaryTypographyProps={{ fontWeight: 600, fontSize: "0.9rem" }}
            primary="Proposal History"
          />
          {historyOpen ? <ExpandLessIcon /> : <ExpandMoreIcon />}
        </ListItemButton>
        <Collapse in={historyOpen} unmountOnExit>
          <Box
            sx={{
              ml: 4,
              pl: 1,
              maxHeight: 240,
              overflowY: "auto",
              borderLeft: 1,
              borderColor: "divider",
            }}
          >
            {historyLoading ? (
              <Box sx={{ display: "flex", alignItems: "center", gap: 1, p: 1 }}>
                <CircularProgress size={14} />
                <Typography variant="caption" color="text.secondary">
                  Loading...
                </Typography>
              </Box>
            ) : history.length === 0 ? (
              <Typography variant="caption" color="text.secondary" sx={{ p: 1, display: "block" }}>
                No proposals yet.
              </Typography>
            ) : (
              history.map((s) => (
                <ListItemButton
                  key={s.session_id}
                  selected={s.session_id === sessionId}
                  onClick={() =>
                    loadSession(s.session_id).then(() => go("/workspace"))
                  }
                  sx={{
                    borderRadius: 1.5,
                    py: 0.5,
                    "&.Mui-selected": { color: "primary.main", fontWeight: 700 },
                  }}
                >
                  <ListItemText
                    primaryTypographyProps={{
                      fontSize: "0.82rem",
                      noWrap: true,
                    }}
                    secondaryTypographyProps={{
                      fontSize: "0.7rem",
                      textTransform: "uppercase",
                      letterSpacing: "0.04em",
                    }}
                    primary={s.job_title || "Untitled"}
                    secondary={s.stage}
                  />
                </ListItemButton>
              ))
            )}
          </Box>
        </Collapse>

        <ListItemButton
          onClick={() => go("/client-database")}
          selected={isActive("/client-database")}
          sx={{
            borderRadius: 2,
            mb: 0.5,
            "&.Mui-selected": {
              bgcolor: (t) => alpha(t.palette.primary.main, 0.1),
              color: "primary.main",
              "& .MuiListItemIcon-root": { color: "primary.main" },
            },
          }}
        >
          <ListItemIcon sx={{ minWidth: 36 }}>
            <StorageOutlinedIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText
            primaryTypographyProps={{ fontWeight: 600, fontSize: "0.9rem" }}
            primary="Client Database"
          />
        </ListItemButton>

        <ListItemButton
          onClick={() => go("/profile")}
          selected={isActive("/profile")}
          sx={{
            borderRadius: 2,
            mb: 0.5,
            "&.Mui-selected": {
              bgcolor: (t) => alpha(t.palette.primary.main, 0.1),
              color: "primary.main",
              "& .MuiListItemIcon-root": { color: "primary.main" },
            },
          }}
        >
          <ListItemIcon sx={{ minWidth: 36 }}>
            <BusinessOutlinedIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText
            primaryTypographyProps={{ fontWeight: 600, fontSize: "0.9rem" }}
            primary="Company Profile"
          />
        </ListItemButton>
      </List>

      <Box sx={{ flex: 1 }} />

      <Divider sx={{ my: 1 }} />
      <Typography
        variant="caption"
        color="text.secondary"
        sx={{ textAlign: "center", display: "block", pb: 1 }}
      >
        ProposalPilot v1.0
      </Typography>
    </Box>
  );
}

export default function Sidebar({
  width,
  topbarHeight,
  isMobile,
  open,
  onClose,
  onNavigate,
  currentPath,
}) {
  if (isMobile) {
    return (
      <Drawer
        variant="temporary"
        open={open}
        onClose={onClose}
        ModalProps={{ keepMounted: true }}
        sx={{
          "& .MuiDrawer-paper": {
            width,
            borderRight: 1,
            borderColor: "divider",
            top: `${topbarHeight}px`,
            height: `calc(100% - ${topbarHeight}px)`,
          },
        }}
      >
        <SidebarContent
          width={width}
          onNavigate={onNavigate}
          currentPath={currentPath}
        />
      </Drawer>
    );
  }

  return (
    <Drawer
      variant="permanent"
      sx={{
        width,
        flexShrink: 0,
        "& .MuiDrawer-paper": {
          width,
          boxSizing: "border-box",
          borderRight: 1,
          borderColor: "divider",
          bgcolor: "background.paper",
          top: `${topbarHeight}px`,
          height: `calc(100% - ${topbarHeight}px)`,
        },
      }}
    >
      <SidebarContent width={width} onNavigate={onNavigate} currentPath={currentPath} />
    </Drawer>
  );
}
