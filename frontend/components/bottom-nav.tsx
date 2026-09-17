"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { NAV_ITEMS, isActivePath } from "@/lib/nav";
import { cn } from "@/lib/utils";

/**
 * Mobile primary navigation, styled like a native tab bar: quiet inactive
 * items, one clear active item, a hairline top edge and a safe-area floor so
 * the iOS home indicator never overlaps a tap target.
 */
export function BottomNav() {
  const pathname = usePathname();
  return (
    <nav
      aria-label="Primary"
      className="fixed inset-x-0 bottom-0 z-40 divider bg-surface/92 backdrop-blur-xl md:hidden"
      style={{ paddingBottom: "max(env(safe-area-inset-bottom), 6px)", boxShadow: "var(--shadow-nav)" }}
    >
      <ul className="flex h-[3.75rem] items-stretch justify-between px-1.5">
        {NAV_ITEMS.map((item) => {
          const active = isActivePath(pathname, item.href);
          const Icon = item.icon;
          return (
            <li key={item.href} className="flex-1">
              <Link
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "flex h-full min-h-11 flex-col items-center justify-center gap-1 rounded-[var(--radius-control)] text-[0.66rem] transition-colors",
                  active ? "font-semibold text-accent" : "font-medium text-muted",
                )}
              >
                <span
                  className={cn(
                    "flex h-7 w-11 items-center justify-center rounded-full transition-colors",
                    active ? "bg-accent-soft" : "bg-transparent",
                  )}
                >
                  <Icon className={cn("h-[1.05rem] w-[1.05rem]", active && "stroke-[2.3]")} />
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
