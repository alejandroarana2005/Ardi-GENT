import axios, { type AxiosError } from "axios";

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1",
  headers: { "Content-Type": "application/json" },
  timeout: 15_000,
});

// Log errors without breaking the UI — callers decide how to surface them
apiClient.interceptors.response.use(
  res => res,
  (err: AxiosError) => {
    const status = err.response?.status;
    const url    = err.config?.url;
    if (err.code === "ECONNREFUSED" || err.code === "ERR_NETWORK") {
      console.error(`[HAIA API] Backend no disponible (${url})`);
    } else {
      console.error(`[HAIA API] ${status ?? "ERR"} ${url}`, err.response?.data ?? err.message);
    }
    return Promise.reject(err);
  },
);
