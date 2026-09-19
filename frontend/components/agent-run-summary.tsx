import { Check, ChevronRight, ShieldCheck } from "lucide-react";

import { DETERMINISTIC_AUTHORITY_LINE, type AgentRun } from "@/lib/agent-sources";
import { cn } from "@/lib/utils";

/**
 * The compact execution surface under an answer.
 *
 * It shows only what the backend actually reported for this answer: how many
 * verified sources were used, which ones, and whether the answer is grounded.
 * Expanded, each source gets one consumer sentence - tool transparency, never
 * reasoning transparency. No prompt, planner output or chain-of-thought.
 */
export function AgentRunSummary({ run, notice }: { run: AgentRun; notice?: string | null }) {
  const preview = run.sources.slice(0, 4).map((source) => source.label);
  const more = run.sources.length - preview.length;

  return (
    <div className="surface-flat mt-2 px-3.5 py-3">
      <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1.5">
        <span
          className={cn(
            "inline-flex items-center gap-1.5 text-[0.66rem] font-semibold tracking-[0.08em]",
            run.grounded ? "text-[var(--status-green)]" : "text-muted",
          )}
        >
          {run.grounded ? (
            <ShieldCheck className="h-3.5 w-3.5" aria-hidden />
          ) : (
            <Check className="h-3.5 w-3.5" aria-hidden />
          )}
          {run.pill}
        </span>
        <span className="text-[0.74rem] font-medium">{run.headline}</span>
      </div>

      <p className="mt-1.5 text-[0.74rem] leading-relaxed text-muted">
        {preview.join(" · ")}
        {more > 0 ? ` · +${more} more` : ""}
      </p>

      <details className="group mt-1">
        <summary className="flex min-h-9 cursor-pointer list-none items-center gap-1 text-[0.74rem] font-medium text-muted">
          How this answer was built
          <ChevronRight className="h-3.5 w-3.5 transition-transform group-open:rotate-90" aria-hidden />
        </summary>
        <ul className="mt-1 space-y-2">
          {run.sources.map((source) => (
            <li key={source.tool} className="flex gap-2">
              <Check className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[var(--status-green)]" aria-hidden />
              <span className="min-w-0">
                <span className="block text-[0.78rem] font-medium">{source.label}</span>
                <span className="block text-[0.72rem] leading-relaxed text-muted">{source.description}</span>
              </span>
            </li>
          ))}
        </ul>
        <p className="mt-2.5 text-[0.7rem] leading-relaxed text-muted">{DETERMINISTIC_AUTHORITY_LINE}</p>
        {notice ? <p className="mt-1 text-[0.7rem] leading-relaxed text-muted">{notice}</p> : null}
      </details>
    </div>
  );
}
