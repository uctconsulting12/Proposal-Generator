import api, { tokenStore } from "./client.js";

export const sessionsApi = {
  start: (intake) => api.post("/session/start", intake).then((r) => r.data),
  send: (sessionId, message) =>
    api
      .post(`/session/${sessionId}/message`, { message })
      .then((r) => r.data),
  load: (sessionId) =>
    api.get(`/session/${sessionId}`).then((r) => r.data),
  list: () => api.get("/session/list").then((r) => r.data),
  finalize: (sessionId) =>
    api.post(`/session/${sessionId}/finalize`, {}).then((r) => r.data),
  reopen: (sessionId) =>
    api.post(`/session/${sessionId}/reopen`, {}).then((r) => r.data),
  discard: (sessionId) =>
    api.delete(`/session/${sessionId}`).then((r) => r.data),
  downloadProposalPdf: async (sessionId, { template } = {}) => {
    const token = tokenStore.get();
    const qs = template ? `?template=${encodeURIComponent(template)}` : "";
    const res = await fetch(`/api/session/${sessionId}/proposal.pdf${qs}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) {
      let message = `HTTP ${res.status}`;
      try {
        const data = await res.json();
        message = data.error || data.detail || message;
      } catch {
        /* ignore */
      }
      throw new Error(message);
    }
    return res.blob();
  },
};
