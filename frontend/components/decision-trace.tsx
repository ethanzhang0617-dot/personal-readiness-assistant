import { ChevronRight } from "lucide-react";

import type { DecisionTraceStep } from "@/types/api";

/**
 * Decision Trace: the product's differentiator, written as a readable causal
 * chain rather than a technical dump. Collapsed by default to protect the
 * hierarchy of the screen above it.
 */
export function DecisionTrace({
  steps,
  rationale,
  headline,
  title = "Why this recommendation",
}: {
  steps: DecisionTraceStep[];
  rationale: string[];
  headline?: string;
  title?: string;
}) {
  return (
    <details className="divider group pt-4">
      <summary className="flex min-h-11 cursor-pointer list-none items-center justify-between gap-3 text-sm font-semibold">
        <span>{title}</span>
        <span className="flex items-center gap-2 text-[0.75rem] font-normal text-muted">
          {steps.length} factors
          <ChevronRight className="h-4 w-4 transition-transform group-open:rotate-90" aria-hidden />
        </span>
      </summary>

      <div className="pb-1 pt-3">
        {headline ? <p className="mb-4 text-[0.82rem] leading-relaxed text-muted">{headline}</p> : null}

        <ol className="space-y-3">
          {steps.map((step, position) => {
            const last = position === steps.length - 1;
            return (
              <li key={step.index} className="flex gap-3">
                <span className="relative flex w-4 shrink-0 justify-center" aria-hidden>
                  <span className={last ? "mt-1 h-2 w-2 rounded-full bg-primary" : "mt-1 h-2 w-2 rounded-full bg-subtle"} />
                  {!last ? <span className="absolute top-3 h-[calc(100%+0.6rem)] w-px bg-subtle" /> : null}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="text-[0.68rem] font-semibold uppercase tracking-[0.08em] text-muted">{step.step}</p>
                  <p className="text-[0.86rem] leading-snug">{step.value}</p>
                </div>
              </li>
            );
          })}
        </ol>

        {rationale.length > 0 ? (
          <ul className="mt-4 space-y-1.5 border-t border-subtle pt-3">
            {rationale.map((line) => (
              <li key={line} className="text-[0.78rem] leading-relaxed text-muted">
                {line}
              </li>
            ))}
          </ul>
        ) : null}

        <p className="mt-3 text-[0.68rem] text-muted">
          A deterministic explanation from the product rules, not model chain-of-thought.
        </p>
      </div>
    </details>
  );
}
