import type { Metadata, Viewport } from "next";

import { AppShell } from "@/components/app-shell";
import { Providers } from "@/components/providers";
import { THEME_INIT_SCRIPT } from "@/lib/theme";

import "./globals.css";

export const metadata: Metadata = {
  title: "Personal Readiness Assistant",
  description:
    "Readiness-aware strength training decision assistant: what to train today, how hard, and why.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f6f4ef" },
    { media: "(prefers-color-scheme: dark)", color: "#0e1215" },
  ],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        {/* Applied before first paint so neither theme flashes. */}
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
      </head>
      <body>
        <Providers>
          <AppShell>{children}</AppShell>
        </Providers>
      </body>
    </html>
  );
}
