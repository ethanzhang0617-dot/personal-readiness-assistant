"use client";

import Link from "next/link";
import { ArrowLeft, CircleCheck, Info, TriangleAlert } from "lucide-react";
import { useRef, useState } from "react";

import { PageHeader } from "@/components/page-header";
import { StatePanel } from "@/components/state-panel";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { api } from "@/lib/api";
import { useUserState } from "@/lib/state-provider";
import { cn } from "@/lib/utils";

const FUTURE_SOURCES = ["Apple Health", "Garmin", "WHOOP", "Oura"];

export function DataView() {
  const { ready, state, chat, exportState, importState, resetLocal, storageAvailable, busy } = useUserState();
  const fileInput = useRef<HTMLInputElement | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [aiConfigured, setAiConfigured] = useState<boolean | null>(null);

  useState(() => {
    api.health().then((result) => {
      if (result.ok) setAiConfigured(result.data.ai_credential_configured);
    });
  });

  if (!ready) {
    return <StatePanel title="Loading local data…" body="Reading this browser's stored data." />;
  }

  const exportBlob = async () => {
    const payload = exportState();
    if (!payload) {
      setError("There is no local data to export yet.");
      return;
    }
    const blob = new Blob([payload], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "personal-readiness-backup.json";
    anchor.click();
    URL.revokeObjectURL(url);
    setMessage("Backup downloaded. It contains only your own product data.");
  };

  const onFile = async (file: File | undefined) => {
    setMessage(null);
    setError(null);
    if (!file) return;
    const text = await file.text();
    const result = await importState(text);
    if (result.ok) setMessage(result.message ?? "Backup imported.");
    else setError(result.error ?? "The backup could not be imported.");
  };

  return (
    <div className="space-y-4">
      <Link
        href="/profile"
        className="inline-flex min-h-9 items-center gap-1.5 text-[0.72rem] text-muted transition-colors hover:text-foreground"
      >
        <ArrowLeft className="h-3.5 w-3.5" aria-hidden />
        Profile
      </Link>

      <PageHeader
        eyebrow="Data & Privacy"
        title="Your data in this browser"
        description="What is stored, where it goes, and what this prototype does not do."
      />

      {message ? <StatePanel tone="info" title="Done" body={message} /> : null}
      {error ? <StatePanel tone="error" title="Not possible" body={error} /> : null}

      <StatePanel
        tone={storageAvailable ? "info" : "error"}
        title={storageAvailable ? "Browser-local storage is active" : "Browser-local storage is unavailable"}
        body={
          storageAvailable
            ? "Check-ins, logged sessions, profile edits and Coach messages are stored in this browser's IndexedDB on this device."
            : "This browser (or private mode) is blocking local storage, so changes will not survive a reload. Clearing site data or private browsing removes everything."
        }
      />

      <Card className="space-y-2 p-4">
        <p className="eyebrow text-muted">Data sources</p>
        <ul className="space-y-2 text-sm">
          <li className="flex items-start gap-2">
            <CircleCheck className="mt-0.5 h-4 w-4 shrink-0 text-muted" aria-hidden />
            Morning check-in: HRV (RMSSD), resting heart rate, sleep duration and quality, fatigue, soreness, stress,
            motivation, local soreness and the safety screen.
          </li>
          <li className="flex items-start gap-2">
            <CircleCheck className="mt-0.5 h-4 w-4 shrink-0 text-muted" aria-hidden />
            Completed sessions: duration, session RPE, muscles and actual working sets.
          </li>
          <li className="flex items-start gap-2">
            <CircleCheck className="mt-0.5 h-4 w-4 shrink-0 text-muted" aria-hidden />
            Seeded demo history: the fixed simulated profiles used for the product demo.
          </li>
        </ul>
        <p className="pt-1 text-[0.68rem] text-muted">Future sources — not connected in this version:</p>
        <ul className="flex flex-wrap gap-2">
          {FUTURE_SOURCES.map((source) => (
            <li
              key={source}
              className="rounded-full border border-subtle bg-surface-muted px-2.5 py-1 text-[0.68rem] text-muted"
            >
              {source} · not connected
            </li>
          ))}
        </ul>
        <p className="text-[0.68rem] text-muted">
          There is no wearable integration and no remote personal-history database. The API computes from the state
          sent with each request and stores nothing.
        </p>
      </Card>

      <Card className="space-y-2 p-4">
        <p className="eyebrow text-muted">AI and privacy</p>
        <p className="text-sm text-muted">
          Personal factual questions are answered from your recorded data with no provider call. When you ask an
          explanation question, a summarised context and your recent Coach messages are sent to the configured AI
          provider — not your full history, not this browser backup, and not another profile&apos;s data.
        </p>
        <p className="text-[0.68rem] text-muted">
          The provider credential is held by the API server
          {aiConfigured === null ? "" : aiConfigured ? " (configured)" : " (not configured: deterministic answers only)"}
          . It is never sent to this browser.
        </p>
      </Card>

      <Card className="space-y-3 p-4">
        <p className="eyebrow text-muted">Export, import and clear</p>
        <p className="text-[0.68rem] text-muted">
          Local data does not follow you to another browser or device. Export a backup if the history matters.
        </p>
        <div className="grid gap-2 md:grid-cols-2">
          <Button variant="secondary" onClick={() => void exportBlob()} disabled={busy}>
            Export my data
          </Button>
          <Button variant="secondary" onClick={() => fileInput.current?.click()} disabled={busy}>
            Import backup
          </Button>
        </div>
        <input
          ref={fileInput}
          type="file"
          accept="application/json"
          className="hidden"
          onChange={(event) => void onFile(event.target.files?.[0])}
        />
        <p className="text-[0.68rem] text-muted">
          Stored locally: {state ? state.daily_history.length : 0} check-in rows ·{" "}
          {state ? state.training_history.length : 0} logged sessions · {chat.length} Coach messages.
        </p>
        <Button
          variant="secondary"
          disabled={busy}
          onClick={async () => {
            const result = await resetLocal();
            setMessage(result.ok ? result.message ?? "Reset complete." : null);
            setError(result.ok ? null : result.error ?? "Reset failed.");
          }}
        >
          Clear local data and reset
        </Button>
      </Card>

      <Card className="space-y-2 p-4">
        <p className="eyebrow text-muted">About this prototype</p>
        <p className="text-sm text-muted">
          Personal Readiness Assistant is an evidence-informed decision-support prototype for strength training. It
          answers how ready you are today, what to train, how hard, and why — with a deterministic Decision Trace.
          Readiness thresholds, aggregation rules, comparison windows and RIR ranges are documented product heuristics
          that have not been prospectively validated as clinical or performance-prediction thresholds.
        </p>
        <p className="flex items-start gap-2 text-[0.68rem] leading-relaxed text-muted">
          <TriangleAlert className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
          Not a medical device, diagnosis, fatigue prediction or injury prediction tool.
        </p>
        <Link href="/profile/science" className={cn(buttonVariants({ variant: "secondary", size: "sm" }))}>
          Read the evidence boundaries and references
        </Link>
      </Card>

      <p className="flex items-start gap-2 text-[0.68rem] leading-relaxed text-muted">
        <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
        This is the Next.js client of the V1.2 migration. The Streamlit V1.1 app remains available as the reference
        implementation during the migration.
      </p>
    </div>
  );
}
