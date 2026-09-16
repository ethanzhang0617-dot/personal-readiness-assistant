import { statusLabel, statusTone } from "@/lib/format";
import { cn } from "@/lib/utils";

/** Colour is always paired with the written status, never used alone. */
export function StatusBadge({ status, className }: { status: string; className?: string }) {
  const tone = statusTone(status);
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[0.7rem] font-semibold tracking-wide",
        tone.bg,
        tone.border,
        tone.text,
        className,
      )}
    >
      <span className={cn("h-1.5 w-1.5 rounded-full", tone.dot)} aria-hidden />
      {statusLabel(status)}
    </span>
  );
}
