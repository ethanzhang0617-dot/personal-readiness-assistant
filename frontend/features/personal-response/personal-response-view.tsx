"use client";

import { useEffect, useState } from "react";

import { PageHeader } from "@/components/page-header";
import {
  AdaptationHistoryList,
  ConfidenceBadge,
  EvidenceCoveragePanel,
  PersonalResponseProfilePanel,
  ResponseEpisodeList,
} from "@/components/personal-response";
import { StatePanel } from "@/components/state-panel";
import { Skeleton } from "@/components/ui/skeleton";
import { useUserState } from "@/lib/state-provider";
import type { PersonalResponse } from "@/types/api";
import { cn } from "@/lib/utils";

// Personal Response: pattern first.
//
// High / Moderate / Low read as visual bands, the interpretation is one line,
// and every statistic sits behind a deliberate expand.

function bandTone(pattern: string, observations: number): { bg: string; fg: string } {
  if (observations === 0) return { bg: "var(--surface-secondary)", fg: "var(--text-muted)" };
  const lower = pattern.toLowerCase();
  if (lower.includes("poorer")) return { bg: "var(--status-red-soft)", fg: "var(--status-red)" };
  if (lower.includes("better")) return { bg: "var(--status-green-soft)", fg: "var(--status-green)" };
  return { bg: "var(--accent-soft)", fg: "var(--accent-primary)" };
}

/** Highest demand first: that is the band the user cares about most. */
const BAND_ORDER = ["High", "Moderate", "Low"];

function orderBands<T extends { band: string }>(bands: T[]): T[] {
  return [...bands].sort((a, b) => {
    const left = BAND_ORDER.indexOf(a.band);
    const right = BAND_ORDER.indexOf(b.band);
    return (left === -1 ? 99 : left) - (right === -1 ? 99 : right);
  });
}

export function PersonalResponseView() {
  const { ready, loadPersonalResponse } = useUserState();
  const [response, setResponse] = useState<PersonalResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!ready) return;
    let cancelled = false;
    loadPersonalResponse().then((result) => {
      if (cancelled) return;
      if (result.ok && result.data) setResponse(result.data);
      setLoading(false);
    });
    return () => {
      cancelled = true;
    };
  }, [loadPersonalResponse, ready]);

  if (!ready || loading) {
    return (
      <div className="space-y-5">
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-8 w-56" />
        <Skeleton className="h-40 w-full rounded-[var(--radius-card)]" />
      </div>
    );
  }

  if (!response) {
    return (
      <StatePanel
        tone="error"
        title="We couldn't load your response pattern"
        body="Reload the page to try again."
      />
    );
  }

  const bands = orderBands(response.profile?.bands ?? []);
  const notable = bands.find((band) => band.observations > 0) ?? null;
  const interpretation = notable
    ? `${notable.band}-demand sessions tend to be followed by ${notable.pattern.replace(/\.$/, "").toLowerCase()} responses.`
    : (response.detail ??
      "Not enough completed episodes yet. Log a session, add your feedback and check in the next morning — that becomes the first episode.");
  const relevant = response.confidence?.relevant_episodes ?? response.relevant_episodes ?? null;

  return (
    <div className="space-y-7">
      <PageHeader
        back={{ href: "/insights", label: "Insights" }}
        eyebrow="Personal response"
        title="Your response pattern"
      />

      <ul className="space-y-3">
        {bands.length > 0 ? (
          bands.map((band) => {
            const tone = bandTone(band.pattern, band.observations);
            return (
              <li
                key={band.band}
                className="rounded-[var(--radius-card)] px-4 py-4"
                style={{ backgroundColor: tone.bg }}
              >
                <div className="flex items-baseline justify-between gap-3">
                  <p className="text-[0.7rem] font-semibold tracking-[0.08em] uppercase" style={{ color: tone.fg }}>
                    {band.band} demand
                  </p>
                  <p className="text-[0.72rem] text-muted">
                    {band.observations > 0
                      ? `${band.observations} relevant session${band.observations === 1 ? "" : "s"}`
                      : "Not enough data"}
                  </p>
                </div>
                <p className="mt-1.5 text-[1rem] font-semibold" style={{ color: tone.fg }}>
                  {band.pattern}
                </p>
              </li>
            );
          })
        ) : (
          <li className="surface-flat px-4 py-4 text-[0.86rem] text-muted">No demand bands recorded yet.</li>
        )}
      </ul>

      <p className="text-[0.88rem] leading-relaxed">{interpretation}</p>

      <div className="flex flex-wrap items-center gap-2">
        <ConfidenceBadge confidence={response.confidence} />
        {relevant !== null ? (
          <span className="text-[0.76rem] text-muted">
            Based on {relevant} relevant session{relevant === 1 ? "" : "s"}
          </span>
        ) : null}
      </div>

      <details className="divider group pt-5">
        <summary className="flex min-h-11 cursor-pointer list-none items-center justify-between gap-3 text-[0.86rem] font-medium">
          How this is calculated
          <span className="text-[0.72rem] text-muted">{response.confidence?.state ?? "—"}</span>
        </summary>
        <div className="space-y-2 pt-3">
          <p className="text-[0.82rem] leading-relaxed">{response.confidence?.explanation ?? "—"}</p>
          {response.confidence?.note ? (
            <p className="text-[0.76rem] leading-relaxed text-muted">{response.confidence.note}</p>
          ) : null}
          {response.note ? <p className="text-[0.76rem] leading-relaxed text-muted">{response.note}</p> : null}
        </div>
      </details>

      <details className="divider group pt-5">
        <summary className="flex min-h-11 cursor-pointer list-none items-center justify-between gap-3 text-[0.86rem] font-medium">
          Supporting sessions
          <span className="text-[0.72rem] text-muted">
            {response.episodes.length} episode{response.episodes.length === 1 ? "" : "s"}
          </span>
        </summary>
        <div className="pt-3">
          <ResponseEpisodeList episodes={response.episodes} />
        </div>
      </details>

      <details className="divider group pt-5">
        <summary className="flex min-h-11 cursor-pointer list-none items-center justify-between gap-3 text-[0.86rem] font-medium">
          Detailed evidence
        </summary>
        <div className="space-y-6 pt-4">
          <PersonalResponseProfilePanel profile={response.profile} />
          <div>
            <p className="label-quiet mb-2">Evidence coverage</p>
            <EvidenceCoveragePanel coverage={response.coverage} />
          </div>
          <div>
            <p className="label-quiet mb-2">Adaptation history</p>
            <AdaptationHistoryList history={response.adaptation_history} />
          </div>
        </div>
      </details>

      <p className={cn("text-[0.72rem] leading-relaxed text-muted")}>
        These are observed patterns from your own logged sessions and check-ins — not a recovery measurement, a
        prediction or a medical assessment.
      </p>
    </div>
  );
}
