import { Card, CardContent, Typography, Box, alpha } from "@mui/material";

export default function StatCard({ label, value, icon: Icon, color = "primary" }) {
  return (
    <Card elevation={0} sx={{ borderRadius: 3, height: "100%" }}>
      <CardContent sx={{ p: 2.25 }}>
        <Box sx={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
          <Box>
            <Typography
              variant="overline"
              sx={{
                color: "text.secondary",
                fontWeight: 700,
                letterSpacing: "0.06em",
                lineHeight: 1,
              }}
            >
              {label}
            </Typography>
            <Typography
              sx={{
                mt: 1,
                fontSize: "2rem",
                fontWeight: 800,
                color: `${color}.main`,
                letterSpacing: "-0.02em",
              }}
            >
              {value}
            </Typography>
          </Box>
          {Icon && (
            <Box
              sx={{
                width: 44,
                height: 44,
                borderRadius: 2,
                display: "grid",
                placeItems: "center",
                bgcolor: (t) => alpha(t.palette[color].main, 0.12),
                color: `${color}.main`,
              }}
            >
              <Icon />
            </Box>
          )}
        </Box>
      </CardContent>
    </Card>
  );
}
