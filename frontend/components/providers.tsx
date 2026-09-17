"use client";

import type { ReactNode } from "react";

import { ThemeProvider } from "@/components/theme-provider";
import { UserStateProvider } from "@/lib/state-provider";

/**
 * Client-side providers. The user's own data lives in this context and in
 * IndexedDB, never on the API server.
 */
export function Providers({ children }: { children: ReactNode }) {
  return (
    <ThemeProvider>
      <UserStateProvider>{children}</UserStateProvider>
    </ThemeProvider>
  );
}
