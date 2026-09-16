import { cva, type VariantProps } from "class-variance-authority";
import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[0.7rem] font-semibold tracking-wide",
  {
    variants: {
      variant: {
        neutral: "border-subtle bg-surface-muted text-muted",
        primary: "border-transparent bg-primary text-primary-foreground",
        green: "border-[var(--status-green-line)] bg-[var(--status-green-soft)] text-[var(--status-green)]",
        amber: "border-[var(--status-amber-line)] bg-[var(--status-amber-soft)] text-[var(--status-amber)]",
        red: "border-[var(--status-red-line)] bg-[var(--status-red-soft)] text-[var(--status-red)]",
      },
    },
    defaultVariants: { variant: "neutral" },
  },
);

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement>, VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}
