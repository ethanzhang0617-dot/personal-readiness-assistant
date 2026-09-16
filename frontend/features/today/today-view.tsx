"use client";

import Link from "next/link";
import { ArrowRight, ShieldCheck } from "lucide-react";

import { CheckInPrompt } from "@/components/check-in-prompt";
import { DecisionTrace } from "@/components/decision-trace";
import { ReadinessHero } from "@/components/readiness-hero";
import { StatePanel } from "@/components/state-panel";
import { TrainingDecision } from "@/components/training-decision";
import { buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useUserState } from "@/lib/state-provider";
import { cn } from "@/lib/utils";

// Today: the flagship screen. It answers four questions in a deliberate order —
// how am I today, what should I train, how hard, and why — and nothing else
// competes for attention.
//
// Mobile order: readiness, decision, action, check-in, explanation.
// Desktop: two columns (readiness + check-in | decision + action), then the
// full-width explanation, so the extra space is used rather than stretched.

export function TodayView() {
  const { ready, today, error } = useUserState();

  if (!ready) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-6 w-24" />
        <Skeleton className="h-[15rem] w-full rounded-[var(--radius-card)]" />
        <Skeleton className="h-24 w-full" />
      </div>
    );
  }

  if (!today) {
    return (
      <StatePanel
        tone="error"
        title="Today is unavailable right now"
        body={`${error ?? "The API did not return a readiness result."} Start the API and reload this page.`}
      />
    );
  }

  const { profile, readiness, training, why } = today;

  return (
    <div className="space-y-5">
      <header className="flex items-end justify-between gap-3">
        <div>
          <p className="eyebrow">Today</p>
          <h1 className="title-page mt-1">{profile.name}</h1>
        </div>
        <p className="text-right text-[0.75rem] leading-snug text-muted">
          {profile.training_goal}
          <br />
          {profile.training_split_preference}
        </p>
      </header>

      {readiness.safety_active ? (
        <StatePanel
          tone="error"
          title="Safety routing is active"
          body={`Recorded safety flags: ${readiness.safety_flags.join(", ") || "a current safety concern"}. Normal workout guidance is disabled; seek appropriate professional assessment for acute or concerning symptoms.`}
        />
      ) : null}

      <div className="grid grid-cols-[minmax(0,1fr)] gap-6 lg:grid-cols-2 lg:items-start lg:gap-x-10">
        <ReadinessHero readiness={readiness} className="lg:col-start-1 lg:row-start-1" />

        <TrainingDecision
          recommendation={training.recommendation}
          className="lg:col-start-2 lg:row-start-1"
        />

        <div className="lg:col-start-2 lg:row-start-2 lg:pt-6">
          <Link
            href="/train"
            className={cn(buttonVariants({ size: "lg" }), "w-full")}
            aria-label="Start session"
          >
            START SESSION
            <ArrowRight className="h-4 w-4" />
          </Link>
          <p className="mt-2 text-center text-[0.7rem] text-muted">
            Opens the session, the prescription and the completed-session log.
          </p>
        </div>

        <CheckInPrompt className="lg:col-start-1 lg:row-start-2 lg:pt-6" />

        <div className="lg:col-span-2 lg:row-start-3">
          <DecisionTrace
            steps={training.decision_trace}
            rationale={why.rationale}
            headline={why.headline}
          />
        </div>
      </div>

      <p className="flex items-center justify-center gap-1.5 text-center text-[0.7rem] text-muted">
        <ShieldCheck className="h-3.5 w-3.5" aria-hidden />
        Decision support only. Not a medical device, diagnosis or injury prediction.
      </p>
    </div>
  );
}
