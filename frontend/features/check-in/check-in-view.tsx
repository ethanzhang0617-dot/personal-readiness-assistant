"use client";

import Link from "next/link";
import { CircleCheck } from "lucide-react";
import { useEffect, useState } from "react";

import { PageHeader } from "@/components/page-header";
import { StatePanel } from "@/components/state-panel";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { api } from "@/lib/api";
import { useUserState } from "@/lib/state-provider";
import type { DailyRow, ScenarioListResponse } from "@/types/api";
import { cn } from "@/lib/utils";

// Morning check-in: only the fields the product already collects, with the same
// direction hints the reference app shows. The engines recalculate on submit;
// nothing scientific is computed in the browser.

interface ScaleField {
  key: "sleep_quality" | "fatigue" | "soreness" | "stress" | "motivation";
  label: string;
  hint: string;
}

const SCALE_FIELDS: ScaleField[] = [
  { key: "sleep_quality", label: "Sleep quality", hint: "1 = very poor · 5 = excellent (higher is better)" },
  { key: "fatigue", label: "Fatigue", hint: "1 = fresh · 5 = exhausted (higher is more fatigue)" },
  { key: "soreness", label: "Global soreness", hint: "1 = none · 5 = severe (higher is more soreness)" },
  { key: "stress", label: "Stress", hint: "1 = calm · 5 = very stressed (higher is more stress)" },
  { key: "motivation", label: "Motivation", hint: "1 = very low · 5 = very high (higher is better)" },
];

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
  // pre-fills the inputs. User edits live in `draft`, so no effect has to sync.
  const savedToday = state?.check_in && state.check_in.date === todayIso() ? state.check_in : null;
  const base = savedToday
    ? fromDailyRow(savedToday)
    : fromScenario(((options?.scenarios ?? []).find((item) => item.name === state?.scenario)?.values ?? {}) as Record<string, unknown>);
  const form: FormState = { ...base, ...draft };
  const setField = <K extends keyof FormState>(key: K, value: FormState[K]) =>
    setDraft((current) => ({ ...current, [key]: value }));

  if (!ready) {
    return <StatePanel title="Loading your check-in…" body="Reading local data from this browser." />;
  }

  const safetyOptions = options?.safety_flags ?? [];
  const muscles = options?.muscle_groups ?? [];

  const validate = (): boolean => {
    const found: Record<string, string> = {};
    if (!numberInRange(form.rmssd_ms, 5, 250)) found.rmssd_ms = "Enter HRV between 5 and 250 ms.";
    if (!numberInRange(form.resting_hr_bpm, 30, 120)) found.resting_hr_bpm = "Enter resting HR between 30 and 120 bpm.";
    if (!numberInRange(form.sleep_hours, 0, 14)) found.sleep_hours = "Enter sleep between 0 and 14 hours.";
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
      <span className="text-[0.8rem] font-medium">
        {label} <span className="text-muted">({unit})</span>
      </span>
      <input
        type="number"
        inputMode="decimal"
        step={step}
        value={form[key]}
        onChange={(event) => setField(key, event.target.value)}
        className="mt-1.5 min-h-11 w-full rounded-[var(--radius-control)] border border-subtle bg-surface px-3 text-sm"
      />
      {errors[key] ? <span className="mt-1 block text-[0.7rem] text-[var(--status-red)]">{errors[key]}</span> : null}
    </label>
  );

  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow="Check-in"
        title="Morning check-in"
        description="The signals this product already uses. Readiness is recalculated from your own baseline."
      />

      {result ? (
        <StatePanel
          tone="info"
          title="Saved"
          body={result}
          action={
            <Link href="/" className={cn(buttonVariants({ variant: "secondary", size: "sm" }))}>
              Back to Today
            </Link>
          }
        />
      ) : null}
      {failure ? <StatePanel tone="error" title="Not saved" body={failure} /> : null}
      {savedToday ? (
        <p className="flex items-center gap-1.5 text-[0.7rem] text-muted">
          <CircleCheck className="h-3.5 w-3.5" aria-hidden />
          A check-in for today is already stored in this browser. Submitting again replaces it.
        </p>
      ) : null}

      <Card className="space-y-3 p-4">
        <p className="eyebrow text-muted">Recovery</p>
        {numberField("rmssd_ms", "HRV (RMSSD)", "ms")}
        {numberField("resting_hr_bpm", "Resting heart rate", "bpm", "1")}
        {numberField("sleep_hours", "Sleep duration", "hours")}
      </Card>

      <Card className="space-y-4 p-4">
        <p className="eyebrow text-muted">How you feel</p>
        {SCALE_FIELDS.map((field) => (
          <div key={field.key}>
            <div className="flex items-baseline justify-between gap-2">
              <span className="text-[0.8rem] font-medium">{field.label}</span>
              <span className="text-[0.8rem] font-semibold tabular-nums">{form[field.key]}</span>
            </div>
            <input
              type="range"
              min={1}
              max={5}
              step={1}
              value={form[field.key]}
              aria-label={field.label}
              onChange={(event) => setField(field.key, Number(event.target.value))}
              className="mt-2 h-11 w-full"
            />
            <p className="text-[0.68rem] text-muted">{field.hint}</p>
          </div>
        ))}
      </Card>

      <Card className="space-y-2 p-4">
        <p className="eyebrow text-muted">Local soreness (optional)</p>
        <p className="text-[0.68rem] text-muted">
          0 = none · 5 = severe. Soreness is one contextual signal, not a recovery measurement.
        </p>
        <div className="mt-1 grid grid-cols-2 gap-2">
          {muscles.map((muscle) => (
            <label key={muscle} className="flex items-center justify-between gap-2 text-[0.78rem]">
              <span>{muscle}</span>
              <select
                aria-label={`${muscle} soreness`}
                value={form.local_soreness[muscle] ?? 0}
                onChange={(event) =>
                  setField("local_soreness", { ...form.local_soreness, [muscle]: Number(event.target.value) })
                }
                className="min-h-9 rounded-[var(--radius-control)] border border-subtle bg-surface px-2 text-[0.78rem]"
              >
                {[0, 1, 2, 3, 4, 5].map((value) => (
                  <option key={value} value={value}>
                    {value}
                  </option>
                ))}
              </select>
            </label>
          ))}
        </div>
      </Card>

      <Card className="space-y-2 p-4">
        <p className="eyebrow text-muted">Safety check</p>
        <p className="text-[0.68rem] text-muted">
          Select anything that applies. A safety flag routes the product to STOP instead of a normal recommendation; it
          is conservative product routing, not a medical diagnosis.
        </p>
        {safetyOptions.map((flag) => (
          <label key={flag} className="flex min-h-9 items-center gap-2 text-[0.78rem]">
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
              className="h-4 w-4"
            />
            {flag}
          </label>
        ))}
      </Card>

      <Button size="lg" variant="primary" className="w-full" disabled={busy} onClick={() => void submit()}>
        {busy ? "Recalculating…" : "Save check-in"}
      </Button>

      <p className="text-center text-[0.68rem] text-muted">
        Profile {profileId} · stored in this browser only
        {today ? ` · current readiness ${today.readiness.status}` : ""}
      </p>
    </div>
  );
}
