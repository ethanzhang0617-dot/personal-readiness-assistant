import type { DecisionTraceStep } from "@/types/api";

/**
 * The Decision Trace is a deterministic explanation, not model reasoning.
 * It stays collapsed by default so the first screen keeps its hierarchy.
 */
export function DecisionTrace({
  steps,
  rationale,
  headline,
}: {
  steps: DecisionTraceStep[];
  rationale: string[];
  headline?: string;
}) {
  return (
    <details className="group rounded-[var(--radius-card)] border border-subtle bg-surface">
      <summary className="flex min-h-11 cursor-pointer list-none items-center justify-between gap-3 p-4 text-sm font-semibold">
        <span>
          Why this session
          <span className="ml-2 text-[0.7rem] font-normal text-muted">
            {steps.length} deterministic factors
          </span>
        </span>
        <span className="text-muted transition-transform group-open:rotate-90" aria-hidden>
          ›
        </span>
      </summary>
      <div className="border-t border-subtle p-4">
        {headline ? <p className="mb-3 text-sm text-muted">{headline}</p> : null}
        <ol className="space-y-2">
          {steps.map((step) => (
            <li key={step.index} className="flex items-baseline justify-between gap-3">
              <span className="text-[0.68rem] font-semibold tracking-wide text-muted uppercase">
                {step.step}
              </span>
              <span className="text-right text-sm">{step.value}</span>
            </li>
          ))}
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
          Deterministic explanation, not model chain-of-thought.
        </p>
      </div>
    </details>
  );
}
