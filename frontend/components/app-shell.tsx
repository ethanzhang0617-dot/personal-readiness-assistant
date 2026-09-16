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
        <header className="sticky top-0 z-30 flex h-12 items-center justify-between border-b border-subtle bg-background/85 px-4 backdrop-blur md:h-14 md:px-8">
          <span className="text-[0.78rem] font-semibold tracking-tight text-foreground md:hidden">
            Personal Readiness Assistant
          </span>
          <span className="hidden text-[0.72rem] text-muted md:inline">
            Deterministic engines · DeepSeek explanations · Product heuristics disclosed
          </span>
          <span className="text-[0.72rem] font-medium text-muted md:hidden">V1.2</span>
        </header>
        <main className="mx-auto w-full max-w-[46rem] flex-1 px-4 pb-[calc(env(safe-area-inset-bottom)+5.75rem)] pt-4 md:max-w-[58rem] md:px-8 md:pb-16 md:pt-10">
          {children}
        </main>
      </div>
      <BottomNav />
    </div>
  );
}
