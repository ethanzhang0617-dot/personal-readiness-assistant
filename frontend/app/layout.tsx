import type { Metadata, Viewport } from "next";

import { AppShell } from "@/components/app-shell";
import { Providers } from "@/components/providers";
import { THEME_INIT_SCRIPT } from "@/lib/theme";

import "./globals.css";

export const metadata: Metadata = {
  title: "Adaptive Training Decision System",
  description:
    "An agentic sports-science training decision system that combines readiness, training history, personal response, "
    + "deterministic decision engines and a tool-using AI Agent into grounded adaptive training guidance.",
  applicationName: "Adaptive Training Decision System",
  openGraph: {
    title: "Adaptive Training Decision System",
    description:
      "An agentic sports-science training decision system: deterministic readiness and training engines plus a "
      + "tool-using AI Agent that explains what to train, how hard and why.",
    type: "website",
  },
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
