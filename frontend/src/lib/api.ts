import axios, { AxiosError } from "axios";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

export const api = axios.create({ baseURL: API_BASE });

let accessToken: string | null = null;
let refreshToken: string | null = null;

export function setTokens(access: string, refresh: string) {
  accessToken = access;
  refreshToken = refresh;
  sessionStorage.setItem("c360_refresh", refresh);
}

export function loadPersistedRefreshToken(): string | null {
  return sessionStorage.getItem("c360_refresh");
}

export function clearTokens() {
  accessToken = null;
  refreshToken = null;
  sessionStorage.removeItem("c360_refresh");
}

export function getAccessToken() {
  return accessToken;
}

api.interceptors.request.use((config) => {
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }
  return config;
});

let refreshing: Promise<string | null> | null = null;

async function tryRefresh(): Promise<string | null> {
  const rt = refreshToken ?? loadPersistedRefreshToken();
  if (!rt) return null;
  try {
    const resp = await axios.post(`${API_BASE}/auth/refresh`, { refresh_token: rt });
    setTokens(resp.data.access_token, resp.data.refresh_token);
    return resp.data.access_token;
  } catch {
    clearTokens();
    return null;
  }
}

api.interceptors.response.use(
  (r) => r,
  async (error: AxiosError) => {
    const original = error.config;
    if (error.response?.status === 401 && original && !(original as any)._retried) {
      (original as any)._retried = true;
      if (!refreshing) refreshing = tryRefresh().finally(() => (refreshing = null));
      const newToken = await refreshing;
      if (newToken) {
        original.headers = original.headers ?? {};
        (original.headers as any).Authorization = `Bearer ${newToken}`;
        return api.request(original);
      }
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

export interface ApiErrorBody {
  error: { code: string; message: string; request_id: string; details?: Record<string, unknown> };
}

export function errorMessage(err: unknown): string {
  const axiosErr = err as AxiosError<ApiErrorBody>;
  return axiosErr?.response?.data?.error?.message ?? "Something went wrong. Please try again.";
}
