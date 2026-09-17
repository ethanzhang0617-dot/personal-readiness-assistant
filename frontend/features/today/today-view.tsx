"use client";

import Link from "next/link";
import { ArrowRight, ShieldCheck } from "lucide-react";

import { CheckInPrompt } from "@/components/check-in-prompt";
import { MetricChip, MetricChipRow } from "@/components/metric-chip";
import { ReadinessRing } from "@/components/readiness-ring";
import { StatePanel } from "@/components/state-panel";
import { buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { formatNumber } from "@/lib/format";
import { useUserState } from "@/lib/state-provider";
import type { TrainingRecommendation, WeeklyExposure } from "@/types/api";
import { cn } from "@/lib/utils";

// Today: what should I do today?
//
// Three layers, never equal in weight — the readiness hero (how ready am I),
// the recommendation (what am I training), and three light supporting metrics.
// Everything else is a deliberate destination.

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

function greeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

function todayLabel(value?: string | null): string {
  const date = value ? new Date(`${value}T00:00:00`) : new Date();
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long" });
}

export function TodayView() {
  const { ready, today, waking } = useUserState();

  if (!ready) {
    return (
      <div className="space-y-5">
        {waking ? (
          <p className="text-[0.8rem] text-muted">Waking your training data…</p>
        ) : null}
        <div className="space-y-2">
          <Skeleton className="h-4 w-28" />
          <Skeleton className="h-8 w-40" />
        </div>
        <Skeleton className="h-[13rem] w-full rounded-[var(--radius-card)]" />
        <Skeleton className="h-[12rem] w-full rounded-[var(--radius-card)]" />
        <Skeleton className="h-16 w-full rounded-[var(--radius-card)]" />
      </div>
    );
  }

  if (!today) {
    return (
      <StatePanel
        tone="error"
        title="We couldn't load today's guidance"
        body="Your training data did not respond. Check your connection and reload — nothing has been lost."
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
    <div className="space-y-5">
      <header className="flex items-end justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[0.78rem] text-muted">{todayLabel(readiness.assessment_date)}</p>
          <h1 className="title-page mt-1">
            {greeting()}, {profile.name}
          </h1>
        </div>
        <p className="shrink-0 text-right text-[0.72rem] leading-snug text-muted">
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

      {/* Level 1 — how ready am I. */}
      <section className="surface-raised flex items-center gap-4 px-5 py-4">
        <ReadinessRing
          index={readiness.index}
          max={readiness.index_scale?.max ?? 100}
          status={readiness.status}
          size={138}
          className="shrink-0"
        />
        <div className="min-w-0">
          <p className="line-clamp-4 text-[0.84rem] leading-relaxed md:line-clamp-none">
            {readiness.explanation ?? "No readiness interpretation is available for today."}
          </p>
          <Link
            href="/readiness"
            className="mt-1.5 inline-flex min-h-8 items-center text-[0.78rem] font-medium text-accent"
          >
            View readiness →
          </Link>
        </div>
      </section>

      {/* Level 2 — what am I training, and the one action. */}
      <section className="surface px-5 py-4">
        <p className="eyebrow">Today&apos;s recommendation</p>
        <h2 className="title-hero mt-1.5">{recommendation.primary_name}</h2>
        <p className="mt-2 text-[0.88rem] text-secondary">
          {[recommendation.session_demand, duration, rir ? `${rir} RIR` : null].filter(Boolean).join(" · ")}
        </p>

        {adaptation && adaptation.direction !== "none" ? (
          <p className="mt-2 text-[0.76rem] leading-snug text-accent">
            {adaptation.label}
            {adaptation.from && adaptation.to ? ` · ${adaptation.from} → ${adaptation.to} demand` : ""}
          </p>
        ) : null}

        {reason ? <p className="mt-3 text-[0.84rem] leading-relaxed text-muted">{reason}</p> : null}

        <Link href="/train" className={cn(buttonVariants({ size: "lg" }), "mt-4 w-full")} aria-label="Start session">
          Start Session
          <ArrowRight className="h-4 w-4" />
        </Link>
      </section>

      {/* Level 3 — three light metrics, never three cards. */}
      <MetricChipRow>
        <MetricChip
          label="Readiness"
          value={readiness.index ?? "—"}
          hint={`/ ${readiness.index_scale?.max ?? 100}`}
        />
        <MetricChip
          label="Exposure"
          value={
            exposure && exposure.target
              ? `${formatNumber(exposure.value)} / ${formatNumber(exposure.target)}`
              : exposure
                ? formatNumber(exposure.value)
                : "—"
          }
          hint={exposure?.group ?? "No target set"}
        />
        <MetricChip label="Evidence" value={confidence?.state ?? "—"} hint="Recommendation confidence" />
      </MetricChipRow>

      <nav aria-label="Secondary" className="flex flex-wrap gap-x-6 gap-y-1">
        <Link href="/decision-trace" className="flex min-h-11 items-center text-[0.82rem] font-medium text-muted transition-colors hover:text-foreground md:min-h-8">
          Why this recommendation →
        </Link>
        <Link href="/decision-explorer" className="flex min-h-11 items-center text-[0.82rem] font-medium text-muted transition-colors hover:text-foreground md:min-h-8">
          What if? →
        </Link>
      </nav>

      <CheckInPrompt />

      <p className="flex items-center justify-center gap-1.5 pb-2 text-center text-[0.72rem] text-muted">
        <ShieldCheck className="h-3.5 w-3.5" aria-hidden />
        Decision support only. Not a medical device, diagnosis or injury prediction.
      </p>
    </div>
  );
}
