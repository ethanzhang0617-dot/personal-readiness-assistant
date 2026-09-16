"use client";

import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import { useUserState } from "@/lib/state-provider";

/**
 * Demo scenario switch. Scenarios are simulated check-ins for the fixed demo
 * profiles; switching one refreshes readiness, training, exposure, the decision
 * trace, the Coach context and Insights.
 */
export function ScenarioSwitcher() {
  const { scenario, setScenario, busy } = useUserState();
  const [options, setOptions] = useState<string[]>([]);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    api.scenarios().then((result) => {
      if (result.ok) setOptions(result.data.scenarios.map((item) => item.name));
    });
  }, []);

  return (
    <div className="rounded-[var(--radius-card)] border border-subtle bg-surface-muted p-3">
      <label className="eyebrow text-muted" htmlFor="scenario">
        Demo scenario
      </label>
      <select
        id="scenario"
        value={scenario ?? ""}
        disabled={busy}
        onChange={async (event) => {
          const result = await setScenario(event.target.value);
          setMessage(result.ok ? result.message ?? null : result.error ?? null);
        }}
        className="mt-2 min-h-11 w-full rounded-[var(--radius-control)] border border-subtle bg-surface px-3 text-sm"
      >
        {options.map((name) => (
          <option key={name} value={name}>
            {name}
          </option>
        ))}
      </select>
      {message ? <p className="mt-1.5 text-[0.68rem] text-muted">{message}</p> : null}
    </div>
  );
}
