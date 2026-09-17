"use client";

import Link from "next/link";
import { Info } from "lucide-react";
import { useMemo, useState } from "react";

import { ActiveSessionPanel } from "@/components/active-session";
import { ExposureList } from "@/components/exposure-list";
import { MuscleFocusMap } from "@/components/muscle-focus-map";
import { PageHeader } from "@/components/page-header";
import { PostSessionFeedback } from "@/components/post-session-feedback";
import { StatePanel } from "@/components/state-panel";
import { Button, buttonVariants } from "@/components/ui/button";
import { Section } from "@/components/ui/section";
import { Segmented } from "@/components/ui/segmented";
import { Skeleton } from "@/components/ui/skeleton";
import { formatNumber, formatShortDate } from "@/lib/format";
import { useUserState } from "@/lib/state-provider";
import type { SessionLogDefaults, TrainingAlternative, WorkoutTemplate } from "@/types/api";
import { cn } from "@/lib/utils";

interface SessionOption {
  prescription_id: string | null;
  name: string;
  intensity: string | null;
  duration: string | null;
  template: WorkoutTemplate | null;
  log_defaults: SessionLogDefaults | null;
  isPrimary: boolean;
}

// Train is an execution surface, not a dashboard.
//
// Pre-session it reads like a launch screen: today's session, what it trains,
// how hard and the single action — everything else folds away. Once a session
// is running the page switches to a focused session mode.

export function TrainView() {
  const { ready, today, error, logSession, startSession, busy } = useUserState();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [duration, setDuration] = useState<string>("");
  const [rpe, setRpe] = useState<number>(6);
  const [completion, setCompletion] = useState<"Completed" | "Partial">("Completed");
  const [notes, setNotes] = useState("");
  const [actualSets, setActualSets] = useState<Record<string, number>>({});
  const [outcome, setOutcome] = useState<string | null>(null);
  const [failure, setFailure] = useState<string | null>(null);
  const [loggedSessionId, setLoggedSessionId] = useState<string | null>(null);

  const options = useMemo<SessionOption[]>(() => {
    if (!today) return [];
    const recommendation = today.training.recommendation;
    return [
      {
        prescription_id: recommendation.prescription_id,
        name: recommendation.primary_name,
        intensity: recommendation.session_demand,
        duration: recommendation.duration,
        template: recommendation.template,
        log_defaults: recommendation.log_defaults,
        isPrimary: true,
      },
      ...recommendation.alternatives.map((item: TrainingAlternative) => ({
        prescription_id: item.prescription_id,
        name: item.name,
        intensity: item.intensity,
        duration: item.duration,
        template: item.template,
        log_defaults: item.log_defaults,
        isPrimary: false,
      })),
    ];
  }, [today]);

  const selected = useMemo(() => {
    const wanted = selectedId ?? options[0]?.prescription_id ?? null;
    return options.find((option) => option.prescription_id === wanted) ?? options[0] ?? null;
  }, [options, selectedId]);

  const range = today?.training.recommendation.estimated_duration_min_range ?? null;
  const defaultDuration = range && range.length > 1 ? Math.round((range[0] + range[1]) / 2) : 50;

  if (!ready) {
    return (
      <div className="space-y-5">
        <Skeleton className="h-4 w-20" />
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-[16rem] w-full rounded-[var(--radius-card)]" />
      </div>
    );
  }
  if (!today) {
    return (
      <StatePanel
        tone="error"
        title="We couldn't load today's session"
        body={`${error ?? "Your training data did not respond."} Reload the page to try again.`}
      />
    );
  }

  const recommendation = today.training.recommendation;
  const isStop = today.readiness.safety_active;
  const active = today.active_session ?? null;
  const focusGroups = recommendation.muscle_groups.length
    ? recommendation.muscle_groups
    : [recommendation.focus ?? recommendation.primary_name];
  const exposureBelowTarget = today.training.exposure.groups.filter(
    (group) => (group.target ?? 0) > 0 && group.value < (group.target ?? 0),
  ).length;

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
      setLoggedSessionId(result.sessionId ?? null);
      setNotes("");
      setActualSets({});
    } else {
      setFailure(result.error ?? "The session could not be logged.");
    }
  };

  const logForm = (
    <div className="space-y-4">
      {outcome ? <p className="text-[0.82rem] font-medium text-[var(--status-green)]">{outcome}</p> : null}
      {failure ? <p className="text-[0.82rem] font-medium text-[var(--status-red)]">{failure}</p> : null}

      <div className="grid grid-cols-2 gap-3">
        <label className="block">
          <span className="text-[0.78rem] font-medium">
            Duration <span className="text-muted">min</span>
          </span>
          <input
            type="number"
            inputMode="numeric"
            min={1}
            step={5}
            value={duration || String(defaultDuration)}
            onChange={(event) => setDuration(event.target.value)}
            className="mt-1.5 min-h-11 w-full rounded-[var(--radius-control)] border border-subtle bg-surface-muted px-3 text-sm"
          />
        </label>
        <label className="block">
          <span className="text-[0.78rem] font-medium">Session RPE</span>
          <input
            type="number"
            inputMode="numeric"
            min={1}
            max={10}
            value={rpe}
            onChange={(event) => setRpe(Math.min(10, Math.max(1, Number(event.target.value) || 1)))}
            className="mt-1.5 min-h-11 w-full rounded-[var(--radius-control)] border border-subtle bg-surface-muted px-3 text-sm"
          />
          <span className="mt-1 block text-[0.68rem] text-muted">1 = very easy · 10 = maximal</span>
        </label>
      </div>

      {(selected?.log_defaults?.exercises ?? []).length > 0 ? (
        <div className="space-y-1.5">
          <p className="text-[0.78rem] font-medium">Actual completed sets</p>
          {(selected?.log_defaults?.exercises ?? []).map((exercise) => (
            <label key={exercise.name} className="flex min-h-11 items-center justify-between gap-3 text-[0.82rem]">
              <span className="min-w-0 truncate">{exercise.name}</span>
              <input
                type="number"
                min={0}
                max={20}
                aria-label={`${exercise.name} actual sets`}
                value={actualSets[exercise.name] ?? exercise.prescribed_sets}
                onChange={(event) =>
                  setActualSets((current) => ({ ...current, [exercise.name]: Number(event.target.value) || 0 }))
                }
                className="min-h-11 w-20 rounded-[var(--radius-control)] border border-subtle bg-surface-muted px-2 text-right text-[0.82rem] md:min-h-10"
              />
            </label>
          ))}
        </div>
      ) : null}

      <div className="space-y-1.5">
        <p className="text-[0.78rem] font-medium">Completion</p>
        <Segmented
          options={[
            { value: "Completed", label: "Completed" },
            { value: "Partial", label: "Partial" },
          ]}
          value={completion}
          size="sm"
          label="Completion status"
          onChange={(value) => setCompletion(value as "Completed" | "Partial")}
        />
      </div>

      <label className="block">
        <span className="text-[0.78rem] font-medium">
          Notes <span className="text-muted">optional</span>
        </span>
        <input
          type="text"
          value={notes}
          onChange={(event) => setNotes(event.target.value)}
          className="mt-1.5 min-h-11 w-full rounded-[var(--radius-control)] border border-subtle bg-surface-muted px-3 text-sm"
        />
      </label>

      <Button size="lg" variant="primary" className="w-full" disabled={busy || isStop} onClick={() => void submitLog()}>
        {busy ? "Saving…" : "Log completed workout"}
      </Button>
    </div>
  );

  // --------------------------------------------------------------------- //
  // Focused session mode: the running session replaces the launch screen.
  // --------------------------------------------------------------------- //
  if (active) {
    return (
      <div className="space-y-6">
        <PageHeader back={{ href: "/", label: "Today" }} eyebrow="Session in progress" title={recommendation.primary_name} />

        {isStop ? (
          <StatePanel
            tone="error"
            title="Safety routing is active"
            body="Normal workout guidance is disabled while a safety flag is selected, and logging a normal session is disabled too."
          />
        ) : null}

        <ActiveSessionPanel active={active} sessionTrace={today.session_trace ?? []} />

        <details className="surface group px-5 py-4">
          <summary className="flex min-h-11 cursor-pointer list-none items-center justify-between gap-3 text-[0.9rem] font-semibold">
            Complete session
            <span className="text-[0.74rem] font-normal text-muted">RPE · sets · notes</span>
          </summary>
          <div className="pt-4">{logForm}</div>
        </details>

        {loggedSessionId ? (
          <Section eyebrow="Personal response" title="Session feedback">
            <PostSessionFeedback
              sessionId={loggedSessionId}
              focus={recommendation.primary_name}
              onDone={(message) => setOutcome(message)}
            />
          </Section>
        ) : null}
      </div>
    );
  }

  // --------------------------------------------------------------------- //
  // Pre-session launch screen.
  // --------------------------------------------------------------------- //
  return (
    <div className="space-y-6">
      <PageHeader back={{ href: "/", label: "Today" }} eyebrow="Train" title="Today's session" />

      {isStop ? (
        <StatePanel
          tone="error"
          title="Safety routing is active"
          body="Normal workout guidance is disabled while a safety flag is selected, and logging a normal session is disabled too."
        />
      ) : null}

      <section className="surface-raised px-5 py-5">
        <h2 className="title-hero">{selected?.name ?? recommendation.primary_name}</h2>
        <p className="mt-2 text-[0.9rem] text-secondary">
          {[selected?.intensity ?? recommendation.session_demand, selected?.duration ?? recommendation.duration, recommendation.rir_guidance]
            .filter(Boolean)
            .join(" · ")}
        </p>

        <MuscleFocusMap groups={focusGroups} className="mt-5" />

        <Button
          size="lg"
          variant="primary"
          className="mt-5 w-full"
          disabled={busy || isStop}
          onClick={() => void startSession(selected?.prescription_id ?? null)}
        >
          {busy ? "Starting…" : "Start Session"}
        </Button>

        <details className="group mt-4">
          <summary className="flex min-h-10 cursor-pointer list-none items-center justify-between gap-3 text-[0.8rem] font-medium">
            Session details
            <span className="text-muted">{(selected?.template?.items ?? []).length} items</span>
          </summary>
          <div className="pt-2">
            <ul className="hairline-list space-y-0">
              {(selected?.template?.items ?? []).map((item) => (
                <li key={item} className="hairline py-2.5 text-[0.86rem]">
                  {item}
                </li>
              ))}
            </ul>
            {selected?.template?.note ? (
              <p className="mt-2 text-[0.72rem] leading-relaxed text-muted">{selected.template.note}</p>
            ) : null}
          </div>
        </details>
      </section>

      {options.length > 1 ? (
        <div>
          <p className="label-quiet mb-2">Alternative</p>
          <Segmented
            options={options.map((option) => ({
              value: option.prescription_id ?? option.name,
              label: option.name,
            }))}
            value={selected?.prescription_id ?? selected?.name ?? ""}
            size="sm"
            label="Session choice"
            onChange={(value) => {
              setSelectedId(String(value));
              setActualSets({});
            }}
          />
        </div>
      ) : null}

      <p className="text-[0.8rem] text-muted">
        {exposureBelowTarget === 0
          ? "Every muscle group is at or above its weekly target."
          : `${exposureBelowTarget} muscle group${exposureBelowTarget === 1 ? "" : "s"} below this week's target.`}
      </p>

      <details className="divider group pt-5">
        <summary className="flex min-h-11 cursor-pointer list-none items-center justify-between gap-3 text-[0.88rem] font-medium">
          Weekly exposure
          <span className="text-[0.74rem] text-muted">{today.training.exposure.groups.length} muscle groups</span>
        </summary>
        <div className="pt-4">
          <ExposureList exposure={today.training.exposure} />
        </div>
      </details>

      <details className="divider group pt-5">
        <summary className="flex min-h-11 cursor-pointer list-none items-center justify-between gap-3 text-[0.88rem] font-medium">
          Recent sessions
          <span className="text-[0.74rem] text-muted">{today.training.history.length} completed</span>
        </summary>
        <div className="pt-3">
          {today.training.history.length > 0 ? (
            <ul>
              {today.training.history.map((session) => (
                <li
                  key={`${session.date}-${session.focus}`}
                  className="hairline flex min-h-12 items-center justify-between gap-3 last:border-b-0"
                >
                  <span className="min-w-0">
                    <span className="block truncate text-[0.86rem] font-medium">
                      {session.focus ?? session.training_type ?? "Session"}
                    </span>
                    <span className="text-[0.72rem] text-muted">{formatShortDate(session.date)}</span>
                  </span>
                  <span className="shrink-0 text-right text-[0.76rem] text-muted">
                    {session.session_rpe !== null ? `RPE ${formatNumber(session.session_rpe)}` : "—"}
                    {session.duration_min !== null ? ` · ${formatNumber(session.duration_min)} min` : ""}
                    {session.working_sets !== null ? ` · ${formatNumber(session.working_sets)} sets` : ""}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <StatePanel
              tone="empty"
              title="No completed sessions yet"
              body="Log today's session and it will appear here, update weekly exposure and feed the next recommendation."
            />
          )}
        </div>
      </details>

      <details className="divider group pt-5">
        <summary className="flex min-h-11 cursor-pointer list-none items-center justify-between gap-3 text-[0.88rem] font-medium">
          Log completed workout
          <span className="text-[0.74rem] text-muted">RPE · sets · notes</span>
        </summary>
        <div className="pt-4">{logForm}</div>
      </details>

      {loggedSessionId ? (
        <Section eyebrow="Personal response" title="Session feedback">
          <PostSessionFeedback
            sessionId={loggedSessionId}
            focus={recommendation.primary_name}
            onDone={(message) => setOutcome(message)}
          />
        </Section>
      ) : null}

      <nav aria-label="Secondary" className="divider flex flex-wrap gap-x-6 gap-y-1 pt-5">
        <Link
          href="/decision-trace"
          className="flex min-h-11 items-center text-[0.82rem] font-medium text-muted transition-colors hover:text-foreground md:min-h-8"
        >
          Why this recommendation →
        </Link>
        <Link
          href="/personal-response"
          className="flex min-h-11 items-center text-[0.82rem] font-medium text-muted transition-colors hover:text-foreground md:min-h-8"
        >
          Personal response →
        </Link>
      </nav>

      <p className="flex items-start gap-2 text-[0.72rem] leading-relaxed text-muted">
        <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
        Today&apos;s inputs come from the morning check-in.
      </p>
      <Link href="/check-in" className={cn(buttonVariants({ variant: "secondary" }), "w-full")}>
        Go to morning check-in
      </Link>
    </div>
  );
}
