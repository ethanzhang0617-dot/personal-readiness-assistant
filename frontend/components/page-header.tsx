import type { ReactNode } from "react";

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow: string;
  title: string;
  description?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="mb-4 flex items-start justify-between gap-3">
      <div className="space-y-1">
        <p className="eyebrow text-muted">{eyebrow}</p>
        <h1 className="text-[1.5rem] font-semibold tracking-tight md:text-[1.75rem]">{title}</h1>
        {description ? <p className="text-sm text-muted">{description}</p> : null}
      </div>
      {actions}
    </div>
  );
}
