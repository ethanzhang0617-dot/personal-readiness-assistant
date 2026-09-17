"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft, ChevronRight } from "lucide-react";
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
    <div className="space-y-6">
      <Link
        href="/coach"
        className="inline-flex min-h-11 items-center gap-1.5 text-[0.75rem] text-muted transition-colors hover:text-foreground md:min-h-9"
      >
        <ArrowLeft className="h-3.5 w-3.5" aria-hidden />
        Coach
      </Link>

      <PageHeader eyebrow="Coach" title={menu.title} description={menu.summary} />

      <ul className="border-y border-subtle">
        {menu.questions.map((question) => (
          <li key={question}>
            <button
              type="button"
              disabled={!ready || busy}
              onClick={() => ask(question)}
              className="flex min-h-12 w-full items-center justify-between gap-3 border-b border-subtle py-3 text-left text-[0.88rem] leading-snug transition-colors last:border-b-0 hover:text-muted disabled:opacity-50"
            >
              {question}
              <span className="shrink-0 text-[0.72rem] text-muted" aria-hidden>
                {sent === question && busy ? "Asking…" : <ChevronRight className="h-4 w-4" />}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
