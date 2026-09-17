import { cva, type VariantProps } from "class-variance-authority";
import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[0.72rem] font-semibold tracking-wide",
  {
    variants: {
      variant: {
        neutral: "bg-surface-muted text-secondary",
        accent: "bg-accent-soft text-accent",
        primary: "bg-primary text-primary-foreground",
        green: "bg-[var(--status-green-soft)] text-[var(--status-green)]",
        amber: "bg-[var(--status-amber-soft)] text-[var(--status-amber)]",
        red: "bg-[var(--status-red-soft)] text-[var(--status-red)]",
      },
    },
    defaultVariants: { variant: "neutral" },
  },
);

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement>, VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}
