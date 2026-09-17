"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Segmented } from "@/components/ui/segmented";
import { COMPLETION_OPTIONS, DIFFICULTY_SCALE, PERFORMANCE_SCALE } from "@/lib/response";
import { useUserState } from "@/lib/state-provider";

// Lightweight post-session follow-up. It deliberately does not repeat session RPE:
// it captures perceived difficulty, performance feeling and how the session ended,
// which is what the response episode needs beyond the logged session itself.

export function PostSessionFeedback({
  sessionId,
  focus,
  onDone,
}: {
  sessionId: string;
  focus: string | null;
  onDone?: (message: string) => void;
}) {
  const { submitFeedback, busy } = useUserState();
  const [difficulty, setDifficulty] = useState(3);
  const [performance, setPerformance] = useState(3);
  const [completion, setCompletion] = useState<string>("Completed");
  const [note, setNote] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    setError(null);
    const result = await submitFeedback(sessionId, { difficulty, performance, completion, note });
    if (result.ok) {
      setMessage(result.message ?? "Response saved.");
      onDone?.(result.message ?? "Response saved.");
    } else {
      setError(result.error ?? "The feedback could not be saved.");
    }
  };

  if (message) {
    return (
      <p className="text-[0.8rem] leading-relaxed text-[var(--status-green)]">{message}</p>
    );
  }

  return (
    <div className="space-y-4">
      <div>
        <p className="text-[0.84rem] font-semibold">How did that session go?</p>
        <p className="mt-0.5 text-[0.72rem] text-muted">
          {focus ? `${focus} · ` : ""}Three quick answers. We compare them with your next check-in.
        </p>
      </div>

      <div className="space-y-3">
        <div>
          <p className="text-[0.78rem] font-medium">Perceived difficulty</p>
          <Segmented
            options={DIFFICULTY_SCALE}
            value={difficulty}
            size="sm"
            label="Perceived difficulty"
            className="mt-1.5"
            onChange={setDifficulty}
          />
        </div>
        <div>
          <p className="text-[0.78rem] font-medium">Performance feeling</p>
          <Segmented
            options={PERFORMANCE_SCALE}
            value={performance}
            size="sm"
            label="Performance feeling"
            className="mt-1.5"
            onChange={setPerformance}
          />
        </div>
        <div>
          <p className="text-[0.78rem] font-medium">Session completion</p>
          <Segmented
            options={COMPLETION_OPTIONS.map((option) => ({ value: option, label: option }))}
            value={completion}
            size="sm"
            label="Session completion"
            className="mt-1.5"
            onChange={setCompletion}
          />
        </div>
        <label className="block">
          <span className="text-[0.78rem] font-medium">
            Note <span className="text-muted">optional</span>
          </span>
          <input
            type="text"
            value={note}
            maxLength={280}
            onChange={(event) => setNote(event.target.value)}
            placeholder="Anything worth remembering about this session"
            className="mt-1.5 min-h-11 w-full rounded-[var(--radius-control)] bg-surface-muted px-3 text-sm"
          />
        </label>
      </div>

      {error ? <p className="text-[0.75rem] text-[var(--status-red)]">{error}</p> : null}

      <Button size="md" variant="primary" className="w-full" disabled={busy} onClick={() => void submit()}>
        {busy ? "Saving…" : "Save session response"}
      </Button>
      <p className="text-[0.68rem] text-muted">
        Stored in this browser. Nothing here is a recovery measurement.
      </p>
    </div>
  );
}
