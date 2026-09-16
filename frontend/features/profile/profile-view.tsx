"use client";

import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { useEffect, useState } from "react";

import { PageHeader } from "@/components/page-header";
import { ProfileSwitcher } from "@/components/profile-switcher";
import { ResponseDemoControl } from "@/components/response-demo-control";
import { ScenarioSwitcher } from "@/components/scenario-switcher";
import { StatePanel } from "@/components/state-panel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Section } from "@/components/ui/section";
import { api } from "@/lib/api";
import { formatNumber } from "@/lib/format";
import { useUserState } from "@/lib/state-provider";
import type { ProfileEdits, ProfileOptionsResponse } from "@/types/api";

function SelectField({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: string[] | undefined;
  onChange: (value: string) => void;
}) {
  return (
    <label className="block">
      <span className="text-[0.75rem] text-muted">{label}</span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        /* A fixed height rather than min-height: WebKit ignores min-height on a
           native select, which leaves Safari with a 23px control. */
        className="mt-1.5 h-11 w-full rounded-[var(--radius-control)] border border-subtle bg-surface px-3 text-sm md:h-10"
      >
        {(options ?? []).map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    </label>
  );
}

function NumberField({
  label,
  value,
  min,
  max,
  step = 1,
  suffix,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step?: number;
  suffix?: string;
  onChange: (value: number) => void;
}) {
  return (
    <label className="block">
      <span className="text-[0.75rem] text-muted">{label}</span>
      <span className="relative mt-1.5 block">
        <input
          type="number"
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={(event) => onChange(Number(event.target.value))}
          className="min-h-11 w-full rounded-[var(--radius-control)] border border-subtle bg-surface px-3 pr-14 text-sm tabular-nums outline-none"
        />
        {suffix ? (
          <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-[0.75rem] text-muted">
            {suffix}
          </span>
        ) : null}
      </span>
    </label>
  );
}

export function ProfileView() {
  const { ready, today, saveProfile, busy, scenario } = useUserState();
  const [options, setOptions] = useState<ProfileOptionsResponse | null>(null);
  const [draft, setDraft] = useState<ProfileEdits>({});
  const [targetDraft, setTargetDraft] = useState<Record<string, number>>({});
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.profileOptions().then((result) => {
      if (!cancelled && result.ok) setOptions(result.data);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  if (!ready || !today) {
    return <StatePanel title="Loading your profile…" body="Reading this browser's stored data." />;
  }

  const profile = today.profile;
  const baseline = (today.readiness.baseline ?? {}) as Record<string, unknown>;
  // Derived form: the stored profile is the base and `draft` holds only the edits,
  // so nothing has to be synchronised by an effect.
  const form: ProfileEdits = {
    name: profile.name,
    age: profile.age,
    sex: profile.sex,
    primary_activity: profile.primary_activity,
    training_goal: profile.training_goal,
    training_level: profile.training_level,
    training_split_preference: profile.training_split_preference,
    personal_sleep_need: profile.personal_sleep_need,
    target_sessions_per_week: profile.target_sessions_per_week,
    ...draft,
  };
  const targets: Record<string, number> = { ...(profile.weekly_set_targets ?? {}), ...targetDraft };
  const set = (key: keyof ProfileEdits, value: string | number) =>
    setDraft((current) => ({ ...current, [key]: value }));

  const save = async () => {
    setMessage(null);
    setError(null);
    const result = await saveProfile({ ...form, weekly_set_targets: targets });
    if (result.ok) setMessage(result.message ?? "Profile saved.");
    else setError(result.error ?? "The profile could not be saved.");
  };

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Profile"
        title={profile.name}
        description="Goal, programme and the context every recommendation is built from."
        actions={profile.is_demo ? <Badge variant="neutral">DEMO</Badge> : null}
      />

      {message ? <StatePanel tone="info" title="Saved" body={message} /> : null}
      {error ? <StatePanel tone="error" title="Not saved" body={error} /> : null}

      <Section eyebrow="Training" title="Goal and programme" divided={false}>
        <div className="grid gap-3 md:grid-cols-2">
          <label className="block md:col-span-2">
            <span className="text-[0.75rem] text-muted">Name</span>
            <input
              value={String(form.name ?? "")}
              onChange={(event) => set("name", event.target.value)}
              className="mt-1.5 min-h-11 w-full rounded-[var(--radius-control)] border border-subtle bg-surface px-3 text-sm"
            />
          </label>
          <SelectField
            label="Training goal"
            value={String(form.training_goal ?? "")}
            options={options?.goals}
            onChange={(value) => set("training_goal", value)}
          />
          <SelectField
            label="Preferred split"
            value={String(form.training_split_preference ?? "")}
            options={options?.splits}
            onChange={(value) => set("training_split_preference", value)}
          />
          <SelectField
            label="Training level"
            value={String(form.training_level ?? "")}
            options={options?.levels}
            onChange={(value) => set("training_level", value)}
          />
          <SelectField
            label="Primary activity"
            value={String(form.primary_activity ?? "")}
            options={options?.activities}
            onChange={(value) => set("primary_activity", value)}
          />
        </div>
      </Section>

      <Section eyebrow="Readiness" title="Baseline inputs">
        <div className="grid gap-3 md:grid-cols-2">
          <NumberField
            label="Personal sleep need"
            value={Number(form.personal_sleep_need ?? 8)}
            min={4}
            max={12}
            step={0.1}
            suffix="hours"
            onChange={(value) => set("personal_sleep_need", value)}
          />
          <NumberField
            label="Target sessions per week"
            value={Number(form.target_sessions_per_week ?? 3)}
            min={0}
            max={14}
            onChange={(value) => set("target_sessions_per_week", value)}
          />
          <NumberField
            label="Age"
            value={Number(form.age ?? 25)}
            min={16}
            max={100}
            onChange={(value) => set("age", value)}
          />
          <SelectField
            label="Sex"
            value={String(form.sex ?? "")}
            options={options?.sexes}
            onChange={(value) => set("sex", value)}
          />
        </div>

        <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-2 border-t border-subtle pt-3 text-[0.75rem] md:grid-cols-4">
          <div>
            <dt className="text-muted">Valid observations</dt>
            <dd className="font-medium tabular-nums">{String(baseline.valid_days ?? "—")}</dd>
          </div>
          <div>
            <dt className="text-muted">Baseline window</dt>
            <dd className="font-medium tabular-nums">{String(baseline.window_days ?? "—")} days</dd>
          </div>
          <div>
            <dt className="text-muted">Confidence</dt>
            <dd className="font-medium">{String(baseline.confidence ?? "—")}</dd>
          </div>
          <div>
            <dt className="text-muted">LnRMSSD mean</dt>
            <dd className="font-medium tabular-nums">
              {baseline.lnrmssd_mean ? formatNumber(baseline.lnrmssd_mean as number, 2) : "—"}
            </dd>
          </div>
        </dl>
        <p className="mt-2 text-[0.68rem] leading-relaxed text-muted">
          Readiness compares today against these personal observations instead of population cut-offs. Baseline
          confidence describes data sufficiency, not model certainty.
        </p>
      </Section>

      <Section
        eyebrow="Planning"
        title="Weekly set targets"
        description="Optional planning targets. Seven-day exposure compares against these; they are not universal optimal-volume claims."
      >
        <div className="grid grid-cols-2 gap-x-4 gap-y-3">
          {(options?.muscle_groups ?? []).map((group) => (
            <label key={group} className="flex items-center justify-between gap-2">
              <span className="text-[0.8rem]">{group}</span>
              <input
                type="number"
                min={0}
                max={40}
                aria-label={`${group} weekly target`}
                value={targets[group] ?? 0}
                onChange={(event) =>
                  setTargetDraft((current) => ({ ...current, [group]: Number(event.target.value) || 0 }))
                }
                className="min-h-11 w-20 rounded-[var(--radius-control)] border border-subtle bg-surface px-2 text-right text-[0.8rem] tabular-nums md:min-h-10"
              />
            </label>
          ))}
        </div>
      </Section>

      <Button size="lg" variant="primary" className="w-full" disabled={busy} onClick={() => void save()}>
        {busy ? "Saving…" : "Save profile"}
      </Button>

      {profile.is_demo ? (
        <Section eyebrow="Demo controls" title="Scenarios and profiles" description="Portfolio demo controls — not part of the daily workflow.">
          <div className="space-y-3">
            <ScenarioSwitcher />
            <ProfileSwitcher />
            <ResponseDemoControl />
          </div>
          {scenario ? <p className="mt-2 text-[0.68rem] text-muted">Active scenario: {scenario}</p> : null}
        </Section>
      ) : null}

      <Section eyebrow="Information" title="Science, data and about">
        <ul className="divide-y divide-subtle border-y border-subtle">
          {[
            { href: "/profile/science", label: "Science & Logic", hint: "Evidence boundaries, heuristics and 13 verified references" },
            { href: "/profile/data", label: "Data, privacy and backup", hint: "What is stored, where it goes, export and import" },
            { href: "/profile/about", label: "About this prototype", hint: "What the product is and what it does not claim" },
          ].map((item) => (
            <li key={item.href}>
              <Link href={item.href} className="flex min-h-14 items-center justify-between gap-3 py-2">
                <span className="min-w-0">
                  <span className="block text-[0.86rem] font-medium">{item.label}</span>
                  <span className="block text-[0.7rem] text-muted">{item.hint}</span>
                </span>
                <ArrowRight className="h-4 w-4 shrink-0 text-muted" aria-hidden />
              </Link>
            </li>
          ))}
        </ul>
      </Section>
    </div>
  );
}
