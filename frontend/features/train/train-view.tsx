import { Info } from "lucide-react";

import { DecisionTrace } from "@/components/decision-trace";
import { PageHeader } from "@/components/page-header";
import { StatePanel } from "@/components/state-panel";
import { Card } from "@/components/ui/card";
import { api } from "@/lib/api";
import { formatNumber, formatShortDate } from "@/lib/format";

/**
 * Train: the session structure. Phase 1 shows the deterministic recommendation,
 * exposure, history and trace; completed-session logging still lives in the
 * Streamlit V1.1 reference app.
 */
export async function TrainView({ profileId }: { profileId?: string }) {
  const [today, exposure, history] = await Promise.all([
    api.today(profileId),
    api.exposure(profileId),
    api.history(profileId, 8),
  ]);

  if (!today.ok) {
    return <StatePanel tone="error" title="Training plan unavailable" body={today.error} />;
  }

  const { recommendation, decision_trace: trace } = today.data.training;

  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow="Train"
        title={recommendation.primary_name}
        description={`${recommendation.session_demand} · ${recommendation.duration} · ${recommendation.rir_guidance ?? "effort guidance unavailable"}`}
      />

      <Card className="p-4">
        <p className="eyebrow text-muted">Prescription</p>
        <ul className="mt-3 divide-y divide-subtle">
          {recommendation.exercises.map((exercise) => (
            <li key={exercise.name} className="flex items-baseline justify-between gap-3 py-2">
              <span className="text-sm font-medium">{exercise.name}</span>
              <span className="text-right text-[0.75rem] text-muted">
                {[exercise.sets ? `${exercise.sets} sets` : null, exercise.reps, exercise.rir]
                  .filter(Boolean)
                  .join(" · ")}
              </span>
            </li>
          ))}
          {recommendation.exercises.length === 0 ? (
            <li className="py-2 text-sm text-muted">No prescription is available for today.</li>
          ) : null}
        </ul>
        {recommendation.alternatives.length > 0 ? (
          <div className="mt-4 border-t border-subtle pt-3">
            <p className="eyebrow text-muted">Alternatives (do not replace the primary)</p>
            <ul className="mt-2 space-y-1">
              {recommendation.alternatives.map((alternative) => (
                <li key={alternative.name} className="text-sm">
                  <span className="font-medium">{alternative.name}</span>
                  <span className="text-muted">
                    {alternative.intensity ? ` · ${alternative.intensity}` : ""}
                    {alternative.duration ? ` · ${alternative.duration}` : ""}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
        {recommendation.avoid.length > 0 ? (
          <p className="mt-3 text-[0.75rem] text-muted">
            Avoid today: {recommendation.avoid.join(", ")}
          </p>
        ) : null}
      </Card>

      <Card className="p-4">
        <p className="eyebrow text-muted">Weekly exposure</p>
        {exposure.ok ? (
          <>
            <ul className="mt-3 space-y-2.5">
              {exposure.data.groups.map((group) => {
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
                      <div
                        className="h-full rounded-full bg-primary"
                        style={{ width: `${Math.round(ratio * 100)}%` }}
                      />
                    </div>
                  </li>
                );
              })}
            </ul>
            <p className="mt-3 text-[0.68rem] leading-relaxed text-muted">{exposure.data.note}</p>
            <p className="mt-1 text-[0.68rem] text-muted">
              Target source: {exposure.data.target_source ?? "not recorded"}
            </p>
          </>
        ) : (
          <p className="mt-3 text-sm text-muted">{exposure.error}</p>
        )}
      </Card>

      <Card className="p-4">
        <p className="eyebrow text-muted">Recent sessions</p>
        {history.ok && history.data.length > 0 ? (
          <ul className="mt-3 divide-y divide-subtle">
            {history.data.map((session) => (
              <li key={`${session.date}-${session.focus}`} className="flex items-baseline justify-between gap-3 py-2">
                <span className="text-sm font-medium">{session.focus ?? session.training_type ?? "Session"}</span>
                <span className="text-right text-[0.75rem] text-muted">
                  {formatShortDate(session.date)}
                  {session.session_rpe !== null ? ` · RPE ${formatNumber(session.session_rpe)}` : ""}
                  {session.duration_min !== null ? ` · ${formatNumber(session.duration_min)} min` : ""}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-3 text-sm text-muted">
            {history.ok ? "No completed sessions are recorded yet." : history.error}
          </p>
        )}
      </Card>

      <DecisionTrace steps={trace} rationale={recommendation.rationale} />

      <p className="flex items-start gap-2 text-[0.68rem] leading-relaxed text-muted">
        <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
        Completed-session logging and the workout template editor remain in the Streamlit V1.1 reference app during the
        migration. This screen reads the same deterministic recommendation.
      </p>
    </div>
  );
}
