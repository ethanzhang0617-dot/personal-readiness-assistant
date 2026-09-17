import { ChevronRight, type LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

import { statusVar } from "@/lib/format";
import { cn } from "@/lib/utils";

/**
 * A single line in an open vertical layout: icon, label, short status, optional
 * value and an optional chevron. Used by Readiness contributors and Insights
 * modules instead of stacking cards.
 */
export function StatusRow({
  icon: Icon,
  label,
  status,
  statusLabel,
  value,
  href,
  detail,
  className,
}: {
  icon?: LucideIcon;
  label: string;
  status?: string;
  statusLabel?: string;
  value?: ReactNode;
  href?: string;
  detail?: ReactNode;
  className?: string;
}) {
  const body = (
    <>
      {Icon ? (
        <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-surface-secondary text-muted">
          <Icon className="h-4 w-4" aria-hidden />
        </span>
      ) : status ? (
        <span
          className="mt-2 h-2.5 w-2.5 shrink-0 rounded-full"
          style={{ backgroundColor: statusVar(status) }}
          aria-hidden
        />
      ) : null}

      <span className="min-w-0 flex-1">
        <span className="flex items-baseline justify-between gap-3">
          <span className="truncate text-[0.9rem] font-medium">{label}</span>
          {value ? <span className="shrink-0 text-[0.85rem] font-semibold tabular-nums">{value}</span> : null}
        </span>
        {statusLabel ? (
          <span className="mt-0.5 block text-[0.8rem]" style={status ? { color: statusVar(status) } : undefined}>
            {statusLabel}
          </span>
        ) : null}
        {detail ? <span className="mt-1 block text-[0.76rem] leading-relaxed text-muted">{detail}</span> : null}
      </span>

      {href ? <ChevronRight className="mt-1 h-4 w-4 shrink-0 text-muted" aria-hidden /> : null}
    </>
  );

  const classes = cn("flex w-full items-start gap-3 py-3.5 text-left", href && "transition-colors hover:opacity-80", className);

  return href ? (
    <a href={href} className={classes}>
      {body}
    </a>
  ) : (
    <div className={classes}>{body}</div>
  );
}
