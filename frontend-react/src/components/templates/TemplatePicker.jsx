import { useEffect, useState } from "react";
import {
  Box,
  Card,
  CardContent,
  CardHeader,
  Typography,
  Stack,
  Chip,
  Divider,
  CircularProgress,
  alpha,
} from "@mui/material";
import StyleOutlinedIcon from "@mui/icons-material/StyleOutlined";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import { templatesApi } from "../../api/templates.js";
import TemplatePreview from "./TemplatePreview.jsx";

export default function TemplatePicker({
  selectedId,
  onSelect,
  accentColor,
}) {
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    templatesApi
      .list()
      .then((data) => {
        if (cancelled) return;
        setTemplates(data.templates || []);
      })
      .catch((err) => !cancelled && setError(err.message))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <Card elevation={0} sx={{ borderRadius: 3 }}>
      <CardHeader
        avatar={<StyleOutlinedIcon color="primary" />}
        title={
          <Typography sx={{ fontWeight: 800 }}>Proposal Templates</Typography>
        }
        subheader="Pick the default layout used when you export a proposal as PDF. You can still override per-proposal from the Workspace."
      />
      <Divider />
      <CardContent>
        {loading ? (
          <Box sx={{ display: "flex", alignItems: "center", gap: 1, p: 1 }}>
            <CircularProgress size={16} />
            <Typography color="text.secondary">Loading templates...</Typography>
          </Box>
        ) : error ? (
          <Typography color="error">{error}</Typography>
        ) : (
          <Box
            sx={{
              display: "grid",
              gap: 2,
              gridTemplateColumns: {
                xs: "1fr",
                sm: "repeat(2, minmax(0,1fr))",
                lg: "repeat(3, minmax(0,1fr))",
              },
            }}
          >
            {templates.map((t) => {
              const isSelected = selectedId === t.id;
              return (
                <Box
                  key={t.id}
                  onClick={() => onSelect(t.id)}
                  sx={{
                    cursor: "pointer",
                    borderRadius: 2.5,
                    border: 2,
                    borderColor: isSelected ? "primary.main" : "divider",
                    p: 1.5,
                    bgcolor: (theme) =>
                      isSelected
                        ? alpha(theme.palette.primary.main, 0.05)
                        : "transparent",
                    transition: "border-color .15s, background-color .15s",
                    position: "relative",
                    "&:hover": {
                      borderColor: "primary.main",
                    },
                  }}
                >
                  {isSelected && (
                    <CheckCircleIcon
                      color="primary"
                      sx={{
                        position: "absolute",
                        top: 8,
                        right: 8,
                        zIndex: 1,
                      }}
                    />
                  )}
                  <Box
                    sx={{
                      display: "grid",
                      placeItems: "center",
                      bgcolor: (theme) =>
                        theme.palette.mode === "dark"
                          ? alpha(theme.palette.common.white, 0.04)
                          : alpha(theme.palette.common.black, 0.025),
                      borderRadius: 2,
                      py: 2,
                      mb: 1.5,
                    }}
                  >
                    <TemplatePreview
                      templateId={t.id}
                      accentColor={accentColor}
                      width={170}
                      height={230}
                    />
                  </Box>
                  <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 0.5 }}>
                    <Typography sx={{ fontWeight: 700 }}>{t.name}</Typography>
                    <Chip
                      label={t.tagline}
                      size="small"
                      color={isSelected ? "primary" : "default"}
                      variant="outlined"
                      sx={{ fontWeight: 600, fontSize: "0.65rem" }}
                    />
                  </Stack>
                  <Typography variant="caption" color="text.secondary">
                    {t.description}
                  </Typography>
                </Box>
              );
            })}
          </Box>
        )}
      </CardContent>
    </Card>
  );
}
