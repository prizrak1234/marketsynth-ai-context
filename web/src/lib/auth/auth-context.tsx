"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  clearLegacyApiKeyStorage,
  fetchCurrentUser,
  loginWithPassword,
  logoutSession,
} from "@/lib/auth/auth-client";
import type { AuthError } from "@/lib/auth/auth-errors";
import type { AuthUser } from "@/lib/auth/session";

type AuthState = {
  user: AuthUser | null;
  loading: boolean;
  /** Login/submit-facing errors only (never anonymous /auth/me 401). */
  error: AuthError | null;
  login: (email: string, password: string) => Promise<boolean>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
  clearError: () => void;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<AuthError | null>(null);

  const clearError = useCallback(() => setError(null), []);

  const refresh = useCallback(async () => {
    clearLegacyApiKeyStorage();
    setLoading(true);
    const res = await fetchCurrentUser();
    if (res.ok) {
      setUser(res.user);
      setError(null);
    } else {
      setUser(null);
      // Do not surface anonymous auth_required as a login form error.
      // Only backend_unavailable from the session probe is worth showing.
      if (res.error.kind === "backend_unavailable") {
        setError(res.error);
      } else {
        setError(null);
      }
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const login = useCallback(async (email: string, password: string) => {
    setLoading(true);
    setError(null);
    const res = await loginWithPassword(email, password);
    if (!res.ok) {
      setUser(null);
      setError(res.error);
      setLoading(false);
      return false;
    }
    // Confirm cookie session is usable (detect cross-host SameSite failure).
    const me = await fetchCurrentUser();
    if (!me.ok) {
      setUser(null);
      setError({
        kind: "session_cookie_failed",
        message: "Не удалось создать сессию.",
        actionHint:
          "Откройте пилот по http://localhost:3000 и убедитесь, что API host совпадает (localhost).",
      });
      setLoading(false);
      return false;
    }
    setUser(me.user);
    setError(null);
    setLoading(false);
    return true;
  }, []);

  const logout = useCallback(async () => {
    await logoutSession();
    setUser(null);
    setError(null);
  }, []);

  const value = useMemo(
    () => ({ user, loading, error, login, logout, refresh, clearError }),
    [user, loading, error, login, logout, refresh, clearError],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return ctx;
}

/** For shared marketing surfaces that may render outside AuthProvider. */
export function useAuthOptional(): Pick<AuthState, "user" | "loading"> {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    return { user: null, loading: false };
  }
  return { user: ctx.user, loading: ctx.loading };
}
