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
} from "@/lib/calibration";
import { useUserState } from "@/lib/state-provider";
import type { ActiveSession, Calibration, DecisionTraceStep } from "@/types/api";
import { cn } from "@/lib/utils";

// Active session + one optional in-session checkpoint.

// This is deliberately NOT a workout tracker: it shows the guidance the product
// already gave, asks three short questions once, and can only hold, ease or
// optionally nudge within the range it already prescribed. The result is one
// strong verdict, one sentence and the updated guidance; the rule detail is one
// deliberate expand away.

function calibrationStyle(result?: string | null): { className: string; colorVar: string } {
  if (result === "EASE") return { className: "bg-[var(--status-amber-soft)]", colorVar: "var(--status-amber)" };
  if (result === "OPTIONAL PUSH") return { className: "bg-[var(--status-green-soft)]", colorVar: "var(--status-green)" };
  return { className: "bg-surface-secondary", colorVar: "var(--text-primary)" };
}

function Stat({ label, value }: { label: string; value: string | null }) {
  return (
    <div className="min-w-0">
      <p className="text-[0.68rem] font-medium tracking-[0.06em] text-muted uppercase">{label}</p>
      <p className="mt-1 truncate text-[0.9rem] font-medium">{value ?? "—"}</p>
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

  const tone = calibrationStyle(shown?.result);

  return (
    <div className="space-y-6">
      <section className="surface-raised px-5 py-5">
        <h2 className="title-hero">{active.primary_focus ?? "Session"}</h2>
        <dl className="mt-4 grid grid-cols-3 gap-x-4 gap-y-3">
          <Stat
            label="How hard"
            value={
              active.base_session_demand && active.session_demand && active.base_session_demand !== active.session_demand
                ? `${active.base_session_demand} → ${active.session_demand}`
                : active.session_demand
            }
          />
          <Stat label="Duration" value={active.duration} />
          <Stat label="Effort" value={active.planned_rir} />
        </dl>
      </section>

      <section className="surface px-5 py-5">
        <h3 className="title-section">How does it feel?</h3>
        <p className="label-quiet mt-1">Optional, once per session.</p>

        <div className="mt-5 space-y-4">
          <div>
            <p className="mb-2 text-[0.8rem] font-medium">Effort</p>
            <Segmented
              options={EFFORT_OPTIONS.map((option) => ({ value: option, label: option }))}
              value={effort}
              size="sm"
              label="Effort compared with expectation"
              onChange={setEffort}
            />
          </div>
          <div>
            <p className="mb-2 text-[0.8rem] font-medium">
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
              onChange={setRir}
            />
            <button
              type="button"
              aria-pressed={rir === null}
              onClick={() => setRir(null)}
              className={cn(
                "mt-2 min-h-9 rounded-full px-3 text-[0.74rem] transition-colors",
                rir === null ? "bg-surface-muted font-semibold text-foreground" : "text-muted",
              )}
            >
              Not sure
            </button>
          </div>
          <div>
            <p className="mb-2 text-[0.8rem] font-medium">Performance</p>
            <Segmented
              options={PERFORMANCE_OPTIONS.map((option) => ({ value: option, label: option }))}
              value={performance}
              size="sm"
              label="Performance feeling"
              onChange={setPerformance}
            />
          </div>
        </div>

        {error ? <p className="mt-3 text-[0.78rem] text-[var(--status-red)]">{error}</p> : null}

        <Button size="lg" variant="primary" className="mt-5 w-full" disabled={busy} onClick={() => void submit()}>
          {busy ? "Updating…" : result ? "Update Guidance" : "Check how it feels"}
        </Button>

        {shown ? (
          <div className={cn("mt-5 rounded-[var(--radius-card)] px-4 py-4", tone.className)}>
            <p className="text-[1.35rem] font-semibold tracking-tight" style={{ color: tone.colorVar }}>
              {calibrationLabel(shown.result)}
            </p>
            <p className="mt-2 text-[0.84rem] leading-relaxed">
              {shown.reason || CALIBRATION_HINTS[String(shown.result)]}
            </p>
            {shown.guidance ? (
              <p className="mt-2 text-[0.88rem] font-medium leading-relaxed">{shown.guidance}</p>
            ) : null}

            <details className="group mt-3">
              <summary className="flex min-h-9 cursor-pointer list-none items-center gap-1 text-[0.74rem] font-medium text-muted">
                Why →
                <span className="transition-transform group-open:rotate-90" aria-hidden>
                  ›
                </span>
              </summary>
              <p className="mt-1.5 text-[0.74rem] leading-relaxed text-muted">{shown.scope}</p>
              <p className="mt-1 text-[0.74rem] leading-relaxed text-muted">{shown.note}</p>
            </details>
          </div>
        ) : null}
      </section>

      <details className="divider group pt-5">
        <summary className="flex min-h-11 cursor-pointer list-none items-center justify-between gap-3 text-[0.88rem] font-medium">
          Session trace
          <span className="text-[0.74rem] text-muted">{sessionTrace.length} steps</span>
        </summary>
        <SessionTrace steps={sessionTrace} className="mt-4" />
      </details>

      <button
        type="button"
        disabled={busy}
        onClick={() => void cancelSession()}
        className="min-h-11 text-[0.76rem] text-muted underline decoration-dotted underline-offset-2 disabled:opacity-50"
      >
        Discard this session
      </button>
    </div>
  );
}
