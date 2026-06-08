import { useRef, useState } from "react";
import {
  Box,
  Card,
  CardHeader,
  CardContent,
  Typography,
  Button,
  Stack,
  Divider,
  Alert,
  CircularProgress,
  Chip,
  IconButton,
  Tooltip,
  TextField,
  Link as MuiLink,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  alpha,
} from "@mui/material";
import CloudUploadOutlinedIcon from "@mui/icons-material/CloudUploadOutlined";
import RefreshIcon from "@mui/icons-material/Refresh";
import InsertDriveFileOutlinedIcon from "@mui/icons-material/InsertDriveFileOutlined";
import GitHubIcon from "@mui/icons-material/GitHub";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import { useSession } from "../contexts/SessionContext.jsx";

function formatBytes(n) {
  if (!n) return "—";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

export default function ClientDatabasePage() {
  const {
    kbDocs,
    kbLoading,
    loadKbDocs,
    uploadDocument,
    importGithubProject,
    deleteDocument,
  } = useSession();
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef(null);

  const [githubUrl, setGithubUrl] = useState("");
  const [importing, setImporting] = useState(false);

  // Delete-confirmation state. We keep the whole doc object so the dialog
  // can show the project name/filename and we don't need a second lookup.
  const [pendingDelete, setPendingDelete] = useState(null);
  const [deleting, setDeleting] = useState(false);

  const handleDeleteConfirm = async () => {
    if (!pendingDelete) return;
    setDeleting(true);
    setError("");
    setInfo("");
    try {
      await deleteDocument(pendingDelete.filename);
      setInfo(
        `Deleted ${pendingDelete.project_name || pendingDelete.filename}.`
      );
      setPendingDelete(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setDeleting(false);
    }
  };

  const handleFiles = async (file) => {
    if (!file) return;
    setUploading(true);
    setError("");
    setInfo("");
    try {
      const data = await uploadDocument(file);
      setInfo(`Uploaded ${data.filename}.`);
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  const handleGithubImport = async () => {
    const url = githubUrl.trim();
    if (!url) return;
    setImporting(true);
    setError("");
    setInfo("");
    try {
      const data = await importGithubProject(url);
      setInfo(`Imported ${data.filename}.`);
      setGithubUrl("");
    } catch (err) {
      setError(err.message);
    } finally {
      setImporting(false);
    }
  };

  return (
    <Box>
      <Box sx={{ mb: 2 }}>
        <Typography variant="h5" sx={{ fontWeight: 800, letterSpacing: "-0.01em" }}>
          Client Database
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Upload past proposals or import GitHub projects. Each gets an AI-generated summary and is indexed into the knowledge base for retrieval.
        </Typography>
      </Box>

      <Card elevation={0} sx={{ borderRadius: 3, mb: 2.5 }}>
        <CardContent sx={{ p: 3 }}>
          <Box
            onClick={() => fileInputRef.current?.click()}
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragOver(false);
              const file = e.dataTransfer.files?.[0];
              if (file) handleFiles(file);
            }}
            sx={{
              border: 2,
              borderStyle: "dashed",
              borderColor: dragOver ? "primary.main" : "divider",
              borderRadius: 3,
              py: 5,
              px: 3,
              display: "grid",
              placeItems: "center",
              gap: 1.5,
              cursor: "pointer",
              transition: "border-color .15s ease, background-color .15s ease",
              bgcolor: (t) =>
                dragOver
                  ? alpha(t.palette.primary.main, 0.06)
                  : "background.paper",
              "&:hover": {
                borderColor: "primary.main",
                bgcolor: (t) => alpha(t.palette.primary.main, 0.04),
              },
            }}
          >
            <CloudUploadOutlinedIcon sx={{ fontSize: 44, color: "primary.main" }} />
            <Typography sx={{ fontWeight: 700 }}>
              Drag & drop a file here, or click to browse
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Supported: .txt, .md, .json, .pdf, .docx
            </Typography>
            <input
              ref={fileInputRef}
              type="file"
              accept=".txt,.md,.json,.pdf,.docx"
              hidden
              onChange={(e) => handleFiles(e.target.files?.[0])}
            />
          </Box>

          <Stack direction="row" spacing={1.5} alignItems="center" sx={{ mt: 2 }}>
            <Button
              variant="contained"
              startIcon={uploading ? <CircularProgress size={14} color="inherit" /> : <CloudUploadOutlinedIcon />}
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
            >
              {uploading ? "Uploading..." : "Upload File"}
            </Button>
            <Tooltip title="Refresh">
              <span>
                <IconButton onClick={loadKbDocs} disabled={kbLoading || uploading}>
                  <RefreshIcon />
                </IconButton>
              </span>
            </Tooltip>
          </Stack>

          <Divider sx={{ my: 3 }}>OR</Divider>

          <Box>
            <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
              <GitHubIcon fontSize="small" />
              <Typography sx={{ fontWeight: 700 }}>Add a GitHub Project</Typography>
            </Stack>
            <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 1.5 }}>
              Paste a public repo URL. We fetch the project name, description, topics, and README from GitHub and index them for RAG.
            </Typography>
            <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
              <TextField
                fullWidth
                size="small"
                placeholder="https://github.com/owner/repo"
                value={githubUrl}
                onChange={(e) => setGithubUrl(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleGithubImport();
                }}
                disabled={importing}
              />
              <Button
                variant="contained"
                startIcon={importing ? <CircularProgress size={14} color="inherit" /> : <GitHubIcon />}
                onClick={handleGithubImport}
                disabled={importing || !githubUrl.trim()}
                sx={{ minWidth: 140 }}
              >
                {importing ? "Importing..." : "Import"}
              </Button>
            </Stack>
          </Box>

          {info && (
            <Alert severity="success" variant="outlined" sx={{ mt: 2 }}>
              {info}
            </Alert>
          )}
          {error && (
            <Alert severity="error" variant="outlined" sx={{ mt: 2 }}>
              {error}
            </Alert>
          )}
        </CardContent>
      </Card>

      <Card elevation={0} sx={{ borderRadius: 3 }}>
        <CardHeader
          title={<Typography sx={{ fontWeight: 800 }}>Past Proposals & Projects</Typography>}
          action={
            <Chip
              size="small"
              label={`${kbDocs.length} DOCUMENTS`}
              sx={{ fontWeight: 700, letterSpacing: "0.04em", color: "text.secondary" }}
            />
          }
        />
        <Divider />
        <CardContent>
          {kbLoading ? (
            <Box sx={{ display: "flex", alignItems: "center", gap: 1, p: 1 }}>
              <CircularProgress size={16} />
              <Typography color="text.secondary">Loading...</Typography>
            </Box>
          ) : kbDocs.length === 0 ? (
            <Typography color="text.secondary">
              No documents yet. Upload a file or import a GitHub project above.
            </Typography>
          ) : (
            <Stack spacing={1.5}>
              {kbDocs.map((d) => (
                <DocCard
                  key={d.relative_path}
                  doc={d}
                  onDelete={() => setPendingDelete(d)}
                />
              ))}
            </Stack>
          )}
        </CardContent>
      </Card>

      <Dialog
        open={Boolean(pendingDelete)}
        onClose={() => !deleting && setPendingDelete(null)}
      >
        <DialogTitle>Delete this document?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            {pendingDelete
              ? `"${
                  pendingDelete.project_name || pendingDelete.filename
                }" will be removed from your Client Database and re-indexed out of RAG retrieval. This cannot be undone.`
              : ""}
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => setPendingDelete(null)}
            disabled={deleting}
          >
            Cancel
          </Button>
          <Button
            color="error"
            variant="contained"
            onClick={handleDeleteConfirm}
            disabled={deleting}
            startIcon={
              deleting ? (
                <CircularProgress size={14} color="inherit" />
              ) : (
                <DeleteOutlineIcon />
              )
            }
          >
            {deleting ? "Deleting..." : "Delete"}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

function DocCard({ doc, onDelete }) {
  const isGithub = doc.source === "github";
  const title = isGithub && doc.project_name ? doc.project_name : doc.filename;
  return (
    <Card variant="outlined" sx={{ borderRadius: 2.5 }}>
      <CardContent>
        <Stack direction="row" spacing={1.5} alignItems="flex-start">
          <Box
            sx={{
              width: 40,
              height: 40,
              borderRadius: 1.5,
              display: "grid",
              placeItems: "center",
              color: isGithub ? "#fff" : "primary.main",
              bgcolor: (t) =>
                isGithub ? "#0f172a" : alpha(t.palette.primary.main, 0.1),
              flexShrink: 0,
            }}
          >
            {isGithub ? <GitHubIcon /> : <InsertDriveFileOutlinedIcon />}
          </Box>
          <Box sx={{ minWidth: 0, flex: 1 }}>
            <Stack
              direction="row"
              spacing={1}
              alignItems="center"
              sx={{ flexWrap: "wrap" }}
            >
              <Typography sx={{ fontWeight: 700 }} noWrap>
                {title}
              </Typography>
              {isGithub && (
                <Chip
                  size="small"
                  icon={<GitHubIcon sx={{ fontSize: 14 }} />}
                  label="GitHub"
                  sx={{ fontWeight: 700, height: 20 }}
                />
              )}
            </Stack>
            <Typography variant="caption" color="text.secondary">
              {(doc.uploaded_at || "").slice(0, 10)} ·{" "}
              {formatBytes(doc.size_bytes)}
              {!isGithub && doc.filename !== title ? ` · ${doc.filename}` : ""}
            </Typography>
            {isGithub && doc.github_url && (
              <Box sx={{ mt: 0.5 }}>
                <MuiLink
                  href={doc.github_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  underline="hover"
                  variant="caption"
                  sx={{ wordBreak: "break-all" }}
                >
                  {doc.github_url}
                </MuiLink>
              </Box>
            )}
            {isGithub && doc.topics && doc.topics.length > 0 && (
              <Stack
                direction="row"
                spacing={0.5}
                sx={{ flexWrap: "wrap", gap: 0.5, mt: 1 }}
              >
                {doc.topics.map((t) => (
                  <Chip
                    key={t}
                    size="small"
                    label={t}
                    sx={{ height: 20, fontSize: "0.7rem" }}
                  />
                ))}
              </Stack>
            )}
            <Typography
              variant="body2"
              color="text.secondary"
              sx={{ mt: 1, whiteSpace: "pre-wrap" }}
            >
              {doc.description}
            </Typography>
          </Box>
          {onDelete && (
            <Tooltip title="Delete from Client Database">
              <IconButton
                size="small"
                color="error"
                onClick={onDelete}
                sx={{ flexShrink: 0 }}
              >
                <DeleteOutlineIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          )}
        </Stack>
      </CardContent>
    </Card>
  );
}
