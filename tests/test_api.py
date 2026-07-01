"""API tests via FastAPI TestClient. The arbitration service is mocked (no model
calls); storage uses an isolated temp DB so analytics math is checked on real rows."""

import pytest
from fastapi.testclient import TestClient

import src.api.routes as routes
from src.api.main import app
from src.schemas.critique import CritiqueReport, Issue, Severity
from src.schemas.verdict import ConfirmedIssue, Disagreement, DismissedFlag, Verdict
from src.storage import db
from src.storage.db import ArbitrationRecord, save_arbitration


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setenv("ARBITRATION_DB_PATH", str(tmp_path / "api_test.db"))
    db.init_db()
    yield


client = TestClient(app)


def _verdict(score=4, adjudicated=True, disagreements=None, dismissed=None, confirmed=None):
    return Verdict(
        overall_score=score,
        confidence=0.7,
        confirmed_issues=confirmed or [],
        dismissed_flags=dismissed or [],
        summary="test verdict",
        critic_reports=[
            CritiqueReport(
                dimension="accuracy", score=2,
                issues=[Issue(quote="q", problem="p", severity=Severity.HIGH)],
                confidence=0.9, critic_model="llama3",
            )
        ],
        disagreements=disagreements or [],
        adjudicated=adjudicated,
    )


def test_health_reports_providers():
    r = client.get("/health")
    assert r.status_code == 200
    assert "providers" in r.json()


def test_arbitrate_endpoint(monkeypatch):
    def fake(llm_output, original_prompt=None):
        return save_arbitration(llm_output, original_prompt, _verdict())

    monkeypatch.setattr(routes, "arbitrate_and_store", fake)
    r = client.post("/v1/arbitrate", json={"llm_output": "some text", "original_prompt": None})
    assert r.status_code == 200
    body = r.json()
    assert body["id"] and body["created_at"]
    assert body["verdict"]["overall_score"] == 4


def test_batch_endpoint(monkeypatch):
    def fake(llm_output, original_prompt=None):
        return save_arbitration(llm_output, original_prompt, _verdict())

    monkeypatch.setattr(routes, "arbitrate_and_store", fake)
    r = client.post(
        "/v1/arbitrate/batch",
        json={"items": [{"llm_output": "a"}, {"llm_output": "b"}]},
    )
    assert r.status_code == 200
    assert len(r.json()["results"]) == 2


def test_get_arbitration_roundtrip():
    rec = save_arbitration("stored output", "the prompt", _verdict(score=7))
    r = client.get(f"/v1/arbitrations/{rec.id}")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == rec.id
    assert body["llm_output"] == "stored output"
    assert body["verdict"]["overall_score"] == 7


def test_get_arbitration_404():
    assert client.get("/v1/arbitrations/nope").status_code == 404


def test_analytics_is_live_not_hardcoded():
    # Empty DB first.
    assert client.get("/v1/analytics").json()["total_arbitrations"] == 0

    # Add two arbitrations with known properties.
    save_arbitration("x", None, _verdict(score=2, adjudicated=True,
        disagreements=[Disagreement(type="unique_find", description="d",
                                    critics_involved=["logic"], details="x")],
        dismissed=[DismissedFlag(description="f", raised_by="completeness", reasoning="r")],
        confirmed=[ConfirmedIssue(description="c", severity=Severity.HIGH,
                                  evidence="e", source_critics=["accuracy"])]))
    save_arbitration("y", None, _verdict(score=8, adjudicated=False))

    stats = client.get("/v1/analytics").json()
    assert stats["total_arbitrations"] == 2
    assert stats["avg_overall_score"] == 5.0           # (2 + 8) / 2
    assert stats["short_circuit_rate"] == 0.5          # one short-circuited
    assert stats["disagreement_rate"] == 0.5           # one had a disagreement
    assert stats["most_overruled_critic"] == "completeness"
    assert stats["disagreement_type_counts"]["unique_find"] == 1


def test_openapi_documents_all_endpoints():
    paths = client.get("/openapi.json").json()["paths"]
    assert "/v1/arbitrate" in paths
    assert "/v1/arbitrate/batch" in paths
    assert "/v1/arbitrations/{arbitration_id}" in paths
    assert "/v1/analytics" in paths
