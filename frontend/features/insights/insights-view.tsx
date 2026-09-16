"use client";

import { useEffect, useState } from "react";

import { ExposureList } from "@/components/exposure-list";
import { PageHeader } from "@/components/page-header";
import { PersonalResponseSummary, ResponseEpisodeList } from "@/components/personal-response";
import { StatePanel } from "@/components/state-panel";
import { StatusBadge } from "@/components/status-badge";
import { TrendChart } from "@/components/trend-chart";
import { Card } from "@/components/ui/card";
import { Section } from "@/components/ui/section";
import { Segmented } from "@/components/ui/segmented";
import { Skeleton } from "@/components/ui/skeleton";
import { formatNumber, formatShortDate } from "@/lib/format";
import { asNumber, asString } from "@/lib/measurements";
import { useUserState } from "@/lib/state-provider";
import type { InsightsResponse } from "@/types/api";
import type { PersonalResponse } from "@/types/api";

const WINDOWS = [
  { value: 28, label: "28" },
  { value: 7, label: "7" },
  { value: 0, label: "All" },
];

export function InsightsView() {
  const { ready, loadInsights, loadPersonalResponse } = useUserState();
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
        <Skeleton className="h-32 w-full rounded-[var(--radius-card)]" />
        <Skeleton className="h-40 w-full" />
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

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Insights"
        title="Trends and load"
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

      <Card className="p-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="eyebrow">Training load</p>
            <p className="mt-1.5 text-[1.6rem] font-semibold tabular-nums leading-none">
              {formatNumber(asNumber(load.recent_7d_mean))}
              <span className="ml-1.5 text-[0.75rem] font-normal text-muted">AU last 7 days</span>
            </p>
          </div>
          {asString(load.status) ? <StatusBadge status={asString(load.status) as string} /> : null}
        </div>
        <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 border-t border-subtle pt-3 text-[0.75rem]">
          <div>
            <dt className="text-muted">21-day reference</dt>
            <dd className="font-medium tabular-nums">{formatNumber(asNumber(load.reference_21d_mean))} AU</dd>
          </div>
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
        <p className="mt-3 text-[0.68rem] leading-relaxed text-muted">
          Training load is duration × session RPE in AU — not session minutes and not sets.
        </p>
      </Card>

      <Section eyebrow="Signals" title="Recorded check-ins" description={data.missing_data_note}>
        <div className="grid gap-4 md:grid-cols-2">
          {data.series.map((series) => (
            <Card key={series.key} className="p-4">
              <div className="flex items-baseline justify-between gap-3">
                <p className="text-[0.82rem] font-semibold">{series.label}</p>
                <p className="text-[0.8rem] font-semibold tabular-nums">
                  {formatNumber(series.latest)}
                  <span className="ml-1 text-[0.68rem] font-normal text-muted">{series.unit}</span>
                </p>
              </div>
              {series.baseline !== null ? (
                <p className="mt-0.5 text-[0.66rem] text-muted">Baseline mean {formatNumber(series.baseline)}</p>
              ) : null}
              <div className="mt-2">
                <TrendChart points={series.points} baseline={series.baseline} unit={series.unit} label={series.label} />
              </div>
            </Card>
          ))}
        </div>
      </Section>

      <Section eyebrow="This week" title="Weekly exposure">
        <ExposureList exposure={data.exposure} />
      </Section>

      <Section
        eyebrow="Personal response"
        title="How you tend to respond"
        description="Built from your logged sessions, your own post-session feedback and the next morning check-in. Observed patterns only."
      >
        {response ? (
          <div className="space-y-4">
            {response.reason ? (
              <p className="text-[0.8rem] leading-relaxed">
                {response.adjustment ? response.reason : (response.detail ?? "No adjustment today.")}
              </p>
            ) : null}
            <PersonalResponseSummary response={response} />
            <ResponseEpisodeList episodes={response.episodes} />
          </div>
        ) : (
          <Skeleton className="h-32 w-full" />
        )}
      </Section>

      <Section eyebrow="History" title="Readiness assessments">
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
          <StatePanel
            tone="empty"
            title="No readiness assessments stored yet"
            body={`${data.available_check_ins} check-ins are available for the charts above. Saving a check-in records an assessment, and it appears here with its index and confidence.`}
          />
        )}
      </Section>
    </div>
  );
}
