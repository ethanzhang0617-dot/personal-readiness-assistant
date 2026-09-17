import type { ReadinessStatus } from "@/types/api";

/** Status colour is paired with a text label everywhere; never colour alone. */
export function statusTone(status: ReadinessStatus | string): {
  text: string;
  bg: string;
  border: string;
  dot: string;
} {
  switch (status) {
    case "GREEN":
      return { text: "text-[var(--status-green)]", bg: "bg-[var(--status-green-soft)]", border: "border-[var(--status-green-line)]", dot: "bg-[var(--status-green)]" };
    case "AMBER":
      return { text: "text-[var(--status-amber)]", bg: "bg-[var(--status-amber-soft)]", border: "border-[var(--status-amber-line)]", dot: "bg-[var(--status-amber)]" };
    case "RED":
    case "STOP / PROFESSIONAL REVIEW":
      return { text: "text-[var(--status-red)]", bg: "bg-[var(--status-red-soft)]", border: "border-[var(--status-red-line)]", dot: "bg-[var(--status-red)]" };
    default:
      return { text: "text-muted", bg: "bg-[var(--muted-soft)]", border: "border-subtle", dot: "bg-muted" };
  }
}

export function statusLabel(status: ReadinessStatus | string): string {
  switch (status) {
    case "GREEN":
      return "Green";
    case "AMBER":
      return "Amber";
    case "RED":
      return "Red";
    case "STOP / PROFESSIONAL REVIEW":
      return "Stop · professional review";
    default:
      return "Insufficient data";
  }
}

export function formatShortDate(value: string | null | undefined): string {
  if (!value) return "—";
  const parsed = new Date(`${value}T00:00:00`);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleDateString("en-GB", { day: "numeric", month: "short" });
}

export function formatNumber(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined) return "—";
  return Number.isInteger(value) ? String(value) : value.toFixed(digits).replace(/\.0$/, "");
}

/**
 * The engines label their steps in upper case ("WEEKLY EXPOSURE"). The consumer
 * interface reads as editorial sentence case instead, so all-caps labels stay
 * rare. Values are never transformed — only these labels.
 */
export function sentenceCase(value: string): string {
  const lower = value.toLowerCase();
  return lower.charAt(0).toUpperCase() + lower.slice(1);
}
