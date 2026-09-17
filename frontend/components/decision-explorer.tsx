"use client";

import { ChevronRight } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Segmented } from "@/components/ui/segmented";
import { api } from "@/lib/api";
import { useUserState } from "@/lib/state-provider";
import type { ExplorerLever, WhatIfResponse } from "@/types/api";
import { cn } from "@/lib/utils";

// What-if / Decision Explorer.
//
// One factor at a time, recomputed by the SAME deterministic rules, shown next to
// the current decision. It is a rule explorer, never a prediction, and the API it
// calls returns no state, so nothing here can change what is saved.

export function DecisionExplorer({ className }: { className?: string }) {
  const { runWhatIf, busy } = useUserState();
  const [levers, setLevers] = useState<ExplorerLever[] | null>(null);
  const [groups, setGroups] = useState<string[]>([]);
  const [leverKey, setLeverKey] = useState<string>("soreness");
  const [group, setGroup] = useState<string>("");
  const [result, setResult] = useState<WhatIfResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    if (levers) return;
    const [leverResult, optionResult] = await Promise.all([api.explorerLevers(), api.profileOptions()]);
    if (leverResult.ok) setLevers(leverResult.data.levers);
    if (optionResult.ok) setGroups(optionResult.data.muscle_groups);
  };

  const compare = async () => {
    setError(null);
    const outcome = await runWhatIf(leverKey, leverKey === "soreness" ? { group: group || null, level: 4 } : {});
    if (outcome.ok && outcome.data) setResult(outcome.data);
    else setError(outcome.error ?? "The comparison could not be computed.");
  };

  const selected = levers?.find((item) => item.key === leverKey) ?? null;

  return (
    <details
      className={cn("group", className)}
      onToggle={(event) => {
        if ((event.target as HTMLDetailsElement).open) void load();
      }}
    >
      <summary className="flex min-h-11 cursor-pointer list-none items-center justify-between gap-3 text-sm font-semibold">
        <span>Decision explorer</span>
        <span className="flex items-center gap-2 text-[0.72rem] font-normal text-muted">
          What if one input were different?
          <ChevronRight className="h-4 w-4 transition-transform group-open:rotate-90" aria-hidden />
        </span>
      </summary>

      <div className="space-y-4 pt-3">
        <p className="text-[0.76rem] leading-relaxed text-muted">
          Under the current rules, if this one condition were different, what would the product decide? It re-runs the
          same deterministic rules with one input changed. It is not a prediction, and it does not change anything you
          have saved.
        </p>

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

        {selected ? <p className="text-[0.72rem] text-muted">{selected.description}</p> : null}

        {leverKey === "soreness" && groups.length > 0 ? (
          <label className="block">
            <span className="text-[0.72rem] font-medium">Muscle group</span>
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

        <Button size="md" variant="secondary" className="w-full" disabled={busy || !levers} onClick={() => void compare()}>
          {busy ? "Comparing…" : "Compare with the current decision"}
        </Button>

        {error ? <p className="text-[0.75rem] text-[var(--status-red)]">{error}</p> : null}

        {result ? (
          <div className="space-y-3 border-t border-subtle pt-3">
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-[var(--radius-control)] border border-subtle p-3">
                <p className="eyebrow">Current</p>
                <p className="mt-1 text-[0.84rem] font-semibold">{result.current.session_demand ?? "—"}</p>
                <p className="text-[0.72rem] text-muted">
                  {result.current.primary_focus ?? "—"} · {result.current.personal_response_adjustment}
                </p>
              </div>
              <div className="rounded-[var(--radius-control)] border border-subtle bg-surface-muted p-3">
                <p className="eyebrow">If {result.changed_input ?? "changed"}</p>
                <p className="mt-1 text-[0.84rem] font-semibold">{result.alternative.session_demand ?? "—"}</p>
                <p className="text-[0.72rem] text-muted">
                  {result.alternative.primary_focus ?? "—"} · {result.alternative.personal_response_adjustment}
                </p>
              </div>
            </div>

            <p className="text-[0.8rem] leading-relaxed">{result.conclusion}</p>

            {result.differences.length > 0 ? (
              <ul className="divide-y divide-subtle border-y border-subtle">
                {result.differences.map((row) => (
                  <li key={row.key} className="flex items-start justify-between gap-3 py-2 text-[0.76rem]">
                    <span className="text-muted">{row.label}</span>
                    <span className="min-w-0 text-right">
                      {String(row.current ?? "—")} → <span className="font-medium">{String(row.alternative ?? "—")}</span>
                    </span>
                  </li>
                ))}
              </ul>
            ) : null}

            {result.why.length > 0 ? (
              <ul className="space-y-1">
                {result.why.slice(0, 4).map((line) => (
                  <li key={line} className="text-[0.74rem] leading-relaxed text-muted">
                    {line}
                  </li>
                ))}
              </ul>
            ) : null}

            <p className="text-[0.68rem] leading-relaxed text-muted">{result.note}</p>
            <p className="text-[0.68rem] leading-relaxed text-muted">{result.read_only_note}</p>
          </div>
        ) : null}
      </div>
    </details>
  );
}
