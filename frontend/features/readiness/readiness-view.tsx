"use client";

import { Activity, Dumbbell, HeartPulse, Moon, Smile, type LucideIcon } from "lucide-react";

import { PageHeader } from "@/components/page-header";
import { ReadinessRing } from "@/components/readiness-ring";
import { StatePanel } from "@/components/state-panel";
import { StatusRow } from "@/components/status-row";
import { Skeleton } from "@/components/ui/skeleton";
import { formatNumber, statusHeadline, statusLabel } from "@/lib/format";
import { asNumber, asRecord, asString } from "@/lib/measurements";
import { useUserState } from "@/lib/state-provider";

// Readiness: status first.
//
// One large visual, one short summary, then the contributors as open rows on a
// single vertical layout — no card stack. Everything the engine recorded that
// does not earn a row sits behind one deliberate expand.

interface Contributor {
  key: string;
  label: string;
  icon: LucideIcon;
  status: string;
  value?: string;
  baseline?: string;
}

function buildContributors(
  measurements: Record<string, unknown>,
  baseline: Record<string, unknown>,
  domains: { key: string; label: string; status: string }[],
) {
  const hrv = asRecord(measurements.hrv);
  const rhr = asRecord(measurements.rhr);
  const sleep = asRecord(measurements.sleep_duration);
  const domainStatus = (key: string, fallback = "INSUFFICIENT DATA") =>
    domains.find((domain) => domain.key === key)?.status ?? fallback;

  const rows: Contributor[] = [];

  const hrvValue = asNumber(hrv.value);
  if (hrvValue !== null) {
    rows.push({
      key: "hrv",
      label: "HRV",
      icon: HeartPulse,
      status: asString(hrv.status) ?? domainStatus("autonomic"),
      value: `${formatNumber(hrvValue)} lnRMSSD`,
      baseline: asNumber(baseline.lnrmssd_mean) !== null ? `Baseline ${formatNumber(asNumber(baseline.lnrmssd_mean) ?? undefined)}` : undefined,
    });
  }

  const rhrValue = asNumber(rhr.value);
  if (rhrValue !== null) {
    rows.push({
      key: "rhr",
      label: "Resting heart rate",
      icon: Activity,
      status: asString(rhr.status) ?? domainStatus("autonomic"),
      value: `${formatNumber(rhrValue)} bpm`,
      baseline: asNumber(baseline.rhr_mean) !== null ? `Baseline ${formatNumber(asNumber(baseline.rhr_mean) ?? undefined)} bpm` : undefined,
    });
  }

  const sleepRatio = asNumber(sleep.ratio);
  rows.push({
    key: "sleep",
    label: "Sleep",
    icon: Moon,
    status: asString(sleep.status) ?? domainStatus("sleep"),
    value: sleepRatio !== null ? `${Math.round(sleepRatio * 100)}% of your sleep need` : undefined,
    baseline: asNumber(baseline.sleep_mean) !== null ? `Baseline ${formatNumber(asNumber(baseline.sleep_mean) ?? undefined)} h` : undefined,
  });

  rows.push({
    key: "subjective",
    label: "Subjective wellness",
    icon: Smile,
    status: domainStatus("subjective"),
    value: undefined,
  });

  rows.push({
    key: "training_load",
    label: "Training load",
    icon: Dumbbell,
    status: domainStatus("training_load"),
    value: undefined,
  });

  return rows;
}

export function ReadinessView() {
  const { ready, today } = useUserState();

  if (!ready) {
    return (
      <div className="space-y-5">
        <Skeleton className="h-4 w-20" />
        <Skeleton className="h-8 w-40" />
        <Skeleton className="h-[16rem] w-full rounded-[var(--radius-card)]" />
      </div>
    );
  }

  if (!today) {
    return (
      <StatePanel
        tone="error"
        title="We couldn't load your readiness"
        body="Your training data did not respond. Reload the page to try again."
      />
    );
  }

  const readiness = today.readiness;
  const max = readiness.index_scale?.max ?? 100;
  const baseline = asRecord(readiness.baseline);
  const contributors = buildContributors(readiness.measurements, baseline, readiness.domains);
  const sleepMean = asNumber(baseline.sleep_mean);
  const hrvMean = asNumber(baseline.lnrmssd_mean);
  const rhrMean = asNumber(baseline.rhr_mean);
  const baselineRows = [
    hrvMean !== null ? { label: "HRV baseline", value: `${formatNumber(hrvMean)} lnRMSSD` } : null,
    rhrMean !== null ? { label: "Resting HR baseline", value: `${formatNumber(rhrMean)} bpm` } : null,
    sleepMean !== null ? { label: "Sleep baseline", value: `${formatNumber(sleepMean)} h` } : null,
    asNumber(baseline.valid_days) !== null ? { label: "Valid observations", value: String(asNumber(baseline.valid_days)) } : null,
    asNumber(baseline.window_days) !== null ? { label: "Baseline window", value: `${asNumber(baseline.window_days)} days` } : null,
    asString(baseline.confidence) ? { label: "Baseline confidence", value: asString(baseline.confidence) as string } : null,
  ].filter((row): row is { label: string; value: string } => row !== null);

  return (
    <div className="space-y-6">
      <PageHeader back={{ href: "/", label: "Today" }} eyebrow="Readiness" title="How ready you are today" />

      <section className="flex flex-col items-center gap-5 md:flex-row md:items-center md:gap-10">
        <ReadinessRing
          index={readiness.index}
          max={max}
          status={readiness.status}
          size={216}
          className="shrink-0"
        />
        <div className="min-w-0 text-center md:text-left">
          <p className="text-[0.95rem] font-semibold" style={{ color: "var(--text-primary)" }}>
            {statusHeadline(readiness.status)} · {statusLabel(readiness.status)}
          </p>
          <p className="mt-2 text-[0.88rem] leading-relaxed text-secondary">
            {readiness.explanation ?? "No readiness interpretation is available for today."}
          </p>
          {readiness.confidence_note ? (
            <p className="mt-2 text-[0.76rem] leading-relaxed text-muted">{readiness.confidence_note}</p>
          ) : null}
        </div>
      </section>

      <section className="divider pt-5">
        <h2 className="title-section mb-1">Key contributors</h2>
        <ul>
          {contributors.map((row) => (
            <li key={row.key} className="hairline last:border-b-0">
              <StatusRow
                icon={row.icon}
                label={row.label}
                status={row.status}
                statusLabel={statusLabel(row.status)}
                value={row.value}
                detail={row.baseline}
              />
            </li>
          ))}
        </ul>
      </section>

      <details className="divider group pt-5">
        <summary className="flex min-h-11 cursor-pointer list-none items-center justify-between gap-3 text-[0.86rem] font-medium">
          Detailed evidence
          <span className="text-[0.72rem] text-muted">{readiness.contributors.length} recorded factors</span>
        </summary>

        <div className="space-y-5 pt-4">
          {readiness.contributors.length > 0 ? (
            <ul className="space-y-2">
              {readiness.contributors.map((line) => (
                <li key={line} className="text-[0.82rem] leading-relaxed text-secondary">
                  {line}
                </li>
              ))}
            </ul>
          ) : null}

          {readiness.why_this_status.length > 0 ? (
            <ul className="space-y-2">
              {readiness.why_this_status.map((line) => (
                <li key={line} className="text-[0.8rem] leading-relaxed text-muted">
                  {line}
                </li>
              ))}
            </ul>
          ) : null}

          {baselineRows.length > 0 ? (
            <dl className="grid grid-cols-2 gap-x-4 gap-y-3">
              {baselineRows.map((row) => (
                <div key={row.label}>
                  <dt className="text-[0.72rem] text-muted">{row.label}</dt>
                  <dd className="mt-0.5 text-[0.84rem] font-medium tabular-nums">{row.value}</dd>
                </div>
              ))}
            </dl>
          ) : null}

          {readiness.limitations.length > 0 ? (
            <ul className="space-y-1.5">
              {readiness.limitations.map((line) => (
                <li key={line} className="text-[0.74rem] leading-relaxed text-muted">
                  {line}
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      </details>
    </div>
  );
}
