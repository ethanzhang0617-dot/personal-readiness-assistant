import { CircleAlert, Info, RefreshCw, WifiOff } from "lucide-react";
import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

interface StatePanelProps {
  tone?: "info" | "error" | "empty";
  title: string;
  body?: ReactNode;
  action?: ReactNode;
}

/** Shared loading / error / empty presentation so no page can fail silently. */
export function StatePanel({ tone = "info", title, body, action }: StatePanelProps) {
  const Icon = tone === "error" ? CircleAlert : tone === "empty" ? WifiOff : Info;
  return (
    <Card className="p-4">
      <div className="flex items-start gap-3">
        <Icon
          className={
            tone === "error"
              ? "mt-0.5 h-4 w-4 shrink-0 text-[var(--status-red)]"
              : "mt-0.5 h-4 w-4 shrink-0 text-muted"
          }
        />
        <div className="space-y-1">
          <p className="text-sm font-semibold">{title}</p>
          {body ? <div className="text-sm text-muted">{body}</div> : null}
          {action ? <div className="pt-2">{action}</div> : null}
        </div>
      </div>
    </Card>
  );
}

export function LoadingCard({ label }: { label: string }) {
  return (
    <Card className="flex items-center gap-3 p-4">
      <RefreshCw className="h-4 w-4 animate-spin text-muted" />
      <span className="text-sm text-muted">{label}</span>
    </Card>
  );
}

export function PrimaryAction({ label }: { label: string }) {
  return (
    <Button size="md" variant="secondary" disabled>
      {label}
    </Button>
  );
}
