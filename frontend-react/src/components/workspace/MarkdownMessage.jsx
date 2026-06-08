import { memo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Box,
  Typography,
  Link as MuiLink,
  Divider,
  Table,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
  TableContainer,
  Paper,
  alpha,
} from "@mui/material";

/**
 * Render assistant chat messages as GitHub-flavoured markdown with MUI
 * styling — headings, lists, tables, code blocks, blockquotes, and links
 * all themed to the current palette so the chat looks like a real document
 * preview instead of a wall of raw markdown.
 */
function MarkdownMessage({ children }) {
  return (
    <Box
      sx={{
        // Tight vertical rhythm — chat bubbles should still feel compact.
        "& > *:first-of-type": { mt: 0 },
        "& > *:last-of-type": { mb: 0 },
        wordBreak: "break-word",
      }}
    >
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {children || ""}
      </ReactMarkdown>
    </Box>
  );
}

const headingSx = (level) => ({
  fontWeight: 800,
  letterSpacing: "-0.01em",
  mt: level <= 2 ? 2 : 1.5,
  mb: 0.75,
  color: level <= 2 ? "primary.main" : "text.primary",
  fontSize:
    level === 1
      ? "1.2rem"
      : level === 2
        ? "1.08rem"
        : level === 3
          ? "0.98rem"
          : "0.92rem",
  lineHeight: 1.3,
  ...(level <= 2 && {
    pb: 0.4,
    borderBottom: 1,
    borderColor: (t) => alpha(t.palette.primary.main, 0.25),
  }),
});

const components = {
  h1: ({ node, ...props }) => (
    <Typography component="h3" sx={headingSx(1)} {...props} />
  ),
  h2: ({ node, ...props }) => (
    <Typography component="h4" sx={headingSx(2)} {...props} />
  ),
  h3: ({ node, ...props }) => (
    <Typography component="h5" sx={headingSx(3)} {...props} />
  ),
  h4: ({ node, ...props }) => (
    <Typography component="h6" sx={headingSx(4)} {...props} />
  ),
  h5: ({ node, ...props }) => (
    <Typography component="h6" sx={headingSx(4)} {...props} />
  ),
  h6: ({ node, ...props }) => (
    <Typography component="h6" sx={headingSx(4)} {...props} />
  ),

  p: ({ node, ...props }) => (
    <Typography
      component="p"
      sx={{
        my: 0.75,
        fontSize: "0.92rem",
        lineHeight: 1.6,
        color: "text.primary",
      }}
      {...props}
    />
  ),

  strong: ({ node, ...props }) => (
    <Box
      component="strong"
      sx={{ fontWeight: 700, color: "text.primary" }}
      {...props}
    />
  ),
  em: ({ node, ...props }) => (
    <Box component="em" sx={{ fontStyle: "italic" }} {...props} />
  ),

  a: ({ node, href, ...props }) => (
    <MuiLink
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      underline="hover"
      sx={{ fontWeight: 600 }}
      {...props}
    />
  ),

  ul: ({ node, ordered, ...props }) => (
    <Box
      component="ul"
      sx={{
        my: 0.75,
        pl: 2.5,
        "& li": { mb: 0.4 },
        "& li::marker": { color: "primary.main" },
      }}
      {...props}
    />
  ),
  ol: ({ node, ordered, ...props }) => (
    <Box
      component="ol"
      sx={{
        my: 0.75,
        pl: 2.5,
        "& li": { mb: 0.4 },
        "& li::marker": { color: "primary.main", fontWeight: 700 },
      }}
      {...props}
    />
  ),
  li: ({ node, ordered, checked, ...props }) => (
    <Box
      component="li"
      sx={{ fontSize: "0.92rem", lineHeight: 1.55 }}
      {...props}
    />
  ),

  blockquote: ({ node, ...props }) => (
    <Box
      component="blockquote"
      sx={{
        my: 1,
        mx: 0,
        pl: 1.5,
        py: 0.5,
        borderLeft: 3,
        borderColor: "primary.main",
        color: "text.secondary",
        fontStyle: "italic",
        bgcolor: (t) => alpha(t.palette.primary.main, 0.05),
        borderRadius: 1,
      }}
      {...props}
    />
  ),

  hr: () => <Divider sx={{ my: 1.5 }} />,

  code: ({ node, inline, className, children, ...props }) => {
    const isInline = inline ?? !String(children).includes("\n");
    if (isInline) {
      return (
        <Box
          component="code"
          sx={{
            fontFamily: '"JetBrains Mono", ui-monospace, monospace',
            fontSize: "0.85em",
            px: 0.6,
            py: 0.1,
            borderRadius: 0.75,
            bgcolor: (t) =>
              t.palette.mode === "dark"
                ? alpha(t.palette.common.white, 0.08)
                : alpha(t.palette.common.black, 0.06),
            color: "primary.main",
          }}
          {...props}
        >
          {children}
        </Box>
      );
    }
    return (
      <Box
        component="pre"
        sx={{
          fontFamily: '"JetBrains Mono", ui-monospace, monospace',
          fontSize: "0.82rem",
          lineHeight: 1.5,
          my: 1,
          p: 1.25,
          borderRadius: 1.5,
          overflowX: "auto",
          bgcolor: (t) =>
            t.palette.mode === "dark"
              ? alpha(t.palette.common.white, 0.06)
              : alpha(t.palette.common.black, 0.04),
          color: "text.primary",
          border: 1,
          borderColor: "divider",
        }}
      >
        <Box component="code" sx={{ fontFamily: "inherit" }} {...props}>
          {children}
        </Box>
      </Box>
    );
  },

  table: ({ node, ...props }) => (
    <TableContainer
      component={Paper}
      variant="outlined"
      sx={{ my: 1.25, borderRadius: 1.5 }}
    >
      <Table size="small" {...props} />
    </TableContainer>
  ),
  thead: ({ node, ...props }) => <TableHead {...props} />,
  tbody: ({ node, ...props }) => <TableBody {...props} />,
  tr: ({ node, ...props }) => (
    <TableRow
      sx={{
        "&:nth-of-type(even)": {
          bgcolor: (t) =>
            t.palette.mode === "dark"
              ? alpha(t.palette.common.white, 0.03)
              : alpha(t.palette.common.black, 0.02),
        },
      }}
      {...props}
    />
  ),
  th: ({ node, ...props }) => (
    <TableCell
      sx={{
        fontWeight: 700,
        color: "primary.contrastText",
        bgcolor: "primary.main",
        fontSize: "0.78rem",
        letterSpacing: "0.02em",
      }}
      {...props}
    />
  ),
  td: ({ node, ...props }) => (
    <TableCell sx={{ fontSize: "0.85rem", verticalAlign: "top" }} {...props} />
  ),
};

export default memo(MarkdownMessage);
