"use client";

import Link from "next/link";
import { CircleCheck } from "lucide-react";
import { useEffect, useState } from "react";

import { PageHeader } from "@/components/page-header";
import { StatePanel } from "@/components/state-panel";
import { Button, buttonVariants } from "@/components/ui/button";
import { Section } from "@/components/ui/section";
import { Segmented } from "@/components/ui/segmented";
import { api } from "@/lib/api";
import { useUserState } from "@/lib/state-provider";
import type { DailyRow, ScenarioListResponse } from "@/types/api";
import { cn } from "@/lib/utils";

// Morning check-in: the same fields the product already collects, arranged for a
// fast daily interaction — compact numeric inputs and one-tap scales, with the
// direction of every scale stated in words.

interface ScaleField {
  key: "sleep_quality" | "fatigue" | "soreness" | "stress" | "motivation";
  label: string;
  low: string;
  high: string;
}

const SCALE_FIELDS: ScaleField[] = [
  { key: "sleep_quality", label: "Sleep quality", low: "Poor", high: "Excellent" },
  { key: "fatigue", label: "Fatigue", low: "Fresh", high: "Exhausted" },
  { key: "soreness", label: "Soreness", low: "None", high: "Severe" },
  { key: "stress", label: "Stress", low: "Calm", high: "High" },
  { key: "motivation", label: "Motivation", low: "Low", high: "High" },
];

const SCALE_OPTIONS = [1, 2, 3, 4, 5].map((value) => ({ value, label: String(value) }));

interface FormState {
  rmssd_ms: string;
  resting_hr_bpm: string;
  sleep_hours: string;
  sleep_quality: number;
  fatigue: number;
  soreness: number;
  stress: number;
  motivation: number;
  local_soreness: Record<string, number>;
  safety_flags: string[];
}

function blankForm(): FormState {
  return {
    rmssd_ms: "",
    resting_hr_bpm: "",
    sleep_hours: "",
    sleep_quality: 4,
    fatigue: 2,
    soreness: 2,
    stress: 2,
    motivation: 4,
    local_soreness: {},
    safety_flags: [],
  };
}

function fromDailyRow(row: DailyRow): FormState {
  return {
    ...blankForm(),
    rmssd_ms: row.rmssd_ms != null ? String(row.rmssd_ms) : "",
    resting_hr_bpm: row.resting_hr_bpm != null ? String(row.resting_hr_bpm) : "",
    sleep_hours: row.sleep_hours != null ? String(row.sleep_hours) : "",
    sleep_quality: row.sleep_quality ?? 4,
    fatigue: row.fatigue ?? 2,
    soreness: row.soreness ?? 2,
    stress: row.stress ?? 2,
    motivation: row.motivation ?? 4,
    local_soreness: row.local_soreness ?? {},
    safety_flags: row.safety_flags ?? [],
  };
}

function fromScenario(values: Record<string, unknown>): FormState {
  const number = (key: string, fallback: number) => (typeof values[key] === "number" ? (values[key] as number) : fallback);
  const text = (key: string) => (typeof values[key] === "number" ? String(values[key]) : "");
  return {
    rmssd_ms: text("rmssd_ms"),
    resting_hr_bpm: text("resting_hr_bpm"),
    sleep_hours: text("sleep_hours"),
    sleep_quality: number("sleep_quality", 4),
    fatigue: number("fatigue", 2),
    soreness: number("soreness", 2),
    stress: number("stress", 2),
    motivation: number("motivation", 4),
    local_soreness: {},
    safety_flags: [],
  };
}

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

function numberInRange(value: string, min: number, max: number): boolean {
  const parsed = Number(value);
  return value.trim() !== "" && Number.isFinite(parsed) && parsed >= min && parsed <= max;
}

export function CheckInView() {
  const { ready, state, today, submitCheckIn, busy, profileId } = useUserState();
  const [options, setOptions] = useState<ScenarioListResponse | null>(null);
  const [draft, setDraft] = useState<Partial<FormState>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [result, setResult] = useState<string | null>(null);
  const [failure, setFailure] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.scenarios().then((response) => {
      if (!cancelled && response.ok) setOptions(response.data);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  // Derived form: a stored check-in wins, otherwise the selected demo scenario
  // pre-fills the inputs. User edits live in `draft`, so nothing syncs by effect.
  const savedToday = state?.check_in && state.check_in.date === todayIso() ? state.check_in : null;
  const base = savedToday
    ? fromDailyRow(savedToday)
    : fromScenario(((options?.scenarios ?? []).find((item) => item.name === state?.scenario)?.values ?? {}) as Record<string, unknown>);
  const form: FormState = { ...base, ...draft };
  const setField = <K extends keyof FormState>(key: K, value: FormState[K]) =>
    setDraft((current) => ({ ...current, [key]: value }));

  if (!ready) {
    return <StatePanel title="Loading your check-in…" body="Reading this browser's stored data." />;
  }

  const safetyOptions = options?.safety_flags ?? [];
  const muscles = options?.muscle_groups ?? [];

  const validate = (): boolean => {
    const found: Record<string, string> = {};
    if (!numberInRange(form.rmssd_ms, 5, 250)) found.rmssd_ms = "5–250 ms";
    if (!numberInRange(form.resting_hr_bpm, 30, 120)) found.resting_hr_bpm = "30–120 bpm";
    if (!numberInRange(form.sleep_hours, 0, 14)) found.sleep_hours = "0–14 hours";
    setErrors(found);
    return Object.keys(found).length === 0;
  };

  const submit = async () => {
    setResult(null);
    setFailure(null);
    if (!validate()) return;
    const outcome = await submitCheckIn({
      rmssd_ms: Number(form.rmssd_ms),
      resting_hr_bpm: Number(form.resting_hr_bpm),
      sleep_hours: Number(form.sleep_hours),
      sleep_quality: form.sleep_quality,
      fatigue: form.fatigue,
      soreness: form.soreness,
      stress: form.stress,
      motivation: form.motivation,
      local_soreness: form.local_soreness,
      safety_flags: form.safety_flags,
    });
    if (outcome.ok) setResult(outcome.message ?? "Check-in saved.");
    else setFailure(outcome.error ?? "The check-in could not be saved.");
  };

  const numberField = (
    key: "rmssd_ms" | "resting_hr_bpm" | "sleep_hours",
    label: string,
    unit: string,
    step = "0.1",
  ) => (
    <label className="block">
      <span className="text-[0.75rem] text-muted">
        {label} <span className="opacity-70">{unit}</span>
      </span>
      <input
        type="number"
        inputMode="decimal"
        step={step}
        value={form[key]}
        onChange={(event) => setField(key, event.target.value)}
        aria-label={label}
        className={cn(
          "mt-1.5 min-h-12 w-full rounded-[var(--radius-control)] border bg-surface px-3 text-[0.95rem] font-medium tabular-nums",
          errors[key] ? "border-[var(--status-red-line)]" : "border-subtle",
        )}
      />
      {errors[key] ? <span className="mt-1 block text-[0.68rem] text-[var(--status-red)]">Use {errors[key]}.</span> : null}
    </label>
  );

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Check-in"
        title="Morning check-in"
        description="Six inputs, about a minute. Readiness recalculates from your own baseline."
      />

      {result ? (
        <StatePanel
          tone="info"
          title="Check-in saved"
          body={result}
          action={
            <Link href="/" className={cn(buttonVariants({ variant: "secondary", size: "sm" }))}>
              Back to Today
            </Link>
          }
        />
      ) : null}
      {failure ? <StatePanel tone="error" title="Not saved" body={failure} /> : null}
      {savedToday && !result ? (
        <p className="flex items-center gap-1.5 text-[0.72rem] text-muted">
          <CircleCheck className="h-3.5 w-3.5" aria-hidden />
          Today&apos;s check-in is already stored in this browser. Saving again replaces it.
        </p>
      ) : null}

      <Section eyebrow="Recovery" title="Overnight signals" divided={false}>
        <div className="grid grid-cols-2 gap-3">
          {numberField("rmssd_ms", "HRV (RMSSD)", "ms")}
          {numberField("resting_hr_bpm", "Resting HR", "bpm", "1")}
          <div className="col-span-2">{numberField("sleep_hours", "Sleep duration", "hours")}</div>
        </div>
      </Section>

      <Section eyebrow="Wellness" title="How you feel">
        <div className="space-y-3">
          {SCALE_FIELDS.map((field) => (
            <div key={field.key}>
              <div className="flex items-baseline justify-between gap-2">
                <span className="text-[0.8rem] font-medium">{field.label}</span>
                <span className="text-[0.68rem] text-muted">
                  1 {field.low} · 5 {field.high}
                </span>
              </div>
              <Segmented
                options={SCALE_OPTIONS}
                value={form[field.key]}
                size="sm"
                label={field.label}
                className="mt-1.5"
                onChange={(value) => setField(field.key, value)}
              />
            </div>
          ))}
        </div>
      </Section>

      <Section
        eyebrow="Context"
        title="Local soreness"
        description="Optional. 0 = none · 5 = severe. Soreness is one contextual signal, not a recovery measurement."
      >
        <div className="grid grid-cols-2 gap-x-4 gap-y-2">
          {muscles.map((muscle) => (
            <label key={muscle} className="flex min-h-11 items-center justify-between gap-2">
              <span className="min-w-0 truncate text-[0.8rem]">{muscle}</span>
              <span className="flex min-h-9 w-16 items-center rounded-[var(--radius-control)] border border-subtle bg-surface px-2">
                <select
                  aria-label={`${muscle} soreness`}
                  value={form.local_soreness[muscle] ?? 0}
                  onChange={(event) =>
                    setField("local_soreness", { ...form.local_soreness, [muscle]: Number(event.target.value) })
                  }
                  className="w-full bg-transparent text-[0.8rem] outline-none"
                >
                  {[0, 1, 2, 3, 4, 5].map((value) => (
                    <option key={value} value={value}>
                      {value}
                    </option>
                  ))}
                </select>
              </span>
            </label>
          ))}
        </div>
      </Section>

      <Section
        eyebrow="Safety"
        title="Safety check"
        description="Select anything that applies. A flag routes the product to STOP instead of a normal recommendation — conservative product routing, not a diagnosis."
      >
        <div className="space-y-1">
          {safetyOptions.map((flag) => (
            <label key={flag} className="flex min-h-11 items-center gap-3 text-[0.82rem]">
              <input
                type="checkbox"
                checked={form.safety_flags.includes(flag)}
                onChange={(event) =>
                  setField(
                    "safety_flags",
                    event.target.checked
                      ? [...form.safety_flags, flag]
                      : form.safety_flags.filter((item) => item !== flag),
                  )
                }
                className="h-4 w-4 shrink-0"
              />
              {flag}
            </label>
          ))}
        </div>
      </Section>

      {/* A full-width action bar rather than a floating card, so the form never
          looks like it is being covered by another box. */}
      <div className="sticky bottom-[calc(env(safe-area-inset-bottom)+4.5rem)] z-20 -mx-4 border-t border-subtle bg-background/95 px-4 py-2.5 backdrop-blur md:static md:mx-0 md:border-0 md:bg-transparent md:px-0 md:backdrop-blur-none">
        <Button size="lg" variant="primary" className="w-full" disabled={busy} onClick={() => void submit()}>
          {busy ? "Recalculating…" : "Save check-in"}
        </Button>
      </div>

      <p className="text-center text-[0.7rem] text-muted">
        {profileId} · stored in this browser only
        {today ? ` · current readiness ${today.readiness.status}` : ""}
      </p>
    </div>
  );
}
