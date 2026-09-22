import React, { createContext, useContext, useEffect, useState } from "react";
import { api, clearTokens, errorMessage, loadPersistedRefreshToken, setTokens } from "../lib/api";
import type { CurrentUser } from "../lib/types";

interface AuthState {
  user: CurrentUser | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const rt = loadPersistedRefreshToken();
    if (!rt) {
      setLoading(false);
      return;
    }
    api
      .post("/auth/refresh", { refresh_token: rt })
      .then((resp) => {
        setTokens(resp.data.access_token, resp.data.refresh_token);
        setUser(resp.data.user);
      })
      .catch(() => clearTokens())
      .finally(() => setLoading(false));
  }, []);

  async function login(email: string, password: string) {
    try {
      const resp = await api.post("/auth/login", { email, password });
      setTokens(resp.data.access_token, resp.data.refresh_token);
      setUser(resp.data.user);
    } catch (err) {
      throw new Error(errorMessage(err));
    }
  }

  function logout() {
    clearTokens();
    setUser(null);
  }

  return <AuthContext.Provider value={{ user, loading, login, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
