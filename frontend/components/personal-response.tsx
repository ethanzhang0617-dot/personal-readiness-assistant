import { ChevronRight } from "lucide-react";

import { formatNumber, formatShortDate } from "@/lib/format";
import { calibrationLabel, calibrationTone } from "@/lib/calibration";
import { ADAPTATION_RESULT_LABELS, EVIDENCE_LABELS } from "@/lib/response";
import type {
  AdaptationEvent,
  EvidenceCoverage,
  PersonalResponse,
  PersonalResponseProfile,
  RecommendationConfidence,
  ResponseEpisode,
} from "@/types/api";
import { cn } from "@/lib/utils";

// Personal Response presentation. Observed response patterns only — never a
// recovery percentage, probability or "AI learned your body" claim.
//
// V1.3 Phase 2 adds the profile (by demand and, where the data supports it, by
// focus), the evidence coverage, the recommendation confidence and the
// adaptation history. All of it stays qualitative on purpose.

function evidenceTone(evidence: string | null | undefined): string {
  return evidence === "Established"
    ? "bg-[var(--status-green-soft)] text-[var(--status-green)]"
    : evidence === "Emerging"
      ? "bg-[var(--status-amber-soft)] text-[var(--status-amber)]"
      : "bg-surface-muted text-muted";
}

/**
 * Recommendation Confidence, as a compact label. It describes how much recent
 * personal evidence supports the personalisation — never a probability, and
 * never a claim about how recovered the user is.
 */
export function ConfidenceBadge({ confidence, className }: {
  confidence?: RecommendationConfidence | null;
  className?: string;
}) {
  if (!confidence?.label) return null;
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center rounded-full px-2 py-0.5 text-[0.62rem] font-semibold",
        evidenceTone(confidence.state),
        className,
      )}
    >
      {confidence.label}
    </span>
  );
}

/** The profile: what the system has learned, with the counts behind it. */
export function PersonalResponseProfilePanel({ profile }: { profile?: PersonalResponseProfile | null }) {
  if (!profile) return null;
  return (
    <div className="space-y-4">
      <ul className="divide-y divide-subtle border-y border-subtle">
        {profile.bands.map((band) => (
          <li key={band.band} className="flex items-start justify-between gap-3 py-3">
            <div className="min-w-0">
              <p className="text-[0.84rem] font-semibold">
                {band.band} demand
                <span className="ml-2 text-[0.7rem] font-normal text-muted">
                  {band.observations} observation{band.observations === 1 ? "" : "s"}
                </span>
              </p>
              <p className="mt-0.5 text-[0.74rem] text-muted">
                {band.observations > 0
                  ? `${band.poorer} / ${band.observations} poorer · ${band.as_usual} / ${band.observations} as expected · ${band.better} / ${band.observations} good`
                  : "No recorded session at this demand yet"}
              </p>
              <p className="mt-1 text-[0.76rem]">{band.pattern}</p>
              <p className="mt-0.5 text-[0.7rem] text-muted">Recent pattern: {band.recent_pattern}</p>
            </div>
            <span
              className={cn(
                "shrink-0 rounded-full px-2 py-0.5 text-[0.62rem] font-semibold",
                evidenceTone(band.evidence),
              )}
            >
              {EVIDENCE_LABELS[band.evidence] ?? band.evidence}
            </span>
          </li>
        ))}
      </ul>

      {profile.focus.length > 0 ? (
        <div>
          <p className="eyebrow">By training focus</p>
          <ul className="mt-2 space-y-2">
            {profile.focus.map((row) => (
              <li key={row.focus} className="flex items-start justify-between gap-3">
                <span className="min-w-0 text-[0.78rem]">
                  <span className="font-medium">{row.focus}</span>
                  <span className="ml-2 text-muted">
                    {row.observations} observation{row.observations === 1 ? "" : "s"}
                  </span>
                </span>
                <span className="shrink-0 text-[0.72rem] text-muted">{row.pattern}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <p className="text-[0.68rem] leading-relaxed text-muted">{profile.focus_note}</p>
    </div>
  );
}

/** How much personalised history actually exists. No fake precision. */
export function EvidenceCoveragePanel({ coverage }: { coverage?: EvidenceCoverage | null }) {
  if (!coverage) return null;
  const last =
    coverage.last_complete_days_ago === null
      ? "—"
      : coverage.last_complete_days_ago === 0
        ? "Today"
        : coverage.last_complete_days_ago === 1
          ? "Yesterday"
          : `${coverage.last_complete_days_ago} days ago`;
  return (
    <div className="space-y-3">
      <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-[0.75rem]">
        <div>
          <dt className="text-muted">Completed episodes</dt>
          <dd className="font-medium tabular-nums">{coverage.episodes_complete}</dd>
        </div>
        <div>
          <dt className="text-muted">Last complete episode</dt>
          <dd className="font-medium">{last}</dd>
        </div>
        {coverage.bands.map((row) => (
          <div key={row.band}>
            <dt className="text-muted">{row.band}-demand observations</dt>
            <dd className="font-medium tabular-nums">{row.observations}</dd>
          </div>
        ))}
        <div>
          <dt className="text-muted">Awaiting next check-in</dt>
          <dd className="font-medium tabular-nums">{coverage.episodes_pending}</dd>
        </div>
      </dl>
      <p className="text-[0.68rem] leading-relaxed text-muted">{coverage.note}</p>
    </div>
  );
}

/** Meaningful decision events only: a change, or an evaluated no-change. */
export function AdaptationHistoryList({ history = [] }: { history?: AdaptationEvent[] }) {
  if (!history.length) {
    return (
      <p className="text-[0.8rem] text-muted">
        No adaptation decisions recorded yet. Today&apos;s evaluation is saved as soon as the product computes your
        recommendation.
      </p>
    );
  }
  return (
    <ul className="divide-y divide-subtle border-y border-subtle">
      {history.map((row) => (
        <li key={`${row.date}-${row.recorded_at}`} className="py-3">
          <div className="flex items-start justify-between gap-3">
            <p className="text-[0.8rem] font-medium">{formatShortDate(row.date)}</p>
            <span className="shrink-0 text-[0.7rem] text-muted">
              {ADAPTATION_RESULT_LABELS[row.result] ?? row.result}
            </span>
          </div>
          <p className="mt-0.5 text-[0.72rem] text-muted tabular-nums">
            Base {row.base_band ?? "—"} → final {row.final_band ?? "—"}
            {row.confidence ? ` · ${row.confidence} evidence` : ""}
            {row.relevant_episodes ? ` · ${row.relevant_episodes} relevant sessions` : ""}
          </p>
          <p className="mt-1 text-[0.74rem] leading-relaxed">{row.reason}</p>
        </li>
      ))}
    </ul>
  );
}

export function PersonalResponseSummary({ response }: { response: PersonalResponse }) {
  const summary = response.summary ?? {};
  const confidence = response.confidence ?? null;
  return (
    <div className="space-y-3">
      <dl className="grid grid-cols-3 gap-px overflow-hidden rounded-[var(--radius-control)] bg-subtle">
        <div className="bg-surface px-3 py-3">
          <dt className="text-[0.7rem] text-muted">Complete episodes</dt>
          <dd className="mt-1 text-[0.95rem] font-semibold tabular-nums">{summary.episodes_complete ?? 0}</dd>
        </div>
        <div className="bg-surface px-3 py-3">
          <dt className="text-[0.7rem] text-muted">Awaiting check-in</dt>
          <dd className="mt-1 text-[0.95rem] font-semibold tabular-nums">{summary.episodes_pending ?? 0}</dd>
        </div>
        <div className="bg-surface px-3 py-3">
          <dt className="text-[0.7rem] text-muted">Evidence</dt>
          <dd className="mt-1 text-[0.9rem] font-semibold">
            {EVIDENCE_LABELS[String(summary.evidence)] ?? summary.evidence ?? "—"}
          </dd>
        </div>
      </dl>

      {confidence ? (
        <div className="flex items-start justify-between gap-3 border-t border-subtle pt-3">
          <div className="min-w-0">
            <p className="eyebrow">Recommendation confidence</p>
            <p className="mt-1 text-[0.78rem] leading-relaxed">{confidence.explanation}</p>
          </div>
          <ConfidenceBadge confidence={confidence} />
        </div>
      ) : null}

      {response.note ? <p className="text-[0.7rem] leading-relaxed text-muted">{response.note}</p> : null}
    </div>
  );
}

function EpisodeRow({ episode }: { episode: ResponseEpisode }) {
  const after = episode.after;
  const feedback = episode.feedback;
  const calibrated = episode.calibrated ?? null;
  const verdict = episode.response?.verdict ?? "unavailable";
  const verdictLabel =
    verdict === "poorer_than_usual" ? "Poorer than usual"
      : verdict === "better_than_usual" ? "Better than usual"
        : verdict === "as_usual" ? "As usual"
          : "Not enough data";
  return (
    <details className="group border-b border-subtle last:border-0">
      <summary className="flex min-h-14 cursor-pointer list-none items-center justify-between gap-3 py-2">
        <span className="min-w-0">
          <span className="block truncate text-[0.84rem] font-medium">
            {episode.focus ?? "Session"}
            {episode.band ? <span className="ml-2 text-[0.7rem] font-normal text-muted">{episode.band} demand</span> : null}
          </span>
          <span className="block text-[0.7rem] text-muted">
            {formatShortDate(episode.date)} ·{" "}
            {feedback ? "feedback recorded" : "no feedback"} ·{" "}
            {calibrated ? "checkpoint recorded · " : ""}
            {episode.link === "linked" ? "next-day check-in linked" : episode.link === "pending" ? "next-day check-in pending" : "no linked check-in"}
          </span>
        </span>
        <span className="flex shrink-0 items-center gap-2">
          <span className="text-[0.7rem] text-muted">{verdictLabel}</span>
          <ChevronRight className="h-4 w-4 text-muted transition-transform group-open:rotate-90" aria-hidden />
        </span>
      </summary>
      <div className="space-y-3 pb-4 pt-1 text-[0.78rem]">
        <div>
          <p className="eyebrow">Before</p>
          <p className="mt-1">
            {episode.before.readiness_status ?? "—"} readiness
            {episode.before.readiness_index !== null ? ` · index ${episode.before.readiness_index}` : ""}
            {Object.keys(episode.before.local_soreness ?? {}).length
              ? ` · soreness ${Object.entries(episode.before.local_soreness).map(([group, value]) => `${group} ${value}/5`).join(", ")}`
              : ""}
          </p>
        </div>
        <div>
          <p className="eyebrow">Recommended</p>
          <p className="mt-1">
            {episode.recommendation.final_demand ?? "—"}
            {episode.recommendation.adjustment ? " (adjusted from your recent response)" : ""}
            {episode.recommendation.duration ? ` · ${episode.recommendation.duration}` : ""}
            {episode.recommendation.rir ? ` · ${episode.recommendation.rir}` : ""}
          </p>
        </div>
        {/* V1.3 final sprint: the in-session checkpoint, when one was recorded.
            Episodes logged without a checkpoint simply omit this step. */}
        {calibrated ? (
          <div>
            <p className="eyebrow">Calibrated</p>
            <p className="mt-1">
              <span
                className={cn(
                  "mr-2 rounded-full px-2 py-0.5 text-[0.62rem] font-semibold",
                  calibrationTone(String(calibrated.result)),
                )}
              >
                {calibrationLabel(calibrated.result)}
              </span>
              {calibrated.effort ?? "—"}
              {calibrated.actual_rir !== null && calibrated.actual_rir !== undefined
                ? ` · ${calibrated.actual_rir} RIR`
                : ""}
              {calibrated.performance ? ` · ${calibrated.performance}` : ""}
            </p>
            {calibrated.guidance ? <p className="mt-0.5 text-muted">{calibrated.guidance}</p> : null}
          </div>
        ) : null}
        <div>
          <p className="eyebrow">Performed</p>
          <p className="mt-1">
            {formatNumber(episode.performed.duration_min)} min · session RPE {formatNumber(episode.performed.session_rpe)}
            {episode.performed.working_sets !== null ? ` · ${formatNumber(episode.performed.working_sets)} sets` : ""}
            {episode.performed.completion ? ` · ${episode.performed.completion}` : ""}
          </p>
          {feedback ? (
            <p className="mt-0.5 text-muted">
              Difficulty {feedback.difficulty}/5 · performance {feedback.performance}/5
              {feedback.note ? ` · “${feedback.note}”` : ""}
            </p>
          ) : null}
        </div>
        <div>
          <p className="eyebrow">After</p>
          {after ? (
            <p className="mt-1">
              Next check-in {formatShortDate(after.date)}: fatigue {after.fatigue ?? "—"}/5, soreness {after.soreness ?? "—"}/5
              {after.sleep_hours !== null ? `, sleep ${formatNumber(after.sleep_hours)} h` : ""}
              {after.rmssd_ms !== null ? `, HRV ${formatNumber(after.rmssd_ms)} ms` : ""}
            </p>
          ) : (
            <p className="mt-1 text-muted">No following check-in is recorded for this session yet.</p>
          )}
          {episode.response?.signals?.length ? (
            <ul className="mt-1.5 space-y-1">
              {episode.response.signals.map((signal) => (
                <li key={signal} className="text-muted">
                  • {signal}
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      </div>
    </details>
  );
}

export function ResponseEpisodeList({ episodes, limit = 8 }: { episodes: ResponseEpisode[]; limit?: number }) {
  if (!episodes.length) {
    return (
      <p className="text-[0.8rem] text-muted">
        No response episodes yet. Log a completed session, save the short feedback, then check in the next morning —
        that becomes the first episode.
      </p>
    );
  }
  return (
    <div className="border-t border-subtle">
      {episodes.slice(0, limit).map((episode) => (
        <EpisodeRow key={episode.session_id} episode={episode} />
      ))}
    </div>
  );
}
