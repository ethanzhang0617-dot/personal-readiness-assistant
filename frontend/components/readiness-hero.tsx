import type { ReadinessSummary } from "@/types/api";

import { StatusBadge } from "@/components/status-badge";

/**
 * The dominant element of Today: one readiness answer, one number, one sentence.
 * Everything detailed lives behind WHY below it.
 */
export function ReadinessHero({ readiness }: { readiness: ReadinessSummary }) {
  const index = readiness.index;
  const max = readiness.index_scale?.max ?? 100;
  return (
    <section className="rounded-[var(--radius-card)] border border-subtle bg-surface p-4 md:p-5">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 space-y-2.5">
          <p className="eyebrow text-muted">Readiness</p>
          <StatusBadge status={readiness.status} />
          <p className="line-clamp-2 text-sm leading-relaxed text-muted">
            {readiness.explanation ?? "No readiness explanation is available for today yet."}
          </p>
        </div>
        <div className="shrink-0 text-right">
          <p className="numeric-hero text-[2.9rem] font-semibold tabular-nums md:text-[3.1rem]">
            {index ?? "—"}
          </p>
          <p className="mt-0.5 text-[0.7rem] text-muted">
            {index === null ? "index unavailable" : `/ ${max} index`}
          </p>
          <p className="text-[0.7rem] text-muted">
            baseline {readiness.confidence?.toLowerCase() ?? "unknown"}
          </p>
        </div>
      </div>

      {readiness.domains.length > 0 ? (
        <dl className="mt-3 grid grid-cols-2 gap-x-3 gap-y-1.5 border-t border-subtle pt-2.5 md:grid-cols-4">
          {readiness.domains.map((domain) => (
            <div key={domain.key} className="flex items-center justify-between gap-2 md:block">
              <dt className="text-[0.68rem] text-muted md:mb-0.5">{domain.label}</dt>
              <dd className="text-[0.7rem] font-semibold">{domain.status}</dd>
            </div>
          ))}
        </dl>
      ) : null}

      {/* Only shown when the baseline is genuinely limited or insufficient. */}
      {readiness.confidence_note && readiness.confidence !== "NORMAL" ? (
        <p className="mt-2.5 text-[0.7rem] text-muted">{readiness.confidence_note}</p>
      ) : null}
    </section>
  );
}
