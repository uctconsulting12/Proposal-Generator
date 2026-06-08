import { createTheme } from "@mui/material/styles";

const BRAND = "#0d4f4a";
const BRAND_DARK = "#093a37";
const ACCENT = "#0f766e";
const ACCENT_BRIGHT = "#14b8a6";

const sharedTypography = {
  fontFamily:
    '"Inter","Plus Jakarta Sans","Segoe UI",Roboto,Tahoma,sans-serif',
  fontSize: 14,
  h1: { fontWeight: 800, letterSpacing: "-0.02em" },
  h2: { fontWeight: 800, letterSpacing: "-0.015em" },
  h3: { fontWeight: 700, letterSpacing: "-0.01em" },
  h4: { fontWeight: 700 },
  h5: { fontWeight: 700 },
  h6: { fontWeight: 700 },
  button: { textTransform: "none", fontWeight: 700, letterSpacing: 0 },
  subtitle2: { fontWeight: 600 },
};

const baseShape = { borderRadius: 12 };

const componentOverrides = (mode) => ({
  MuiCssBaseline: {
    styleOverrides: {
      body: {
        scrollbarColor:
          mode === "dark" ? "#3a4e52 #11201f" : "#cfd8dc #f3f5f7",
      },
      "::-webkit-scrollbar": { width: 10, height: 10 },
      "::-webkit-scrollbar-thumb": {
        background: mode === "dark" ? "#3a4e52" : "#cfd8dc",
        borderRadius: 6,
      },
    },
  },
  MuiButton: {
    defaultProps: { disableElevation: true },
    styleOverrides: {
      root: { borderRadius: 10, paddingInline: 16, paddingBlock: 9 },
      containedPrimary: {
        background: `linear-gradient(135deg, ${BRAND} 0%, ${BRAND_DARK} 100%)`,
        "&:hover": {
          background: `linear-gradient(135deg, ${BRAND_DARK} 0%, ${BRAND} 100%)`,
          filter: "brightness(1.05)",
        },
      },
    },
  },
  MuiPaper: {
    styleOverrides: {
      root: {
        backgroundImage: "none",
      },
    },
  },
  MuiCard: {
    styleOverrides: {
      root: {
        borderRadius: 14,
        border: `1px solid ${mode === "dark" ? "#1f3133" : "#e3e8eb"}`,
      },
    },
  },
  MuiOutlinedInput: {
    styleOverrides: {
      root: {
        borderRadius: 10,
      },
    },
  },
  MuiAppBar: {
    styleOverrides: {
      root: {
        backgroundImage: "none",
      },
    },
  },
  MuiChip: {
    styleOverrides: {
      root: { borderRadius: 8, fontWeight: 600 },
    },
  },
  MuiTooltip: {
    styleOverrides: {
      tooltip: { fontSize: 12, borderRadius: 6 },
    },
  },
});

export const buildTheme = (mode = "light") =>
  createTheme({
    shape: baseShape,
    typography: sharedTypography,
    palette:
      mode === "dark"
        ? {
            mode: "dark",
            primary: { main: ACCENT_BRIGHT, dark: ACCENT, contrastText: "#0b1418" },
            secondary: { main: "#94e1d4" },
            background: { default: "#0b1418", paper: "#11201f" },
            divider: "#1f3133",
            text: { primary: "#e8eef0", secondary: "#b8c7cc" },
            success: { main: "#22c55e" },
            warning: { main: "#f59e0b" },
            error: { main: "#ef4444" },
          }
        : {
            mode: "light",
            primary: { main: BRAND, dark: BRAND_DARK, contrastText: "#ffffff" },
            secondary: { main: ACCENT },
            background: { default: "#f3f5f7", paper: "#ffffff" },
            divider: "#e3e8eb",
            text: { primary: "#0f1f23", secondary: "#41545b" },
            success: { main: "#15803d" },
            warning: { main: "#b45309" },
            error: { main: "#b91c1c" },
          },
    components: componentOverrides(mode),
  });

export const brandColors = { BRAND, BRAND_DARK, ACCENT, ACCENT_BRIGHT };
