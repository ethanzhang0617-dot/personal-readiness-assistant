import Link from "next/link";
import { ArrowLeft, Info } from "lucide-react";

import { PageHeader } from "@/components/page-header";
import { Section } from "@/components/ui/section";

const FLOW = [
  { step: "01", title: "Profile", body: "Goal and split preference" },
  { step: "02", title: "Morning check-in", body: "Recovery signals" },
  { step: "03", title: "Readiness", body: "Four deterministic domains" },
  { step: "04", title: "Recent training", body: "Completed sessions" },
  { step: "05", title: "Direction", body: "Primary recommendation plus alternatives" },
  { step: "06", title: "Training log", body: "Explicit completed-session record" },
];

// Consumer-level view of the tool-using Agent. The step names are the product's
// own vocabulary; nothing here exposes planner output or hidden reasoning.
const AGENT_STEPS = [
  { title: "Your question", body: "Readiness, today's session, training history or how to adapt" },
  { title: "Agent planner", body: "Decides which verified information the answer needs" },
  { title: "Verified training tools", body: "Read-only capabilities inside the product" },
  { title: "Deterministic results", body: "The engines produce the numbers and the decision" },
  { title: "DeepSeek explanation", body: "Turns the verified results into plain language" },
  { title: "Grounded answer", body: "Shown with the sources that were actually checked" },
];

const AGENT_TOOL_GROUPS = [
  { group: "Readiness", tools: "Readiness · Training Load" },
  { group: "Today's session", tools: "Recommendation · Decision Trace" },
  { group: "Recent training", tools: "Recent Training · Weekly Exposure" },
  { group: "Personal response", tools: "Personal Response · Recommendation Confidence" },
  { group: "Adaptation", tools: "Decision Explorer · In-session Calibration" },
  { group: "Context", tools: "Profile & programme" },
];

export function AboutView() {
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
        title="Adaptive Training Decision System"
        description="Agentic Sports-Science Adaptive Training Decision System"
      />

      <div className="surface-flat space-y-3 p-5">
        <p className="text-[0.9rem] leading-relaxed">
          An independent product project combining sports science, adaptive personal response, deterministic training
          engines and a tool-using AI Agent to turn daily readiness into grounded, actionable training decisions.
        </p>
        <p className="text-[0.82rem] leading-relaxed text-muted">
          基于运动科学与 Agent 的自适应训练决策系统
        </p>
        <p className="text-[0.82rem] leading-relaxed text-muted">
          It answers how ready you are today, what to train, how hard and why — using your personal baseline,
          completed training and programme context.
        </p>
        <p className="text-[0.82rem] leading-relaxed text-muted">
          This is an educational, portfolio-stage prototype. Readiness thresholds, domain aggregation, comparison
          windows, RIR ranges and the recommendation order are documented product heuristics. They have not been
          prospectively validated as clinical, performance-prediction or injury-prediction thresholds.
        </p>
        <p className="text-[0.74rem] leading-relaxed text-muted">
          Former project name: Personal Readiness Assistant. Previously developed as Personal Readiness Assistant
          through V1.4.0; V1.0 prototype → V1.1 productization → V1.2 Next.js migration → V1.3 adaptive decision loop
          → V1.4 tool-using Agent.
        </p>
      </div>

      <Section title="Six steps">
        <ol className="grid gap-3 sm:grid-cols-2">
          {FLOW.map((item) => (
            <li key={item.step} className="flex gap-3">
              <span className="text-[0.68rem] font-semibold tabular-nums text-muted">{item.step}</span>
              <span className="min-w-0">
                <span className="block text-[0.84rem] font-medium">{item.title}</span>
                <span className="block text-[0.74rem] text-muted">{item.body}</span>
              </span>
            </li>
          ))}
        </ol>
      </Section>

      <Section title="How the Agent works">
        <p className="text-[0.9rem] font-medium">
          The Agent decides what to check. The deterministic engines decide how you train.
        </p>
        <ol className="mt-3 space-y-2">
          {AGENT_STEPS.map((item, index) => (
            <li key={item.title} className="flex gap-3">
              <span className="text-[0.68rem] font-semibold tabular-nums text-muted">
                {String(index + 1).padStart(2, "0")}
              </span>
              <span className="min-w-0">
                <span className="block text-[0.84rem] font-medium">{item.title}</span>
                <span className="block text-[0.74rem] text-muted">{item.body}</span>
              </span>
            </li>
          ))}
        </ol>
        <dl className="mt-4 grid gap-2 text-[0.74rem] sm:grid-cols-2">
          {AGENT_TOOL_GROUPS.map((item) => (
            <div key={item.group}>
              <dt className="font-medium">{item.group}</dt>
              <dd className="text-muted">{item.tools}</dd>
            </div>
          ))}
        </dl>
        <p className="mt-4 text-[0.78rem] leading-relaxed text-muted">
          DeepSeek orchestrates verified training context and explains the result, but does not independently override
          readiness, recommendation, calibration or safety decisions. Every answer shows which verified sources were
          checked; hidden reasoning is never exposed.
        </p>
      </Section>

      <Section title="How this build is put together">
        <dl className="grid gap-3 text-[0.78rem] sm:grid-cols-2">
          <div>
            <dt className="font-medium">Frontend</dt>
            <dd className="text-muted">Next.js (App Router) with TypeScript and Tailwind CSS.</dd>
          </div>
          <div>
            <dt className="font-medium">API</dt>
            <dd className="text-muted">FastAPI adapter that calls the existing deterministic engines.</dd>
          </div>
          <div>
            <dt className="font-medium">Local data</dt>
            <dd className="text-muted">Check-ins, sessions, profile edits and Coach history live in this browser.</dd>
          </div>
          <div>
            <dt className="font-medium">AI</dt>
            <dd className="text-muted">
              Personal facts are answered deterministically; explanation questions may use a configured AI provider.
            </dd>
          </div>
        </dl>
      </Section>

      <Section title="Safety and limits">
        <ul className="space-y-1.5 text-[0.78rem] leading-relaxed text-muted">
          <li>Not a medical device, diagnosis, fatigue prediction or injury prediction tool.</li>
          <li>Not clinically validated, and not a substitute for a coach or clinician.</li>
          <li>No wearable integration, no accounts and no remote personal-history database.</li>
        </ul>
        <p className="mt-3 flex items-start gap-2 text-[0.7rem] text-muted">
          <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
          Read the evidence boundaries and the 13 verified references under Profile → Science &amp; Logic.
        </p>
      </Section>
    </div>
  );
}
