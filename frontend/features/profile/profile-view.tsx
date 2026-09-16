import Link from "next/link";
import { ArrowRight, CircleCheck, Info } from "lucide-react";

import { PageHeader } from "@/components/page-header";
import { StatePanel } from "@/components/state-panel";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { api } from "@/lib/api";
import { formatNumber } from "@/lib/format";

function Row({ label, value }: { label: string; value: string | number | null | undefined }) {
  return (
    <div className="flex items-baseline justify-between gap-3 py-2">
      <dt className="text-[0.78rem] text-muted">{label}</dt>
      <dd className="text-right text-sm font-medium">{value ?? "—"}</dd>
    </div>
  );
}

export async function ProfileView({ profileId }: { profileId?: string }) {
  const [profile, health, readiness] = await Promise.all([
    api.profile(profileId),
    api.health(),
    api.readiness(profileId),
  ]);

  if (!profile.ok) {
    return <StatePanel tone="error" title="Profile unavailable" body={profile.error} />;
  }

  const data = profile.data;
  const baseline = readiness.ok ? readiness.data.baseline : {};

  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow="Profile"
        title={data.name}
        description="Goal, programme and the context every recommendation is built from."
        actions={data.is_demo ? <Badge variant="neutral">DEMO</Badge> : null}
      />

      <Card className="p-4">
        <p className="eyebrow text-muted">Training setup</p>
        <dl className="mt-2 divide-y divide-subtle">
          <Row label="Goal" value={data.training_goal} />
          <Row label="Programme / split" value={data.training_split_preference} />
          <Row label="Training level" value={data.training_level} />
          <Row label="Primary activity" value={data.primary_activity} />
          <Row label="Target sessions / week" value={data.target_sessions_per_week} />
          <Row
            label="Personal sleep need"
            value={data.personal_sleep_need !== null ? `${formatNumber(data.personal_sleep_need)} h` : null}
          />
        </dl>
      </Card>

      <Card className="p-4">
        <p className="eyebrow text-muted">Personal baseline</p>
        <dl className="mt-2 divide-y divide-subtle">
          <Row label="Valid paired observations" value={(baseline as Record<string, unknown>).valid_days as number ?? "—"} />
          <Row label="Baseline window" value={`${(baseline as Record<string, unknown>).window_days as number ?? 28} days`} />
          <Row label="Baseline confidence" value={(baseline as Record<string, unknown>).confidence as string ?? "—"} />
        </dl>
        <p className="mt-2 text-[0.68rem] leading-relaxed text-muted">
          Readiness compares today against these personal observations rather than population cut-offs. Baseline
          confidence describes data sufficiency, not model certainty.
        </p>
      </Card>

      <Card className="p-4">
        <p className="eyebrow text-muted">Weekly set targets</p>
        {Object.keys(data.weekly_set_targets).length > 0 ? (
          <ul className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1.5 md:grid-cols-3">
            {Object.entries(data.weekly_set_targets).map(([group, target]) => (
              <li key={group} className="flex items-baseline justify-between gap-2">
                <span className="text-[0.78rem]">{group}</span>
                <span className="text-[0.78rem] tabular-nums text-muted">{formatNumber(target)}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-3 text-sm text-muted">No weekly set targets are configured.</p>
        )}
        <p className="mt-2 text-[0.68rem] text-muted">
          Targets are planning inputs, not universal optimal-volume claims.
        </p>
      </Card>

      <Card className="p-4">
        <p className="eyebrow text-muted">Data sources</p>
        <ul className="mt-3 space-y-2 text-sm">
          <li className="flex items-start gap-2">
            <CircleCheck className="mt-0.5 h-4 w-4 shrink-0 text-muted" aria-hidden />
            Morning check-in: HRV (RMSSD), resting heart rate, sleep duration and quality, fatigue, soreness, stress,
            motivation, local soreness and safety screen.
          </li>
          <li className="flex items-start gap-2">
            <CircleCheck className="mt-0.5 h-4 w-4 shrink-0 text-muted" aria-hidden />
            Completed sessions: duration, session RPE, muscles and working sets.
          </li>
          <li className="flex items-start gap-2">
            <CircleCheck className="mt-0.5 h-4 w-4 shrink-0 text-muted" aria-hidden />
            No wearable integration and no remote personal-history database in this phase.
          </li>
        </ul>
      </Card>

      <Card className="p-4">
        <p className="eyebrow text-muted">AI and privacy</p>
        {health.ok ? (
          <p className="mt-2 text-sm text-muted">
            Explanation provider: <span className="font-medium text-foreground">{health.data.ai_provider}</span> ·{" "}
            {health.data.ai_explanations_enabled ? "explanations enabled" : "explanations disabled (deterministic answers only)"}.
            The provider credential is held by the API server and is never sent to this browser.
          </p>
        ) : (
          <p className="mt-2 text-sm text-muted">{health.error}</p>
        )}
        <p className="mt-2 text-[0.68rem] leading-relaxed text-muted">
          Personal factual questions are answered from your recorded data without any provider call. When you ask an
          explanation question, a summarised context and the recent Coach messages are sent to the configured AI
          provider. In the Streamlit V1.1 reference app, saved history stays in this browser&apos;s IndexedDB; the Phase 1
          API serves the fixed demo profiles only and stores nothing.
        </p>
      </Card>

      <Link
        href="/profile/science"
        className="flex min-h-14 items-center justify-between gap-3 rounded-[var(--radius-card)] border border-subtle bg-surface px-4 text-sm font-medium transition-colors hover:bg-surface-muted"
      >
        <span>
          Science &amp; Logic
          <span className="block text-[0.7rem] font-normal text-muted">
            Evidence boundaries, heuristics and 13 verified references
          </span>
        </span>
        <ArrowRight className="h-4 w-4 text-muted" aria-hidden />
      </Link>

      <p className="flex items-start gap-2 text-[0.68rem] leading-relaxed text-muted">
        <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
        About: an educational decision-support prototype. Not a medical device, diagnosis, injury prediction or
        clinically validated training prescription.
      </p>
    </div>
  );
}
