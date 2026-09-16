import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export interface StatItem {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
}

/** Compact evidence row: three aligned facts, no boxes inside boxes. */
export function StatRow({ items, className }: { items: StatItem[]; className?: string }) {
  return (
    <dl className={cn("grid grid-cols-3 gap-px overflow-hidden rounded-[var(--radius-control)] bg-subtle", className)}>
      {items.map((item) => (
        <div key={item.label} className="bg-surface px-3 py-3">
          <dt className="text-[0.7rem] font-medium text-muted">{item.label}</dt>
          <dd className="mt-1 text-[0.95rem] font-semibold tabular-nums leading-tight">{item.value}</dd>
          {item.hint ? <dd className="mt-0.5 text-[0.68rem] text-muted">{item.hint}</dd> : null}
        </div>
      ))}
    </dl>
  );
}
