import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

/**
 * Section: the default grouping for information on a page.
 *
 * The product is deliberately not a wall of bordered cards, so most blocks use a
 * divider plus typographic hierarchy instead of a box. `Card` is reserved for
 * surfaces that carry real meaning (the readiness hero, the primary decision).
 */
export function Section({
  eyebrow,
  title,
  description,
  action,
  children,
  className,
  divided = true,
}: {
  eyebrow?: string;
  title?: string;
  description?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
  divided?: boolean;
}) {
  return (
    <section className={cn(divided && "divider pt-5", className)}>
      {eyebrow || title || action ? (
        <header className="mb-3 flex items-end justify-between gap-3">
          <div className="min-w-0">
            {eyebrow ? <p className="eyebrow">{eyebrow}</p> : null}
            {title ? <h2 className="title-section mt-1">{title}</h2> : null}
          </div>
          {action ? <div className="shrink-0">{action}</div> : null}
        </header>
      ) : null}
      {description ? <p className="mb-3 text-sm leading-relaxed text-muted">{description}</p> : null}
      {children}
    </section>
  );
}
