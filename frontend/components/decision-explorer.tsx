"use client";

import { ArrowDown } from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Segmented } from "@/components/ui/segmented";
import { api } from "@/lib/api";
import { useUserState } from "@/lib/state-provider";
import type { ExplorerLever, WhatIfResponse } from "@/types/api";
import { cn } from "@/lib/utils";

// What-if / Decision Explorer.

// One factor at a time, recomputed by the SAME deterministic rules. The reading
// order is current → change → alternative, then one short reason; the engine's
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
    <div className={cn("space-y-6", className)}>
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
              className="mt-1.5 min-h-11 w-full rounded-[var(--radius-control)] border border-subtle bg-surface-muted px-3 text-sm"
            >
              {groups.map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </select>
          </label>
        ) : null}

        <Button size="lg" className="w-full" disabled={busy || !levers} onClick={() => void compare()}>
          {busy ? "Comparing…" : "Compare with the current decision"}
        </Button>
      </div>

      {error ? <p className="text-[0.8rem] text-[var(--status-red)]">{error}</p> : null}

      {result ? (
        <div className="space-y-3">
          <div className="surface px-5 py-4">
            <p className="eyebrow">Current</p>
            <p className="mt-1 text-[1.2rem] font-semibold">{result.current.session_demand ?? "—"}</p>
            <p className="mt-0.5 text-[0.78rem] text-muted">{result.current.primary_focus ?? "—"}</p>
          </div>

          <div className="flex items-center gap-3 pl-1">
            <ArrowDown className="h-4 w-4 text-muted" aria-hidden />
            <div className="min-w-0">
              <p className="text-[0.72rem] font-medium tracking-[0.06em] text-muted uppercase">Change</p>
              <p className="text-[0.86rem] font-medium">{result.lever_label ?? "One input"}</p>
              <p className="text-[0.76rem] text-muted">{changeDetail || result.changed_input || ""}</p>
            </div>
          </div>

          <div className="surface-raised px-5 py-4">
            <p className="eyebrow">Alternative</p>
            <p className="mt-1 text-[1.2rem] font-semibold" style={{ color: "var(--accent-primary)" }}>
              {result.alternative.session_demand ?? "—"}
            </p>
            <p className="mt-0.5 text-[0.78rem] text-muted">{result.alternative.primary_focus ?? "—"}</p>
          </div>

          <p className="text-[0.86rem] leading-relaxed">{result.conclusion}</p>

          <details className="divider group pt-4">
            <summary className="flex min-h-10 cursor-pointer list-none items-center gap-1 text-[0.8rem] font-medium text-muted">
              Why →
              <span className="transition-transform group-open:rotate-90" aria-hidden>
                ›
              </span>
            </summary>

            <div className="mt-3 space-y-4">
              {result.differences.length > 0 ? (
                <ul>
                  {result.differences.map((row) => (
                    <li
                      key={row.key}
                      className="hairline flex items-start justify-between gap-3 py-2 text-[0.78rem] last:border-b-0"
                    >
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
                <ul className="space-y-2">
                  {result.why.map((line) => (
                    <li key={line} className="text-[0.78rem] leading-relaxed text-muted">
                      {line}
                    </li>
                  ))}
                </ul>
              ) : null}

              {selected ? <p className="text-[0.74rem] leading-relaxed text-muted">{selected.description}</p> : null}
              <p className="text-[0.72rem] leading-relaxed text-muted">{result.note}</p>
              <p className="text-[0.72rem] leading-relaxed text-muted">{result.read_only_note}</p>
            </div>
          </details>
        </div>
      ) : null}
    </div>
  );
}
