import api from "./client.js";

export const kbApi = {
  list: () => api.get("/kb/list").then((r) => r.data),
  upload: (file) => {
    const formData = new FormData();
    formData.append("file", file);
    return api
      .post("/kb/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      })
      .then((r) => r.data);
  },
  reindex: () => api.post("/kb/reindex").then((r) => r.data),
  importGithub: (githubUrl) =>
    api.post("/kb/github", { github_url: githubUrl }).then((r) => r.data),
  delete: (filename) =>
    api
      .delete("/kb/document", { params: { filename } })
      .then((r) => r.data),
};
