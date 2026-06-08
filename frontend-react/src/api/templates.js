import api from "./client.js";

export const templatesApi = {
  list: () => api.get("/templates").then((r) => r.data),
};
