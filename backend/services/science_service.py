"""Science & Logic payload, reusing the audited content module verbatim."""

from __future__ import annotations

from typing import Any

from science_content import EVIDENCE_BOUNDARIES, EVIDENCE_LABELS, EVIDENCE_MAP, LIMITATIONS, REFERENCES


def references() -> dict[str, Any]:
    return {
        "evidence_boundaries": list(EVIDENCE_BOUNDARIES),
        "labels": dict(EVIDENCE_LABELS),
        "evidence_map": [
            {"key": key, "concept": item["concept"], "evidence": item["evidence"],
             "implementation": item["implementation"], "label": item["label"], "pmids": list(item["pmids"])}
            for key, item in EVIDENCE_MAP.items()
        ],
        "references": [
            {**reference,
             "pubmed_url": f"https://pubmed.ncbi.nlm.nih.gov/{reference['pmid']}/",
             "doi_url": f"https://doi.org/{reference['doi']}" if reference.get("doi") else None}
            for reference in REFERENCES
        ],
        "limitations": list(LIMITATIONS),
        "verification": "Bibliographic fields verified against PubMed, Europe PMC and Crossref (2026-09-16).",
    }
