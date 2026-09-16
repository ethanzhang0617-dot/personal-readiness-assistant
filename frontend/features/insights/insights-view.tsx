import { Info } from "lucide-react";

import { PageHeader } from "@/components/page-header";
import { StatePanel } from "@/components/state-panel";
import { StatusBadge } from "@/components/status-badge";
import { Card } from "@/components/ui/card";
import { api } from "@/lib/api";
import { formatNumber } from "@/lib/format";
import { asNumber, asRecord, asString } from "@/lib/measurements";

/**
 * Insights (Phase 1 shell): shows the daily values the API already exposes.
 * No new analytics model is introduced here.
 */
export async function InsightsView({ profileId }: { profileId?: string }) {
  const [readiness, exposure] = await Promise.all([api.readiness(profileId), api.exposure(profileId)]);

  if (!readiness.ok) {
    return <StatePanel tone="error" title="Insights are unavailable" body={readiness.error} />;
  }

  const { measurements } = readiness.data;
  const load = asRecord(measurements.training_load);
  const hrv = asRecord(measurements.hrv);
  const rhr = asRecord(measurements.rhr);
  const sleep = asRecord(measurements.sleep_duration);
  const checkIn = readiness.data.check_in;

  const metrics = [
    {
      label: "HRV (LnRMSSD z)",
      value: asNumber(hrv.z_score) !== null ? `${formatNumber(asNumber(hrv.z_score), 2)} SD` : "—",
      status: asString(hrv.status),
      note: "today vs your own baseline",
    },
    {
      label: "Resting HR",
      value: asNumber(checkIn.resting_hr_bpm) !== null ? `${formatNumber(asNumber(checkIn.resting_hr_bpm))} bpm` : "—",
      status: asString(rhr.status),
      note: asNumber(rhr.z_score) !== null ? `${formatNumber(asNumber(rhr.z_score), 2)} SD vs baseline` : "baseline pending",
    },
    {
      label: "Sleep",
      value: asNumber(checkIn.sleep_hours) !== null ? `${formatNumber(asNumber(checkIn.sleep_hours))} h` : "—",
      status: asString(sleep.status),
      note: asNumber(sleep.ratio) !== null ? `${formatNumber(asNumber(sleep.ratio), 2)}× of your sleep need` : "sleep need not recorded",
    },
    {
      label: "Training load (AU)",
      value: asNumber(load.recent_7d_mean) !== null ? formatNumber(asNumber(load.recent_7d_mean)) : "—",
      status: asString(load.status),
      note: `${formatNumber(asNumber(load.reference_21d_mean))} AU reference over 21 days`,
    },
  ];

  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow="Insights"
        title="Signals and load"
        description="Today's values, each with its unit, baseline comparison and data sufficiency."
      />

      <Card className="divide-y divide-subtle">
        {metrics.map((metric) => (
          <div key={metric.label} className="flex items-start justify-between gap-3 p-4">
            <div>
              <p className="text-sm font-medium">{metric.label}</p>
              <p className="mt-0.5 text-[0.7rem] text-muted">{metric.note}</p>
            </div>
            <div className="text-right">
              <p className="text-lg font-semibold tabular-nums">{metric.value}</p>
              {metric.status ? <StatusBadge status={metric.status} className="mt-1" /> : null}
            </div>
          </div>
        ))}
      </Card>

      <Card className="p-4">
        <p className="eyebrow text-muted">Readiness domains</p>
        <ul className="mt-3 space-y-2">
          {readiness.data.domains.map((domain) => (
            <li key={domain.key} className="flex items-center justify-between gap-3">
              <span className="text-sm">{domain.label}</span>
              <StatusBadge status={domain.status} />
            </li>
          ))}
        </ul>
        <p className="mt-3 text-[0.68rem] leading-relaxed text-muted">
          A domain is classifiable only when today&apos;s input exists and the personal baseline has enough observations.
          Fewer than three classifiable domains return INSUFFICIENT DATA by design.
        </p>
      </Card>

      <Card className="p-4">
        <p className="eyebrow text-muted">Weekly exposure</p>
        {exposure.ok ? (
          <ul className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 md:grid-cols-3">
            {exposure.data.groups.map((group) => (
              <li key={group.group} className="flex items-baseline justify-between gap-2">
                <span className="text-[0.78rem]">{group.group}</span>
                <span className="text-[0.78rem] tabular-nums text-muted">
                  {formatNumber(group.value)}
                  {group.target ? ` / ${formatNumber(group.target)}` : ""}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-3 text-sm text-muted">{exposure.error}</p>
        )}
      </Card>

      <StatePanel
        tone="empty"
        title="Trend charts are not part of the Phase 1 API"
        body="The Phase 1 backend exposes today's values and the completed-session list. Multi-day HRV, resting-HR, sleep and load charts remain in the Streamlit V1.1 reference implementation until a history endpoint is added."
      />

      <p className="flex items-start gap-2 text-[0.68rem] leading-relaxed text-muted">
        <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
        Every value above comes from the deterministic engines. Thresholds and windows are disclosed product heuristics,
        not validated clinical cut-offs.
      </p>
    </div>
  );
}
