"use client";

import Link from "next/link";
import { ArrowUpRight, Sunrise } from "lucide-react";

import { todayIso, useUserState } from "@/lib/state-provider";
import { cn } from "@/lib/utils";

/** Today's check-in state as a quiet inline row, not another card. */
export function CheckInPrompt({ className }: { className?: string }) {
  const { state } = useUserState();
  const checkedIn = Boolean(state?.check_in && state.check_in.date === todayIso());

  return (
    <Link
      href="/check-in"
      className={cn(
        "flex min-h-14 items-center justify-between gap-3 rounded-[var(--radius-card)] bg-surface-secondary px-4 py-3 transition-colors hover:bg-accent-soft",
        className,
      )}
    >
      <span className="flex min-w-0 items-center gap-3">
        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-surface text-muted">
          <Sunrise className="h-4 w-4" aria-hidden />
        </span>
        <span className="min-w-0">
          <span className="block text-[0.86rem] font-medium">Morning check-in</span>
          <span className="block truncate text-[0.74rem] text-muted">
            {checkedIn ? "Recorded today" : "Not recorded · demo scenario"}
          </span>
        </span>
      </span>
      <span className="flex shrink-0 items-center gap-1 text-[0.8rem] font-semibold text-accent">
        {checkedIn ? "Update" : "Check in"}
        <ArrowUpRight className="h-3.5 w-3.5" aria-hidden />
      </span>
    </Link>
  );
}
