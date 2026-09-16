"use client";

import { useState } from "react";

import { useUserState } from "@/lib/state-provider";
import { cn } from "@/lib/utils";

/**
 * Switches between the fixed demo profiles. Each profile keeps its own local
 * check-ins, logged sessions and Coach conversation in this browser, so switching
 * never mixes one profile's data into another.
 */
export function ProfileSwitcher() {
  const { profiles, profileId, switchProfile, busy } = useUserState();
  const [message, setMessage] = useState<string | null>(null);

  if (profiles.length <= 1) return null;

  return (
    <div className="rounded-[var(--radius-card)] border border-subtle bg-surface-muted p-3">
      <p className="eyebrow text-muted">Active profile</p>
      <div className="mt-2 flex flex-wrap gap-2">
        {profiles.map((profile) => (
          <button
            key={profile.user_id}
            type="button"
            disabled={busy}
            onClick={async () => {
              if (profile.user_id === profileId) return;
              const result = await switchProfile(profile.user_id);
              setMessage(result.ok ? `Active profile: ${profile.name}` : result.error ?? null);
            }}
            className={cn(
              "min-h-9 rounded-full border px-3 text-[0.75rem] font-medium transition-colors",
              profile.user_id === profileId
                ? "border-transparent bg-primary text-primary-foreground"
                : "border-subtle bg-surface text-muted",
            )}
          >
            {profile.name}
          </button>
        ))}
      </div>
      <p className="mt-2 text-[0.68rem] text-muted">
        Demo profiles are fixed simulated data. Local check-ins and logged sessions are stored per profile in this
        browser.
      </p>
      {message ? <p className="mt-1 text-[0.68rem] text-muted">{message}</p> : null}
    </div>
  );
}
