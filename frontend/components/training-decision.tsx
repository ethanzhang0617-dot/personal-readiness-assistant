import { StatRow } from "@/components/ui/stat-row";
import type { TrainingRecommendation } from "@/types/api";
import { cn } from "@/lib/utils";

/**
 * The decision, not a metric. WHAT TO TRAIN is the headline; how hard, duration
 * and effort are its supporting facts in one aligned row.
 */
export function TrainingDecision({
  recommendation,
  className,
}: {
  recommendation: TrainingRecommendation;
  className?: string;
}) {
  const range = recommendation.estimated_duration_min_range;
  const duration = range && range.length > 1 ? `${range[0]}–${range[1]} min` : recommendation.duration;
  const rir = recommendation.rir_guidance ? recommendation.rir_guidance.replace(/RIR/i, "").trim() : null;

  return (
    <section className={cn("space-y-3", className)}>
      <div>
        <p className="eyebrow">Today&apos;s training</p>
        <h2 className="mt-1.5 text-[1.75rem] font-semibold leading-[1.1] tracking-[-0.02em]">
          {recommendation.primary_name}
        </h2>
        <p className="mt-1 text-sm text-muted">
          {[recommendation.training_type, recommendation.focus, recommendation.muscle_groups.join(" · ")]
            .filter(Boolean)
            .join(" · ")}
        </p>
      </div>

      <StatRow
        items={[
          { label: "How hard", value: recommendation.session_demand },
          { label: "Duration", value: duration },
          { label: "Effort", value: rir ? `${rir} RIR` : "—" },
        ]}
      />

      {recommendation.adaptation ? (
        <p className="text-[0.74rem] leading-relaxed text-muted">
          <span className="font-semibold text-foreground">{recommendation.adaptation.label}</span>
          {recommendation.adaptation.from && recommendation.adaptation.to
            ? ` · ${recommendation.adaptation.from} → ${recommendation.adaptation.to} demand`
            : ""}
        </p>
      ) : null}
    </section>
  );
}
