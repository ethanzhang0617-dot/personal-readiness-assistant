import { sentenceCase } from "@/lib/format";
import type { DecisionTraceStep } from "@/types/api";
import { cn } from "@/lib/utils";

/**
 * Decision Trace as a vertical reasoning path.
 *
 * Small node, one-line summary, thin connecting line, and the final
 * recommendation highlighted. Structured evidence is one deliberate expand
 * away, and the wording stays the deterministic rule explanation — never model
 * chain-of-thought.
 */
export function DecisionTrace({
  steps,
  rationale = [],
  headline,
}: {
  steps: DecisionTraceStep[];
  rationale?: string[];
  headline?: string;
}) {
  return (
    <div className="space-y-4">
      {headline ? <p className="text-[0.84rem] leading-relaxed text-muted">{headline}</p> : null}

      <ol>
        {steps.map((step, position) => {
          const last = position === steps.length - 1;
          return (
            <li key={step.index} className="relative flex gap-4 pb-5 last:pb-0">
              <span className="relative flex w-3 shrink-0 justify-center" aria-hidden>
                <span
                  className={cn("mt-2 h-2.5 w-2.5 rounded-full", last ? "bg-accent" : "bg-[var(--border-strong)]")}
                />
                {!last ? (
                  <span className="absolute top-5 h-[calc(100%-0.5rem)] w-px bg-[var(--border-subtle)]" />
                ) : null}
              </span>

              <div className="min-w-0 flex-1">
                <p className="text-[0.72rem] font-medium tracking-[0.06em] text-muted uppercase">
                  {sentenceCase(step.step)}
                </p>
                <p
                  className={cn(
                    "mt-0.5 leading-snug",
                    last ? "text-[1.05rem] font-semibold" : "text-[0.9rem]",
                  )}
                >
                  {step.value}
                </p>

                {step.detail ? (
                  <details className="group mt-2">
                    <summary className="flex min-h-9 cursor-pointer list-none items-center gap-1 text-[0.76rem] font-medium text-muted">
                      Details
                      <span className="transition-transform group-open:rotate-90" aria-hidden>
                        ›
                      </span>
                    </summary>
                    <dl className="mt-2 space-y-1.5 text-[0.78rem] leading-relaxed">
                      <div className="flex gap-2">
                        <dt className="w-[5.5rem] shrink-0 text-muted">Evidence</dt>
                        <dd>{step.detail.evidence}</dd>
                      </div>
                      <div className="flex gap-2">
                        <dt className="w-[5.5rem] shrink-0 text-muted">Pattern</dt>
                        <dd>{step.detail.pattern}</dd>
                      </div>
                      <div className="flex gap-2">
                        <dt className="w-[5.5rem] shrink-0 text-muted">Confidence</dt>
                        <dd>{step.detail.confidence}</dd>
                      </div>
                      <div className="flex gap-2">
                        <dt className="w-[5.5rem] shrink-0 text-muted">Adjustment</dt>
                        <dd>{step.detail.adjustment}</dd>
                      </div>
                    </dl>
                  </details>
                ) : null}
              </div>
            </li>
          );
        })}
      </ol>

      {rationale.length > 0 ? (
        <details className="divider group pt-4">
          <summary className="flex min-h-10 cursor-pointer list-none items-center gap-1 text-[0.8rem] font-medium">
            Rule basis
            <span className="transition-transform group-open:rotate-90" aria-hidden>
              ›
            </span>
          </summary>
          <ul className="mt-3 space-y-2">
            {rationale.map((line) => (
              <li key={line} className="text-[0.8rem] leading-relaxed text-muted">
                {line}
              </li>
            ))}
          </ul>
        </details>
      ) : null}

      <p className="text-[0.72rem] text-muted">
        A deterministic explanation from the product rules, not model chain-of-thought.
      </p>
    </div>
  );
}
