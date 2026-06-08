import { useEffect, useMemo, useRef, useState } from "react";
import {
  Box,
  Card,
  CardHeader,
  CardContent,
  Avatar,
  Typography,
  IconButton,
  InputBase,
  Button,
  Chip,
  Stack,
  alpha,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Divider,
  FormControlLabel,
  Switch,
  Link,
  Autocomplete,
  TextField,
} from "@mui/material";
import SendIcon from "@mui/icons-material/Send";
import SmartToyOutlinedIcon from "@mui/icons-material/SmartToyOutlined";
import PersonOutlineIcon from "@mui/icons-material/PersonOutline";
import WarningAmberOutlinedIcon from "@mui/icons-material/WarningAmberOutlined";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import LockOutlinedIcon from "@mui/icons-material/LockOutlined";
import LockOpenOutlinedIcon from "@mui/icons-material/LockOpenOutlined";
import PictureAsPdfOutlinedIcon from "@mui/icons-material/PictureAsPdfOutlined";
import BoltOutlinedIcon from "@mui/icons-material/BoltOutlined";
import HttpsOutlinedIcon from "@mui/icons-material/HttpsOutlined";
import GitHubIcon from "@mui/icons-material/GitHub";
import { useSession } from "../../contexts/SessionContext.jsx";
import ExportMenu from "./ExportMenu.jsx";
import MarkdownMessage from "./MarkdownMessage.jsx";

const STAGE_INFO = {
  questioning: {
    label: "Gathering Requirements",
    placeholder: "Answer the question to help shape the proposal...",
    step: "STEP 1 OF 3",
    color: "warning",
  },
  draft: {
    label: "Draft Review",
    placeholder:
      "Describe changes, or type 'approve' to generate the full proposal",
    step: "STEP 2 OF 3",
    color: "info",
  },
  final: {
    label: "Proposal Ready",
    placeholder: "Ask for a change or ask a question",
    step: "STEP 3 OF 3",
    color: "success",
  },
};

// Once a session is finalized the workflow is locked but the backend still
// answers questions about the proposal/intake context. Surface that as a
// dedicated "Q&A" status so the user knows they can keep asking.
const QA_INFO = {
  label: "Q&A Mode",
  placeholder: "Ask a question about this proposal...",
  step: "READ-ONLY Q&A",
  color: "default",
};

function MessageRow({ msg }) {
  const isUser = msg.role === "You";
  const isSystem = msg.role === "System";

  const bubbleSx = isSystem
    ? {
      bgcolor: (t) =>
        t.palette.mode === "dark" ? "#2a2410" : "#fff8e1",
      color: (t) => (t.palette.mode === "dark" ? "#f7d774" : "#5a4400"),
      borderColor: (t) =>
        t.palette.mode === "dark" ? "#5a4a18" : "#f3d27a",
    }
    : isUser
      ? {
        bgcolor: (t) =>
          t.palette.mode === "dark"
            ? alpha(t.palette.primary.main, 0.16)
            : alpha(t.palette.primary.main, 0.08),
        color: "text.primary",
        borderColor: (t) =>
          t.palette.mode === "dark"
            ? alpha(t.palette.primary.main, 0.35)
            : alpha(t.palette.primary.main, 0.25),
      }
      : {
        bgcolor: (t) =>
          t.palette.mode === "dark" ? "#143231" : "#effaf6",
        color: "text.primary",
        borderColor: (t) =>
          t.palette.mode === "dark"
            ? alpha(t.palette.primary.main, 0.3)
            : "rgba(13, 79, 74, 0.18)",
      };

  return (
    <Box
      sx={{
        display: "flex",
        gap: 1.25,
        justifyContent: isUser ? "flex-end" : "flex-start",
        alignItems: "flex-start",
      }}
    >
      {!isUser && (
        <Avatar
          sx={{
            width: 34,
            height: 34,
            bgcolor: isSystem
              ? "warning.main"
              : "linear-gradient(135deg,#0d4f4a,#14b8a6)",
            background: !isSystem
              ? "linear-gradient(135deg,#0d4f4a,#14b8a6)"
              : undefined,
          }}
        >
          {isSystem ? (
            <WarningAmberOutlinedIcon fontSize="small" />
          ) : (
            <SmartToyOutlinedIcon fontSize="small" />
          )}
        </Avatar>
      )}
      <Box
        sx={{
          maxWidth: isUser ? "78%" : "85%",
          px: 1.75,
          py: 1.25,
          border: 1,
          borderRadius: 2.5,
          lineHeight: 1.55,
          // User/system messages stay literal (no markdown rendering),
          // assistant messages are rendered as fancy markdown.
          ...(isUser || isSystem
            ? { whiteSpace: "pre-wrap", wordBreak: "break-word" }
            : { overflowWrap: "anywhere" }),
          ...bubbleSx,
        }}
      >
        {isUser || isSystem ? (
          msg.text
        ) : (
          <MarkdownMessage>{msg.text}</MarkdownMessage>
        )}
      </Box>
      {isUser && (
        <Avatar sx={{ width: 34, height: 34, bgcolor: "grey.700" }}>
          <PersonOutlineIcon fontSize="small" />
        </Avatar>
      )}
    </Box>
  );
}

export default function ChatPanel() {
  const {
    sessionId,
    stage,
    closed,
    messages,
    sending,
    sendMessage,
    finalizeSession,
    reopenSession,
    discardSession,
    downloadProposalPdf,
    retrievedSources,
    kbDocs,
  } = useSession();

  // Finalized sessions still accept messages — the backend treats them as
  // Q&A about the existing proposal. Use a dedicated status so users see
  // that the chat is still live, just locked from generating new drafts.
  const stageInfo = closed
    ? QA_INFO
    : STAGE_INFO[stage] || STAGE_INFO.questioning;
  const [draft, setDraft] = useState("");
  const [confirmFinalize, setConfirmFinalize] = useState(false);
  const streamRef = useRef(null);

  // Split the Client Database into two pools:
  //   * autoMatchedProjects — retrieved as RAG context for this session AND
  //     carry a GitHub URL. Default ON (the model already considers these
  //     similar so we surface them as the recommended attachments).
  //   * otherProjects — every other GitHub-backed doc the user owns. These
  //     feed the manual "add another project" Autocomplete below so the
  //     user can attach a portfolio match the RAG missed.
  const { autoMatchedProjects, otherProjects } = useMemo(() => {
    const retrievedSet = new Set(retrievedSources || []);
    const auto = [];
    const other = [];
    for (const d of kbDocs || []) {
      if (!d.github_url) continue;
      const entry = {
        key: d.relative_path,
        name: d.project_name || d.filename,
        url: d.github_url,
        description: d.description || "",
      };
      if (retrievedSet.has(d.relative_path)) auto.push(entry);
      else other.push(entry);
    }
    return { autoMatchedProjects: auto, otherProjects: other };
  }, [retrievedSources, kbDocs]);

  // Per-project toggle state for the auto-matched section. Default ON.
  const [includeLinks, setIncludeLinks] = useState({});
  // Manually-picked projects from the dropdown. These have no separate
  // toggle: presence in this list == "include in final proposal".
  const [manualPicks, setManualPicks] = useState([]);

  useEffect(() => {
    const next = {};
    for (const p of autoMatchedProjects) next[p.key] = true;
    setIncludeLinks(next);
    setManualPicks([]);
  }, [autoMatchedProjects]);

  // Available manual options = otherProjects minus anything already picked.
  // We rebuild the Autocomplete option list off this so a project can't be
  // attached twice.
  const manualPickKeys = new Set(manualPicks.map((p) => p.key));
  const manualOptions = otherProjects.filter((p) => !manualPickKeys.has(p.key));

  const includedProjects = [
    ...autoMatchedProjects.filter((p) => includeLinks[p.key]),
    ...manualPicks,
  ];
  const showAttachmentsPanel =
    autoMatchedProjects.length > 0 || otherProjects.length > 0;

  // Build the message body sent on Approve. When no projects are available
  // at all we keep the literal "approve" so the backend's approval detector
  // (fixed-word set) still matches.
  const buildApprovalMessage = () => {
    if (!showAttachmentsPanel) return "approve";
    if (includedProjects.length === 0) {
      return (
        "approve\n\n" +
        "[Instruction to assistant: do NOT include any GitHub repo URLs in " +
        "the final proposal. Reference past projects by name only.]"
      );
    }
    const bullets = includedProjects
      .map((p) => `- [${p.name}](${p.url})`)
      .join("\n");
    return (
      "approve\n\n" +
      "[Instruction to assistant: when citing any of the following past " +
      "projects in the final proposal, include its GitHub URL in markdown " +
      "link form the FIRST time the project is mentioned (e.g. in Section 3 " +
      "Portfolio Match). Do not invent URLs for projects not on this list. " +
      "Treat every project on this list as a deliberate user-attached " +
      "portfolio match — surface each one at least once.]\n" +
      bullets
    );
  };

  useEffect(() => {
    if (streamRef.current) {
      streamRef.current.scrollTop = streamRef.current.scrollHeight;
    }
  }, [messages]);

  const canSend = Boolean(sessionId) && !sending;
  const submit = async () => {
    const text = draft.trim();
    if (!text) return;
    setDraft("");
    await sendMessage(text);
  };

  return (
    <Card
      elevation={0}
      sx={{
        borderRadius: 3,
        display: "flex",
        flexDirection: "column",
        minHeight: 600,
      }}
    >
      <CardHeader
        sx={{ pb: 1.5 }}
        title={
          <Stack direction="row" alignItems="center" spacing={1.25}>
            <Box
              sx={{
                width: 10,
                height: 10,
                borderRadius: "50%",
                bgcolor: "primary.main",
                boxShadow: (t) =>
                  `0 0 0 4px ${alpha(t.palette.primary.main, 0.18)}`,
              }}
            />
            <Typography sx={{ fontWeight: 700 }}>
              Status:{" "}
              <Box component="span" sx={{ color: "primary.main" }}>
                {stageInfo.label}
              </Box>
            </Typography>
          </Stack>
        }
        action={
          <Stack direction="row" alignItems="center" spacing={1.25}>
            <Chip
              size="small"
              label={stageInfo.step}
              color={stageInfo.color}
              variant="outlined"
              sx={{ fontWeight: 700, letterSpacing: "0.04em" }}
            />
            {stage === "final" && sessionId ? (
              <ExportMenu
                onExport={({ template } = {}) =>
                  downloadProposalPdf({ template })
                }
              />
            ) : (
              <Tooltip title="Available once the proposal is finalized">
                <span>
                  <Button
                    size="small"
                    variant="outlined"
                    startIcon={<PictureAsPdfOutlinedIcon />}
                    disabled
                  >
                    Export
                  </Button>
                </span>
              </Tooltip>
            )}
          </Stack>
        }
      />
      <Divider />

      <CardContent
        sx={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          gap: 1.5,
          pt: 2,
        }}
      >
        <Box
          ref={streamRef}
          sx={{
            flex: 1,
            overflowY: "auto",
            display: "flex",
            flexDirection: "column",
            gap: 1.5,
            pr: 0.5,
            minHeight: 280,
            maxHeight: "60vh",
          }}
        >
          {messages.length === 0 ? (
            <MessageRow
              msg={{
                role: "Assistant",
                text:
                  "Hello! Fill in the project details on the left and click 'Start Session' to begin. I will create a draft proposal you can approve.",
              }}
            />
          ) : (
            messages.map((m, i) => <MessageRow key={i} msg={m} />)
          )}
        </Box>

        {stage === "draft" && !closed && sessionId && showAttachmentsPanel && (
          <Box
            sx={{
              border: 1,
              borderColor: "divider",
              borderRadius: 2.5,
              p: 1.5,
              bgcolor: (t) =>
                t.palette.mode === "dark"
                  ? alpha(t.palette.primary.main, 0.06)
                  : alpha(t.palette.primary.main, 0.04),
            }}
          >
            <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1 }}>
              <GitHubIcon fontSize="small" />
              <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                Attach projects to the final proposal
              </Typography>
            </Stack>

            {autoMatchedProjects.length > 0 && (
              <>
                <Typography
                  variant="caption"
                  color="text.secondary"
                  sx={{ display: "block", mb: 1 }}
                >
                  Closest matches from your Client Database — toggle off any
                  that don't fit.
                </Typography>
                <Stack spacing={0.5} sx={{ mb: otherProjects.length > 0 ? 1.5 : 0 }}>
                  {autoMatchedProjects.map((p) => (
                    <Stack
                      key={p.key}
                      direction="row"
                      alignItems="center"
                      justifyContent="space-between"
                      spacing={1}
                      sx={{ flexWrap: "wrap" }}
                    >
                      <FormControlLabel
                        sx={{ m: 0 }}
                        control={
                          <Switch
                            size="small"
                            checked={Boolean(includeLinks[p.key])}
                            onChange={(e) =>
                              setIncludeLinks((prev) => ({
                                ...prev,
                                [p.key]: e.target.checked,
                              }))
                            }
                          />
                        }
                        label={
                          <Typography variant="body2" sx={{ fontWeight: 600 }}>
                            {p.name}
                          </Typography>
                        }
                      />
                      <Link
                        href={p.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        variant="caption"
                        sx={{ overflowWrap: "anywhere" }}
                      >
                        {p.url}
                      </Link>
                    </Stack>
                  ))}
                </Stack>
              </>
            )}

            {otherProjects.length > 0 && (
              <>
                {autoMatchedProjects.length > 0 && <Divider sx={{ my: 1 }} />}
                <Typography
                  variant="caption"
                  color="text.secondary"
                  sx={{ display: "block", mb: 1 }}
                >
                  Add another project from your Client Database (these aren't
                  in the auto-retrieved set but you can attach them manually).
                </Typography>
                <Autocomplete
                  multiple
                  size="small"
                  options={manualOptions}
                  value={manualPicks}
                  onChange={(_e, value) => setManualPicks(value)}
                  isOptionEqualToValue={(opt, val) => opt.key === val.key}
                  getOptionLabel={(opt) => opt.name}
                  renderOption={(props, opt) => (
                    <li {...props} key={opt.key}>
                      <Box sx={{ minWidth: 0 }}>
                        <Typography variant="body2" sx={{ fontWeight: 600 }}>
                          {opt.name}
                        </Typography>
                        <Typography
                          variant="caption"
                          color="text.secondary"
                          sx={{ overflowWrap: "anywhere" }}
                        >
                          {opt.url}
                        </Typography>
                      </Box>
                    </li>
                  )}
                  renderTags={(value, getTagProps) =>
                    value.map((opt, index) => (
                      <Chip
                        {...getTagProps({ index })}
                        key={opt.key}
                        size="small"
                        icon={<GitHubIcon sx={{ fontSize: 14 }} />}
                        label={opt.name}
                        sx={{ fontWeight: 600 }}
                      />
                    ))
                  }
                  renderInput={(params) => (
                    <TextField
                      {...params}
                      placeholder={
                        manualPicks.length === 0
                          ? "Search projects to attach..."
                          : ""
                      }
                    />
                  )}
                />
              </>
            )}
          </Box>
        )}

        {stage === "draft" && !closed && sessionId && (
          <Button
            variant="contained"
            color="success"
            size="large"
            startIcon={<CheckCircleOutlineIcon />}
            disabled={!canSend}
            onClick={() => sendMessage(buildApprovalMessage())}
          >
            Approve & Generate Full Proposal
          </Button>
        )}

        {stage === "final" && sessionId && !closed && (
          <Button
            variant="outlined"
            startIcon={<LockOutlinedIcon />}
            onClick={() => setConfirmFinalize(true)}
          >
            Finalize Session (lock chat)
          </Button>
        )}

        {sessionId && closed && (
          <Button
            variant="outlined"
            color="primary"
            startIcon={<LockOpenOutlinedIcon />}
            onClick={reopenSession}
          >
            Reopen Session (resume editing)
          </Button>
        )}

        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            gap: 1,
            border: 1,
            borderColor: "divider",
            borderRadius: 2.5,
            bgcolor: (t) =>
              t.palette.mode === "dark"
                ? alpha(t.palette.common.white, 0.04)
                : alpha(t.palette.common.black, 0.03),
            px: 1.5,
            py: 0.5,
          }}
        >
          <InputBase
            sx={{ flex: 1, fontSize: "0.95rem", py: 0.5 }}
            value={draft}
            disabled={!sessionId}
            placeholder={
              sessionId ? stageInfo.placeholder : "Start a session first..."
            }
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                submit();
              }
            }}
            multiline
            maxRows={4}
          />
          <IconButton
            color="primary"
            disabled={!canSend || !draft.trim()}
            onClick={submit}
            sx={{
              bgcolor: "primary.main",
              color: "primary.contrastText",
              "&:hover": { bgcolor: "primary.dark" },
              "&.Mui-disabled": {
                bgcolor: (t) => alpha(t.palette.primary.main, 0.25),
                color: "primary.contrastText",
              },
              borderRadius: 2,
              width: 38,
              height: 38,
            }}
          >
            <SendIcon fontSize="small" />
          </IconButton>
        </Box>

        <Stack
          direction="row"
          spacing={2.5}
          justifyContent="center"
          sx={{ color: "text.secondary", fontSize: "0.8rem", pt: 0.5 }}
        >
          <Stack direction="row" alignItems="center" spacing={0.5}>
            <BoltOutlinedIcon fontSize="inherit" />
            <Typography variant="caption">AI Power: High</Typography>
          </Stack>
          <Stack direction="row" alignItems="center" spacing={0.5}>
            <HttpsOutlinedIcon fontSize="inherit" />
            <Typography variant="caption">Encrypted & Private</Typography>
          </Stack>
        </Stack>
      </CardContent>

      <Dialog open={confirmFinalize} onClose={() => setConfirmFinalize(false)}>
        <DialogTitle>Save this session?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Save & Lock keeps the proposal in your history and switches the
            chat to Q&A mode (you can reopen it later). Discard removes the
            session entirely — chat, intake and proposal are deleted and
            cannot be recovered.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmFinalize(false)}>Cancel</Button>
          <Button
            color="error"
            onClick={async () => {
              setConfirmFinalize(false);
              await discardSession();
            }}
          >
            Discard
          </Button>
          <Button
            variant="contained"
            color="primary"
            onClick={async () => {
              setConfirmFinalize(false);
              await finalizeSession();
            }}
          >
            Save & Lock
          </Button>
        </DialogActions>
      </Dialog>
    </Card>
  );
}
