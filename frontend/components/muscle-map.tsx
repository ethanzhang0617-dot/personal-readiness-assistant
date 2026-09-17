import { cn } from "@/lib/utils";

/**
 * Muscle-focus visual.
 *
 * A project-owned abstract figure — not a downloaded asset — that highlights
 * the body regions today's recommendation actually trains. Regions that are not
 * visible from the front (back, hamstrings, glutes) are drawn as a soft
 * "posterior" shape behind the figure, and every training focus is also listed
 * as a chip so the meaning never depends on the drawing alone.
 */

type Region = "chest" | "shoulders" | "arms" | "core" | "quads" | "posterior";

const GROUP_REGIONS: Record<string, Region[]> = {
  chest: ["chest"],
  back: ["posterior"],
  lats: ["posterior"],
  shoulders: ["shoulders"],
  arms: ["arms"],
  biceps: ["arms"],
  triceps: ["arms"],
  core: ["core"],
  abs: ["core"],
  legs: ["quads", "posterior"],
  quads: ["quads"],
  hamstrings: ["posterior"],
  glutes: ["posterior"],
  "hamstrings / glutes": ["posterior"],
  "chest / triceps": ["chest", "arms"],
  "shoulders / arms": ["shoulders", "arms"],
  "back / biceps": ["posterior", "arms"],
};

function regionsFor(groups: string[]): Set<Region> {
  const found = new Set<Region>();
  for (const group of groups) {
    for (const region of GROUP_REGIONS[group.trim().toLowerCase()] ?? []) found.add(region);
  }
  return found;
}

export function MuscleMap({
  groups,
  className,
  compact = false,
}: {
  groups: string[];
  className?: string;
  compact?: boolean;
}) {
  const active = regionsFor(groups);
  const on = (region: Region) => active.has(region);

  const fill = (region: Region) => (on(region) ? "var(--accent-soft)" : "var(--surface-secondary)");
  const stroke = (region: Region) => (on(region) ? "var(--accent-primary)" : "var(--border-subtle)");
  const width = (region: Region) => (on(region) ? 1.6 : 1);

  return (
    <div className={cn("flex items-center gap-5", className)}>
      <svg
        viewBox="0 0 140 240"
        role="img"
        aria-label={
          groups.length
            ? `Muscle focus: ${groups.join(", ")}`
            : "No muscle focus recorded for today"
        }
        className={compact ? "h-32 w-auto" : "h-44 w-auto"}
      >
        {/* Posterior chain sits behind the figure. */}
        <rect
          x={40}
          y={42}
          width={60}
          height={116}
          rx={24}
          fill={on("posterior") ? "var(--accent-soft)" : "none"}
          stroke={on("posterior") ? "var(--accent-secondary)" : "var(--border-subtle)"}
          strokeWidth={1}
          strokeDasharray="5 5"
          opacity={0.9}
        />

        <circle cx={70} cy={22} r={14} fill={fill("core")} stroke={stroke("core")} strokeWidth={1} opacity={0.85} />

        <rect x={58} y={34} width={24} height={12} rx={5} fill={fill("core")} stroke={stroke("core")} strokeWidth={width("core")} />

        <circle cx={41} cy={54} r={12} fill={fill("shoulders")} stroke={stroke("shoulders")} strokeWidth={width("shoulders")} />
        <circle cx={99} cy={54} r={12} fill={fill("shoulders")} stroke={stroke("shoulders")} strokeWidth={width("shoulders")} />

        <rect x={49} y={44} width={42} height={30} rx={13} fill={fill("chest")} stroke={stroke("chest")} strokeWidth={width("chest")} />

        <rect x={21} y={62} width={18} height={54} rx={9} fill={fill("arms")} stroke={stroke("arms")} strokeWidth={width("arms")} />
        <rect x={101} y={62} width={18} height={54} rx={9} fill={fill("arms")} stroke={stroke("arms")} strokeWidth={width("arms")} />

        <rect x={52} y={80} width={36} height={36} rx={14} fill={fill("core")} stroke={stroke("core")} strokeWidth={width("core")} />

        <rect x={52} y={122} width={16} height={62} rx={8} fill={fill("quads")} stroke={stroke("quads")} strokeWidth={width("quads")} />
        <rect x={72} y={122} width={16} height={62} rx={8} fill={fill("quads")} stroke={stroke("quads")} strokeWidth={width("quads")} />
      </svg>

      {!compact && groups.length > 0 ? (
        <ul className="flex min-w-0 flex-wrap gap-1.5">
          {groups.map((group) => (
            <li
              key={group}
              className="rounded-full bg-accent-soft px-2.5 py-1 text-[0.72rem] font-medium text-accent"
            >
              {group}
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
