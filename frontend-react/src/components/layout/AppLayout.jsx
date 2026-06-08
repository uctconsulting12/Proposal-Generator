import { useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { Box, useMediaQuery, useTheme } from "@mui/material";
import Topbar from "./Topbar.jsx";
import Sidebar from "./Sidebar.jsx";
import { SessionProvider } from "../../contexts/SessionContext.jsx";
import { ProfileProvider } from "../../contexts/ProfileContext.jsx";

const SIDEBAR_WIDTH = 264;
const TOPBAR_HEIGHT = 64;

export default function AppLayout() {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("md"));
  const [mobileOpen, setMobileOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const location = useLocation();

  // Close drawer on navigation (mobile)
  const handleNavigate = () => {
    if (isMobile) setMobileOpen(false);
  };

  return (
    <ProfileProvider>
      <SessionProvider>
        <Box sx={{ minHeight: "100vh", bgcolor: "background.default" }}>
        <Topbar
          topbarHeight={TOPBAR_HEIGHT}
          sidebarWidth={SIDEBAR_WIDTH}
          searchTerm={searchTerm}
          onSearchChange={setSearchTerm}
          onMenuClick={() => setMobileOpen((o) => !o)}
          isMobile={isMobile}
        />
        <Sidebar
          width={SIDEBAR_WIDTH}
          topbarHeight={TOPBAR_HEIGHT}
          isMobile={isMobile}
          open={mobileOpen}
          onClose={() => setMobileOpen(false)}
          onNavigate={handleNavigate}
          currentPath={location.pathname}
        />
        <Box
          component="main"
          sx={{
            pt: `${TOPBAR_HEIGHT}px`,
            pl: { xs: 0, md: `${SIDEBAR_WIDTH}px` },
            minHeight: "100vh",
          }}
        >
          <Box sx={{ p: { xs: 2, md: 3 } }}>
            <Outlet context={{ searchTerm }} />
          </Box>
        </Box>
        </Box>
      </SessionProvider>
    </ProfileProvider>
  );
}
