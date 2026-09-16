"use client";

import Link from "next/link";
import { Info } from "lucide-react";
import { useMemo, useState } from "react";

import { DecisionTrace } from "@/components/decision-trace";
import { ExposureList } from "@/components/exposure-list";
import { PageHeader } from "@/components/page-header";
import { PersonalResponseSummary, ResponseEpisodeList } from "@/components/personal-response";
import { PostSessionFeedback } from "@/components/post-session-feedback";
import { StatePanel } from "@/components/state-panel";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
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
      <div className="space-y-4">
        <Skeleton className="h-6 w-24" />
        <Skeleton className="h-20 w-full" />
        <Skeleton className="h-56 w-full" />
      </div>
    );
  }
  if (!today) {
    return (
      <StatePanel
        tone="error"
        title="Training plan unavailable"
        body={`${error ?? "No training plan was returned."} Start the API and reload this page.`}
      />
    );
  }

  const recommendation = today.training.recommendation;
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
      setLoggedSessionId(result.sessionId ?? null);
      setNotes("");
      setActualSets({});
    } else {
      setFailure(result.error ?? "The session could not be logged.");
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Train"
        title={recommendation.primary_name}
        description={`${recommendation.session_demand} · ${recommendation.duration} · ${recommendation.rir_guidance ?? "effort guidance unavailable"}`}
      />

      {isStop ? (
        <StatePanel
          tone="error"
          title="Safety routing is active"
          body="Normal workout guidance is disabled while a safety flag is selected, and logging a normal session is disabled too."
        />
      ) : null}

      {options.length > 1 ? (
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
      ) : null}

      <Section
        eyebrow={selected?.isPrimary ? "Primary recommendation" : "Rule-generated alternative"}
        // The page title already names the primary session; only an alternative
        // needs its own heading so the two never duplicate each other.
        title={selected?.isPrimary ? undefined : (selected?.template?.title ?? selected?.name)}
        description={[selected?.intensity, selected?.duration].filter(Boolean).join(" · ")}
      >
        <ul className="divide-y divide-subtle border-y border-subtle">
          {(selected?.template?.items ?? []).map((item) => (
            <li key={item} className="py-2.5 text-[0.86rem]">
              {item}
            </li>
          ))}
        </ul>
        {selected?.template?.note ? (
          <p className="mt-2 text-[0.68rem] text-muted">{selected.template.note}</p>
        ) : null}
        {recommendation.alternatives.length > 0 ? (
          <p className="mt-2 text-[0.68rem] text-muted">
            Choosing an alternative never replaces the primary recommendation.
          </p>
        ) : null}
      </Section>

      <Section eyebrow="This week" title="Weekly exposure">
        <ExposureList exposure={today.training.exposure} />
      </Section>

      <Section
        eyebrow="History"
        title="Recent sessions"
        description={`${today.training.history.length} completed sessions, newest first.`}
      >
        {today.training.history.length > 0 ? (
          <ul className="divide-y divide-subtle border-y border-subtle">
            {today.training.history.map((session) => (
              <li key={`${session.date}-${session.focus}`} className="flex min-h-12 items-center justify-between gap-3">
                <span className="min-w-0">
                  <span className="block truncate text-[0.86rem] font-medium">
                    {session.focus ?? session.training_type ?? "Session"}
                  </span>
                  <span className="text-[0.7rem] text-muted">{formatShortDate(session.date)}</span>
                </span>
                <span className="shrink-0 text-right text-[0.74rem] text-muted">
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
            body="Log today's session below and it will appear here, update weekly exposure and feed the next recommendation."
          />
        )}
      </Section>

      <DecisionTrace steps={today.training.decision_trace} rationale={recommendation.rationale} />

      <Section
        eyebrow="Personal response"
        title="Response history"
        description="Each episode links the session you logged, your feedback and the next check-in."
      >
        {today.personal_response ? (
          <div className="space-y-4">
            <PersonalResponseSummary response={today.personal_response} />
            <ResponseEpisodeList episodes={today.personal_response.episodes} limit={5} />
          </div>
        ) : null}
      </Section>

      <Section eyebrow="After training" title="Log completed workout">
        <Card className="space-y-4 p-4">
          <p className="text-[0.72rem] leading-relaxed text-muted">
            Seven-day exposure uses the sets you actually completed. Logging here updates exposure, training load and the
            next recommendation immediately.
          </p>
          {outcome ? <p className="text-[0.8rem] font-medium text-[var(--status-green)]">{outcome}</p> : null}
          {failure ? <p className="text-[0.8rem] font-medium text-[var(--status-red)]">{failure}</p> : null}

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
                className="mt-1.5 min-h-11 w-full rounded-[var(--radius-control)] border border-subtle bg-surface px-3 text-sm"
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
                className="mt-1.5 min-h-11 w-full rounded-[var(--radius-control)] border border-subtle bg-surface px-3 text-sm"
              />
              <span className="mt-1 block text-[0.66rem] text-muted">1 = very easy · 10 = maximal</span>
            </label>
          </div>

          {(selected?.log_defaults?.exercises ?? []).length > 0 ? (
            <div className="space-y-1.5">
              <p className="text-[0.78rem] font-medium">Actual completed sets</p>
              {(selected?.log_defaults?.exercises ?? []).map((exercise) => (
                <label key={exercise.name} className="flex min-h-11 items-center justify-between gap-3 text-[0.8rem]">
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
                    className="min-h-11 w-20 rounded-[var(--radius-control)] border border-subtle bg-surface px-2 text-right text-[0.8rem] md:min-h-10"
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
              className="mt-1.5 min-h-11 w-full rounded-[var(--radius-control)] border border-subtle bg-surface px-3 text-sm"
            />
          </label>

          <Button size="lg" variant="primary" className="w-full" disabled={busy || isStop} onClick={() => void submitLog()}>
            {busy ? "Saving…" : "Log completed workout"}
          </Button>
        </Card>
      </Section>

      {loggedSessionId ? (
        <Section eyebrow="Personal response" title="Session feedback" divided={false}>
          <Card className="p-4">
            <PostSessionFeedback
              sessionId={loggedSessionId}
              focus={recommendation.primary_name}
              onDone={(message) => setOutcome(message)}
            />
          </Card>
        </Section>
      ) : null}

      <p className="flex items-start gap-2 text-[0.7rem] leading-relaxed text-muted">
        <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
        Today&apos;s inputs come from the morning check-in. Changing them there replaces today&apos;s demo scenario.
      </p>
      <Link href="/check-in" className={cn(buttonVariants({ variant: "secondary" }), "w-full")}>
        Go to morning check-in
      </Link>
    </div>
  );
}
