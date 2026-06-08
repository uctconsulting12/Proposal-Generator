import { Box, alpha } from "@mui/material";

/**
 * Pure-CSS mock of how each PDF template will look. The real PDF is rendered
 * server-side by fpdf2; these previews exist so users can visually compare
 * styles without round-tripping to the backend.
 */
export default function TemplatePreview({
  templateId,
  accentColor = "#0f766e",
  width = 220,
  height = 300,
}) {
  const accent = accentColor || "#0f766e";

  if (templateId === "classic") {
    return <ClassicPreview accent={accent} width={width} height={height} />;
  }
  if (templateId === "bold") {
    return <BoldPreview accent={accent} width={width} height={height} />;
  }
  if (templateId === "technical") {
    return <TechnicalPreview accent={accent} width={width} height={height} />;
  }
  return <ModernPreview accent={accent} width={width} height={height} />;
}

function Page({ children, width, height, sx }) {
  return (
    <Box
      sx={{
        width,
        height,
        bgcolor: "#ffffff",
        color: "#0f1f23",
        borderRadius: 1,
        boxShadow: (t) =>
          t.palette.mode === "dark"
            ? "0 4px 16px rgba(0,0,0,0.45)"
            : "0 4px 16px rgba(15,31,35,0.12)",
        overflow: "hidden",
        position: "relative",
        fontFamily: "Inter, system-ui, sans-serif",
        ...sx,
      }}
    >
      {children}
    </Box>
  );
}

function Lines({ count = 4, width = "90%", color = "#cfd8dc", gap = 4, height = 4 }) {
  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: `${gap}px` }}>
      {Array.from({ length: count }).map((_, i) => (
        <Box
          key={i}
          sx={{
            width: i === count - 1 ? "60%" : width,
            height,
            borderRadius: 0.5,
            bgcolor: color,
          }}
        />
      ))}
    </Box>
  );
}

// ---------------- Modern ----------------
function ModernPreview({ accent, width, height }) {
  return (
    <Page width={width} height={height}>
      <Box sx={{ height: 22, bgcolor: accent, color: "#fff", display: "flex", alignItems: "center", px: 1.25, fontSize: 8, fontWeight: 700, letterSpacing: "0.1em" }}>
        PROJECT PROPOSAL
      </Box>
      <Box sx={{ p: 1.5 }}>
        <Box sx={{ display: "flex", alignItems: "flex-start", gap: 1 }}>
          <Box sx={{ width: 22, height: 22, borderRadius: 0.5, bgcolor: alpha(accent, 0.18), border: `1px solid ${accent}` }} />
          <Box sx={{ flex: 1 }}>
            <Box sx={{ height: 8, width: "85%", borderRadius: 0.5, bgcolor: "#1f3133", mb: 0.5 }} />
            <Box sx={{ height: 5, width: "60%", borderRadius: 0.5, bgcolor: "#748a92" }} />
          </Box>
        </Box>
        <Box sx={{ mt: 1.25 }}>
          <Lines count={3} />
        </Box>
        <Box sx={{ height: 1, bgcolor: accent, mt: 1.5, mb: 1.5, opacity: 0.4 }} />
        <Box sx={{ height: 6, width: "40%", borderRadius: 0.5, bgcolor: accent, mb: 0.75 }} />
        <Lines count={5} />
        <Box sx={{ mt: 1.5 }}>
          <Box sx={{ height: 6, width: "35%", borderRadius: 0.5, bgcolor: accent, mb: 0.75 }} />
          <Lines count={3} />
        </Box>
      </Box>
      <FooterBar accent={accent} />
    </Page>
  );
}

// ---------------- Classic ----------------
function ClassicPreview({ accent, width, height }) {
  return (
    <Page width={width} height={height} sx={{ fontFamily: '"Times New Roman", Georgia, serif' }}>
      <Box sx={{ pt: 3, display: "flex", flexDirection: "column", alignItems: "center", px: 1.5 }}>
        <Box sx={{ width: 18, height: 18, borderRadius: 0.5, bgcolor: alpha(accent, 0.18), border: `1px solid ${accent}`, mb: 1 }} />
        <Box sx={{ fontSize: 6, color: "#748a92", letterSpacing: "0.2em", mb: 0.75 }}>
          PROJECT PROPOSAL
        </Box>
        <Box sx={{ height: 9, width: "75%", borderRadius: 0.5, bgcolor: "#1f3133", mb: 0.5 }} />
        <Box sx={{ height: 9, width: "55%", borderRadius: 0.5, bgcolor: "#1f3133", mb: 1 }} />
        <Box sx={{ height: 2, width: 30, bgcolor: accent, mb: 1.25 }} />
        <Lines count={3} width="70%" color="#748a92" gap={3} height={3} />
        <Box sx={{ height: 1, width: "60%", bgcolor: "#cfd8dc", mt: 1.5, mb: 1.5 }} />
      </Box>
      <Box sx={{ px: 1.5 }}>
        <Box sx={{ height: 7, width: "35%", borderRadius: 0.5, bgcolor: "#1f3133", mb: 0.4 }} />
        <Box sx={{ height: 1.5, width: 20, bgcolor: accent, mb: 0.75 }} />
        <Lines count={4} />
        <Box sx={{ mt: 1.25 }}>
          <Box sx={{ height: 7, width: "30%", borderRadius: 0.5, bgcolor: "#1f3133", mb: 0.4 }} />
          <Box sx={{ height: 1.5, width: 20, bgcolor: accent, mb: 0.75 }} />
          <Lines count={3} />
        </Box>
      </Box>
      <FooterBar accent="#cfd8dc" />
    </Page>
  );
}

// ---------------- Bold ----------------
function BoldPreview({ accent, width, height }) {
  return (
    <Page width={width} height={height}>
      <Box
        sx={{
          height: "45%",
          bgcolor: accent,
          color: "#fff",
          p: 1.25,
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
        }}
      >
        <Box sx={{ width: 22, height: 22, bgcolor: "rgba(255,255,255,0.2)", borderRadius: 0.5 }} />
        <Box>
          <Box sx={{ fontSize: 6, letterSpacing: "0.15em", opacity: 0.85, mb: 0.5 }}>
            PROJECT PROPOSAL
          </Box>
          <Box sx={{ height: 14, width: "80%", borderRadius: 0.5, bgcolor: "rgba(255,255,255,0.95)", mb: 0.5 }} />
          <Box sx={{ height: 14, width: "55%", borderRadius: 0.5, bgcolor: "rgba(255,255,255,0.95)" }} />
        </Box>
      </Box>
      <Box sx={{ p: 1.5 }}>
        <Box sx={{ fontSize: 6, color: accent, fontWeight: 700, letterSpacing: "0.12em", mb: 0.5 }}>
          SECTION 01
        </Box>
        <Box sx={{ height: 9, width: "70%", borderRadius: 0.5, bgcolor: "#1f3133", mb: 1 }} />
        <Lines count={4} />
        <Box sx={{ mt: 1.25 }}>
          <Box sx={{ fontSize: 6, color: accent, fontWeight: 700, letterSpacing: "0.12em", mb: 0.5 }}>
            SECTION 02
          </Box>
          <Box sx={{ height: 9, width: "55%", borderRadius: 0.5, bgcolor: "#1f3133", mb: 1 }} />
          <Lines count={3} />
        </Box>
      </Box>
      <Box sx={{ position: "absolute", bottom: 4, left: 8, display: "flex", alignItems: "center", gap: 0.5 }}>
        <Box sx={{ width: 4, height: 4, bgcolor: accent }} />
        <Box sx={{ height: 4, width: 30, bgcolor: "#1f3133", borderRadius: 0.5 }} />
      </Box>
    </Page>
  );
}

// ---------------- Technical (UCT-style) ----------------
function TechnicalPreview({ accent, width, height }) {
  return (
    <Page width={width} height={height} sx={{ fontFamily: '"Times New Roman", Georgia, serif' }}>
      <Box sx={{ pt: 1.5, display: "flex", flexDirection: "column", alignItems: "center", px: 1.5 }}>
        {/* logo + brand block */}
        <Box sx={{ width: 18, height: 18, borderRadius: "50%", bgcolor: alpha(accent, 0.18), border: `1px solid ${accent}`, mb: 0.75 }} />
        <Box sx={{ height: 7, width: "55%", borderRadius: 0.5, bgcolor: accent, mb: 0.4 }} />
        <Box sx={{ height: 3, width: "40%", borderRadius: 0.5, bgcolor: "#cfd8dc", mb: 1 }} />
        {/* thick rule */}
        <Box sx={{ height: 1.5, width: "92%", bgcolor: accent, mb: 1.5 }} />
        {/* title */}
        <Box sx={{ height: 10, width: "85%", borderRadius: 0.5, bgcolor: accent, mb: 0.5 }} />
        <Box sx={{ height: 7, width: "60%", borderRadius: 0.5, bgcolor: alpha(accent, 0.55), mb: 1.25 }} />
        <Box sx={{ height: 1.5, width: "92%", bgcolor: accent, mb: 1.25 }} />
      </Box>
      {/* numbered section preview */}
      <Box sx={{ px: 1.5 }}>
        <Box sx={{ height: 7, width: "55%", borderRadius: 0.5, bgcolor: accent, mb: 0.4 }} />
        <Box sx={{ height: 0.8, width: "100%", bgcolor: accent, mb: 0.75, opacity: 0.6 }} />
        <Lines count={3} />
        {/* mini table mock */}
        <Box sx={{ mt: 1, border: "0.5px solid #cfd8dc", borderRadius: 0.5, overflow: "hidden" }}>
          <Box sx={{ display: "flex", bgcolor: accent }}>
            {[0, 1, 2].map((i) => (
              <Box key={i} sx={{ flex: 1, py: 0.4, px: 0.5, borderRight: i < 2 ? "0.5px solid rgba(255,255,255,0.5)" : "none" }}>
                <Box sx={{ height: 3, bgcolor: "rgba(255,255,255,0.95)", borderRadius: 0.3 }} />
              </Box>
            ))}
          </Box>
          {[0, 1, 2].map((row) => (
            <Box key={row} sx={{ display: "flex", bgcolor: row % 2 === 0 ? "#f5f8fb" : "#fff" }}>
              {[0, 1, 2].map((i) => (
                <Box key={i} sx={{ flex: 1, py: 0.5, px: 0.5 }}>
                  <Box sx={{ height: 2.5, bgcolor: "#cfd8dc", borderRadius: 0.3, width: i === 1 ? "85%" : "70%" }} />
                </Box>
              ))}
            </Box>
          ))}
        </Box>
      </Box>
      {/* centred footer */}
      <Box sx={{ position: "absolute", bottom: 6, left: 0, right: 0, textAlign: "center" }}>
        <Box sx={{ height: 3, width: 40, borderRadius: 0.3, bgcolor: accent, mx: "auto" }} />
      </Box>
    </Page>
  );
}

function FooterBar({ accent }) {
  return (
    <Box sx={{ position: "absolute", bottom: 6, left: 8, right: 8 }}>
      <Box sx={{ height: 1, bgcolor: accent, mb: 0.5, opacity: 0.7 }} />
      <Box sx={{ display: "flex", justifyContent: "space-between" }}>
        <Box sx={{ height: 4, width: 28, bgcolor: "#cfd8dc", borderRadius: 0.5 }} />
        <Box sx={{ height: 4, width: 14, bgcolor: "#cfd8dc", borderRadius: 0.5 }} />
      </Box>
    </Box>
  );
}
