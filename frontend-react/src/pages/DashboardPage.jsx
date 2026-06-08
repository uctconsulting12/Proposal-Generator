import { useMemo } from "react";
import {
  Box,
  Card,
  CardHeader,
  CardContent,
  Typography,
  Chip,
  Stack,
  Button,
  Table,
  TableHead,
  TableRow,
  TableCell,
  TableBody,
  Select,
  MenuItem,
  Divider,
  TableContainer,
  IconButton,
  Tooltip,
} from "@mui/material";
import DescriptionOutlinedIcon from "@mui/icons-material/DescriptionOutlined";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import PendingActionsOutlinedIcon from "@mui/icons-material/PendingActionsOutlined";
import EmojiEventsOutlinedIcon from "@mui/icons-material/EmojiEventsOutlined";
import RefreshIcon from "@mui/icons-material/Refresh";
import { useNavigate, useOutletContext } from "react-router-dom";
import StatCard from "../components/common/StatCard.jsx";
import { useSession } from "../contexts/SessionContext.jsx";

const STAGE_COLOR = {
  questioning: "warning",
  draft: "info",
  final: "success",
};

export default function DashboardPage() {
  const navigate = useNavigate();
  const { searchTerm = "" } = useOutletContext() || {};
  const {
    history,
    historyLoading,
    loadHistory,
    outcomes,
    setOutcome,
    loadSession,
  } = useSession();

  const filtered = useMemo(() => {
    const term = searchTerm.trim().toLowerCase();
    if (!term) return history;
    return history.filter((s) =>
      (s.job_title || "").toLowerCase().includes(term)
    );
  }, [history, searchTerm]);

  const total = history.length;
  const finalCount = history.filter((s) => s.stage === "final").length;
  const draftCount = history.filter((s) => s.stage === "draft").length;
  const wonCount = history.filter((s) => outcomes[s.session_id] === "won").length;

  const openProposal = async (id) => {
    await loadSession(id);
    navigate("/workspace");
  };

  return (
    <Box>
      <Stack
        direction={{ xs: "column", sm: "row" }}
        justifyContent="space-between"
        alignItems={{ xs: "flex-start", sm: "center" }}
        spacing={1}
        sx={{ mb: 2 }}
      >
        <Box>
          <Typography variant="h5" sx={{ fontWeight: 800, letterSpacing: "-0.01em" }}>
            Dashboard
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Manage past proposals. Mark each as Won, Lost, or Pending to track performance.
          </Typography>
        </Box>
        <Tooltip title="Refresh">
          <IconButton onClick={loadHistory} disabled={historyLoading}>
            <RefreshIcon />
          </IconButton>
        </Tooltip>
      </Stack>

      <Box
        sx={{
          display: "grid",
          gap: 2,
          gridTemplateColumns: {
            xs: "1fr",
            sm: "repeat(2, minmax(0, 1fr))",
            md: "repeat(4, minmax(0, 1fr))",
          },
          mb: 3,
        }}
      >
        <StatCard
          label="Total Proposals"
          value={total}
          icon={DescriptionOutlinedIcon}
          color="primary"
        />
        <StatCard
          label="Finalized"
          value={finalCount}
          icon={CheckCircleOutlineIcon}
          color="primary"
        />
        <StatCard
          label="Drafts"
          value={draftCount}
          icon={PendingActionsOutlinedIcon}
          color="warning"
        />
        <StatCard
          label="Won (manual)"
          value={wonCount}
          icon={EmojiEventsOutlinedIcon}
          color="success"
        />
      </Box>

      <Card elevation={0} sx={{ borderRadius: 3 }}>
        <CardHeader
          title={
            <Typography sx={{ fontWeight: 800 }}>Proposal Performance</Typography>
          }
          action={
            <Chip
              size="small"
              label={`${total} TOTAL`}
              sx={{
                fontWeight: 700,
                letterSpacing: "0.04em",
                color: "text.secondary",
              }}
            />
          }
        />
        <Divider />
        <CardContent sx={{ p: 0 }}>
          {filtered.length === 0 ? (
            <Box sx={{ p: 3 }}>
              <Typography color="text.secondary">
                {history.length === 0
                  ? "No proposals yet. Create one from the Workspace to populate this table."
                  : "No proposals match your search."}
              </Typography>
            </Box>
          ) : (
            <TableContainer>
              <Table size="medium">
                <TableHead>
                  <TableRow>
                    <TableCell>
                      <strong>Project</strong>
                    </TableCell>
                    <TableCell>
                      <strong>Stage</strong>
                    </TableCell>
                    <TableCell>
                      <strong>Updated</strong>
                    </TableCell>
                    <TableCell>
                      <strong>Outcome</strong>
                    </TableCell>
                    <TableCell align="right" />
                  </TableRow>
                </TableHead>
                <TableBody>
                  {filtered.map((s) => {
                    const outcome = outcomes[s.session_id] || "pending";
                    return (
                      <TableRow hover key={s.session_id}>
                        <TableCell>
                          <Typography sx={{ fontWeight: 700 }}>
                            {s.job_title || "Untitled"}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Chip
                            size="small"
                            label={s.stage}
                            color={STAGE_COLOR[s.stage] || "default"}
                            variant="outlined"
                            sx={{ fontWeight: 700 }}
                          />
                        </TableCell>
                        <TableCell sx={{ color: "text.secondary" }}>
                          {(s.updated_at || "").slice(0, 10) || "—"}
                        </TableCell>
                        <TableCell>
                          <Select
                            size="small"
                            value={outcome}
                            onChange={(e) =>
                              setOutcome(s.session_id, e.target.value)
                            }
                            sx={{ minWidth: 120, borderRadius: 2 }}
                          >
                            <MenuItem value="pending">Pending</MenuItem>
                            <MenuItem value="won">Won</MenuItem>
                            <MenuItem value="lost">Lost</MenuItem>
                          </Select>
                        </TableCell>
                        <TableCell align="right">
                          <Button
                            size="small"
                            variant="outlined"
                            onClick={() => openProposal(s.session_id)}
                          >
                            Open
                          </Button>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </CardContent>
      </Card>
    </Box>
  );
}
