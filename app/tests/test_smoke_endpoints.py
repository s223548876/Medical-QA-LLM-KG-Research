from fastapi.testclient import TestClient

import routers.api as api_router_module
from main import app


client = TestClient(app)


def test_health_smoke():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_query_smoke(monkeypatch):
    def fake_query(**kwargs):
        return {
            "question": kwargs["question"],
            "qtype": "definition",
            "extracted_terms": [],
            "debug": [],
            "results": [
                {
                    "term": None,
                    "conceptId": None,
                    "subgraph_size": 0,
                    "subgraph_summary": [],
                    "answer": "stubbed query answer",
                    "relevance": 1.0,
                }
            ],
        }

    monkeypatch.setattr(api_router_module.query_service, "query", fake_query)
    resp = client.get("/query", params={"question": "what is asthma"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["question"] == "what is asthma"
    assert body["results"][0]["answer"] == "stubbed query answer"


def test_llm_only_smoke(monkeypatch):
    def fake_llm_only(**kwargs):
        return {
            "question": kwargs["question"],
            "qtype": "definition",
            "results": [
                {
                    "term": None,
                    "conceptId": None,
                    "subgraph_size": 0,
                    "subgraph_summary": [],
                    "answer": "stubbed llm answer",
                    "relevance": 1.0,
                }
            ],
        }

    monkeypatch.setattr(api_router_module.query_service, "llm_only", fake_llm_only)
    resp = client.get("/llm_only", params={"question": "what is diabetes"})
    assert resp.status_code == 200
    assert resp.json()["results"][0]["answer"] == "stubbed llm answer"


def test_demo_search_get_smoke(monkeypatch):
    def fake_demo_search(**kwargs):
        return {
            "question": kwargs["question"],
            "qtype": "definition",
            "results": [{"answer": "stubbed demo answer"}],
            "matched": True,
            "similarity": 1.0,
            "mapped_to": {"bank_id": None, "qtype": "definition", "question": kwargs["question"]},
            "answers": {
                "a_label": "Answer A",
                "a_text": "stubbed demo answer",
                "b_label": "Answer B",
                "b_text": "stubbed demo answer",
            },
        }

    monkeypatch.setattr(api_router_module.query_service, "demo_search_compat_response", fake_demo_search)
    resp = client.get("/demo/search", params={"question": "asthma treatment"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["matched"] is True
    assert body["answers"]["a_text"] == "stubbed demo answer"


def test_demo_search_post_smoke(monkeypatch):
    def fake_demo_search(**kwargs):
        return {
            "question": kwargs["question"],
            "qtype": "symptoms",
            "results": [{"answer": "stubbed post demo answer"}],
            "matched": True,
            "similarity": 1.0,
            "mapped_to": {"bank_id": None, "qtype": "symptoms", "question": kwargs["question"]},
            "answers": {
                "a_label": "Answer A",
                "a_text": "stubbed post demo answer",
                "b_label": "Answer B",
                "b_text": "stubbed post demo answer",
            },
        }

    monkeypatch.setattr(api_router_module.query_service, "demo_search_compat_response", fake_demo_search)
    resp = client.post("/demo/search", json={"question": "asthma symptoms"})
    assert resp.status_code == 200
    assert resp.json()["answers"]["a_text"] == "stubbed post demo answer"
