"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { NAV_ITEMS, isActivePath } from "@/lib/nav";
import { cn } from "@/lib/utils";

/** Desktop navigation. Mobile uses the bottom bar instead. */
export function SideNav() {
  const pathname = usePathname();
  return (
    <aside className="hidden w-64 shrink-0 border-r border-subtle bg-surface md:flex md:flex-col">
      <div className="flex h-16 items-center gap-2 border-b border-subtle px-5">
        <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary text-[0.7rem] font-bold text-primary-foreground">
          PR
        </span>
        <span className="text-sm font-semibold tracking-tight">Personal Readiness</span>
      </div>
      <nav aria-label="Primary" className="flex flex-col gap-1 p-3">
        {NAV_ITEMS.map((item) => {
          const active = isActivePath(pathname, item.href);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={active ? "page" : undefined}
              className={cn(
                "flex h-11 items-center gap-3 rounded-[var(--radius-control)] px-3 text-sm transition-colors",
                active ? "bg-subtle font-semibold text-foreground" : "font-medium text-muted hover:bg-surface-muted hover:text-foreground",
              )}
            >
              <Icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div className="mt-auto space-y-1 p-4 text-[0.7rem] leading-relaxed text-muted">
        <p>V1.2 migration preview.</p>
        <p>The Streamlit V1.1 app remains the reference implementation.</p>
      </div>
    </aside>
  );
}
