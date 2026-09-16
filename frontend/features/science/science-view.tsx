import Link from "next/link";
import { ArrowLeft, ExternalLink } from "lucide-react";

import { PageHeader } from "@/components/page-header";
import { StatePanel } from "@/components/state-panel";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { api } from "@/lib/api";

/**
 * Science & Logic ported from the audited content module. The qualification
 * language is carried over verbatim: it must not be shortened away.
 */
export async function ScienceView() {
  const [result, logic] = await Promise.all([api.science(), api.scienceLogic()]);

  if (!result.ok) {
    return <StatePanel tone="error" title="Science & Logic is unavailable" body={result.error} />;
  }

  const { evidence_boundaries: boundaries, evidence_map: evidenceMap, labels, limitations, references, verification } =
    result.data;

  return (
    <div className="space-y-4">
      <Link
        href="/profile"
        className="inline-flex min-h-9 items-center gap-1.5 text-[0.72rem] text-muted transition-colors hover:text-foreground"
      >
        <ArrowLeft className="h-3.5 w-3.5" aria-hidden />
        Profile
      </Link>

      <PageHeader
        eyebrow="Science & Logic"
        title="Evidence and boundaries"
        description="What the literature supports, and where this product uses its own heuristics."
      />

      <Card className="space-y-3 p-4">
        <p className="eyebrow text-muted">Evidence boundaries</p>
        {boundaries.map((paragraph) => (
          <p key={paragraph} className="text-[0.82rem] leading-relaxed text-muted">
            {paragraph}
          </p>
        ))}
      </Card>

      {logic.ok ? (
        <>
          <Card className="space-y-3 p-4">
            <p className="eyebrow text-muted">System overview</p>
            <p className="text-[0.78rem] leading-relaxed">
              {logic.data.system_steps.map((step) => step.toLowerCase()).join(" → ")}
            </p>
            <div className="grid gap-2 pt-1">
              {Object.entries(logic.data.inputs).map(([key, value]) => (
                <p key={key} className="text-[0.74rem] text-muted">
                  <span className="font-semibold uppercase tracking-wide text-foreground">{key.replace("_", " ")}</span> ·{" "}
                  {value}
                </p>
              ))}
            </div>
          </Card>

          <Card className="space-y-3 p-4">
            <p className="eyebrow text-muted">Threshold table</p>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-[0.72rem]">
                <thead className="text-muted">
                  <tr>
                    <th className="pb-1 font-medium">Input</th>
                    <th className="pb-1 font-medium">Green</th>
                    <th className="pb-1 font-medium">Amber</th>
                    <th className="pb-1 font-medium">Red</th>
                  </tr>
                </thead>
                <tbody>
                  {logic.data.thresholds.map((row) => (
                    <tr key={row.key} className="border-t border-subtle">
                      <td className="py-1.5 pr-2">{row.label}</td>
                      <td className="py-1.5 pr-2 tabular-nums">{row.green}</td>
                      <td className="py-1.5 pr-2 tabular-nums">{row.amber}</td>
                      <td className="py-1.5 tabular-nums">{row.red}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="text-[0.7rem] text-muted">{logic.data.threshold_caveat}</p>
          </Card>

          <Card className="space-y-3 p-4">
            <p className="eyebrow text-muted">Overall readiness logic</p>
            <ul className="space-y-1.5">
              {logic.data.overall_rule.map((rule) => (
                <li key={rule} className="text-[0.76rem] leading-relaxed text-muted">
                  • {rule}
                </li>
              ))}
            </ul>
            <p className="text-[0.74rem] leading-relaxed">{logic.data.readiness_index_caveat}</p>
            <p className="text-[0.74rem] leading-relaxed text-muted">{logic.data.safety_override}</p>
          </Card>

          <Card className="space-y-3 p-4">
            <p className="eyebrow text-muted">How today&apos;s training is selected</p>
            <ol className="space-y-1.5">
              {logic.data.decision_order.map((step, index) => (
                <li key={step} className="text-[0.76rem] leading-relaxed">
                  <span className="font-semibold">{index + 1}.</span> {step}
                </li>
              ))}
            </ol>
            <p className="text-[0.74rem] leading-relaxed text-muted">{logic.data.session_demand_mapping}</p>
            <p className="text-[0.74rem] leading-relaxed text-muted">
              Training Load is calendar-based: mean daily session-RPE load across{" "}
              {String(logic.data.training_load.recent_window ?? "the last 7 complete calendar days")} compared with{" "}
              {String(logic.data.training_load.reference_window ?? "the preceding 21 complete calendar days")}.
            </p>
            <p className="text-[0.74rem] leading-relaxed text-muted">
              Weekly exposure uses weighted working sets:{" "}
              {String(logic.data.fractional_sets["label"] ?? "direct sets count 1.0 and mapped secondary sets 0.5")}
            </p>
            <p className="text-[0.74rem] leading-relaxed text-muted">{logic.data.rir_guidance}</p>
          </Card>

          <Card className="space-y-2 p-4">
            <p className="eyebrow text-muted">Example decision</p>
            <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-[0.74rem]">
              {Object.entries(logic.data.example_decision).map(([key, value]) => (
                <div key={key} className="flex justify-between gap-2">
                  <dt className="text-muted capitalize">{key.replace("_", " ")}</dt>
                  <dd className="text-right font-medium">{value}</dd>
                </div>
              ))}
            </dl>
            <p className="text-[0.7rem] text-muted">{logic.data.example_note}</p>
          </Card>
        </>
      ) : (
        <StatePanel tone="error" title="Rule detail unavailable" body={logic.error} />
      )}

      <section className="space-y-2">
        <h2 className="px-1 text-sm font-semibold">Concept by concept</h2>
        {evidenceMap.map((row) => (
          <Card key={row.key} className="p-4">
            <div className="flex items-start justify-between gap-3">
              <p className="text-sm font-semibold">{row.concept}</p>
              <Badge
                variant={
                  row.label === labels.heuristic
                    ? "amber"
                    : row.label === labels.not_clinical
                      ? "red"
                      : "green"
                }
              >
                {row.label === labels.heuristic ? "Product heuristic" : "Evidence-supported"}
              </Badge>
            </div>
            <p className="mt-2 text-[0.78rem] leading-relaxed text-muted">{row.evidence}</p>
            <p className="mt-1.5 text-[0.78rem] leading-relaxed">{row.implementation}</p>
            {row.pmids.length > 0 ? (
              <p className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-[0.68rem] text-muted">
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
              <p className="mt-2 text-[0.68rem] text-muted">No direct citation: product design choice.</p>
            )}
          </Card>
        ))}
      </section>

      <Card className="p-4">
        <p className="eyebrow text-muted">What this system does not claim</p>
        <ul className="mt-3 space-y-1.5">
          {limitations.map((item) => (
            <li key={item} className="text-[0.78rem] leading-relaxed text-muted">
              {item}
            </li>
          ))}
        </ul>
      </Card>

      <section className="space-y-2">
        <div className="flex items-baseline justify-between gap-3 px-1">
          <h2 className="text-sm font-semibold">References</h2>
          <span className="text-[0.68rem] text-muted">{references.length} verified</span>
        </div>
        <p className="px-1 text-[0.68rem] leading-relaxed text-muted">{verification}</p>
        {references.map((reference) => (
          <Card key={reference.pmid} className="p-4">
            <p className="text-[0.78rem] font-semibold leading-snug">
              {reference.authors} ({reference.year})
            </p>
            <p className="mt-1 text-[0.8rem] leading-relaxed">{reference.title}</p>
            <p className="mt-1.5 text-[0.72rem] text-muted">
              {reference.journal}, {reference.citation}
            </p>
            <p className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[0.7rem]">
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
          </Card>
        ))}
      </section>
    </div>
  );
}
