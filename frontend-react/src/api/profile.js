import api, { tokenStore } from "./client.js";

export const profileApi = {
  get: () => api.get("/profile").then((r) => r.data),
  update: (payload) => api.put("/profile", payload).then((r) => r.data),
  uploadLogo: (file) => {
    const formData = new FormData();
    formData.append("file", file);
    return api
      .post("/profile/logo", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      })
      .then((r) => r.data);
  },
  deleteLogo: () => api.delete("/profile/logo").then((r) => r.data),
  // <img> tags can't send Authorization headers, so we pull the logo over
  // fetch() and hand back an object URL the consumer can revoke when done.
  fetchLogoObjectUrl: async () => {
    const token = tokenStore.get();
    const res = await fetch("/api/profile/logo", {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) {
      if (res.status === 404) return null;
      throw new Error(`HTTP ${res.status}`);
    }
    const blob = await res.blob();
    return URL.createObjectURL(blob);
  },
};
