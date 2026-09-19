import type { ReactNode } from "react";

import { BottomNav } from "@/components/bottom-nav";
import { SideNav } from "@/components/side-nav";

/**
 * Application shell.
 *
 * Compact app header, content column, native-style bottom bar on phones and a
 * quiet sidebar on desktop. The bottom padding clears the fixed bar plus the
 * iOS safe area so nothing can collide with navigation.
 */
export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-dvh bg-background">
      <SideNav />
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex h-12 items-center justify-between gap-3 border-b border-subtle bg-background/80 px-4 backdrop-blur-xl md:h-14 md:px-10">
          <span className="text-[0.8rem] font-semibold tracking-tight text-foreground md:hidden">
            Personal Readiness
          </span>
          <span className="hidden md:block" aria-hidden />
          <span className="text-[0.66rem] font-medium tracking-[0.08em] text-muted">V1.4</span>
        </header>
        <main className="mx-auto w-full max-w-[44rem] flex-1 px-4 pb-[calc(env(safe-area-inset-bottom)+6rem)] pt-4 md:max-w-[62rem] md:px-10 md:pb-20 md:pt-10">
          {children}
        </main>
      </div>
      <BottomNav />
    </div>
  );
}
