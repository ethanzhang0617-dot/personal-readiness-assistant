"use client";

import { ArrowUp, CircleAlert, Sparkles } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { PageHeader } from "@/components/page-header";
import { Skeleton } from "@/components/ui/skeleton";
import { statusLabel } from "@/lib/format";
import { useUserState } from "@/lib/state-provider";
import type { CoachKind } from "@/types/api";
import { cn } from "@/lib/utils";

const STARTERS = [
  "Why this workout?",
  "Explain my readiness.",
  "Can I train harder today?",
  // Phrasing matters: the deterministic router resolves "How much have I trained
  // back this week?" to weekly exposure. "How much back volume have I done?" is
  // deliberately NOT used here because the router treats it as unresolved.
  "How much have I trained back this week?",
];

const KIND_LABEL: Record<CoachKind, string> = {
  verified_data: "VERIFIED DATA",
  ai_explanation: "AI explanation",
  deterministic_fallback: "Rule-based answer",
  safety: "Safety",
};

// Coach: factual questions are answered by the deterministic layer with zero
// provider calls; only explanation questions may reach the AI provider, and every
// answer keeps its provenance label. The conversation lives in this browser and
// survives navigation and reloads.

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
    <div className="flex flex-col gap-4">
      <PageHeader
        eyebrow="Coach"
        title="AI Coach"
        description="Ask about your readiness, today's session, training and recovery."
      />

      {today ? (
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-[var(--radius-card)] border border-subtle bg-surface-muted px-4 py-3 text-[0.72rem] text-muted">
          <span className="font-semibold text-foreground">Readiness {statusLabel(today.readiness.status)}</span>
          <span>· {today.training.recommendation.primary_name}</span>
          <span>· {today.training.recommendation.session_demand}</span>
        </div>
      ) : (
        <Skeleton className="h-11 w-full" />
      )}

      <div className="min-h-[16rem] space-y-3">
        {chat.length === 0 ? (
          <div className="space-y-3">
            <p className="flex items-center gap-2 text-sm text-muted">
              <Sparkles className="h-4 w-4" aria-hidden />
              Start with one of these, or ask your own question.
            </p>
            <div className="grid gap-2">
              {STARTERS.map((starter) => (
                <button
                  key={starter}
                  type="button"
                  disabled={!ready || busy}
                  onClick={() => void send(starter)}
                  className="flex min-h-11 items-center justify-between gap-3 rounded-[var(--radius-control)] border border-subtle bg-surface px-4 text-left text-sm transition-colors hover:bg-surface-muted disabled:opacity-50"
                >
                  {starter}
                  <span aria-hidden className="text-muted">
                    →
                  </span>
                </button>
              ))}
            </div>
          </div>
        ) : null}

        {chat.map((message) => (
          <div
            key={message.id}
            className={cn(
              "max-w-[92%] rounded-[var(--radius-card)] px-4 py-3 text-sm leading-relaxed",
              message.role === "user" ? "ml-auto bg-primary text-primary-foreground" : "border border-subtle bg-surface",
            )}
          >
            {message.role === "assistant" && message.kind ? (
              <div className="mb-2 flex flex-wrap items-center gap-2">
                <span
                  className={cn(
                    "rounded-full px-2 py-0.5 text-[0.62rem] font-semibold tracking-wide",
                    message.kind === "verified_data"
                      ? "bg-[var(--status-green-soft)] text-[var(--status-green)]"
                      : "bg-muted-soft text-muted",
                  )}
                >
                  {KIND_LABEL[message.kind]}
                </span>
                {message.provider ? <span className="text-[0.62rem] text-muted">{message.provider}</span> : null}
              </div>
            ) : null}
            <p className="whitespace-pre-wrap">{message.content}</p>
            {message.notice ? (
              <p className="mt-2 flex items-start gap-1.5 text-[0.66rem] text-muted">
                <CircleAlert className="mt-0.5 h-3 w-3 shrink-0" aria-hidden />
                {message.notice}
              </p>
            ) : null}
          </div>
        ))}

        {busy && chat[chat.length - 1]?.role === "user" ? (
          <div className="max-w-[92%] space-y-2 rounded-[var(--radius-card)] border border-subtle bg-surface px-4 py-3">
            <Skeleton className="h-3 w-4/5" />
            <Skeleton className="h-3 w-3/5" />
            <p className="text-[0.66rem] text-muted">Thinking about your training context…</p>
          </div>
        ) : null}
        <div ref={scrollAnchor} />
      </div>

      {error ? (
        <p className="flex items-start gap-2 rounded-[var(--radius-card)] border border-[var(--status-red-line)] bg-[var(--status-red-soft)] px-4 py-3 text-[0.72rem] text-[var(--status-red)]">
          <CircleAlert className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
          {error}
        </p>
      ) : null}

      <form
        onSubmit={(event) => {
          event.preventDefault();
          void send(draft);
        }}
        className="sticky bottom-[calc(env(safe-area-inset-bottom)+4.75rem)] z-20 flex items-end gap-2 rounded-[var(--radius-card)] border border-subtle bg-surface p-2 md:static"
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
          className="max-h-32 min-h-11 flex-1 resize-none bg-transparent px-2 py-2.5 text-sm outline-none placeholder:text-muted"
        />
        <button
          type="submit"
          disabled={busy || draft.trim().length === 0}
          aria-label="Send message"
          className="flex h-11 w-11 shrink-0 items-center justify-center rounded-[var(--radius-control)] bg-primary text-primary-foreground transition-opacity disabled:opacity-40"
        >
          <ArrowUp className="h-4 w-4" />
        </button>
      </form>

      <div className="flex items-center justify-between gap-3">
        <p className="text-[0.66rem] text-muted">
          Factual answers come from your recorded data and never call the AI provider. Conversation is stored in this
          browser.
        </p>
        {chat.length > 0 ? (
          <button
            type="button"
            onClick={() => void clearChat()}
            className="min-h-9 shrink-0 text-[0.7rem] text-muted underline decoration-dotted underline-offset-2"
          >
            Clear
          </button>
        ) : null}
      </div>
    </div>
  );
}
