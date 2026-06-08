import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  MenuItem,
  Button,
  Stack,
  Alert,
  CircularProgress,
} from "@mui/material";
import SaveOutlinedIcon from "@mui/icons-material/SaveOutlined";
import PlayArrowRoundedIcon from "@mui/icons-material/PlayArrowRounded";
import TechStackInput from "./TechStackInput.jsx";
import { useSession } from "../../contexts/SessionContext.jsx";

const BUDGET_OPTIONS = [
  "",
  "<$5k",
  "$5k - $10k",
  "$10k - $25k",
  "$25k - $50k",
  "$50k+",
];

export default function ProjectForm() {
  const {
    intake,
    updateIntake,
    startSession,
    startingSession,
    status,
    sessionId,
  } = useSession();

  const set = (key) => (e) => updateIntake(key, e.target.value);

  return (
    <Card elevation={0} sx={{ borderRadius: 3 }}>
      <CardContent sx={{ p: { xs: 2.5, md: 3 } }}>
        <Stack spacing={2.25}>
          <Box>
            <Typography variant="h6" sx={{ fontWeight: 800 }}>
              Project Details
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Provide context so your AI assistant can craft the best proposal.
            </Typography>
          </Box>

          <TextField
            label="Client Name"
            placeholder="e.g. Acme Corp"
            fullWidth
            size="small"
            value={intake.client_name}
            onChange={set("client_name")}
          />

          <TextField
            label="Project Title *"
            placeholder="e.g. Cloud Migration Strategy"
            fullWidth
            required
            size="small"
            value={intake.job_title}
            onChange={set("job_title")}
          />

          <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
            <TextField
              select
              label="Budget Range"
              fullWidth
              size="small"
              value={intake.budget}
              onChange={set("budget")}
            >
              {BUDGET_OPTIONS.map((opt) => (
                <MenuItem key={opt || "none"} value={opt}>
                  {opt || "Select a range..."}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              label="Timeline"
              placeholder="e.g. 3 Months"
              fullWidth
              size="small"
              value={intake.timeline}
              onChange={set("timeline")}
            />
          </Stack>

          <TechStackInput
            value={intake.tech_stack}
            onChange={(v) => updateIntake("tech_stack", v)}
          />

          <TextField
            label="Job Description *"
            placeholder="Paste the job requirements or project brief here..."
            fullWidth
            required
            multiline
            minRows={5}
            size="small"
            value={intake.job_description}
            onChange={set("job_description")}
          />

          <TextField
            label="Deliverables"
            placeholder="List the key deliverables..."
            fullWidth
            multiline
            minRows={3}
            size="small"
            value={intake.deliverables}
            onChange={set("deliverables")}
          />

          <TextField
            label="Constraints"
            placeholder="Budget, timeline, technical limitations..."
            fullWidth
            multiline
            minRows={3}
            size="small"
            value={intake.constraints}
            onChange={set("constraints")}
          />

          <Button
            variant={sessionId ? "outlined" : "contained"}
            color="primary"
            size="large"
            startIcon={
              startingSession ? (
                <CircularProgress size={18} color="inherit" />
              ) : sessionId ? (
                <SaveOutlinedIcon />
              ) : (
                <PlayArrowRoundedIcon />
              )
            }
            disabled={startingSession}
            onClick={startSession}
            fullWidth
          >
            {startingSession
              ? "Starting..."
              : sessionId
                ? "Start New Session With These Details"
                : "Start Session"}
          </Button>

          {status.text && (
            <Alert
              severity={status.severity || "info"}
              variant="outlined"
              sx={{ borderRadius: 2 }}
            >
              {status.text}
            </Alert>
          )}
        </Stack>
      </CardContent>
    </Card>
  );
}
