# Architecture

This document describes the current FastAPI project structure and request flow.

## Request Flow (Text Diagram)

```text
HTTP Request
  -> routers (app/routers/api.py, app/routers/web.py)
  -> query_service (app/services/query_service.py)
  -> nlp_service (app/services/nlp_service.py)
  -> neo4j_repository (app/repositories/neo4j_repository.py) / ollama_client (app/clients/ollama_client.py)
  -> prompt_builder (app/services/prompt_builder.py)
  -> HTTP Response
```

Notes:
- `/query`, `/llm_only`, `/demo/search`, `/health` are exposed by `routers/api.py`.
- `query_service` orchestrates fallback decisions and output shape.

## Module Responsibilities (One Line Each)

- `core/settings`: Centralized environment loading and typed runtime settings.
- `core/security`: API-key guard logic and local-warning behavior when key is unset.
- `routers`: HTTP route definitions and parameter mapping to service-layer calls.
- `services`: Domain/application logic orchestration (`query_service`, `nlp_service`, `prompt_builder`).
- `repositories`: Data access layer for Neo4j graph queries and lookup operations.
- `clients`: External service adapters (LLM call wrapper via Ollama HTTP API).

## Suggested Thesis Section Mapping

- `3.3.2` -> `app/services/nlp_service.py` (question type detection, term extraction, reranking helpers).
- `3.3.3` -> `app/repositories/neo4j_repository.py` (graph retrieval and concept lookup against Neo4j).
- `3.3.4` -> `app/services/query_service.py` + `app/services/prompt_builder.py` (end-to-end orchestration, prompt construction, fallback strategy).

## Environment Variables (From `app/core/settings.py`)

Source of truth: `app/core/settings.py` (`Settings.from_env`).

- `OPENAI_API_KEY`
- `NEO4J_URI`
- `NEO4J_USER`
- `NEO4J_PASSWORD`
- `OLLAMA_BASE_URL`
- `APP_API_KEY`
- `FRONTEND_ORIGINS` (comma-separated list; parsed into `list[str]`)
