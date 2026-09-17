"use client";

import { DecisionExplorer } from "@/components/decision-explorer";
import { PageHeader } from "@/components/page-header";
import { useUserState } from "@/lib/state-provider";

// Decision Explorer as a small experiment tool: the current decision, one
// changed input, the alternative the same rules produce, and one short reason.
// It remains read-only and never a prediction.

export function DecisionExplorerView() {
  const { today } = useUserState();

  return (
    <div className="space-y-6">
      <PageHeader
        back={{ href: "/", label: "Today" }}
        eyebrow="What if?"
        title="See how one input would change today's recommendation"
        description="The same deterministic rules, re-run with a single condition changed."
      />

      <p className="text-[0.84rem] leading-relaxed text-muted">
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
