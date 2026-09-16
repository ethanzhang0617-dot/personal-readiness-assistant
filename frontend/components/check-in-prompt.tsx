"use client";

import Link from "next/link";
import { ArrowUpRight, CalendarDays } from "lucide-react";

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
        "divider flex min-h-12 items-center justify-between gap-3 pt-4 text-sm transition-colors hover:text-foreground",
        className,
      )}
    >
      <span className="flex min-w-0 items-center gap-2.5">
        <CalendarDays className="h-4 w-4 shrink-0 text-muted" aria-hidden />
        <span className="truncate">
          <span className="font-medium">Morning check-in</span>
          <span className="ml-2 text-muted">{checkedIn ? "recorded today" : "not recorded · demo scenario"}</span>
        </span>
      </span>
      <span className="flex shrink-0 items-center gap-1 text-[0.78rem] font-semibold">
        {checkedIn ? "Update" : "Check in"}
        <ArrowUpRight className="h-3.5 w-3.5" aria-hidden />
      </span>
    </Link>
  );
}
