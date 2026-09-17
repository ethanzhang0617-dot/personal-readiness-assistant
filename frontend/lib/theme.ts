/**
 * Appearance preference: Light, Dark or System.
 *
 * This is presentation only. The preference lives in localStorage, never in a
 * product record, and the resolved theme is applied as a class on <html> so the
 * CSS variables swap without re-rendering any product data.
 */

export type ThemeMode = "system" | "light" | "dark";
export type ResolvedTheme = "light" | "dark";

export const THEME_STORAGE_KEY = "pra.appearance";
/** Fired after the stored preference changes so listeners can re-read it. */
export const THEME_EVENT = "pra:appearance";

export const THEME_MODES: { value: ThemeMode; label: string }[] = [
  { value: "system", label: "System" },
  { value: "light", label: "Light" },
  { value: "dark", label: "Dark" },
];

export function isThemeMode(value: unknown): value is ThemeMode {
  return value === "system" || value === "light" || value === "dark";
}

/** Client-only: read the stored preference, defaulting to System. */
export function readStoredTheme(): ThemeMode {
  if (typeof window === "undefined") return "system";
  try {
    const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
    return isThemeMode(stored) ? stored : "system";
  } catch {
    return "system";
  }
}

export function storeTheme(mode: ThemeMode): void {
  try {
    window.localStorage.setItem(THEME_STORAGE_KEY, mode);
  } catch {
    /* Private mode or a blocked store: the preference simply does not persist. */
  }
  window.dispatchEvent(new Event(THEME_EVENT));
}

export function systemPrefersDark(): boolean {
  if (typeof window === "undefined" || !window.matchMedia) return false;
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

export function resolveTheme(mode: ThemeMode, prefersDark: boolean): ResolvedTheme {
  if (mode === "system") return prefersDark ? "dark" : "light";
  return mode;
}

export function applyTheme(resolved: ResolvedTheme): void {
  if (typeof document === "undefined") return;
  const root = document.documentElement;
  root.classList.toggle("dark", resolved === "dark");
  root.style.colorScheme = resolved;
}

/**
 * Runs before first paint so the correct theme is already applied — no white
 * flash before dark, no dark flash before light.
 */
export const THEME_INIT_SCRIPT = `(function(){try{var k="${THEME_STORAGE_KEY}";var s=localStorage.getItem(k);var m=(s==="light"||s==="dark")?s:"system";var d=m==="dark"||(m==="system"&&window.matchMedia&&window.matchMedia("(prefers-color-scheme: dark)").matches);var r=document.documentElement;r.classList.toggle("dark",!!d);r.style.colorScheme=d?"dark":"light";}catch(e){}})();`;
