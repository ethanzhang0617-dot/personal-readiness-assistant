"use client";

import Link from "next/link";
import { ArrowRight, ShieldCheck } from "lucide-react";

import { CheckInPrompt } from "@/components/check-in-prompt";
import { DecisionTrace } from "@/components/decision-trace";
import { ReadinessHero } from "@/components/readiness-hero";
import { StatePanel } from "@/components/state-panel";
import { TrainingBlock } from "@/components/training-block";
import { buttonVariants } from "@/components/ui/button";
import { useUserState } from "@/lib/state-provider";
import { cn } from "@/lib/utils";

/**
 * Today: readiness answer, training answer, effort answer, then the CTA.
 * Everything comes from the engines through the API; the user's own data lives
 * in this browser.
 */
export function TodayView() {
  const { ready, today, error } = useUserState();

  if (!ready) {
    return <StatePanel title="Loading your readiness context…" body="Reading local data and recalculating from the engines." />;
  }

  if (!today) {
    return (
      <StatePanel
        tone="error"
        title="Today is unavailable right now"
        body={error ?? "The API did not return a readiness result."}
      />
    );
  }

  const { profile, readiness, training, why } = today;

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
      <CheckInPrompt />
      <Link href="/train" className={cn(buttonVariants({ size: "lg" }), "w-full")} aria-label="Start session">
        START SESSION
        <ArrowRight className="h-4 w-4" />
      </Link>
      <DecisionTrace
        steps={training.decision_trace}
        rationale={why.rationale}
        headline={why.headline}
      />

      <p className="flex items-center justify-center gap-1.5 text-center text-[0.68rem] text-muted">
        <ShieldCheck className="h-3.5 w-3.5" aria-hidden />
        Decision support only. Not a medical device, diagnosis or injury prediction.
      </p>
    </div>
  );
}
