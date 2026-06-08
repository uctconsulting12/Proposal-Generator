import axios from "axios";

const TOKEN_KEY = "copilot_jwt";

export const tokenStore = {
  get: () => (localStorage.getItem(TOKEN_KEY) || "").trim() || null,
  set: (token) => localStorage.setItem(TOKEN_KEY, token),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

export const api = axios.create({
  baseURL: "/api",
  timeout: 200_000,
});

api.interceptors.request.use((config) => {
  const token = tokenStore.get();
  if (token) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const data = error?.response?.data;
    const message =
      (data && (data.error || data.detail || data.message)) ||
      error?.message ||
      "Request failed";
    const wrapped = new Error(message);
    wrapped.status = error?.response?.status;
    wrapped.data = data;
    return Promise.reject(wrapped);
  }
);

export default api;
