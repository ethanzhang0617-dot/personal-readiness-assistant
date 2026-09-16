import Link from "next/link";
import { ArrowLeft, ExternalLink } from "lucide-react";

import { PageHeader } from "@/components/page-header";
import { StatePanel } from "@/components/state-panel";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Section } from "@/components/ui/section";
import { api } from "@/lib/api";

/**
 * Science & Logic ported from the audited content module. Scientific meaning and
 * qualification language are unchanged; only layout, labels and mobile
 * readability are adjusted.
 */
export async function ScienceView() {
  const [result, logic] = await Promise.all([api.science(), api.scienceLogic()]);

  if (!result.ok) {
    return <StatePanel tone="error" title="Science & Logic is unavailable" body={result.error} />;
  }

  const { evidence_boundaries: boundaries, evidence_map: evidenceMap, labels, limitations, references, verification } =
    result.data;

  const nav = [
    { href: "#boundaries", label: "Boundaries" },
    { href: "#concepts", label: "Concepts" },
    { href: "#rules", label: "Rules" },
    { href: "#references", label: "References" },
  ];

  return (
    <div className="space-y-6">
      <Link
        href="/profile"
        className="inline-flex min-h-9 items-center gap-1.5 text-[0.75rem] text-muted transition-colors hover:text-foreground"
      >
        <ArrowLeft className="h-3.5 w-3.5" aria-hidden />
        Profile
      </Link>

      <PageHeader
        eyebrow="Science & Logic"
        title="Evidence and boundaries"
        description="What the literature supports, and where this product uses its own heuristics."
      />

      <nav aria-label="Sections" className="-mx-1 flex gap-2 overflow-x-auto px-1 pb-1">
        {nav.map((item) => (
          <a
            key={item.href}
            href={item.href}
            className="shrink-0 rounded-full border border-subtle bg-surface px-3 py-1.5 text-[0.75rem] font-medium text-muted transition-colors hover:text-foreground"
          >
            {item.label}
          </a>
        ))}
      </nav>

      <section id="boundaries" className="scroll-mt-20">
        <Card className="space-y-3 p-5">
          <p className="eyebrow">Evidence boundaries</p>
          {boundaries.map((paragraph) => (
            <p key={paragraph} className="text-[0.85rem] leading-relaxed">
              {paragraph}
            </p>
          ))}
        </Card>
      </section>

      <section id="concepts" className="scroll-mt-20">
        <Section eyebrow="Evidence" title="Concept by concept" divided={false}>
          <ul className="divide-y divide-subtle border-y border-subtle">
            {evidenceMap.map((row) => (
              <li key={row.key} className="space-y-1.5 py-4">
                <div className="flex items-start justify-between gap-3">
                  <p className="text-[0.86rem] font-semibold">{row.concept}</p>
                  <Badge
                    variant={
                      row.label === labels.heuristic ? "amber" : row.label === labels.not_clinical ? "red" : "green"
                    }
                  >
                    {row.label === labels.heuristic ? "Product heuristic" : "Evidence-supported"}
                  </Badge>
                </div>
                <p className="text-[0.78rem] leading-relaxed text-muted">{row.evidence}</p>
                <p className="text-[0.78rem] leading-relaxed">{row.implementation}</p>
                {row.pmids.length > 0 ? (
                  <p className="flex flex-wrap gap-x-3 gap-y-1 text-[0.7rem] text-muted">
                    {row.pmids.map((pmid) => (
                      <a
                        key={pmid}
                        href={`https://pubmed.ncbi.nlm.nih.gov/${pmid}/`}
                        target="_blank"
                        rel="noreferrer"
                        className="underline decoration-dotted underline-offset-2"
                      >
                        PMID {pmid}
                      </a>
                    ))}
                  </p>
                ) : (
                  <p className="text-[0.7rem] text-muted">No direct citation: product design choice.</p>
                )}
              </li>
            ))}
          </ul>
        </Section>
      </section>

      {logic.ok ? (
        <section id="rules" className="scroll-mt-20 space-y-6">
          <Section eyebrow="System" title="How the decision is built">
            <p className="text-[0.8rem] leading-relaxed text-muted">
              {logic.data.system_steps.map((step) => step.toLowerCase()).join(" → ")}
            </p>
            <dl className="mt-3 grid gap-2 sm:grid-cols-2">
              {Object.entries(logic.data.inputs).map(([key, value]) => (
                <div key={key}>
                  <dt className="text-[0.7rem] font-semibold uppercase tracking-[0.08em] text-muted">
                    {key.replace("_", " ")}
                  </dt>
                  <dd className="text-[0.78rem] leading-snug">{value}</dd>
                </div>
              ))}
            </dl>
          </Section>

          <Section eyebrow="Thresholds" title="Transparent operating bands">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-[0.74rem]">
                <thead className="text-muted">
                  <tr>
                    <th className="pb-1.5 font-medium">Input</th>
                    <th className="pb-1.5 font-medium">Green</th>
                    <th className="pb-1.5 font-medium">Amber</th>
                    <th className="pb-1.5 font-medium">Red</th>
                  </tr>
                </thead>
                <tbody>
                  {logic.data.thresholds.map((row) => (
                    <tr key={row.key} className="border-t border-subtle">
                      <td className="py-2 pr-2">{row.label}</td>
                      <td className="py-2 pr-2 tabular-nums">{row.green}</td>
                      <td className="py-2 pr-2 tabular-nums">{row.amber}</td>
                      <td className="py-2 tabular-nums">{row.red}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="mt-2 text-[0.7rem] text-muted">{logic.data.threshold_caveat}</p>
          </Section>

          <Section eyebrow="Aggregation" title="Overall readiness logic">
            <ul className="space-y-1.5">
              {logic.data.overall_rule.map((rule) => (
                <li key={rule} className="text-[0.78rem] leading-relaxed text-muted">
                  • {rule}
                </li>
              ))}
            </ul>
            <p className="mt-3 text-[0.8rem] leading-relaxed">{logic.data.readiness_index_caveat}</p>
            <p className="mt-2 text-[0.78rem] leading-relaxed text-muted">{logic.data.safety_override}</p>
          </Section>

          <Section eyebrow="Selection" title="How today's training is chosen">
            <ol className="space-y-1.5">
              {logic.data.decision_order.map((step, index) => (
                <li key={step} className="text-[0.78rem] leading-relaxed">
                  <span className="font-semibold">{index + 1}.</span> {step}
                </li>
              ))}
            </ol>
            <p className="mt-3 text-[0.78rem] leading-relaxed text-muted">{logic.data.session_demand_mapping}</p>
            <p className="mt-2 text-[0.78rem] leading-relaxed text-muted">
              Training Load is calendar-based: mean daily session-RPE load across{" "}
              {String(logic.data.training_load.recent_window ?? "the last 7 complete calendar days")} compared with{" "}
              {String(logic.data.training_load.reference_window ?? "the preceding 21 complete calendar days")}.
            </p>
            <p className="mt-2 text-[0.78rem] leading-relaxed text-muted">
              Weekly exposure uses weighted working sets:{" "}
              {String(logic.data.fractional_sets["label"] ?? "direct sets count 1.0 and mapped secondary sets 0.5")}
            </p>
            <p className="mt-2 text-[0.78rem] leading-relaxed text-muted">{logic.data.rir_guidance}</p>
          </Section>

          <Section eyebrow="Illustration" title="Example decision">
            <dl className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-[0.78rem]">
              {Object.entries(logic.data.example_decision).map(([key, value]) => (
                <div key={key} className="flex justify-between gap-2">
                  <dt className="capitalize text-muted">{key.replace("_", " ")}</dt>
                  <dd className="text-right font-medium">{value}</dd>
                </div>
              ))}
            </dl>
            <p className="mt-3 text-[0.74rem] leading-relaxed text-muted">{logic.data.example_note}</p>
          </Section>
        </section>
      ) : (
        <StatePanel tone="error" title="Rule detail unavailable" body={logic.error} />
      )}

      <Section eyebrow="Limits" title="What this system does not claim">
        <ul className="space-y-1.5">
          {limitations.map((item) => (
            <li key={item} className="text-[0.78rem] leading-relaxed text-muted">
              {item}
            </li>
          ))}
        </ul>
      </Section>

      <section id="references" className="scroll-mt-20">
        <Section
          eyebrow="Bibliography"
          title="References"
          description={verification}
          action={<span className="text-[0.72rem] text-muted">{references.length} verified</span>}
          divided={false}
        >
          <ol className="divide-y divide-subtle border-y border-subtle">
            {references.map((reference) => (
              <li key={reference.pmid} className="py-4">
                <p className="text-[0.78rem] font-semibold leading-snug">
                  {reference.authors} ({reference.year})
                </p>
                <p className="mt-1 text-[0.82rem] leading-relaxed">{reference.title}</p>
                <p className="mt-1 text-[0.74rem] text-muted">
                  {reference.journal}, {reference.citation}
                </p>
                <p className="mt-1.5 flex flex-wrap gap-x-4 gap-y-1 text-[0.72rem]">
                  <a
                    href={reference.pubmed_url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 underline decoration-dotted underline-offset-2"
                  >
                    PMID {reference.pmid}
                    <ExternalLink className="h-3 w-3" aria-hidden />
                  </a>
                  {reference.doi_url ? (
                    <a
                      href={reference.doi_url}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1 underline decoration-dotted underline-offset-2"
                    >
                      DOI
                      <ExternalLink className="h-3 w-3" aria-hidden />
                    </a>
                  ) : null}
                </p>
              </li>
            ))}
          </ol>
        </Section>
      </section>
    </div>
  );
}
