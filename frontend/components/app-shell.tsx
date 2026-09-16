import type { ReactNode } from "react";

import { BottomNav } from "@/components/bottom-nav";
import { SideNav } from "@/components/side-nav";

/**
 * Application shell: content column first, navigation adapted per viewport.
 * The bottom padding clears the fixed mobile bar plus the iOS safe area.
 */
export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-dvh bg-background">
      <SideNav />
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex h-12 items-center justify-between border-b border-subtle bg-background/90 px-4 backdrop-blur md:h-16 md:px-8">
          <span className="eyebrow text-muted">Personal Readiness Assistant</span>
          <span className="hidden text-[0.7rem] text-muted md:inline">
            Deterministic engines · DeepSeek explanations · Product heuristics disclosed
          </span>
        </header>
        <main className="mx-auto w-full max-w-[46rem] flex-1 px-4 pb-[calc(env(safe-area-inset-bottom)+5.5rem)] pt-3 md:max-w-[54rem] md:px-8 md:pb-12 md:pt-8">
          {children}
        </main>
      </div>
      <BottomNav />
    </div>
  );
}
