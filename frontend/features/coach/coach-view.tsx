"use client";

import { ArrowUp, CircleAlert, ShieldCheck, Sparkles } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useUserState } from "@/lib/state-provider";
import type { CoachKind } from "@/types/api";
import { cn } from "@/lib/utils";

const STARTERS = [
  "Why this workout?",
  "Explain my readiness.",
  "Can I train harder today?",
  // Phrasing matters: the deterministic router resolves this exact wording to
  // weekly exposure. The router is a protected contract, so the starter adapts.
  "How much have I trained back this week?",
];

// Personal Response starters resolve deterministically (zero provider calls).
// The wording is deliberately the phrasing the deterministic router matches.
const RESPONSE_STARTERS = [
  "How do I usually respond to high-demand sessions?",
  "How confident is today's personalized recommendation?",
  "How many sessions support this adjustment?",
  "Has Personal Response changed my training before?",
  "Why didn't you increase today's training if I usually recover well?",
];

// In-session calibration starters. These resolve deterministically too, and they
// only answer from recorded checkpoints — never from the explanation provider.
const CALIBRATION_STARTERS = [
  "What is my calibration today?",
  "Have I often needed to ease off recently?",
  "What RIR did I just record?",
];

// Provenance is communicated quietly: a small label above the answer, never a
// developer badge. Verified answers are the deterministic layer; everything else
// came from the explanation provider or its rule-based fallback.
const PROVENANCE: Record<CoachKind, { label: string; tone: "verified" | "ai" | "fallback" | "safety" }> = {
  verified_data: { label: "From your recorded data", tone: "verified" },
  ai_explanation: { label: "AI explanation", tone: "ai" },
  deterministic_fallback: { label: "Rule-based answer", tone: "fallback" },
  safety: { label: "Safety guidance", tone: "safety" },
};

export function CoachView() {
  const { ready, today, chat, askCoach, clearChat, busy } = useUserState();
  const [draft, setDraft] = useState("");
  const [error, setError] = useState<string | null>(null);
  const scrollAnchor = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    scrollAnchor.current?.scrollIntoView({ block: "end" });
  }, [chat, busy]);

  const send = async (question: string) => {
    const trimmed = question.trim();
    if (!trimmed) return;
    setDraft("");
    setError(null);
    const result = await askCoach(trimmed);
    if (!result.ok) setError(result.error ?? "The Coach is unavailable.");
  };

  return (
    <div className="flex min-h-[calc(100dvh-9rem)] flex-col gap-4">
      <PageHeader
        eyebrow="Coach"
        title="AI Coach"
        description="Ask about your readiness, today's session, training and recovery."
      />

      {today ? (
        <div className="surface flex items-center gap-3 px-4 py-3">
          <StatusBadge status={today.readiness.status} />
          <p className="min-w-0 truncate text-[0.78rem] text-muted">
            {today.training.recommendation.primary_name} · {today.training.recommendation.session_demand} ·{" "}
            {today.training.recommendation.duration}
          </p>
        </div>
      ) : (
        <Skeleton className="h-12 w-full" />
      )}

      <div className="flex-1 space-y-5">
        {chat.length === 0 ? (
          <div className="space-y-4 pt-2">
            <div className="space-y-1.5">
              <p className="flex items-center gap-2 text-sm font-medium">
                <Sparkles className="h-4 w-4 text-muted" aria-hidden />
                Start a conversation
              </p>
              <p className="text-[0.8rem] leading-relaxed text-muted">
                Questions about your own numbers are answered from your recorded data. Explanation questions may use the
                configured AI provider.
              </p>
            </div>
            <ul className="divide-y divide-subtle border-y border-subtle">
              {STARTERS.map((starter) => (
                <li key={starter}>
                  <button
                    type="button"
                    disabled={!ready || busy}
                    onClick={() => void send(starter)}
                    className="flex min-h-12 w-full items-center justify-between gap-3 text-left text-sm transition-colors hover:text-foreground disabled:opacity-50"
                  >
                    {starter}
                    <span aria-hidden className="text-muted">
                      →
                    </span>
                  </button>
                </li>
              ))}
            </ul>
            <p className="text-[0.7rem] font-medium text-muted">Personal response</p>
            <ul className="divide-y divide-subtle border-y border-subtle">
              {RESPONSE_STARTERS.map((starter) => (
                <li key={starter}>
                  <button
                    type="button"
                    disabled={!ready || busy}
                    onClick={() => void send(starter)}
                    className="flex min-h-12 w-full items-center justify-between gap-3 text-left text-sm transition-colors hover:text-foreground disabled:opacity-50"
                  >
                    {starter}
                    <span aria-hidden className="text-muted">
                      →
                    </span>
                  </button>
                </li>
              ))}
            </ul>
            <p className="text-[0.7rem] font-medium text-muted">In-session calibration</p>
            <ul className="divide-y divide-subtle border-y border-subtle">
              {CALIBRATION_STARTERS.map((starter) => (
                <li key={starter}>
                  <button
                    type="button"
                    disabled={!ready || busy}
                    onClick={() => void send(starter)}
                    className="flex min-h-12 w-full items-center justify-between gap-3 text-left text-sm transition-colors hover:text-foreground disabled:opacity-50"
                  >
                    {starter}
                    <span aria-hidden className="text-muted">
                      →
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        {chat.map((message) => {
          const provenance = message.kind ? PROVENANCE[message.kind] : null;
          if (message.role === "user") {
            return (
              <div key={message.id} className="flex justify-end">
                <p className="max-w-[85%] rounded-[1.1rem] rounded-br-md bg-primary px-4 py-2.5 text-sm leading-relaxed text-primary-foreground">
                  {message.content}
                </p>
              </div>
            );
          }
          return (
            <article key={message.id} className="flex gap-3">
              <span
                className={cn(
                  "mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-[0.62rem] font-bold",
                  provenance?.tone === "verified"
                    ? "bg-[var(--status-green-soft)] text-[var(--status-green)]"
                    : "bg-subtle text-muted",
                )}
                aria-hidden
              >
                {provenance?.tone === "verified" ? "✓" : "AI"}
              </span>
              <div className="min-w-0 flex-1 space-y-1.5">
                <p className="text-[0.68rem] font-semibold uppercase tracking-[0.08em] text-muted">
                  {provenance?.label ?? "Answer"}
                </p>
                <p className="whitespace-pre-wrap text-[0.9rem] leading-relaxed">{message.content}</p>
                {message.notice ? (
                  <p className="flex items-start gap-1.5 text-[0.7rem] leading-relaxed text-muted">
                    <CircleAlert className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
                    {message.notice}
                  </p>
                ) : null}
              </div>
            </article>
          );
        })}

        {busy && chat[chat.length - 1]?.role === "user" ? (
          <div className="flex gap-3">
            <span className="mt-0.5 h-7 w-7 shrink-0 rounded-full bg-subtle" aria-hidden />
            <div className="flex-1 space-y-2 pt-1">
              <Skeleton className="h-3 w-4/5" />
              <Skeleton className="h-3 w-3/5" />
              <p className="text-[0.7rem] text-muted">Thinking about your training context…</p>
            </div>
          </div>
        ) : null}
        <div ref={scrollAnchor} />
      </div>

      {error ? (
        <p className="flex items-start gap-2 rounded-[var(--radius-control)] border border-[var(--status-red-line)] bg-[var(--status-red-soft)] px-4 py-3 text-[0.78rem] text-[var(--status-red)]">
          <CircleAlert className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
          {error}
        </p>
      ) : null}

      <div className="sticky bottom-[calc(env(safe-area-inset-bottom)+4.75rem)] z-20 space-y-2 md:static">
        <form
          onSubmit={(event) => {
            event.preventDefault();
            void send(draft);
          }}
          className="surface-raised flex items-end gap-2 p-1.5"
        >
          <label className="sr-only" htmlFor="coach-input">
            Ask the Coach
          </label>
          <textarea
            id="coach-input"
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                void send(draft);
              }
            }}
            rows={1}
            placeholder="Ask about your training or recovery…"
            className="max-h-32 min-h-11 flex-1 resize-none bg-transparent px-3 py-2.5 text-sm outline-none placeholder:text-muted"
          />
          <button
            type="submit"
            disabled={busy || draft.trim().length === 0}
            aria-label="Send message"
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-[0.6rem] bg-primary text-primary-foreground transition-opacity disabled:opacity-35"
          >
            <ArrowUp className="h-4 w-4" />
          </button>
        </form>

        <div className="flex items-center justify-between gap-3 px-1">
          <p className="flex items-center gap-1.5 text-[0.68rem] text-muted">
            <ShieldCheck className="h-3.5 w-3.5" aria-hidden />
            Conversation is stored in this browser.
          </p>
          {chat.length > 0 ? (
            <button
              type="button"
              onClick={() => void clearChat()}
              className="min-h-11 px-1 text-[0.72rem] text-muted underline decoration-dotted underline-offset-2 md:min-h-9"
            >
              Clear conversation
            </button>
          ) : null}
        </div>
      </div>
    </div>
  );
}
