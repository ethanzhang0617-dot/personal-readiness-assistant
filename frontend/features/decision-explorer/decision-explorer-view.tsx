"use client";

import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import { DecisionExplorer } from "@/components/decision-explorer";
import { PageHeader } from "@/components/page-header";
import { useUserState } from "@/lib/state-provider";

// Decision Explorer as a small experiment tool: current decision, one changed
// input, alternative decision, one short reason. The deterministic rules it
// re-runs are unchanged and nothing it does is saved.

export function DecisionExplorerView() {
  const { today } = useUserState();

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
        eyebrow="What if?"
        title="See how one input would change today's decision"
        description="The same deterministic rules, re-run with a single condition changed."
      />

      <p className="text-[0.82rem] leading-relaxed text-muted">
        Today&apos;s recommendation is{" "}
        <span className="font-medium text-foreground">
          {today?.training.recommendation.primary_name ?? "—"} · {today?.training.recommendation.session_demand ?? "—"}
        </span>
        .
      </p>

      <DecisionExplorer />
    </div>
  );
}
