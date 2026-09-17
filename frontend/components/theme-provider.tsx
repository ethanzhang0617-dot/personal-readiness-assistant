"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useSyncExternalStore, type ReactNode } from "react";

import {
  applyTheme,
  readStoredTheme,
  resolveTheme,
  storeTheme,
  systemPrefersDark,
  THEME_EVENT,
  type ResolvedTheme,
  type ThemeMode,
} from "@/lib/theme";

interface ThemeContextValue {
  mode: ThemeMode;
  resolved: ResolvedTheme;
  setMode: (mode: ThemeMode) => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

/**
 * Appearance provider.
 *
 * The inline script in the document head has already applied the correct theme
 * before first paint; this keeps it correct afterwards, follows the operating
 * system while the preference is "System", and never re-renders product data —
 * a theme change swaps CSS variables only.
 */

function subscribePreference(onChange: () => void) {
  window.addEventListener("storage", onChange);
  window.addEventListener(THEME_EVENT, onChange);
  return () => {
    window.removeEventListener("storage", onChange);
    window.removeEventListener(THEME_EVENT, onChange);
  };
}

function subscribeSystem(onChange: () => void) {
  if (!window.matchMedia) return () => {};
  const media = window.matchMedia("(prefers-color-scheme: dark)");
  media.addEventListener("change", onChange);
  return () => media.removeEventListener("change", onChange);
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const mode = useSyncExternalStore(subscribePreference, readStoredTheme, () => "system" as ThemeMode);
  const prefersDark = useSyncExternalStore(subscribeSystem, systemPrefersDark, () => false);
  const resolved = resolveTheme(mode, prefersDark);

  useEffect(() => {
    applyTheme(resolved);
  }, [resolved]);

  const setMode = useCallback((next: ThemeMode) => {
    storeTheme(next);
  }, []);

  const value = useMemo(() => ({ mode, resolved, setMode }), [mode, resolved, setMode]);

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const context = useContext(ThemeContext);
  if (!context) throw new Error("useTheme must be used inside ThemeProvider");
  return context;
}
