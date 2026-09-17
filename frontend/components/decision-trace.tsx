import { sentenceCase } from "@/lib/format";
import type { DecisionTraceStep } from "@/types/api";
import { cn } from "@/lib/utils";

/**
 * Decision Trace as a path, not a report.
 *
 * Every step shows one short line; the structured Personal Response evidence is
 * available behind a deliberate expand. The product's differentiator stays
 * readable instead of turning into a wall of paragraphs, and the wording is
 * still the deterministic one — a rule explanation, never model chain-of-thought.
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
    <div className="space-y-3">
      {headline ? <p className="text-[0.82rem] leading-relaxed text-muted">{headline}</p> : null}

      <ol className="space-y-0">
        {steps.map((step, position) => {
          const last = position === steps.length - 1;
          return (
            <li key={step.index} className="relative flex gap-3 pb-4 last:pb-0">
              <span className="relative flex w-4 shrink-0 justify-center" aria-hidden>
                <span className={cn("mt-1.5 h-2 w-2 rounded-full", last ? "bg-primary" : "bg-subtle")} />
                {!last ? <span className="absolute top-3.5 h-[calc(100%-0.25rem)] w-px bg-subtle" /> : null}
              </span>
              <div className="min-w-0 flex-1">
                <p className="label-quiet">{sentenceCase(step.step)}</p>
                <p className={cn("leading-snug", last ? "text-[0.95rem] font-semibold" : "text-[0.86rem]")}>
                  {step.value}
                </p>

                {step.detail ? (
                  <details className="group mt-1.5">
                    <summary className="flex min-h-9 cursor-pointer list-none items-center gap-1 text-[0.74rem] font-medium text-muted">
                      More
                      <span className="transition-transform group-open:rotate-90" aria-hidden>
                        ›
                      </span>
                    </summary>
                    <dl className="mt-2 space-y-1 text-[0.76rem] leading-relaxed">
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
        <details className="divider group pt-3.5">
          <summary className="flex min-h-10 cursor-pointer list-none items-center gap-1 text-[0.78rem] font-medium">
            Rule basis
            <span className="transition-transform group-open:rotate-90" aria-hidden>
              ›
            </span>
          </summary>
          <ul className="mt-2 space-y-1.5">
            {rationale.map((line) => (
              <li key={line} className="text-[0.78rem] leading-relaxed text-muted">
                {line}
              </li>
            ))}
          </ul>
        </details>
      ) : null}

      <p className="text-[0.68rem] text-muted">
        A deterministic explanation from the product rules, not model chain-of-thought.
      </p>
    </div>
  );
}
