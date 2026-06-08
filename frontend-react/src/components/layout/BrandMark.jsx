import { Box, Typography } from "@mui/material";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";

export default function BrandMark({ size = "md", color = "primary.main" }) {
  const dim = size === "lg" ? 36 : 28;
  const font = size === "lg" ? "1.25rem" : "1.05rem";
  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
      <Box
        sx={{
          width: dim,
          height: dim,
          borderRadius: 1.5,
          background: "linear-gradient(135deg, #0d4f4a 0%, #14b8a6 100%)",
          display: "grid",
          placeItems: "center",
          color: "#fff",
          boxShadow: "0 4px 12px rgba(13, 79, 74, 0.25)",
        }}
      >
        <AutoAwesomeIcon sx={{ fontSize: dim * 0.55 }} />
      </Box>
      <Typography
        component="span"
        sx={{
          fontWeight: 800,
          fontSize: font,
          letterSpacing: "-0.01em",
          color,
        }}
      >
        ProposalPilot AI
      </Typography>
    </Box>
  );
}
