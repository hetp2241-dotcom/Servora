import axios from "axios";

function cookie(name: string) {
  return document.cookie.split(";").map((item) => item.trim()).find((item) => item.startsWith(`${name}=`))?.split("=").slice(1).join("=") ?? "";
}

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "/api",
  withCredentials: true,
  headers: { Accept: "application/json" }
});

api.interceptors.request.use((config) => {
  const token = decodeURIComponent(cookie("csrftoken"));
  if (token) config.headers.set("X-CSRFToken", token);
  return config;
});

export async function ensureCsrf() {
  await api.get("/csrf/");
}

export function formData(values: Record<string, string | number | boolean | File | null | undefined>) {
  const data = new FormData();
  Object.entries(values).forEach(([key, value]) => {
    if (value !== null && value !== undefined) data.append(key, value instanceof File ? value : String(value));
  });
  return data;
}

export function websocketUrl(path: string) {
  const configured = import.meta.env.VITE_WS_BASE_URL;

  // If the environment provides an explicit WS base URL, use it.
  // This keeps production compatibility and supports deployments behind a different host.
  if (configured) return `${configured.replace(/\/$/, "")}${path}`;

  // Dev fallback: connect to the same origin the browser is on (Vite).
  // Note: Vite proxy must have ws: true configured for /ws.
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}${path}`;
}

