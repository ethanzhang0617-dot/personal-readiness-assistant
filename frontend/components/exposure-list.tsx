import { formatNumber } from "@/lib/format";
import type { WeeklyExposure } from "@/types/api";
import { cn } from "@/lib/utils";

// Weekly exposure: one track per muscle group showing recorded work against the
// configured target. The direct-1.0 / secondary-0.5 counting rule is unchanged;
// this only presents it as a readable progress list instead of a table.

export function ExposureList({ exposure, className }: { exposure: WeeklyExposure; className?: string }) {
  return (
    <div className={cn("space-y-3", className)}>
      <ul className="space-y-3">
        {exposure.groups.map((group) => {
          const target = group.target ?? 0;
          const ratio = target > 0 ? Math.min(group.value / target, 1) : 0;
          const remaining = target > 0 ? Math.max(target - group.value, 0) : null;
          return (
            <li key={group.group}>
              <div className="flex items-baseline justify-between gap-3">
                <span className="text-[0.82rem] font-medium">{group.group}</span>
                <span className="text-[0.76rem] tabular-nums text-muted">
                  {formatNumber(group.value)}
                  {target > 0 ? ` / ${formatNumber(target)} sets` : " sets"}
                </span>
              </div>
              <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-subtle">
                <div
                  className={cn("h-full rounded-full", target > 0 && group.value >= target ? "bg-[var(--status-green)]" : "bg-primary")}
                  style={{ width: `${Math.round(ratio * 100)}%` }}
                />
              </div>
              {remaining !== null ? (
                <p className="mt-1 text-[0.68rem] text-muted">
                  {remaining > 0 ? `${formatNumber(remaining)} sets below target` : "At or above target"}
                </p>
              ) : null}
            </li>
          );
        })}
      </ul>
      <p className="text-[0.68rem] leading-relaxed text-muted">{exposure.note}</p>
      <p className="text-[0.68rem] text-muted">Target source: {exposure.target_source ?? "not recorded"}</p>
    </div>
  );
}
