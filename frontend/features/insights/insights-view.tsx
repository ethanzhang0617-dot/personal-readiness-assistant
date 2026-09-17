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
import { Sparkline } from "@/components/sparkline";
import { StatePanel } from "@/components/state-panel";
import { TrendChart } from "@/components/trend-chart";
import { Segmented } from "@/components/ui/segmented";
import { Skeleton } from "@/components/ui/skeleton";
import { calibrationLabel, calibrationTone } from "@/lib/calibration";
import { formatNumber, formatShortDate, statusHeadline } from "@/lib/format";
import { asNumber } from "@/lib/measurements";
import { useUserState } from "@/lib/state-provider";
import type { InsightsResponse, PersonalResponse } from "@/types/api";
import { cn } from "@/lib/utils";

const WINDOWS = [
  { value: 28, label: "28" },
  { value: 7, label: "7" },
  { value: 0, label: "All" },
];

// Insights: trend-first.
//
// Four visual modules — Readiness, Training, Personal response, Evidence — each
// with one takeaway and one visual. Charts, episodes and coverage are deliberate
// expands, and weekly exposure stays with Train where it belongs.

/** Data-derived trends, never invented copy. */
function readinessTrend(history: { index: number | null }[]): string | null {
  const values = history.map((row) => row.index).filter((value): value is number => value !== null);
  if (values.length < 3) return null;
  const latest = values[0];
  const mean = values.reduce((total, value) => total + value, 0) / values.length;
  const delta = latest - mean;
  if (delta >= 4) return "Trending up this week";
  if (delta <= -4) return "Trending down this week";
  return "Holding steady this week";
}

function loadTrend(recent: number | null, reference: number | null): string | null {
  if (recent === null || reference === null || reference === 0) return null;
  const ratio = (recent - reference) / reference;
  if (ratio <= -0.12) return "Below your own 21-day reference";
  if (ratio >= 0.12) return "Above your own 21-day reference";
  return "In line with your own 21-day reference";
}

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
      <div className="space-y-5">
        <Skeleton className="h-4 w-20" />
        <Skeleton className="h-8 w-52" />
        <Skeleton className="h-28 w-full rounded-[var(--radius-card)]" />
        <Skeleton className="h-28 w-full rounded-[var(--radius-card)]" />
      </div>
    );
  }
  if (error || !data) {
    return (
      <StatePanel
        tone="error"
        title="We couldn't load your insights"
        body={`${error ?? "No data was returned."} The rest of the product still works.`}
      />
    );
  }

  const load = data.load;
  const recentLoad = asNumber(load.recent_7d_mean);
  const referenceLoad = asNumber(load.reference_21d_mean);
  const loadSeries = data.series.find((series) => series.key === "session_load") ?? null;
  const signalSeries = data.series.filter((series) => series.key !== "session_load");
  const readinessSeries = data.series.find((series) => series.key === "ln_rmssd") ?? null;
  const confidence = response?.confidence ?? today?.training.recommendation.recommendation_confidence ?? null;
  const bands = [...(response?.profile?.bands ?? [])].sort((a, b) => {
    const order = ["High", "Moderate", "Low"];
    const left = order.indexOf(a.band);
    const right = order.indexOf(b.band);
    return (left === -1 ? 99 : left) - (right === -1 ? 99 : right);
  });
  const notableBand = bands.find((band) => band.observations > 0) ?? null;
  const patternLine = notableBand
    ? `${notableBand.band}-demand sessions tend to be followed by ${notableBand.pattern.replace(/\.$/, "").toLowerCase()} responses.`
    : (response?.detail ?? "No completed response episodes yet — log a session, add feedback and check in the next morning.");
  const relevantSessions = confidence?.relevant_episodes ?? response?.relevant_episodes ?? null;
  const trend = readinessTrend(data.readiness_history);
  const loadLine = loadTrend(recentLoad, referenceLoad);

  return (
    <div className="space-y-7">
      <PageHeader eyebrow="Insights" title="Your week in context" />

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

      {/* Readiness */}
      <section>
        <div className="flex items-baseline justify-between gap-3">
          <h2 className="title-section">Readiness</h2>
          <Link href="/readiness" className="text-[0.78rem] font-medium text-accent">
            View →
          </Link>
        </div>
        <p className="mt-2 text-[0.95rem] font-semibold">
          {trend ?? statusHeadline(today?.readiness.status ?? "INSUFFICIENT DATA")}
        </p>
        <p className="mt-1 text-[0.8rem] text-muted">
          Index {today?.readiness.index ?? "—"} · {statusHeadline(today?.readiness.status ?? "")}
        </p>
        {readinessSeries ? (
          <div className="mt-3">
            <Sparkline points={readinessSeries.points} />
          </div>
        ) : null}
      </section>

      {/* Training */}
      <section className="divider pt-6">
        <h2 className="title-section">Training</h2>
        <p className="title-metric mt-2">
          {formatNumber(recentLoad)}
          <span className="ml-1.5 text-[0.78rem] font-normal text-muted">pts · last 7 days</span>
        </p>
        {loadLine ? <p className="mt-1 text-[0.8rem] text-muted">{loadLine}</p> : null}
        {loadSeries ? (
          <div className="mt-3">
            <Sparkline points={loadSeries.points} />
          </div>
        ) : null}

        <details className="group mt-3">
          <summary className="flex min-h-10 cursor-pointer list-none items-center gap-1 text-[0.78rem] font-medium text-muted">
            Load detail
            <span className="transition-transform group-open:rotate-90" aria-hidden>
              ›
            </span>
          </summary>
          <div className="pt-3">
            <dl className="grid grid-cols-2 gap-x-4 gap-y-3">
              <div>
                <dt className="text-[0.72rem] text-muted">21-day reference</dt>
                <dd className="mt-0.5 text-[0.85rem] font-medium tabular-nums">{formatNumber(referenceLoad)} pts</dd>
              </div>
              <div>
                <dt className="text-[0.72rem] text-muted">Sessions, last 14 days</dt>
                <dd className="mt-0.5 text-[0.85rem] font-medium tabular-nums">{data.sessions_last_14_days}</dd>
              </div>
            </dl>
            <p className="mt-3 text-[0.72rem] leading-relaxed text-muted">
              Training Load Points are calculated from session duration × session RPE. They are relative workload
              units for comparing training stress over time — not kilograms, calories or an absolute physiological
              measurement.
            </p>
          </div>
        </details>
      </section>

      {/* Personal response */}
      <section className="divider pt-6">
        <div className="flex items-baseline justify-between gap-3">
          <h2 className="title-section">Personal response</h2>
          <Link href="/personal-response" className="text-[0.78rem] font-medium text-accent">
            View Personal Response →
          </Link>
        </div>
        <p className="mt-2 text-[0.88rem] leading-relaxed">{patternLine}</p>
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <ConfidenceBadge confidence={confidence} />
          {relevantSessions !== null ? (
            <span className="text-[0.74rem] text-muted">
              Based on {relevantSessions} relevant session{relevantSessions === 1 ? "" : "s"}
            </span>
          ) : null}
        </div>

        <ul className="mt-4">
          {(bands.length > 0 ? bands : []).map((band) => (
            <li key={band.band} className="hairline flex items-center justify-between gap-3 py-3 last:border-b-0">
              <span
                className="shrink-0 rounded-full px-2.5 py-1 text-[0.68rem] font-semibold"
                style={{
                  backgroundColor:
                    band.observations === 0
                      ? "var(--surface-secondary)"
                      : band.pattern.toLowerCase().includes("poorer")
                        ? "var(--status-red-soft)"
                        : band.pattern.toLowerCase().includes("better")
                          ? "var(--status-green-soft)"
                          : "var(--accent-soft)",
                  color:
                    band.observations === 0
                      ? "var(--text-muted)"
                      : band.pattern.toLowerCase().includes("poorer")
                        ? "var(--status-red)"
                        : band.pattern.toLowerCase().includes("better")
                          ? "var(--status-green)"
                          : "var(--accent-primary)",
                }}
              >
                {band.band}
              </span>
              <span className="min-w-0 flex-1 truncate text-[0.84rem]">{band.pattern}</span>
              <span className="shrink-0 text-[0.74rem] text-muted">
                {band.observations > 0 ? `${band.observations} sessions` : "No data"}
              </span>
            </li>
          ))}
        </ul>

        <details id="personal-response" className="group mt-3">
          <summary className="flex min-h-10 cursor-pointer list-none items-center gap-1 text-[0.78rem] font-medium text-muted">
            Response detail
            <span className="transition-transform group-open:rotate-90" aria-hidden>
              ›
            </span>
          </summary>
          <div className="space-y-5 pt-4">
            {response ? (
              <>
                <PersonalResponseProfilePanel profile={response.profile} />
                <div>
                  <p className="label-quiet mb-2">Evidence coverage</p>
                  <EvidenceCoveragePanel coverage={response.coverage} />
                </div>
                <div>
                  <p className="label-quiet mb-2">Recent response episodes</p>
                  <ResponseEpisodeList episodes={response.episodes} />
                </div>
                <div>
                  <p className="label-quiet mb-2">Adaptation history</p>
                  <AdaptationHistoryList history={response.adaptation_history} />
                </div>
              </>
            ) : (
              <Skeleton className="h-24 w-full" />
            )}

            {(today?.calibration?.summary.total ?? 0) > 0 ? (
              <div>
                <p className="label-quiet mb-2">In-session calibration</p>
                <p className="text-[0.8rem]">{today?.calibration?.summary.trend}</p>
                <ul>
                  {(today?.calibration?.history ?? []).slice(-5).reverse().map((row) => (
                    <li
                      key={`${row.recorded_at}-${row.session_id ?? ""}`}
                      className="hairline flex items-start justify-between gap-3 py-2.5 last:border-b-0"
                    >
                      <span className="min-w-0">
                        <span className="block text-[0.8rem] font-medium">{formatShortDate(row.date)}</span>
                        <span className="block text-[0.72rem] text-muted">
                          {row.focus ?? "Session"} · {row.effort ?? "—"}
                          {row.actual_rir !== null && row.actual_rir !== undefined ? ` · ${row.actual_rir} RIR` : ""}
                        </span>
                      </span>
                      <span
                        className={cn(
                          "shrink-0 rounded-full px-2 py-0.5 text-[0.64rem] font-semibold",
                          calibrationTone(row.result),
                        )}
                      >
                        {calibrationLabel(row.result)}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </div>
        </details>
      </section>

      {/* Evidence */}
      <section className="divider pt-6">
        <h2 className="title-section">Evidence</h2>
        <p className="mt-2 text-[1.1rem] font-semibold">{confidence?.state ?? "—"}</p>
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
          <div className="space-y-2 pt-3">
            <p className="text-[0.8rem] leading-relaxed">{confidence?.explanation ?? "—"}</p>
            {confidence?.note ? <p className="text-[0.74rem] leading-relaxed text-muted">{confidence.note}</p> : null}
          </div>
        </details>
      </section>

      {/* Every chart, behind one expand. */}
      <details className="divider group pt-6">
        <summary className="flex min-h-11 cursor-pointer list-none items-center justify-between gap-3 text-[0.9rem] font-semibold">
          All signals
          <span className="text-[0.74rem] font-normal text-muted">{signalSeries.length} charts</span>
        </summary>
        <div className="pt-4">
          <p className="mb-4 text-[0.76rem] leading-relaxed text-muted">{data.missing_data_note}</p>
          <div className="grid gap-6 md:grid-cols-2">
            {signalSeries.map((series) => (
              <div key={series.key}>
                <div className="flex items-baseline justify-between gap-3">
                  <p className="text-[0.84rem] font-semibold">{series.label}</p>
                  <p className="text-[0.84rem] font-semibold tabular-nums">
                    {formatNumber(series.latest)}
                    <span className="ml-1 text-[0.7rem] font-normal text-muted">{series.unit}</span>
                  </p>
                </div>
                {series.baseline !== null ? (
                  <p className="mt-0.5 text-[0.7rem] text-muted">Baseline mean {formatNumber(series.baseline)}</p>
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

      <p className="text-[0.74rem] leading-relaxed text-muted">
        Weekly exposure is maintained on{" "}
        <Link href="/train" className="font-medium text-accent underline decoration-dotted underline-offset-2">
          Train
        </Link>
        , where it belongs with the session.
      </p>
    </div>
  );
}
