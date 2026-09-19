"use client";

import Link from "next/link";
import { ArrowLeft, CircleCheck, Info, TriangleAlert } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { PageHeader } from "@/components/page-header";
import { StatePanel } from "@/components/state-panel";
import { Button } from "@/components/ui/button";
import { Section } from "@/components/ui/section";
import { api } from "@/lib/api";
import { useUserState } from "@/lib/state-provider";
import type { UserState } from "@/types/api";

const FUTURE_SOURCES = ["Apple Health", "Garmin", "WHOOP", "Oura"];

interface ImportCandidate {
  fileName: string;
  raw: string;
  profiles: number;
  checkIns: number;
  sessions: number;
  messages: number;
}

function summarise(raw: string, fileName: string): ImportCandidate | { error: string } {
  let parsed: { states?: Record<string, UserState>; chats?: Record<string, unknown[]>; state?: UserState };
  try {
    parsed = JSON.parse(raw);
  } catch {
    return { error: "That file is not valid JSON." };
  }
  const states = parsed.states ?? (parsed.state ? { [parsed.state.profile_id]: parsed.state } : null);
  if (!states || Object.keys(states).length === 0) {
    return { error: "This file does not contain data from this app." };
  }
  const profileStates = Object.values(states);
  return {
    fileName,
    raw,
    profiles: profileStates.length,
    checkIns: profileStates.reduce((total, item) => total + (item.daily_history?.length ?? 0), 0),
    sessions: profileStates.reduce((total, item) => total + (item.training_history?.length ?? 0), 0),
    messages: Object.values(parsed.chats ?? {}).reduce((total, thread) => total + (thread?.length ?? 0), 0),
  };
}

export function DataView() {
  const { ready, state, chat, exportState, importState, resetLocal, storageAvailable, busy } = useUserState();
  const fileInput = useRef<HTMLInputElement | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [aiConfigured, setAiConfigured] = useState<boolean | null>(null);
  const [candidate, setCandidate] = useState<ImportCandidate | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.health().then((result) => {
      if (!cancelled && result.ok) setAiConfigured(result.data.ai_credential_configured);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  if (!ready) {
    return <StatePanel title="Loading local data…" body="Reading this browser's stored data." />;
  }

  const exportBlob = () => {
    const payload = exportState();
    if (!payload) {
      setError("There is no local data to export yet.");
      return;
    }
    const url = URL.createObjectURL(new Blob([payload], { type: "application/json" }));
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
    setCandidate(null);
    if (!file) return;
    const summary = summarise(await file.text(), file.name);
    if ("error" in summary) setError(summary.error);
    else setCandidate(summary);
  };

  const confirmImport = async () => {
    if (!candidate) return;
    const result = await importState(candidate.raw);
    setCandidate(null);
    if (result.ok) setMessage(result.message ?? "Backup imported.");
    else setError(result.error ?? "The backup could not be imported.");
  };

  return (
    <div className="space-y-5">
      <Link
        href="/profile"
        className="inline-flex min-h-11 items-center gap-1.5 text-[0.75rem] text-muted transition-colors hover:text-foreground md:min-h-9"
      >
        <ArrowLeft className="h-3.5 w-3.5" aria-hidden />
        Profile
      </Link>

      <PageHeader
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

      <Section title="What the product reads" divided={false}>
        <ul className="space-y-2 text-[0.82rem]">
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
            Seeded demo history for the fixed simulated profiles.
          </li>
        </ul>
        <p className="mt-3 text-[0.7rem] font-medium text-muted">Future sources — not connected in this version</p>
        <ul className="mt-1.5 flex flex-wrap gap-2">
          {FUTURE_SOURCES.map((source) => (
            <li key={source} className="rounded-full bg-surface-muted px-2.5 py-1 text-[0.7rem] text-muted">
              {source} · not connected
            </li>
          ))}
        </ul>
        <p className="mt-3 text-[0.7rem] leading-relaxed text-muted">
          There is no wearable integration and no remote personal-history database. The API computes from the state sent
          with each request and stores nothing.
        </p>
      </Section>

      <Section title="What leaves this device">
        <p className="text-[0.82rem] leading-relaxed text-muted">
          Personal factual questions are answered from your recorded data with no provider call. When you ask an
          explanation question, a summarised context and your recent Coach messages are sent to the configured AI
          provider — not your full history, not this browser backup, and not another profile&apos;s data.
        </p>
        <p className="mt-2 text-[0.7rem] text-muted">
          The provider credential is held by the API server
          {aiConfigured === null ? "" : aiConfigured ? " (configured)" : " (not configured: deterministic answers only)"}.
          It is never sent to this browser.
        </p>
      </Section>

      <Section
        title="Export, import and clear"
        description="Local data does not follow you to another browser or device. Export a backup if the history matters."
      >
        <div className="grid gap-2 sm:grid-cols-2">
          <Button variant="secondary" onClick={exportBlob} disabled={busy}>
            Export my data
          </Button>
          <Button variant="secondary" onClick={() => fileInput.current?.click()} disabled={busy}>
            Choose backup file
          </Button>
        </div>
        <input
          ref={fileInput}
          type="file"
          accept="application/json"
          className="hidden"
          onChange={(event) => void onFile(event.target.files?.[0])}
        />

        {candidate ? (
          <div className="surface-flat mt-3 space-y-3 p-4">
            <div>
              <p className="text-[0.82rem] font-semibold">{candidate.fileName}</p>
              <p className="mt-0.5 text-[0.72rem] text-muted">
                Valid backup · {candidate.profiles} profile{candidate.profiles === 1 ? "" : "s"} ·{" "}
                {candidate.checkIns} check-ins · {candidate.sessions} sessions · {candidate.messages} messages
              </p>
            </div>
            <p className="flex items-start gap-2 text-[0.72rem] text-[var(--status-amber)]">
              <TriangleAlert className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
              Importing replaces the training data currently stored in this browser. Export first if you want
              to keep it.
            </p>
            <div className="flex gap-2">
              <Button variant="secondary" size="sm" onClick={() => setCandidate(null)}>
                Cancel
              </Button>
              <Button variant="danger" size="sm" disabled={busy} onClick={() => void confirmImport()}>
                Replace local data
              </Button>
            </div>
          </div>
        ) : null}

        <p className="mt-3 text-[0.7rem] text-muted">
          Stored locally: {state ? state.daily_history.length : 0} check-in rows ·{" "}
          {state ? state.training_history.length : 0} logged sessions · {chat.length} Coach messages.
        </p>
        <Button
          variant="secondary"
          className="mt-2"
          disabled={busy}
          onClick={async () => {
            const result = await resetLocal();
            setMessage(result.ok ? result.message ?? "Reset complete." : null);
            setError(result.ok ? null : result.error ?? "Reset failed.");
          }}
        >
          Clear local data and reset
        </Button>
      </Section>

      <p className="flex items-start gap-2 text-[0.7rem] leading-relaxed text-muted">
        <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
        Your check-ins, logged sessions, profile edits and Coach history stay in this browser. Nothing is written to a
        server database.
      </p>
    </div>
  );
}
