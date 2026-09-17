"use client";

import Link from "next/link";
import { ArrowRight, ShieldCheck } from "lucide-react";

import { CheckInPrompt } from "@/components/check-in-prompt";
import { StatePanel } from "@/components/state-panel";
import { StatusBadge } from "@/components/status-badge";
import { buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { StatRow } from "@/components/ui/stat-row";
import { formatNumber } from "@/lib/format";
import { useUserState } from "@/lib/state-provider";
import type { TrainingRecommendation, WeeklyExposure } from "@/types/api";
import { cn } from "@/lib/utils";

// Today answers one question: what should I do today?
//
// Hierarchy on purpose — decision first, then a single reason, then up to three
// light indicators. Readiness detail, the Decision Trace and the Decision
// Explorer are deliberate secondary destinations, so nothing here competes with
// the decision or pushes Start Session below the first viewport.

/** The exposure row that belongs to today's focus, so the number is meaningful. */
function focusExposure(exposure: WeeklyExposure | undefined, recommendation: TrainingRecommendation) {
  if (!exposure) return null;
  const wanted = [recommendation.focus, ...recommendation.muscle_groups]
    .filter((value): value is string => Boolean(value))
    .map((value) => value.toLowerCase());
  return (
    exposure.groups.find((group) => wanted.includes(group.group.toLowerCase())) ??
    exposure.groups.find((group) =>
      wanted.some((value) => value.includes(group.group.toLowerCase()) || group.group.toLowerCase().includes(value)),
    ) ??
    null
  );
}

export function TodayView() {
  const { ready, today, error } = useUserState();

  if (!ready) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-6 w-24" />
        <Skeleton className="h-[13rem] w-full rounded-[var(--radius-card)]" />
        <Skeleton className="h-20 w-full" />
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
  const recommendation = training.recommendation;
  const range = recommendation.estimated_duration_min_range;
  const duration = range && range.length > 1 ? `${range[0]}–${range[1]} min` : recommendation.duration;
  const rir = recommendation.rir_guidance ? recommendation.rir_guidance.replace(/RIR/i, "").trim() : null;
  const reason = recommendation.rationale?.[0] ?? why.headline;
  const confidence = recommendation.recommendation_confidence ?? null;
  const exposure = focusExposure(training.exposure, recommendation);
  const adaptation = recommendation.adaptation ?? null;

  return (
    <div className="space-y-6">
      <header className="flex items-end justify-between gap-3">
        <div>
          <p className="eyebrow">Today</p>
          <h1 className="title-page mt-1">{profile.name}</h1>
        </div>
        <p className="text-right text-[0.72rem] leading-snug text-muted">
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

      {/* Level 1 — the decision, and the only action. */}
      <section className="surface-raised px-5 py-5">
        <div className="flex items-center justify-between gap-3">
          <StatusBadge status={readiness.status} />
          <p className="text-[0.72rem] text-muted">
            Readiness
            <span className="ml-1.5 font-semibold tabular-nums text-foreground">{readiness.index ?? "—"}</span>
          </p>
        </div>

        <h2 className="title-decision mt-3">{recommendation.primary_name}</h2>
        <p className="mt-1.5 text-[0.86rem] text-muted">
          {[recommendation.session_demand, duration, rir ? `${rir} RIR` : null].filter(Boolean).join(" · ")}
        </p>

        {adaptation && adaptation.direction !== "none" ? (
          <p className="mt-2 text-[0.74rem] leading-snug text-muted">
            {adaptation.label}
            {adaptation.from && adaptation.to ? ` · ${adaptation.from} → ${adaptation.to} demand` : ""}
          </p>
        ) : null}

        {/* Level 2 — exactly one reason. */}
        {reason ? <p className="mt-3 text-[0.82rem] leading-relaxed">{reason}</p> : null}

        <Link href="/train" className={cn(buttonVariants({ size: "lg" }), "mt-4 w-full")} aria-label="Start session">
          Start Session
          <ArrowRight className="h-4 w-4" />
        </Link>
      </section>

      {/* Level 3 — three light indicators, no explanation. */}
      <StatRow
        items={[
          { label: "Readiness", value: readiness.index ?? "—", hint: `/ ${readiness.index_scale?.max ?? 100} index` },
          {
            label: "Exposure",
            value:
              exposure && exposure.target
                ? `${formatNumber(exposure.value)} / ${formatNumber(exposure.target)}`
                : exposure
                  ? formatNumber(exposure.value)
                  : "—",
            hint: exposure?.group ?? "no target set",
          },
          { label: "Evidence", value: confidence?.state ?? "—", hint: "recommendation confidence" },
        ]}
      />

      <nav aria-label="Secondary" className="divider -mt-1 flex flex-wrap gap-x-5 gap-y-1 pt-4">
        <Link
          href="/readiness"
          className="flex min-h-11 items-center text-[0.82rem] font-medium transition-colors hover:text-muted md:min-h-8"
        >
          View readiness →
        </Link>
        <Link
          href="/decision-trace"
          className="flex min-h-11 items-center text-[0.82rem] font-medium transition-colors hover:text-muted md:min-h-8"
        >
          Why this recommendation →
        </Link>
        <Link
          href="/decision-explorer"
          className="flex min-h-11 items-center text-[0.82rem] font-medium transition-colors hover:text-muted md:min-h-8"
        >
          What if? →
        </Link>
      </nav>

      <CheckInPrompt />

      <p className="flex items-center justify-center gap-1.5 text-center text-[0.7rem] text-muted">
        <ShieldCheck className="h-3.5 w-3.5" aria-hidden />
        Decision support only. Not a medical device, diagnosis or injury prediction.
      </p>
    </div>
  );
}
