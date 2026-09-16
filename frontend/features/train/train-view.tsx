"use client";

import Link from "next/link";
import { Info } from "lucide-react";
import { useMemo, useState } from "react";

import { DecisionTrace } from "@/components/decision-trace";
import { PageHeader } from "@/components/page-header";
import { StatePanel } from "@/components/state-panel";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { formatNumber, formatShortDate } from "@/lib/format";
import { useUserState } from "@/lib/state-provider";
import { cn } from "@/lib/utils";
import type { SessionLogDefaults, TrainingAlternative, WorkoutTemplate } from "@/types/api";

interface SessionOption {
  prescription_id: string | null;
  name: string;
  intensity: string | null;
  duration: string | null;
  rir: string | null;
  template: WorkoutTemplate | null;
  log_defaults: SessionLogDefaults | null;
  isPrimary: boolean;
  muscle_groups: string[];
  training_type: string | null;
}

export function TrainView() {
  const { ready, today, error, logSession, busy } = useUserState();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [duration, setDuration] = useState<string>("");
  const [rpe, setRpe] = useState<number>(6);
  const [completion, setCompletion] = useState<"Completed" | "Partial">("Completed");
  const [notes, setNotes] = useState("");
  const [actualSets, setActualSets] = useState<Record<string, number>>({});
  const [outcome, setOutcome] = useState<string | null>(null);
  const [failure, setFailure] = useState<string | null>(null);

  const options = useMemo<SessionOption[]>(() => {
    if (!today) return [];
    const recommendation = today.training.recommendation;
    const primary: SessionOption = {
      prescription_id: recommendation.prescription_id,
      name: recommendation.primary_name,
      intensity: recommendation.session_demand,
      duration: recommendation.duration,
      rir: recommendation.rir_guidance,
      template: recommendation.template as WorkoutTemplate,
      log_defaults: recommendation.log_defaults,
      isPrimary: true,
      muscle_groups: recommendation.muscle_groups,
      training_type: recommendation.training_type,
    };
    const alternatives: SessionOption[] = recommendation.alternatives.map((item: TrainingAlternative) => ({
      prescription_id: item.prescription_id,
      name: item.name,
      intensity: item.intensity,
      duration: item.duration,
      rir: null,
      template: item.template,
      log_defaults: item.log_defaults,
      isPrimary: false,
      muscle_groups: item.muscle_groups,
      training_type: item.training_type,
    }));
    return [primary, ...alternatives];
  }, [today]);

  const selected = useMemo(() => {
    const wanted = selectedId ?? options[0]?.prescription_id ?? null;
    return options.find((option) => option.prescription_id === wanted) ?? options[0] ?? null;
  }, [options, selectedId]);

  const range = today?.training.recommendation.estimated_duration_min_range ?? null;
  const defaultDuration = range && range.length > 1 ? Math.round((range[0] + range[1]) / 2) : 50;

  if (!ready) {
    return <StatePanel title="Loading today's session…" body="Reading local data and recalculating from the engines." />;
  }
  if (!today) {
    return <StatePanel tone="error" title="Training plan unavailable" body={error ?? "No training plan was returned."} />;
  }

  const recommendation = today.training.recommendation;
  const exposure = today.training.exposure;
  const history = today.training.history;
  const isStop = today.readiness.safety_active;

  const submitLog = async () => {
    setOutcome(null);
    setFailure(null);
    const durationValue = Number(duration || defaultDuration);
    if (!Number.isFinite(durationValue) || durationValue <= 0) {
      setFailure("Enter a completed duration greater than zero.");
      return;
    }
    const exercises = (selected?.log_defaults?.exercises ?? []).map((exercise) => ({
      name: exercise.name,
      working_sets: actualSets[exercise.name] ?? exercise.prescribed_sets,
      prescribed_sets: exercise.prescribed_sets,
    }));
    const result = await logSession({
      prescription_id: selected?.prescription_id ?? null,
      duration_min: durationValue,
      session_rpe: rpe,
      completion_status: completion,
      notes,
      exercises: exercises.length > 0 ? exercises : null,
    });
    if (result.ok) {
      setOutcome(result.message ?? "Session logged.");
      setNotes("");
      setActualSets({});
    } else {
      setFailure(result.error ?? "The session could not be logged.");
    }
  };

  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow="Train"
        title={recommendation.primary_name}
        description={`${recommendation.session_demand} · ${recommendation.duration} · ${recommendation.rir_guidance ?? "effort guidance unavailable"}`}
      />

      {isStop ? (
        <StatePanel
          tone="error"
          title="Safety routing is active"
          body="Normal workout guidance is disabled while a safety flag is selected. Logging a normal session is disabled too."
        />
      ) : null}

      {options.length > 1 ? (
        <div className="flex flex-wrap gap-2">
          {options.map((option) => (
            <button
              key={option.prescription_id ?? option.name}
              type="button"
              onClick={() => {
                setSelectedId(option.prescription_id);
                setActualSets({});
              }}
              className={cn(
                "min-h-9 rounded-full border px-3 text-[0.75rem] font-medium transition-colors",
                option.prescription_id === selected?.prescription_id
                  ? "border-transparent bg-primary text-primary-foreground"
                  : "border-subtle bg-surface text-muted",
              )}
            >
              {option.name}
              {option.isPrimary ? " · primary" : ""}
            </button>
          ))}
        </div>
      ) : null}

      <Card className="p-4">
        <p className="eyebrow text-muted">
          {selected?.isPrimary ? "Primary recommendation" : "Rule-generated alternative"}
        </p>
        <p className="mt-1 text-sm text-muted">
          {[selected?.template?.title, selected?.intensity, selected?.duration].filter(Boolean).join(" · ")}
        </p>
        <ul className="mt-3 divide-y divide-subtle">
          {(selected?.template?.items ?? []).map((item) => (
            <li key={item} className="py-2 text-sm">
              {item}
            </li>
          ))}
        </ul>
        {selected?.template?.note ? (
          <p className="mt-2 text-[0.68rem] text-muted">{selected.template.note}</p>
        ) : null}
        {recommendation.alternatives.length > 0 ? (
          <p className="mt-3 border-t border-subtle pt-2 text-[0.68rem] text-muted">
            Selecting an alternative never replaces the primary recommendation.
          </p>
        ) : null}
      </Card>

      <Card className="p-4">
        <p className="eyebrow text-muted">Weekly exposure</p>
        <ul className="mt-3 space-y-2.5">
          {exposure.groups.map((group) => {
            const target = group.target ?? 0;
            const ratio = target > 0 ? Math.min(group.value / target, 1) : 0;
            return (
              <li key={group.group}>
                <div className="flex items-baseline justify-between gap-3 text-sm">
                  <span>{group.group}</span>
                  <span className="tabular-nums text-muted">
                    {formatNumber(group.value)} / {target > 0 ? formatNumber(target) : "—"}
                  </span>
                </div>
                <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-muted-soft">
                  <div className="h-full rounded-full bg-primary" style={{ width: `${Math.round(ratio * 100)}%` }} />
                </div>
              </li>
            );
          })}
        </ul>
        <p className="mt-3 text-[0.68rem] leading-relaxed text-muted">{exposure.note}</p>
        <p className="mt-1 text-[0.68rem] text-muted">Target source: {exposure.target_source ?? "not recorded"}</p>
      </Card>

      <Card className="p-4">
        <p className="eyebrow text-muted">Recent sessions</p>
        {history.length > 0 ? (
          <ul className="mt-3 divide-y divide-subtle">
            {history.map((session) => (
              <li key={`${session.date}-${session.focus}`} className="flex items-baseline justify-between gap-3 py-2">
                <span className="text-sm font-medium">{session.focus ?? session.training_type ?? "Session"}</span>
                <span className="text-right text-[0.75rem] text-muted">
                  {formatShortDate(session.date)}
                  {session.session_rpe !== null ? ` · RPE ${formatNumber(session.session_rpe)}` : ""}
                  {session.duration_min !== null ? ` · ${formatNumber(session.duration_min)} min` : ""}
                  {session.working_sets !== null ? ` · ${formatNumber(session.working_sets)} sets` : ""}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-3 text-sm text-muted">No completed sessions are recorded yet.</p>
        )}
      </Card>

      <DecisionTrace steps={today.training.decision_trace} rationale={recommendation.rationale} />

      <Card className="space-y-3 p-4">
        <p className="eyebrow text-muted">Log completed workout</p>
        <p className="text-[0.68rem] text-muted">
          Seven-day exposure uses the actual completed sets, not the planned prescription. A logged session immediately
          updates exposure, training load and the next recommendation.
        </p>
        {outcome ? <p className="text-[0.78rem] text-[var(--status-green)]">{outcome}</p> : null}
        {failure ? <p className="text-[0.78rem] text-[var(--status-red)]">{failure}</p> : null}

        <div className="grid grid-cols-2 gap-3">
          <label className="block">
            <span className="text-[0.8rem] font-medium">
              Duration <span className="text-muted">(min)</span>
            </span>
            <input
              type="number"
              inputMode="numeric"
              min={1}
              step={5}
              value={duration || String(defaultDuration)}
              onChange={(event) => setDuration(event.target.value)}
              className="mt-1.5 min-h-11 w-full rounded-[var(--radius-control)] border border-subtle bg-surface px-3 text-sm"
            />
          </label>
          <label className="block">
            <span className="text-[0.8rem] font-medium">Session RPE (1–10)</span>
            <input
              type="number"
              inputMode="numeric"
              min={1}
              max={10}
              value={rpe}
              onChange={(event) => setRpe(Math.min(10, Math.max(1, Number(event.target.value) || 1)))}
              className="mt-1.5 min-h-11 w-full rounded-[var(--radius-control)] border border-subtle bg-surface px-3 text-sm"
            />
          </label>
        </div>

        {(selected?.log_defaults?.exercises ?? []).length > 0 ? (
          <div className="space-y-2">
            <p className="text-[0.8rem] font-medium">Actual completed sets</p>
            {(selected?.log_defaults?.exercises ?? []).map((exercise) => (
              <label key={exercise.name} className="flex items-center justify-between gap-3 text-[0.78rem]">
                <span>{exercise.name}</span>
                <input
                  type="number"
                  min={0}
                  max={20}
                  aria-label={`${exercise.name} actual sets`}
                  value={actualSets[exercise.name] ?? exercise.prescribed_sets}
                  onChange={(event) =>
                    setActualSets((current) => ({ ...current, [exercise.name]: Number(event.target.value) || 0 }))
                  }
                  className="min-h-9 w-20 rounded-[var(--radius-control)] border border-subtle bg-surface px-2 text-right text-[0.78rem]"
                />
              </label>
            ))}
          </div>
        ) : null}

        <div className="grid grid-cols-2 gap-3">
          <label className="block">
            <span className="text-[0.8rem] font-medium">Completion</span>
            <select
              value={completion}
              onChange={(event) => setCompletion(event.target.value as "Completed" | "Partial")}
              className="mt-1.5 min-h-11 w-full rounded-[var(--radius-control)] border border-subtle bg-surface px-3 text-sm"
            >
              <option value="Completed">Completed</option>
              <option value="Partial">Partial</option>
            </select>
          </label>
          <label className="block">
            <span className="text-[0.8rem] font-medium">
              Notes <span className="text-muted">(optional)</span>
            </span>
            <input
              type="text"
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
              className="mt-1.5 min-h-11 w-full rounded-[var(--radius-control)] border border-subtle bg-surface px-3 text-sm"
            />
          </label>
        </div>

        <Button size="lg" variant="primary" className="w-full" disabled={busy || isStop} onClick={() => void submitLog()}>
          {busy ? "Saving…" : "Log completed workout"}
        </Button>
      </Card>

      <p className="flex items-start gap-2 text-[0.68rem] leading-relaxed text-muted">
        <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
        Need to change today&apos;s inputs? Use the morning check-in — it replaces the simulated scenario for today.
      </p>
      <Link href="/check-in" className={cn(buttonVariants({ variant: "secondary" }), "w-full")}>
        Go to morning check-in
      </Link>
    </div>
  );
}
