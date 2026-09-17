"use client";

import { useState } from "react";

import { SessionTrace } from "@/components/session-trace";
import { Button } from "@/components/ui/button";
import { Segmented } from "@/components/ui/segmented";
import {
  CALIBRATION_HINTS,
  EFFORT_OPTIONS,
  PERFORMANCE_OPTIONS,
  RIR_OPTIONS,
  calibrationLabel,
  calibrationTone,
} from "@/lib/calibration";
import { useUserState } from "@/lib/state-provider";
import type { ActiveSession, Calibration, DecisionTraceStep } from "@/types/api";
import { cn } from "@/lib/utils";

// Active session + one optional in-session checkpoint.
//
// This is deliberately NOT a workout tracker: it shows the guidance the product
// already gave, asks three short questions once, and can only ever hold, ease or
// optionally nudge within the range it already prescribed. The result is three
// lines — verdict, one reason, updated guidance — and the rule detail is one
// deliberate expand away.

function Stat({ label, value }: { label: string; value: string | null }) {
  return (
    <div className="min-w-0">
      <p className="label-quiet">{label}</p>
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
        reason: stored.reason ?? CALIBRATION_HINTS[String(stored.result ?? "HOLD")],
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
      <div className="surface-raised px-5 py-5">
        <p className="label-quiet">Session in progress</p>
        <h2 className="mt-1 text-[1.35rem] font-semibold tracking-tight">{active.primary_focus ?? "Session"}</h2>
        <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-3">
          <Stat
            label="How hard"
            value={
              active.base_session_demand && active.session_demand && active.base_session_demand !== active.session_demand
                ? `${active.base_session_demand} → ${active.session_demand}`
                : active.session_demand
            }
          />
          <Stat label="Duration" value={active.duration} />
          <Stat label="Effort guidance" value={active.planned_rir} />
          <Stat label="Current guidance" value={shown?.guidance ? "Updated" : "As prescribed"} />
        </dl>
      </div>

      <div className="surface px-5 py-5">
        <h3 className="text-[0.95rem] font-semibold">How does it feel?</h3>
        <p className="label-quiet mt-0.5">Optional, once per session.</p>

        <div className="mt-4 space-y-3.5">
          <div>
            <p className="text-[0.8rem] font-medium">Effort</p>
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
            <p className="text-[0.8rem] font-medium">
              RIR
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
            <p className="text-[0.8rem] font-medium">Performance</p>
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

        <Button size="lg" variant="primary" className="mt-4 w-full" disabled={busy} onClick={() => void submit()}>
          {busy ? "Updating…" : result ? "Update guidance" : "Check how it feels"}
        </Button>

        {shown ? (
          <div className="divider mt-4 space-y-2 pt-4">
            <div className="flex items-center gap-2">
              <span className={cn("rounded-full px-2.5 py-1 text-[0.7rem] font-semibold", calibrationTone(shown.result))}>
                {calibrationLabel(shown.result)}
              </span>
            </div>
            <p className="text-[0.82rem] leading-relaxed">
              {shown.reason || CALIBRATION_HINTS[String(shown.result)]}
            </p>
            {shown.guidance ? (
              <p className="text-[0.86rem] font-medium leading-relaxed">{shown.guidance}</p>
            ) : null}

            <details className="group pt-1">
              <summary className="flex min-h-10 cursor-pointer list-none items-center gap-1 text-[0.74rem] font-medium text-muted">
                Why →
                <span className="transition-transform group-open:rotate-90" aria-hidden>
                  ›
                </span>
              </summary>
              <p className="mt-1.5 text-[0.72rem] leading-relaxed text-muted">{shown.scope}</p>
              <p className="mt-1 text-[0.72rem] leading-relaxed text-muted">{shown.note}</p>
            </details>
          </div>
        ) : null}
      </div>

      <details className="divider group pt-4">
        <summary className="flex min-h-11 cursor-pointer list-none items-center justify-between gap-3 text-[0.86rem] font-medium">
          Session trace
          <span className="text-[0.72rem] text-muted">{sessionTrace.length} steps</span>
        </summary>
        <SessionTrace steps={sessionTrace} className="mt-3" />
      </details>

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
