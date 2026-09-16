import Link from "next/link";
import { ArrowRight, ShieldCheck } from "lucide-react";

import { DecisionTrace } from "@/components/decision-trace";
import { ReadinessHero } from "@/components/readiness-hero";
import { StatePanel } from "@/components/state-panel";
import { TrainingBlock } from "@/components/training-block";
import { buttonVariants } from "@/components/ui/button";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

/**
 * Today: readiness answer, training answer, effort answer, then the CTA.
 * Everything comes from the API; no personal value is hardcoded here.
 */
export async function TodayView({ profileId }: { profileId?: string }) {
  const result = await api.today(profileId);

  if (!result.ok) {
    return (
      <StatePanel
        tone="error"
        title="Today is unavailable right now"
        body={result.error}
      />
    );
  }

  const { profile, readiness, training, why } = result.data;

  return (
    <div className="space-y-3 md:space-y-4">
      <div className="flex items-end justify-between gap-3">
        <div>
          <p className="eyebrow text-muted">Today</p>
          <h1 className="text-[1.6rem] font-semibold tracking-tight md:text-[1.9rem]">
            {profile.name}
          </h1>
        </div>
        <p className="text-right text-[0.7rem] text-muted">
          {profile.training_goal}
          <br />
          {profile.training_split_preference}
        </p>
      </div>

      {readiness.safety_active ? (
        <StatePanel
          tone="error"
          title="Safety routing is active"
          body={`Recorded safety flags: ${readiness.safety_flags.join(", ") || "a current safety concern"}. Normal workout guidance is disabled; seek appropriate professional assessment for acute or concerning symptoms.`}
        />
      ) : null}

      <ReadinessHero readiness={readiness} />
      <TrainingBlock recommendation={training.recommendation} />
      <DecisionTrace
        steps={training.decision_trace}
        rationale={why.rationale}
        headline={why.headline}
      />

      <Link
        href="/train"
        className={cn(buttonVariants({ size: "lg" }), "w-full")}
        aria-label="Start session"
      >
        START SESSION
        <ArrowRight className="h-4 w-4" />
      </Link>

      <p className="flex items-center justify-center gap-1.5 text-center text-[0.68rem] text-muted">
        <ShieldCheck className="h-3.5 w-3.5" aria-hidden />
        Decision support only. Not a medical device, diagnosis or injury prediction.
      </p>
    </div>
  );
}
