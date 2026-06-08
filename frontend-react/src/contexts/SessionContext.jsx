import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { sessionsApi } from "../api/sessions.js";
import { kbApi } from "../api/kb.js";
import { useAuth } from "./AuthContext.jsx";

const SessionContext = createContext(null);
const OUTCOME_KEY = "proposal_outcomes_v1";

const readOutcomes = () => {
  try {
    return JSON.parse(localStorage.getItem(OUTCOME_KEY) || "{}");
  } catch {
    return {};
  }
};
const writeOutcomes = (map) =>
  localStorage.setItem(OUTCOME_KEY, JSON.stringify(map));

const EMPTY_INTAKE = {
  client_name: "",
  job_title: "",
  budget: "",
  timeline: "",
  tech_stack: "",
  deliverables: "",
  constraints: "",
  job_description: "",
};

export function SessionProvider({ children }) {
  const { user } = useAuth();

  // Active workspace
  const [sessionId, setSessionId] = useState(null);
  const [stage, setStage] = useState("questioning");
  const [closed, setClosed] = useState(false);
  const [messages, setMessages] = useState([]);
  const [intake, setIntake] = useState(EMPTY_INTAKE);
  const [status, setStatus] = useState({ text: "", severity: "info" });
  // RAG sources retrieved for this session, populated on startSession. Joined
  // with kbDocs in the UI to surface "include this GitHub link?" toggles
  // during the draft-review stage.
  const [retrievedSources, setRetrievedSources] = useState([]);

  // Async flags
  const [sending, setSending] = useState(false);
  const [startingSession, setStartingSession] = useState(false);

  // History + KB
  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [kbDocs, setKbDocs] = useState([]);
  const [kbLoading, setKbLoading] = useState(false);

  // Per-user outcome map (Dashboard only — client-side)
  const [outcomes, setOutcomes] = useState(readOutcomes());

  // ---- helpers --------------------------------------------------------
  const appendMessage = useCallback((role, text) => {
    setMessages((prev) => [...prev, { role, text }]);
  }, []);

  const updateIntake = useCallback((key, value) => {
    setIntake((prev) => ({ ...prev, [key]: value }));
  }, []);

  const resetWorkspace = useCallback(() => {
    setSessionId(null);
    setStage("questioning");
    setClosed(false);
    setMessages([]);
    setIntake(EMPTY_INTAKE);
    setStatus({ text: "", severity: "info" });
    setRetrievedSources([]);
  }, []);

  // ---- session ops ----------------------------------------------------
  const loadHistory = useCallback(async () => {
    setHistoryLoading(true);
    try {
      const data = await sessionsApi.list();
      setHistory(data.sessions || []);
    } catch (err) {
      setStatus({ text: err.message, severity: "error" });
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  const loadKbDocs = useCallback(async () => {
    setKbLoading(true);
    try {
      const data = await kbApi.list();
      setKbDocs(data.documents || []);
    } catch (err) {
      setStatus({ text: err.message, severity: "error" });
    } finally {
      setKbLoading(false);
    }
  }, []);

  const loadSession = useCallback(async (id) => {
    const data = await sessionsApi.load(id);
    setSessionId(data.session_id);
    setStage(data.stage);
    setClosed(Boolean(data.closed));
    setIntake((prev) => ({ ...prev, ...EMPTY_INTAKE, ...data.intake }));
    const mapped = (data.messages || []).map((m) => ({
      role: m.role === "assistant" ? "Assistant" : "You",
      text: m.content,
    }));
    setMessages(mapped);
    // Retrieved sources are only returned by /start, not /load — older
    // sessions silently get no toggles, which is fine.
    setRetrievedSources([]);
    setStatus({ text: `Loaded: ${data.job_title}`, severity: "success" });
    return data;
  }, []);

  const startSession = useCallback(async () => {
    if (!intake.job_title.trim() || !intake.job_description.trim()) {
      setStatus({
        text: "Project title and job description are required.",
        severity: "warning",
      });
      return;
    }
    setStartingSession(true);
    setMessages([]);
    setClosed(false);
    setStatus({ text: "Starting session...", severity: "info" });
    try {
      const data = await sessionsApi.start(intake);
      await loadSession(data.session_id);
      await loadHistory();
      // loadSession clears retrievedSources; set them after so the draft-stage
      // GitHub-link toggles know which projects were actually retrieved.
      setRetrievedSources(data.retrieved_sources || []);
      const sources = (data.retrieved_sources || []).slice(0, 4).join(", ");
      setStatus({
        text: `Session started. RAG sources: ${sources || "none"}`,
        severity: "success",
      });
    } catch (err) {
      setStatus({ text: err.message, severity: "error" });
    } finally {
      setStartingSession(false);
    }
  }, [intake, loadHistory, loadSession]);

  const sendMessage = useCallback(
    async (text) => {
      if (!text || !sessionId || sending) return;
      appendMessage("You", text);
      setSending(true);
      try {
        const data = await sessionsApi.send(sessionId, text);
        appendMessage("Assistant", data.assistant);
        setStage(data.stage);
      } catch (err) {
        appendMessage("System", `Error: ${err.message}`);
      } finally {
        setSending(false);
      }
    },
    [sessionId, sending, appendMessage]
  );

  const finalizeSession = useCallback(async () => {
    if (!sessionId || closed) return;
    try {
      await sessionsApi.finalize(sessionId);
      setClosed(true);
      appendMessage("System", "Session finalized. Chat is now in Q&A mode.");
      setStatus({ text: "Session finalized.", severity: "success" });
      await loadHistory();
    } catch (err) {
      appendMessage("System", `Error: ${err.message}`);
    }
  }, [sessionId, closed, appendMessage, loadHistory]);

  const discardSession = useCallback(async () => {
    if (!sessionId) return;
    try {
      await sessionsApi.discard(sessionId);
      resetWorkspace();
      await loadHistory();
      setStatus({ text: "Session discarded.", severity: "success" });
    } catch (err) {
      appendMessage("System", `Error: ${err.message}`);
    }
  }, [sessionId, resetWorkspace, loadHistory, appendMessage]);

  const reopenSession = useCallback(async () => {
    if (!sessionId || !closed) return;
    try {
      await sessionsApi.reopen(sessionId);
      setClosed(false);
      appendMessage(
        "System",
        "Session reopened. You can edit the proposal or ask for changes."
      );
      setStatus({ text: "Session reopened.", severity: "success" });
      await loadHistory();
    } catch (err) {
      appendMessage("System", `Error: ${err.message}`);
    }
  }, [sessionId, closed, appendMessage, loadHistory]);

  const downloadProposalPdf = useCallback(
    async ({ template } = {}) => {
      if (!sessionId) return;
      try {
        const blob = await sessionsApi.downloadProposalPdf(sessionId, {
          template,
        });
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = template
          ? `proposal-${template}.pdf`
          : "proposal.pdf";
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(a.href);
      } catch (err) {
        appendMessage("System", `PDF download failed: ${err.message}`);
      }
    },
    [sessionId, appendMessage]
  );

  const uploadDocument = useCallback(
    async (file) => {
      if (!file) return null;
      const data = await kbApi.upload(file);
      await loadKbDocs();
      return data;
    },
    [loadKbDocs]
  );

  const importGithubProject = useCallback(
    async (githubUrl) => {
      const url = (githubUrl || "").trim();
      if (!url) return null;
      const data = await kbApi.importGithub(url);
      await loadKbDocs();
      return data;
    },
    [loadKbDocs]
  );

  const deleteDocument = useCallback(
    async (filename) => {
      const name = (filename || "").trim();
      if (!name) return null;
      const data = await kbApi.delete(name);
      await loadKbDocs();
      return data;
    },
    [loadKbDocs]
  );

  // ---- outcomes ------------------------------------------------------
  const setOutcome = useCallback((id, value) => {
    setOutcomes((prev) => {
      const next = { ...prev, [id]: value };
      writeOutcomes(next);
      return next;
    });
  }, []);

  // ---- lifecycle: reload when user changes ---------------------------
  useEffect(() => {
    if (!user) {
      resetWorkspace();
      setHistory([]);
      setKbDocs([]);
      return;
    }
    loadHistory();
    loadKbDocs();
  }, [user, loadHistory, loadKbDocs, resetWorkspace]);

  const value = useMemo(
    () => ({
      // active session
      sessionId,
      stage,
      closed,
      messages,
      intake,
      status,
      sending,
      startingSession,
      retrievedSources,
      // history / KB
      history,
      historyLoading,
      kbDocs,
      kbLoading,
      // outcomes
      outcomes,
      // mutations
      updateIntake,
      resetWorkspace,
      setStatus,
      startSession,
      sendMessage,
      finalizeSession,
      reopenSession,
      discardSession,
      downloadProposalPdf,
      loadSession,
      loadHistory,
      loadKbDocs,
      uploadDocument,
      importGithubProject,
      deleteDocument,
      setOutcome,
    }),
    [
      sessionId,
      stage,
      closed,
      messages,
      intake,
      status,
      sending,
      startingSession,
      retrievedSources,
      history,
      historyLoading,
      kbDocs,
      kbLoading,
      outcomes,
      updateIntake,
      resetWorkspace,
      startSession,
      sendMessage,
      finalizeSession,
      reopenSession,
      discardSession,
      downloadProposalPdf,
      loadSession,
      loadHistory,
      loadKbDocs,
      uploadDocument,
      importGithubProject,
      deleteDocument,
      setOutcome,
    ]
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export const useSession = () => {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error("useSession must be inside SessionProvider");
  return ctx;
};
