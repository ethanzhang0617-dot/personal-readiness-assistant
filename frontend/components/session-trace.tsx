import type { DecisionTraceStep } from "@/types/api";
import { cn } from "@/lib/utils";

/**
 * The session's own causal chain, kept separate from the pre-session Decision
 * Trace on Today:
 *
 *   PRE-SESSION DECISION → PERSONAL RESPONSE → STARTING GUIDANCE
 *   → IN-SESSION OBSERVATION → CALIBRATION → FINAL SESSION GUIDANCE
 *
 * It is the same deterministic material as the Decision Trace, just scoped to
 * the session and extended with whatever the checkpoint observed.
 */
export function SessionTrace({ steps, className }: { steps: DecisionTraceStep[]; className?: string }) {
  if (!steps.length) return null;
  return (
    <ol className={cn("space-y-2.5", className)}>
      {steps.map((step) => (
        <li key={step.index} className="flex gap-3">
          <span className="relative flex w-4 shrink-0 justify-center" aria-hidden>
            <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-subtle" />
            {step.index !== steps.length ? (
              <span className="absolute top-3.5 h-[calc(100%+0.5rem)] w-px bg-subtle" />
            ) : null}
          </span>
          <div className="min-w-0 flex-1">
            <p className="text-[0.66rem] font-semibold uppercase tracking-[0.08em] text-muted">{step.step}</p>
            <p className="text-[0.82rem] leading-snug">{step.value}</p>
          </div>
        </li>
      ))}
    </ol>
  );
}
