(() => {
  const { useMemo, useRef, useState, useEffect, useCallback } = React;
  const h = React.createElement;

  // Stage descriptors. UI labels only — the server is the source of truth.
  const STAGE_INFO = {
    questioning: {
      label: "Gathering Requirements",
      placeholder: "Answer the question to help shape the proposal...",
      step: "STEP 1 OF 3",
      pillClass: "questioning",
    },
    draft: {
      label: "Draft Review",
      placeholder: "Describe changes, or type 'approve' to generate the full proposal",
      step: "STEP 2 OF 3",
      pillClass: "draft",
    },
    final: {
      label: "Proposal Ready",
      placeholder: "Ask for a change or ask a question",
      step: "STEP 3 OF 3",
      pillClass: "final",
    },
  };

  // localStorage helpers for client-side-only fields (proposal outcome).
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

  function App() {
    // --- auth ----------------------------------------------------------
    const [authUser, setAuthUser] = useState(null);
    const [authLoading, setAuthLoading] = useState(false);
    const [authError, setAuthError] = useState("");
    const [authInfo, setAuthInfo] = useState("");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");

    // --- session / workspace state ------------------------------------
    const [sessionId, setSessionId] = useState(null);
    const [closed, setClosed] = useState(false);
    const [stage, setStage] = useState("questioning");
    const [messages, setMessages] = useState([]);
    const [chatInput, setChatInput] = useState("");
    const [sending, setSending] = useState(false);
    const [loadingStart, setLoadingStart] = useState(false);
    const [status, setStatus] = useState("");

    // --- intake form ---------------------------------------------------
    const [form, setForm] = useState({
      client_name: "",
      job_title: "",
      budget: "",
      timeline: "",
      tech_stack: "",
      deliverables: "",
      constraints: "",
      job_description: "",
    });
    const [techInput, setTechInput] = useState("");

    // --- history / KB --------------------------------------------------
    const [sessionHistory, setSessionHistory] = useState([]);
    const [loadingHistory, setLoadingHistory] = useState(false);
    const [historyOpen, setHistoryOpen] = useState(false);
    const [kbDocs, setKbDocs] = useState([]);
    const [kbLoading, setKbLoading] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [uploadError, setUploadError] = useState("");

    // --- shell ---------------------------------------------------------
    const [theme, setTheme] = useState("light");
    const [page, setPage] = useState("workspace");
    const [searchTerm, setSearchTerm] = useState("");
    const [outcomes, setOutcomes] = useState(readOutcomes());

    const chatBoxRef = useRef(null);
    const stageInfo = STAGE_INFO[stage] || STAGE_INFO.questioning;

    // Auto-scroll chat to bottom on new messages.
    useEffect(() => {
      if (chatBoxRef.current) {
        chatBoxRef.current.scrollTop = chatBoxRef.current.scrollHeight;
      }
    }, [messages]);

    // Theme bootstrap.
    useEffect(() => {
      const saved = (localStorage.getItem("copilot_theme") || "light").trim();
      const next = saved === "dark" ? "dark" : "light";
      setTheme(next);
      document.body.setAttribute("data-theme", next);
    }, []);
    useEffect(() => {
      document.body.setAttribute("data-theme", theme);
      localStorage.setItem("copilot_theme", theme);
    }, [theme]);

    // Restore auth session via JWT.
    useEffect(() => {
      const token = (localStorage.getItem("copilot_jwt") || "").trim();
      if (!token) return;
      fetch("/api/auth/me", { headers: { Authorization: `Bearer ${token}` } })
        .then((res) => (res.ok ? res.json() : Promise.reject(new Error("Session expired"))))
        .then((data) => setAuthUser(data))
        .catch(() => {
          localStorage.removeItem("copilot_jwt");
          setAuthUser(null);
        });
    }, []);

    // ---- auth helpers -------------------------------------------------
    const authHeaders = useCallback(() => {
      const token = (localStorage.getItem("copilot_jwt") || "").trim();
      return token ? { Authorization: `Bearer ${token}` } : {};
    }, []);

    const postJson = useCallback(async (url, body) => {
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify(body || {}),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
      return data;
    }, [authHeaders]);

    const getJson = useCallback(async (url) => {
      const res = await fetch(url, { headers: { ...authHeaders() } });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
      return data;
    }, [authHeaders]);

    // ---- session ops --------------------------------------------------
    const appendMessage = (role, text) =>
      setMessages((prev) => [...prev, { role, text }]);

    const updateForm = (key, value) =>
      setForm((prev) => ({ ...prev, [key]: value }));

    const loadSessionHistory = useCallback(async () => {
      setLoadingHistory(true);
      try {
        const data = await getJson("/api/session/list");
        setSessionHistory(data.sessions || []);
      } catch (err) {
        setStatus(`Error: ${err.message}`);
      } finally {
        setLoadingHistory(false);
      }
    }, [getJson]);

    const loadKbDocs = useCallback(async () => {
      setKbLoading(true);
      try {
        const data = await getJson("/api/kb/list");
        setKbDocs(data.documents || []);
      } catch (err) {
        setUploadError(err.message);
      } finally {
        setKbLoading(false);
      }
    }, [getJson]);

    useEffect(() => {
      if (!authUser) return;
      loadSessionHistory();
      loadKbDocs();
    }, [authUser, loadSessionHistory, loadKbDocs]);

    const sendMessage = async (text) => {
      if (!text || !sessionId || sending) return;
      appendMessage("You", text);
      setSending(true);
      try {
        const data = await postJson(`/api/session/${sessionId}/message`, { message: text });
        appendMessage("Assistant", data.assistant);
        setStage(data.stage);
      } catch (err) {
        appendMessage("System", `Error: ${err.message}`);
      } finally {
        setSending(false);
      }
    };

    const startSession = async () => {
      if (!form.job_title.trim() || !form.job_description.trim()) {
        setStatus("Project title and project description are required.");
        return;
      }
      setLoadingStart(true);
      setClosed(false);
      setMessages([]);
      setStatus("Starting session...");
      try {
        const data = await postJson("/api/session/start", form);
        await loadSession(data.session_id);
        await loadSessionHistory();
        const sources = (data.retrieved_sources || []).slice(0, 4).join(", ");
        setStatus(`Session started · RAG sources: ${sources || "none"}`);
      } catch (err) {
        setStatus(`Error: ${err.message}`);
      } finally {
        setLoadingStart(false);
      }
    };

    const loadSession = async (id) => {
      const data = await getJson(`/api/session/${id}`);
      setSessionId(data.session_id);
      setStage(data.stage);
      setClosed(Boolean(data.closed));
      setForm((prev) => ({ ...prev, ...data.intake }));
      const mapped = (data.messages || []).map((m) => ({
        role: m.role === "assistant" ? "Assistant" : "You",
        text: m.content,
      }));
      setMessages(mapped);
      setStatus(`Loaded: ${data.job_title}`);
      setPage("workspace");
      setHistoryOpen(false);
    };

    const onSubmitChat = async () => {
      const message = chatInput.trim();
      if (!message) return;
      setChatInput("");
      await sendMessage(message);
    };

    const finalizeSession = async () => {
      if (!sessionId || closed) return;
      if (!window.confirm("Finalize this session? You won't be able to send more messages.")) return;
      try {
        await postJson(`/api/session/${sessionId}/finalize`, {});
        setClosed(true);
        appendMessage("System", "Session finalized. Chat is now in Q&A mode.");
        setStatus("Finalized.");
        await loadSessionHistory();
      } catch (err) {
        appendMessage("System", `Error: ${err.message}`);
      }
    };

    const downloadProposalPdf = async () => {
      try {
        const res = await fetch(
          `/api/session/${sessionId}/proposal.pdf`,
          { headers: authHeaders() }
        );
        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          throw new Error(data.error || `HTTP ${res.status}`);
        }
        const blob = await res.blob();
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = "proposal.pdf";
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(a.href);
      } catch (err) {
        appendMessage("System", `PDF download failed: ${err.message}`);
      }
    };

    const resetWorkspace = () => {
      setSessionId(null);
      setStage("questioning");
      setClosed(false);
      setMessages([]);
      setStatus("");
      setForm({
        client_name: "",
        job_title: "",
        budget: "",
        timeline: "",
        tech_stack: "",
        deliverables: "",
        constraints: "",
        job_description: "",
      });
      setTechInput("");
      setPage("workspace");
    };

    // ---- auth flow ----------------------------------------------------
    const authenticate = async (mode) => {
      if (!email.trim() || !password.trim()) {
        setAuthError("Email and password are required.");
        return;
      }
      setAuthLoading(true);
      setAuthError("");
      setAuthInfo("");
      try {
        const endpoint = mode === "signup" ? "/api/auth/signup" : "/api/auth/signin";
        const data = await postJson(endpoint, { email, password });
        localStorage.setItem("copilot_jwt", data.access_token);
        setAuthUser({ email: data.email, user_id: data.user_id });
        setAuthInfo(mode === "signup" ? "Profile created." : "Signed in.");
      } catch (err) {
        setAuthError(err.message);
      } finally {
        setAuthLoading(false);
      }
    };

    const logout = () => {
      localStorage.removeItem("copilot_jwt");
      setAuthUser(null);
      resetWorkspace();
      setSessionHistory([]);
      setKbDocs([]);
    };

    const toggleTheme = () =>
      setTheme((prev) => (prev === "dark" ? "light" : "dark"));

    // ---- tech-stack chip helpers --------------------------------------
    const techList = useMemo(
      () => form.tech_stack.split(",").map((t) => t.trim()).filter(Boolean),
      [form.tech_stack]
    );
    const addTech = (value) => {
      const v = value.trim().replace(/,$/, "");
      if (!v) return;
      const next = [...techList, v];
      updateForm("tech_stack", next.join(", "));
      setTechInput("");
    };
    const removeTech = (idx) => {
      const next = techList.filter((_, i) => i !== idx);
      updateForm("tech_stack", next.join(", "));
    };

    // ---- file upload --------------------------------------------------
    const uploadDocument = async (file) => {
      if (!file) return;
      setUploading(true);
      setUploadError("");
      try {
        const formData = new FormData();
        formData.append("file", file);
        const res = await fetch("/api/kb/upload", {
          method: "POST",
          headers: { ...authHeaders() },
          body: formData,
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
        await loadKbDocs();
      } catch (err) {
        setUploadError(err.message);
      } finally {
        setUploading(false);
      }
    };

    // ---- GitHub project import ---------------------------------------
    const importGithub = async (githubUrl) => {
      if (!githubUrl) return;
      setUploading(true);
      setUploadError("");
      try {
        await postJson("/api/kb/github", { github_url: githubUrl });
        await loadKbDocs();
      } catch (err) {
        setUploadError(err.message);
      } finally {
        setUploading(false);
      }
    };

    // ---- outcome tracking (Dashboard) ---------------------------------
    const setOutcome = (id, value) => {
      const next = { ...outcomes, [id]: value };
      setOutcomes(next);
      writeOutcomes(next);
    };

    const filteredSessions = useMemo(() => {
      const term = searchTerm.trim().toLowerCase();
      if (!term) return sessionHistory;
      return sessionHistory.filter((s) =>
        (s.job_title || "").toLowerCase().includes(term)
      );
    }, [sessionHistory, searchTerm]);

    // ---- render: auth gate --------------------------------------------
    if (!authUser) return renderLogin({
      email, password, setEmail, setPassword,
      authLoading, authError, authInfo,
      authenticate, theme, toggleTheme,
    });

    return h("div", { className: "app" },
      renderTopbar({
        page, setPage, searchTerm, setSearchTerm,
        authUser, theme, toggleTheme, logout,
      }),
      h("div", { className: "body" },
        renderSidebar({
          page, setPage,
          historyOpen, setHistoryOpen,
          sessionHistory, loadingHistory,
          loadSessionHistory, loadSession,
          activeSessionId: sessionId,
          resetWorkspace,
          authUser,
        }),
        h("main", { className: "main" },
          page === "dashboard"
            ? renderDashboard({ sessionHistory, outcomes, setOutcome, loadSession })
            : page === "client-db"
              ? h(ClientDb, { kbDocs, kbLoading, uploading, uploadError, uploadDocument, importGithub, loadKbDocs })
              : renderWorkspace({
                form, updateForm,
                techList, techInput, setTechInput, addTech, removeTech,
                loadingStart, startSession, status,
                stage, stageInfo, messages, chatBoxRef,
                chatInput, setChatInput, onSubmitChat, sending,
                sessionId, closed, sendMessage,
                downloadProposalPdf, finalizeSession,
                canSend: Boolean(sessionId) && !sending,
              })
        )
      )
    );
  }

  // ---------- Topbar ---------------------------------------------------
  function renderTopbar({ page, setPage, searchTerm, setSearchTerm, authUser, theme, toggleTheme, logout }) {
    const navLink = (key, label) =>
      h("a", {
        className: page === key ? "active" : "",
        onClick: () => setPage(key),
      }, label);

    return h("header", { className: "topbar" },
      h("div", { className: "brand" },
        h("span", { className: "brand-dot" }),
        "ProposalPilot AI"
      ),
      h("nav", { className: "topnav" },
        navLink("workspace", "Workspace"),
        navLink("dashboard", "Dashboard"),
        navLink("client-db", "Client Database")
      ),
      h("div", { className: "topbar-right" },
        h("div", { className: "search" },
          h("span", { style: { color: "var(--muted)" } }, "🔍"),
          h("input", {
            placeholder: "Search proposals...",
            value: searchTerm,
            onChange: (e) => setSearchTerm(e.target.value),
          })
        ),
        h("button", { className: "icon-btn", onClick: toggleTheme, title: "Toggle theme" },
          theme === "dark" ? "☀️" : "🌙"
        ),
        h("button", { className: "icon-btn", onClick: logout, title: `Logout (${authUser.email})` }, "⎋"),
        h("button", { className: "avatar", title: authUser.email },
          authUser.email.slice(0, 1).toUpperCase()
        )
      )
    );
  }

  // ---------- Sidebar --------------------------------------------------
  function renderSidebar({
    page, setPage,
    historyOpen, setHistoryOpen,
    sessionHistory, loadingHistory, loadSessionHistory, loadSession,
    activeSessionId, resetWorkspace, authUser,
  }) {
    const navBtn = (key, label, icon) =>
      h("button", {
        className: `nav-item ${page === key ? "active" : ""}`,
        onClick: () => setPage(key),
      },
        h("span", null, icon),
        h("span", null, label)
      );

    return h("aside", { className: "sidebar" },
      h("div", { className: "plan-card" },
        h("div", { className: "icon" }),
        h("div", null,
          h("div", { className: "title" }, "Workspace"),
          h("div", { className: "sub" }, authUser.email)
        )
      ),
      h("button", { className: "new-proposal-btn", onClick: resetWorkspace },
        h("span", null, "+"),
        h("span", null, "New Proposal")
      ),
      navBtn("dashboard", "Dashboard", "▦"),
      navBtn("workspace", "Active Project", "📝"),

      // Proposal History dropdown
      h("button", {
        className: `nav-item ${historyOpen ? "open" : ""}`,
        onClick: () => {
          if (!historyOpen) loadSessionHistory();
          setHistoryOpen(!historyOpen);
        },
      },
        h("span", null, "🕘"),
        h("span", null, "Proposal History"),
        h("span", { className: "chev" }, "▸")
      ),
      historyOpen
        ? h("div", { className: "nav-sub" },
          loadingHistory
            ? h("div", { className: "empty" }, "Loading...")
            : (sessionHistory.length === 0
              ? h("div", { className: "empty" }, "No proposals yet.")
              : sessionHistory.map((s) =>
                h("button", {
                  key: s.session_id,
                  className: s.session_id === activeSessionId ? "active" : "",
                  onClick: () => loadSession(s.session_id),
                  title: `${s.job_title} · ${s.stage}`,
                }, `${s.job_title || "Untitled"} · ${s.stage}`)
              ))
        )
        : null,

      navBtn("client-db", "Client Database", "🗂")
    );
  }

  // ---------- Workspace (project details + chat) -----------------------
  function renderWorkspace(p) {
    const projectDetails = h("section", { className: "panel" },
      h("div", { className: "panel-body" },
        h("h2", null, "Project Details"),
        h("p", { className: "panel-sub" },
          "Provide context for your AI assistant to generate the best possible proposal."
        ),

        labeledField("Client Name", "e.g. Acme Corp", p.form.client_name, (v) => p.updateForm("client_name", v)),
        labeledField("Project Title *", "e.g. Cloud Migration Strategy", p.form.job_title, (v) => p.updateForm("job_title", v)),

        h("div", { className: "field-row" },
          h("div", { className: "field" },
            h("label", null, "Budget Range"),
            h("select", {
              value: p.form.budget,
              onChange: (e) => p.updateForm("budget", e.target.value),
            },
              h("option", { value: "" }, "Select a range..."),
              h("option", { value: "<$5k" }, "< $5k"),
              h("option", { value: "$5k - $10k" }, "$5k - $10k"),
              h("option", { value: "$10k - $25k" }, "$10k - $25k"),
              h("option", { value: "$25k - $50k" }, "$25k - $50k"),
              h("option", { value: "$50k+" }, "$50k+")
            )
          ),
          h("div", { className: "field" },
            h("label", null, "Timeline"),
            h("input", {
              placeholder: "e.g. 3 Months",
              value: p.form.timeline,
              onChange: (e) => p.updateForm("timeline", e.target.value),
            })
          )
        ),

        h("div", { className: "field" },
          h("label", null, "Tech Stack"),
          h("div", { className: "chip-input" },
            p.techList.map((tech, idx) =>
              h("span", { key: `${tech}-${idx}`, className: "chip" },
                tech,
                h("button", { onClick: () => p.removeTech(idx), title: "Remove" }, "×")
              )
            ),
            h("input", {
              placeholder: p.techList.length ? "" : "Add technology...",
              value: p.techInput,
              onChange: (e) => p.setTechInput(e.target.value),
              onKeyDown: (e) => {
                if ((e.key === "Enter" || e.key === ",") && p.techInput.trim()) {
                  e.preventDefault();
                  p.addTech(p.techInput);
                } else if (e.key === "Backspace" && !p.techInput && p.techList.length) {
                  p.removeTech(p.techList.length - 1);
                }
              },
              onBlur: () => { if (p.techInput.trim()) p.addTech(p.techInput); },
            })
          )
        ),

        h("div", { className: "field" },
          h("label", null, "Job Description *"),
          h("textarea", {
            placeholder: "Paste the job requirements or project brief here...",
            value: p.form.job_description,
            onChange: (e) => p.updateForm("job_description", e.target.value),
          })
        ),

        h("div", { className: "field" },
          h("label", null, "Deliverables"),
          h("textarea", {
            value: p.form.deliverables,
            onChange: (e) => p.updateForm("deliverables", e.target.value),
            style: { minHeight: "80px" },
          })
        ),

        h("div", { className: "field" },
          h("label", null, "Constraints"),
          h("textarea", {
            value: p.form.constraints,
            onChange: (e) => p.updateForm("constraints", e.target.value),
            style: { minHeight: "80px" },
          })
        ),

        h("button", {
          className: "btn btn-outline",
          style: { width: "100%" },
          disabled: p.loadingStart,
          onClick: p.startSession,
        },
          h("span", null, "💾"),
          p.loadingStart ? "Starting..." : (p.sessionId ? "Save Project Draft" : "Start Session")
        ),
        p.status ? h("div", { className: "status-line" }, p.status) : null
      )
    );

    const conversation = h("section", { className: "panel" },
      h("div", { className: "panel-header" },
        h("div", { className: "status-pill" },
          h("span", { className: "dot" }),
          "Status: ",
          h("span", { className: "stage-name" }, p.stageInfo.label)
        ),
        h("div", { style: { display: "flex", alignItems: "center", gap: "10px" } },
          h("span", { className: "step-meta" }, p.stageInfo.step),
          p.stage === "final" && p.sessionId
            ? h("button", { className: "btn btn-soft", onClick: p.downloadProposalPdf }, "Preview / Export")
            : h("button", { className: "btn btn-soft", disabled: true }, "Export")
        )
      ),
      h("div", { className: "panel-body chat-shell" },
        h("div", { className: "chat-stream", ref: p.chatBoxRef },
          p.messages.length === 0
            ? h("div", { className: "msg-row" },
              h("div", { className: "msg-avatar bot" }, "AI"),
              h("div", { className: "bubble bot" },
                "Hello! Fill in the project details on the left and click ",
                h("b", null, "Start Session"),
                " to begin. I'll ask short clarifying questions, then draft a proposal you can approve."
              )
            )
            : p.messages.map((msg, i) => {
              const isUser = msg.role === "You";
              const isSystem = msg.role === "System";
              return h("div", {
                key: i,
                className: `msg-row ${isUser ? "user" : ""}`,
              },
                !isUser ? h("div", { className: "msg-avatar bot" }, isSystem ? "⚠" : "AI") : null,
                h("div", {
                  className: `bubble ${isSystem ? "system" : (isUser ? "user" : "bot")}`,
                }, msg.text),
                isUser ? h("div", { className: "msg-avatar user" }, "👤") : null
              );
            })
        ),

        p.stage === "draft" && !p.closed && p.sessionId
          ? h("button", {
            className: "btn btn-success",
            disabled: !p.canSend,
            onClick: () => p.sendMessage("Approve"),
          }, "Approve & Generate Full Proposal")
          : null,

        p.stage === "final" && p.sessionId && !p.closed
          ? h("button", {
            className: "btn btn-soft",
            onClick: p.finalizeSession,
          }, "Finalize Session (lock chat)")
          : null,

        h("div", { className: "composer" },
          h("input", {
            value: p.chatInput,
            placeholder: p.sessionId ? p.stageInfo.placeholder : "Start a session first...",
            disabled: !p.sessionId,
            onChange: (e) => p.setChatInput(e.target.value),
            onKeyDown: (e) => {
              if (e.key === "Enter") { e.preventDefault(); p.onSubmitChat(); }
            },
          }),
          h("button", {
            className: "send-btn",
            disabled: !p.canSend,
            onClick: p.onSubmitChat,
          }, p.sending ? "…" : "➤")
        ),

        h("div", { className: "footer-meta" },
          h("span", null, "⚡ AI Power: High"),
          h("span", null, "🔒 Encrypted & Private")
        )
      )
    );

    return h("div", { className: "workspace-grid" }, projectDetails, conversation);
  }

  // ---------- Dashboard ------------------------------------------------
  function renderDashboard({ sessionHistory, outcomes, setOutcome, loadSession }) {
    const total = sessionHistory.length;
    const finalCount = sessionHistory.filter((s) => s.stage === "final").length;
    const draftCount = sessionHistory.filter((s) => s.stage === "draft").length;
    const wonCount = sessionHistory.filter((s) => outcomes[s.session_id] === "won").length;

    const stat = (label, value, kind) =>
      h("div", { className: `stat ${kind || ""}` },
        h("div", { className: "label" }, label),
        h("div", { className: "value" }, value)
      );

    return h("div", null,
      h("h1", { style: { margin: "0 0 4px", fontSize: "1.6rem", letterSpacing: "-0.01em" } }, "Dashboard"),
      h("p", { style: { color: "var(--muted)", marginTop: 0, marginBottom: "18px" } },
        "Manage your past proposals. Mark each as Won, Lost, or Pending to track your performance."
      ),

      h("div", { className: "stats-grid" },
        stat("Total Proposals", total, "brand"),
        stat("Finalized", finalCount, "brand"),
        stat("Drafts", draftCount, "warning"),
        stat("Won (manual)", wonCount, "success")
      ),

      h("section", { className: "panel" },
        h("div", { className: "panel-header" },
          h("h2", null, "Proposal Performance"),
          h("span", { className: "step-meta" }, `${total} TOTAL`)
        ),
        h("div", { className: "panel-body", style: { padding: 0 } },
          total === 0
            ? h("div", { style: { padding: "24px", color: "var(--muted)" } },
              "No proposals yet. Create one from the Workspace to populate this table.")
            : h("table", { className: "simple" },
              h("thead", null,
                h("tr", null,
                  h("th", null, "Project"),
                  h("th", null, "Client"),
                  h("th", null, "Stage"),
                  h("th", null, "Updated"),
                  h("th", null, "Outcome"),
                  h("th", null, "")
                )
              ),
              h("tbody", null,
                sessionHistory.map((s) => {
                  const outcome = outcomes[s.session_id] || "pending";
                  return h("tr", { key: s.session_id },
                    h("td", null, h("b", null, s.job_title || "Untitled")),
                    h("td", null, "—"),
                    h("td", null, h("span", { className: `pill ${s.stage}` }, s.stage)),
                    h("td", { style: { color: "var(--muted)" } },
                      (s.updated_at || "").slice(0, 10)
                    ),
                    h("td", null,
                      h("select", {
                        value: outcome,
                        onChange: (e) => setOutcome(s.session_id, e.target.value),
                        style: {
                          padding: "5px 8px",
                          borderRadius: "8px",
                          border: "1px solid var(--line-strong)",
                          background: "var(--bg-panel)",
                        },
                      },
                        h("option", { value: "pending" }, "Pending"),
                        h("option", { value: "won" }, "Won"),
                        h("option", { value: "lost" }, "Lost")
                      )
                    ),
                    h("td", null,
                      h("button", {
                        className: "btn btn-soft",
                        style: { padding: "6px 10px" },
                        onClick: () => loadSession(s.session_id),
                      }, "Open")
                    )
                  );
                })
              )
            )
        )
      )
    );
  }

  // ---------- Client Database -----------------------------------------
  function ClientDb({ kbDocs, kbLoading, uploading, uploadError, uploadDocument, importGithub, loadKbDocs }) {
    const [githubUrl, setGithubUrl] = useState("");

    const submitGithub = async () => {
      const url = githubUrl.trim();
      if (!url) return;
      await importGithub(url);
      setGithubUrl("");
    };

    return h("div", null,
      h("h1", { style: { margin: "0 0 4px", fontSize: "1.6rem", letterSpacing: "-0.01em" } },
        "Client Database"
      ),
      h("p", { style: { color: "var(--muted)", marginTop: 0, marginBottom: "18px" } },
        "Upload past proposals or import GitHub projects. Each gets an AI-generated summary and is indexed into the knowledge base for retrieval."
      ),

      h("section", { className: "panel", style: { marginBottom: "18px" } },
        h("div", { className: "panel-body" },
          h("div", { className: "field" },
            h("label", null, "Upload a document  (.txt, .md, .json, .pdf, .docx)"),
            h("input", {
              type: "file",
              disabled: uploading,
              onChange: (e) => uploadDocument(e.target.files && e.target.files[0]),
            })
          ),

          h("div", { style: { borderTop: "1px dashed var(--line)", margin: "8px 0 14px" } }),

          h("div", { className: "field" },
            h("label", null, "Add a GitHub Project"),
            h("div", { style: { display: "flex", gap: "8px", alignItems: "center" } },
              h("input", {
                placeholder: "https://github.com/owner/repo",
                value: githubUrl,
                disabled: uploading,
                onChange: (e) => setGithubUrl(e.target.value),
                onKeyDown: (e) => { if (e.key === "Enter") submitGithub(); },
                style: { flex: 1 },
              }),
              h("button", {
                className: "btn btn-primary",
                disabled: uploading || !githubUrl.trim(),
                onClick: submitGithub,
              }, uploading ? "Importing..." : "Import")
            ),
            h("div", { className: "status-line" },
              "We fetch project name, description, topics, and the README from GitHub. The README becomes searchable in your knowledge base."
            )
          ),

          uploading ? h("div", { className: "status-line" }, "Working...") : null,
          uploadError ? h("div", { className: "status-line error" }, `Error: ${uploadError}`) : null,
          h("button", { className: "btn btn-soft", onClick: loadKbDocs }, "Refresh")
        )
      ),

      h("section", { className: "panel" },
        h("div", { className: "panel-header" },
          h("h2", null, "Past Proposals & Projects"),
          h("span", { className: "step-meta" }, `${kbDocs.length} DOCUMENTS`)
        ),
        h("div", { className: "panel-body" },
          kbLoading
            ? h("div", { className: "status-line" }, "Loading...")
            : (kbDocs.length === 0
              ? h("div", { className: "status-line" }, "No documents yet. Upload a file or import a GitHub project above.")
              : kbDocs.map((d) => renderDocCard(d)))
        )
      )
    );
  }

  function renderDocCard(d) {
    const isGithub = d.source === "github";
    const title = isGithub && d.project_name ? d.project_name : d.filename;

    const headerRow = h("div", {
      style: { display: "flex", justifyContent: "space-between", alignItems: "center", gap: "10px" }
    },
      h("div", { className: "title" },
        isGithub ? h("span", { style: { marginRight: "6px" } }, "🐙") : null,
        title
      ),
      isGithub
        ? h("span", {
            className: "pill final",
            style: { background: "var(--brand-soft)", color: "var(--brand)" },
          }, "GitHub")
        : null
    );

    const link = isGithub && d.github_url
      ? h("a", {
          href: d.github_url,
          target: "_blank",
          rel: "noopener noreferrer",
          style: { color: "var(--brand)", fontSize: "0.85rem", wordBreak: "break-all" },
        }, d.github_url)
      : null;

    const topicChips = isGithub && d.topics && d.topics.length
      ? h("div", { style: { display: "flex", flexWrap: "wrap", gap: "6px", marginTop: "4px" } },
          d.topics.map((t) =>
            h("span", { key: t, className: "chip", style: { fontSize: "0.72rem" } }, t)
          )
        )
      : null;

    return h("div", { key: d.relative_path, className: "doc-card" },
      headerRow,
      h("div", { className: "meta" },
        (d.uploaded_at || "").slice(0, 10),
        " · ",
        formatBytes(d.size_bytes),
        !isGithub ? ` · ${d.filename}` : ""
      ),
      link,
      topicChips,
      h("div", { className: "desc" }, d.description)
    );
  }

  // ---------- Login screen --------------------------------------------
  function renderLogin({ email, password, setEmail, setPassword, authLoading, authError, authInfo, authenticate, theme, toggleTheme }) {
    return h("div", { className: "login-shell" },
      h("div", { className: "login-card" },
        h("div", { className: "brand", style: { marginBottom: "10px" } },
          h("span", { className: "brand-dot" }),
          "ProposalPilot AI"
        ),
        h("h1", { className: "login-title" }, "Welcome back"),
        h("p", { className: "login-sub" }, "Sign in to your workspace, or create a new account."),

        h("div", { className: "field" },
          h("label", null, "Email"),
          h("input", {
            type: "email",
            placeholder: "you@example.com",
            value: email,
            onChange: (e) => setEmail(e.target.value),
          })
        ),
        h("div", { className: "field" },
          h("label", null, "Password"),
          h("input", {
            type: "password",
            value: password,
            onChange: (e) => setPassword(e.target.value),
          })
        ),
        h("div", { style: { display: "flex", gap: "10px" } },
          h("button", {
            className: "btn btn-primary",
            style: { flex: 1 },
            disabled: authLoading,
            onClick: () => authenticate("signin"),
          }, authLoading ? "Please wait..." : "Sign in"),
          h("button", {
            className: "btn btn-soft",
            style: { flex: 1 },
            disabled: authLoading,
            onClick: () => authenticate("signup"),
          }, authLoading ? "Please wait..." : "Sign up")
        ),
        authInfo ? h("div", { className: "status-line" }, authInfo) : null,
        authError ? h("div", { className: "status-line error" }, `Error: ${authError}`) : null,
        h("div", { style: { textAlign: "center", marginTop: "16px" } },
          h("button", { className: "btn btn-soft", onClick: toggleTheme },
            theme === "dark" ? "Light theme" : "Dark theme"
          )
        )
      )
    );
  }

  // ---------- helpers --------------------------------------------------
  function labeledField(label, placeholder, value, onChange) {
    return h("div", { className: "field" },
      h("label", null, label),
      h("input", {
        placeholder,
        value,
        onChange: (e) => onChange(e.target.value),
      })
    );
  }

  function formatBytes(n) {
    if (!n) return "—";
    if (n < 1024) return `${n} B`;
    if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
    return `${(n / (1024 * 1024)).toFixed(1)} MB`;
  }

  const root = ReactDOM.createRoot(document.getElementById("root"));
  root.render(h(App));
})();
