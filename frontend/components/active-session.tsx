"use client";

import { useState } from "react";

import { SessionTrace } from "@/components/session-trace";
import { Button } from "@/components/ui/button";
import { Segmented } from "@/components/ui/segmented";
import { EFFORT_OPTIONS, PERFORMANCE_OPTIONS, RIR_OPTIONS, calibrationLabel, calibrationTone } from "@/lib/calibration";
import { useUserState } from "@/lib/state-provider";
import type { ActiveSession, Calibration, DecisionTraceStep } from "@/types/api";
import { cn } from "@/lib/utils";

// Active session + one optional in-session checkpoint.
//
// This is deliberately NOT a workout tracker: it shows the guidance the product
// already gave, asks three short questions once, and can only ever hold, ease or
// optionally nudge within the range it already prescribed. It asks nothing about
// sleep, HRV, stress or motivation — those belong to the morning check-in.

function Stat({ label, value }: { label: string; value: string | null }) {
  return (
    <div className="min-w-0">
      <p className="text-[0.66rem] uppercase tracking-[0.08em] text-muted">{label}</p>
      <p className="mt-0.5 truncate text-[0.82rem] font-medium">{value ?? "—"}</p>
    </div>
  );
}

export function ActiveSessionPanel({
  active,
  sessionTrace,
}: {
  active: ActiveSession;
  sessionTrace: DecisionTraceStep[];
}) {
  const { submitCalibration, cancelSession, busy } = useUserState();
  const [effort, setEffort] = useState<string>("As expected");
  const [performance, setPerformance] = useState<string>("As expected");
  const [rir, setRir] = useState<number | null>(2);
  const [result, setResult] = useState<Calibration | null>(null);
  const [error, setError] = useState<string | null>(null);

  // A checkpoint recorded earlier (for example before a reload) is shown in the
  // same shape as a fresh one, so the guidance never disappears on the user.
  const stored = active.calibration ?? null;
  const shown = result ?? (stored
    ? {
        result: (stored.result ?? "HOLD") as Calibration["result"],
        reason: stored.reason ?? "Recorded during this session.",
        guidance: stored.guidance ?? "",
        scope: "Within the effort range already prescribed — no tier, focus, exercise or volume change",
        note: "Stored with this session. It does not change the session demand, focus, exercises or volume.",
      }
    : null);

  const submit = async () => {
    setError(null);
    const outcome = await submitCalibration({ effort, performance, actual_rir: rir });
    if (outcome.ok && outcome.calibration) setResult(outcome.calibration);
    else setError(outcome.error ?? "The checkpoint could not be saved.");
  };

  return (
    <div className="space-y-4">
      <div className="rounded-[var(--radius-card)] border border-subtle bg-surface-muted p-4">
        <p className="eyebrow">Session in progress</p>
        <dl className="mt-2 grid grid-cols-2 gap-x-4 gap-y-3">
          <Stat label="Session" value={active.primary_focus} />
          <Stat
            label="How hard"
            value={
              active.base_session_demand && active.session_demand && active.base_session_demand !== active.session_demand
                ? `${active.base_session_demand} → ${active.session_demand}`
                : active.session_demand
            }
          />
          <Stat label="Effort guidance" value={active.planned_rir} />
          <Stat label="Duration" value={active.duration} />
        </dl>
        {active.adjustment ? (
          <p className="mt-3 text-[0.72rem] text-muted">
            Today&apos;s demand already reflects your recent response. Completing the session does not change what you
            train — only how hard.
          </p>
        ) : null}
      </div>

      <div className="rounded-[var(--radius-card)] border border-subtle p-4">
        <p className="text-[0.84rem] font-semibold">In-session checkpoint</p>
        <p className="mt-0.5 text-[0.72rem] leading-relaxed text-muted">
          Optional, once. It compares the session so far with the guidance you started with. It never changes the
          session demand, the focus, the exercises or the volume.
        </p>

        <div className="mt-3 space-y-3">
          <div>
            <p className="text-[0.78rem] font-medium">Effort compared with expectation</p>
            <Segmented
              options={EFFORT_OPTIONS.map((option) => ({ value: option, label: option }))}
              value={effort}
              size="sm"
              label="Effort compared with expectation"
              className="mt-1.5"
              onChange={setEffort}
            />
          </div>
          <div>
            <p className="text-[0.78rem] font-medium">
              Actual RIR on a representative set
              <span className="ml-2 font-normal text-muted">
                {active.planned_rir ? `prescribed ${active.planned_rir}` : "0 = to failure"}
              </span>
            </p>
            <Segmented
              options={RIR_OPTIONS.map((option) => ({ value: option, label: String(option) }))}
              value={rir ?? RIR_OPTIONS[0]}
              size="sm"
              label="Actual reps in reserve"
              className="mt-1.5"
              onChange={setRir}
            />
            <button
              type="button"
              aria-pressed={rir === null}
              onClick={() => setRir(null)}
              className={cn(
                "mt-1.5 min-h-11 rounded-full border px-3 text-[0.72rem] transition-colors md:min-h-9",
                rir === null ? "border-foreground bg-surface-muted font-semibold" : "border-subtle text-muted",
              )}
            >
              Not sure
            </button>
          </div>
          <div>
            <p className="text-[0.78rem] font-medium">Performance feeling</p>
            <Segmented
              options={PERFORMANCE_OPTIONS.map((option) => ({ value: option, label: option }))}
              value={performance}
              size="sm"
              label="Performance feeling"
              className="mt-1.5"
              onChange={setPerformance}
            />
          </div>
        </div>

        {error ? <p className="mt-3 text-[0.75rem] text-[var(--status-red)]">{error}</p> : null}

        <Button size="md" variant="secondary" className="mt-3 w-full" disabled={busy} onClick={() => void submit()}>
          {busy ? "Checking…" : result ? "Update the checkpoint" : "Check the plan"}
        </Button>

        {shown ? (
          <div className="mt-4 space-y-2 border-t border-subtle pt-3">
            <div className="flex items-center gap-2">
              <span className={cn("rounded-full px-2 py-0.5 text-[0.62rem] font-semibold", calibrationTone(shown.result))}>
                {calibrationLabel(shown.result)}
              </span>
              <span className="text-[0.68rem] text-muted">{shown.scope}</span>
            </div>
            <p className="text-[0.8rem] leading-relaxed">{shown.reason}</p>
            <p className="text-[0.82rem] font-medium leading-relaxed">{shown.guidance}</p>
            <p className="text-[0.68rem] leading-relaxed text-muted">{shown.note}</p>
          </div>
        ) : null}
      </div>

      <div>
        <p className="eyebrow">Session trace</p>
        <SessionTrace steps={sessionTrace} className="mt-2" />
      </div>

      <button
        type="button"
        disabled={busy}
        onClick={() => void cancelSession()}
        className="min-h-11 text-[0.74rem] text-muted underline decoration-dotted underline-offset-2 disabled:opacity-50 md:min-h-9"
      >
        Discard this session
      </button>
    </div>
  );
}
