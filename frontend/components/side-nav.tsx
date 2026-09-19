"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { ThemeToggle } from "@/components/theme-toggle";
import { NAV_ITEMS, isActivePath } from "@/lib/nav";
import { cn } from "@/lib/utils";

/** Desktop navigation. Phones use the bottom bar instead. */
export function SideNav() {
  const pathname = usePathname();
  return (
    <aside className="hidden w-60 shrink-0 border-r border-subtle bg-surface md:flex md:flex-col">
      <div className="flex h-14 items-center gap-2.5 px-5">
        <span className="flex h-7 w-7 items-center justify-center rounded-[0.6rem] bg-primary text-[0.68rem] font-bold text-primary-foreground">
          AT
        </span>
        {/* Compact lockup: the full official title lives in About and the document metadata. */}
        <span className="min-w-0 leading-tight">
          <span className="block text-[0.8rem] font-semibold tracking-tight">Adaptive Training</span>
          <span className="block text-[0.66rem] font-medium text-muted">Decision System</span>
        </span>
      </div>
      <nav aria-label="Primary" className="flex flex-col gap-0.5 px-3 py-3">
        {NAV_ITEMS.map((item) => {
          const active = isActivePath(pathname, item.href);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={active ? "page" : undefined}
              className={cn(
                "flex h-10 items-center gap-3 rounded-[var(--radius-control)] px-3 text-[0.84rem] transition-colors",
                active
                  ? "bg-surface-muted font-semibold text-foreground"
                  : "font-medium text-muted hover:bg-surface-muted/70 hover:text-foreground",
              )}
            >
              <Icon className={cn("h-4 w-4", active && "text-accent")} />
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div className="mt-auto flex items-center justify-between gap-2 px-4 py-4">
        <span className="text-[0.66rem] font-medium tracking-[0.08em] text-muted">V1.4</span>
        <ThemeToggle />
      </div>
    </aside>
  );
}
