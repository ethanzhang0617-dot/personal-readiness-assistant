import { StatusBadge } from "@/components/status-badge";
import { statusTone } from "@/lib/format";
import type { ReadinessSummary } from "@/types/api";
import { cn } from "@/lib/utils";

/**
 * The readiness hero: one intentional number, one status, one interpretation.
 * No gauge and no decoration — the largest type on the screen is the answer.
 */
export function ReadinessHero({ readiness, className }: { readiness: ReadinessSummary; className?: string }) {
  const index = readiness.index;
  const max = readiness.index_scale?.max ?? 100;
  const limited = readiness.confidence && readiness.confidence !== "NORMAL";

  return (
    <section className={cn("surface-raised min-w-0 overflow-hidden", className)}>
      <div className="flex items-start justify-between gap-5 p-5">
        <div className="min-w-0 space-y-3">
          <p className="eyebrow">Readiness</p>
          <StatusBadge status={readiness.status} />
          <p className="line-clamp-3 max-w-[30ch] text-[0.95rem] leading-snug">
            {readiness.explanation ?? "No readiness interpretation is available for today."}
          </p>
        </div>

        <div className="shrink-0 text-right">
          <p className="display-hero">{index ?? "—"}</p>
          <p className="mt-1 text-[0.72rem] font-medium text-muted">
            {index === null ? "index unavailable" : `/ ${max} index`}
          </p>
        </div>
      </div>

      {readiness.domains.length > 0 ? (
        <dl className="grid grid-cols-2 gap-x-4 gap-y-2 border-t border-subtle px-5 py-3.5 md:grid-cols-4">
          {readiness.domains.map((domain) => {
            const tone = statusTone(domain.status);
            return (
              <div key={domain.key}>
                <dt className="text-[0.68rem] leading-tight text-muted">{domain.label}</dt>
                <dd className="mt-1 flex items-center gap-1.5">
                  <span className={cn("h-1.5 w-1.5 rounded-full", tone.dot)} aria-hidden />
                  <span className="text-[0.78rem] font-semibold">{domain.status}</span>
                </dd>
              </div>
            );
          })}
        </dl>
      ) : null}

      <p className="border-t border-subtle px-5 py-2.5 text-[0.7rem] text-muted">
        {limited
          ? readiness.confidence_note
          : `Compared with your own baseline (${readiness.confidence?.toLowerCase() ?? "unknown"} confidence).`}
      </p>
    </section>
  );
}
