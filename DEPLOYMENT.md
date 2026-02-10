# Deployment

## Required Environment Variables

- `OPENAI_API_KEY`: API key for `code/judge_eval.py` evaluation script.
- `NEO4J_URI`: Neo4j Bolt URI used by `app/main.py` (example: `bolt://host.docker.internal:7687`).
- `NEO4J_USER`: Neo4j username used by `app/main.py`.
- `NEO4J_PASSWORD`: Neo4j password used by `app/main.py`.
- `OLLAMA_BASE_URL`: Base URL for Ollama server used by `app/main.py` (example: `http://host.docker.internal:11434`).
- `APP_API_KEY`: API key for protected routes (`/query`, `/llm_only`, `/demo/search`). If empty, auth check is disabled for local testing.
- `FRONTEND_ORIGINS`: Comma-separated CORS allowlist, for example: `https://<username>.github.io,https://<username>.github.io/<repo>`.

## Local Run

1. Copy `.env.example` to `.env` and fill values.
2. Run:
   - `cd app`
   - `python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload`

## Docker Compose Run

1. Create `.env` from `.env.example`.
2. Run:
   - `docker compose up --build`

## Development / Tests

1. Run in `app/` directory:
   - `pip install -r requirements.txt -r requirements-dev.txt`
   - `pytest -q`

## GitHub Pages Frontend

1. Use `app/static/index.html` and `app/static/config.js` as static assets.
2. Set `window.__CONFIG__.API_BASE_URL` in `config.js` to your backend domain.
3. Set `window.__CONFIG__.API_KEY` in `config.js` to the same value as backend `APP_API_KEY`.
4. Deploy static files either:
   - repository root (Pages source = `main` root), or
   - `docs/` folder (Pages source = `main` /docs).
