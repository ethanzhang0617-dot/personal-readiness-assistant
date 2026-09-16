"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { NAV_ITEMS, isActivePath } from "@/lib/nav";
import { cn } from "@/lib/utils";

/**
 * Mobile primary navigation. Fixed to the viewport bottom, 44px+ targets and a
 * safe-area floor so iOS home indicators never overlap a tap target.
 */
export function BottomNav() {
  const pathname = usePathname();
  return (
    <nav
      aria-label="Primary"
      className="fixed inset-x-0 bottom-0 z-40 border-t border-subtle bg-surface/95 backdrop-blur md:hidden"
      style={{ paddingBottom: "max(env(safe-area-inset-bottom), 8px)" }}
    >
      <ul className="flex h-16 items-stretch justify-between px-1">
        {NAV_ITEMS.map((item) => {
          const active = isActivePath(pathname, item.href);
          const Icon = item.icon;
          return (
            <li key={item.href} className="flex-1">
              <Link
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "flex h-full min-h-11 flex-col items-center justify-center gap-1 rounded-[var(--radius-control)] text-[0.72rem] font-medium transition-colors",
                  active ? "text-foreground" : "text-muted",
                )}
              >
                <span
                  className={cn(
                    "flex h-7 w-12 items-center justify-center rounded-full transition-colors",
                    active ? "bg-muted-soft" : "bg-transparent",
                  )}
                >
                  <Icon className={cn("h-[1.15rem] w-[1.15rem]", active && "stroke-[2.4]")} />
                </span>
                {item.label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
