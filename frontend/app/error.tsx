"use client";

import { StatePanel } from "@/components/state-panel";
import { Button } from "@/components/ui/button";

export default function RouteError({ reset }: { error: Error; reset: () => void }) {
  return (
    <StatePanel
      tone="error"
      title="This screen failed to load"
      body="The page state could not be rendered. Your data is unchanged."
      action={<Button onClick={reset} variant="secondary">Try again</Button>}
    />
  );
}
