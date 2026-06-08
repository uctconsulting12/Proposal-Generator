import api from "./client.js";

export const authApi = {
  signup: (email, password) =>
    api.post("/auth/signup", { email, password }).then((r) => r.data),
  signin: (email, password) =>
    api.post("/auth/signin", { email, password }).then((r) => r.data),
  me: () => api.get("/auth/me").then((r) => r.data),
};
