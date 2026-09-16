import { ChevronRight } from "lucide-react";

import { formatNumber, formatShortDate } from "@/lib/format";
import { EVIDENCE_LABELS } from "@/lib/response";
import type { PersonalResponse, ResponseEpisode } from "@/types/api";
import { cn } from "@/lib/utils";

// Personal Response presentation. Observed response patterns only — never a
// recovery percentage, probability or "AI learned your body" claim.

export function PersonalResponseSummary({ response }: { response: PersonalResponse }) {
  const summary = response.summary ?? {};
  const bands = response.bands ?? [];
  return (
    <div className="space-y-4">
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

      <ul className="divide-y divide-subtle border-y border-subtle">
        {bands.map((band) => (
          <li key={band.band} className="flex items-start justify-between gap-3 py-3">
            <div className="min-w-0">
              <p className="text-[0.84rem] font-semibold">
                {band.band} demand
                <span className="ml-2 text-[0.7rem] font-normal text-muted">
                  {band.observations} observation{band.observations === 1 ? "" : "s"}
                </span>
              </p>
              <p className="mt-0.5 text-[0.75rem] text-muted">{band.pattern}</p>
            </div>
            <span
              className={cn(
                "shrink-0 rounded-full px-2 py-0.5 text-[0.62rem] font-semibold",
                band.evidence === "Established"
                  ? "bg-[var(--status-green-soft)] text-[var(--status-green)]"
                  : band.evidence === "Emerging"
                    ? "bg-[var(--status-amber-soft)] text-[var(--status-amber)]"
                    : "bg-surface-muted text-muted",
              )}
            >
              {EVIDENCE_LABELS[band.evidence] ?? band.evidence}
            </span>
          </li>
        ))}
      </ul>

      {response.note ? <p className="text-[0.7rem] leading-relaxed text-muted">{response.note}</p> : null}
    </div>
  );
}

function EpisodeRow({ episode }: { episode: ResponseEpisode }) {
  const after = episode.after;
  const feedback = episode.feedback;
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
