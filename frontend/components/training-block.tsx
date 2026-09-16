import type { TrainingRecommendation } from "@/types/api";

/**
 * WHAT TO TRAIN and HOW HARD are two different answers; they must not be merged
 * into one row of equal-weight cards.
 */
export function TrainingBlock({ recommendation }: { recommendation: TrainingRecommendation }) {
  const range = recommendation.estimated_duration_min_range;
  const duration = range && range.length > 1 ? `${range[0]}–${range[1]} min` : recommendation.duration;
  return (
    <section className="rounded-[var(--radius-card)] border border-subtle bg-surface">
      <div className="p-4 md:p-5">
        <p className="eyebrow text-muted">Today&apos;s training</p>
        <h2 className="mt-2 text-[1.45rem] font-semibold leading-tight tracking-tight">
          {recommendation.primary_name}
        </h2>
          <p className="mt-1 text-[0.82rem] text-muted">
          {[recommendation.training_type, recommendation.focus, duration].filter(Boolean).join(" · ")}
        </p>
        {recommendation.muscle_groups.length > 0 ? (
          <p className="mt-2 text-[0.72rem] text-muted">
            {recommendation.muscle_groups.join(" · ")}
          </p>
        ) : null}
      </div>

      <div className="grid grid-cols-2 gap-px border-t border-subtle bg-subtle">
        <div className="bg-surface p-4">
          <p className="eyebrow text-muted">How hard</p>
          <p className="mt-1 text-base font-semibold">{recommendation.session_demand}</p>
          <p className="mt-0.5 text-[0.72rem] text-muted">
            {recommendation.rir_guidance ?? "Effort guidance unavailable"}
          </p>
        </div>
        <div className="bg-surface p-4">
          <p className="eyebrow text-muted">Session length</p>
          <p className="mt-1 text-base font-semibold">{duration}</p>
          <p className="mt-0.5 text-[0.72rem] text-muted">duration in minutes</p>
        </div>
      </div>
    </section>
  );
}
