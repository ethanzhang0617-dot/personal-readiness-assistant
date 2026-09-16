import type { InsightPoint } from "@/types/api";

// Minimal responsive trend chart. Missing values break the line instead of
// dropping to zero, and a baseline reference is drawn only when it exists.

interface TrendChartProps {
  points: InsightPoint[];
  baseline?: number | null;
  height?: number;
  label: string;
}

export function TrendChart({ points, baseline = null, height = 96, label }: TrendChartProps) {
  const values = points.map((point) => point.value).filter((value): value is number => value !== null);
  const means = points.map((point) => point.rolling_mean).filter((value): value is number => value !== null);

  if (values.length < 2) {
    return (
      <p className="flex h-24 items-center justify-center rounded-[var(--radius-control)] bg-muted-soft text-[0.72rem] text-muted">
        Not enough recorded data yet.
      </p>
    );
  }

  const pool = [...values, ...means, ...(baseline !== null ? [baseline] : [])];
  const min = Math.min(...pool);
  const max = Math.max(...pool);
  const span = max - min || 1;
  const padding = span * 0.12;
  const low = min - padding;
  const high = max + padding;
  const width = 320;
  const x = (index: number) => (points.length === 1 ? 0 : (index / (points.length - 1)) * width);
  const y = (value: number) => height - ((value - low) / (high - low)) * height;

  const segments: string[] = [];
  let current: string[] = [];
  points.forEach((point, index) => {
    if (point.value === null) {
      if (current.length > 1) segments.push(current.join(" "));
      current = [];
      return;
    }
    current.push(`${current.length === 0 ? "M" : "L"}${x(index).toFixed(1)},${y(point.value).toFixed(1)}`);
  });
  if (current.length > 1) segments.push(current.join(" "));

  const meanPath = points
    .map((point, index) => (point.rolling_mean === null ? null : `${x(index).toFixed(1)},${y(point.rolling_mean).toFixed(1)}`))
    .filter((value): value is string => value !== null)
    .join(" L");

  const baselineY = baseline !== null ? y(baseline) : null;

  return (
    <figure className="w-full">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        preserveAspectRatio="none"
        role="img"
        aria-label={label}
        className="h-24 w-full"
      >
        {baselineY !== null ? (
          <line
            x1={0}
            x2={width}
            y1={baselineY}
            y2={baselineY}
            stroke="var(--color-muted)"
            strokeWidth={1}
            strokeDasharray="2 3"
            opacity={0.5}
          />
        ) : null}
        {meanPath ? (
          <path d={`M${meanPath}`} fill="none" stroke="var(--color-muted)" strokeWidth={1.5} strokeDasharray="5 4" />
        ) : null}
        {segments.map((path) => (
          <path key={path} d={path} fill="none" stroke="var(--color-primary)" strokeWidth={2} strokeLinecap="round" />
        ))}
      </svg>
      <figcaption className="mt-1 flex justify-between text-[0.62rem] text-muted">
        <span>{points[0]?.date}</span>
        <span>
          {low.toFixed(1)} – {high.toFixed(1)}
        </span>
        <span>{points[points.length - 1]?.date}</span>
      </figcaption>
    </figure>
  );
}
