/**
 * AuthContext.tsx — V2 Unified Profile-Aware Auth Context
 *
 * Architecture:
 *  - JWT in localStorage (authentication only)
 *  - Full UserProfile fetched from GET /auth/profile after login
 *  - UIConfig fetched from GET /auth/me/ui-config after login
 *  - /auth/profile is the source of truth — NOT the JWT payload
 *  - On page refresh, profile is re-fetched to ensure freshness
 */

import { createContext, useContext, useState, useEffect, useCallback } from "react";
import { api } from "../api/client";
import type { ProfileType } from "../utils/ageUtils";

// ── Types ────────────────────────────────────────────────────────────────────

export interface UserProfile {
  id: number;
  email: string;
  full_name: string | null;
  is_active: boolean;
  profile_type: ProfileType;
  preferred_learning_mode: string | null;
  preferred_language: string;
  level: number;
  xp_points: number;
  user_streak: number;
  pending_parent_link: boolean;
}

export interface UIConfig {
  profile_type: ProfileType;
  theme: string;
  font_size: string;
  animations: boolean;
  sounds: boolean;
  confetti: boolean;
  tts_speed: string;
  difficulty_default: string;
  feedback_tone: string;
  gamification: string;
}

interface AuthContextType {
  token: string | null;
  user: UserProfile | null;
  uiConfig: UIConfig | null;
  profileType: ProfileType | null;
  isLoading: boolean;
  login: (token: string) => Promise<void>;
  logout: () => void;
  refreshProfile: () => Promise<void>;
  themeMode: "light" | "dark";
  toggleTheme: () => void;
}

// ── Context ──────────────────────────────────────────────────────────────────

const AuthCtx = createContext<AuthContextType>({
  token: null,
  user: null,
  uiConfig: null,
  profileType: null,
  isLoading: false,
  login: async () => {},
  logout: () => {},
  refreshProfile: async () => {},
  themeMode: "light",
  toggleTheme: () => {},
});

export const useAuth = () => useContext(AuthCtx);

// ── Provider ─────────────────────────────────────────────────────────────────

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(
    localStorage.getItem("token")
  );
  const [user, setUser] = useState<UserProfile | null>(() => {
    const saved = localStorage.getItem("user_profile");
    return saved ? JSON.parse(saved) : null;
  });
  const [uiConfig, setUiConfig] = useState<UIConfig | null>(() => {
    const saved = localStorage.getItem("ui_config");
    return saved ? JSON.parse(saved) : null;
  });
  const [isLoading, setIsLoading] = useState(false);

  const [themeMode, setThemeMode] = useState<"light" | "dark">(() => {
    const saved = localStorage.getItem("theme-mode");
    if (saved === "dark" || saved === "light") return saved;
    if (window.matchMedia("(prefers-color-scheme: dark)").matches) return "dark";
    return "light";
  });

  const toggleTheme = () => {
    setThemeMode((prev) => (prev === "light" ? "dark" : "light"));
  };

  useEffect(() => {
    const root = document.documentElement;
    if (themeMode === "dark") {
      root.classList.add("dark");
    } else {
      root.classList.remove("dark");
    }
    localStorage.setItem("theme-mode", themeMode);
  }, [themeMode]);

  const profileType: ProfileType | null = user?.profile_type ?? null;

  /**
   * Fetch and cache both /auth/profile and /auth/me/ui-config.
   * Called after login and on page refresh if token exists.
   */
  const refreshProfile = useCallback(async () => {
    if (!token) return;
    setIsLoading(true);
    try {
      const [profileRes, configRes] = await Promise.all([
        api.get<UserProfile>("/auth/profile"),
        api.get<UIConfig>("/auth/me/ui-config"),
      ]);

      const userProfile = profileRes.data;
      const uiCfg = configRes.data;

      setUser(userProfile);
      setUiConfig(uiCfg);

      // Cache in localStorage for instant page-refresh hydration
      localStorage.setItem("user_profile", JSON.stringify(userProfile));
      localStorage.setItem("ui_config", JSON.stringify(uiCfg));
    } catch (err) {
      console.error("Failed to refresh profile — logging out for safety", err);
      // If profile fetch fails (token expired etc.) — log out gracefully
      logout();
    } finally {
      setIsLoading(false);
    }
  }, [token]); // eslint-disable-line react-hooks/exhaustive-deps

  /**
   * Login: store token, then immediately hydrate profile.
   */
  const login = async (newToken: string) => {
    localStorage.setItem("token", newToken);
    setToken(newToken);
    // Profile fetch is triggered by the useEffect below watching [token]
  };

  const logout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user_profile");
    localStorage.removeItem("ui_config");
    setToken(null);
    setUser(null);
    setUiConfig(null);
  };

  // On mount or token change, re-hydrate profile from server
  useEffect(() => {
    if (token) {
      refreshProfile();
    }
  }, [token]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <AuthCtx.Provider
      value={{
        token,
        user,
        uiConfig,
        profileType,
        isLoading,
        login,
        logout,
        refreshProfile,
        themeMode,
        toggleTheme,
      }}
    >
      {children}
    </AuthCtx.Provider>
  );
}
