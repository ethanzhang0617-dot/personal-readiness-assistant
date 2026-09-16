"""Science & Logic payload, reusing the audited content module verbatim."""

from __future__ import annotations

from typing import Any

from readiness_engine import AMBER, GREEN, RED
from science_content import (EVIDENCE_BOUNDARIES, EVIDENCE_LABELS, EVIDENCE_MAP, LIMITATIONS,
                             READINESS_RULE_METADATA, RECOMMENDATION_RULE_METADATA, REFERENCES)


_THRESHOLD_LABELS = {
    "hrv_z": "HRV / LnRMSSD z",
    "rhr_z": "Resting HR z",
    "sleep_ratio": "Sleep / personal need",
    "sleep_quality": "Sleep quality",
    "subjective_badness": "Subjective badness",
}


def logic() -> dict[str, Any]:
    """The rule-level Science & Logic content, taken from the engines' own metadata."""
    thresholds = [
        {"key": key, "label": _THRESHOLD_LABELS.get(key, key),
         "green": values[GREEN], "amber": values[AMBER], "red": values[RED],
         "label_text": EVIDENCE_LABELS["heuristic"]}
        for key, values in READINESS_RULE_METADATA["thresholds"].items()
    ]
    return {
        "baseline": dict(READINESS_RULE_METADATA["baseline"]),
        "thresholds": thresholds,
        "threshold_caveat": "All exact category boundaries are transparent prototype operating thresholds — NOT A CLINICAL THRESHOLD.",
        "overall_rule": list(READINESS_RULE_METADATA["overall_rule"]),
        "readiness_index": dict(READINESS_RULE_METADATA["readiness_index"]),
        "readiness_index_caveat": ("The Readiness Index is a secondary communication score averaged across classifiable "
                                  "domains. It is not a recovery percentage, fatigue probability or injury probability."),
        "training_load": dict(READINESS_RULE_METADATA["training_load"]),
        "decision_order": list(RECOMMENDATION_RULE_METADATA["decision_order"]),
        "session_demand_mapping": ("Readiness primarily modifies session demand: Green → Normal; Amber → Reduced / "
                                   "autoregulated; Red → rest or lower-demand; STOP → no normal recommendation."),
        "fractional_sets": dict(RECOMMENDATION_RULE_METADATA["fractional_sets"]),
        "rir_guidance": ("For strength templates, normal-demand guidance is typically 1–3 RIR; reduced-demand guidance "
                         "is 2–4 RIR with unnecessary failure avoided. These are practical product ranges, not "
                         "validated readiness thresholds."),
        "safety_override": ("Safety override: chest pain, fainting / near fainting, fever / acute illness, acute injury "
                            "preventing normal training, or unusual shortness of breath routes to STOP. This is "
                            "conservative product routing, not a medical diagnosis."),
        "example_decision": {
            "goal": "Muscle Gain", "programme": "Body-part Split", "today": GREEN,
            "back": "6 / 12 weekly sets", "chest": "10 / 10", "yesterday": "Legs · RPE 8",
            "local_soreness": "Quads 4 / 5", "recommendation": "Back + Biceps",
        },
        "example_note": ("Goal favours resistance training; Back is below target; Chest is near target; Legs were "
                         "trained recently at high effort; lower-body soreness is elevated; Green readiness supports "
                         "normal session demand."),
        "system_steps": ["PERSONAL BASELINE", "DAILY CHECK-IN", "FOUR READINESS DOMAINS", "SAFETY SCREEN",
                         "OVERALL READINESS", "TRAINING HISTORY", "WEEKLY TRAINING EXPOSURE", "GOAL + SPLIT",
                         "LOCAL SORENESS", "SESSION DEMAND", "TODAY'S TRAINING RECOMMENDATION"],
        "inputs": {
            "autonomic": "HRV / RMSSD · Resting heart rate",
            "sleep": "Sleep duration relative to personal sleep need · Sleep quality",
            "subjective": "Fatigue · Stress · Motivation · Global soreness",
            "training_load": "Completed-session duration · Session RPE · Recent load trend",
            "training_context": "Goal · Split · Completed sessions · Weekly muscle exposure · Today's local soreness",
        },
    }


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
