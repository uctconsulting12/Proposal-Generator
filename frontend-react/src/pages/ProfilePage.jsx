import { useEffect, useRef, useState } from "react";
import {
  Box,
  Card,
  CardContent,
  CardHeader,
  Typography,
  TextField,
  Button,
  Stack,
  Alert,
  Avatar,
  Divider,
  IconButton,
  CircularProgress,
  Tooltip,
  FormControlLabel,
  Switch,
  alpha,
} from "@mui/material";
import CloudUploadOutlinedIcon from "@mui/icons-material/CloudUploadOutlined";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import SaveOutlinedIcon from "@mui/icons-material/SaveOutlined";
import BusinessOutlinedIcon from "@mui/icons-material/BusinessOutlined";
import ColorLensOutlinedIcon from "@mui/icons-material/ColorLensOutlined";
import { useProfile } from "../contexts/ProfileContext.jsx";
import TemplatePicker from "../components/templates/TemplatePicker.jsx";

const PRESET_COLORS = [
  "#0f766e", "#0d4f4a", "#1d4ed8", "#7c3aed",
  "#db2777", "#ea580c", "#ca8a04", "#16a34a",
];

export default function ProfilePage() {
  const { profile, logoUrl, loading, save, uploadLogo, removeLogo } =
    useProfile();
  const [form, setForm] = useState(profile);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [status, setStatus] = useState({ text: "", severity: "info" });
  const fileInputRef = useRef(null);
  const [dragOver, setDragOver] = useState(false);

  useEffect(() => {
    setForm(profile);
  }, [profile]);

  const dirty =
    form.company_name !== profile.company_name ||
    form.company_intro !== profile.company_intro ||
    form.intro_verbatim !== profile.intro_verbatim ||
    form.signature !== profile.signature ||
    form.accent_color !== profile.accent_color ||
    form.template_id !== profile.template_id;

  const set = (key) => (e) => setForm((p) => ({ ...p, [key]: e.target.value }));

  const onSave = async () => {
    setSaving(true);
    setStatus({ text: "", severity: "info" });
    try {
      await save({
        company_name: form.company_name,
        company_intro: form.company_intro,
        intro_verbatim: form.intro_verbatim,
        signature: form.signature,
        accent_color: form.accent_color,
        template_id: form.template_id,
      });
      setStatus({ text: "Profile saved.", severity: "success" });
    } catch (err) {
      setStatus({ text: err.message, severity: "error" });
    } finally {
      setSaving(false);
    }
  };

  const onUpload = async (file) => {
    if (!file) return;
    setUploading(true);
    setStatus({ text: "", severity: "info" });
    try {
      await uploadLogo(file);
      setStatus({ text: "Logo updated.", severity: "success" });
    } catch (err) {
      setStatus({ text: err.message, severity: "error" });
    } finally {
      setUploading(false);
    }
  };

  const onRemoveLogo = async () => {
    setUploading(true);
    setStatus({ text: "", severity: "info" });
    try {
      await removeLogo();
      setStatus({ text: "Logo removed.", severity: "success" });
    } catch (err) {
      setStatus({ text: err.message, severity: "error" });
    } finally {
      setUploading(false);
    }
  };

  return (
    <Box sx={{ maxWidth: 920, mx: "auto" }}>
      <Box sx={{ mb: 2 }}>
        <Typography
          variant="h5"
          sx={{ fontWeight: 800, letterSpacing: "-0.01em" }}
        >
          Company Profile
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Your logo, intro and signature are used to brand every proposal —
          the cover, the AI's voice, and the PDF footer.
        </Typography>
      </Box>

      {status.text && (
        <Alert
          severity={status.severity}
          variant="outlined"
          sx={{ mb: 2 }}
          onClose={() => setStatus({ text: "", severity: "info" })}
        >
          {status.text}
        </Alert>
      )}

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" },
          gap: 2.5,
        }}
      >
        {/* ---------------- Logo ---------------- */}
        <Card elevation={0} sx={{ borderRadius: 3 }}>
          <CardHeader
            avatar={<BusinessOutlinedIcon color="primary" />}
            title={<Typography sx={{ fontWeight: 800 }}>Company Logo</Typography>}
            subheader="Shown on the proposal cover. PNG, JPG, WEBP or GIF. 2 MB max."
          />
          <Divider />
          <CardContent>
            <Stack alignItems="center" spacing={2}>
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
                  if (file) onUpload(file);
                }}
                sx={{
                  width: 200,
                  height: 200,
                  borderRadius: 3,
                  border: 2,
                  borderStyle: "dashed",
                  borderColor: dragOver ? "primary.main" : "divider",
                  display: "grid",
                  placeItems: "center",
                  cursor: "pointer",
                  bgcolor: (t) =>
                    dragOver
                      ? alpha(t.palette.primary.main, 0.06)
                      : alpha(t.palette.primary.main, 0.02),
                  position: "relative",
                  overflow: "hidden",
                  transition: "border-color .15s, background-color .15s",
                }}
              >
                {logoUrl ? (
                  <Box
                    component="img"
                    src={logoUrl}
                    alt="Company logo"
                    sx={{
                      maxWidth: "85%",
                      maxHeight: "85%",
                      objectFit: "contain",
                    }}
                  />
                ) : (
                  <Stack alignItems="center" spacing={0.5}>
                    <Avatar
                      sx={{
                        bgcolor: (t) => alpha(t.palette.primary.main, 0.12),
                        color: "primary.main",
                        width: 56,
                        height: 56,
                      }}
                    >
                      <CloudUploadOutlinedIcon />
                    </Avatar>
                    <Typography
                      variant="caption"
                      sx={{ fontWeight: 600 }}
                      color="text.secondary"
                    >
                      Click or drop image
                    </Typography>
                  </Stack>
                )}
              </Box>

              <input
                ref={fileInputRef}
                type="file"
                accept=".png,.jpg,.jpeg,.webp,.gif"
                hidden
                onChange={(e) => onUpload(e.target.files?.[0])}
              />

              <Stack direction="row" spacing={1}>
                <Button
                  variant="contained"
                  startIcon={
                    uploading ? (
                      <CircularProgress size={14} color="inherit" />
                    ) : (
                      <CloudUploadOutlinedIcon />
                    )
                  }
                  onClick={() => fileInputRef.current?.click()}
                  disabled={uploading || loading}
                >
                  {profile.has_logo ? "Replace" : "Upload"}
                </Button>
                {profile.has_logo && (
                  <Tooltip title="Remove logo">
                    <span>
                      <IconButton
                        color="error"
                        onClick={onRemoveLogo}
                        disabled={uploading || loading}
                      >
                        <DeleteOutlineIcon />
                      </IconButton>
                    </span>
                  </Tooltip>
                )}
              </Stack>
            </Stack>
          </CardContent>
        </Card>

        {/* ---------------- Brand accent ---------------- */}
        <Card elevation={0} sx={{ borderRadius: 3 }}>
          <CardHeader
            avatar={<ColorLensOutlinedIcon color="primary" />}
            title={<Typography sx={{ fontWeight: 800 }}>Brand Accent</Typography>}
            subheader="Colour for the PDF cover band, section headings and footer rule."
          />
          <Divider />
          <CardContent>
            <Stack spacing={2}>
              <Box
                sx={{
                  height: 90,
                  borderRadius: 2.5,
                  background: `linear-gradient(135deg, ${form.accent_color} 0%, ${shade(
                    form.accent_color,
                    -20
                  )} 100%)`,
                  border: 1,
                  borderColor: "divider",
                  display: "grid",
                  placeItems: "center",
                  color: "#fff",
                  fontWeight: 700,
                  letterSpacing: "0.04em",
                }}
              >
                PROJECT PROPOSAL
              </Box>

              <Stack direction="row" spacing={1.5} alignItems="center">
                <Box
                  component="input"
                  type="color"
                  value={form.accent_color}
                  onChange={(e) =>
                    setForm((p) => ({ ...p, accent_color: e.target.value }))
                  }
                  sx={{
                    width: 48,
                    height: 40,
                    border: 0,
                    bgcolor: "transparent",
                    cursor: "pointer",
                    p: 0,
                  }}
                />
                <TextField
                  size="small"
                  value={form.accent_color}
                  onChange={set("accent_color")}
                  inputProps={{
                    pattern: "^#[0-9a-fA-F]{6}$",
                    maxLength: 7,
                    style: { fontFamily: "monospace" },
                  }}
                  sx={{ width: 130 }}
                />
              </Stack>

              <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                {PRESET_COLORS.map((c) => (
                  <Box
                    key={c}
                    onClick={() =>
                      setForm((p) => ({ ...p, accent_color: c }))
                    }
                    sx={{
                      width: 28,
                      height: 28,
                      borderRadius: 1,
                      bgcolor: c,
                      cursor: "pointer",
                      border: 2,
                      borderColor:
                        form.accent_color.toLowerCase() === c.toLowerCase()
                          ? "primary.main"
                          : "transparent",
                      outline: "1px solid",
                      outlineColor: "divider",
                    }}
                  />
                ))}
              </Stack>
            </Stack>
          </CardContent>
        </Card>

        {/* ---------------- Templates (full width) ---------------- */}
        <Box sx={{ gridColumn: "1 / -1" }}>
          <TemplatePicker
            selectedId={form.template_id}
            accentColor={form.accent_color}
            onSelect={(id) => setForm((p) => ({ ...p, template_id: id }))}
          />
        </Box>

        {/* ---------------- Details (full width) ---------------- */}
        <Card elevation={0} sx={{ borderRadius: 3, gridColumn: "1 / -1" }}>
          <CardHeader
            title={<Typography sx={{ fontWeight: 800 }}>Details</Typography>}
            subheader="The intro doubles as voice/style context for the AI assistant."
          />
          <Divider />
          <CardContent>
            <Stack spacing={2}>
              <TextField
                label="Company Name"
                placeholder="e.g. XYZ Technologies"
                fullWidth
                size="small"
                value={form.company_name}
                onChange={set("company_name")}
                inputProps={{ maxLength: 200 }}
                helperText="Used on the PDF cover and footer."
              />
              <TextField
                label="Company Introduction"
                placeholder="A short paragraph about your company — services, scale, signature wins. The AI uses this to write proposals in your voice."
                fullWidth
                multiline
                minRows={4}
                value={form.company_intro}
                onChange={set("company_intro")}
                inputProps={{ maxLength: 2000 }}
                helperText={`${form.company_intro.length}/2000 characters`}
              />

              <Box
                sx={{
                  border: 1,
                  borderColor: "divider",
                  borderRadius: 2,
                  px: 1.75,
                  py: 1.25,
                  bgcolor: (t) =>
                    form.intro_verbatim
                      ? alpha(t.palette.primary.main, 0.04)
                      : "transparent",
                  transition: "background-color .15s",
                }}
              >
                <FormControlLabel
                  sx={{ alignItems: "flex-start", m: 0 }}
                  control={
                    <Switch
                      checked={Boolean(form.intro_verbatim)}
                      onChange={(e) =>
                        setForm((p) => ({
                          ...p,
                          intro_verbatim: e.target.checked,
                        }))
                      }
                      sx={{ mt: -0.25 }}
                    />
                  }
                  label={
                    <Box sx={{ ml: 1 }}>
                      <Typography sx={{ fontWeight: 700, fontSize: "0.92rem" }}>
                        Use the full intro verbatim
                      </Typography>
                      <Typography
                        variant="caption"
                        color="text.secondary"
                        sx={{ display: "block", mt: 0.25 }}
                      >
                        {form.intro_verbatim
                          ? "Your intro is printed word-for-word on the PDF cover and used as the About Us section."
                          : "Default. The AI condenses your intro into a clean 1-2 sentence About Us paragraph and the PDF cover stays focused on the title."}
                      </Typography>
                    </Box>
                  }
                />
              </Box>

              <TextField
                label="Proposal Signature"
                placeholder="e.g. XYZ Technologies .  [EMAIL ADRESS]"
                fullWidth
                size="small"
                value={form.signature}
                onChange={set("signature")}
                inputProps={{ maxLength: 200 }}
                helperText="Appended at the end of every PDF proposal."
              />

              <Stack
                direction="row"
                spacing={1.5}
                justifyContent="flex-end"
                sx={{ pt: 1 }}
              >
                <Button
                  variant="outlined"
                  onClick={() => setForm(profile)}
                  disabled={!dirty || saving}
                >
                  Discard
                </Button>
                <Button
                  variant="contained"
                  startIcon={
                    saving ? (
                      <CircularProgress size={14} color="inherit" />
                    ) : (
                      <SaveOutlinedIcon />
                    )
                  }
                  onClick={onSave}
                  disabled={!dirty || saving}
                >
                  Save Profile
                </Button>
              </Stack>
            </Stack>
          </CardContent>
        </Card>
      </Box>
    </Box>
  );
}

// Tiny hex shader for the preview gradient — keeps the page self-contained.
function shade(hex, percent) {
  const m = /^#?([a-f\d]{6})$/i.exec(hex);
  if (!m) return hex;
  const num = parseInt(m[1], 16);
  const r = Math.max(
    0,
    Math.min(255, (num >> 16) + Math.round((255 * percent) / 100))
  );
  const g = Math.max(
    0,
    Math.min(255, ((num >> 8) & 0xff) + Math.round((255 * percent) / 100))
  );
  const b = Math.max(
    0,
    Math.min(255, (num & 0xff) + Math.round((255 * percent) / 100))
  );
  return `#${((r << 16) | (g << 8) | b).toString(16).padStart(6, "0")}`;
}
