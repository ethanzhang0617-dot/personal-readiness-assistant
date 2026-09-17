import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

/**
 * Section: the default grouping for information on a page.
 *
 * A short heading, an optional single-line description and a separator. Most
 * blocks are open layout rather than boxes.
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
    <section className={cn(divided && "divider pt-6", className)}>
      {eyebrow || title || action ? (
        <header className="mb-3 flex items-end justify-between gap-3">
          <div className="min-w-0">
            {eyebrow ? <p className="eyebrow mb-1">{eyebrow}</p> : null}
            {title ? <h2 className="title-section">{title}</h2> : null}
          </div>
          {action ? <div className="shrink-0">{action}</div> : null}
        </header>
      ) : null}
      {description ? <p className="mb-3 text-[0.82rem] leading-relaxed text-muted">{description}</p> : null}
      {children}
    </section>
  );
}
