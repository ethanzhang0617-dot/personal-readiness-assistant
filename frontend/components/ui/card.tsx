import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

/**
 * A surface. Used sparingly now: the redesign prefers open layout plus
 * separators, and reserves containers for the readiness hero, the primary
 * decision and genuinely grouped data.
 */
export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("surface", className)} {...props} />;
}

export function CardHeader({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("flex flex-col gap-1 p-5 pb-2", className)} {...props} />;
}

export function CardTitle({ className, ...props }: HTMLAttributes<HTMLHeadingElement>) {
  return <h2 className={cn("title-section", className)} {...props} />;
}

export function CardDescription({ className, ...props }: HTMLAttributes<HTMLParagraphElement>) {
  return <p className={cn("text-[0.82rem] text-muted", className)} {...props} />;
}

export function CardContent({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("p-5 pt-2", className)} {...props} />;
}

export function CardFooter({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("flex items-center gap-2 p-5 pt-0", className)} {...props} />;
}
