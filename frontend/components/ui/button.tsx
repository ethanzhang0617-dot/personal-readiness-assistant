import { cva, type VariantProps } from "class-variance-authority";
import type { ButtonHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

/**
 * shadcn/ui-style button. Variants keep the V1.1 colour contract: charcoal for
 * ordinary primary actions, status colours reserved for status, red never a CTA.
 */
export const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-[var(--radius-control)] text-sm font-semibold transition-[background-color,transform,opacity] duration-150 active:scale-[0.99] disabled:pointer-events-none disabled:opacity-55",
  {
    variants: {
      variant: {
        primary: "bg-primary text-primary-foreground hover:bg-primary/92",
        secondary: "border border-subtle bg-surface text-foreground hover:border-primary/25 hover:bg-surface-muted",
        ghost: "text-foreground hover:bg-surface-muted",
        danger: "bg-[var(--status-red)] text-white hover:opacity-90",
      },
      size: {
        sm: "h-10 px-3.5",
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
