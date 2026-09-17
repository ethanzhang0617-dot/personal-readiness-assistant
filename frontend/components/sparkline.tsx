import type { InsightPoint } from "@/types/api";
import { cn } from "@/lib/utils";

/**
 * Tiny trend line for an Insights module. Gaps stay gaps — a missing day is
 * never drawn as zero — and the line uses the theme's chart tokens.
 */
export function Sparkline({
  points,
  className,
  width = 220,
  height = 48,
}: {
  points: InsightPoint[];
  className?: string;
  width?: number;
  height?: number;
}) {
  const values = points.map((point) => point.value).filter((value): value is number => value !== null);
  if (values.length < 2) {
    return (
      <p className={cn("text-[0.74rem] text-muted", className)}>Not enough recorded data yet.</p>
    );
  }

  const low = Math.min(...values);
  const high = Math.max(...values);
  const span = high - low || 1;
  const pad = 4;
  const step = points.length > 1 ? (width - pad * 2) / (points.length - 1) : 0;
  const y = (value: number) => pad + (height - pad * 2) * (1 - (value - low) / span);

  const segments: string[] = [];
  let current: string[] = [];
  points.forEach((point, index) => {
    if (point.value === null) {
      if (current.length > 1) segments.push(current.join(" "));
      current = [];
      return;
    }
    current.push(`${current.length === 0 ? "M" : "L"}${(pad + index * step).toFixed(1)},${y(point.value).toFixed(1)}`);
  });
  if (current.length > 1) segments.push(current.join(" "));

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="none"
      role="img"
      aria-label={`Trend over ${points.length} check-ins, latest ${points[points.length - 1]?.value ?? "no record"}`}
      className={cn("h-12 w-full", className)}
    >
      {segments.map((path) => (
        <path
          key={path}
          d={path}
          fill="none"
          stroke="var(--chart-line)"
          strokeWidth={2}
          strokeLinecap="round"
          vectorEffect="non-scaling-stroke"
        />
      ))}
    </svg>
  );
}
