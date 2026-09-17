"use client";

import { Moon, Sun } from "lucide-react";

import { useTheme } from "@/components/theme-provider";
import { cn } from "@/lib/utils";

/**
 * Compact appearance toggle. It flips between Light and Dark; System stays
 * available in Profile → Appearance. Deliberately quiet — a preference, not a
 * product feature.
 */
export function ThemeToggle({ className }: { className?: string }) {
  const { resolved, setMode } = useTheme();
  const next = resolved === "dark" ? "light" : "dark";
  return (
    <button
      type="button"
      onClick={() => setMode(next)}
      aria-label={`Switch to ${next} appearance`}
      title={`Switch to ${next} appearance`}
      className={cn(
        "inline-flex h-9 w-9 items-center justify-center rounded-full text-muted transition-colors hover:bg-surface-muted hover:text-foreground",
        className,
      )}
    >
      {resolved === "dark" ? <Moon className="h-4 w-4" aria-hidden /> : <Sun className="h-4 w-4" aria-hidden />}
    </button>
  );
}
