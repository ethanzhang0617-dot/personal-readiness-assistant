"use client";

import { ArrowUp, CircleAlert, Sparkles } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { PageHeader } from "@/components/page-header";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { statusLabel } from "@/lib/format";
import type { CoachKind, CoachTurn, TodayResponse } from "@/types/api";
import { cn } from "@/lib/utils";

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  provider?: string;
  kind?: CoachKind;
  notice?: string | null;
  failed?: boolean;
}

const STARTERS = [
  "Why this workout?",
  "Can I train harder today?",
  "What's my training load today?",
  "How much have I trained back this week?",
];

const KIND_LABEL: Record<CoachKind, string> = {
  verified_data: "VERIFIED DATA",
  ai_explanation: "AI explanation",
  deterministic_fallback: "Rule-based answer",
  safety: "Safety",
};

/**
 * Coach: real chat surface. Personal factual questions are answered by the
 * deterministic layer with zero provider calls; only explanation questions may
 * reach the AI provider, and every answer keeps its provenance label.
 */
export function CoachView({ profileId }: { profileId?: string }) {
  const [context, setContext] = useState<TodayResponse | null>(null);
  const [contextError, setContextError] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const scrollAnchor = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.today(profileId).then((result) => {
      if (cancelled) return;
      if (result.ok) setContext(result.data);
      else setContextError(result.error);
    });
    return () => {
      cancelled = true;
    };
  }, [profileId]);

  const send = useCallback(
    async (question: string) => {
      const trimmed = question.trim();
      if (!trimmed || sending) return;
      const history: CoachTurn[] = messages
        .filter((message) => !message.failed)
        .map((message) => ({ role: message.role, content: message.content }));
      setMessages((current) => [
        ...current,
        { id: `user-${Date.now()}`, role: "user", content: trimmed },
      ]);
      setDraft("");
      setSending(true);
      const result = await api.coachMessage(trimmed, history, profileId);
      setSending(false);
      if (!result.ok) {
        setMessages((current) => [
          ...current,
          {
            id: `assistant-${Date.now()}`,
            role: "assistant",
            content: "The Coach is unavailable right now. Your question was not sent to the AI provider.",
            kind: "deterministic_fallback",
            failed: true,
          },
        ]);
        return;
      }
      setMessages((current) => [
        ...current,
        {
          id: `assistant-${Date.now()}`,
          role: "assistant",
          content: result.data.answer,
          provider: result.data.provider,
          kind: result.data.kind,
          notice: result.data.notice,
        },
      ]);
    },
    [messages, profileId, sending],
  );

  useEffect(() => {
    scrollAnchor.current?.scrollIntoView({ block: "end" });
  }, [messages, sending]);

  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        eyebrow="Coach"
        title="AI Coach"
        description="Ask about your readiness, today's session, training and recovery."
      />

      {context ? (
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-[var(--radius-card)] border border-subtle bg-surface-muted px-4 py-3 text-[0.72rem] text-muted">
          <span className="font-semibold text-foreground">
            Readiness {statusLabel(context.readiness.status)}
          </span>
          <span>· {context.training.recommendation.primary_name}</span>
          <span>· {context.training.recommendation.session_demand}</span>
        </div>
      ) : contextError ? (
        <p className="rounded-[var(--radius-card)] border border-subtle bg-surface-muted px-4 py-3 text-[0.72rem] text-muted">
          Context unavailable: {contextError}
        </p>
      ) : (
        <Skeleton className="h-11 w-full" />
      )}

      <div className="min-h-[16rem] space-y-3">
        {messages.length === 0 ? (
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
                  onClick={() => void send(starter)}
                  className="flex min-h-11 items-center justify-between gap-3 rounded-[var(--radius-control)] border border-subtle bg-surface px-4 text-left text-sm transition-colors hover:bg-surface-muted"
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

        {messages.map((message) => (
          <div
            key={message.id}
            className={cn(
              "max-w-[92%] rounded-[var(--radius-card)] px-4 py-3 text-sm leading-relaxed",
              message.role === "user"
                ? "ml-auto bg-primary text-primary-foreground"
                : "border border-subtle bg-surface",
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
                {message.provider ? (
                  <span className="text-[0.62rem] text-muted">{message.provider}</span>
                ) : null}
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

        {sending ? (
          <div className="max-w-[92%] space-y-2 rounded-[var(--radius-card)] border border-subtle bg-surface px-4 py-3">
            <Skeleton className="h-3 w-4/5" />
            <Skeleton className="h-3 w-3/5" />
            <p className="text-[0.66rem] text-muted">Thinking about your training context…</p>
          </div>
        ) : null}
        <div ref={scrollAnchor} />
      </div>

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
          disabled={sending || draft.trim().length === 0}
          aria-label="Send message"
          className="flex h-11 w-11 shrink-0 items-center justify-center rounded-[var(--radius-control)] bg-primary text-primary-foreground transition-opacity disabled:opacity-40"
        >
          <ArrowUp className="h-4 w-4" />
        </button>
      </form>
    </div>
  );
}
