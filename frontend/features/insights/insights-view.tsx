"use client";

import { useEffect, useState } from "react";

import { PageHeader } from "@/components/page-header";
import { StatePanel } from "@/components/state-panel";
import { StatusBadge } from "@/components/status-badge";
import { TrendChart } from "@/components/trend-chart";
import { Card } from "@/components/ui/card";
import { formatNumber, formatShortDate } from "@/lib/format";
import { asNumber, asString } from "@/lib/measurements";
import { useUserState } from "@/lib/state-provider";
import type { InsightsResponse } from "@/types/api";
import { cn } from "@/lib/utils";

const WINDOWS = [
  { value: 7, label: "Last 7 check-ins" },
  { value: 28, label: "Last 28 check-ins" },
  { value: 0, label: "All check-ins" },
];

export function InsightsView() {
  const { ready, loadInsights } = useUserState();
  const [window, setWindow] = useState(28);
  const [data, setData] = useState<InsightsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

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

  // Loading is derived, not stored: no data and no error means a request is in flight.
  if (!ready || (!data && !error)) {
    return <StatePanel title="Loading insights…" body="Reading recorded check-ins from this browser." />;
  }
  if (error || !data) {
    return <StatePanel tone="error" title="Insights are unavailable" body={error ?? "No data was returned."} />;
  }

  const load = data.load;

  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow="Insights"
        title="Trends and load"
        description="Patterns across your own recorded signals and completed training."
      />

      <div className="flex flex-wrap gap-2">
        {WINDOWS.map((option) => (
          <button
            key={option.value}
            type="button"
            onClick={() => {
              if (option.value === window) return;
              setData(null);
              setError(null);
              setWindow(option.value);
            }}
            className={cn(
              "min-h-9 rounded-full border px-3 text-[0.75rem] font-medium transition-colors",
              window === option.value
                ? "border-transparent bg-primary text-primary-foreground"
                : "border-subtle bg-surface text-muted",
            )}
          >
            {option.label}
          </button>
        ))}
      </div>

      {data.series.map((series) => (
        <Card key={series.key} className="p-4">
          <div className="flex items-baseline justify-between gap-3">
            <p className="eyebrow text-muted">{series.label}</p>
            <p className="text-sm font-semibold tabular-nums">
              {formatNumber(series.latest)}
              <span className="ml-1 text-[0.68rem] font-normal text-muted">{series.unit}</span>
            </p>
          </div>
          {series.baseline !== null ? (
            <p className="mt-0.5 text-[0.66rem] text-muted">Baseline mean {formatNumber(series.baseline)}</p>
          ) : null}
          <div className="mt-2">
            <TrendChart points={series.points} baseline={series.baseline} label={`${series.label} trend`} />
          </div>
          <p className="mt-2 text-[0.66rem] text-muted">{series.note}</p>
        </Card>
      ))}

      <Card className="p-4">
        <p className="eyebrow text-muted">Training load</p>
        <div className="mt-2 flex items-baseline justify-between gap-3">
          <p className="text-sm">
            Last 7 complete days: <span className="font-semibold">{formatNumber(asNumber(load.recent_7d_mean))}</span> AU
          </p>
          {asString(load.status) ? <StatusBadge status={asString(load.status) as string} /> : null}
        </div>
        <p className="mt-1 text-[0.72rem] text-muted">
          Reference: {formatNumber(asNumber(load.reference_21d_mean))} AU over the preceding 21 complete days ·{" "}
          {String(load.calendar_days_covered ?? "—")} of {String(load.calendar_days_required ?? "—")} calendar days
          covered ({String(load.data_sufficiency ?? "unknown")}).
        </p>
        <p className="mt-1 text-[0.66rem] text-muted">
          Training load is duration × session RPE in AU. It is not session minutes and not sets.
        </p>
      </Card>

      <Card className="p-4">
        <p className="eyebrow text-muted">Weekly exposure</p>
        <ul className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 md:grid-cols-3">
          {data.exposure.groups.map((group) => (
            <li key={group.group} className="flex items-baseline justify-between gap-2">
              <span className="text-[0.78rem]">{group.group}</span>
              <span className="text-[0.78rem] tabular-nums text-muted">
                {formatNumber(group.value)}
                {group.target ? ` / ${formatNumber(group.target)}` : ""}
              </span>
            </li>
          ))}
        </ul>
        <p className="mt-2 text-[0.66rem] text-muted">{data.exposure.note}</p>
      </Card>

      <Card className="p-4">
        <p className="eyebrow text-muted">Readiness history</p>
        {data.readiness_history.length > 0 ? (
          <ul className="mt-3 divide-y divide-subtle">
            {data.readiness_history.slice(0, 10).map((row) => (
              <li key={row.date} className="flex items-center justify-between gap-3 py-2">
                <span className="text-[0.78rem]">{formatShortDate(row.date)}</span>
                <span className="flex items-center gap-2">
                  <span className="text-[0.7rem] text-muted">Index {row.index ?? "—"}</span>
                  {row.status ? <StatusBadge status={row.status} /> : null}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-3 text-sm text-muted">
            No readiness assessments are stored yet. Saving a check-in records one, and it appears here.
          </p>
        )}
      </Card>

      <StatePanel
        tone="empty"
        title={`${data.available_check_ins} recorded check-ins in total`}
        body={data.missing_data_note}
      />
    </div>
  );
}
