import { cva, type VariantProps } from "class-variance-authority";
import type { ButtonHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

/**
 * Buttons keep the product's colour contract: charcoal ink for primary actions
 * (which becomes warm white in dark mode), quiet surfaces for secondary
 * actions, and status colours reserved for status.
 */
export const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-full text-[0.9rem] font-semibold transition-[background-color,color,transform,opacity] duration-150 active:scale-[0.985] disabled:pointer-events-none disabled:opacity-55",
  {
    variants: {
      variant: {
        primary: "bg-primary text-primary-foreground hover:opacity-92",
        secondary: "bg-surface-muted text-foreground hover:bg-accent-soft hover:text-accent",
        ghost: "text-secondary hover:bg-surface-muted hover:text-foreground",
        danger: "bg-[var(--status-red)] text-white hover:opacity-90",
      },
      size: {
        sm: "h-9 px-3.5 text-[0.82rem]",
        md: "h-11 px-4",
        lg: "h-13 px-5 text-[0.95rem] shadow-[var(--shadow-raised)]",
        icon: "h-11 w-11",
      },
    },
    defaultVariants: { variant: "primary", size: "md" },
  },
);

export interface ButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

export function Button({ className, variant, size, ...props }: ButtonProps) {
  return <button className={cn(buttonVariants({ variant, size }), className)} {...props} />;
}
