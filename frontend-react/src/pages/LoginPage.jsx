import { useState } from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  Stack,
  Alert,
  IconButton,
  InputAdornment,
  Tooltip,
  CircularProgress,
} from "@mui/material";
import VisibilityIcon from "@mui/icons-material/Visibility";
import VisibilityOffIcon from "@mui/icons-material/VisibilityOff";
import LightModeOutlinedIcon from "@mui/icons-material/LightModeOutlined";
import DarkModeOutlinedIcon from "@mui/icons-material/DarkModeOutlined";
import BrandMark from "../components/layout/BrandMark.jsx";
import { useAuth } from "../contexts/AuthContext.jsx";
import { useThemeMode } from "../contexts/ThemeModeContext.jsx";

export default function LoginPage() {
  const { signin, signup } = useAuth();
  const { mode, toggleMode } = useThemeMode();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");

  const submit = async (which) => {
    if (!email.trim() || !password.trim()) {
      setError("Email and password are required.");
      return;
    }
    setLoading(true);
    setError("");
    setInfo("");
    try {
      if (which === "signup") {
        await signup(email.trim(), password);
        setInfo("Profile created.");
      } else {
        await signin(email.trim(), password);
        setInfo("Signed in.");
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const onKeyDown = (e) => {
    if (e.key === "Enter") submit("signin");
  };

  return (
    <Box
      sx={{
        minHeight: "100vh",
        display: "grid",
        placeItems: "center",
        p: 2,
        background: (t) =>
          t.palette.mode === "dark"
            ? "radial-gradient(1200px 600px at 20% -10%, rgba(20,184,166,0.12), transparent 60%), radial-gradient(900px 500px at 90% 110%, rgba(13,79,74,0.16), transparent 70%), #0b1418"
            : "radial-gradient(1200px 600px at 20% -10%, rgba(13,79,74,0.10), transparent 60%), radial-gradient(900px 500px at 90% 110%, rgba(20,184,166,0.10), transparent 70%), #f3f5f7",
      }}
    >
      <Box sx={{ position: "absolute", top: 16, right: 16 }}>
        <Tooltip title={mode === "dark" ? "Light mode" : "Dark mode"}>
          <IconButton onClick={toggleMode}>
            {mode === "dark" ? <LightModeOutlinedIcon /> : <DarkModeOutlinedIcon />}
          </IconButton>
        </Tooltip>
      </Box>

      <Card
        elevation={0}
        sx={{
          width: "100%",
          maxWidth: 440,
          borderRadius: 3,
          boxShadow: "0 24px 60px rgba(13, 31, 35, 0.18)",
        }}
      >
        <CardContent sx={{ p: { xs: 3, sm: 4 } }}>
          <Stack spacing={2.5}>
            <BrandMark size="lg" />
            <Box>
              <Typography variant="h5" sx={{ fontWeight: 800, color: "primary.main" }}>
                Welcome back
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Sign in to your workspace, or create a new account.
              </Typography>
            </Box>

            <TextField
              label="Email"
              type="email"
              fullWidth
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              onKeyDown={onKeyDown}
              size="small"
            />

            <TextField
              label="Password"
              type={showPw ? "text" : "password"}
              fullWidth
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              onKeyDown={onKeyDown}
              size="small"
              InputProps={{
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton
                      onClick={() => setShowPw((s) => !s)}
                      edge="end"
                      size="small"
                    >
                      {showPw ? <VisibilityOffIcon /> : <VisibilityIcon />}
                    </IconButton>
                  </InputAdornment>
                ),
              }}
            />

            <Stack direction="row" spacing={1.5}>
              <Button
                fullWidth
                variant="contained"
                onClick={() => submit("signin")}
                disabled={loading}
                size="large"
                startIcon={loading ? <CircularProgress size={16} color="inherit" /> : null}
              >
                Sign in
              </Button>
              <Button
                fullWidth
                variant="outlined"
                onClick={() => submit("signup")}
                disabled={loading}
                size="large"
              >
                Sign up
              </Button>
            </Stack>

            {info && (
              <Alert severity="success" variant="outlined">
                {info}
              </Alert>
            )}
            {error && (
              <Alert severity="error" variant="outlined">
                {error}
              </Alert>
            )}

            <Typography
              variant="caption"
              color="text.secondary"
              sx={{ textAlign: "center" }}
            >
              By continuing you agree to the workspace terms.
            </Typography>
          </Stack>
        </CardContent>
      </Card>
    </Box>
  );
}
