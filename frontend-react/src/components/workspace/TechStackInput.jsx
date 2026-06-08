import { useMemo, useState } from "react";
import { Box, Chip, InputBase, Typography } from "@mui/material";

export default function TechStackInput({ value, onChange }) {
  const [draft, setDraft] = useState("");

  const list = useMemo(
    () =>
      (value || "")
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean),
    [value]
  );

  const commit = (next) => onChange(next.join(", "));

  const addTech = (raw) => {
    const v = raw.trim().replace(/,$/, "");
    if (!v) return;
    commit([...list, v]);
    setDraft("");
  };

  const removeTech = (idx) => commit(list.filter((_, i) => i !== idx));

  return (
    <Box>
      <Typography
        variant="caption"
        sx={{ fontWeight: 600, color: "text.secondary", display: "block", mb: 0.75 }}
      >
        Tech Stack
      </Typography>
      <Box
        sx={{
          minHeight: 48,
          borderRadius: 2.5,
          border: 1,
          borderColor: "divider",
          px: 1.25,
          py: 0.75,
          display: "flex",
          flexWrap: "wrap",
          gap: 0.75,
          alignItems: "center",
          bgcolor: "background.paper",
          "&:focus-within": {
            borderColor: "primary.main",
            boxShadow: (t) =>
              `0 0 0 3px ${
                t.palette.mode === "dark"
                  ? "rgba(20,184,166,0.16)"
                  : "rgba(13,79,74,0.15)"
              }`,
          },
        }}
      >
        {list.map((tech, idx) => (
          <Chip
            key={`${tech}-${idx}`}
            label={tech}
            size="small"
            onDelete={() => removeTech(idx)}
            color="primary"
            variant="outlined"
            sx={{ fontWeight: 600 }}
          />
        ))}
        <InputBase
          value={draft}
          placeholder={list.length ? "" : "Add technology..."}
          sx={{ flex: 1, minWidth: 120, fontSize: "0.9rem" }}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if ((e.key === "Enter" || e.key === ",") && draft.trim()) {
              e.preventDefault();
              addTech(draft);
            } else if (e.key === "Backspace" && !draft && list.length) {
              removeTech(list.length - 1);
            }
          }}
          onBlur={() => {
            if (draft.trim()) addTech(draft);
          }}
        />
      </Box>
    </Box>
  );
}
