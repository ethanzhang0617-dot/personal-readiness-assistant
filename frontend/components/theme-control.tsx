"use client";

import { Monitor, Moon, Sun, type LucideIcon } from "lucide-react";

import { useTheme } from "@/components/theme-provider";
import { THEME_MODES, type ThemeMode } from "@/lib/theme";
import { cn } from "@/lib/utils";

const ICONS: Record<ThemeMode, LucideIcon> = {
  system: Monitor,
  light: Sun,
  dark: Moon,
};

/**
 * Appearance preference. System / Light / Dark, stored locally and applied
 * before first paint. A preference row, not a feature.
 */
export function ThemeControl() {
  const { mode, resolved, setMode } = useTheme();

  return (
    <div className="space-y-2">
      <div role="group" aria-label="Appearance" className="flex gap-1 rounded-[var(--radius-control)] bg-surface-muted p-1">
        {THEME_MODES.map((option) => {
          const active = option.value === mode;
          const Icon = ICONS[option.value];
          return (
            <button
              key={option.value}
              type="button"
              aria-pressed={active}
              onClick={() => setMode(option.value)}
              className={cn(
                "flex min-h-11 flex-1 items-center justify-center gap-1.5 rounded-[0.6rem] text-[0.82rem] font-semibold transition-colors md:min-h-9",
                active ? "bg-surface text-foreground shadow-[var(--shadow-soft)]" : "text-muted hover:text-foreground",
              )}
            >
              <Icon className="h-3.5 w-3.5" aria-hidden />
              {option.label}
            </button>
          );
        })}
      </div>
      <p className="text-[0.72rem] leading-relaxed text-muted">
        {mode === "system"
          ? `Following your device, currently ${resolved}.`
          : `Always ${mode}, regardless of your device setting.`}
      </p>
    </div>
  );
}
