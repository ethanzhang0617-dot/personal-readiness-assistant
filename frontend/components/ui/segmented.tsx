"use client";

import { cn } from "@/lib/utils";

export interface SegmentedOption<T extends string | number> {
  value: T;
  label: string;
  hint?: string;
}

/**
 * Segmented control: fast, touch-sized selection for short option sets — the
 * 1–5 wellness scales, the Insights window, the calibration answers and the
 * appearance preference.
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
    <div
      className={cn("flex gap-1 rounded-[var(--radius-control)] bg-surface-muted p-1", className)}
      role="group"
      aria-label={label}
    >
      {options.map((option) => {
        const active = option.value === value;
        return (
          <button
            key={String(option.value)}
            type="button"
            aria-pressed={active}
            onClick={() => onChange(option.value)}
            className={cn(
              "flex-1 rounded-[0.65rem] font-semibold transition-[background-color,color,box-shadow] duration-150",
              // Touch targets stay 44px on small screens; the compact size is a
              // desktop-only density choice.
              size === "md" ? "min-h-11" : "min-h-11 md:min-h-9",
              active
                ? "bg-surface text-foreground shadow-[var(--shadow-soft)]"
                : "text-muted hover:text-foreground",
            )}
          >
            <span className="block px-2 text-[0.84rem] leading-tight">{option.label}</span>
            {option.hint && active ? (
              <span className="mt-0.5 block text-[0.62rem] font-normal text-muted">{option.hint}</span>
            ) : null}
          </button>
        );
      })}
    </div>
  );
}
