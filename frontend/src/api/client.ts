import axios from "axios";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8080";

export const api = axios.create({
  baseURL: API_BASE,
  timeout: 120_000, // GEE calls can be slow
  headers: { "Content-Type": "application/json" },
});

// Response interceptor for consistent error handling
api.interceptors.response.use(
  (res) => res,
  (err) => {
    const message =
      err.response?.data?.detail || err.response?.data?.error || err.message;
    return Promise.reject(new Error(message));
  }
);
