"use client";

import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import { PageHeader } from "@/components/page-header";
import { StatePanel } from "@/components/state-panel";
import { StatusBadge } from "@/components/status-badge";
import { Section } from "@/components/ui/section";
import { Skeleton } from "@/components/ui/skeleton";
import { statusTone } from "@/lib/format";
import { useUserState } from "@/lib/state-provider";
import { cn } from "@/lib/utils";

// Readiness detail lives here, not on Today.
//
// Level 1 is the overall state and the index. Level 2 is at most three
// contributors. Everything else — every domain, the baseline context and the
// limitations — sits behind one deliberate expand.

const MAX_CONTRIBUTORS = 3;

export function ReadinessView() {
  const { ready, today, error } = useUserState();

  if (!ready) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-6 w-28" />
        <Skeleton className="h-40 w-full rounded-[var(--radius-card)]" />
        <Skeleton className="h-24 w-full" />
      </div>
    );
  }

  if (!today) {
    return (
      <StatePanel
        tone="error"
        title="Readiness is unavailable right now"
        body={`${error ?? "The API did not return a readiness result."} Start the API and reload this page.`}
      />
    );
  }

  const readiness = today.readiness;
  const contributors = readiness.contributors.slice(0, MAX_CONTRIBUTORS);
  const remaining = readiness.contributors.slice(MAX_CONTRIBUTORS);
  const max = readiness.index_scale?.max ?? 100;

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
        eyebrow="Readiness"
        title="How ready you are today"
        description="Compared with your own recorded baseline."
      />

      <section className="surface px-5 py-5">
        <div className="flex items-end justify-between gap-4">
          <StatusBadge status={readiness.status} />
          <p className="text-right">
            <span className="title-metric">{readiness.index ?? "—"}</span>
            <span className="ml-1 text-[0.72rem] text-muted">/ {max}</span>
          </p>
        </div>
        <p className="mt-3 text-[0.86rem] leading-relaxed">
          {readiness.explanation ?? "No readiness interpretation is available for today."}
        </p>
      </section>

      <Section title="Key contributors" divided={false}>
        {contributors.length > 0 ? (
          <ul className="border-t border-subtle">
            {contributors.map((line) => (
              <li key={line} className="border-b border-subtle py-2.5 text-[0.82rem] leading-relaxed">
                {line}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-[0.82rem] text-muted">No material contributors were recorded for today.</p>
        )}

        <details className="divider group mt-4 pt-3.5">
          <summary className="flex min-h-10 cursor-pointer list-none items-center gap-1 text-[0.78rem] font-medium">
            View all contributors
            <span className="transition-transform group-open:rotate-90" aria-hidden>
              ›
            </span>
          </summary>

          <div className="mt-3 space-y-4">
            {readiness.domains.length > 0 ? (
              <dl className="grid grid-cols-2 gap-x-4 gap-y-3">
                {readiness.domains.map((domain) => {
                  const tone = statusTone(domain.status);
                  return (
                    <div key={domain.key}>
                      <dt className="text-[0.72rem] text-muted">{domain.label}</dt>
                      <dd className="mt-1 flex items-center gap-1.5">
                        <span className={cn("h-1.5 w-1.5 rounded-full", tone.dot)} aria-hidden />
                        <span className="text-[0.8rem] font-medium">{domain.status}</span>
                      </dd>
                    </div>
                  );
                })}
              </dl>
            ) : null}

            {remaining.length > 0 ? (
              <ul className="space-y-1.5">
                {remaining.map((line) => (
                  <li key={line} className="text-[0.78rem] leading-relaxed text-muted">
                    {line}
                  </li>
                ))}
              </ul>
            ) : null}

            {readiness.why_this_status.length > 0 ? (
              <ul className="space-y-1.5">
                {readiness.why_this_status.map((line) => (
                  <li key={line} className="text-[0.78rem] leading-relaxed text-muted">
                    {line}
                  </li>
                ))}
              </ul>
            ) : null}

            {readiness.confidence_note ? (
              <p className="text-[0.74rem] leading-relaxed text-muted">{readiness.confidence_note}</p>
            ) : null}

            {readiness.limitations.length > 0 ? (
              <ul className="space-y-1.5">
                {readiness.limitations.map((line) => (
                  <li key={line} className="text-[0.72rem] leading-relaxed text-muted">
                    {line}
                  </li>
                ))}
              </ul>
            ) : null}
          </div>
        </details>
      </Section>

      <p className="divider pt-4 text-[0.74rem] leading-relaxed text-muted">
        Readiness compares today against your own observations, not population cut-offs.{" "}
        <Link href="/decision-trace" className="font-medium text-foreground underline decoration-dotted underline-offset-2">
          See how it fed today&apos;s recommendation →</Link>
      </p>
    </div>
  );
}
