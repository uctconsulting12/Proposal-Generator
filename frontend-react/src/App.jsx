import { Routes, Route, Navigate } from "react-router-dom";
import { Box, CircularProgress } from "@mui/material";
import AppLayout from "./components/layout/AppLayout.jsx";
import LoginPage from "./pages/LoginPage.jsx";
import WorkspacePage from "./pages/WorkspacePage.jsx";
import DashboardPage from "./pages/DashboardPage.jsx";
import ClientDatabasePage from "./pages/ClientDatabasePage.jsx";
import ProfilePage from "./pages/ProfilePage.jsx";
import { useAuth } from "./contexts/AuthContext.jsx";

function PrivateRoute({ children }) {
  const { user, bootstrapping } = useAuth();
  if (bootstrapping) {
    return (
      <Box sx={{ display: "grid", placeItems: "center", minHeight: "100vh" }}>
        <CircularProgress />
      </Box>
    );
  }
  return user ? children : <Navigate to="/login" replace />;
}

export default function App() {
  const { user } = useAuth();
  return (
    <Routes>
      <Route
        path="/login"
        element={user ? <Navigate to="/" replace /> : <LoginPage />}
      />
      <Route
        element={
          <PrivateRoute>
            <AppLayout />
          </PrivateRoute>
        }
      >
        <Route index element={<WorkspacePage />} />
        <Route path="/workspace" element={<WorkspacePage />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/client-database" element={<ClientDatabasePage />} />
        <Route path="/profile" element={<ProfilePage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
