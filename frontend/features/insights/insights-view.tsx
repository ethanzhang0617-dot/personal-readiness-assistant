"use client";

import Link from "next/link";
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
import { StatusBadge } from "@/components/status-badge";
import { TrendChart } from "@/components/trend-chart";
import { Section } from "@/components/ui/section";
import { Segmented } from "@/components/ui/segmented";
import { Skeleton } from "@/components/ui/skeleton";
import { calibrationLabel, calibrationTone } from "@/lib/calibration";
import { formatNumber, formatShortDate } from "@/lib/format";
import { asNumber, asString } from "@/lib/measurements";
import { useUserState } from "@/lib/state-provider";
import type { InsightsResponse, PersonalResponse } from "@/types/api";
import { cn } from "@/lib/utils";

const WINDOWS = [
  { value: 28, label: "28" },
  { value: 7, label: "7" },
  { value: 0, label: "All" },
];

// Insights: four modules, one takeaway and one number each. Charts, episode
// detail, coverage and the Personal Response profile are deliberate expands, so
// the screen does not repeat what Train already owns (weekly exposure) and never
// renders the same Personal Response content twice.

export function InsightsView() {
  const { ready, today, loadInsights, loadPersonalResponse } = useUserState();
  const [window, setWindow] = useState(28);
  const [data, setData] = useState<InsightsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<PersonalResponse | null>(null);

  useEffect(() => {
    if (!ready) return;
    let cancelled = false;
    loadInsights(window === 0 ? undefined : window).then((result) => {
      if (cancelled) return;
      if (result.ok && result.data) {
        setData(result.data);
        setError(null);
      } else {
        setError(result.error ?? "Insights are unavailable.");
      }
    });
    return () => {
      cancelled = true;
    };
  }, [loadInsights, ready, window]);

  useEffect(() => {
    if (!ready) return;
    let cancelled = false;
    loadPersonalResponse().then((result) => {
      if (!cancelled && result.ok && result.data) setResponse(result.data);
    });
    return () => {
      cancelled = true;
    };
  }, [loadPersonalResponse, ready]);

  if (!ready || (!data && !error)) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-6 w-32" />
        <Skeleton className="h-24 w-full rounded-[var(--radius-card)]" />
        <Skeleton className="h-32 w-full" />
      </div>
    );
  }
  if (error || !data) {
    return (
      <StatePanel
        tone="error"
        title="Insights are unavailable"
        body={`${error ?? "No data was returned."} The rest of the product still works.`}
      />
    );
  }

  const load = data.load;
  const loadSeries = data.series.find((series) => series.key === "session_load") ?? null;
  const signalSeries = data.series.filter((series) => series.key !== "session_load");
  const confidence =
    response?.confidence ?? today?.training.recommendation.recommendation_confidence ?? null;
  const bands = response?.profile?.bands ?? [];
  const notableBand = bands.find((band) => band.observations > 0) ?? null;
  const patternLine = notableBand
    ? `${notableBand.band} demand tends to be followed by ${notableBand.pattern.replace(/\.$/, "").toLowerCase()} responses.`
    : (response?.detail ?? "No completed response episodes yet — log a session, add feedback and check in the next morning.");
  const relevantSessions = confidence?.relevant_episodes ?? response?.relevant_episodes ?? null;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Insights"
        title="Your week in context"
        description="Your own recorded signals. Days without a check-in stay gaps."
      />

      <Segmented
        options={WINDOWS}
        value={window}
        label="Time window in check-ins"
        size="sm"
        onChange={(value) => {
          if (value === window) return;
          setData(null);
          setError(null);
          setWindow(value);
        }}
      />

      {/* 1 — Readiness */}
      <Section title="Readiness" divided={false}>
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="title-metric">
              {today?.readiness.index ?? "—"}
              <span className="ml-1 text-[0.72rem] font-normal text-muted">
                {today?.readiness.status_label ?? ""}
              </span>
            </p>
            <p className="mt-1 text-[0.8rem] leading-relaxed text-muted">
              {today?.readiness.contributors?.[0] ?? today?.readiness.explanation ?? "No readiness detail for today."}
            </p>
          </div>
          {today ? <StatusBadge status={today.readiness.status} /> : null}
        </div>

        <details className="group mt-3">
          <summary className="flex min-h-10 cursor-pointer list-none items-center gap-1 text-[0.78rem] font-medium text-muted">
            Readiness history
            <span className="transition-transform group-open:rotate-90" aria-hidden>
              ›
            </span>
          </summary>
          <div className="pt-2">
            {data.readiness_history.length > 0 ? (
              <ul className="divide-y divide-subtle border-y border-subtle">
                {data.readiness_history.slice(0, 10).map((row) => (
                  <li key={row.date} className="flex min-h-11 items-center justify-between gap-3">
                    <span className="text-[0.8rem]">{formatShortDate(row.date)}</span>
                    <span className="flex items-center gap-3">
                      <span className="text-[0.72rem] text-muted">Index {row.index ?? "—"}</span>
                      {row.status ? <StatusBadge status={row.status} /> : null}
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-[0.78rem] leading-relaxed text-muted">
                No readiness assessments stored yet. {data.available_check_ins} check-ins are available for the charts
                below; saving a check-in records an assessment.
              </p>
            )}
            <Link
              href="/readiness"
              className="mt-2 flex min-h-10 items-center text-[0.78rem] font-medium text-muted"
            >
              View readiness →
            </Link>
          </div>
        </details>
      </Section>

      {/* 2 — Training */}
      <Section title="Training">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="title-metric">
              {formatNumber(asNumber(load.recent_7d_mean))}
              <span className="ml-1.5 text-[0.75rem] font-normal text-muted">pts last 7 days</span>
            </p>
            <p className="mt-1 text-[0.78rem] text-muted">
              21-day reference {formatNumber(asNumber(load.reference_21d_mean))} pts
            </p>
          </div>
          {asString(load.status) ? <StatusBadge status={asString(load.status) as string} /> : null}
        </div>

        {loadSeries ? (
          <div className="mt-3">
            <TrendChart
              points={loadSeries.points}
              baseline={loadSeries.baseline}
              unit={loadSeries.unit}
              label={loadSeries.label}
            />
          </div>
        ) : null}

        <details className="group mt-3">
          <summary className="flex min-h-10 cursor-pointer list-none items-center gap-1 text-[0.78rem] font-medium text-muted">
            Load detail
            <span className="transition-transform group-open:rotate-90" aria-hidden>
              ›
            </span>
          </summary>
          <div className="pt-2">
            <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-[0.75rem]">
              <div>
                <dt className="text-muted">Calendar coverage</dt>
                <dd className="font-medium tabular-nums">
                  {String(load.calendar_days_covered ?? "—")}/{String(load.calendar_days_required ?? "—")} days
                </dd>
              </div>
              <div>
                <dt className="text-muted">Sessions, last 14 days</dt>
                <dd className="font-medium tabular-nums">{data.sessions_last_14_days}</dd>
              </div>
              <div>
                <dt className="text-muted">Data sufficiency</dt>
                <dd className="font-medium">{asString(load.data_sufficiency) ?? "—"}</dd>
              </div>
            </dl>
            <p className="mt-3 text-[0.7rem] leading-relaxed text-muted">
              Training Load Points are calculated from session duration × session RPE. They are relative workload
              units for comparing training stress over time — not kilograms, calories or an absolute physiological
              measurement.
            </p>
          </div>
        </details>
      </Section>

      {/* 3 — Personal response */}
      <Section title="Personal response">
        <p className="text-[0.86rem] leading-relaxed">{patternLine}</p>
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <ConfidenceBadge confidence={confidence} />
          {relevantSessions !== null ? (
            <span className="text-[0.74rem] text-muted">
              Based on {relevantSessions} relevant session{relevantSessions === 1 ? "" : "s"}
            </span>
          ) : null}
        </div>

        <ul className="mt-4 divide-y divide-subtle border-y border-subtle">
          {(bands.length > 0 ? bands : []).map((band) => (
            <li key={band.band} className="flex items-start justify-between gap-3 py-3">
              <div className="min-w-0">
                <p className="text-[0.82rem] font-semibold">{band.band} demand</p>
                <p className="mt-0.5 text-[0.78rem]">{band.pattern}</p>
                <p className="mt-0.5 text-[0.7rem] text-muted">
                  {band.observations > 0
                    ? `${band.observations} relevant session${band.observations === 1 ? "" : "s"}`
                    : "Not enough data"}
                </p>
              </div>
              {band.observations === 0 ? (
                <span className="shrink-0 rounded-full bg-surface-muted px-2 py-0.5 text-[0.62rem] font-semibold text-muted">
                  No data
                </span>
              ) : null}
            </li>
          ))}
          {bands.length === 0 ? (
            <li className="py-3 text-[0.8rem] text-muted">No demand bands recorded yet.</li>
          ) : null}
        </ul>

        <details className="group mt-3">
          <summary className="flex min-h-10 cursor-pointer list-none items-center gap-1 text-[0.78rem] font-medium text-muted">
            Response detail
            <span className="transition-transform group-open:rotate-90" aria-hidden>
              ›
            </span>
          </summary>
          <div className="space-y-5 pt-3">
            {response ? (
              <>
                <PersonalResponseProfilePanel profile={response.profile} />
                <div>
                  <p className="label-quiet">Evidence coverage</p>
                  <div className="mt-2">
                    <EvidenceCoveragePanel coverage={response.coverage} />
                  </div>
                </div>
                <div>
                  <p className="label-quiet">Recent response episodes</p>
                  <div className="mt-2">
                    <ResponseEpisodeList episodes={response.episodes} />
                  </div>
                </div>
                <div>
                  <p className="label-quiet">Adaptation history</p>
                  <div className="mt-2">
                    <AdaptationHistoryList history={response.adaptation_history} />
                  </div>
                </div>
              </>
            ) : (
              <Skeleton className="h-24 w-full" />
            )}

            {(today?.calibration?.summary.total ?? 0) > 0 ? (
              <div>
                <p className="label-quiet">In-session calibration</p>
                <div className="mt-2 space-y-2">
                  <p className="text-[0.78rem]">{today?.calibration?.summary.trend}</p>
                  <ul className="divide-y divide-subtle border-y border-subtle">
                    {(today?.calibration?.history ?? []).slice(-5).reverse().map((row) => (
                      <li
                        key={`${row.recorded_at}-${row.session_id ?? ""}`}
                        className="flex items-start justify-between gap-3 py-2.5"
                      >
                        <span className="min-w-0">
                          <span className="block text-[0.78rem] font-medium">{formatShortDate(row.date)}</span>
                          <span className="block text-[0.7rem] text-muted">
                            {row.focus ?? "Session"} · {row.effort ?? "—"}
                            {row.actual_rir !== null && row.actual_rir !== undefined ? ` · ${row.actual_rir} RIR` : ""}
                          </span>
                        </span>
                        <span
                          className={cn(
                            "shrink-0 rounded-full px-2 py-0.5 text-[0.62rem] font-semibold",
                            calibrationTone(row.result),
                          )}
                        >
                          {calibrationLabel(row.result)}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            ) : null}
          </div>
        </details>
      </Section>

      {/* 4 — Evidence */}
      <Section title="Evidence">
        <p className="title-metric">{confidence?.state ?? "—"}</p>
        <p className="mt-1 text-[0.8rem] text-muted">
          {relevantSessions !== null
            ? `Based on ${relevantSessions} relevant session${relevantSessions === 1 ? "" : "s"}`
            : "Personal evidence is still accumulating."}
        </p>

        <details className="group mt-3">
          <summary className="flex min-h-10 cursor-pointer list-none items-center gap-1 text-[0.78rem] font-medium text-muted">
            How this is calculated →
            <span className="transition-transform group-open:rotate-90" aria-hidden>
              ›
            </span>
          </summary>
          <div className="space-y-2 pt-2">
            <p className="text-[0.78rem] leading-relaxed">{confidence?.explanation ?? "—"}</p>
            {confidence?.note ? (
              <p className="text-[0.72rem] leading-relaxed text-muted">{confidence.note}</p>
            ) : null}
          </div>
        </details>
      </Section>

      {/* Signals — every chart, behind one expand. */}
      <details className="divider group pt-4">
        <summary className="flex min-h-11 cursor-pointer list-none items-center justify-between gap-3 text-[0.88rem] font-semibold">
          All signals
          <span className="text-[0.72rem] font-normal text-muted">{signalSeries.length} charts</span>
        </summary>
        <div className="pt-3">
          <p className="mb-3 text-[0.74rem] leading-relaxed text-muted">{data.missing_data_note}</p>
          <div className="grid gap-5 md:grid-cols-2">
            {signalSeries.map((series) => (
              <div key={series.key}>
                <div className="flex items-baseline justify-between gap-3">
                  <p className="text-[0.82rem] font-semibold">{series.label}</p>
                  <p className="text-[0.8rem] font-semibold tabular-nums">
                    {formatNumber(series.latest)}
                    <span className="ml-1 text-[0.68rem] font-normal text-muted">{series.unit}</span>
                  </p>
                </div>
                {series.baseline !== null ? (
                  <p className="mt-0.5 text-[0.68rem] text-muted">Baseline mean {formatNumber(series.baseline)}</p>
                ) : null}
                <div className="mt-2">
                  <TrendChart
                    points={series.points}
                    baseline={series.baseline}
                    unit={series.unit}
                    label={series.label}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </details>

      <p className="text-[0.72rem] leading-relaxed text-muted">
        Weekly exposure is maintained on{" "}
        <Link href="/train" className="font-medium text-foreground underline decoration-dotted underline-offset-2">
          Train
        </Link>
        , where it belongs with the session.
      </p>
    </div>
  );
}
