import { formatNumber } from "@/lib/format";
import type { WeeklyExposure } from "@/types/api";
import { cn } from "@/lib/utils";

// Weekly exposure: one track per muscle group showing recorded work against the
// configured target. The direct-1.0 / secondary-0.5 counting rule is unchanged;
// only the presentation is.

export function ExposureList({ exposure, className }: { exposure: WeeklyExposure; className?: string }) {
  return (
    <div className={cn("space-y-4", className)}>
      <ul className="space-y-3.5">
        {exposure.groups.map((group) => {
          const target = group.target ?? 0;
          const ratio = target > 0 ? Math.min(group.value / target, 1) : 0;
          const remaining = target > 0 ? Math.max(target - group.value, 0) : null;
          const complete = target > 0 && group.value >= target;
          return (
            <li key={group.group}>
              <div className="flex items-baseline justify-between gap-3">
                <span className="text-[0.86rem] font-medium">{group.group}</span>
                <span className="text-[0.78rem] tabular-nums text-muted">
                  {formatNumber(group.value)}
                  {target > 0 ? ` / ${formatNumber(target)}` : ""}
                </span>
              </div>
              <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-surface-muted">
                <div
                  className={cn("h-full rounded-full", complete ? "bg-[var(--status-green)]" : "bg-accent")}
                  style={{ width: `${Math.round(ratio * 100)}%` }}
                />
              </div>
              {remaining !== null ? (
                <p className="mt-1.5 text-[0.72rem] text-muted">
                  {remaining > 0 ? `${formatNumber(remaining)} sets below target` : "At or above target"}
                </p>
              ) : null}
            </li>
          );
        })}
      </ul>
      <p className="text-[0.72rem] leading-relaxed text-muted">{exposure.note}</p>
      <p className="text-[0.72rem] text-muted">Target source: {exposure.target_source ?? "not recorded"}</p>
    </div>
  );
}
