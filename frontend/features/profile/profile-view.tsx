"use client";

import Link from "next/link";
import { ArrowRight, Info } from "lucide-react";
import { useEffect, useState } from "react";

import { PageHeader } from "@/components/page-header";
import { ProfileSwitcher } from "@/components/profile-switcher";
import { ScenarioSwitcher } from "@/components/scenario-switcher";
import { StatePanel } from "@/components/state-panel";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { api } from "@/lib/api";
import { formatNumber } from "@/lib/format";
import { useUserState } from "@/lib/state-provider";
import type { ProfileEdits, ProfileOptionsResponse } from "@/types/api";
import { cn } from "@/lib/utils";

export function ProfileView() {
  const { ready, today, saveProfile, busy, scenario } = useUserState();
  const [options, setOptions] = useState<ProfileOptionsResponse | null>(null);
  const [form, setForm] = useState<ProfileEdits>({});
  const [targets, setTargets] = useState<Record<string, number>>({});
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.profileOptions().then((result) => {
      if (result.ok) setOptions(result.data);
    });
  }, []);

  useEffect(() => {
    if (!today) return;
    const profile = today.profile;
    setForm({
      name: profile.name,
      age: profile.age,
      sex: profile.sex,
      primary_activity: profile.primary_activity,
      training_goal: profile.training_goal,
      training_level: profile.training_level,
      training_split_preference: profile.training_split_preference,
      personal_sleep_need: profile.personal_sleep_need,
      target_sessions_per_week: profile.target_sessions_per_week,
    });
    setTargets(profile.weekly_set_targets ?? {});
  }, [today]);

  if (!ready || !today) {
    return <StatePanel title="Loading your profile…" body="Reading local data from this browser." />;
  }

  const profile = today.profile;
  const baseline = (today.readiness.baseline ?? {}) as Record<string, unknown>;

  const save = async () => {
    setMessage(null);
    setError(null);
    const result = await saveProfile({ ...form, weekly_set_targets: targets });
    if (result.ok) setMessage(result.message ?? "Profile saved.");
    else setError(result.error ?? "The profile could not be saved.");
  };

  const select = (key: keyof ProfileEdits, label: string, values: string[] | undefined) => (
    <label className="block" key={String(key)}>
      <span className="text-[0.78rem] text-muted">{label}</span>
      <select
        value={String(form[key] ?? "")}
        onChange={(event) => setForm((current) => ({ ...current, [key]: event.target.value }))}
        className="mt-1 min-h-11 w-full rounded-[var(--radius-control)] border border-subtle bg-surface px-3 text-sm"
      >
        {(values ?? []).map((value) => (
          <option key={value} value={value}>
            {value}
          </option>
        ))}
      </select>
    </label>
  );

  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow="Profile"
        title={profile.name}
        description="Goal, programme and the context every recommendation is built from."
        actions={profile.is_demo ? <Badge variant="neutral">DEMO</Badge> : null}
      />

      {message ? <StatePanel tone="info" title="Saved" body={message} /> : null}
      {error ? <StatePanel tone="error" title="Not saved" body={error} /> : null}

      <ProfileSwitcher />

      <Card className="space-y-3 p-4">
        <p className="eyebrow text-muted">Goal and programme</p>
        <label className="block">
          <span className="text-[0.78rem] text-muted">Name</span>
          <input
            value={String(form.name ?? "")}
            onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
            className="mt-1 min-h-11 w-full rounded-[var(--radius-control)] border border-subtle bg-surface px-3 text-sm"
          />
        </label>
        {select("training_goal", "Training goal", options?.goals)}
        {select("training_split_preference", "Preferred training split", options?.splits)}
        {select("training_level", "Training level", options?.levels)}
        {select("primary_activity", "Primary activity", options?.activities)}
      </Card>

      <Card className="space-y-3 p-4">
        <p className="eyebrow text-muted">Baseline inputs</p>
        <div className="grid grid-cols-2 gap-3">
          <label className="block">
            <span className="text-[0.78rem] text-muted">Age</span>
            <input
              type="number"
              min={16}
              max={100}
              value={Number(form.age ?? 25)}
              onChange={(event) => setForm((current) => ({ ...current, age: Number(event.target.value) }))}
              className="mt-1 min-h-11 w-full rounded-[var(--radius-control)] border border-subtle bg-surface px-3 text-sm"
            />
          </label>
          <label className="block">
            <span className="text-[0.78rem] text-muted">Sleep need (hours)</span>
            <input
              type="number"
              step={0.1}
              min={4}
              max={12}
              value={Number(form.personal_sleep_need ?? 8)}
              onChange={(event) =>
                setForm((current) => ({ ...current, personal_sleep_need: Number(event.target.value) }))
              }
              className="mt-1 min-h-11 w-full rounded-[var(--radius-control)] border border-subtle bg-surface px-3 text-sm"
            />
          </label>
          <label className="block">
            <span className="text-[0.78rem] text-muted">Target sessions / week</span>
            <input
              type="number"
              min={0}
              max={14}
              value={Number(form.target_sessions_per_week ?? 3)}
              onChange={(event) =>
                setForm((current) => ({ ...current, target_sessions_per_week: Number(event.target.value) }))
              }
              className="mt-1 min-h-11 w-full rounded-[var(--radius-control)] border border-subtle bg-surface px-3 text-sm"
            />
          </label>
          {select("sex", "Sex", options?.sexes)}
        </div>
      </Card>

      <Card className="space-y-3 p-4">
        <p className="eyebrow text-muted">Weekly set targets</p>
        <p className="text-[0.68rem] text-muted">
          Optional planning targets. Seven-day exposure compares against these; they are not universal optimal-volume
          claims.
        </p>
        <div className="grid grid-cols-2 gap-3">
          {(options?.muscle_groups ?? []).map((group) => (
            <label key={group} className="flex items-center justify-between gap-2 text-[0.78rem]">
              <span>{group}</span>
              <input
                type="number"
                min={0}
                max={40}
                step={1}
                value={targets[group] ?? 0}
                onChange={(event) => setTargets((current) => ({ ...current, [group]: Number(event.target.value) || 0 }))}
                className="min-h-9 w-20 rounded-[var(--radius-control)] border border-subtle bg-surface px-2 text-right text-[0.78rem]"
              />
            </label>
          ))}
        </div>
      </Card>

      <Button size="lg" variant="primary" className="w-full" disabled={busy} onClick={() => void save()}>
        {busy ? "Saving…" : "Save profile"}
      </Button>

      <Card className="p-4">
        <p className="eyebrow text-muted">Personal baseline</p>
        <dl className="mt-2 divide-y divide-subtle text-sm">
          <div className="flex justify-between py-2">
            <dt className="text-muted">Valid paired observations</dt>
            <dd>{String(baseline.valid_days ?? "—")}</dd>
          </div>
          <div className="flex justify-between py-2">
            <dt className="text-muted">Baseline window</dt>
            <dd>{String(baseline.window_days ?? "—")} days</dd>
          </div>
          <div className="flex justify-between py-2">
            <dt className="text-muted">Baseline confidence</dt>
            <dd>{String(baseline.confidence ?? "—")}</dd>
          </div>
          <div className="flex justify-between py-2">
            <dt className="text-muted">LnRMSSD mean</dt>
            <dd className="tabular-nums">{(baseline.lnrmssd_mean as number) ? formatNumber(baseline.lnrmssd_mean as number, 2) : "—"}</dd>
          </div>
        </dl>
        <p className="mt-2 text-[0.68rem] leading-relaxed text-muted">
          Readiness compares today against these personal observations rather than population cut-offs. Baseline
          confidence describes data sufficiency, not model certainty.
        </p>
      </Card>

      {profile.is_demo ? <ScenarioSwitcher /> : null}
      {scenario ? <p className="text-[0.68rem] text-muted">Active demo scenario: {scenario}</p> : null}

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

      <Link
        href="/profile/data"
        className={cn(buttonVariants({ variant: "secondary" }), "w-full")}
      >
        Data, privacy, import / export and about
      </Link>

      <p className="flex items-start gap-2 text-[0.68rem] leading-relaxed text-muted">
        <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
        An educational decision-support prototype. Not a medical device, diagnosis, injury prediction or clinically
        validated training prescription.
      </p>
    </div>
  );
}
