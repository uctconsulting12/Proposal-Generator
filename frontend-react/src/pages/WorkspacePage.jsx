import { useEffect } from "react";
import { Box } from "@mui/material";
import ProjectForm from "../components/workspace/ProjectForm.jsx";
import ChatPanel from "../components/workspace/ChatPanel.jsx";
import { useSession } from "../contexts/SessionContext.jsx";

const DEFAULT_TITLE = "ProposalPilot AI";

export default function WorkspacePage() {
  const { intake } = useSession();
  // Surface the active proposal in the browser tab so users with multiple
  // tabs open can tell them apart at a glance. The title falls back to the
  // app name whenever the intake hasn't been filled in yet, and is restored
  // when the workspace unmounts so other pages aren't left with a stale tab
  // label.
  useEffect(() => {
    const jobTitle = (intake?.job_title || "").trim();
    document.title = jobTitle
      ? `${jobTitle} | ${DEFAULT_TITLE}`
      : DEFAULT_TITLE;
    return () => {
      document.title = DEFAULT_TITLE;
    };
  }, [intake?.job_title]);

  return (
    <Box
      sx={{
        display: "grid",
        gap: 2.5,
        gridTemplateColumns: { xs: "1fr", lg: "minmax(0, 1fr) minmax(0, 1fr)" },
        alignItems: "start",
      }}
    >
      <ProjectForm />
      <ChatPanel />
    </Box>
  );
}
