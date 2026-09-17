"use client";

import Link from "next/link";

import { DecisionTrace } from "@/components/decision-trace";
import { PageHeader } from "@/components/page-header";
import { StatePanel } from "@/components/state-panel";
import { Skeleton } from "@/components/ui/skeleton";
import { useUserState } from "@/lib/state-provider";

// The Decision Trace is a deliberate destination: the user asks for it, so it
// keeps its detail — but it reads as a path, one line per step.

export function DecisionTraceView() {
  const { ready, today, error } = useUserState();

  if (!ready) {
    return (
      <div className="space-y-5">
        <Skeleton className="h-4 w-20" />
        <Skeleton className="h-8 w-44" />
        <Skeleton className="h-72 w-full rounded-[var(--radius-card)]" />
      </div>
    );
  }

  if (!today) {
    return (
      <StatePanel
        tone="error"
        title="We couldn't load today's decision"
        body={`${error ?? "Your training data did not respond."} Reload the page to try again.`}
      />
    );
  }

  const recommendation = today.training.recommendation;

  return (
    <div className="space-y-6">
      <PageHeader
        back={{ href: "/", label: "Today" }}
        eyebrow="Decision trace"
        title={recommendation.primary_name}
        description="The path the deterministic rules followed to today's recommendation."
      />

      <DecisionTrace steps={today.training.decision_trace} rationale={recommendation.rationale} />

      <p className="divider pt-5 text-[0.78rem] leading-relaxed text-muted">
        Change one input and see what the same rules would decide:{" "}
        <Link href="/decision-explorer" className="font-medium text-accent underline decoration-dotted underline-offset-2">
          What if? →
        </Link>
      </p>
    </div>
  );
}
