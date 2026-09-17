import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import type { ReactNode } from "react";

/**
 * Minimal page header: an optional back affordance, a small context label such
 * as the date, a short title and at most one line of description.
 */
export function PageHeader({
  eyebrow,
  title,
  description,
  back,
  actions,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  back?: { href: string; label: string };
  actions?: ReactNode;
}) {
  return (
    <div className="mb-5">
      {back ? (
        <Link
          href={back.href}
          className="mb-3 inline-flex min-h-9 items-center gap-1.5 text-[0.78rem] text-muted transition-colors hover:text-foreground"
        >
          <ArrowLeft className="h-3.5 w-3.5" aria-hidden />
          {back.label}
        </Link>
      ) : null}
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          {eyebrow ? <p className="eyebrow mb-1">{eyebrow}</p> : null}
          <h1 className="title-page">{title}</h1>
          {description ? <p className="mt-1.5 text-[0.84rem] leading-relaxed text-muted">{description}</p> : null}
        </div>
        {actions}
      </div>
    </div>
  );
}
