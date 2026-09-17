import { CircleAlert, Info, WifiOff } from "lucide-react";
import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

interface StatePanelProps {
  tone?: "info" | "error" | "empty";
  title: string;
  body?: ReactNode;
  action?: ReactNode;
  className?: string;
}

/**
 * Shared loading / error / empty presentation so no page can fail silently.
 * Human-readable only: never JSON, a stack trace or a raw HTTP message.
 */
export function StatePanel({ tone = "info", title, body, action, className }: StatePanelProps) {
  const Icon = tone === "error" ? CircleAlert : tone === "empty" ? WifiOff : Info;
  return (
    <div
      className={cn(
        "surface-flat px-4 py-4",
        tone === "error" && "border border-[var(--status-red-line)]",
        className,
      )}
    >
      <div className="flex items-start gap-3">
        <Icon
          className={cn(
            "mt-0.5 h-4 w-4 shrink-0",
            tone === "error" ? "text-[var(--status-red)]" : "text-muted",
          )}
          aria-hidden
        />
        <div className="min-w-0 space-y-1">
          <p className="text-[0.88rem] font-semibold">{title}</p>
          {body ? <div className="text-[0.82rem] leading-relaxed text-muted">{body}</div> : null}
          {action ? <div className="pt-2">{action}</div> : null}
        </div>
      </div>
    </div>
  );
}
