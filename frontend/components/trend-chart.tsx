"use client";

import { useRef, useState } from "react";

import { formatShortDate } from "@/lib/format";
import type { InsightPoint } from "@/types/api";

// Dependency-free responsive trend chart. Missing values break the line instead
// of dropping to zero, a dashed line shows the 7-check-in mean, a dotted line
// shows the personal baseline, and hovering or tapping reveals the exact value.

const WIDTH = 320;
const HEIGHT = 120;
const PAD_LEFT = 30;
const PAD_RIGHT = 6;
const PAD_TOP = 8;
const PAD_BOTTOM = 6;

interface TrendChartProps {
  points: InsightPoint[];
  baseline?: number | null;
  unit?: string;
  label: string;
}

export function TrendChart({ points, baseline = null, unit = "", label }: TrendChartProps) {
  const [active, setActive] = useState<number | null>(null);
  const frame = useRef<HTMLDivElement | null>(null);

  const values = points.map((point) => point.value).filter((value): value is number => value !== null);
  const means = points.map((point) => point.rolling_mean).filter((value): value is number => value !== null);

  if (values.length < 2) {
    return (
      <div className="flex h-28 items-center justify-center rounded-[var(--radius-control)] bg-surface-muted text-[0.78rem] text-muted">
        Not enough recorded data yet — check in for a few more days.
      </div>
    );
  }

  const pool = [...values, ...means, ...(baseline !== null ? [baseline] : [])];
  const low = Math.min(...pool);
  const high = Math.max(...pool);
  const span = high - low || 1;
  const min = low - span * 0.12;
  const max = high + span * 0.12;
  const innerWidth = WIDTH - PAD_LEFT - PAD_RIGHT;
  const innerHeight = HEIGHT - PAD_TOP - PAD_BOTTOM;
  const x = (index: number) => PAD_LEFT + (points.length === 1 ? 0 : (index / (points.length - 1)) * innerWidth);
  const y = (value: number) => PAD_TOP + innerHeight - ((value - min) / (max - min)) * innerHeight;

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
    .map((point, index) =>
      point.rolling_mean === null ? null : `${x(index).toFixed(1)},${y(point.rolling_mean).toFixed(1)}`,
    )
    .filter((value): value is string => value !== null)
    .join(" L");

  const ticks = [max, (max + min) / 2, min];
  const shown = active !== null ? points[active] : points[points.length - 1];
  const shownValue = shown?.value ?? null;

  const move = (clientX: number) => {
    const box = frame.current?.getBoundingClientRect();
    if (!box) return;
    const ratio = Math.min(Math.max((clientX - box.left) / box.width, 0), 1);
    const svgX = ratio * WIDTH;
    const index = Math.round(((svgX - PAD_LEFT) / innerWidth) * (points.length - 1));
    setActive(Math.min(Math.max(index, 0), points.length - 1));
  };

  return (
    <figure className="w-full">
      <div
        ref={frame}
        className="relative"
        onMouseMove={(event) => move(event.clientX)}
        onMouseLeave={() => setActive(null)}
        onTouchStart={(event) => move(event.touches[0].clientX)}
        onTouchMove={(event) => move(event.touches[0].clientX)}
        onTouchEnd={() => setActive(null)}
      >
        <svg
          viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
          preserveAspectRatio="none"
          role="img"
          aria-label={`${label}: latest ${shownValue ?? "no"} ${unit}. Trend over ${points.length} check-ins.`}
          className="h-28 w-full"
        >
          {ticks.map((tick, index) => (
            <g key={tick + index}>
              <line
                x1={PAD_LEFT}
                x2={WIDTH - PAD_RIGHT}
                y1={y(tick)}
                y2={y(tick)}
                stroke="var(--chart-grid)"
                strokeWidth={1}
              />
              <text x={0} y={y(tick) + 3} fontSize={9} fill="var(--text-muted)">
                {tick.toFixed(tick >= 100 ? 0 : 1)}
              </text>
            </g>
          ))}

          {baseline !== null ? (
            <line
              x1={PAD_LEFT}
              x2={WIDTH - PAD_RIGHT}
              y1={y(baseline)}
              y2={y(baseline)}
              stroke="var(--chart-baseline)"
              strokeWidth={1}
              strokeDasharray="2 3"
              opacity={0.55}
            />
          ) : null}

          {meanPath ? (
            <path d={`M${meanPath}`} fill="none" stroke="var(--chart-mean)" strokeWidth={1.5} strokeDasharray="5 4" />
          ) : null}

          {segments.map((path) => (
            <path key={path} d={path} fill="none" stroke="var(--chart-line)" strokeWidth={2} strokeLinecap="round" />
          ))}

          {active !== null && shown?.value !== null && shown?.value !== undefined ? (
            <>
              <line
                x1={x(active)}
                x2={x(active)}
                y1={PAD_TOP}
                y2={HEIGHT - PAD_BOTTOM}
                stroke="var(--chart-mean)"
                strokeWidth={1}
                opacity={0.5}
              />
              <circle cx={x(active)} cy={y(shown.value)} r={3.5} fill="var(--chart-line)" />
            </>
          ) : null}
        </svg>

        <div className="mt-1.5 flex items-center justify-between text-[0.68rem] text-muted">
          <span>{formatShortDate(points[0]?.date)}</span>
          <span aria-live="polite">
            {shown ? (
              <span className="font-medium text-foreground">
                {formatShortDate(shown.date)}
                {" · "}
                {shown.value === null ? "no record" : `${shown.value}${unit ? ` ${unit}` : ""}`}
              </span>
            ) : null}
          </span>
          <span>{formatShortDate(points[points.length - 1]?.date)}</span>
        </div>
      </div>
      <figcaption className="mt-1 text-[0.64rem] text-muted">
        Solid: recorded value · dashed: 7-check-in mean{baseline !== null ? " · dotted: your baseline" : ""}
      </figcaption>
    </figure>
  );
}
