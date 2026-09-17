"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { PageHeader } from "@/components/page-header";
import type { CoachMenu } from "@/lib/coach-questions";
import { useUserState } from "@/lib/state-provider";

// A Coach-internal secondary surface: one short list of questions, plain rows,
// no cards and no essays. Asking a question sends it through exactly the same
// Coach path as before and returns to the conversation, which is where answers
// belong.

export function CoachMenuView({ menu }: { menu: CoachMenu }) {
  const { askCoach, ready, busy } = useUserState();
  const router = useRouter();
  const [sent, setSent] = useState<string | null>(null);

  const ask = (question: string) => {
    setSent(question);
    // The provider owns the conversation, so the answer lands on Coach even
    // though this page navigates away immediately.
    void askCoach(question);
    router.push("/coach");
  };

  return (
    <div className="mx-auto w-full space-y-6 md:max-w-[42rem]">
      <PageHeader back={{ href: "/coach", label: "Coach" }} eyebrow="Coach" title={menu.title} description={menu.summary} />

      <ul className="space-y-1">
        {menu.questions.map((question) => (
          <li key={question}>
            <button
              type="button"
              disabled={!ready || busy}
              onClick={() => ask(question)}
              className="flex min-h-14 w-full items-center justify-between gap-3 rounded-[var(--radius-control)] px-3 text-left text-[0.9rem] leading-snug transition-colors hover:bg-surface-muted disabled:opacity-50"
            >
              {question}
              <span className="shrink-0 text-[0.74rem] text-muted" aria-hidden>
                {sent === question && busy ? "Asking…" : "→"}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
