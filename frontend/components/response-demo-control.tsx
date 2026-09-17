"use client";

import { useState } from "react";

import { useUserState } from "@/lib/state-provider";
import { RESPONSE_DEMO_CASES, RESPONSE_DEMO_LABELS } from "@/lib/response";
import { cn } from "@/lib/utils";

// Portfolio demo control: loads one of the documented Personal Response histories
// into this browser so the adaptive states can be demonstrated. It is deliberately
// placed in the demo controls, not in the daily workflow.

export function ResponseDemoControl() {
  const { seedResponseDemo, busy } = useUserState();
  const [message, setMessage] = useState<string | null>(null);

  return (
    <div className="rounded-[var(--radius-card)] border border-subtle bg-surface-muted p-3">
      <p className="eyebrow">Response history demo</p>
      <p className="mt-1 text-[0.68rem] leading-relaxed text-muted">
        Loads recorded sessions with feedback into this browser so the Personal Response states can be
        demonstrated. Use the &quot;Well Recovered Day&quot; scenario to see an adjustment.
      </p>
      <div className="mt-2 flex flex-wrap gap-2">
        {RESPONSE_DEMO_CASES.map((caseName) => (
          <button
            key={caseName}
            type="button"
            disabled={busy}
            onClick={async () => {
              const result = await seedResponseDemo(caseName);
              setMessage(result.ok ? `Loaded: ${RESPONSE_DEMO_LABELS[caseName]}` : result.error ?? null);
            }}
            className={cn(
              "min-h-11 rounded-full bg-surface-muted px-3.5 text-[0.76rem] font-medium",
              "text-muted transition-colors hover:text-foreground md:min-h-9",
            )}
          >
            {RESPONSE_DEMO_LABELS[caseName]}
          </button>
        ))}
      </div>
      {message ? <p className="mt-2 text-[0.68rem] text-muted">{message}</p> : null}
    </div>
  );
}
