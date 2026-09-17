import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

/**
 * A lightweight supporting metric. Deliberately not a card: three of these sit
 * in one row under the primary decision.
 */
export function MetricChip({
  label,
  value,
  hint,
  className,
}: {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("min-w-0 flex-1 px-1", className)}>
      <p className="text-[0.68rem] font-medium tracking-[0.06em] text-muted uppercase">{label}</p>
      <p className="mt-1 truncate text-[1.05rem] font-semibold tabular-nums leading-tight">{value}</p>
      {hint ? <p className="mt-0.5 truncate text-[0.7rem] text-muted">{hint}</p> : null}
    </div>
  );
}

export function MetricChipRow({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div
      className={cn(
        "flex items-stretch gap-3 divide-x-0 rounded-[var(--radius-card)] bg-surface-secondary px-4 py-3.5",
        className,
      )}
    >
      {children}
    </div>
  );
}
