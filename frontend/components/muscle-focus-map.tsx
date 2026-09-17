"use client";

import { useEffect, useRef, useState } from "react";
import { MuscleMap } from "@musclemap/react";
import type { MuscleGroup, MuscleMapValues } from "@musclemap/core";

import { useTheme } from "@/components/theme-provider";
import { cn } from "@/lib/utils";

// Muscle focus visual — realistic anatomical body.
//
// The body, the traced muscle surfaces and the reference photographs all come
// from Jsplice/MuscleMap (MIT). This file is a display adapter: it maps the
// product's own training-focus vocabulary onto MuscleMap muscle groups and
// renders a photoreal hybrid (restrained grayscale body + highlighted targets).
// It reads the recommendation; it never decides what is trained.
//
// Attribution: see docs/THIRD_PARTY_NOTICES.md.

/**
 * Display adapter from the product's focus vocabulary to MuscleMap groups.
 * Unknown tokens are ignored, so an unmapped focus simply renders the body with
 * no highlight instead of failing.
 */
const TOKEN_GROUPS: Record<string, MuscleGroup[]> = {
  chest: ["CHEST"],
  back: ["LATS", "BACK_UPPER", "TRAPEZIUS"],
  lats: ["LATS"],
  "upper back": ["BACK_UPPER"],
  traps: ["TRAPEZIUS"],
  biceps: ["BICEPS"],
  triceps: ["TRICEPS"],
  arms: ["BICEPS", "TRICEPS"],
  forearms: ["FOREARMS"],
  shoulders: ["SHOULDERS_FRONT", "SHOULDERS_SIDE", "SHOULDERS_REAR"],
  delts: ["SHOULDERS_FRONT", "SHOULDERS_SIDE", "SHOULDERS_REAR"],
  core: ["CORE", "OBLIQUES"],
  abs: ["CORE"],
  abdominals: ["CORE"],
  obliques: ["OBLIQUES"],
  glutes: ["GLUTES"],
  quads: ["QUADS"],
  quadriceps: ["QUADS"],
  hamstrings: ["HAMSTRINGS"],
  calves: ["CALVES"],
  adductors: ["ADDUCTORS"],
  abductors: ["ABDUCTORS"],
  "hip flexors": ["HIP_FLEXORS"],
  // Session-level focus names, expanded to their muscle groups.
  push: ["CHEST", "SHOULDERS_FRONT", "SHOULDERS_SIDE", "TRICEPS"],
  pull: ["LATS", "BACK_UPPER", "BICEPS"],
  legs: ["QUADS", "HAMSTRINGS", "GLUTES", "CALVES"],
  "lower body": ["QUADS", "HAMSTRINGS", "GLUTES", "CALVES"],
  "upper body": ["CHEST", "LATS", "BACK_UPPER", "SHOULDERS_SIDE", "BICEPS", "TRICEPS"],
  "full body": ["CHEST", "LATS", "BACK_UPPER", "SHOULDERS_SIDE", "BICEPS", "TRICEPS", "QUADS", "HAMSTRINGS", "GLUTES"],
};

function tokensOf(groups: string[]): string[] {
  return groups
    .flatMap((group) => group.split(/[+/·,]| and /i))
    .map((token) => token.trim().toLowerCase())
    .filter(Boolean);
}

/** Muscle groups to highlight, plus the original tokens we could not map. */
export function mapFocusToMuscles(groups: string[]): { values: MuscleMapValues; unmapped: string[] } {
  const mapped = new Set<MuscleGroup>();
  const unmapped: string[] = [];
  for (const token of tokensOf(groups)) {
    const hit = TOKEN_GROUPS[token];
    if (hit) hit.forEach((group) => mapped.add(group));
    else unmapped.push(token);
  }
  const values: MuscleMapValues = {};
  for (const group of mapped) values[group] = { score: 100 };
  return { values, unmapped };
}

/** Localized labels so hover, focus and screen readers read naturally. */
const LABELS: Partial<Record<MuscleGroup, string>> = {
  CHEST: "Chest",
  BACK_UPPER: "Upper back",
  BACK_LOWER: "Lower back",
  TRAPEZIUS: "Trapezius",
  RHOMBOIDS: "Rhomboids",
  LATS: "Lats",
  SHOULDERS_FRONT: "Front deltoid",
  SHOULDERS_SIDE: "Side deltoid",
  SHOULDERS_REAR: "Rear deltoid",
  BICEPS: "Biceps",
  TRICEPS: "Triceps",
  FOREARMS: "Forearms",
  CORE: "Core",
  OBLIQUES: "Obliques",
  GLUTES: "Glutes",
  QUADS: "Quads",
  HAMSTRINGS: "Hamstrings",
  CALVES: "Calves",
};

const ACCENT = { light: "#0d7c93", dark: "#4ec8de" } as const;
const BASE = { light: "#c9ccce", dark: "#39424b" } as const;

/**
 * Body photographs: derived from the MIT-licensed reference photos bundled in
 * @musclemap/assets, desaturated and tone-mapped per theme so the photoreal
 * hybrid reads as a restrained grayscale body rather than a coloured heatmap.
 * Provenance and licence: docs/THIRD_PARTY_NOTICES.md.
 */
const BODY = {
  light: { front: "/musclemap/male-front-light.webp", back: "/musclemap/male-back-light.webp" },
  dark: { front: "/musclemap/male-front-dark.webp", back: "/musclemap/male-back-dark.webp" },
} as const;

export function MuscleFocusMap({ groups, className }: { groups: string[]; className?: string }) {
  const { resolved } = useTheme();
  const frame = useRef<HTMLDivElement | null>(null);
  const [available, setAvailable] = useState(0);

  useEffect(() => {
    const node = frame.current;
    if (!node) return;
    const measure = () => setAvailable(node.clientWidth);
    measure();
    if (typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(measure);
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  const { values, unmapped } = mapFocusToMuscles(groups);
  const highlighted = Object.keys(values).length > 0;

  // Front and back figures share the width, so the pair can never overflow.
  const gap = 16;
  const figureWidth = Math.max(112, Math.min(232, Math.floor(((available || 320) - gap) / 2)));
  const accent = ACCENT[resolved];

  const figure = (view: "FRONT" | "BACK") => (
    <div className="flex min-w-0 flex-1 flex-col items-center">
      <MuscleMap
        values={values}
        view={view}
        sex="MALE"
        figureWidth={figureWidth}
        showLegend={false}
        glow={highlighted}
        tooltipFields={["group"]}
        labels={LABELS}
        monochromeColor={accent}
        monochromeBaseColor={BASE[resolved]}
        backgroundImageFront={view === "FRONT" ? BODY[resolved].front : undefined}
        backgroundImageBack={view === "BACK" ? BODY[resolved].back : undefined}
        backgroundOpacity={1}
        style={{ color: "var(--text-primary)", gap: 0 }}
      />
      <p className="mt-1 text-[0.68rem] font-medium tracking-[0.06em] text-muted uppercase">{view.toLowerCase()}</p>
    </div>
  );

  return (
    <div className={cn("space-y-2", className)}>
      <div ref={frame} className="flex items-start justify-center" style={{ gap }}>
        {figure("FRONT")}
        {figure("BACK")}
      </div>

      {groups.length > 0 ? (
        <div className="flex flex-wrap justify-center gap-1.5">
          {groups.map((group) => (
            <span key={group} className="rounded-full bg-accent-soft px-2.5 py-1 text-[0.72rem] font-medium text-accent">
              {group}
            </span>
          ))}
        </div>
      ) : (
        <p className="text-center text-[0.74rem] text-muted">No muscle focus recorded for today.</p>
      )}

      {/* A focus this product supports but the anatomy map has no region for:
          the body still renders, and the wording stays honest. */}
      {unmapped.length > 0 ? (
        <p className="text-center text-[0.72rem] text-muted">No muscle region for: {unmapped.join(", ")}</p>
      ) : null}
    </div>
  );
}
