"""Focused tests for the V1.2 FastAPI adapter.

These tests only cover the transport layer. Scientific behaviour is still
asserted by the existing ``test_app.py`` suite, which stays unchanged.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

import ai_engine
from backend.main import app


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


def test_health_reports_engines_and_never_exposes_the_credential(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["api_version"].startswith("1.2.0")
    assert payload["ai_provider"] == ai_engine.AI_PROVIDER_LABEL
    assert "readiness_engine.assess_readiness" in payload["engines"]
    assert "training_recommendation_engine.recommend_training" in payload["engines"]
    assert isinstance(payload["ai_credential_configured"], bool)
    body = json.dumps(payload)
    assert "DEEPSEEK_API_KEY" not in body
    assert "sk-" not in body


def test_readiness_endpoint_matches_the_engine(client: TestClient) -> None:
    import app as streamlit_app
    from demo_data import build_demo_profiles
    from readiness_engine import assess_readiness

    payload = client.get("/api/readiness").json()

    profile = build_demo_profiles()[0]
    expected = assess_readiness(streamlit_app.get_draft(profile), profile["history"],
                                profile["personal_sleep_need"], profile["assessments"])

    assert payload["status"] == expected["overall_readiness"]
    assert payload["index"] == expected["readiness_index"]
    assert payload["confidence"] == expected["assessment_confidence"]
    assert payload["index_scale"] == {"min": 0, "max": 100}
    assert {domain["key"] for domain in payload["domains"]} == set(expected["domains"])
    assert payload["source"] == "readiness_engine.assess_readiness"


def test_recommendation_and_trace_match_the_engine(client: TestClient) -> None:
    payload = client.get("/api/training/recommendation").json()
    trace = client.get("/api/decision-trace").json()

    assert payload["primary_name"]
    assert payload["session_demand"]
    assert payload["duration"]
    assert payload["source"] == "training_recommendation_engine.recommend_training"
    assert [step["index"] for step in trace] == list(range(1, len(trace) + 1))
    assert trace[0]["step"] == "GOAL"
    assert trace[-1]["step"] == "RECOMMENDATION"
    assert trace[-1]["value"] == payload["primary_name"]
    assert all(step["source"] == "deterministic" for step in trace)


def test_today_separates_how_hard_from_duration(client: TestClient) -> None:
    payload = client.get("/api/today").json()
    recommendation = payload["training"]["recommendation"]
    assert payload["readiness"]["status"]
    assert recommendation["session_demand"] != recommendation["duration"]
    assert recommendation["duration"].endswith("min")
    assert payload["why"]["note"].startswith("Decision Trace is a deterministic explanation")


def test_exposure_uses_weighted_working_sets(client: TestClient) -> None:
    payload = client.get("/api/training/exposure").json()
    assert payload["unit"] == "weighted working sets"
    assert "Direct sets count 1.0" in payload["note"]
    assert "not days and not sessions" in payload["note"]
    assert payload["groups"]


def test_science_endpoint_serves_the_audited_reference_set(client: TestClient) -> None:
    payload = client.get("/api/science/references").json()
    assert len(payload["references"]) == 13
    assert len(payload["evidence_boundaries"]) == 3
    pmids = {reference["pmid"] for reference in payload["references"]}
    assert {"24578692", "30558493", "41343037"} <= pmids
    for reference in payload["references"]:
        assert reference["pubmed_url"].endswith(f"/{reference['pmid']}/")
        assert reference["doi_url"].startswith("https://doi.org/10.")
    joined = " ".join(payload["evidence_boundaries"])
    assert "not clinically validated" in joined
    assert "have not been prospectively validated" in joined


def test_unknown_profile_returns_404(client: TestClient) -> None:
    assert client.get("/api/today?profile_id=does-not-exist").status_code == 404


def test_coach_factual_endpoint_makes_zero_provider_calls(client: TestClient, monkeypatch) -> None:
    calls: list[str] = []

    def counted_post(url, *args, **kwargs):
        calls.append(str(url))
        raise AssertionError("a personal factual question must not call the AI provider")

    monkeypatch.setattr(ai_engine.requests, "post", counted_post)
    response = client.post("/api/coach/message", json={"question": "How much have I trained back this week?"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["kind"] == "verified_data"
    assert payload["ai_used"] is False
    assert payload["verified_data"] is True
    assert "weighted working set" in payload["answer"].casefold()
    assert calls == []


def test_coach_explanation_degrades_when_the_provider_is_down(client: TestClient, monkeypatch) -> None:
    def exploding_post(url, *args, **kwargs):
        raise ai_engine.requests.exceptions.ConnectionError("provider unreachable")

    monkeypatch.setattr(ai_engine.requests, "post", exploding_post)
    response = client.post("/api/coach/message", json={"question": "Why this workout?"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["kind"] == "deterministic_fallback"
    assert payload["ai_used"] is False
    assert payload["notice"]
    assert payload["answer"]


def test_coach_rejects_an_empty_question(client: TestClient) -> None:
    assert client.post("/api/coach/message", json={"question": ""}).status_code == 422
