import { Skeleton } from "@/components/ui/skeleton";

/** Route-level skeleton shaped like the real content, not a line of loading text. */
export default function Loading() {
  return (
    <div className="space-y-5" aria-busy="true" aria-live="polite">
      <span className="sr-only">Loading</span>
      <div className="space-y-2">
        <Skeleton className="h-3 w-16" />
        <Skeleton className="h-7 w-40" />
      </div>
      <Skeleton className="h-[15rem] w-full rounded-[var(--radius-card)]" />
      <Skeleton className="h-16 w-full" />
      <Skeleton className="h-24 w-full" />
    </div>
  );
}
