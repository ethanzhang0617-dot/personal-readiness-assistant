"use client";

import { cn } from "@/lib/utils";

export interface SegmentedOption<T extends string | number> {
  value: T;
  label: string;
  hint?: string;
}

/**
 * Segmented control: fast, touch-sized selection for short option sets such as
 * the 1–5 wellness scales or the Insights time window.
 */
export function Segmented<T extends string | number>({
  options,
  value,
  onChange,
  label,
  size = "md",
  className,
}: {
  options: SegmentedOption<T>[];
  value: T;
  onChange: (value: T) => void;
  label?: string;
  size?: "sm" | "md";
  className?: string;
}) {
  return (
    <div className={cn("flex gap-1 rounded-[var(--radius-control)] bg-surface-muted p-1", className)} role="group" aria-label={label}>
      {options.map((option) => {
        const active = option.value === value;
        return (
          <button
            key={String(option.value)}
            type="button"
            aria-pressed={active}
            onClick={() => onChange(option.value)}
            className={cn(
              "flex-1 rounded-[0.6rem] font-semibold transition-colors",
              size === "md" ? "min-h-11" : "min-h-9",
              active ? "bg-primary text-primary-foreground" : "text-muted hover:bg-subtle/60",
            )}
          >
            <span className="block text-sm leading-tight">{option.label}</span>
            {option.hint && active ? (
              <span className="mt-0.5 block text-[0.62rem] font-normal opacity-80">{option.hint}</span>
            ) : null}
          </button>
        );
      })}
    </div>
  );
}
