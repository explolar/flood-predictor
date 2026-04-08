import axios from "axios";

const API_BASE = import.meta.env.VITE_API_URL || "";

export const api = axios.create({
  baseURL: API_BASE,
  timeout: 120_000, // GEE calls can be slow
  headers: { "Content-Type": "application/json" },
});

/** Client with longer timeout for heavy multi-module endpoints (Impact, HAND). */
export const apiHeavy = axios.create({
  baseURL: API_BASE,
  timeout: 300_000, // 5 min for multi-step GEE workflows
  headers: { "Content-Type": "application/json" },
});

apiHeavy.interceptors.response.use(
  (res) => res,
  (err) => {
    const message =
      err.response?.data?.detail || err.response?.data?.error || err.message;
    return Promise.reject(new Error(message));
  }
);

// Response interceptor for consistent error handling
api.interceptors.response.use(
  (res) => res,
  (err) => {
    const message =
      err.response?.data?.detail || err.response?.data?.error || err.message;
    return Promise.reject(new Error(message));
  }
);
