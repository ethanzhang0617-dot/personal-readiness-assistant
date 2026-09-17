"use client";

import { useEffect, useState } from "react";

import { statusHeadline, statusVar } from "@/lib/format";
import { cn } from "@/lib/utils";

/**
 * Readiness ring: one number, one status, one quiet arc.
 *
 * The arc animates in once (respecting reduced motion) and the colour is the
 * product's own status colour, so the ring means the same thing in both themes.
 * There is no glow, no gradient and no gauge chrome.
 */
export function ReadinessRing({
  index,
  max = 100,
  status,
  caption = "Readiness",
  size = 208,
  className,
}: {
  index: number | null;
  max?: number;
  status: string;
  caption?: string;
  size?: number;
  className?: string;
}) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    const frame = window.requestAnimationFrame(() => setMounted(true));
    return () => window.cancelAnimationFrame(frame);
  }, []);

  const stroke = Math.max(8, Math.round(size * 0.048));
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const ratio = index === null ? 0 : Math.max(0, Math.min(index / (max || 100), 1));
  const progress = mounted ? ratio : 0;

  return (
    <div className={cn("relative inline-flex items-center justify-center", className)} style={{ width: size, height: size }}>
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        role="img"
        aria-label={
          index === null
            ? `${caption}: not available today`
            : `${caption} ${index} out of ${max}. ${statusHeadline(status)}.`
        }
        className="-rotate-90"
      >
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="var(--ring-track)"
          strokeWidth={stroke}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={statusVar(status)}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={circumference * (1 - progress)}
          style={{ transition: "stroke-dashoffset 900ms cubic-bezier(0.22, 0.61, 0.36, 1)" }}
        />
      </svg>

      <div className="absolute inset-0 flex flex-col items-center justify-center gap-1">
        <span className="display-hero text-foreground">{index ?? "—"}</span>
        <span className="text-[0.72rem] font-semibold tracking-[0.08em] text-muted uppercase">{caption}</span>
        <span className="text-[0.8rem] font-semibold" style={{ color: statusVar(status) }}>
          {statusHeadline(status)}
        </span>
      </div>
    </div>
  );
}
