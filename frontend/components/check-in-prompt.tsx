"use client";

import Link from "next/link";
import { CalendarDays } from "lucide-react";

import { todayIso, useUserState } from "@/lib/state-provider";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

/** Today's check-in state, surfaced on the home screen. */
export function CheckInPrompt() {
  const { state } = useUserState();
  const checkedIn = Boolean(state?.check_in && state.check_in.date === todayIso());

  return (
    <section className="flex items-center justify-between gap-3 rounded-[var(--radius-card)] border border-subtle bg-surface px-3 py-2.5">
      <div className="flex min-w-0 items-center gap-2.5">
        <CalendarDays className="h-4 w-4 shrink-0 text-muted" aria-hidden />
        <p className="truncate text-[0.78rem]">
          <span className="eyebrow mr-1.5 text-muted">Check-in</span>
          {checkedIn ? "recorded today" : "not recorded · demo scenario"}
        </p>
      </div>
      <Link
        href="/check-in"
        className={cn(buttonVariants({ variant: checkedIn ? "ghost" : "secondary", size: "sm" }), "shrink-0")}
      >
        {checkedIn ? "Update" : "Check in"}
      </Link>
    </section>
  );
}
