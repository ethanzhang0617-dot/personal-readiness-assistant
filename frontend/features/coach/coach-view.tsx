"use client";

import Link from "next/link";
import { ArrowUp, ChevronRight, CircleAlert, ShieldCheck, Sparkles } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { PageHeader } from "@/components/page-header";
import { RichText } from "@/components/ui/rich-text";
import { Skeleton } from "@/components/ui/skeleton";
import { COACH_MENUS, PRIMARY_QUESTIONS } from "@/lib/coach-questions";
import { useUserState } from "@/lib/state-provider";
import type { CoachKind } from "@/types/api";
import { cn } from "@/lib/utils";

// Coach home: conversational, not a FAQ directory.
//
// Four high-frequency questions and three compact links to the Coach-internal
// menus. The full question library never renders here, and the answers below are
// exactly the same answers the product produced before — only their entry points
// moved.

// Provenance is communicated quietly: a small label above the answer, never a
// developer badge. Verified answers are the deterministic layer; everything else
// came from the explanation provider or its rule-based fallback.
const PROVENANCE: Record<CoachKind, { label: string; tone: "verified" | "ai" | "fallback" | "safety" }> = {
  verified_data: { label: "From your recorded data", tone: "verified" },
  ai_explanation: { label: "AI explanation", tone: "ai" },
  deterministic_fallback: { label: "Rule-based answer", tone: "fallback" },
  safety: { label: "Safety guidance", tone: "safety" },
};

function QuestionList({
  onAsk,
  disabled,
  className,
}: {
  onAsk: (question: string) => void;
  disabled: boolean;
  className?: string;
}) {
  return (
    <ul className={cn("border-y border-subtle", className)}>
      {PRIMARY_QUESTIONS.map((question) => (
        <li key={question}>
          <button
            type="button"
            disabled={disabled}
            onClick={() => onAsk(question)}
            className="flex min-h-12 w-full items-center justify-between gap-3 border-b border-subtle py-3 text-left text-[0.88rem] leading-snug transition-colors last:border-b-0 hover:text-muted disabled:opacity-50"
          >
            {question}
            <span aria-hidden className="shrink-0 text-muted">
              →
            </span>
          </button>
        </li>
      ))}
    </ul>
  );
}

function TopicLinks({ className }: { className?: string }) {
  return (
    <nav aria-label="Coach topics" className={cn("border-y border-subtle", className)}>
      {COACH_MENUS.map((menu) => (
        <Link
          key={menu.key}
          href={menu.href}
          className="flex min-h-12 items-center justify-between gap-3 border-b border-subtle py-3 text-[0.88rem] transition-colors last:border-b-0 hover:text-muted"
        >
          <span className="font-medium">{menu.title}</span>
          <span className="flex shrink-0 items-center gap-1 text-[0.72rem] text-muted">
            {menu.questions.length} questions
            <ChevronRight className="h-4 w-4" aria-hidden />
          </span>
        </Link>
      ))}
    </nav>
  );
}

export function CoachView() {
  const { ready, chat, askCoach, clearChat, busy } = useUserState();
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
    <div className="flex min-h-[calc(100dvh-9rem)] flex-col gap-5">
      <PageHeader
        eyebrow="Coach"
        title="Ask Coach"
        description="Ask about today's session, your readiness, or your recorded training."
      />

      <div className="flex-1 space-y-5">
        {chat.length === 0 ? (
          <div className="space-y-5">
            <div className="space-y-2">
              <p className="flex items-center gap-2 text-[0.82rem] font-medium">
                <Sparkles className="h-4 w-4 text-muted" aria-hidden />
                Suggested questions
              </p>
              <QuestionList onAsk={(question) => void send(question)} disabled={!ready || busy} />
            </div>
            <TopicLinks />
          </div>
        ) : (
          <>
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
                    <p className="label-quiet font-semibold">{provenance?.label ?? "Answer"}</p>
                    <RichText text={message.content} />
                    {message.kind === "ai_explanation" ? (
                      <details className="group">
                        <summary className="flex min-h-9 cursor-pointer list-none items-center gap-1 text-[0.72rem] font-medium text-muted">
                          See reasoning →
                          <span className="transition-transform group-open:rotate-90" aria-hidden>
                            ›
                          </span>
                        </summary>
                        <p className="mt-1.5 text-[0.72rem] leading-relaxed text-muted">
                          This wording is generated from your verified structured facts. The recommendation and every
                          personal number come from the deterministic decision system, not from the model.
                        </p>
                        {message.notice ? (
                          <p className="mt-1 text-[0.72rem] leading-relaxed text-muted">{message.notice}</p>
                        ) : null}
                      </details>
                    ) : message.notice ? (
                      <p className="flex items-start gap-1.5 text-[0.7rem] leading-relaxed text-muted">
                        <CircleAlert className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
                        {message.notice}
                      </p>
                    ) : null}
                  </div>
                </article>
              );
            })}

            {/* Once a conversation exists the home stays short: the library and
                the topic links fold away behind one line. */}
            <details className="divider group pt-4">
              <summary className="flex min-h-11 cursor-pointer list-none items-center justify-between gap-3 text-[0.84rem] font-medium">
                Suggested questions
                <ChevronRight className="h-4 w-4 text-muted transition-transform group-open:rotate-90" aria-hidden />
              </summary>
              <div className="space-y-5 pt-3">
                <QuestionList onAsk={(question) => void send(question)} disabled={!ready || busy} />
                <TopicLinks />
              </div>
            </details>
          </>
        )}

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
