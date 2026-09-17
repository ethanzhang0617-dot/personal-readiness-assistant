"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Segmented } from "@/components/ui/segmented";
import { api } from "@/lib/api";
import { useUserState } from "@/lib/state-provider";
import type { ExplorerLever, WhatIfResponse } from "@/types/api";
import { cn } from "@/lib/utils";

// What-if / Decision Explorer.
//
// One factor at a time, recomputed by the SAME deterministic rules. The reading
// order is current → change → alternative → one short reason; the engine's own
// field-by-field comparison stays behind "Why →". It is a rule explorer, never a
// prediction, and nothing here is saved.

export function DecisionExplorer({ className }: { className?: string }) {
  const { runWhatIf, busy } = useUserState();
  const [levers, setLevers] = useState<ExplorerLever[] | null>(null);
  const [groups, setGroups] = useState<string[]>([]);
  const [leverKey, setLeverKey] = useState<string>("soreness");
  const [group, setGroup] = useState<string>("");
  const [result, setResult] = useState<WhatIfResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void Promise.all([api.explorerLevers(), api.profileOptions()]).then(([leverResult, optionResult]) => {
      if (cancelled) return;
      if (leverResult.ok) setLevers(leverResult.data.levers);
      if (optionResult.ok) setGroups(optionResult.data.muscle_groups);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const compare = async () => {
    setError(null);
    const outcome = await runWhatIf(leverKey, leverKey === "soreness" ? { group: group || null, level: 4 } : {});
    if (outcome.ok && outcome.data) setResult(outcome.data);
    else setError(outcome.error ?? "The comparison could not be computed.");
  };

  const selected = levers?.find((item) => item.key === leverKey) ?? null;
  const changeDetail = result
    ? Object.entries(result.change ?? {})
        .map(([key, value]) => `${key.replace(/_/g, " ")} ${String(value)}`)
        .join(" · ")
    : "";

  return (
    <div className={cn("space-y-5", className)}>
      <div className="space-y-3">
        {levers ? (
          <Segmented
            options={levers.map((item) => ({ value: item.key, label: item.label }))}
            value={leverKey}
            size="sm"
            label="What-if input"
            onChange={(value) => {
              setLeverKey(String(value));
              setResult(null);
            }}
          />
        ) : null}

        {leverKey === "soreness" && groups.length > 0 ? (
          <label className="block">
            <span className="label-quiet">Muscle group</span>
            <select
              value={group || groups[0]}
              onChange={(event) => {
                setGroup(event.target.value);
                setResult(null);
              }}
              className="mt-1.5 min-h-11 w-full rounded-[var(--radius-control)] border border-subtle bg-surface px-3 text-sm"
            >
              {groups.map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </select>
          </label>
        ) : null}

        <Button size="md" className="w-full" disabled={busy || !levers} onClick={() => void compare()}>
          {busy ? "Comparing…" : "Compare with the current decision"}
        </Button>
      </div>

      {error ? <p className="text-[0.78rem] text-[var(--status-red)]">{error}</p> : null}

      {result ? (
        <div className="surface px-5 py-5">
          <dl className="grid grid-cols-3 gap-x-4">
            <div className="min-w-0">
              <dt className="label-quiet">Current</dt>
              <dd className="mt-1 text-[0.95rem] font-semibold">{result.current.session_demand ?? "—"}</dd>
              <dd className="mt-0.5 truncate text-[0.72rem] text-muted">{result.current.primary_focus ?? "—"}</dd>
            </div>
            <div className="min-w-0">
              <dt className="label-quiet">Change</dt>
              <dd className="mt-1 text-[0.95rem] font-semibold">{result.lever_label ?? "One input"}</dd>
              <dd className="mt-0.5 text-[0.72rem] text-muted">{changeDetail || result.changed_input || ""}</dd>
            </div>
            <div className="min-w-0">
              <dt className="label-quiet">Alternative</dt>
              <dd className="mt-1 text-[0.95rem] font-semibold">{result.alternative.session_demand ?? "—"}</dd>
              <dd className="mt-0.5 truncate text-[0.72rem] text-muted">{result.alternative.primary_focus ?? "—"}</dd>
            </div>
          </dl>

          <p className="mt-4 border-t border-subtle pt-4 text-[0.84rem] leading-relaxed">{result.conclusion}</p>

          <details className="group mt-2">
            <summary className="flex min-h-10 cursor-pointer list-none items-center gap-1 text-[0.76rem] font-medium text-muted">
              Why →
              <span className="transition-transform group-open:rotate-90" aria-hidden>
                ›
              </span>
            </summary>

            <div className="mt-2 space-y-3">
              {result.differences.length > 0 ? (
                <ul className="divide-y divide-subtle border-y border-subtle">
                  {result.differences.map((row) => (
                    <li key={row.key} className="flex items-start justify-between gap-3 py-2 text-[0.76rem]">
                      <span className="text-muted">{row.label}</span>
                      <span className="min-w-0 text-right">
                        {String(row.current ?? "—")} →{" "}
                        <span className="font-medium">{String(row.alternative ?? "—")}</span>
                      </span>
                    </li>
                  ))}
                </ul>
              ) : null}

              {result.why.length > 0 ? (
                <ul className="space-y-1.5">
                  {result.why.map((line) => (
                    <li key={line} className="text-[0.76rem] leading-relaxed text-muted">
                      {line}
                    </li>
                  ))}
                </ul>
              ) : null}

              {selected ? <p className="text-[0.72rem] leading-relaxed text-muted">{selected.description}</p> : null}
              <p className="text-[0.68rem] leading-relaxed text-muted">{result.note}</p>
              <p className="text-[0.68rem] leading-relaxed text-muted">{result.read_only_note}</p>
            </div>
          </details>
        </div>
      ) : null}
    </div>
  );
}
