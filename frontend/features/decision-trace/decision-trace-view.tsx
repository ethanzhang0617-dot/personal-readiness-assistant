"use client";

import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import { DecisionTrace } from "@/components/decision-trace";
import { PageHeader } from "@/components/page-header";
import { StatePanel } from "@/components/state-panel";
import { Skeleton } from "@/components/ui/skeleton";
import { useUserState } from "@/lib/state-provider";

// The Decision Trace is a deliberate destination: the user asks for it, so it
// keeps its detail, but it reads as a path with one line per step.

export function DecisionTraceView() {
  const { ready, today, error } = useUserState();

  if (!ready) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-6 w-32" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (!today) {
    return (
      <StatePanel
        tone="error"
        title="The decision trace is unavailable right now"
        body={`${error ?? "The API did not return today's decision."} Start the API and reload this page.`}
      />
    );
  }

  const recommendation = today.training.recommendation;

  return (
    <div className="space-y-6">
      <Link
        href="/"
        className="inline-flex min-h-11 items-center gap-1.5 text-[0.75rem] text-muted transition-colors hover:text-foreground md:min-h-9"
      >
        <ArrowLeft className="h-3.5 w-3.5" aria-hidden />
        Today
      </Link>

      <PageHeader
        eyebrow="Decision trace"
        title={recommendation.primary_name}
        description="The path the deterministic rules followed to today's recommendation."
      />

      <DecisionTrace
        steps={today.training.decision_trace}
        rationale={recommendation.rationale}
      />

      <p className="divider pt-4 text-[0.74rem] leading-relaxed text-muted">
        Change one input and see what the same rules would decide:{" "}
        <Link href="/decision-explorer" className="font-medium text-foreground underline decoration-dotted underline-offset-2">
          What if? →
        </Link>
      </p>
    </div>
  );
}
