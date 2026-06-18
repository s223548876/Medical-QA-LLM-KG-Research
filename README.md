# Medical-QA-LLM-KG-Research

醫療問答研究系統，整合 FastAPI、Neo4j 知識圖譜、Ollama 大型語言模型，以及 React/Vite 前端。系統支援「使用者模式」與「研究模式」，可比較純 LLM 與知識圖譜增強回答，並提供概念映射、子圖摘要與推理路徑。

> 本專案僅供研究、展示與系統評估用途，不應取代專業醫療診斷、治療或醫師建議。

## Features

- FastAPI 後端 API：提供 `/demo/search`、`/query`、`/llm_only`、`/health`
- React + Vite 前端：提供醫學問題輸入、主題建議、答案顯示與研究分析面板
- Neo4j 知識圖譜查詢：依醫學概念 ID 擷取 SNOMED CT 關係子圖
- Ollama LLM 生成：支援純 LLM 與知識圖譜增強答案
- 雙模式輸出：
  - 使用者模式：以較易讀的格式呈現知識圖譜重點與一般性補充
  - 研究模式：呈現純 LLM 與 KG + LLM 比較、SNOMED 映射、子圖摘要與推理路徑
- API Key 保護：以 `APP_API_KEY` / `X-API-KEY` 控制受保護 API
- CORS allowlist：以 `FRONTEND_ORIGINS` 控制可存取後端的前端來源
- GitHub Pages 前端部署流程：`frontend/dist` 可由 workflow 部署

## Tech Stack

| Layer | Technology |
| --- | --- |
| Backend | Python, FastAPI, Uvicorn |
| Knowledge graph | Neo4j |
| LLM runtime | Ollama HTTP API |
| NLP helpers | spaCy, scikit-learn |
| Frontend | React 18, Vite, TypeScript |
| UI | Tailwind CSS, Radix UI, lucide-react |
| Tests | pytest, FastAPI TestClient |

## Project Structure

```text
.
├─ app/
│  ├─ main.py                     # FastAPI entrypoint
│  ├─ routers/                    # HTTP route definitions
│  ├─ services/                   # Query orchestration, NLP, prompts
│  ├─ repositories/               # Neo4j data access
│  ├─ clients/                    # Ollama client
│  ├─ static/                     # Legacy static frontend assets
│  └─ tests/                      # Backend smoke tests
├─ frontend/
│  ├─ public/config.js            # Runtime API config for browser
│  ├─ src/app/                    # React application
│  └─ vite.config.ts
├─ code/                          # Evaluation and research scripts
├─ docs/                          # Architecture notes
├─ docker-compose.yml
├─ Dockerfile
├─ DEPLOYMENT.md
└─ README.md
```

## Request Flow

```text
Frontend
  -> /demo/search?mode=user|research
  -> routers/api.py
  -> services/query_service.py
  -> services/nlp_service.py
  -> repositories/neo4j_repository.py
  -> clients/ollama_client.py
  -> services/prompt_builder.py
  -> JSON response
```

## Modes

### 使用者模式

使用者模式透過 `mode=user` 啟用，目標是讓一般使用者較容易理解回答。輸出會優先呈現知識圖譜可支持的內容，並在需要時補充一般醫學常識。

前端入口：

```text
使用者模式 -> 提交查詢
```

API 範例：

```bash
curl -G "http://127.0.0.1:8000/demo/search" \
  -H "X-API-KEY: <APP_API_KEY>" \
  --data-urlencode "question=氣喘有哪些症狀？" \
  --data-urlencode "topic_key=Asthma" \
  --data-urlencode "qtype=symptoms" \
  --data-urlencode "mode=user"
```

### 研究模式

研究模式透過 `mode=research` 啟用，目標是支援研究與系統評估。前端會顯示純 LLM 與 KG + LLM 的比較、概念映射、子圖摘要、fallback 狀態與推理路徑。

API 範例：

```bash
curl -G "http://127.0.0.1:8000/demo/search" \
  -H "X-API-KEY: <APP_API_KEY>" \
  --data-urlencode "question=氣喘有哪些症狀？" \
  --data-urlencode "topic_key=Asthma" \
  --data-urlencode "qtype=symptoms" \
  --data-urlencode "mode=research"
```

## API Endpoints

### `GET /health`

健康檢查。

```bash
curl http://127.0.0.1:8000/health
```

Response:

```json
{ "status": "ok" }
```

### `GET /query`

查詢知識圖譜並產生 KG + LLM 回答。

Query parameters:

| Name | Required | Description |
| --- | --- | --- |
| `question` | yes | 使用者問題 |
| `mode` | no | `research` 或 `user`，預設 `research` |
| `qtype` / `qtype_hint` | no | `definition`、`symptoms`、`treatments` |
| `topic_key` | no | 主題對應英文醫學詞，例如 `Asthma` |
| `lite` | no | `1` 使用較輕量的自然語句生成 |
| `max_k` | no | 候選概念上限 |
| `model` | no | Ollama 模型名稱 |

### `GET /llm_only`

只呼叫 LLM，不使用知識圖譜。

```bash
curl -G "http://127.0.0.1:8000/llm_only" \
  -H "X-API-KEY: <APP_API_KEY>" \
  --data-urlencode "question=什麼是糖尿病？"
```

### `GET /demo/search`

前端主要使用的相容 API。回傳內容同時包含核心查詢結果與前端比較欄位。

重要 response 欄位：

| Field | Description |
| --- | --- |
| `answers.a_text` | 知識圖譜 + LLM 答案 |
| `answers.b_text` | 純 LLM 答案 |
| `results[0].answer` | 核心 KG + LLM 結果 |
| `results[0].subgraph_summary` | 子圖摘要 |
| `mapped_to.bank_id` | 對應概念 ID |
| `mapped_to.qtype` | 問題類型 |
| `debug` | fallback、timing、evidence level 等除錯資訊 |

### `POST /demo/search`

支援 JSON body 的 demo search。

```bash
curl -X POST "http://127.0.0.1:8000/demo/search?mode=user" \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: <APP_API_KEY>" \
  -d "{\"question\":\"氣喘有哪些症狀？\",\"topic_key\":\"Asthma\",\"qtype\":\"symptoms\"}"
```

## Environment Variables

請先複製 `.env.example`：

```bash
cp .env.example .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

填入以下變數：

| Variable | Description | Example |
| --- | --- | --- |
| `OPENAI_API_KEY` | 評估腳本可能使用的 OpenAI API key | empty for local demo |
| `NEO4J_URI` | Neo4j Bolt URI | `bolt://localhost:7687` |
| `NEO4J_USER` | Neo4j 使用者 | `neo4j` |
| `NEO4J_PASSWORD` | Neo4j 密碼 | `your-password` |
| `OLLAMA_BASE_URL` | Ollama server URL | `http://localhost:11434` |
| `APP_API_KEY` | 後端 API key | `dev-local-key` |
| `FRONTEND_ORIGINS` | CORS allowlist, comma-separated | `http://localhost:5173,http://127.0.0.1:5173` |

安全注意：

- 不要 commit `.env`
- 不要把真實 API key 寫進 `frontend/public/config.js`
- 公開部署時請使用自己的後端網域與 API key 管理方式

## Backend Setup

### 1. Install Python dependencies

```bash
cd app
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt
```

macOS / Linux:

```bash
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
```

### 2. Start Neo4j

本專案預期 Neo4j 已載入醫學知識圖譜資料。若使用 Docker Compose，可先準備 `.env`，再執行：

```bash
docker compose up neo4j
```

Neo4j browser 預設位於：

```text
http://localhost:7474
```

### 3. Start Ollama

確認 Ollama 已啟動，並已安裝要使用的模型，例如：

```bash
ollama pull cwchang/llama-3-taiwan-8b-instruct
```

預設後端會呼叫：

```text
http://localhost:11434/api/generate
```

### 4. Run FastAPI

在 `app/` 目錄中執行：

```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

健康檢查：

```bash
curl http://127.0.0.1:8000/health
```

## Frontend Setup

### 1. Install dependencies

```bash
cd frontend
npm install
```

### 2. Configure runtime API

編輯 `frontend/public/config.js`：

```js
window.__CONFIG__ = window.__CONFIG__ || {
  API_BASE_URL: "http://127.0.0.1:8000",
  API_KEY: "dev-local-key"
};
```

`API_KEY` 需與後端 `.env` 的 `APP_API_KEY` 一致。

### 3. Run development server

```bash
npm run dev
```

預設網址：

```text
http://localhost:5173
```

### 4. Build

```bash
npm run build
```

輸出目錄：

```text
frontend/dist
```

## Docker

準備 `.env` 後可執行：

```bash
docker compose up --build
```

服務：

- Backend: `http://127.0.0.1:8000`
- Neo4j Browser: `http://127.0.0.1:7474`

注意：`docker-compose.yml` 使用 `.env` 注入設定，Neo4j 資料 volume 預設放在本機 `neo4j/`，此資料夾不應提交到 Git。

## Tests

Backend smoke tests:

```bash
pytest -q
```

Frontend build check:

```bash
cd frontend
npm run build
```

Manual API check:

```bash
curl -G "http://127.0.0.1:8000/demo/search" \
  -H "X-API-KEY: <APP_API_KEY>" \
  --data-urlencode "question=氣喘有哪些症狀？" \
  --data-urlencode "topic_key=Asthma" \
  --data-urlencode "qtype=symptoms" \
  --data-urlencode "mode=research"
```

## Evaluation Scripts

`code/` 目錄保存研究評估與分析腳本，例如：

- `evaluate_bertscore.py`
- `judge_eval.py`
- `judge_stats.py`
- `ci_bootstrap.py`
- `summarize_efficiency.py`

部分腳本會讀取本機實驗資料或呼叫 API。請依腳本參數與 `.env` 設定調整路徑、API base URL 與 API key。

## Deployment

### Backend

可部署到任何支援 Python ASGI 的平台。必要條件：

- 可連線到 Neo4j
- 可連線到 Ollama 或相容 LLM 服務
- 設定 `APP_API_KEY`
- 設定 `FRONTEND_ORIGINS`

啟動命令：

```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

### Frontend

GitHub Pages workflow 會建置 `frontend` 並部署 `dist`。Vite base path 由 `frontend/vite.config.ts` 控制：

- 若有 `VITE_BASE_PATH`，優先使用該值
- 否則使用 GitHub repository 名稱推導 base path

部署前請更新 `frontend/public/config.js`：

```js
window.__CONFIG__ = window.__CONFIG__ || {
  API_BASE_URL: "https://your-backend-domain",
  API_KEY: "your-public-demo-key"
};
```

## Troubleshooting

### API 回 401

確認前端 `frontend/public/config.js` 的 `API_KEY` 是否與後端 `.env` 的 `APP_API_KEY` 相同。

### 前端無法連線後端

確認：

- 後端是否在 `http://127.0.0.1:8000`
- `FRONTEND_ORIGINS` 是否包含 `http://localhost:5173` 或 `http://127.0.0.1:5173`
- `frontend/public/config.js` 的 `API_BASE_URL` 是否正確

### LLM 回傳呼叫失敗

確認：

- Ollama 是否啟動
- `OLLAMA_BASE_URL` 是否正確
- 指定模型是否已 `ollama pull`

### 知識圖譜沒有結果

確認：

- Neo4j 是否啟動
- `NEO4J_URI`、`NEO4J_USER`、`NEO4J_PASSWORD` 是否正確
- 知識圖譜資料是否已匯入
- 查詢是否提供合適的 `topic_key`

## Security And Repository Hygiene

本 repo 已排除下列本機或大型檔案：

- `.env` / `.env.*`
- `app/models/`
- `frontend/node_modules/`
- `frontend/dist/`
- `neo4j/`
- `*.log`
- 本機實驗輸出資料夾

若需要分享大型模型、Neo4j dump 或實驗資料，建議使用私有儲存、release artifact、cloud bucket 或資料集管理工具，不要直接 commit 到 GitHub。

## References

- 架構說明：[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- 部署補充：[DEPLOYMENT.md](DEPLOYMENT.md)
- FastAPI: https://fastapi.tiangolo.com/
- Neo4j: https://neo4j.com/
- Ollama: https://ollama.com/
- Vite: https://vite.dev/
